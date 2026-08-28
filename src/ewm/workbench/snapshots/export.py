"""Deterministic standalone HTML export and verification for investigations."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ewm.ontology.snapshots import (
    DEFAULT_MAX_HTML_BYTES,
    INVESTIGATION_SCHEMA,
    InvestigationSnapshot,
    investigation_from_bytes,
    investigation_to_bytes,
)

_STATIC_DIRECTORY = Path(__file__).parents[1] / "static"
_SNAPSHOT_TEMPLATE = re.compile(
    r'<template id="ewm-snapshot" data-sha256="([a-f0-9]{64})">([^<]+)</template>'
)
_SCHEMA_META = f'<meta name="ewm-snapshot-schema" content="{INVESTIGATION_SCHEMA}">'
_SCRIPT = re.compile(r'<script type="module">(.*?)</script>', re.DOTALL)
_STYLE = re.compile(r"<style>(.*?)</style>", re.DOTALL)
_CSP = re.compile(
    r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">'
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _csp_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


@dataclass(frozen=True, slots=True)
class SnapshotAssets:
    """The shared reproducible frontend bundle in inline-safe form."""

    script: str
    style: str

    def __post_init__(self) -> None:
        if "</script" in self.script.lower():
            raise ValueError("snapshot script contains an unsafe closing script sequence")
        if "</style" in self.style.lower():
            raise ValueError("snapshot style contains an unsafe closing style sequence")

    @property
    def script_sha256_csp(self) -> str:
        return _csp_sha256(self.script)

    @property
    def style_sha256_csp(self) -> str:
        return _csp_sha256(self.style)

    @classmethod
    def from_built_workbench(cls, directory: Path | None = None) -> SnapshotAssets:
        """Load the single shared API/snapshot bundle from the generated manifest."""

        root = directory or _STATIC_DIRECTORY
        try:
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            entry = manifest["index.html"]
            imports = tuple(entry.get("imports", ()))
            dynamic = tuple(
                item
                for item in entry.get("dynamicImports", ())
                if item != "index.html"
            )
            css_files = tuple(entry.get("css", ()))
            if imports or dynamic or len(css_files) != 1:
                raise SnapshotExportError(
                    "built workbench is not a self-contained single frontend bundle",
                    code="snapshot_assets_not_single_bundle",
                    context={"imports": list(imports), "dynamic_imports": list(dynamic)},
                )
            script = (root / str(entry["file"])).read_text(encoding="utf-8")
            style = (root / str(css_files[0])).read_text(encoding="utf-8")
        except SnapshotExportError:
            raise
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise SnapshotExportError(
                "reproducible workbench assets are missing or invalid",
                code="snapshot_assets_invalid",
            ) from error
        return cls(script=script, style=style)


class SnapshotExportError(ValueError):
    """Machine-readable standalone-export failure."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "snapshot_export_failed",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "context": dict(self.context)}


class SnapshotVerificationError(ValueError):
    """Raised when standalone bytes fail structural or integrity verification."""


@dataclass(frozen=True, slots=True)
class SnapshotExportReport:
    output: Path
    file_sha256: str
    embedded_sha256: str
    subset_digest: str
    projection_digest: str
    html_bytes: int
    authenticity_claim: str = "separately-comparable-file-digest-only"
    digital_signature_present: bool = False


@dataclass(frozen=True, slots=True)
class SnapshotVerificationReport:
    path: Path
    ok: bool
    file_sha256: str
    embedded_sha256: str
    subset_digest: str
    projection_digest: str
    source_bundle_sha256: str
    authenticity_verified: bool
    authenticity_claim: str = "separately-comparable-file-digest-only"
    digital_signature_present: bool = False


def _document(payload: bytes, assets: SnapshotAssets) -> bytes:
    embedded_sha256 = _sha256(payload)
    encoded = base64.b64encode(payload).decode("ascii")
    csp = "; ".join(
        (
            "default-src 'none'",
            "base-uri 'none'",
            "connect-src 'none'",
            "font-src data:",
            "form-action 'none'",
            "img-src data: blob:",
            f"script-src {assets.script_sha256_csp}",
            f"style-src {assets.style_sha256_csp}",
            "worker-src 'none'",
        )
    )
    html = (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"{_SCHEMA_META}\n"
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">\n'
        "<title>EWM · Portable Investigation</title>\n"
        f"<style>{assets.style}</style>\n"
        "</head>\n"
        "<body>\n"
        '<div id="root"></div>\n'
        f'<template id="ewm-snapshot" data-sha256="{embedded_sha256}">{encoded}</template>\n'
        f'<script type="module">{assets.script}</script>\n'
        "</body>\n"
        "</html>\n"
    )
    return html.encode("utf-8")


