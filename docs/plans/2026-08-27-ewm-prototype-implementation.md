# EWM Prototype Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Build and validate an installable open-source Python package implementing a shared EWM/DDGE core plus forecasting, FX, and AI-mediated credit laboratories.

**Architecture:** Use a modular monolith with immutable records and structural protocols at the core. Generic world and fixed-point machinery consume those protocols; scenarios provide only economic primitives and oracle checks; an experiment layer composes scenarios, solvers, statistics, and local artifacts.

**Tech Stack:** Python 3.11+, NumPy, SciPy, pandas, scikit-learn, pytest, Hypothesis, Ruff, mypy, coverage, GitHub Actions.

---

## Shared conventions

- Create `.venv` with `python -m venv .venv` and run project commands through
  `.venv/bin/python`; the system interpreter is PEP 668 managed.
- Use a `src/` package layout and distribution name `economic-world-model`; import name is `ewm`.
- Use frozen, slotted dataclasses for value records and `typing.Protocol` for behavior boundaries.
- Pass `numpy.random.Generator` explicitly into every stochastic operation.
- Never call `numpy.random.seed` or module-level random functions.
- Scenario modules may import `ewm.core`, NumPy, SciPy, pandas, and scikit-learn. They may not import `ewm.experiments` or generic solver implementations.
- Tests follow `test_<unit>_<behavior>` naming and compare economic quantities with declared tolerances.
- After each task, run the task-specific test, then `python -m pytest -q` before committing.

### Task 1: Package and repository foundation

**Files:**

- Create: `pyproject.toml`
- Create: `README.md`
- Create: `LICENSE`
- Create: `src/ewm/__init__.py`
- Create: `src/ewm/py.typed`
- Create: `tests/test_package.py`

**Step 1: Write the failing package test**

```python
from importlib.metadata import version

import ewm


def test_package_exposes_version() -> None:
    assert ewm.__version__ == version("economic-world-model")
```

**Step 2: Verify failure**

Run: `python -m pytest tests/test_package.py -q`  
Expected: failure because the package and metadata do not exist.

**Step 3: Add minimal package metadata**

Use Hatchling, Python `>=3.11`, runtime dependencies `numpy`, `scipy`, `pandas`, and
`scikit-learn`, plus a `dev` optional dependency containing pytest, Hypothesis, Ruff, mypy, coverage,
and build. Do not declare the CLI entry point until Task 8 creates `ewm.cli`. In `__init__.py`, use
`importlib.metadata.version` and export `__version__`.

The README must state the synthetic-only claim boundary and list the three laboratories. Use the MIT
license for version 0.1.

**Step 4: Install and verify**

Run: `python -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'`  
Expected: editable installation succeeds.

Run: `.venv/bin/python -m pytest tests/test_package.py -q`  
Expected: one passing test.

**Step 5: Commit**

```bash
git add .gitignore pyproject.toml README.md LICENSE src/ewm tests/test_package.py docs
git commit -m "chore: initialize EWM research package"
```

### Task 2: Core records, protocols, randomness, and events

**Files:**

- Create: `src/ewm/core/__init__.py`
- Create: `src/ewm/core/records.py`
- Create: `src/ewm/core/protocols.py`
- Create: `src/ewm/core/randomness.py`
- Create: `src/ewm/core/events.py`
- Create: `tests/unit/test_core_records.py`
- Create: `tests/unit/test_randomness.py`

**Step 1: Write failing contract tests**

```python
import numpy as np

from ewm.core import Action, EventLog, RunMetadata, make_rng


def test_run_metadata_and_action_are_immutable() -> None:
    metadata = RunMetadata(scenario="forecasting", seed=42, run_id="test")
    action = Action(agent_id="a", kind="hold", values={})
    assert metadata.seed == 42
    assert action.kind == "hold"


def test_owned_rng_is_reproducible() -> None:
    assert np.array_equal(make_rng(7).normal(size=8), make_rng(7).normal(size=8))


def test_event_log_returns_a_snapshot() -> None:
    log = EventLog()
    log.append("reset", {"seed": 1})
    assert log.snapshot()[0].kind == "reset"
```

Also test frozen-record assignment failure and that mutating a returned event payload cannot mutate
the stored event.

**Step 2: Verify failure**

Run: `python -m pytest tests/unit/test_core_records.py tests/unit/test_randomness.py -q`  
Expected: import failures.

**Step 3: Implement the core contracts**

Create records for `RunMetadata`, `Action`, `ConstraintViolation`, `Transition`, `GeneratedDataset`,
`EquilibriumResult`, `FixedPoint`, `DDGEResult`, and `ExperimentResult`. Store arrays as NumPy arrays
but copy them at record boundaries where mutation would corrupt provenance.

Define structural protocols for:

