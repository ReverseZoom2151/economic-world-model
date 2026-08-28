# Test organization by evidence intent

Tests are grouped by what they establish, not only by the source module they touch:

| Directory | Evidence intent |
|---|---|
| `unit/` | Local records, algorithms, and component contracts |
| `integration/` | Cross-component public workflows, artifacts, replay, and source traceability |
| `conformance/` | Paper-level requirements and claim-boundary enforcement |
| `scenarios/` | Economy-specific mechanics and source targets |
| `properties/` | Invariants over generated inputs and state transitions |
| `ontology/` | Graph models, schemas, profiles, bundles, and compilation |
| `oracles/` | Package-import-free numerical checks |
| `packaging/` | Release metadata, mutation, and distribution gates |
| `documentation/` | Current documentation contracts and recursive structural integrity |

## Evidence intent and path stability

Paths under `conformance/`, `oracles/`, `properties/`, `scenarios/`, and selected integration tests
are named in machine-readable evidence registries. Move them only as an atomic traceability
migration that updates registries, provenance strings, automation, and documentation together.
