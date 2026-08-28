# EWM Ontology Research Workbench Implementation Plan

> **Execution requirement:** Use the `executing-plans` skill to implement this plan task by task on
> `main`. Do not create a worktree or feature branch. Stop after a failing verification, preserve the
> failure evidence, and fix it before advancing.

**Goal:** Implement the approved local-first EWM ontology research workbench, deterministic 3D
ontology scene, evidence-aware economic globe, and portable static investigation export without
changing the semantics or authority of the existing economic engine and sealed run bundles.

**Architecture:** Verified `ewm.run.v2` artifacts are projected through versioned scenario adapters
into an immutable `ewm.ontology.v1` graph and coverage ledger. A read-only query layer feeds either a
secured loopback FastAPI service or a deterministic `ewm.investigation.v1` snapshot. One React client
uses the same contracts for both data sources. Existing lower packages never depend on ontology or
workbench code.

**Technology:** Python 3.11+, frozen dataclasses, existing EWM canonical serialization, FastAPI and
Uvicorn as optional dependencies, React, TypeScript, Vite, Cytoscape.js, Vega-Lite, Three.js, React
Three Fiber, Drei, Vitest, Testing Library, axe, and Playwright.

**Authoritative design:**
[`docs/architecture/ontology-research-workbench.md`](../architecture/ontology-research-workbench.md)

## Working conventions

- Work directly on `main`, as requested by the maintainer.
- Begin every behavior change with a focused failing test.
- Run the focused test, implement the smallest complete behavior, then rerun the focused test.
- Run the relevant package suite before every commit.
- Keep every commit single-purpose and push it immediately with `git push origin main`.
- Preserve all existing tests, scientific classifications, sealed artifact contracts, and public
  APIs unless this plan names an additive change.
- Never write generated ontology content into a sealed run directory.
- Reuse `canonical_json` and `content_digest`; do not create another Python canonicalizer or hasher.
- Do not infer missing economic relations, geographic anchors, equilibrium status, or evidence.
- Do not include generated timestamps in artifact or snapshot identity.
- Keep all frontend runtime assets local and reproducibly built.

## Phase gates

| Gate | Tasks | Required evidence |
|---|---|---|
| Ontology foundation | 1-5 | Import boundaries, canonical records, fourteen invariants, deterministic projection bundle |
| Paper-faithful projection | 6-8 | Verified source mapping, all registered profiles, DDGE and claim-boundary conformance |
| Research query surface | 9-11 | Bounded queries, explicit comparison preflight, installed CLI smoke tests |
| Local workbench | 12-17 | Reproducible frontend, secured API, approved 2D workflows, accessibility |
| Spatial investigation | 18-19 | Deterministic 3D scene, explicit-only globe placement, WebGL fallback |
| Portable release | 20-22 | API/snapshot parity, offline operation, security/performance gates, documentation audit |

### Task 1: Enforce ontology and workbench dependency boundaries

**Files:**

- Modify: `tests/test_architecture.py`
- Create: `src/ewm/ontology/__init__.py`
- Create: `src/ewm/workbench/__init__.py`

**Step 1: Write the failing architecture test**

Extend `LAYER_IMPORTS` with these allowed prefixes:

```python
"ontology": (
    "ewm._version",
    "ewm.core",
    "ewm.equilibrium",
    "ewm.experiments",
    "ewm.ontology",
    "ewm.scenarios",
),
"workbench": ("ewm._version", "ewm.ontology", "ewm.workbench"),
```

Add an assertion that every named package layer exists. Existing lower-layer rules must continue to
reject imports of `ewm.ontology` and `ewm.workbench`.

**Step 2: Verify the failure**

Run:

```bash
python -m pytest tests/test_architecture.py -q
```

Expected: failure because the two package directories do not exist.

**Step 3: Add minimal packages**

Create package docstrings only. Do not export unstable objects yet.

**Step 4: Verify the boundary**

Run:

```bash
python -m pytest tests/test_architecture.py tests/test_package.py -q
ruff check src/ewm/ontology src/ewm/workbench tests/test_architecture.py
mypy src
```

Expected: all pass.

**Step 5: Commit and push**

```bash
git add tests/test_architecture.py src/ewm/ontology/__init__.py src/ewm/workbench/__init__.py
git commit -m "test: enforce ontology dependency boundaries"
git push origin main
```

### Task 2: Add immutable canonical ontology records

**Files:**

- Create: `src/ewm/ontology/model.py`
- Modify: `src/ewm/ontology/__init__.py`
- Create: `tests/ontology/test_model.py`

**Step 1: Specify the records**

Write tests for:

- `OntologyRef` validation and ordering;
- `SourceLocator` without absolute exported paths;
- deeply immutable properties;
- finite numeric values;
- `OntologyObject`, `RelationAssertion`, `Measurement`, `CoverageEntry`, and
  `OntologyProjection` construction;
- mutation attempts raising `TypeError` or `FrozenInstanceError`.

Use a small recursive payload to prove nested mappings and lists are frozen.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_model.py -q
```

Expected: import failure.

**Step 3: Implement the value objects**

Use frozen dataclasses, tuples, and read-only mappings. Reject booleans where a numeric measurement is
required, `NaN`, infinities, empty IDs, invalid layers, and absolute exported paths.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_model.py -q
ruff check src/ewm/ontology tests/ontology/test_model.py
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology tests/ontology/test_model.py
git commit -m "feat: add canonical ontology records"
git push origin main
```