```python
class EconomicWorld(Protocol):
    def reset(self, seed: int | None = None) -> object: ...
    def observe(self, state: object, agent_id: str) -> object: ...
    def run_agents(self, state: object) -> tuple[Action, ...]: ...
    def step(self, state: object, actions: tuple[Action, ...]) -> Transition: ...


class DDGEProblem(Protocol):
    @property
    def dimension(self) -> int: ...
    def update(self, theta: np.ndarray) -> np.ndarray: ...
```

`EventLog` uses a private list and returns immutable snapshots. `make_rng(seed)` returns
`np.random.default_rng(seed)`. `spawn_rngs(seed, count)` uses `SeedSequence.spawn`.

**Step 4: Verify contracts**

Run: `python -m pytest tests/unit/test_core_records.py tests/unit/test_randomness.py -q`  
Expected: all tests pass.

**Step 5: Commit**

```bash
git add src/ewm/core tests/unit
git commit -m "feat: add typed EWM core contracts"
```

### Task 3: World runtime, constraints, and mechanisms

**Files:**

- Create: `src/ewm/core/agents.py`
- Create: `src/ewm/core/constraints.py`
- Create: `src/ewm/core/mechanisms.py`
- Create: `src/ewm/core/world.py`
- Create: `tests/unit/test_constraints.py`
- Create: `tests/unit/test_world.py`

**Step 1: Write failing runtime tests**

Test that:

- rejected actions never enter the mechanism;
- the rejection is present in `Transition.violations` and the event log;
- agent execution order is deterministic;
- `step` does not mutate the input state;
- two resets with the same seed produce equivalent initial states.

Use a tiny test mechanism:

```python
class SumMechanism:
    def clear(self, state, actions, rng):
        return {"total": state["total"] + sum(a.values["amount"] for a in actions)}, {}
```

**Step 2: Verify failure**

Run: `python -m pytest tests/unit/test_constraints.py tests/unit/test_world.py -q`  
Expected: import failures.

**Step 3: Implement the runtime**

Implement `Constraint` and `Mechanism` protocols, `ConstraintSet.validate`, a `FunctionalAgent`, and
`World`. `World.step` must execute:

```text
copy state -> validate actions -> retain feasible actions -> deterministic schedule
-> mechanism.clear -> build Transition -> append event -> return
```

The runtime remains synchronous in version 0.1. Do not add threads or a deceptive `parallel=True`
argument.

**Step 4: Verify runtime behavior**

Run: `python -m pytest tests/unit/test_constraints.py tests/unit/test_world.py -q`  
Expected: all tests pass.

Run: `python -m pytest -q`  
Expected: complete suite passes.

**Step 5: Commit**

```bash
git add src/ewm/core tests/unit
git commit -m "feat: add deterministic economic world runtime"
```

### Task 4: Generic fixed-point and DDGE solvers

**Files:**

- Create: `src/ewm/equilibrium/__init__.py`
- Create: `src/ewm/equilibrium/fixed_point.py`
- Create: `src/ewm/equilibrium/inner.py`
- Create: `src/ewm/equilibrium/ddge.py`
- Create: `src/ewm/equilibrium/damping.py`
- Create: `src/ewm/equilibrium/diagnostics.py`
- Create: `tests/unit/test_fixed_point.py`
- Create: `tests/unit/test_diagnostics.py`

**Step 1: Write failing mathematical tests**

Cover:

- linear map `F(theta)=0.4 theta + 1.2` converges to `theta=2`;
- a scalar inner-equilibrium residual solved through `solve_equilibrium` agrees with
  `scipy.optimize.root`;
- damped update equals `(1-eta) theta + eta F(theta)`;
- multistart on `F(theta)=tanh(1.8 theta)` returns three distinct roots;
- a complementary eigenvalue above one remains unstable for every positive damping value tested;
- a negative eigenvalue `-1.6` is stabilized at `eta=0.5`;
- contraction residual bound dominates true remaining distance for the linear case.

**Step 2: Verify failure**

Run: `python -m pytest tests/unit/test_fixed_point.py tests/unit/test_diagnostics.py -q`  
Expected: import failures.

**Step 3: Implement solvers and diagnostics**

Add an `EquilibriumProblem` protocol with a residual method and implement `solve_equilibrium` as a
thin, result-preserving wrapper around SciPy root finding. Implement `FixedPointConfig`,
`iterate_fixed_point`, `solve_multistart`, `solve_ddge`,
`fixed_point_residual`, `finite_difference_jacobian`, `local_modulus`, and
`posteriori_distance_bound`. Deduplicate roots by Euclidean tolerance and preserve initialization,
iteration count, residual path, convergence status, and local stability estimate.

**Step 4: Verify mathematics by two methods**

