# Showcase geography declaration

The repository showcase uses five researcher-declared coordinates solely to exercise the Economic
Globe renderer against a real, verified FX simulation. They are illustrative presentation anchors,
not observations, jurisdiction claims, calibration data, or assertions about where the abstract
agents and mechanisms exist.

| FX declaration | Latitude | Longitude | Uncertainty |
|---|---:|---:|---:|
| Spot FX market | 40.7128 | -74.0060 | 250 km |
| Bank agent | 51.5072 | -0.1276 | 250 km |
| Firm agent | 1.3521 | 103.8198 | 250 km |
| Household population | 35.6762 | 139.6503 | 250 km |
| Adaptive trend learner | 50.1109 | 8.6821 | 250 km |

The derived `ewm.geo-overlay.v1` sidecar records `anchor_basis=declared` and
`source_kind=researcher_declaration`. The sealed run remains unchanged. The workbench displays these
anchors as researcher-declared evidence and retains their source digest and uncertainty.
