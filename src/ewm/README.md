# Package map

`ewm` is organized around stable economic and evidence domains:

| Package | Ownership |
|---|---|
| `core/` | Shared domain declarations, runtime, assurance, and provenance primitives |
| `equilibrium/` | Inner equilibrium, DDGE, fixed points, damping, certificates, and diagnostics |
| `capabilities/` | Han L3-L6 cognition, evolution, institutions, alignment, and evidence gates |
| `conformance/` | Installable paper-level report construction and evidence orchestration |
| `scenarios/` | Economy-owned models, presets, agents, mechanisms, and validation protocols |
| `experiments/` | Experiment execution, artifacts, analysis, studies, and discovery |
| `ontology/` | Immutable graph records, schema validation, bundles, compilation, and profiles |
| `workbench/` | Read-only investigation services and portable exports |
| `protocols/` | Installed scientific protocol resources with stable paths |

Within experiments, `experiments/catalog/` owns discovery, `experiments/runs/` owns the sealed run
lifecycle, `experiments/analysis/` owns measurements and claim boundaries, `experiments/labs/` owns
economy-specific studies, `experiments/studies/` owns locked protocols, and
`experiments/assurance/` verifies external sources. The historical `ewm.experiments.registry`
module retains executor functions whose module names are embedded in ontology provenance.

Within core, `core/domain/` owns economic declarations and records, `core/runtime/` owns world
execution, `core/assurance/` owns coherence and evidence checks, and `core/provenance/` owns
contracts, serialization, randomness, and replay. Historical direct module imports are aliases to
these single implementation modules. Type-only declarations keep the locked Han v1 sources
byte-stable while making those legacy imports visible to static analysis.

Within equilibrium, `equilibrium/solvers/` owns inner-equilibrium, fixed-point, damping, and DDGE
execution. `equilibrium/analysis/` owns certificates, set-valued correspondences, and diagnostics.

Within ontology, `ontology/graph/` owns immutable records, identities, vocabulary, and invariants.
`ontology/projection/` owns compilation, publication, bundle identity, and verification.
`ontology/profiles/` retains stable adapter class paths because their module-qualified names
contribute to projection identity.

The evidence-bound files under `capabilities/` and `scenarios/fx/` remain in place for the Han v1
protocols. Moving them requires an explicit v2 evidence migration, not an ordinary refactor.