def _prepare_output(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise SnapshotExportError("snapshot output must not be a symbolic link")
    mode = path.parent.lstat().st_mode
    if path.parent.is_symlink() or not stat.S_ISDIR(mode):
        raise SnapshotExportError("snapshot output parent must be a real directory")


def _atomic_write(path: Path, value: bytes) -> None:
    _prepare_output(path)
    descriptor, staging_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".staging", dir=path.parent
    )
    staging = Path(staging_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staging, path)
    finally:
        if staging.exists():
            staging.unlink()


def export_snapshot_html(
    snapshot: InvestigationSnapshot,
    output: Path,
    *,
    assets: SnapshotAssets | None = None,
    max_html_bytes: int = DEFAULT_MAX_HTML_BYTES,
) -> SnapshotExportReport:
    """Write one deterministic, CSP-constrained, standalone investigation."""

    if isinstance(max_html_bytes, bool) or max_html_bytes < 1:
        raise ValueError("maximum snapshot HTML bytes must be positive")
    payload = investigation_to_bytes(snapshot)
    selected_assets = assets or SnapshotAssets.from_built_workbench()
    document = _document(payload, selected_assets)
    if len(document) > max_html_bytes:
        raise SnapshotExportError(
            "generated snapshot exceeds the standalone HTML size limit",
            code="snapshot_file_size_exceeded",
            context={
                "generated_html_bytes": len(document),
                "max_html_bytes": max_html_bytes,
                "reductions": [
                    "select fewer ontology objects, relations, or events",
                    "omit the globe lens when geographic geometry is not needed",
                ],
            },
        )
    target = Path(output)
    _atomic_write(target, document)
    return SnapshotExportReport(
        output=target,
        file_sha256=_sha256(document),
        embedded_sha256=_sha256(payload),
        subset_digest=snapshot.subset_digest,
        projection_digest=snapshot.projection_digest,
        html_bytes=len(document),
    )


def write_detached_sha256(report: SnapshotExportReport) -> Path:
    """Write the optional separately comparable full-file digest."""

    path = report.output.with_suffix(report.output.suffix + ".sha256")
    _atomic_write(path, (report.file_sha256 + "\n").encode("ascii"))
    return path


def verify_snapshot_html(
    path: Path,
    *,
    expected_file_sha256: str | None = None,
) -> SnapshotVerificationReport:
    """Verify file, CSP, embedded bytes, canonical schema, and subset integrity."""

    selected_path = Path(path)
    try:
        document = selected_path.read_bytes()
        html = document.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SnapshotVerificationError("snapshot is not readable UTF-8 HTML") from error
    file_sha256 = _sha256(document)
    if expected_file_sha256 is not None:
        if not re.fullmatch(r"[a-f0-9]{64}", expected_file_sha256):
            raise SnapshotVerificationError("expected file digest is not lowercase SHA-256")
        if file_sha256 != expected_file_sha256:
            raise SnapshotVerificationError("snapshot does not match the expected file digest")
    if _SCHEMA_META not in html:
        raise SnapshotVerificationError("snapshot document schema is missing or unsupported")
    match = _SNAPSHOT_TEMPLATE.search(html)
    if match is None:
        raise SnapshotVerificationError("snapshot embedded payload is missing or malformed")
    declared_digest, encoded = match.groups()
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise SnapshotVerificationError("snapshot embedded payload is not valid base64") from error
    embedded_sha256 = _sha256(payload)
    if embedded_sha256 != declared_digest:
        raise SnapshotVerificationError("snapshot embedded payload digest does not match")
    script_match = _SCRIPT.search(html)
    style_match = _STYLE.search(html)
    csp_match = _CSP.search(html)
    if script_match is None or style_match is None or csp_match is None:
        raise SnapshotVerificationError("snapshot executable assets or CSP are missing")
    csp = csp_match.group(1)
    if _csp_sha256(script_match.group(1)) not in csp:
        raise SnapshotVerificationError("snapshot script CSP hash does not match")
    if _csp_sha256(style_match.group(1)) not in csp:
        raise SnapshotVerificationError("snapshot style CSP hash does not match")
    non_executable_shell = _STYLE.sub("", _SCRIPT.sub("", html)).lower()
    if any(token in non_executable_shell for token in ('src="', 'href="')):
        raise SnapshotVerificationError("snapshot contains an external resource reference")
    try:
        snapshot = investigation_from_bytes(payload)
    except (TypeError, ValueError) as error:
        raise SnapshotVerificationError(f"snapshot payload failed verification: {error}") from error
    return SnapshotVerificationReport(
        path=selected_path,
        ok=True,
        file_sha256=file_sha256,
        embedded_sha256=embedded_sha256,
        subset_digest=snapshot.subset_digest,
        projection_digest=snapshot.projection_digest,
        source_bundle_sha256=snapshot.source_bundle_sha256,
        authenticity_verified=expected_file_sha256 is not None,
    )


__all__ = [
    "SnapshotAssets",
    "SnapshotExportError",
    "SnapshotExportReport",
    "SnapshotVerificationError",
    "SnapshotVerificationReport",
    "export_snapshot_html",
    "verify_snapshot_html",
    "write_detached_sha256",
]
