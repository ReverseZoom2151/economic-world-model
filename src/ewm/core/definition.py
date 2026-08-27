"""Declarative objects for Cong's Economic World Model definition."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


def _owned_names(
    values: tuple[str, ...], label: str, *, allow_empty: bool = True
) -> tuple[str, ...]:
    owned = tuple(values)
    if not allow_empty and not owned:
        raise ValueError(f"{label} must not be empty")
    if any(not value for value in owned):
        raise ValueError(f"{label} must not contain empty names")
    if len(owned) != len(set(owned)):
        raise ValueError(f"{label} must be unique")
    return owned


@dataclass(frozen=True, slots=True)
class SpaceDefinition:
    """A named economic state, action, outcome, or intervention space."""

    name: str
    description: str
    elements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("space name must not be empty")
        if not self.description:
            raise ValueError("space description must not be empty")
        object.__setattr__(self, "elements", _owned_names(self.elements, "space elements"))


@dataclass(frozen=True, slots=True)
class AgentBlock:
    """One agent's information, admissible policies, and beliefs."""

    agent_id: str
    information: tuple[str, ...]
    policies: tuple[str, ...]
    beliefs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id must not be empty")
        object.__setattr__(
            self,
            "information",
            _owned_names(self.information, "agent information", allow_empty=False),
        )
        object.__setattr__(
            self,
            "policies",
            _owned_names(self.policies, "agent policies", allow_empty=False),
        )
        object.__setattr__(
            self,
            "beliefs",
            _owned_names(self.beliefs, "agent beliefs", allow_empty=False),
        )


class CoherenceKind(StrEnum):
    """The three coherence classes distinguished in Cong's framework."""

    HARD_EQUALITY = "hard_equality"
    INEQUALITY = "inequality"
    SOFT = "soft"


@dataclass(frozen=True, slots=True)
class CoherenceCondition:
    """A named economic equality, inequality, or diagnostic condition."""

    name: str
    kind: CoherenceKind
    expression: str
    tolerance: float | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("coherence condition name must not be empty")
        if not self.expression:
            raise ValueError("coherence expression must not be empty")
        if self.tolerance is not None and self.tolerance < 0.0:
            raise ValueError("coherence tolerance must be non-negative")


@dataclass(frozen=True, slots=True)
class KernelDefinition:
    """A declared transition or observation object, learned or analytical."""

    name: str
    inputs: tuple[str, ...]
    output: str
    parameter: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("kernel name must not be empty")
        object.__setattr__(
            self,
            "inputs",
            _owned_names(self.inputs, "kernel inputs", allow_empty=False),
        )
        if not self.output:
            raise ValueError("kernel output must not be empty")
        if self.parameter == "":
            raise ValueError("kernel parameter must not be empty")

    @property
    def learned(self) -> bool:
        """Whether the declared object depends on a learned parameter block."""

        return self.parameter is not None


class WorldComponent(StrEnum):
    """EWM components that an intervention may transform."""

    STATE_SPACE = "state_space"
    ACTION_SPACE = "action_space"
    OUTCOME_SPACE = "outcome_space"
    FEASIBILITY = "feasibility"
    INFORMATION = "information"
    POLICIES = "policies"
    BELIEFS = "beliefs"
    COHERENCE = "coherence"
    TRANSITION = "transition"
    OBSERVATION = "observation"
    OBJECTIVES = "objectives"
    CONSTRAINTS = "constraints"


@dataclass(frozen=True, slots=True)
class InterventionSemantics:
    """A typed declaration of which EWM blocks a regime changes."""

    intervention: str
    modifies: frozenset[WorldComponent]
    description: str

    def __post_init__(self) -> None:
        if not self.intervention:
            raise ValueError("intervention name must not be empty")
        if not self.description:
            raise ValueError("intervention description must not be empty")
        object.__setattr__(self, "modifies", frozenset(self.modifies))


@dataclass(frozen=True, slots=True)
class EconomicWorldModelDefinition:
    """The full tuple in Cong's Definition 2.6 as validated named blocks."""

    state_space: SpaceDefinition
    action_space: SpaceDefinition
    outcome_space: SpaceDefinition
    intervention_space: SpaceDefinition
    number_of_agents: int
    agents: tuple[AgentBlock, ...]
    coherence_conditions: tuple[CoherenceCondition, ...]
    transition_kernel: KernelDefinition
    observation_kernel: KernelDefinition
    intervention_semantics: tuple[InterventionSemantics, ...]

    def __post_init__(self) -> None:
        agents = tuple(self.agents)
        conditions = tuple(self.coherence_conditions)
        semantics = tuple(self.intervention_semantics)
        object.__setattr__(self, "agents", agents)
        object.__setattr__(self, "coherence_conditions", conditions)
        object.__setattr__(self, "intervention_semantics", semantics)

        if self.number_of_agents < 1:
            raise ValueError("number_of_agents must be positive")
        if self.number_of_agents != len(agents):
            raise ValueError("number_of_agents must equal the number of agent blocks")
        _owned_names(
            tuple(agent.agent_id for agent in agents),
            "agent identifiers",
            allow_empty=False,
        )
        _owned_names(
            tuple(condition.name for condition in conditions),
            "coherence condition names",
        )
        semantic_names = _owned_names(
            tuple(item.intervention for item in semantics),
            "intervention semantic names",
        )

        declared = set(self.intervention_space.elements)
        if declared:
            missing = declared.difference(semantic_names)
            unknown = set(semantic_names).difference(declared)
            if missing:
                raise ValueError(f"missing intervention semantics: {sorted(missing)}")
            if unknown:
                raise ValueError(f"semantics declared for unknown interventions: {sorted(unknown)}")

    @property
    def agent_ids(self) -> tuple[str, ...]:
        """Agent identifiers in declared order."""

        return tuple(agent.agent_id for agent in self.agents)

    @property
    def hard_coherence(self) -> tuple[CoherenceCondition, ...]:
        """Conditions that must hold as exact equalities or by construction."""

        return tuple(
            item for item in self.coherence_conditions if item.kind is CoherenceKind.HARD_EQUALITY
        )

    @property
    def inequality_coherence(self) -> tuple[CoherenceCondition, ...]:
        """Declared economic inequality and support restrictions."""

        return tuple(
            item for item in self.coherence_conditions if item.kind is CoherenceKind.INEQUALITY
        )

    @property
    def soft_coherence(self) -> tuple[CoherenceCondition, ...]:
        """Conditions reported through diagnostics or penalties."""

        return tuple(item for item in self.coherence_conditions if item.kind is CoherenceKind.SOFT)

    def intervention(self, name: str) -> InterventionSemantics:
        """Return the declared transformation semantics for one regime."""

        for semantics in self.intervention_semantics:
            if semantics.intervention == name:
                return semantics
        raise KeyError(f"unknown intervention {name!r}")
