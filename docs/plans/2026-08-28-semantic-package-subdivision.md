# Semantic package subdivision plan

**Status:** active
**Branch:** `main`
**Baseline:** 582 tests passing; Ruff clean; mypy clean

## Objective

Replace the remaining large flat Python directories with cohesive subpackages while preserving
public aggregate exports, historical direct imports, numerical behavior, scientific claim
boundaries, and traceability.

## Target boundaries

```text
ewm/
  core/
    domain/       declarations, records, specifications, protocols, agents, mechanisms
    runtime/      compilation, world execution, transitions, events, interventions
    assurance/    coherence, evaluation, evidence, reconciliation
    provenance/   contracts, canonical serialization, randomness, replay
  equilibrium/
    solvers/      inner equilibrium, fixed points, damping, DDGE
    analysis/     certificates, correspondences, diagnostics
  experiments/
    catalog/      scenario adapters and catalog assembly
    runs/         identities, artifacts, execution, replay, verification
    analysis/     metrics, statistics, evaluation, and claim authorization
    labs/         credit, FX, and production study implementations
    studies/      locked protocols and their command adapter
    assurance/    paper-source verification
  ontology/
    graph/        immutable records, identities, and schema validation
    projection/   compilation, sealing, bundle identity, and verification
    profiles/     provenance-stable scenario adapters
```

## Compatibility and evidence rules

- Keep one implementation file per concern. Historical module paths resolve through module aliases,
  not facade files that duplicate the directory clutter.
- Preserve `ewm`, `ewm.core`, `ewm.equilibrium`, and `ewm.experiments` aggregate exports.
- Preserve the historical `ewm.core.world.World` module identity used by serialized consumers.
- Keep `ewm.experiments.registry` at its existing path because profile provenance records its
  executor symbols.
- Keep Han v1 capability files and the FX validation source set at their existing paths. Moving
  either set requires a new evidence protocol version.
- Update every conformance implementation path in the same commit as its source move.
- Treat changed source fingerprints as expected provenance and unchanged numerical results as the
  behavioral requirement.

## Sequence

1. Add structure contracts and one shared internal module-alias utility.
2. Subdivide `core` and update its traceability paths.
3. Subdivide `equilibrium` and update its traceability paths.
4. Subdivide `experiments`, retaining the provenance-bound registry entry point.
5. Subdivide ontology records and projection services while preserving profile module identities.
6. Refresh ownership maps, run strict source verification, full paper conformance, scientific
   stress, tests, lint, types, distribution, and reproducibility gates.
