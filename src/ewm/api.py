"""Stable, deliberately small public facade for worlds and experiments."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, overload

from ewm.core import (
    AgentSpecification,
    AlignmentSpecification,
    CoevolutionSpecification,
    DDGEProblem,
    EnvironmentSpecification,
    EvaluationSpecification,
    WorldSpecification,
)
from ewm.core.specs import (
    agent,
    agent_updates,
    alignment,
    coevolution,
    constraints,
    correction,
    data_sources,
    environment,
    environment_updates,
    evaluation,
    mechanism,
    scheduler,
    state,
)
from ewm.experiments import (
    EXPERIMENTS,
    SCENARIO_DESCRIPTIONS,
    SCENARIO_REGISTRY,
    RolloutResult,
    ScenarioConfig,
)
from ewm.experiments.runner import ExperimentRun, run_experiment
from ewm.scenarios.credit import CreditRegime


@dataclass(frozen=True, slots=True)
class ScenarioHandle:
    """A configured scenario with explicit preset and seed provenance."""

    name: str
    preset: str
    seed: int
    config: ScenarioConfig

    def ddge_problem(
        self,
        *,
        regime: CreditRegime = CreditRegime.SELECTIVE,
    ) -> DDGEProblem:
        """Construct this scenario's declared behavior-data-learning problem."""

        return SCENARIO_REGISTRY.scenario(self.name).make_ddge_problem(
            self.config,
            regime,
        )


@overload
def make(
    name: str,
    *,
    preset: str = "smoke",
    seed: int = 42,
    agents: None = None,
    environment: None = None,
    coevolution: None = None,
    alignment: None = None,
    evaluation: None = None,
    **overrides: Any,
) -> ScenarioHandle: ...


@overload
def make(
    name: str,
    *,
    agents: Sequence[AgentSpecification],
    environment: EnvironmentSpecification,
    coevolution: CoevolutionSpecification | None = None,
    alignment: AlignmentSpecification | None = None,
    evaluation: EvaluationSpecification | None = None,
    preset: str = "smoke",
    seed: int = 42,
    **overrides: Any,
) -> WorldSpecification: ...


def make(
    name: str,
    *,
    preset: str = "smoke",
    seed: int = 42,
    agents: Sequence[AgentSpecification] | None = None,
    environment: EnvironmentSpecification | None = None,
    coevolution: CoevolutionSpecification | None = None,
    alignment: AlignmentSpecification | None = None,
    evaluation: EvaluationSpecification | None = None,
    **overrides: Any,
) -> ScenarioHandle | WorldSpecification:
    """Configure a named laboratory or assemble Han's declarative world specification."""

    declares_world = any(
        item is not None for item in (agents, environment, coevolution, alignment, evaluation)
    )
    if declares_world:
        if agents is None or environment is None:
            raise ValueError("declarative make requires agents and environment")
        if overrides:
            raise ValueError("scenario overrides do not apply to declarative specifications")
        return WorldSpecification(
            name=name,
            agents=tuple(agents),
            environment=environment,
            coevolution=coevolution,
            alignment=alignment,
            evaluation=evaluation,
        )

    if preset not in ("smoke", "research"):
        raise ValueError("preset must be 'smoke' or 'research'")
    config = SCENARIO_REGISTRY.scenario(name).configure(preset, seed, overrides)
    return ScenarioHandle(name=name, preset=preset, seed=seed, config=config)


def rollout(
    scenario: ScenarioHandle,
    *,
    periods: int | None = None,
    theta: float = 0.0,
) -> RolloutResult:
    """Simulate a configured temporal world while holding learned parameters fixed."""

    if periods is not None and periods < 1:
        raise ValueError("periods must be positive")
    return SCENARIO_REGISTRY.scenario(scenario.name).run_rollout(
        scenario.config,
        scenario.seed,
        periods,
        theta,
    )


def list_scenarios() -> tuple[str, ...]:
    """Return all registered economic laboratories."""

    return tuple(sorted(SCENARIO_DESCRIPTIONS))


def list_experiments() -> tuple[str, ...]:
    """Return all registered reproducible experiments."""

    return tuple(sorted(EXPERIMENTS))


def describe(name: str) -> str:
    """Describe a registered scenario or experiment."""

    if name in SCENARIO_DESCRIPTIONS:
        return SCENARIO_DESCRIPTIONS[name]
    if name in EXPERIMENTS:
        return EXPERIMENTS[name].description
    choices = ", ".join((*list_scenarios(), *list_experiments()))
    raise ValueError(f"unknown scenario or experiment {name!r}; choose from: {choices}")


__all__ = [
    "ExperimentRun",
    "RolloutResult",
    "ScenarioHandle",
    "agent",
    "agent_updates",
    "alignment",
    "coevolution",
    "constraints",
    "correction",
    "data_sources",
    "describe",
    "environment",
    "environment_updates",
    "evaluation",
    "list_experiments",
    "list_scenarios",
    "make",
    "mechanism",
    "rollout",
    "run_experiment",
    "scheduler",
    "state",
]