### Task 3: Implement schema vocabulary and fourteen invariants

**Files:**

- Create: `src/ewm/ontology/schema.py`
- Create: `tests/ontology/test_schema.py`
- Create: `tests/properties/test_ontology_schema_properties.py`

**Step 1: Specify valid and invalid graphs**

Create one minimal valid graph and one focused failing fixture for each invariant in architecture
section 4.8. Include unresolved references, wrong relation direction, duplicate natural identity,
cross-layer conflation, collapsed correspondences, undocumented closure gaps, uncertified bounds,
conflated interventions, and unsupported claims.

Add Hypothesis properties for input ordering, duplicate insertion, and malformed canonical values.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_schema.py \
  tests/properties/test_ontology_schema_properties.py -q
```

**Step 3: Implement the registry and validator**

Define typed object specifications, relation specifications, cardinalities, layer assignments, and
cross-record validation. Return deterministic, structured violations ordered by invariant, object,
and source location. A projection with any error is unusable.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_schema.py \
  tests/properties/test_ontology_schema_properties.py -q
python -m pytest tests/conformance/test_claim_boundaries.py -q
ruff check src/ewm/ontology tests/ontology tests/properties/test_ontology_schema_properties.py
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology/schema.py tests/ontology/test_schema.py \
  tests/properties/test_ontology_schema_properties.py
git commit -m "feat: validate ontology schemas and invariants"
git push origin main
```

### Task 4: Add deterministic identities and canonical serialization

**Files:**

- Create: `src/ewm/ontology/identity.py`
- Create: `tests/ontology/test_identity.py`
- Create: `tests/properties/test_ontology_identity_properties.py`

**Step 1: Specify identity behavior**

Test that:

- labels do not affect identity;
- source and semantic keys do affect identity;
- order-independent collections yield the same digest;
- source record order remains significant where semantics require it;
- collisions fail closed;
- repeated serialization is byte-identical;
- the implementation delegates to `canonical_json` and `content_digest`.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_identity.py \
  tests/properties/test_ontology_identity_properties.py -q
```

**Step 3: Implement IDs and serializers**

Generate `ewm:{namespace}:{kind}:{digest}` IDs from canonical semantic payloads. Keep display prefixes
out of the digest. Provide explicit serialization methods for every record and reject unknown values.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_identity.py \
  tests/properties/test_ontology_identity_properties.py -q
python -m pytest tests/unit/test_artifact_identity.py -q
ruff check src/ewm/ontology tests/ontology tests/properties/test_ontology_identity_properties.py
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology/identity.py tests/ontology/test_identity.py \
  tests/properties/test_ontology_identity_properties.py
git commit -m "feat: add deterministic ontology identities"
git push origin main
```

### Task 5: Seal and verify derived ontology projection bundles

**Files:**

- Create: `src/ewm/ontology/verification.py`
- Create: `src/ewm/ontology/projection.py`
- Create: `tests/ontology/test_projection_bundle.py`
- Create: `tests/integration/test_projection_integrity.py`

**Step 1: Specify the bundle**

Tests must require exactly:

```text
manifest.json
projection.json
coverage.json
```

Specify `ewm.ontology.v1`, canonical bytes, payload sizes and digests, source run hash, adapter and
source digests, projection digest, atomic output, no wall-clock identity, rejection of extra files,
and rejection of modified or self-inconsistent payloads.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_projection_bundle.py \
  tests/integration/test_projection_integrity.py -q
```

**Step 3: Implement bundle writing and verification**

Write into a temporary sibling directory, fsync files where supported, verify the finished temporary
bundle, then rename it atomically. Never open the source run directory for writing.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_projection_bundle.py \
  tests/integration/test_projection_integrity.py -q
python -m pytest tests/integration/test_artifact_integrity.py -q
ruff check src/ewm/ontology tests/ontology tests/integration/test_projection_integrity.py
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology/verification.py src/ewm/ontology/projection.py \
  tests/ontology/test_projection_bundle.py tests/integration/test_projection_integrity.py
git commit -m "feat: seal ontology projection bundles"
git push origin main
```

### Task 6: Project only verified run bundles with a coverage ledger

**Files:**

- Create: `src/ewm/ontology/compiler.py`
- Create: `src/ewm/ontology/profiles/base.py`
- Create: `src/ewm/ontology/profiles/__init__.py`
- Create: `tests/ontology/test_compiler.py`
- Create: `tests/integration/test_run_projection.py`

**Step 1: Specify the projection pipeline**

Cover these states:

