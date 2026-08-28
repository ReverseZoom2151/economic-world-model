# Ontology guide

**Document version:** 1.0  
**Last reviewed:** 2026-08-29  
**Scope:** Canonical read-only projections derived from verified EWM runs

The ontology reconstructs the economic and evidentiary structure of a run without changing the run
or its mechanism. Projection accepts a verified `ewm.run.v2` bundle and a compatible, source-digested
scenario profile. A legacy, malformed, tampered, unsupported, or oversized bundle cannot produce a
projection.

This layer is package engineering informed by [Cong's EWM and DDGE
formalism](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6559940) and [Han et al.'s systems
blueprint](https://arxiv.org/abs/2608.06020v1). It does not add empirical validity, theorem proofs,
or capability awards to the source run.

## Project and verify

Install the package, create a run, and write a derived projection outside the sealed run directory:

```bash
python -m pip install -e .
ewm run fx.rollout --preset smoke --seed 42 --output runs
ewm ontology project --run-dir runs/<run_hash> --output projections/fx-smoke
ewm ontology verify --bundle projections/fx-smoke
```

`ontology project` verifies the source bundle before it creates output. `ontology verify` checks the
projection manifest, canonical payload bytes, payload sizes and digests, projection identity,
adapter identity, and source identity. Both commands emit stable JSON and return nonzero on failure.

An optional geography sidecar can be supplied during projection:

```bash
ewm ontology project \
  --run-dir runs/<run_hash> \
  --output projections/fx-with-geo \
  --geo-overlay overlays/fx.geo.json
```

The sidecar remains outside the sealed run and becomes part of the derived projection identity. See
[Globe eligibility](workbench.md#globe-eligibility) for the geographic rules.

## Six layers

Each object belongs to one of six layers. A relation may connect layers only when its registered
direction and endpoint kinds allow it.

| Layer | Question | Examples |
|---|---|---|
| Schema | Which vocabulary and constraints apply? | Object type, relation type, profile, invariant |
| Economic declaration | Which economy was specified? | World, agent, market, mechanism, learner, intervention |
| Runtime occurrence | Which events occurred in this execution? | Run, step, state, action, transaction, outcome, generated datum |
| Learning and equilibrium | Which updates and closure assessments exist? | Dataset, training run, parameter version, DDGE candidate, residual, certificate |
| Research and evidence | Which measurements and claims were recorded? | Experiment, protocol, estimand, measurement, evidence, limitation |
| Provenance | Which source authorizes each assertion? | Projection, source locator, derivation, software identity, digest, paper anchor |

## Fourteen invariants

The schema compiler enforces these fourteen invariants and rejects the complete projection if any
one fails:

1. Every stored record has a unique stable identity.
2. Every reference resolves inside the projection or through a declared external source.
3. Every relation has an allowed direction, endpoint kind, and cardinality.
4. Every assertion has a source locator, and runtime assertions trace to a verified run.
5. Every object belongs to exactly one ontology layer.
6. Declarations and runtime occurrences remain separate and connect through `INSTANTIATES`.
7. Sealed run content remains immutable; a projection or snapshot is a derived artifact.
8. Rollouts, inner equilibria, fixed-point candidates, DDGE candidates, numerical validations, and
   certified results remain distinct kinds.
9. Set-valued correspondences retain every observed candidate and selector metadata.
10. Behavior, generated data, learning, and deployment use typed stages. An absent stage requires a
    coverage entry.
11. A residual retains its value, norm, tolerance, solver, stopping rule, and status.
12. A residual supports a distance or welfare bound only through a linked certificate with the
    required assumptions.
13. Declared interventions, realized interventions, and observed outcomes remain separate.
14. Every claim links to authorizing evidence and retains its source evidence classification.

Validation failures are structured and sorted by invariant number, record identity, and source
location. Order of input records cannot change the result.

## Identity and provenance

Canonical identities use the form:

```text
ewm:{namespace}:{kind}:{digest}
```

The digest includes stable source identity and semantic keys. A display label does not affect it.
Runtime identities include the verified run and source record selector. Profile-derived declarations
include the profile identity and source digest. The compiler reuses the package's canonical JSON and
SHA-256 functions, so the ontology does not create a second identity system.

A `SourceLocator` may point to a checksummed run payload and selector, an adapter code symbol, a
protocol artifact, or a paper anchor. Exported paths are relative and portable. A source locator
records origin; it does not prove the truth of the source assertion.

## Projection coverage

Every supported source field receives one coverage disposition:

| Status | Meaning |
|---|---|
| `projected` | One or more ontology records preserve the field. |
| `omitted` | The profile chose not to project the field and records a reason. |
| `rejected` | The field conflicts with the profile or schema and records a reason. |
| `unavailable` | The source lacks the semantic information required to construct the record. |

`unavailable` is evidence of a gap, not a zero value. Adapter-derived declarations carry
`evidence_origin=adapter_derived`; they are not presented as run-authored evidence.

## DDGE interpretation

The ontology preserves the inner correspondence:

$$
E_i(\theta)
=
\lbrace(\pi,\mu)\mid(\pi,\mu)
\text{ satisfy the declared inner conditions under }(\theta,i)\rbrace.
$$

Generated data and learning induce the outer map:

$$
F_i(\theta)=L_i\!\left(D_i\!\left(E_i(\theta),\theta\right)\right),
\qquad
\theta^{\star}\in F_i(\theta^{\star}).
$$

The fixed-point expression is set-valued when the inner solution is a correspondence. A selector is
stored only when the evidence declares one.

DDGE records keep four status distinctions:

| Status | Supported reading |
|---|---|
| `observed` | A source artifact records the value or execution. |
| `candidate` | A solver or declared construction proposes a possible fixed point. |
| `numerically validated` | Declared residual and tolerance checks pass for the recorded candidate. |
| `certified` | A linked theorem certificate verifies its stated assumptions and conclusion. |

A numerically validated candidate is not a certified existence, uniqueness, stability, welfare, or
empirical result. Multiplicity, initialization, selector, basin, damping, and residual metadata
remain visible when the source provides them.

## Profiles

Release 0.2.0 registers profiles for scalar DDGE, forecasting, FX, credit, and production runs. Each
profile declares compatible experiment IDs, package versions, artifact schemas, and a source digest.
Unknown experiment or package versions fail closed. The profile cannot read unverified paths or
write into the sealed run.

Use the [profile extension guide](ontology-extension-guide.md) to add a scenario. New profiles must
preserve the six layers, all fourteen invariants, source classifications, and coverage gaps.

## Read-only queries

`OntologyQueryService` builds immutable indexes for identity, type, layer, relations, runtime
context, source location, measurements, claims, and evidence. Collection reads use stable ordering,
bounded page sizes, opaque cursors, typed filters, and bounded path depth. Cursors bind to their
projection and filter, so they cannot be reused against different evidence.

The service does not expose a graph database or mutation operation. Scientific comparisons require
matching world, protocol, software, estimand, unit, sample, and estimator identities. Labels are
never used as alignment keys.

## Failure diagnosis

| Failure | Check |
|---|---|
| Source run fails verification | Run `ewm verify-run` and inspect the reported payload. |
| Profile is incompatible | Check experiment, package version, artifact schema, and installed profile. |
| Projection validation fails | Read the structured invariant number and record identity. |
| Projection output already differs | Select a new path; publication treats mismatched existing output as a collision. |
| Coverage contains gaps | Read each status and reason before drawing a claim. |
| Geo overlay fails | Check target identity, source metadata, coordinates, duplicates, and validity interval. |

The [workbench guide](workbench.md) describes the investigation interface. The [snapshot guide](snapshots.md)
describes bounded offline sharing.
