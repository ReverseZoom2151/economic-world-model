"""CLI integration for canonical geographic overlay sidecars."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ewm
from ewm.cli import main
from ewm.ontology import DEFAULT_PROFILES, compile_run_projection, load_projection_bundle


def _run(root: Path) -> Path:
    return ewm.run_experiment(
        "fx.rollout",
        preset="smoke",
        seed=37,
        output_root=root,
    ).run_dir


def _overlay(target_id: str, **entry_overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "target_id": target_id,
        "crs": "EPSG:4326",
        "latitude": 44.4268,
        "longitude": 26.1025,
        "anchor_basis": "externally_supplied",
        "validity": {"start": "2026-01-01", "end": "2026-12-31"},
        "uncertainty_km": 5.0,
        "source": {
            "source_kind": "external_dataset",
            "source_id": "registry:locations:v1",
            "artifact_path": "sources/locations.csv",
            "record_selector": "row:17",
            "payload_digest": "d" * 64,
        },
    }
    entry.update(entry_overrides)
    return {"schema": "ewm.geo-overlay.v1", "anchors": [entry]}


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, allow_nan=False, sort_keys=True), encoding="utf-8")


def test_cli_applies_external_overlay_without_mutating_the_sealed_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _run(tmp_path / "runs")
    before = {path.name: path.read_bytes() for path in run_dir.iterdir()}
    base = compile_run_projection(run_dir, adapters=DEFAULT_PROFILES).projection
    target = next(item for item in base.objects if item.ref.kind == "market")
    overlay_path = tmp_path / "research-inputs" / "geo.json"
    overlay_path.parent.mkdir()
    _write(overlay_path, _overlay(target.ref.id))
    output = tmp_path / "derived" / "ontology"

    status = main(
        [
            "ontology",
            "project",
            "--run-dir",
            str(run_dir),
            "--output",
            str(output),
            "--geo-overlay",
            str(overlay_path),
        ]
    )
    result = json.loads(capsys.readouterr().out)
    projection = load_projection_bundle(output)

    assert status == 0
    assert result["geo_overlay_digest"] == next(
        item.properties["overlay_digest"]
        for item in projection.objects
        if item.ref.kind == "geo_anchor"
    )
    assert result["projection_digest"] != base.projection_digest
    assert any(item.relation_type == "GEO_ANCHORED_AT" for item in projection.relations)
    anchor = next(item for item in projection.objects if item.ref.kind == "geo_anchor")
    assert anchor.properties["evidence_classification"] == "researcher_declared"
    assert anchor.properties["anchor_basis"] == "externally_supplied"
    assert before == {path.name: path.read_bytes() for path in run_dir.iterdir()}
    assert overlay_path.is_file()
    assert overlay_path.parent not in run_dir.parents


@pytest.mark.parametrize(
    "overlay",
    (
        _overlay("ewm:unknown:market"),
        _overlay("placeholder", source=None),
        _overlay("placeholder", latitude=100.0),
    ),
)
def test_cli_rejects_unknown_targets_missing_sources_and_invalid_coordinates(
    overlay: dict[str, object],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _run(tmp_path / "runs")
    base = compile_run_projection(run_dir, adapters=DEFAULT_PROFILES).projection
    known_id = next(item.ref.id for item in base.objects if item.ref.kind == "market")
    entry = overlay["anchors"][0]  # type: ignore[index]
    if entry["target_id"] == "placeholder":  # type: ignore[index]
        entry["target_id"] = known_id  # type: ignore[index]
    overlay_path = tmp_path / "geo.json"
    _write(overlay_path, overlay)
    output = tmp_path / "must-not-exist"

    status = main(
        [
            "ontology",
            "project",
            "--run-dir",
            str(run_dir),
            "--output",
            str(output),
            "--geo-overlay",
            str(overlay_path),
        ]
    )
    failure = json.loads(capsys.readouterr().out)

    assert status != 0
    assert failure["error_type"] == "GeoOverlayError"
    assert not output.exists()