Run the unit tests, then independently compare the linear fixed point with `scipy.optimize.root` in a
test. Expected: all roots and residual bounds agree within declared tolerances.

**Step 5: Commit**

```bash
git add src/ewm/equilibrium tests/unit
git commit -m "feat: add DDGE fixed-point solvers and diagnostics"
```

### Task 5: Self-fulfilling forecasting laboratory

**Files:**

- Create: `src/ewm/scenarios/__init__.py`
- Create: `src/ewm/scenarios/forecasting/__init__.py`
- Create: `src/ewm/scenarios/forecasting/model.py`
- Create: `src/ewm/scenarios/forecasting/presets.py`
- Create: `src/ewm/scenarios/forecasting/oracles.py`
- Create: `tests/scenarios/test_forecasting.py`

**Step 1: Write failing laboratory tests**

Test `F(0)=0`, a central finite-difference estimate of `F'(0)=c`, one root below `c=1`, three roots
above `c=1`, stable outer branches, unstable middle branch, sign-selected basins, and seeded
finite-sample ejection from zero.

**Step 2: Implement the induced population map**

Simulate the stationary law under a deployed slope using burn-in and explicit common random
numbers. Estimate the population update from the conditional mean,

```python
numerator = mean(x * tanh(c * theta * x))
denominator = mean(x * x)
return numerator / denominator
```

rather than regressing realized next-period noise. This preserves `F(0)=0` and the exact local
derivative while still allowing the deployment-induced stationary distribution to vary with `theta`.
Use antithetic shocks for symmetry. Add a separate finite-sample retraining path that regresses
realized transitions and therefore exhibits sampling-noise ejection.

**Step 3: Add oracle report**

The oracle report compares multistart roots with bracketing roots from `scipy.optimize.brentq`, finite-
difference and analytical derivatives, local stability, and simulated first autocorrelation.

**Step 4: Verify**

Run: `python -m pytest tests/scenarios/test_forecasting.py -q`  
Expected: all theoretical and stochastic assertions pass under fixed seeds.

**Step 5: Commit**

```bash
git add src/ewm/scenarios tests/scenarios/test_forecasting.py
git commit -m "feat: add self-fulfilling forecasting laboratory"
```

### Task 6: Multi-agent FX laboratory

**Files:**

- Create: `src/ewm/scenarios/fx/__init__.py`
- Create: `src/ewm/scenarios/fx/model.py`
- Create: `src/ewm/scenarios/fx/mechanism.py`
- Create: `src/ewm/scenarios/fx/agents.py`
- Create: `src/ewm/scenarios/fx/presets.py`
- Create: `tests/scenarios/test_fx.py`
- Create: `tests/properties/test_fx_accounting.py`

**Step 1: Write failing mechanism and property tests**

Test no-crossing books, exact crossing, partial pro-rata allocation, budget rejection, inventory
rejection, deterministic tie-breaking, cash conservation, FX conservation, and clearing equality.
Use Hypothesis to generate feasible books and assert conservation after settlement.

**Step 2: Implement typed FX economics**

Define immutable `FXAccount`, `FXOrder`, and `FXState`. Implement household, firm, and bank policy
functions. Implement uniform-price batch clearing by choosing the candidate limit price that maximizes
executable volume, using deterministic tie-breaking and pro-rata allocation on the long side.

**Step 3: Implement adaptive rollout and comparisons**

Update bounded-memory beliefs after each clearing event. Add paired demand-shock, trend-intensity,
and adaptive-versus-fixed experiments. Report price, volume, volatility, rejected orders, accounting
residuals, and effect differences.

**Step 4: Verify**

Run: `python -m pytest tests/scenarios/test_fx.py tests/properties/test_fx_accounting.py -q`  
Expected: all example and generated accounting tests pass.

**Step 5: Commit**

```bash
git add src/ewm/scenarios/fx tests/scenarios/test_fx.py tests/properties
git commit -m "feat: add multi-agent FX laboratory"
```

### Task 7: AI-mediated credit laboratory

**Files:**

- Create: `src/ewm/scenarios/credit/__init__.py`
- Create: `src/ewm/scenarios/credit/model.py`
- Create: `src/ewm/scenarios/credit/population.py`
- Create: `src/ewm/scenarios/credit/learner.py`
- Create: `src/ewm/scenarios/credit/presets.py`
- Create: `src/ewm/scenarios/credit/oracles.py`
- Create: `tests/scenarios/test_credit.py`

**Step 1: Write failing economic-invariant tests**

Test that GenAI changes text but not quality or potential repayment, adoption requires a decision
flip and affordable cost, only approved outcomes enter selective retraining, full-information training
uses the entire cohort, and the omniscient screener is invariant to polish.

**Step 2: Implement population and learner**

