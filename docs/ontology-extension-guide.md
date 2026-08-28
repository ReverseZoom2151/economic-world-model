# Ontology profile extension guide

**Document version:** 1.0  
**Last reviewed:** 2026-08-29  
**Audience:** Researchers adding a scenario-specific projection

An ontology profile maps a known sealed run schema into canonical, sourced records. It does not
execute the economy, alter a run, infer missing primitives, or redefine the shared vocabulary.

## Profile contract

Implement `OntologyProfile` from
`ewm.ontology.profiles.contracts.base`. A profile declares:

```python
class ExampleOntologyProfile:
    identity = "example.ontology-profile.v1"
    experiment_ids = frozenset({"example.rollout"})
    package_versions = frozenset({"0.2.0"})
    artifact_schemas = frozenset({"ewm.run.v2"})
    source_digest = content_digest(
        {
            "profile": identity,
            "mapping_version": 1,
            "sources": ("ewm.scenarios.example.model.ExampleWorld",),
        }
    )

    def project(self, context: OntologyProfileContext) -> ProfileProjection:
        ...
```

The profile identity names the semantic mapping. Change its version when the mapping meaning or
output contract changes. The source digest binds the identity to the exact mapping version and code
symbols. Compatibility lists are allowlists; unknown versions fail closed.

## Source boundary

`OntologyProfileContext` contains immutable data from a source bundle that passed preflight and
`ewm.run.v2` verification:

- manifest, configuration, metrics, events, and trace arrays;
- exact payload digests;
- source run and adapter locators;
- experiment, scenario, preset, seed, package version, and artifact schema.

Use `artifact_source(context, filename, selector=...)` for records obtained from a payload. It
rejects filenames absent from the verified manifest and attaches the exact payload digest. Use the
adapter locator for declarations whose semantics come from installed scenario code. Do not open
paths from the profile or attach an absolute workstation path.

## Build records

`ProfileBuilder` creates deterministic identities and maintains sourced immutable records:

```python
builder = ProfileBuilder(
    context,
    profile_identity=self.identity,
    source_digest=self.source_digest,
)

world = builder.declaration(
    "world",
    {"scenario": "example"},
    {"scenario": "example", "world_kind": "declared_example"},
)

outcome = builder.object(
    "outcome",
    "runtime_occurrence",
    {"sequence": 12},
    {"sequence": 12, "outcome_kind": "market_price"},
    sources=(artifact_source(context, "events.jsonl", selector="sequence=12"),),
)

builder.relation(
    "REALIZES",
    mechanism_invocation,
    outcome,
    {"sequence": 12},
    locator=artifact_source(context, "events.jsonl", selector="sequence=12"),
)
```

Use declarations for economic objects supplied by scenario code and runtime objects for observed run
records. The builder labels declarations `adapter_derived` and includes the profile identity.

## Layer and relation choices

Choose one of the six layers defined in the [ontology guide](ontology.md#six-layers). Reuse the
registered object and relation kinds in `ewm.ontology.graph.schema`. Relation direction is
authoritative. Store one directed relation and let query code display an inverse when needed.

Do not collapse:

- a declaration into its runtime occurrence;
- an inner equilibrium into a DDGE candidate;
- a numerical validation into a certificate;
- a declared intervention into its realization or outcome;
- an evidence artifact into the claim it supports;
- multiple candidates in a correspondence into one selected point.

If the shared vocabulary cannot express the scenario, propose a canonical schema change with its
invariants and cross-profile tests. A private relation string inside one profile is rejected.

## Measurements and evidence

Every measurement needs a subject, name, finite canonical value or null, unit, status, sample
metadata, uncertainty metadata, and source locator. Preserve source terminology and units. Do not
coerce units or manufacture uncertainty.

A claim object retains its original `evidence_classification`. It requires a matching sourced
evidence artifact linked through `SUPPORTS`. A residual-based distance or welfare claim also requires
the appropriate certificate. Profile code cannot upgrade `qualitative-reconstruction` or
`paper-inspired` evidence to exact replication.

## Coverage ledger

Every supported source field must be either projected or represented by one explicit gap:

```python
builder.projected(
    "events.sequence=12.market_price",
    outcome,
    source=artifact_source(context, "events.jsonl", selector="sequence=12"),
)

builder.gap(
    "config.parameters.welfare_bound",
    "unavailable",
    "the run contains no certified sensitivity constant",
)
```

The coverage ledger accepts `projected`, `omitted`, `rejected`, and `unavailable`. A projected entry
needs a target. Every other status needs a reason. Never represent an absent field with zero, an
empty label, or an invented default.

The compiler checks that profile coverage plus generic coverage accounts for the exact source-field
inventory. Duplicates, missing fields, and unsupported targets fail projection.

## Registration

Place the implementation under `src/ewm/ontology/profiles/scenarios/` and its tests under
`tests/ontology/profiles/`. Export one immutable instance from the profile module and add it to
`DEFAULT_PROFILES` in `src/ewm/ontology/profiles/__init__.py` only after compatibility and
conformance tests pass.

Registration order must not affect projection bytes. A run must match exactly one compatible
profile. Zero or multiple matches fail closed.

## Required tests

Add focused tests for:

1. exact compatibility selection and rejection of unknown versions;
2. deterministic profile and projection digests;
3. every declaration's `adapter_derived` origin and source digest;
4. exact payload selectors and digests for run-derived records;
5. complete coverage ledger accounting;
6. scenario-specific economic invariants and preserved evidence classifications;
7. projection validation against all fourteen invariants;
8. a verified smoke run projected end to end;
9. tampered, legacy, oversized, and malformed source failure;
10. package import, formatting, typing, and distribution checks.

Useful commands are:

```bash
python -m pytest tests/ontology/profiles/test_example.py -q
python -m pytest tests/ontology/graph tests/ontology/projection -q
python -m pytest tests/conformance/test_ontology_paper_semantics.py \
  tests/conformance/test_ontology_evidence_truthfulness.py -q
ruff check src/ewm/ontology tests/ontology
mypy src
python scripts/check_distribution.py dist
```

## Review checklist

- The profile maps observed fields and code-derived declarations without changing the economic
  runtime.
- Identities use semantic keys, source identity, profile identity, and source digest.
- Every record and relation has an exact source locator.
- The coverage ledger includes every supported source field and every scientific gap.
- DDGE roles, multiplicity, selector metadata, residuals, and certificate status remain distinct.
- Claims retain the evidence boundary already declared by the experiment.
- Unknown experiments, package versions, and artifact schemas fail before profile execution.
- No output is written inside the sealed source run.

Run the complete release audit in [workbench-release-audit.md](workbench-release-audit.md) before
publishing a profile as part of a release.
