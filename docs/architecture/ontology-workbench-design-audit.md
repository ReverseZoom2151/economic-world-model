# Ontology Workbench Design Audit

Date: 2026-08-28  
Scope: architecture and implementation planning only  
Result: complete for design; implementation has not started

## Audit method

This audit derives requirements from the approved planning goal and checks each one against the new
architecture, the task-level plan, and the current repository. A design requirement passes only when
the architecture fixes the decision and the implementation plan names files, tests, commands, and a
completion gate. Current code evidence is used to detect contradictions and unsupported assumptions,
not to claim that planned work exists.

Authoritative design artifacts:

- [`ontology-research-workbench.md`](ontology-research-workbench.md)
- [`2026-08-28-ontology-workbench-implementation.md`](../plans/2026-08-28-ontology-workbench-implementation.md)

Current repository evidence:

- `src/ewm/core`, `src/ewm/equilibrium`, `src/ewm/scenarios`, and `src/ewm/experiments`;
- `tests/test_architecture.py`;
- `src/ewm/experiments/runs/verification.py` and `src/ewm/experiments/runs/identity.py`;
- `src/ewm/core/provenance/serialization.py`;
- `docs/mathematical-contract.md`, `docs/paper-traceability.md`, `docs/replication.md`,
  `docs/capability-matrix.md`, and `docs/limitations.md`;
- `references/papers.toml` and `references/conformance.toml`;
- `.github/workflows/ci.yml`, `.github/workflows/security.yml`,
  `scripts/benchmark_experiments.py`, and `scripts/scientific_stress.py`.

## Requirement matrix

| Requirement | Architecture evidence | Plan evidence | Current-state check | Result |
|---|---|---|---|---|
| Local-first solo-researcher product | Sections 1 and 3 | Goal, architecture, Tasks 13-22 | No current server or frontend exists | Design complete; implementation pending |
| Portable static snapshot | Sections 8.1, 10, and 11 | Task 20 | No snapshot format exists | Design complete; implementation pending |
| Preserve economic engine | Sections 1 and 8.3 | Tasks 1 and 6 | Existing dependency test defines lower layers | Pass |
| Preserve sealed artifact authority | Sections 3.3, 4.8, 8.5, and 12 | Tasks 5, 6, and 20 | `ARTIFACT_SCHEMA` is `ewm.run.v2`; verifier is read-only | Pass |
| Cong economic and DDGE semantics | Sections 2, 4, and 5 | Tasks 7 and 8 | Correspondence, candidate, consistency, and certificate types exist | Pass |
| Han runtime and capability semantics | Sections 2 and 5.4 | Task 8 | Capability levels and evidence gates exist; current award is L2 | Pass |
| Formal ontology | Section 4 | Tasks 2-8 | No ontology package exists | Design complete; implementation pending |
| Investigation workflows | Section 6 | Tasks 14-22 | Current CLI has no investigation client | Design complete; implementation pending |
| Palantir-style workspace | Sections 7.1-7.4 | Tasks 14-17 | No client exists | Design complete; implementation pending |
| Deterministic 3D graph | Sections 7.5 and 14 | Task 18 | No WebGL dependency exists | Design complete; implementation pending |
| Economic globe | Sections 4.7 and 7.6 | Task 19 | Current scenarios contain no geographic identifiers | Pass with explicit geo-overlay contract |
| API and query contracts | Sections 8.6 and 9 | Tasks 9, 10, and 13 | Current public API only runs and describes experiments | Design complete; implementation pending |
| Portable data-source parity | Sections 9.4 and 10 | Task 20 | No frontend data source exists | Design complete; implementation pending |
| Scientific validation | Sections 5 and 12 | Tasks 7, 8, and 21 | Existing conformance and independent oracles provide the base | Pass |
| Security boundaries | Sections 10, 11, and 13 | Tasks 6, 13, 20, and 21 | Existing verifier has no byte or decompression caps | Pass after bounded-preflight correction |
| Measurable performance | Section 14 | Task 21 | Existing benchmark reports p50, p95, p99, and peak RSS | Pass |
| Complete test strategy | Section 15 | Every task starts with a failing test; Task 21 adds E2E | Existing suite covers Python only | Design complete; implementation pending |
| Feature priority | Section 16 | Phase-gate table | No competing workbench roadmap exists | Pass |
| Phased implementation | Section 17 | Twenty-two ordered tasks | Existing plans cover the economic prototype, not this feature | Pass |
| Granular commits on `main` | Section 17 | Every task ends with one commit and push | Repository is on `main`; prior history is granular | Pass |
| No duplicate infrastructure | Sections 8, 12, and 15.4 | Tasks extend current verifier, CI, benchmark, and stress suite | Current machinery identified by exact path | Pass |
| No mandatory agent SDK or Mesa | Sections 3.3, 8.1, and 18 | Technology list omits them | Current package has no such dependency | Pass |
| Honest current limitations | Sections 2, 12, 18, and 19 | Tasks 8 and 22 | Current limitation and traceability documents agree | Pass |

## Paper-fidelity audit

### Cong

The design preserves these distinctions:

