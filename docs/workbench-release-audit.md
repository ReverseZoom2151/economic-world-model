# Ontology workbench release audit

**Document version:** 1.0  
**Audit date:** 2026-08-29  
**Release line:** 0.2.0 development head  
**Result:** Pass for the declared local, read-only research scope

## Requirement-by-requirement evidence

This matrix names current executable evidence for every completion criterion in the approved
[implementation plan](plans/2026-08-28-ontology-workbench-implementation.md). A passing row proves
the stated software contract. It does not establish empirical economic validity, a general theorem,
or a Han capability beyond the evidence gates documented elsewhere.

| Requirement | Status | Current evidence |
|---|---|---|
| All 22 tasks are present on `main` and `origin/main` | Pass | `git log --oneline origin/main` contains the task commits from `test: enforce ontology dependency boundaries` through `docs: publish ontology workbench researcher guide`; local and remote heads are compared after the final push. |
| Existing engine and sealed run authority have no ontology dependency | Pass | `tests/test_architecture.py` and `tests/integration/runtime/test_package_structure_contracts.py` enforce package direction, acyclic imports, package ownership, and the `ewm.run.v2` authority. |
| Projection integrity and fourteen invariants fail closed | Pass | `tests/ontology/graph/test_schema.py` has a valid fixture and one focused failure for each invariant; `tests/integration/ontology/test_projection_integrity.py` covers modified, malformed, resealed, and digest-substitution attacks. |
| Every registered profile projects a verified smoke run | Pass | `tests/ontology/profiles/test_scalar.py`, `test_forecasting.py`, `test_fx.py`, `test_credit.py`, and `test_production.py`; `tests/integration/ontology/test_run_projection.py` checks publication and verification. |
| DDGE and paper evidence semantics remain truthful | Pass | `tests/conformance/test_ontology_paper_semantics.py`, `tests/conformance/test_ontology_evidence_truthfulness.py`, and `tests/conformance/test_evidence_truthfulness.py` preserve candidate, validation, certificate, capability, and empirical-validity boundaries. |
| API collections are bounded and API and snapshot data sources agree | Pass | `tests/ontology/query/test_service.py`, `tests/workbench/http/test_api.py`, `workbench/tests/data-source.test.ts`, and `workbench/tests/snapshot/snapshot-data-source.test.ts` cover caps, cursors, envelopes, and shared source behavior. |
| Eight investigation workflows execute across the CLI, API, and browser | Pass | `workbench/e2e/investigation-workflows.spec.ts` covers verified-run opening and the investigation entry points; the per-lens unit suites test bounded data behavior; `tests/integration/ontology/test_snapshot_cli.py` and `workbench/e2e/offline-snapshot.spec.ts` cover export, verification, and offline opening. |
| 3D placement is deterministic and a non-WebGL fallback exists | Pass | `workbench/tests/scene-layout.test.ts`, `workbench/tests/scene-interaction.test.tsx`, and `workbench/e2e/scene.spec.ts` cover semantic coordinates, camera controls, budgets, selection, frame demand, and fallback. |
| Globe placement requires explicit sourced geography | Pass | `tests/ontology/geography/test_geo_anchor.py`, `tests/integration/ontology/test_geo_overlay_cli.py`, `workbench/tests/globe.test.tsx`, and `workbench/e2e/globe.spec.ts` reject inferred geography and validate explicit anchors. |
| Portable snapshots work without networking in Chromium and Firefox | Pass | `tests/ontology/snapshot/test_contract.py`, `tests/workbench/snapshot/test_export.py`, `tests/integration/ontology/test_snapshot_cli.py`, and `workbench/e2e/offline-snapshot.spec.ts` cover deterministic export, verification, corruption refusal, and offline browser use. |
| Local transport and snapshot inputs resist declared attacks | Pass | `tests/workbench/http/test_security.py`, `tests/workbench/security/test_adversarial_inputs.py`, and `workbench/e2e/security.spec.ts` cover host, origin, token, path, secret, body, nesting, HTML-breakout, GeoJSON, persistence, and remote-resource cases. |
| Keyboard, reduced-motion, and serious accessibility checks pass | Pass | `workbench/e2e/accessibility.spec.ts` uses axe, keyboard traversal, focus checks, and reduced-motion media emulation; each 3D workflow retains an ordinary DOM or 2D fallback. |
| Bounded performance evidence has environment and percentile metadata | Pass | `scripts/benchmark_workbench.py` emits `ewm.workbench-benchmark.v1`; `tests/integration/workbench/test_benchmark.py` checks fixture identity, sample size, percentiles, peak memory, and targets classified as targets rather than claims. |
| Python and frontend builds are reproducible and distributable | Pass | `scripts/check_reproducible_build.py`, `scripts/check_frontend_build.py`, `scripts/check_distribution.py`, `tests/integration/experiments/test_installed_run_cli.py`, and the wheel inspection outside the repository cover byte identity, included assets, imports, and installed CLI execution. |
| Public claims retain source and limitation boundaries | Pass | `tests/documentation/test_public_documentation.py`, [Paper traceability](paper-traceability.md), [Replication](replication.md), [Ontology](ontology.md), [Snapshots](snapshots.md), and [Limitations](limitations.md) enforce the two paper links and current claim boundary. |