- valid sealed run and compatible adapter;
- tampered run;
- oversized payload, excessive event lines, and high-ratio or oversized NPZ members;
- legacy unsealed run;
- unknown experiment;
- known experiment with incompatible adapter version;
- supported runtime fields with unavailable declarations;
- adapter-derived declarations labeled and source-digested;
- every input field projected, deliberately omitted, or rejected.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_compiler.py tests/integration/test_run_projection.py -q
```

**Step 3: Implement the fail-closed compiler**

The compiler performs a read-only size and archive-expansion preflight, then calls the existing
artifact verifier. It selects an adapter by artifact and experiment identity, projects generic run,
payload, event, measurement, and provenance records, validates the whole graph, and only then
exposes or writes it.

Legacy input is rejected by default. An explicit diagnostic mode may inspect it but must not produce
a verified projection.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_compiler.py tests/integration/test_run_projection.py -q
python -m pytest tests/integration/test_artifact_integrity.py \
  tests/integration/test_conformance_source_verification.py -q
ruff check src/ewm/ontology tests/ontology tests/integration/test_run_projection.py
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology/compiler.py src/ewm/ontology/profiles \
  tests/ontology/test_compiler.py tests/integration/test_run_projection.py
git commit -m "feat: project verified run bundles"
git push origin main
```

### Task 7: Add scenario ontology profiles

**Files:**

- Create: `src/ewm/ontology/profiles/scalar.py`
- Create: `src/ewm/ontology/profiles/forecasting.py`
- Create: `src/ewm/ontology/profiles/fx.py`
- Create: `src/ewm/ontology/profiles/credit.py`
- Create: `src/ewm/ontology/profiles/production.py`
- Modify: `src/ewm/ontology/profiles/__init__.py`
- Create: `tests/ontology/profiles/test_scalar.py`
- Create: `tests/ontology/profiles/test_forecasting.py`
- Create: `tests/ontology/profiles/test_fx.py`
- Create: `tests/ontology/profiles/test_credit.py`
- Create: `tests/ontology/profiles/test_production.py`

**Step 1: Specify each adapter against real smoke artifacts**

Assert representative declaration, runtime, learning, equilibrium, evidence, and provenance objects
and relations for each profile. Test exact source locators and explicit omissions. Include FX
transactions and rejections, forecasting roots and learned coefficients, credit regimes and locked
diagnostics, production optimization and clearing, and scalar fixed-point records.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/profiles -q
```

**Step 3: Implement adapters without changing scenarios**

Adapters read public or stable internal records and code metadata. If the artifact lacks a semantic
field, record the gap. Do not modify `src/ewm/scenarios` or `src/ewm/experiments` to make the tests
easier in this task.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/profiles tests/scenarios -q
python scripts/scientific_stress.py --quick
ruff check src/ewm/ontology tests/ontology
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology/profiles tests/ontology/profiles
git commit -m "feat: add scenario ontology profiles"
git push origin main
```

### Task 8: Preserve DDGE, correspondence, capability, and evidence semantics

**Files:**

- Modify: `src/ewm/ontology/schema.py`
- Modify: `src/ewm/ontology/compiler.py`
- Modify: `src/ewm/ontology/profiles/scalar.py`
- Modify: `src/ewm/ontology/profiles/forecasting.py`
- Modify: `src/ewm/ontology/profiles/fx.py`
- Create: `tests/conformance/test_ontology_paper_semantics.py`
- Create: `tests/conformance/test_ontology_evidence_truthfulness.py`

**Step 1: Specify paper-semantic boundaries**

Test:

- separate rollout, inner-equilibrium, candidate, numerical-validation, and certification kinds;
- multiple candidates and selector metadata survive projection;
- behavior, data, learner, and redeployment form typed closure paths;
- residual vectors, norms, tolerances, solvers, and stopping rules survive projection;
- distance or welfare bounds require the existing certificate objects;
- Han higher-level readiness remains blocked and cannot be awarded by ontology naming;
- claim evidence classifications exactly match existing validated evidence.

**Step 2: Verify the failure**

```bash
python -m pytest tests/conformance/test_ontology_paper_semantics.py \
  tests/conformance/test_ontology_evidence_truthfulness.py -q
```

**Step 3: Implement semantic projection rules**

Map the existing correspondence, DDGE, theorem-certificate, capability, readiness, evaluation, claim,
and evidence records without broadening their status. Preserve missing and not-measured states.

**Step 4: Verify**

```bash
python -m pytest tests/conformance tests/ontology -q
python scripts/run_conformance.py
python scripts/scientific_stress.py --quick
ruff check src/ewm/ontology tests/conformance
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology tests/conformance/test_ontology_paper_semantics.py \
  tests/conformance/test_ontology_evidence_truthfulness.py
git commit -m "feat: project DDGE claims and evidence"
git push origin main
```

### Task 9: Build immutable indexes and bounded queries

**Files:**

- Create: `src/ewm/ontology/indexes.py`
- Create: `src/ewm/ontology/query.py`
- Create: `tests/ontology/test_indexes.py`
- Create: `tests/ontology/test_query.py`
- Create: `tests/properties/test_ontology_query_properties.py`

**Step 1: Specify query contracts**

Cover ID, type, layer, relation direction, run, episode, event sequence, time window, source locator,
measurement, claim, and evidence indexes. Require stable ordering, opaque cursors, limit caps, typed
path filters, maximum traversal depth, and structured cost-limit errors.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_indexes.py tests/ontology/test_query.py \
  tests/properties/test_ontology_query_properties.py -q
```

**Step 3: Implement immutable indexes and query service**

Build all indexes once from a validated projection. Return immutable pages and path results. Do not
return internal mutable mappings or permit unbounded collection reads.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_indexes.py tests/ontology/test_query.py \
  tests/properties/test_ontology_query_properties.py -q
ruff check src/ewm/ontology tests/ontology tests/properties/test_ontology_query_properties.py
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology/indexes.py src/ewm/ontology/query.py \
  tests/ontology/test_indexes.py tests/ontology/test_query.py \
  tests/properties/test_ontology_query_properties.py
git commit -m "feat: index and query ontology projections"
git push origin main
```

