# Paper-Faithful EWM Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Turn the package into a comprehensive, auditable adaptation of Cong's EWM/DDGE
framework and Han et al.'s systems blueprint, with exact replication claims only where the published
source fixes enough of the model to support them.

**Architecture:** Keep the dependency direction `core -> equilibrium/scenarios -> experiments ->
public API`. Add paper-neutral primitives to `core`, mathematical DDGE objects and diagnostics to
`equilibrium`, exact or explicitly package-authored laboratories to `scenarios`, and evidence reports
to `experiments`. Han's agent, environment, co-evolution, alignment, and evaluation interfaces stay
provider-neutral; capability levels are awarded by machine-checkable evidence gates rather than by
the presence of class names.

**Tech Stack:** Python 3.11+, NumPy, SciPy, pandas, scikit-learn, stdlib `tomllib`, pytest,
Hypothesis, Ruff, mypy, coverage, GitHub Actions.

---

## Source and claim policy

- Locked source A: Lin William Cong, *Economic World Models and Data-Driven Generative
  Equilibria*, current draft April 2026, 72 pages, SHA-256
  `c5ed935e09b5b0a607f0523d6be293ba4de1707bc242083ad1cd5a5937820357`.
- Locked source B: Han et al., *From Economic Agents to Agentic Economies: A Systems Blueprint
  for Economic World Models*, arXiv:2608.06020v1, 6 August 2026, 44 pages, SHA-256
  `918e51bc34b102a4d51c5a55528cdd90ca78576df2bc1955dee31e65c051c8e6`.
- Both PDFs passed a page-structure preflight. They remain local and ignored; the repository stores
  only bibliographic metadata, hashes, public links, and page/section anchors.
- `exact-replication` means equations, parameters, and target quantities are fixed by the locked
  source and independently reproduced. `conformance` means a protocol or invariant is implemented.
  `paper-inspired` means this package supplies a mechanism or parameter absent from the paper.
- Cong says Laboratory I has accompanying replication code, but the locked PDF contains no code
  URL and omits parameters needed for an exact numerical reconstruction. Until public author code is
  located, its existing credit laboratory remains a disclosed qualitative reconstruction, not an
  exact replication.
- Han is a systems blueprint, not a numerical model. Its architecture is tested for protocol
  conformance. L3 through L6 capability claims require runtime evidence; interface availability alone
  never awards a capability level.

## Verification policy

Every formal numerical claim gets at least two independent checks where possible:

1. a direct formula, analytical identity, or theorem-derived bound;
2. an independent numerical route such as bracketing, finite differences, exhaustive small-case
   enumeration, seeded simulation, or property testing.

Tests distinguish proof obligations, deterministic numerical verification, stochastic evidence, and
empirical validation. Passing synthetic tests cannot establish real-world validity.

### Task 1: Lock sources and make traceability executable

**Files:**

- Create: `references/papers.toml`
- Create: `references/conformance.toml`
- Create: `docs/paper-traceability.md`
- Create: `tests/integration/test_paper_traceability.py`
- Modify: `README.md`

**Step 1: Write failing registry tests**

Test unique source IDs, exact hashes, valid statuses, existing implementation/test paths, required
claim labels, and full coverage of the paper sections and equations declared in the registry.

**Step 2: Run the focused test and confirm failure**

Run: `python -m pytest tests/integration/test_paper_traceability.py -q`

**Step 3: Add source and conformance registries**

Record every Cong definition/result/laboratory and every Han equation, capability level, component,
runtime interface, and evaluation layer. Each item carries source pages, status, claim type,
implementation paths, evidence paths, and a limitation when incomplete.

**Step 4: Document how to read the registry**

Add a concise traceability guide and link it from the README.

**Step 5: Verify and commit**

Run: `python -m pytest tests/integration/test_paper_traceability.py -q`

Commit: `docs: lock paper sources and add conformance registry`

### Task 2: Implement Cong's full formal object contract

**Files:**