## Final local command ledger

The release audit uses the repository virtual environment for Python commands and a locked npm
install for browser commands:

```bash
.venv/bin/python -m pytest tests/documentation/test_public_documentation.py -q
.venv/bin/python -m pytest -q
.venv/bin/python scripts/run_conformance.py
.venv/bin/python scripts/scientific_stress.py --quick
.venv/bin/python scripts/check_reproducible_build.py
.venv/bin/python scripts/check_frontend_build.py
.venv/bin/python -m build --outdir dist
.venv/bin/python scripts/check_distribution.py dist

cd workbench
npm ci
npm run lint
npm run typecheck
npm test
npm run build
npx playwright test
```

Additional gates used by CI are:

```bash
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/python -m pytest tests/test_architecture.py \
  tests/integration/runtime/test_package_structure_contracts.py -q
.venv/bin/python scripts/check_workbench_network.py
.venv/bin/python scripts/benchmark_workbench.py --tier small --repeats 3
npm audit --omit=dev --audit-level=high
```

`scripts/check_frontend_build.py` performs two clean frontend builds and compares both with the
committed wheel assets. The Python reproducibility check builds twice in isolated temporary
directories. Distribution inspection validates included resources and metadata. The installed-wheel
test creates an isolated environment outside the checkout and validates public imports and CLIs.

Recorded outcomes on the audit environment:

| Gate | Result |
|---|---|
| Full Python suite | 723 passed |
| Paper conformance suite | 82 passed; L2 synthetic systems conformance; 16 higher-level readiness requirements remain blocked and non-awarding |
| Strict source verification | Both supplied PDFs matched registered SHA-256 hashes and page counts |
| Scientific stress, quick mode | All seven declared checks passed |
| Ruff | All checks passed |
| Mypy | No issues in 166 source files |
| Frontend unit suite | 50 tests in 17 files passed |
| Playwright | 28 tests passed across Chromium and Firefox |
| npm production audit | Zero vulnerabilities reported |
| Reproducible builds | Two Python distributions and two frontend builds matched byte for byte |
| Distribution inspection | Wheel and source archive validated; installed-wheel CLI test passed outside the checkout |

## Browser evidence

The Playwright project runs the same suite in Chromium and Firefox. The snapshot case blocks every
network route after loading the local file, verifies the selected projection and lens, and confirms
that a corrupted payload refuses to render. The scene cases inspect deterministic semantic
coordinates and capture the rendered frame; the globe cases test both explicit placement and the
unavailable state.

Visual checks are regression evidence for layout and rendering behavior. They are not perceptual or
scientific validation of a chart.

## Performance observation

The recorded small-tier observation used WSL2 Linux 5.15, x86_64, Python 3.12.3, 64 reported CPUs,
the `fx.rollout` smoke fixture at seed 73, 242 objects, 335 relations, and 6 measurements. Three
repeats produced these p95 observations:

| Operation | p95 elapsed | Maximum traced Python memory |
|---|---:|---:|
| Projection | 0.850 s | 20.9 MB |
| Bounded 200-object query | 0.000382 s | 13.5 kB |
| Standalone snapshot export | 2.398 s | 54.9 MB |

These measurements describe one local environment and a small fixture. The script labels the
interactive-open and 3D-frame budgets as release targets because this benchmark does not measure
them. Medium and large tiers run on scheduled or manual CI; no service-level objective is claimed.

## Evidence boundaries

The audit establishes that the implementation follows the declared ontology, transport,
visualization, security, packaging, and documentation contracts. It does not show that synthetic
agents match human behavior, that a DDGE is unique, that residuals imply welfare accuracy, that a
globe location is true beyond its cited source, or that the system is safe for policy or commercial
decisions.

The source PDFs are ignored and are not available to ordinary CI. `scripts/run_conformance.py`
records absent PDFs as `not_present`. A strict source audit requires locally supplied bytes and
`--require-sources`; the expected hashes alone do not prove that the sources were observed.

For this local audit, `scripts/verify_sources.py --require-all` observed both supplied PDFs and
matched their registered SHA-256 hashes and page counts. The files remain ignored and are not part of
the repository or distribution.
