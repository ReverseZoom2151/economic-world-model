"""Adversarial parser, transport, geometry, and snapshot boundaries."""

from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from ewm.ontology.snapshot import SnapshotSelection, validate_globe_geometry
from ewm.workbench.export import SnapshotAssets


@pytest.mark.parametrize(
    "query",
    (
        {"file": "../../etc/passwd"},
        {"run_dir": "C:\\Users\\attacker"},
        {"token": "secret-in-query"},
    ),
)
def test_api_rejects_path_and_secret_selectors(
    client: TestClient,
    api_headers: dict[str, str],
    query: dict[str, str],
) -> None:
    response = client.get("/api/v1/system", params=query, headers=api_headers)

    assert response.status_code == 400
    assert not any(value in response.text for value in query.values())


def test_selection_rejects_nonfinite_camera_and_deep_nesting() -> None:
    with pytest.raises(ValueError, match="finite"):
        SnapshotSelection.from_data(
            {
                "lens": "scene",
                "camera": {
                    "projection": "perspective",
                    "position": [math.nan, 0, 0],
                    "target": [0, 0, 0],
                },
            }
        )

    nested: object = "leaf"
    for _ in range(80):
        nested = {"next": nested}
    with pytest.raises(ValueError, match="nesting"):
        SnapshotSelection.from_data({"lens": "world", "layout": nested})


def test_inline_assets_reject_html_breakout_sequences() -> None:
    with pytest.raises(ValueError, match="closing script"):
        SnapshotAssets(script="</script><img src=x>", style="body{}")
    with pytest.raises(ValueError, match="closing style"):
        SnapshotAssets(script="void 0", style="</style><script>alert(1)</script>")


def test_globe_geometry_rejects_malformed_and_nonfinite_coordinates() -> None:
    with pytest.raises(ValueError, match="FeatureCollection"):
        validate_globe_geometry({"type": "Polygon", "coordinates": []})
    with pytest.raises(ValueError, match="finite"):
        validate_globe_geometry(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[math.inf, 0], [0, 0], [0, 1]]],
                        },
                        "properties": {},
                    }
                ],
            }
        )