- the inner object is a correspondence and may be empty or set-valued;
- policy and belief witnesses remain distinct from the deployed parameter;
- generated data and the learner are typed stages in the outer closure;
- a rollout is not an inner equilibrium;
- a fixed-point candidate is not a certified DDGE;
- numerical residuals retain solver, norm, tolerance, and stopping metadata;
- distance and welfare bounds require the corresponding certificate and assumptions;
- multiplicity, selection, initialization, and basin evidence remain visible;
- Laboratory I, Laboratory II, Laboratory III, and Appendix D keep their separate replication
  classifications.

Evidence in the current repository includes `src/ewm/equilibrium/analysis/correspondence.py`,
`src/ewm/equilibrium/solvers/ddge.py`, `src/ewm/equilibrium/analysis/diagnostics.py`,
`src/ewm/equilibrium/analysis/certificates.py`, `src/ewm/core/domain/records.py`, and the Cong
conformance tests.

### Han et al.

The design preserves these distinctions:

- interface availability is separate from observed capability evidence;
- the L1-L6 ladder is cumulative;
- DDGE consistency and empirical validity are separate axes;
- fixture execution cannot satisfy higher evidence classes;
- controlled co-evolution events remain different from institutional or alignment outcomes;
- current L3-L6 results remain blocked readiness observations;
- the ontology cannot award a capability because a class or relation has the right name.

Evidence in the current repository includes `src/ewm/core/provenance/contracts.py`,
`src/ewm/core/runtime/coevolution.py`, `src/ewm/capabilities/levels.py`,
`src/ewm/capabilities/readiness.py`, `src/ewm/scenarios/fx/validation.py`, and the Han conformance
tests.

## Repository contradiction audit

### Existing verifier limits

The first design draft described oversized bundles as an existing verifier failure. Inspection of
`src/ewm/experiments/runs/verification.py` contradicted that wording. The verifier checks exact
filenames,
regular files, hashes, JSON structure, finite numbers, event sequence, NPZ entry names, and object
dtype. It does not cap file size, event count, uncompressed NPZ size, or archive expansion ratio.

The architecture now places a bounded read-only preflight before the existing verifier. Task 6 names
the required adversarial tests. This addition does not change `ewm.run.v2`.

### Geographic evidence

Searches across the FX and production scenarios found no country, jurisdiction, coordinate, or
geographic identifier. Mapping their abstract objects to real locations would fabricate semantics.
The approved globe now accepts an optional `ewm.geo-overlay.v1` sidecar with explicit sources and a
`researcher_declared` status. The overlay contributes to projection identity and remains separate
from the run.

### Snapshot authenticity

An embedded digest detects partial or accidental corruption. A person who can rewrite the HTML can
also rewrite its verifier and digest. The architecture now states that authenticity requires an
expected digest obtained through another channel. V1 makes no digital-signature claim.

### Artifact-derived declarations

Some economic declarations live in installed scenario code rather than run payloads. The design
labels those records `adapter_derived`, records adapter and source digests, and exposes coverage gaps.
A matching version string alone does not turn current code into run-authored evidence.

### Replay coverage

Current deterministic `replay-run` support covers sealed FX rollout artifacts only. The design does
not require replay as a prerequisite for other profiles. It requires integrity verification and
marks unavailable runtime reconstruction in coverage.

## Architecture consistency

The dependency graph is acyclic:

```text
core, equilibrium, scenarios, experiments
                    |
                    v
                ontology
                    |
                    v
                workbench
                    |
                    v
                   CLI
```

The design has one canonical serializer, one sealed run verifier, one projection schema, one query
model, one frontend data-source interface, and one set of CI gates. The static viewer changes the
transport, not the economic or evidentiary semantics.

## Scope audit

The plan includes all V1 requirements approved during section review:

- canonical ontology plus scalar, forecasting, FX, credit, and production profiles;
- verified projection, coverage, immutable indexes, queries, comparisons, API, and CLI;
- World, Runtime, Market, Learning, DDGE, Compare, Evidence, and Lineage lenses;
- deterministic 3D ontology scene and explicit-anchor globe;
- portable, deterministic, offline snapshots;
- scientific, security, accessibility, performance, packaging, and reproducibility gates;
- researcher, snapshot, and profile-extension documentation.

Deferred work remains outside V1: cloud services, collaboration, live remote data, graph databases,
ontology authoring UI, automatic LLM claims, RDF storage, and an agent SDK requirement.

## Editorial audit

The two design artifacts contain no em dashes, smart quotes, Unicode arrows, placeholders, invented
performance results, or claims that implementation exists. The implementation plan names exact
paths and focused commands. Each task has a failing-test step, an implementation step, a verification
step, one commit, and one push.

## Audit conclusion

The architecture and implementation plan cover every requirement in the planning goal. The audit
found and corrected three material issues: verifier size assumptions, globe usefulness without
geographic data, and snapshot-authenticity wording. No planning requirement remains unresolved.

This result authorizes implementation. It does not claim that the ontology, workbench, 3D scene,
globe, API, or snapshot compiler already exists.