- Create: `src/ewm/core/definition.py`
- Create: `tests/unit/test_definition.py`
- Modify: `src/ewm/core/__init__.py`
- Modify: `docs/mathematical-contract.md`
- Modify: `references/conformance.toml`

**Step 1: Write failing tests**

Cover Definition 2.6's exact blocks, agent-count consistency, named information/policy/belief blocks,
hard/inequality/soft coherence declarations, transition and observation objects, and typed
intervention semantics. Test immutable ownership and duplicate-agent rejection.

**Step 2: Implement minimal immutable records**

Add `AgentBlock`, `CoherenceKind`, `CoherenceCondition`, `InterventionSemantics`, and
`EconomicWorldModelDefinition`. These records describe an EWM; they do not pretend to solve it.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_definition.py tests/unit/test_core_records.py -q`

Commit: `feat: encode Cong economic world model definition`

### Task 3: Implement DDGE correspondences and consistency certificates

**Files:**

- Create: `src/ewm/equilibrium/correspondence.py`
- Create: `tests/unit/test_correspondence.py`
- Modify: `src/ewm/equilibrium/__init__.py`
- Modify: `src/ewm/core/records.py`
- Modify: `references/conformance.toml`

**Step 1: Write failing tests**

Use finite discrete correspondences to test nonempty inner equilibrium sets, selector ambiguity,
behavioral optimality, belief consistency, feasibility/aggregate consistency, learning consistency,
and rejection of a candidate that satisfies only the outer parameter equation.

**Step 2: Implement verification, not a misleading universal solver**

Add typed finite `EquilibriumCorrespondence`, `DDGECandidate`, component residuals, and a
`DDGEConsistencyCertificate`. Preserve the existing efficient single-valued solver separately.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_correspondence.py tests/unit/test_fixed_point.py -q`

Commit: `feat: verify set-valued DDGE consistency`

### Task 4: Complete Cong's theorem diagnostics

**Files:**

- Modify: `src/ewm/equilibrium/diagnostics.py`
- Modify: `src/ewm/equilibrium/damping.py`
- Modify: `src/ewm/equilibrium/__init__.py`
- Create: `tests/unit/test_cong_bounds.py`
- Modify: `docs/mathematical-contract.md`
- Modify: `references/conformance.toml`

**Step 1: Write failing formula and edge-case tests**

Cover Proposition A.8's primitive modulus, Theorem 3.4's residual displacement and welfare bound,
its exact linear center displacement, Corollary A.9, Proposition 4.1's value/robust-regret bounds,
and Appendix A.10's damping stabilizability condition. Compare linear formulas with direct solves and
Bellman systems.

**Step 2: Implement named, assumption-explicit functions**