Generate latent quality, ten structured features, fifteen text features, adoption costs, and common
repayment uniforms. Use a ridge-logistic learner with an intercept and explicit coefficient vector.
Implement approval from the zero-profit threshold and profit from repayment revenue and loss given
default.

**Step 3: Implement five regimes and DDGE problem**

Implement no-GenAI, frozen-model, selective-DDGE, full-information-DDGE, and omniscient-oracle
evaluations. The DDGE update regenerates adoption and observations under the candidate coefficients,
fits the declared training sample, and applies damping.

**Step 4: Add counterfactual and sensitivity tests**

Tune only the named `paper_like` preset to exhibit the prespecified qualitative pattern. Add a small
parameter grid demonstrating that sign reversal and selective-training dominance are not universal.
Report profit per applicant, adoption, AUC, FPR/FNR, residual, noise floor, and coefficient distance.

Run: `python -m pytest tests/scenarios/test_credit.py -q`  
Expected: invariants and named-preset hypotheses pass; sensitivity cases include at least one boundary
or reversal.

**Step 5: Commit**

```bash
git add src/ewm/scenarios/credit tests/scenarios/test_credit.py
git commit -m "feat: add AI-mediated credit DDGE laboratory"
```

### Task 8: Experiment runner, artifacts, public API, and CLI

**Files:**

- Create: `src/ewm/experiments/__init__.py`
- Create: `src/ewm/experiments/registry.py`
- Create: `src/ewm/experiments/runner.py`
- Create: `src/ewm/experiments/metrics.py`
- Create: `src/ewm/experiments/statistics.py`
- Create: `src/ewm/experiments/artifacts.py`
- Create: `src/ewm/api.py`
- Create: `src/ewm/cli.py`
- Modify: `src/ewm/__init__.py`
- Modify: `pyproject.toml`
- Create: `tests/integration/test_public_api.py`
- Create: `tests/integration/test_artifacts.py`

**Step 1: Write failing public-flow tests**

Exercise `ewm.make`, `ewm.rollout`, `ewm.solve_ddge`, and `ewm.run_experiment`. Verify that a run
directory contains valid `manifest.json`, `config.json`, `metrics.json`, `summary.csv`, `trace.npz`,
and `events.jsonl`, and that repeated identical inputs produce identical numerical contents and run
hashes.

**Step 2: Implement explicit registry and runner**

Use a plain dictionary of scenario factories. Reject unknown scenarios and experiments with helpful
messages. The runner owns seeds, timing, configuration hashing, paired statistics, and artifact
creation; scenario code returns records and never writes files.

**Step 3: Implement the thin CLI**

Use `argparse` with `list`, `run`, and `describe` commands. No interactive UI or web dependency.
Declare `ewm = "ewm.cli:main"` in `pyproject.toml` only after the module exists. Re-export
`solve_equilibrium` alongside the other approved public operations.

**Step 4: Verify**

Run: `python -m pytest tests/integration -q`  
Expected: all public API and artifact tests pass.

Run: `ewm list`  
Expected: forecasting, fx, and credit scenarios are listed.

**Step 5: Commit**

```bash
git add src/ewm tests/integration
git commit -m "feat: expose reproducible EWM experiment API"
```

### Task 9: Quality gates, documentation, CI, and release verification

**Files:**

- Create: `docs/mathematical-contract.md`
- Create: `docs/experiments.md`
- Create: `docs/capability-matrix.md`
- Create: `examples/forecasting.py`
- Create: `examples/fx.py`
- Create: `examples/credit.py`
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `pyproject.toml`
- Create: `tests/test_architecture.py`

**Step 1: Add architecture-boundary test**

Use the standard-library AST to reject imports from `ewm.experiments` or `ewm.equilibrium` inside
scenario modules and any upward import inside core.

**Step 2: Add documentation and examples**

Document equations, regime semantics, hypothesis status, capability levels, reproducibility,
limitations, and exact smoke/research commands. Every example must execute in CI.

**Step 3: Add CI and static gates**

CI runs on supported Python versions and executes Ruff, mypy, pytest, coverage, package build, and
the three examples. Add coverage configuration with a defensible threshold after measuring the suite.

**Step 4: Complete the scientific acceptance audit**

Run:

```bash
ruff check .
mypy src
python -m pytest -q
python -m build
python examples/forecasting.py
python examples/fx.py
python examples/credit.py
```

Expected: all commands succeed. Inspect output artifacts and verify each approved requirement against
tests or runnable evidence. Do not infer broad completion from a narrow smoke test.

**Step 5: Commit and push**

```bash
git add .
git commit -m "docs: complete initial EWM research release"
git push -u origin main
```

Verify the public GitHub repository, default branch, README rendering, license detection, and CI state.