### Task 10: Compare only compatible economic runs

**Files:**

- Create: `src/ewm/ontology/comparison.py`
- Create: `tests/ontology/test_comparison.py`
- Create: `tests/integration/test_ontology_comparisons.py`

**Step 1: Specify comparison preflight**

Test compatible and incompatible world identities, protocols, seeds, interventions, estimands,
units, samples, estimators, software identities, and ontology schemas. Require exact rejection reasons
before aligned values are emitted. Preserve paired-seed and multiplicity metadata.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_comparison.py \
  tests/integration/test_ontology_comparisons.py -q
```

**Step 3: Implement comparison plans and results**

Produce a preflight report, deterministic alignment plan, aligned results, and unaligned records. Do
not align by display label or coerce units heuristically.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_comparison.py \
  tests/integration/test_ontology_comparisons.py tests/integration/test_comparisons.py -q
ruff check src/ewm/ontology tests/ontology tests/integration/test_ontology_comparisons.py
mypy src/ewm/ontology
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology/comparison.py tests/ontology/test_comparison.py \
  tests/integration/test_ontology_comparisons.py
git commit -m "feat: compare compatible economic runs"
git push origin main
```

### Task 11: Expose ontology CLI commands

**Files:**

- Modify: `src/ewm/cli.py`
- Modify: `src/ewm/ontology/__init__.py`
- Create: `tests/integration/test_ontology_cli.py`
- Modify: `tests/integration/test_installed_run_cli.py`

**Step 1: Specify commands and failures**

Add tests for:

```text
ewm ontology project
ewm ontology verify
```

Require JSON success and failure envelopes, nonzero exit codes, no writes on verification failure,
explicit output paths, and installed-wheel execution outside the source tree.

**Step 2: Verify the failure**

```bash
python -m pytest tests/integration/test_ontology_cli.py \
  tests/integration/test_installed_run_cli.py -q
```

**Step 3: Implement additive CLI groups**

Preserve current `list`, `describe`, `run`, `verify-run`, and `replay-run` behavior. Keep CLI parsing
thin and delegate to ontology services.

**Step 4: Verify**

```bash
python -m pytest tests/integration/test_ontology_cli.py \
  tests/integration/test_installed_run_cli.py tests/integration/test_run_cli.py -q
ruff check src/ewm/cli.py src/ewm/ontology tests/integration/test_ontology_cli.py
mypy src
```

**Step 5: Commit and push**

```bash
git add src/ewm/cli.py src/ewm/ontology/__init__.py \
  tests/integration/test_ontology_cli.py tests/integration/test_installed_run_cli.py
git commit -m "feat: expose ontology CLI commands"
git push origin main
```

### Task 12: Add a reproducible isolated frontend toolchain

**Files:**

- Modify: `.gitignore`
- Modify: `pyproject.toml`
- Create: `workbench/package.json`
- Create: `workbench/package-lock.json`
- Create: `workbench/tsconfig.json`
- Create: `workbench/vite.config.ts`
- Create: `workbench/vitest.config.ts`
- Create: `workbench/playwright.config.ts`
- Create: `workbench/index.html`
- Create: `workbench/src/main.tsx`
- Create: `workbench/src/styles.css`
- Create: `workbench/src/vite-env.d.ts`
- Create: `workbench/tests/smoke.test.tsx`
- Create: `scripts/check_frontend_build.py`
- Modify: `scripts/check_distribution.py`

**Step 1: Specify the build output**

Write Python tests or script tests that require a deterministic asset manifest and built client under
`src/ewm/workbench/static`. Extend distribution inspection to require those files once built.

**Step 2: Verify the failure**

```bash
python scripts/check_frontend_build.py
```

Expected: failure because no lockfile or built asset manifest exists.

**Step 3: Create and lock the toolchain**

Configure React, TypeScript, Vite, ESLint, Vitest, Testing Library, axe, Playwright, Cytoscape.js,
Vega-Lite, Three.js, React Three Fiber, and Drei. Set Vite output to the Python static package. Pin the
Node major version in project metadata and CI. Do not load runtime resources from a CDN.

Add a minimal client smoke test and make the reproducibility script build twice with a fixed
environment and compare asset bytes and manifest content.

**Step 4: Verify**

```bash
cd workbench
npm ci
npm run lint
npm run typecheck
npm test
npm run build
cd ..
python scripts/check_frontend_build.py
python -m build --outdir dist
python scripts/check_distribution.py dist
```

**Step 5: Commit and push**

```bash
git add .gitignore pyproject.toml workbench src/ewm/workbench/static \
  scripts/check_frontend_build.py scripts/check_distribution.py
git commit -m "build: add isolated workbench toolchain"
git push origin main
```

### Task 13: Serve versioned contracts through a secured loopback API

**Files:**

- Modify: `pyproject.toml`
- Create: `src/ewm/workbench/contracts.py`
- Create: `src/ewm/workbench/security.py`
- Create: `src/ewm/workbench/api.py`
- Create: `src/ewm/workbench/server.py`
- Create: `tests/workbench/test_contracts.py`
- Create: `tests/workbench/test_api.py`
- Create: `tests/workbench/test_security.py`
- Create: `workbench/scripts/generate-contracts.mjs`
- Create: `workbench/src/contracts/generated.ts`