Inputs must expose all required constants; functions reject invalid contraction, discount, reward,
and dimension assumptions. Results record formulas and assumptions rather than returning anonymous
floats where a certificate is useful.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_cong_bounds.py tests/unit/test_diagnostics.py -q`

Commit: `feat: add Cong contraction welfare and robustness bounds`

### Task 5: Reproduce Cong Laboratory II exactly

**Files:**

- Create: `src/ewm/scenarios/scalar/model.py`
- Create: `src/ewm/scenarios/scalar/verification.py`
- Create: `src/ewm/scenarios/scalar/__init__.py`
- Create: `tests/scenarios/test_scalar.py`
- Create: `examples/scalar.py`
- Modify: `src/ewm/scenarios/__init__.py`
- Modify: `src/ewm/api.py`
- Modify: `references/conformance.toml`

**Step 1: Write failing closed-form tests**

Test Appendix equation (A.1), inner solution, composite gain, exact linear displacement, three roots
iff `g > 1`, near-onset expansion error, branch stability, complementarity versus contrarian damping,
and the a posteriori bound.

**Step 2: Implement source-parameterized model and independent root oracle**

Use SciPy bracketing for the nonzero roots and the package fixed-point solver as independent routes.
Do not copy results from the forecasting module.

**Step 3: Verify and commit**

Run: `python -m pytest tests/scenarios/test_scalar.py -q`

Commit: `feat: reproduce Cong scalar DDGE laboratory`

### Task 6: Tighten Cong Laboratory III replication

**Files:**

- Create: `src/ewm/scenarios/forecasting/verification.py`
- Modify: `src/ewm/scenarios/forecasting/model.py`
- Modify: `src/ewm/scenarios/forecasting/presets.py`
- Modify: `tests/scenarios/test_forecasting.py`
- Create: `tests/scenarios/test_forecasting_replication.py`
- Modify: `examples/forecasting.py`
- Modify: `references/conformance.toml`

**Step 1: Add paper-target tests**

Check `c=1.8`, `sigma=0.5`, the reported outer slopes near plus/minus `0.795`, derivative at the
origin within one percent, 4,000-observation rounds, basin dependence, noise ejection, and ACF
contrast. Separate deterministic population checks from seeded finite-sample evidence.

**Step 2: Add a named exact-paper preset and report**

Preserve smoke/research presets. Make Monte Carlo tolerances and seed sets explicit in metadata.

**Step 3: Verify and commit**

Run: `python -m pytest tests/scenarios/test_forecasting_replication.py -q`

Commit: `test: verify Cong self-fulfilling forecast laboratory`

### Task 7: Audit the Laboratory I reconstruction against every published target

**Files:**

- Create: `src/ewm/scenarios/credit/provenance.py`
- Create: `tests/scenarios/test_credit_paper_targets.py`
- Modify: `src/ewm/scenarios/credit/presets.py`
- Modify: `src/ewm/experiments/credit.py`
- Modify: `docs/experiments.md`
- Modify: `references/conformance.toml`

**Step 1: Encode published observables and missing primitives**

Record dimensions, cohort size, cutoff equation, qualitative ordering, figure-reported targets, and
the parameters absent from the PDF. Ensure the `paper_like` name cannot be read as exact
replication; introduce `cong_qualitative_reconstruction` with compatibility alias and warning-free
metadata.

**Step 2: Test all claims the source actually supports**

Assert endogenous adoption, selective observation, frozen predicted/realized sign reversal,
DDGE partial repair, zero omniscient effect, metric definitions, and residual/noise-floor reporting.
Numerical magnitudes that cannot be recreated exactly are reported as differences, not failures.

**Step 3: Verify and commit**

Run: `python -m pytest tests/scenarios/test_credit_paper_targets.py tests/scenarios/test_credit.py -q`

Commit: `docs: delimit and verify Cong credit reconstruction`

### Task 8: Match Han's specification interfaces

**Files:**

- Create: `src/ewm/core/specs.py`
- Create: `tests/unit/test_specs.py`
- Modify: `src/ewm/core/__init__.py`
- Modify: `src/ewm/api.py`
- Modify: `src/ewm/__init__.py`
- Modify: `references/conformance.toml`

**Step 1: Write failing Figure 9, 11, 13, and 15 construction tests**

Cover `agent`, `state`, `constraints`, `scheduler`, `mechanism`, `environment`, `coevolution`,
`alignment`, and `evaluation` factories using the paper's FX-shaped examples.

**Step 2: Implement immutable declarative specifications**

Factories validate references among action types, roles, accounts, signals, targets, and correction
bounds. They compile only supported mechanisms into a runtime and fail clearly for declarations
without an implementation.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_specs.py tests/integration/test_public_api.py -q`

Commit: `feat: add Han declarative specification interfaces`

### Task 9: Match Han's compact runtime protocol

**Files:**

- Modify: `src/ewm/core/world.py`
- Modify: `src/ewm/core/protocols.py`
- Modify: `src/ewm/core/events.py`
- Create: `src/ewm/core/evaluation.py`
- Create: `tests/integration/test_han_runtime_protocol.py`
- Modify: `references/conformance.toml`

**Step 1: Write failing Figure 8, 10, 12, and 17 tests**

