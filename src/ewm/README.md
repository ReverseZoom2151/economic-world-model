# Package map

`ewm` is organized around stable economic and evidence domains:

| Package | Ownership |
|---|---|
| `core/` | Shared declarations, records, economic runtime, coherence, and provenance primitives |
| `equilibrium/` | Inner equilibrium, DDGE, fixed points, damping, certificates, and diagnostics |
| `capabilities/` | Han L3-L6 cognition, evolution, institutions, alignment, and evidence gates |
| `scenarios/` | Economy-owned models, presets, agents, mechanisms, and validation protocols |
| `experiments/` | Experiment execution, artifacts, analysis, studies, and discovery |
| `ontology/` | Immutable graph records, schema validation, bundles, compilation, and profiles |
| `workbench/` | Read-only investigation services and portable exports |
| `protocols/` | Installed scientific protocol resources with stable paths |

Within experiments, `experiments/catalog/` owns catalog models, scenario adapters, and default
assembly. The historical `ewm.experiments.registry` module retains executor functions whose module
names are embedded in ontology provenance.

Within ontology, `ontology/bundles/` owns identity shared by publication and verification. This
keeps the module import graph acyclic. `ontology/profiles/` retains stable adapter class paths because
their module-qualified names contribute to projection identity.

The evidence-bound files under `capabilities/` and `scenarios/fx/` remain in place for the Han v1
protocols. Moving them requires an explicit v2 evidence migration, not an ordinary refactor.