**Step 1: Specify API and security behavior**

Test every endpoint in architecture section 9, pagination and cost limits, error envelopes, API minor
headers, idempotent comparisons and exports, loopback binding, host and origin rejection, disabled
CORS, token headers, no-store bootstrap, and token absence from URLs, cookies, Web Storage, and logs.

Test that API requests cannot select new filesystem paths.

**Step 2: Verify the failure**

```bash
python -m pytest tests/workbench/test_contracts.py tests/workbench/test_api.py \
  tests/workbench/test_security.py -q
```

**Step 3: Implement contracts, API, and launcher**

Add a `workbench` optional dependency extra for FastAPI and Uvicorn. Build the service from an
immutable approved-run registry and existing query services. Generate TypeScript contracts from the
checked OpenAPI document and require a clean generation diff.

**Step 4: Verify**

```bash
python -m pytest tests/workbench -q
cd workbench
npm run generate:contracts
git diff --exit-code -- src/contracts/generated.ts
npm run typecheck
cd ..
ruff check src/ewm/workbench tests/workbench
mypy src
```

**Step 5: Commit and push**

```bash
git add pyproject.toml src/ewm/workbench tests/workbench \
  workbench/scripts/generate-contracts.mjs workbench/src/contracts/generated.ts
git commit -m "feat: serve the secured local ontology API"
git push origin main
```

### Task 14: Add shared data sources and the investigation shell

**Files:**

- Create: `workbench/src/data/InvestigationDataSource.ts`
- Create: `workbench/src/data/ApiDataSource.ts`
- Create: `workbench/src/state/investigation.tsx`
- Create: `workbench/src/components/AppShell.tsx`
- Create: `workbench/src/components/ObjectExplorer.tsx`
- Create: `workbench/src/components/EvidenceInspector.tsx`
- Create: `workbench/src/components/Timeline.tsx`
- Create: `workbench/src/components/LensRouter.tsx`
- Create: `workbench/src/testing/fixtures.ts`
- Create: `workbench/tests/data-source.test.ts`
- Create: `workbench/tests/investigation-state.test.tsx`
- Create: `workbench/tests/app-shell.test.tsx`

**Step 1: Specify synchronized state**

Test run, object, relation, time-window, comparison, lens, camera, and filter selection. Ensure URL
state contains identifiers and view state but never the session token. Test loading, empty, partial,
unsupported, and failed-integrity states.

**Step 2: Verify the failure**

```bash
cd workbench
npm test -- data-source.test.ts investigation-state.test.tsx app-shell.test.tsx
```

**Step 3: Implement the shell**

Use one typed reducer and context boundary for synchronized investigation state. Keep scientific data
inside data-source responses, not duplicated in visual components. Use real DOM controls for the
explorer, timeline, inspector, and lens navigation.

**Step 4: Verify**

```bash
cd workbench
npm run lint
npm run typecheck
npm test
npm run build
```

**Step 5: Commit and push**

```bash
git add workbench/src workbench/tests
git commit -m "feat: add workbench data sources and shell"
git push origin main
```

### Task 15: Visualize declared worlds and runtime episodes

**Files:**

- Create: `workbench/src/lenses/WorldLens.tsx`
- Create: `workbench/src/lenses/RuntimeLens.tsx`
- Create: `workbench/src/lenses/MarketLens.tsx`
- Create: `workbench/src/visuals/SemanticGraph.tsx`
- Create: `workbench/src/visuals/StateActionFlow.tsx`
- Create: `workbench/src/visuals/MarketCharts.tsx`
- Create: `workbench/src/visuals/visualGrammar.ts`
- Create: `workbench/tests/world-lens.test.tsx`
- Create: `workbench/tests/runtime-lens.test.tsx`
- Create: `workbench/tests/market-lens.test.tsx`

**Step 1: Specify scientific encodings**

Test stable semantic layouts, typed legends, source labels, units, uncertainty, selection sync,
progressive expansion, event brushing, market rejections, and sparse-data fallbacks. Prove repeated
input yields identical layout coordinates.

**Step 2: Verify the failure**

```bash
cd workbench
npm test -- world-lens.test.tsx runtime-lens.test.tsx market-lens.test.tsx
```

**Step 3: Implement the first three lenses**

Use Cytoscape only through `SemanticGraph`. Use Vega-Lite only through typed chart builders that
require units, sample metadata, uncertainty, and source. Do not initialize a random force layout.

**Step 4: Verify**

```bash
cd workbench
npm run lint
npm run typecheck
npm test
npm run build
```

**Step 5: Commit and push**

```bash
git add workbench/src/lenses workbench/src/visuals workbench/tests
git commit -m "feat: visualize worlds and runtime episodes"
git push origin main
```

### Task 16: Visualize learning closure and DDGE diagnostics

**Files:**

- Create: `workbench/src/lenses/LearningLens.tsx`
- Create: `workbench/src/lenses/DdgeLens.tsx`
- Create: `workbench/src/visuals/LearningClosure.tsx`
- Create: `workbench/src/visuals/ResidualHistory.tsx`
- Create: `workbench/src/visuals/CandidateBasins.tsx`
- Create: `workbench/src/visuals/CertificatePanel.tsx`
- Create: `workbench/tests/learning-lens.test.tsx`
- Create: `workbench/tests/ddge-lens.test.tsx`

