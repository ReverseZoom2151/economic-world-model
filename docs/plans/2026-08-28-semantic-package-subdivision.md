# Semantic package subdivision plan

**Status:** complete
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

## Outcome

Completed on 2026-08-28.

- `core` now separates domain, runtime, assurance, and provenance concerns.
- `equilibrium` now separates solvers from analysis and certification.
- `experiments` now separates catalog discovery, run lifecycle, analysis, laboratories, locked
  studies, and source assurance. The provenance-bound registry remains the only loose implementation
  module.
- `ontology` now separates canonical graph semantics from projection compilation, bundle identity,
  publication, and verification. Scenario profile module identities remain stable.
- Historical direct imports resolve to the single canonical module object. No compatibility facade
  duplicates implementation logic.
- Six type-only core declarations preserve static analysis for byte-locked Han v1 imports without
  leaving loose implementation modules.
- Unit and integration tests are grouped by evidence domain. Four Han v1 provenance tests remain at
  their locked historical locations.
- Current traceability registries, commands, workflows, mutation configuration, documentation, and
  installed entry points reference the new canonical paths.

Final verification: 594 tests passed, Ruff passed, mypy passed, 82 strict conformance evidence tests
passed, both paper sources verified, all quick scientific stress checks passed, wheel and source
distribution contents validated, and repeated 0.2.0 builds were byte-identical.
