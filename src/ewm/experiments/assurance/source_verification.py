"""Verification of paper sources locked by the source registry."""

from __future__ import annotations

import hashlib
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import Path

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class SourceVerificationStatus(StrEnum):
    """Outcomes from observing one locked source on the local filesystem."""

    VERIFIED = "verified"
    NOT_PRESENT = "not_present"
    HASH_MISMATCH = "hash_mismatch"
    PAGE_COUNT_MISMATCH = "page_count_mismatch"
    INVALID_PDF = "invalid_pdf"


@dataclass(frozen=True, slots=True)
class PaperSource:
    """Immutable fields needed to identify and verify one paper source."""

    id: str
    title: str
    authors: tuple[str, ...]
    version: str
    pages: int
    public_url: str
    sha256: str
    local_filename: str
    media_type: str
    local_pdf_tracked: bool
    preflight: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class SourceVerification:
    """Expected and observed identity for one local paper source."""

    source_id: str
    status: SourceVerificationStatus
    local_filename: str
    expected_sha256: str
    observed_sha256: str | None
    expected_pages: int
    observed_pages: int | None
    detail: str | None = None

    def as_dict(self) -> dict[str, object]:
        """Return the stable JSON-compatible representation used in reports."""

        return {
            "detail": self.detail,
            "expected_pages": self.expected_pages,
            "expected_sha256": self.expected_sha256,
            "local_filename": self.local_filename,
            "observed_pages": self.observed_pages,
            "observed_sha256": self.observed_sha256,
            "status": self.status.value,
        }


def _required_string(
    record: Mapping[str, object],
    field: str,
    *,
    location: str,
) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{location}.{field} must be a non-empty string")
    return value


def _optional_string(
    record: Mapping[str, object],
    field: str,
    *,
    location: str,
) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{location}.{field} must be a non-empty string when present")
    return value


def _parse_source(record: Mapping[str, object], *, index: int) -> PaperSource:
    location = f"source[{index}]"
    source_id = _required_string(record, "id", location=location)
    pages = record.get("pages")
    if isinstance(pages, bool) or not isinstance(pages, int) or pages <= 0:
        raise ValueError(f"{location}.pages must be a positive integer")
    authors = record.get("authors")
    if (
        not isinstance(authors, list)
        or not authors
        or not all(isinstance(author, str) and author for author in authors)
    ):
        raise ValueError(f"{location}.authors must be a non-empty list of strings")
    sha256 = _required_string(record, "sha256", location=location)
    if _SHA256_PATTERN.fullmatch(sha256) is None:
        raise ValueError(f"{location}.sha256 must be a lowercase SHA-256 digest")
    local_filename = _required_string(record, "local_filename", location=location)
    candidate = Path(local_filename)
    if candidate.is_absolute() or candidate.name != local_filename:
        raise ValueError(f"{location}.local_filename must be a filename, not a path")
    media_type = _required_string(record, "media_type", location=location)
    if media_type != "application/pdf":
        raise ValueError(f"{location}.media_type must be application/pdf")
    local_pdf_tracked = record.get("local_pdf_tracked")
    if not isinstance(local_pdf_tracked, bool):
        raise ValueError(f"{location}.local_pdf_tracked must be a boolean")
    return PaperSource(
        id=source_id,
        title=_required_string(record, "title", location=location),
        authors=tuple(authors),
        version=_required_string(record, "version", location=location),
        pages=pages,
        public_url=_required_string(record, "public_url", location=location),
        sha256=sha256,
        local_filename=local_filename,
        media_type=media_type,
        local_pdf_tracked=local_pdf_tracked,
        preflight=_optional_string(record, "preflight", location=location),
        notes=_optional_string(record, "notes", location=location),
    )