**Step 1: Specify semantic truthfulness**

Test closure gaps, dataset membership, training and deployment identity, multiple candidates, scalar
and vector residuals, norms, tolerances, solver status, basins, stability, certificate assumptions,
and the four result statuses. Test that an uncertified small residual cannot render a bound.

**Step 2: Verify the failure**

```bash
cd workbench
npm test -- learning-lens.test.tsx ddge-lens.test.tsx
```

**Step 3: Implement the learning and DDGE lenses**

Use exact ontology kinds rather than frontend heuristics. Preserve unavailable stages and do not
select a preferred fixed point without displaying selector metadata.

**Step 4: Verify**

```bash
cd workbench
npm run lint
npm run typecheck
npm test
npm run build
```

**Step 5: Commit and push**

```bash
git add workbench/src/lenses workbench/src/visuals workbench/tests
git commit -m "feat: visualize learning loops and DDGE"
git push origin main
```

### Task 17: Add comparison, evidence, and lineage lenses

**Files:**

- Create: `workbench/src/lenses/CompareLens.tsx`
- Create: `workbench/src/lenses/EvidenceLens.tsx`
- Create: `workbench/src/lenses/LineageLens.tsx`
- Create: `workbench/src/visuals/ComparisonPreflight.tsx`
- Create: `workbench/src/visuals/ClaimAudit.tsx`
- Create: `workbench/src/visuals/LineagePath.tsx`
- Create: `workbench/tests/compare-lens.test.tsx`
- Create: `workbench/tests/evidence-lens.test.tsx`
- Create: `workbench/tests/lineage-lens.test.tsx`

**Step 1: Specify rejected and accepted comparisons**

Test explicit incompatibility reports, paired sample metadata, claim to evidence traversal, source
locators, limitation display, source redaction, unsupported states, and missing source files.

**Step 2: Verify the failure**

```bash
cd workbench
npm test -- compare-lens.test.tsx evidence-lens.test.tsx lineage-lens.test.tsx
```

**Step 3: Implement the three lenses**

Render preflight before aligned results. Keep claim status in text and redundant shape encoding.
Lineage paths must preserve relation direction and source identity.

**Step 4: Verify**

```bash
cd workbench
npm run lint
npm run typecheck
npm test
npm run build
```

**Step 5: Commit and push**

```bash
git add workbench/src/lenses workbench/src/visuals workbench/tests
git commit -m "feat: add comparison evidence and lineage lenses"
git push origin main
```

### Task 18: Add the deterministic 3D ontology scene

**Files:**

- Create: `workbench/src/lenses/SceneLens.tsx`
- Create: `workbench/src/scene/layout.ts`
- Create: `workbench/src/scene/OntologyScene.tsx`
- Create: `workbench/src/scene/InstancedNodes.tsx`
- Create: `workbench/src/scene/RelationLines.tsx`
- Create: `workbench/src/scene/SceneControls.tsx`
- Create: `workbench/src/scene/WebGLFallback.tsx`
- Create: `workbench/tests/scene-layout.test.ts`
- Create: `workbench/tests/scene-interaction.test.tsx`
- Create: `workbench/e2e/scene.spec.ts`

**Step 1: Specify semantic coordinates and fallback**

Test X semantic lanes, Y ontology layers, Z time or version, stable placement, serialized camera
state, perspective and orthographic modes, selection sync, layer isolation, focus and reset,
progressive limits, reduced motion, and no-WebGL fallback.

**Step 2: Verify the failure**

```bash
cd workbench
npm test -- scene-layout.test.ts scene-interaction.test.tsx
```

**Step 3: Implement the scene**

Use `Canvas` with `frameloop="demand"`, capped DPR, instanced node geometry, shared materials,
batched lines, selective raycasting, and explicit invalidation from controls. Do not use random
placement, continuous idle animation, glow, or depth as an undeclared quantity.

**Step 4: Verify**

```bash
cd workbench
npm run lint
npm run typecheck
npm test
npm run build
npx playwright test e2e/scene.spec.ts
```

**Step 5: Commit and push**

```bash
git add workbench/src/lenses/SceneLens.tsx workbench/src/scene workbench/tests \
  workbench/e2e/scene.spec.ts
git commit -m "feat: add deterministic 3D ontology scene"
git push origin main
```

### Task 19: Add the evidence-aware economic globe

**Files:**

- Modify: `src/ewm/ontology/model.py`
- Modify: `src/ewm/ontology/schema.py`
- Modify: `src/ewm/ontology/query.py`
- Create: `src/ewm/ontology/geo.py`
- Modify: `src/ewm/cli.py`
- Create: `tests/ontology/test_geo_anchor.py`
- Create: `tests/integration/test_geo_overlay_cli.py`
- Create: `workbench/src/lenses/GlobeLens.tsx`
- Create: `workbench/src/globe/geometry.ts`
- Create: `workbench/src/globe/EconomicGlobe.tsx`
- Create: `workbench/src/globe/AnchoredObjects.tsx`
- Create: `workbench/src/globe/FlowArcs.tsx`
- Create: `workbench/src/globe/GlobeLegend.tsx`
- Create: `workbench/src/assets/natural-earth-110m.json`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `workbench/tests/globe.test.tsx`
- Create: `workbench/e2e/globe.spec.ts`

