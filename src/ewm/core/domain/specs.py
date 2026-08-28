"""Immutable specifications shaped after Han et al. Figures 9-15."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, cast

from .records import freeze_value


def _names(
    values: Sequence[str],
    label: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    result = tuple(values)
    if not allow_empty and not result:
        raise ValueError(f"{label} must not be empty")
    if any(not value for value in result):
        raise ValueError(f"{label} must not contain empty names")
    if len(result) != len(set(result)):
        raise ValueError(f"{label} must be unique")
    return result


def _named_channels(
    values: Mapping[str, Sequence[str]],
) -> Mapping[str, tuple[str, ...]]:
    if not values:
        raise ValueError("information_channels must not be empty")
    channels = {
        name: _names(signals, f"information channel {name!r}")
        for name, signals in values.items()
    }
    if any(not name for name in channels):
        raise ValueError("information channel names must not be empty")
    return cast(Mapping[str, tuple[str, ...]], freeze_value(channels))


@dataclass(frozen=True, slots=True)
class AgentSpecification:
    """Role-level agent declaration from Han et al. Figure 9."""

    role: str
    objective: str
    state_variables: tuple[str, ...]
    information_channels: Mapping[str, tuple[str, ...]]
    action_space: tuple[str, ...]
    tools: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    memory_window: int = 0
    count: int = 1
    belief: str | None = None

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("agent role must not be empty")
        if not self.objective:
            raise ValueError("agent objective must not be empty")
        if self.count < 1:
            raise ValueError("agent count must be positive")
        if self.memory_window < 0:
            raise ValueError("memory_window must be non-negative")
        if self.belief == "":
            raise ValueError("belief must not be empty")
        object.__setattr__(
            self,
            "state_variables",
            _names(self.state_variables, "agent state_variables"),
        )
        object.__setattr__(
            self,
            "information_channels",
            _named_channels(self.information_channels),
        )
        object.__setattr__(
            self,
            "action_space",
            _names(self.action_space, "agent action_space"),
        )
        object.__setattr__(self, "tools", _names(self.tools, "agent tools", allow_empty=True))
        object.__setattr__(
            self,
            "constraints",
            _names(self.constraints, "agent constraints", allow_empty=True),
        )

    @property
    def instance_ids(self) -> tuple[str, ...]:
        """Stable identifiers implied by the role-level population declaration."""

        width = max(1, len(str(self.count - 1)))
        return tuple(f"{self.role}-{index:0{width}d}" for index in range(self.count))


@dataclass(frozen=True, slots=True)
class StateSpecification:
    """Initial aggregate variables and role-level accounts."""

    variables: Mapping[str, Any]
    accounts: Mapping[str, Mapping[str, Any]]

    def __post_init__(self) -> None:
        if not self.variables:
            raise ValueError("state variables must not be empty")
        if any(not name for name in self.variables):
            raise ValueError("state variable names must not be empty")
        if any(not role or not values for role, values in self.accounts.items()):
            raise ValueError("state accounts require nonempty role names and values")
        object.__setattr__(self, "variables", freeze_value(self.variables))
        object.__setattr__(self, "accounts", freeze_value(self.accounts))


@dataclass(frozen=True, slots=True)
class ConstraintsSpecification:
    """Named economic feasibility rules and their violation policy."""

    rules: tuple[str, ...]
    violation_policy: str = "reject_and_log"

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", _names(self.rules, "constraint rules"))
        if self.violation_policy not in {"reject_and_log", "raise"}:
            raise ValueError("unsupported constraint violation_policy")


@dataclass(frozen=True, slots=True)
class SchedulerSpecification:
    """Deterministic action-ordering declaration."""

    policy: str = "deterministic"
    priority: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.policy not in {"deterministic", "submission_order", "role_priority"}:
            raise ValueError("unsupported scheduler policy")
        object.__setattr__(
            self,
            "priority",
            _names(self.priority, "scheduler priority", allow_empty=True),
        )
        if self.policy == "role_priority" and not self.priority:
            raise ValueError("role_priority scheduler requires priority roles")


@dataclass(frozen=True, slots=True)
class MechanismSpecification:
    """Institutional clearing, pricing, and settlement declaration."""

    type: str
    participants: tuple[str, ...]
    input_actions: tuple[str, ...]
    pricing_rule: str
    settlement_rule: str

    def __post_init__(self) -> None:
        if not self.type:
            raise ValueError("mechanism type must not be empty")
        if not self.pricing_rule or not self.settlement_rule:
            raise ValueError("pricing_rule and settlement_rule must not be empty")
        object.__setattr__(
            self,
            "participants",
            _names(self.participants, "mechanism participants"),
        )
        object.__setattr__(
            self,
            "input_actions",
            _names(self.input_actions, "mechanism input_actions"),
        )


@dataclass(frozen=True, slots=True)
class EnvironmentSpecification:
    """State, feasibility, ordering, and mechanism blocks from Figure 11."""

    state: StateSpecification
    constraints: ConstraintsSpecification
    scheduler: SchedulerSpecification
    mechanism: MechanismSpecification


@dataclass(frozen=True, slots=True)
class UpdateSpecification:
    """Allow-listed adaptive targets and their feedback signals."""

    targets: tuple[str, ...]
    signals: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "targets", _names(self.targets, "update targets"))
        object.__setattr__(self, "signals", _names(self.signals, "update signals"))


@dataclass(frozen=True, slots=True)
class CoevolutionSpecification:
    """Bidirectional agent-environment update declaration from Figure 13."""

    agent_updates: UpdateSpecification
    environment_updates: UpdateSpecification

    def __post_init__(self) -> None:
        allowed_agent = {"belief", "memory", "policy", "state", "skills", "tools"}
        allowed_environment = {"mechanism_parameters", "rules", "information"}
        unknown_agent = set(self.agent_updates.targets).difference(allowed_agent)
        unknown_environment = set(self.environment_updates.targets).difference(
            allowed_environment
        )
        if unknown_agent:
            raise ValueError(f"unknown agent update targets: {sorted(unknown_agent)}")
        if unknown_environment:
            raise ValueError(
                f"unknown environment update targets: {sorted(unknown_environment)}"
            )


@dataclass(frozen=True, slots=True)
class DataSourcesSpecification:
    """Named external streams and retrieval frequency."""

    streams: tuple[str, ...]
    frequency: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "streams", _names(self.streams, "data streams"))
        if not self.frequency:
            raise ValueError("data frequency must not be empty")


@dataclass(frozen=True, slots=True)
class CorrectionSpecification:
    """Allow-listed bounded correction targets."""

    agent_targets: tuple[str, ...]
    environment_targets: tuple[str, ...]
    policy: str
    max_delta: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "agent_targets",
            _names(self.agent_targets, "correction agent_targets", allow_empty=True),
        )
        object.__setattr__(
            self,
            "environment_targets",
            _names(
                self.environment_targets,
                "correction environment_targets",
                allow_empty=True,
            ),
        )
        if not self.agent_targets and not self.environment_targets:
            raise ValueError("correction requires at least one target")
        if self.policy != "bounded_update":
            raise ValueError("only bounded_update correction is supported")
        if not isfinite(self.max_delta) or self.max_delta <= 0.0:
            raise ValueError("correction max_delta must be finite and positive")


@dataclass(frozen=True, slots=True)
class AlignmentSpecification:
    """Evidence, discrepancy, tolerance, and correction blocks from Figure 15."""

    data_sources: DataSourcesSpecification
    targets: tuple[str, ...]
    metrics: tuple[str, ...]
    tolerance: Mapping[str, float]
    correction: CorrectionSpecification

    def __post_init__(self) -> None:
        object.__setattr__(self, "targets", _names(self.targets, "alignment targets"))
        object.__setattr__(self, "metrics", _names(self.metrics, "alignment metrics"))
        if set(self.tolerance) != set(self.metrics):
            raise ValueError("alignment tolerance keys must equal metric names")
        if any(
            not isfinite(value) or value < 0.0 for value in self.tolerance.values()
        ):
            raise ValueError("alignment tolerances must be finite and non-negative")
        object.__setattr__(self, "tolerance", freeze_value(self.tolerance))


@dataclass(frozen=True, slots=True)
class EvaluationSpecification:
    """Trajectory metrics grouped by Han's five evaluation layers."""

    layers: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        allowed = {"agents", "environment", "coevolution", "alignment", "efficiency"}
        unknown = set(self.layers).difference(allowed)
        if unknown:
            raise ValueError(f"unknown evaluation layers: {sorted(unknown)}")
        normalized = {
            layer: _names(metrics, f"evaluation layer {layer!r}")
            for layer, metrics in self.layers.items()
        }
        object.__setattr__(self, "layers", freeze_value(normalized))