Exercise `reset`, `run_agents(state, parallel=...)`, stateful `step(actions)`, backward-compatible
`step(state, actions)`, `log`, read-only `evaluate`, and idempotent `close`. Confirm every public
call emits a versioned event and evaluation cannot mutate world state.

**Step 2: Implement deterministic state ownership and scheduler boundary**

`parallel=True` may use concurrency only when deterministic independent RNG streams preserve action
identity. If the initial implementation executes serially, report that fact in diagnostics instead of
claiming parallel efficiency.

**Step 3: Verify and commit**

Run: `python -m pytest tests/integration/test_han_runtime_protocol.py tests/unit/test_world.py -q`

Commit: `feat: implement Han runtime protocol`

### Task 10: Implement controlled agent-environment co-evolution

**Files:**

- Create: `src/ewm/core/coevolution.py`
- Create: `tests/unit/test_coevolution.py`
- Modify: `src/ewm/core/world.py`
- Modify: `src/ewm/core/records.py`
- Modify: `references/conformance.toml`

**Step 1: Test bidirectional, allow-listed, versioned updates**

Use a small deterministic market where outcome feedback updates one agent belief and aggregate
behavior recalibrates one mechanism parameter. Reject undeclared targets and out-of-bound updates.

**Step 2: Implement `world.coevolve(state, actions, next_state)`**

Return a structured update report with before/after versions, signals, bounded deltas, and stability
diagnostics. Co-evolution is distinct from external alignment.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_coevolution.py -q`

Commit: `feat: add controlled agent environment coevolution`

### Task 11: Add L3 cognitive-agent substrate without an SDK lock-in

**Files:**

- Create: `src/ewm/capabilities/cognition.py`
- Create: `src/ewm/capabilities/__init__.py`
- Create: `tests/unit/test_cognition.py`
- Create: `examples/cognitive_agent.py`
- Modify: `pyproject.toml`
- Modify: `references/conformance.toml`

**Step 1: Test an injectable language-model boundary**

Use a deterministic fake backend to verify role-specific observation, explicit beliefs, bounded
memory, declared tools, schema-validated actions, retry/failure behavior, and provenance. Never test
against a paid or nondeterministic provider in CI.

**Step 2: Implement a provider-neutral protocol**

No Mastra, LangChain, Mesa, or provider SDK is required. Add optional adapters only when they reduce
real complexity. The fake backend proves protocol conformance but does not award empirical
behavioral fidelity.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_cognition.py -q`

Commit: `feat: add provider neutral cognitive agents`

### Task 12: Add L4 persistent capability evolution

**Files:**

- Create: `src/ewm/capabilities/evolution.py`
- Create: `tests/unit/test_capability_evolution.py`
- Modify: `src/ewm/capabilities/__init__.py`
- Modify: `references/conformance.toml`

**Step 1: Test proposal, sandbox evaluation, promotion, rollback, and persistence**

Capabilities may add a versioned strategy, skill, tool, memory routine, or policy routine only after
passing declared evaluation and safety gates. Failed candidates leave the active agent unchanged.

**Step 2: Implement artifact-neutral evolution records**

The core stores manifests and evidence, not executable arbitrary code. Persistence is explicit
serialization of approved manifests.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_capability_evolution.py -q`

Commit: `feat: add gated self evolution substrate`

### Task 13: Add L5 endogenous institutional evolution

**Files:**

- Create: `src/ewm/capabilities/institutions.py`
- Create: `tests/unit/test_institutions.py`
- Modify: `src/ewm/core/world.py`
- Modify: `src/ewm/capabilities/__init__.py`
- Modify: `references/conformance.toml`

**Step 1: Test proposals and constitutional constraints**

Agents or diagnostics may propose versioned rule, mechanism, contract, policy, information, or
governance changes. Changes require allow-list, feasibility, accounting, safety, and acceptance
checks. Counterexamples verify that rule evolution cannot bypass hard coherence.

**Step 2: Implement institution transition records and application boundary**

Keep governance selection pluggable and deterministic in CI. Emit regime/version changes into the
world log so counterfactuals remain reproducible.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_institutions.py -q`

