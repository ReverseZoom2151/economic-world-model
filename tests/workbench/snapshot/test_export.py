"""Standalone HTML export, CSP, and corruption-verification contracts."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ewm.ontology.snapshot import SnapshotSelection, SnapshotSource, compile_investigation
from ewm.workbench.export import (
    SnapshotAssets,
    SnapshotExportError,
    SnapshotVerificationError,
    export_snapshot_html,
    verify_snapshot_html,
)


def _investigation(approved_registry):
    approved = approved_registry.get("left")
    return compile_investigation(
        approved.projection,
        SnapshotSource(
            run_id=approved.run_id,
            source_run_hash=approved.source_run_hash,
            source_identity_sha256="1" * 64,
            source_bundle_sha256="2" * 64,
            profile_identity=approved.profile_identity,
            profile_digest="3" * 64,
            integrity_level=approved.integrity_level,
        ),
        SnapshotSelection.from_data({"lens": "world"}),
    )


def test_export_is_deterministic_self_contained_and_csp_hashed(
    tmp_path: Path,
    approved_registry,
) -> None:
    assets = SnapshotAssets(
        script="document.documentElement.dataset.snapshotReady='true';",
        style="body{color:#11130f}",
    )
    first = tmp_path / "first.html"
    second = tmp_path / "second.html"

    first_report = export_snapshot_html(_investigation(approved_registry), first, assets=assets)
    second_report = export_snapshot_html(_investigation(approved_registry), second, assets=assets)
    html = first.read_text(encoding="utf-8")

    assert first.read_bytes() == second.read_bytes()
    assert first_report.file_sha256 == second_report.file_sha256
    assert first_report.file_sha256 == hashlib.sha256(first.read_bytes()).hexdigest()
    assert "ewm.investigation.v1" in html
    assert "Content-Security-Policy" in html
    assert assets.script_sha256_csp in html
    assert assets.style_sha256_csp in html
    assert '<template id="ewm-snapshot"' in html
    assert "http://" not in html and "https://" not in html
    assert "src=" not in html and "href=" not in html
    assert "digital-signature" not in html
    verification = verify_snapshot_html(first, expected_file_sha256=first_report.file_sha256)
    assert verification.ok is True
    assert verification.authenticity_verified is True
    assert verification.digital_signature_present is False


def test_verifier_detects_embedded_corruption_and_external_digest_mismatch(
    tmp_path: Path,
    approved_registry,
) -> None:
    output = tmp_path / "snapshot.html"
    report = export_snapshot_html(
        _investigation(approved_registry),
        output,
        assets=SnapshotAssets(script="void 0;", style="body{}"),
    )

    with pytest.raises(SnapshotVerificationError, match="expected file digest"):
        verify_snapshot_html(output, expected_file_sha256="0" * 64)

    html = output.read_text(encoding="utf-8")
    marker = '<template id="ewm-snapshot"'
    start = html.index(">", html.index(marker)) + 1
    corrupted = html[:start] + ("A" if html[start] != "A" else "B") + html[start + 1 :]
    output.write_text(corrupted, encoding="utf-8")

    with pytest.raises(SnapshotVerificationError, match="embedded payload digest"):
        verify_snapshot_html(output)
    assert report.authenticity_claim == "separately-comparable-file-digest-only"


def test_export_refuses_html_above_the_declared_file_limit(
    tmp_path: Path,
    approved_registry,
) -> None:
    with pytest.raises(SnapshotExportError) as caught:
        export_snapshot_html(
            _investigation(approved_registry),
            tmp_path / "too-large.html",
            assets=SnapshotAssets(script="x" * 4_096, style="body{}"),
            max_html_bytes=512,
        )

    assert caught.value.as_dict()["code"] == "snapshot_file_size_exceeded"
    assert not (tmp_path / "too-large.html").exists()