_RUNTIME_MECHANISMS = {
    ("batch_clearing", "uniform_clearing", "cash_asset_delivery"):
        "fx_uniform_batch_v1"
}


@dataclass(frozen=True, slots=True)
class WorldSpecification:
    """Validated assembly of Han's five specification interfaces."""

    name: str
    agents: tuple[AgentSpecification, ...]
    environment: EnvironmentSpecification
    coevolution: CoevolutionSpecification | None = None
    alignment: AlignmentSpecification | None = None
    evaluation: EvaluationSpecification | None = None
    roles: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("world specification name must not be empty")
        agents = tuple(self.agents)
        if not agents:
            raise ValueError("world specification requires agents")
        roles = _names(tuple(agent.role for agent in agents), "agent roles")
        object.__setattr__(self, "agents", agents)
        object.__setattr__(self, "roles", roles)

        unknown_participants = set(self.environment.mechanism.participants).difference(roles)
        if unknown_participants:
            raise ValueError(
                f"unknown mechanism participants: {sorted(unknown_participants)}"
            )
        missing_accounts = set(roles).difference(self.environment.state.accounts)
        if missing_accounts:
            raise ValueError(f"missing role accounts: {sorted(missing_accounts)}")
        available_actions = {
            action for agent_spec in agents for action in agent_spec.action_space
        }
        unknown_actions = set(self.environment.mechanism.input_actions).difference(
            available_actions
        )
        if unknown_actions:
            raise ValueError(f"unknown mechanism input actions: {sorted(unknown_actions)}")
        declared_constraints = set(self.environment.constraints.rules)
        missing_constraints = {
            constraint
            for agent_spec in agents
            for constraint in agent_spec.constraints
            if constraint not in declared_constraints
        }
        if missing_constraints:
            raise ValueError(
                f"agent constraints absent from environment: {sorted(missing_constraints)}"
            )
        if self.alignment is not None:
            unknown_targets = set(self.alignment.targets).difference(
                self.environment.state.variables
            )
            if unknown_targets:
                raise ValueError(f"unknown alignment targets: {sorted(unknown_targets)}")

    @property
    def runtime_mechanism(self) -> str:
        """Return the registered adapter or fail before unsupported execution."""

        mechanism = self.environment.mechanism
        key = (mechanism.type, mechanism.pricing_rule, mechanism.settlement_rule)
        try:
            return _RUNTIME_MECHANISMS[key]
        except KeyError as error:
            raise NotImplementedError(
                f"no runtime compiler for mechanism {mechanism.type!r} with "
                f"pricing {mechanism.pricing_rule!r} and settlement "
                f"{mechanism.settlement_rule!r}"
            ) from error


