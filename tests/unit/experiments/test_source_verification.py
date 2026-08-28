"""Unit contracts for paper-source verification."""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path

import pytest
from ewm.experiments.source_verification import (
    load_paper_sources,
    verify_sources,
)


@dataclass(frozen=True)
class SourceFixture:
    registry_path: Path
    source_dir: Path
    pdf_path: Path
    sha256: str


def _minimal_pdf(page_count: int) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            b"<< /Type /Pages /Count "
            + str(page_count).encode("ascii")
            + b" /Kids ["
            + b" ".join(
                f"{object_number} 0 R".encode("ascii") for object_number in range(3, page_count + 3)
            )
            + b"] >>"
        ),
    ]
    objects.extend(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>" for _ in range(page_count)
    )

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_number} 0 obj\n".encode("ascii"))
        document.extend(body)
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)


def _write_pdf(path: Path, *, page_count: int) -> None:
    if importlib.util.find_spec("pypdf") is not None:
        from pypdf import PdfWriter

        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=612, height=792)
        with path.open("wb") as handle:
            writer.write(handle)
        return
    path.write_bytes(_minimal_pdf(page_count))


def _write_registry(
    path: Path,
    *,
    sha256: str,
    pages: int,
    local_filename: str = "fixture-paper.pdf",
) -> None:
    path.write_text(
        f'''schema_version = 1

[[source]]
id = "fixture-paper"
title = "Fixture Paper"
authors = ["Test Author"]
version = "Fixture version 1"
pages = {pages}
public_url = "https://example.invalid/fixture-paper"
sha256 = "{sha256}"
local_filename = "{local_filename}"
media_type = "application/pdf"
local_pdf_tracked = false
''',
        encoding="utf-8",
    )


@pytest.fixture
def source_fixture(tmp_path: Path) -> SourceFixture:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    pdf_path = source_dir / "fixture-paper.pdf"
    _write_pdf(pdf_path, page_count=2)
    sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    registry_path = tmp_path / "papers.toml"
    _write_registry(registry_path, sha256=sha256, pages=2)
    return SourceFixture(
        registry_path=registry_path,
        source_dir=source_dir,
        pdf_path=pdf_path,
        sha256=sha256,
    )


def test_load_paper_sources_parses_enriched_registry_fields(
    source_fixture: SourceFixture,
) -> None:
    sources = load_paper_sources(source_fixture.registry_path)

    assert len(sources) == 1
    source = sources[0]
    assert source.id == "fixture-paper"
    assert source.local_filename == "fixture-paper.pdf"
    assert source.media_type == "application/pdf"
    assert source.pages == 2
    assert source.sha256 == source_fixture.sha256


def test_verify_sources_observes_matching_pdf(
    source_fixture: SourceFixture,
) -> None:
    results = verify_sources(
        source_fixture.registry_path,
        source_dir=source_fixture.source_dir,
    )

    assert len(results) == 1
    result = results[0]
    assert result.source_id == "fixture-paper"
    assert result.status == "verified"
    assert result.observed_sha256 == source_fixture.sha256
    assert result.observed_pages == 2


def test_verify_sources_reports_missing_pdf_without_false_pass(
    source_fixture: SourceFixture,
) -> None:
    source_fixture.pdf_path.unlink()

    result = verify_sources(
        source_fixture.registry_path,
        source_dir=source_fixture.source_dir,
    )[0]

    assert result.status == "not_present"
    assert result.observed_sha256 is None
    assert result.observed_pages is None


def test_verify_sources_detects_mutated_pdf(
    source_fixture: SourceFixture,
) -> None:
    source_fixture.pdf_path.write_bytes(
        source_fixture.pdf_path.read_bytes() + b"\n% checksum mutation\n"
    )

    result = verify_sources(
        source_fixture.registry_path,
        source_dir=source_fixture.source_dir,
    )[0]

    assert result.status == "hash_mismatch"
    assert (
        result.observed_sha256 == hashlib.sha256(source_fixture.pdf_path.read_bytes()).hexdigest()
    )
    assert result.observed_sha256 != source_fixture.sha256


def test_verify_sources_detects_page_count_mismatch(
    source_fixture: SourceFixture,
) -> None:
    _write_registry(
        source_fixture.registry_path,
        sha256=source_fixture.sha256,
        pages=3,
    )

    result = verify_sources(
        source_fixture.registry_path,
        source_dir=source_fixture.source_dir,
    )[0]

    assert result.status == "page_count_mismatch"
    assert result.observed_sha256 == source_fixture.sha256
    assert result.observed_pages == 2