**Step 1: Specify explicit geography**

Test coordinate reference systems, validity intervals, declared versus observed anchors, source
locators, rejection of invalid coordinates, and the rule that no object without `GEO_ANCHORED_AT`
appears on the globe. Specify canonical `ewm.geo-overlay.v1` parsing, overlay digests in projection
identity, `researcher_declared` classification, rejection of unknown identities or missing sources,
and the `--geo-overlay` CLI input. Test nonspatial unavailable states and comparison overlays.

Record the official Natural Earth source, public-domain status, version, and asset digest before
adding the simplified geometry.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_geo_anchor.py \
  tests/integration/test_geo_overlay_cli.py -q
cd workbench
npm test -- globe.test.tsx
```

**Step 3: Implement the geo extension and globe**

Keep anchor projection optional. Read sidecars only from CLI-approved paths, keep them outside sealed
runs, and retain their evidence status in every projected anchor. Render bundled geometry, instanced
markers, bounded flow arcs, timeline filtering, uncertainty, selection sync, and explicit legend
encodings. Make no tile, font, telemetry, or data request.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_geo_anchor.py \
  tests/integration/test_geo_overlay_cli.py -q
cd workbench
npm run lint
npm run typecheck
npm test
npm run build
npx playwright test e2e/globe.spec.ts
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology src/ewm/cli.py tests/ontology/test_geo_anchor.py \
  tests/integration/test_geo_overlay_cli.py workbench/src/lenses/GlobeLens.tsx \
  workbench/src/globe workbench/src/assets workbench/tests workbench/e2e/globe.spec.ts \
  THIRD_PARTY_NOTICES.md
git commit -m "feat: add evidence aware economic globe"
git push origin main
```

### Task 20: Compile and verify portable offline investigations

**Files:**

- Create: `src/ewm/ontology/snapshot.py`
- Create: `src/ewm/workbench/export.py`
- Modify: `src/ewm/cli.py`
- Create: `workbench/src/data/SnapshotDataSource.ts`
- Create: `workbench/src/snapshot/bootstrap.ts`
- Create: `tests/ontology/test_snapshot.py`
- Create: `tests/workbench/test_snapshot_export.py`
- Create: `tests/integration/test_snapshot_cli.py`
- Create: `workbench/tests/snapshot-data-source.test.ts`
- Create: `workbench/e2e/offline-snapshot.spec.ts`

**Step 1: Specify `ewm.investigation.v1`**

Test canonical selection, data limits, source and projection digests, serialized 2D and 3D view
state, bundled globe geometry only when selected, CSP hashes, no remote references, deterministic
bytes, corruption detection, separately comparable file digest, and the stated absence of digital
signature authenticity.

Test semantic parity between `ApiDataSource` and `SnapshotDataSource` for all query contracts.

**Step 2: Verify the failure**

```bash
python -m pytest tests/ontology/test_snapshot.py tests/workbench/test_snapshot_export.py \
  tests/integration/test_snapshot_cli.py -q
cd workbench
npm test -- snapshot-data-source.test.ts
```

**Step 3: Implement export, verification, and offline bootstrap**

Embed canonical base64 data as non-executable content, inline the reproducibly built assets, apply
fixed CSP hashes, verify with Web Crypto before rendering, and expose `snapshot export` and
`snapshot verify` CLI commands. Refuse oversized exports with a structured reduction diagnostic.

**Step 4: Verify**

```bash
python -m pytest tests/ontology/test_snapshot.py tests/workbench/test_snapshot_export.py \
  tests/integration/test_snapshot_cli.py -q
cd workbench
npm run lint
npm run typecheck
npm test
npm run build
npx playwright test e2e/offline-snapshot.spec.ts --project=chromium
npx playwright test e2e/offline-snapshot.spec.ts --project=firefox
```

**Step 5: Commit and push**

```bash
git add src/ewm/ontology/snapshot.py src/ewm/workbench/export.py src/ewm/cli.py \
  workbench/src/data/SnapshotDataSource.ts workbench/src/snapshot tests/ontology/test_snapshot.py \
  tests/workbench/test_snapshot_export.py tests/integration/test_snapshot_cli.py \
  workbench/tests/snapshot-data-source.test.ts workbench/e2e/offline-snapshot.spec.ts
git commit -m "feat: compile verifiable offline snapshots"
git push origin main
```

### Task 21: Enforce end-to-end quality, security, and performance gates

**Files:**

- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/security.yml`
- Modify: `scripts/benchmark_experiments.py`
- Create: `scripts/benchmark_workbench.py`
- Create: `scripts/check_workbench_network.py`
- Create: `tests/workbench/test_adversarial_inputs.py`
- Create: `tests/integration/test_workbench_benchmark.py`
- Create: `workbench/e2e/investigation-workflows.spec.ts`
- Create: `workbench/e2e/accessibility.spec.ts`
- Create: `workbench/e2e/security.spec.ts`
- Create: `workbench/e2e/visual.spec.ts`

**Step 1: Specify release-gate failures**

Add deterministic small, medium, and large fixture generators. Test percentile and peak-memory report
schema, projection and query budgets, 3D frame measurements, snapshot limits, script labels, path
traversal, host/origin/token attacks, nesting and size bombs, non-finite numbers, malformed geometry,
remote request attempts, keyboard workflows, reduced motion, and WebGL fallback.

**Step 2: Verify focused failures**

```bash
python -m pytest tests/workbench/test_adversarial_inputs.py \
  tests/integration/test_workbench_benchmark.py -q