def load_paper_sources(registry_path: Path) -> tuple[PaperSource, ...]:
    """Parse and validate the paper records in an enriched TOML registry."""

    with registry_path.open("rb") as handle:
        registry = tomllib.load(handle)
    schema_version = registry.get("schema_version")
    if schema_version != 1:
        raise ValueError("papers registry schema_version must be 1")
    raw_sources = registry.get("source")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("papers registry must contain at least one [[source]] record")

    sources: list[PaperSource] = []
    identifiers: set[str] = set()
    filenames: set[str] = set()
    for index, raw_source in enumerate(raw_sources):
        if not isinstance(raw_source, dict):
            raise ValueError(f"source[{index}] must be a table")
        source = _parse_source(raw_source, index=index)
        if source.id in identifiers:
            raise ValueError(f"duplicate paper source id: {source.id}")
        if source.local_filename in filenames:
            raise ValueError(f"duplicate paper source filename: {source.local_filename}")
        identifiers.add(source.id)
        filenames.add(source.local_filename)
        sources.append(source)
    return tuple(sources)


def _pdf_page_count(content: bytes) -> int:
    if not content.startswith(b"%PDF-"):
        raise ValueError("file does not have a PDF header")
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - exercised outside the dev environment
        raise RuntimeError(
            "PDF structure verification requires the 'pypdf' development dependency"
        ) from exc
    reader = PdfReader(BytesIO(content), strict=True)
    return len(reader.pages)


def _verify_source(source: PaperSource, *, source_dir: Path) -> SourceVerification:
    path = source_dir / source.local_filename
    if not path.exists():
        return SourceVerification(
            source_id=source.id,
            status=SourceVerificationStatus.NOT_PRESENT,
            local_filename=source.local_filename,
            expected_sha256=source.sha256,
            observed_sha256=None,
            expected_pages=source.pages,
            observed_pages=None,
        )
    if not path.is_file():
        return SourceVerification(
            source_id=source.id,
            status=SourceVerificationStatus.INVALID_PDF,
            local_filename=source.local_filename,
            expected_sha256=source.sha256,
            observed_sha256=None,
            expected_pages=source.pages,
            observed_pages=None,
            detail="source path is not a regular file",
        )

    try:
        content = path.read_bytes()
    except OSError as exc:
        return SourceVerification(
            source_id=source.id,
            status=SourceVerificationStatus.INVALID_PDF,
            local_filename=source.local_filename,
            expected_sha256=source.sha256,
            observed_sha256=None,
            expected_pages=source.pages,
            observed_pages=None,
            detail=f"source could not be read: {exc}",
        )
    observed_sha256 = hashlib.sha256(content).hexdigest()
    if observed_sha256 != source.sha256:
        return SourceVerification(
            source_id=source.id,
            status=SourceVerificationStatus.HASH_MISMATCH,
            local_filename=source.local_filename,
            expected_sha256=source.sha256,
            observed_sha256=observed_sha256,
            expected_pages=source.pages,
            observed_pages=None,
        )

    try:
        observed_pages = _pdf_page_count(content)
    except Exception as exc:
        return SourceVerification(
            source_id=source.id,
            status=SourceVerificationStatus.INVALID_PDF,
            local_filename=source.local_filename,
            expected_sha256=source.sha256,
            observed_sha256=observed_sha256,
            expected_pages=source.pages,
            observed_pages=None,
            detail=str(exc),
        )
    status = (
        SourceVerificationStatus.VERIFIED
        if observed_pages == source.pages
        else SourceVerificationStatus.PAGE_COUNT_MISMATCH
    )
    return SourceVerification(
        source_id=source.id,
        status=status,
        local_filename=source.local_filename,
        expected_sha256=source.sha256,
        observed_sha256=observed_sha256,
        expected_pages=source.pages,
        observed_pages=observed_pages,
    )


def verify_sources(
    registry_path: Path,
    *,
    source_dir: Path,
) -> tuple[SourceVerification, ...]:
    """Observe every registered source without fetching or modifying source files."""

    return tuple(
        _verify_source(source, source_dir=source_dir)
        for source in load_paper_sources(registry_path)
    )


def verification_failed(
    results: tuple[SourceVerification, ...],
    *,
    require_sources: bool,
) -> bool:
    """Return whether observed results must fail a verification command."""

    allowed = (
        {SourceVerificationStatus.VERIFIED}
        if require_sources
        else {
            SourceVerificationStatus.VERIFIED,
            SourceVerificationStatus.NOT_PRESENT,
        }
    )
    return any(result.status not in allowed for result in results)