def agent(
    *,
    role: str,
    objective: str,
    state_variables: Sequence[str],
    information_channels: Mapping[str, Sequence[str]],
    action_space: Sequence[str],
    tools: Sequence[str] = (),
    constraints: Sequence[str] = (),
    memory_window: int = 0,
    count: int = 1,
    belief: str | None = None,
) -> AgentSpecification:
    """Construct one role-level agent specification."""

    return AgentSpecification(
        role=role,
        objective=objective,
        state_variables=tuple(state_variables),
        information_channels={key: tuple(value) for key, value in information_channels.items()},
        action_space=tuple(action_space),
        tools=tuple(tools),
        constraints=tuple(constraints),
        memory_window=memory_window,
        count=count,
        belief=belief,
    )


def state(
    *, variables: Mapping[str, Any], accounts: Mapping[str, Mapping[str, Any]]
) -> StateSpecification:
    """Construct an immutable initial-state specification."""

    return StateSpecification(variables=variables, accounts=accounts)


def constraints(
    *, rules: Sequence[str], violation_policy: str = "reject_and_log"
) -> ConstraintsSpecification:
    """Construct an economic-constraint specification."""

    return ConstraintsSpecification(tuple(rules), violation_policy)


def scheduler(
    *, policy: str = "deterministic", priority: Sequence[str] = ()
) -> SchedulerSpecification:
    """Construct a scheduler specification."""

    return SchedulerSpecification(policy=policy, priority=tuple(priority))