cd workbench
npx playwright test e2e/investigation-workflows.spec.ts e2e/accessibility.spec.ts \
  e2e/security.spec.ts
```

**Step 3: Implement gates and CI jobs**

Extend current CI rather than creating a duplicate pipeline. Add Node setup with dependency caching,
lint, typecheck, tests, production build, generated-contract diff, rebuilt-asset diff, offline E2E,
and network checks. Add locked JavaScript dependency auditing to the security workflow. Keep medium
performance benchmarks scheduled and pre-release; use bounded smoke fixtures on pull requests.

**Step 4: Run the complete local release gate**

```bash
ruff check .
mypy src
coverage run -m pytest -q
coverage report
python scripts/run_conformance.py
python scripts/scientific_stress.py --quick
python scripts/benchmark_workbench.py --tier small
python scripts/check_reproducible_build.py
python scripts/check_frontend_build.py
python scripts/check_workbench_network.py
cd workbench
npm ci
npm run lint
npm run typecheck
npm test
npm run build
npx playwright test
npm audit --audit-level=high
```

Expected: all functional, scientific, security, accessibility, and reproducibility gates pass.
Performance reports must distinguish measured targets from non-blocking large-tier characterization.

**Step 5: Commit and push**

```bash
git add .github/workflows scripts tests/workbench/test_adversarial_inputs.py \
  tests/integration/test_workbench_benchmark.py workbench/e2e
git commit -m "test: harden ontology workbench release gates"
git push origin main
```

### Task 22: Publish researcher documentation and complete the release audit

**Files:**

- Modify: `README.md`
- Modify: `docs/experiments.md`
- Modify: `docs/limitations.md`
- Modify: `docs/paper-traceability.md`
- Modify: `docs/replication.md`
- Create: `docs/ontology.md`
- Create: `docs/workbench.md`
- Create: `docs/snapshots.md`
- Create: `docs/ontology-extension-guide.md`
- Create: `docs/workbench-release-audit.md`
- Modify: `tests/documentation/test_public_documentation.py`
- Modify: `CHANGELOG.md`

**Step 1: Specify public documentation claims**

Extend documentation tests to require:

- both paper links and current claim boundaries;
- ontology and workbench links;
- verified-run requirement;
- six ontology layers and fourteen invariants;
- DDGE status distinctions;
- 3D semantic-axis and explicit-geo rules;
- snapshot corruption versus authenticity distinction;
- optional dependencies and offline behavior;
- current limits, unsupported cases, and performance reference environment.

**Step 2: Verify the failure**

```bash
python -m pytest tests/documentation/test_public_documentation.py -q
```

**Step 3: Write and cross-link the guides**

Document installation, CLI, all eight workflows, API, snapshot sharing, profile extension, scientific
interpretation, 3D controls, globe eligibility, security, and troubleshooting. Render mathematical
expressions with GitHub-supported display math. Do not use em dashes, inflated claims, or vague
marketing language.

Build `docs/workbench-release-audit.md` as a requirement-by-requirement evidence matrix. For each
architecture completion criterion, name the exact test, command output, generated artifact, or file
that proves it. Mark missing evidence as incomplete and continue implementation.

**Step 4: Run the final audit**

```bash
python -m pytest tests/documentation/test_public_documentation.py -q
python -m pytest -q
python scripts/run_conformance.py
python scripts/scientific_stress.py --quick
python scripts/check_reproducible_build.py
python scripts/check_frontend_build.py
python -m build --outdir dist
python scripts/check_distribution.py dist
cd workbench
npm ci
npm run lint
npm run typecheck
npm test
npm run build
npx playwright test
```

Inspect the built wheel outside the repository and open a generated snapshot with networking
disabled in Chromium and Firefox. Do not declare completion from a narrower smoke check.

**Step 5: Commit and push**

```bash
git add README.md CHANGELOG.md docs tests/documentation/test_public_documentation.py
git commit -m "docs: publish ontology workbench researcher guide"
git push origin main
```

## Final implementation completion check

Before tagging a release, prove every item below from current-state evidence:

- all 22 task commits exist on `main` and `origin/main`;
- the existing engine and sealed artifact contracts have not acquired ontology dependencies;
- projection integrity and all fourteen invariants fail closed under corruption;
- every registered scenario profile projects a verified smoke run;
- paper-semantic and evidence-truthfulness conformance passes;
- all API collections are bounded and API/snapshot data sources agree;
- all eight investigation workflows pass end to end;
- 3D placement is deterministic and non-WebGL fallback works;
- the globe renders no object without an explicit sourced `GeoAnchor`;
- an offline snapshot works with networking disabled in Chromium and Firefox;
- security, accessibility, performance, packaging, and reproducibility gates pass;
- public documentation preserves every current limitation and claim boundary.

If any evidence is missing, indirect, stale, or narrower than the requirement, the implementation is
not complete.