Commit: `feat: add governed institutional evolution`

### Task 14: Add L6 external-evidence alignment with bounded correction

**Files:**

- Create: `src/ewm/capabilities/alignment.py`
- Create: `tests/unit/test_alignment.py`
- Modify: `src/ewm/core/world.py`
- Modify: `src/ewm/capabilities/__init__.py`
- Create: `examples/offline_alignment.py`
- Modify: `references/conformance.toml`

**Step 1: Test Figure 15 and 16 semantics offline**

Use a timestamped fixture stream to measure target-specific discrepancy, compare tolerances,
diagnose source, plan allow-listed bounded corrections, apply atomically, and retain intervention
provenance. Test stale evidence, missing targets, excessive corrections, and no-op within tolerance.

**Step 2: Implement adapters, metrics, and correction reports**

Separate data retrieval from alignment logic. The fixture demonstrates the correction protocol, not
a live economic twin. A capability gate must continue to withhold validated L6 status without an
external-data contract, repeated out-of-sample evidence, and drift/correction performance.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_alignment.py -q`

Commit: `feat: add bounded real world alignment protocol`

### Task 15: Make capability claims machine-checkable

**Files:**

- Create: `src/ewm/capabilities/levels.py`
- Create: `tests/unit/test_capability_levels.py`
- Modify: `src/ewm/capabilities/__init__.py`
- Modify: `docs/capability-matrix.md`
- Modify: `references/conformance.toml`

**Step 1: Write adversarial gate tests**

An interface, fake backend, single correction, or self-reported label must not award L3–L6. Test the
cumulative prerequisites and evidence requirements for each level.

**Step 2: Implement evidence objects and assessments**

Return achieved level, satisfied requirements, missing requirements, evidence provenance, and
warnings. Preserve separate DDGE-consistency and empirical-validity axes.

**Step 3: Verify and commit**

Run: `python -m pytest tests/unit/test_capability_levels.py -q`

Commit: `feat: enforce EWM capability evidence gates`

### Task 16: Implement Cong's competitive-equilibrium template as a disclosed instantiation

**Files:**

- Create: `src/ewm/scenarios/production/model.py`
- Create: `src/ewm/scenarios/production/__init__.py`
- Create: `tests/scenarios/test_production.py`
- Create: `examples/production.py`
- Modify: `src/ewm/scenarios/__init__.py`
- Modify: `references/conformance.toml`

**Step 1: Test budgets, firm optimality, and both clearing equations**

Instantiate Appendix D with documented CRRA/disutility and Cobb-Douglas primitives supplied by the
package. Solve prices independently through root equations and closed-form first-order conditions in
a tractable case. Property-test feasibility over bounded aggregate states.

**Step 2: Implement a transparent distributional state**

Keep household assets/shocks explicit, prices endogenous, borrowing bound enforced by construction,
and market residuals reported. Label all primitives absent from Cong as package-authored.

**Step 3: Verify and commit**

Run: `python -m pytest tests/scenarios/test_production.py -q`

Commit: `feat: instantiate Cong competitive economy template`

### Task 17: Add the layered evaluation stack

**Files:**

- Create: `src/ewm/experiments/evaluation.py`
- Create: `tests/integration/test_layered_evaluation.py`
- Modify: `src/ewm/core/evaluation.py`
- Modify: `src/ewm/experiments/__init__.py`
- Modify: `docs/experiments.md`
- Modify: `references/conformance.toml`

**Step 1: Test Han Table 3 layers**

Produce agent, environment, co-evolution, alignment, and efficiency sections. Include action
validity, role consistency, constraint rate, clearing/accounting error, adaptation gain/stability,
drift/correction magnitude, runtime, and memory/agent scaling. Missing evidence is `not-measured`,
never zero.

**Step 2: Implement read-only reports over versioned event logs**

Ensure the evaluator does not change world, agent, mechanism, or correction state.

**Step 3: Verify and commit**

Run: `python -m pytest tests/integration/test_layered_evaluation.py -q`

Commit: `feat: add layered EWM evaluation reports`

### Task 18: Add end-to-end conformance laboratories

**Files:**

- Create: `tests/conformance/test_cong_conformance.py`
- Create: `tests/conformance/test_han_conformance.py`
- Create: `tests/conformance/test_claim_boundaries.py`
- Create: `scripts/run_conformance.py`
- Modify: `pyproject.toml`
- Modify: `references/conformance.toml`

**Step 1: Add independent paper-level tests**

Cong tests traverse definition -> equilibrium -> data -> learner -> fixed point -> residual/bounds.
Han tests traverse specification -> reset -> actions -> transition -> co-evolution -> offline alignment
-> evaluation, then inspect every logged event. Claim-boundary tests reject unsupported exact,
calibrated, policy-valid, or digital-twin labels.

**Step 2: Add a reproducible local conformance command**

Emit JSON with source hashes, package/runtime fingerprints, deterministic test outcomes, stochastic
seed sets, achieved capability gates, and unresolved external dependencies.

**Step 3: Verify and commit**

Run: `python -m pytest tests/conformance -q`

Commit: `test: add paper level conformance suite`

### Task 19: Publish complete documentation without inflating claims

**Files:**

- Modify: `README.md`
- Modify: `docs/mathematical-contract.md`
- Modify: `docs/capability-matrix.md`
- Modify: `docs/product-validation.md`
- Modify: `docs/paper-traceability.md`
- Create: `docs/replication.md`
- Create: `docs/limitations.md`

**Step 1: Document the architecture and paper mapping**

Explain what comes verbatim from paper definitions, what is an exact numerical replication, what is
a systems-protocol conformance implementation, and what this package authors. Render equations in
GitHub-supported LaTeX blocks and keep prose free of unsupported claims.

**Step 2: Document reproduction and unresolved dependencies**

Provide exact commands, expected ranges, source versions, seeds, and why Laboratory I cannot yet be
called exact. Explain that L3–L6 interfaces do not by themselves validate human behavior or a real
economy twin.

**Step 3: Verify and commit**

Run: `python -m pytest tests/integration/test_paper_traceability.py tests/conformance -q`

Commit: `docs: publish paper faithful replication guide`

### Task 20: Full independent release audit

**Files:**

- Modify as findings require; do not weaken tests to obtain green status.

**Step 1: Run all static and behavioral gates**

Run:

```bash
python -m ruff check .
python -m mypy src
python -m pytest --cov=ewm --cov-report=term-missing --cov-branch
python -m build
python scripts/run_conformance.py
python scripts/scientific_stress.py
python scripts/benchmark_experiments.py
```

**Step 2: Inspect artifacts and clean-install the wheel**

Install the built wheel into a fresh temporary virtual environment, run public examples, and verify
that source registries and typing markers are packaged as intended.

**Step 3: Run a claim audit and update evidence documents**

Search for `exact`, `replicate`, `validated`, `calibrated`, `twin`, `L3`, `L4`, `L5`, and `L6`.
Every occurrence must link to evidence or state a limitation.

**Step 4: Commit and push final audit evidence**

Commit: `chore: complete paper faithful release audit`

Push `main`, verify every GitHub Actions job succeeds, and record the successful commit SHA and
workflow URLs in `docs/product-validation.md`.

## Completion conditions

The goal is complete only when:

- every registered implementable paper item is either implemented with passing evidence or marked
  `blocked-external` with a precise missing source/evidence dependency;
- Cong Laboratories II and III pass exact paper-target tests;
- Laboratory I is never called exact without the missing author parameters/code;
- all five Han evaluation layers and all seven runtime calls are executable;
- L3–L6 substrates exist, but achieved levels are awarded only by evidence gates;
- the full suite, static checks, build, clean install, stress tests, and benchmarks pass;
- every coherent change is committed and pushed separately to `main`; and
- GitHub Actions is green at the final commit.
