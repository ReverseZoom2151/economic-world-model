# Documentation map

The documentation is organized by purpose. Current public guides stay at stable paths in this
directory; design records and historical execution plans have their own collections.

## Guides

| Guide | Purpose |
|---|---|
| [Experiments](experiments.md) | Run registry, artifacts, verification, replay, and metrics |
| [Replication](replication.md) | Locked sources, numerical targets, tolerances, and exact commands |
| [Limitations](limitations.md) | Scientific, empirical, numerical, and deployment boundaries |
| [Product validation](product-validation.md) | Current audit plus explicitly labeled historical audits |

## Mathematical and paper reference

| Reference | Purpose |
|---|---|
| [Mathematical contract](mathematical-contract.md) | Formal objects, equations, and theorem obligations |
| [Paper traceability](paper-traceability.md) | Source identity, claim classes, and evidence gates |
| [Paper implementation matrix](paper-implementation-matrix.md) | Requirement-level implementation status for both papers |
| [Capability matrix](capability-matrix.md) | Han L1-L6 evidence gates and the independent DDGE axis |

## Research

| Study | Purpose |
|---|---|
| [Ontology repository study](ontology-repository-study.md) | External repository patterns, provenance, verification, and licensing |

## Architecture

The [`architecture/`](architecture/) directory contains approved system boundaries, dependency
maps, and design audits. These documents describe intended ownership and invariants; tests and code
remain authoritative for current behavior.

## Plans

The [`plans/`](plans/) directory contains dated execution plans. Plans are historical records as well
as active checklists, so old version numbers and superseded paths may appear there intentionally.