def mechanism(
    *,
    type: str,
    participants: Sequence[str],
    input_actions: Sequence[str],
    pricing_rule: str,
    settlement_rule: str,
) -> MechanismSpecification:
    """Construct a mechanism specification."""

    return MechanismSpecification(
        type=type,
        participants=tuple(participants),
        input_actions=tuple(input_actions),
        pricing_rule=pricing_rule,
        settlement_rule=settlement_rule,
    )


def environment(
    *,
    state: StateSpecification,
    constraints: ConstraintsSpecification,
    scheduler: SchedulerSpecification,
    mechanism: MechanismSpecification,
) -> EnvironmentSpecification:
    """Construct an environment specification."""

    return EnvironmentSpecification(state, constraints, scheduler, mechanism)


def agent_updates(
    *, targets: Sequence[str], signals: Sequence[str]
) -> UpdateSpecification:
    """Construct the agent side of a co-evolution declaration."""

    return UpdateSpecification(tuple(targets), tuple(signals))


def environment_updates(
    *, targets: Sequence[str], signals: Sequence[str]
) -> UpdateSpecification:
    """Construct the environment side of a co-evolution declaration."""

    return UpdateSpecification(tuple(targets), tuple(signals))


def coevolution(
    *,
    agent_updates: UpdateSpecification,
    environment_updates: UpdateSpecification,
) -> CoevolutionSpecification:
    """Construct a bidirectional co-evolution specification."""

    return CoevolutionSpecification(agent_updates, environment_updates)


def data_sources(
    *, streams: Sequence[str], frequency: str
) -> DataSourcesSpecification:
    """Construct an external-data-source declaration."""

    return DataSourcesSpecification(tuple(streams), frequency)


def correction(
    *,
    agent_targets: Sequence[str],
    environment_targets: Sequence[str],
    policy: str,
    max_delta: float = 0.1,
) -> CorrectionSpecification:
    """Construct a bounded correction declaration."""

    return CorrectionSpecification(
        tuple(agent_targets), tuple(environment_targets), policy, max_delta
    )


def alignment(
    *,
    data_sources: DataSourcesSpecification,
    targets: Sequence[str],
    metrics: Sequence[str],
    tolerance: Mapping[str, float],
    correction: CorrectionSpecification,
) -> AlignmentSpecification:
    """Construct an external-evidence alignment specification."""

    return AlignmentSpecification(
        data_sources,
        tuple(targets),
        tuple(metrics),
        tolerance,
        correction,
    )


def evaluation(
    *, layers: Mapping[str, Sequence[str]]
) -> EvaluationSpecification:
    """Construct a layered trajectory-evaluation specification."""

    return EvaluationSpecification(
        {layer: tuple(metrics) for layer, metrics in layers.items()}
    )
