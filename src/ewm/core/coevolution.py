"""Controlled bidirectional adaptation for agents and economic environments."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from math import isfinite
from typing import Any

from .records import (
    Action,
    CoevolutionProposal,
    CoevolutionReport,
    CoevolutionSnapshot,
    CoevolutionUpdate,
)
from .specs import CoevolutionSpecification

ProposalRule = Callable[
    [Any, tuple[Action, ...], Any, CoevolutionSnapshot],
    tuple[CoevolutionProposal, ...],
]


def _finite_components(
    values: Mapping[str, float],
    label: str,
) -> dict[str, float]:
    result = {name: float(value) for name, value in values.items()}
    if any(not name for name in result):
        raise ValueError(f"{label} names must not be empty")
    if any(not isfinite(value) for value in result.values()):
        raise ValueError(f"{label} values must be finite")
    return result


def _positive_bounds(values: Mapping[str, float], label: str) -> dict[str, float]:
    result = _finite_components(values, label)
    if any(value <= 0.0 for value in result.values()):
        raise ValueError(f"{label} must be positive")
    return result


class ControlledCoevolution:
    """Apply allow-listed, bounded proposals atomically to adaptive component state."""

    def __init__(
        self,
        *,
        specification: CoevolutionSpecification,
        agent_components: Mapping[str, Mapping[str, float]],
        environment_components: Mapping[str, float],
        agent_bounds: Mapping[str, float],
        environment_bounds: Mapping[str, float],
        proposal_rule: ProposalRule,
    ) -> None:
        if not agent_components:
            raise ValueError("controlled coevolution requires agent components")
        self._specification = specification
        self._agent_components = {
            owner_id: _finite_components(components, f"agent {owner_id!r} components")
            for owner_id, components in agent_components.items()
        }
        if any(not owner_id for owner_id in self._agent_components):
            raise ValueError("coevolution agent identifiers must not be empty")
        self._environment_components = _finite_components(
            environment_components, "environment components"
        )
        self._agent_bounds = _positive_bounds(agent_bounds, "agent bounds")
        self._environment_bounds = _positive_bounds(
            environment_bounds, "environment bounds"
        )
        self._proposal_rule = proposal_rule
        self._version = 0

    @property
    def version(self) -> int:
        return self._version

    @property
    def agent_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._agent_components))

    @property
    def snapshot(self) -> CoevolutionSnapshot:
        """Return an immutable copy of the current controlled component state."""

        return CoevolutionSnapshot(
            version=self._version,
            agent_components=self._agent_components,
            environment_components=self._environment_components,
        )

    def _validated_update(
        self,
        proposal: CoevolutionProposal,
    ) -> CoevolutionUpdate:
        if proposal.scope == "agent":
            declared_targets = set(self._specification.agent_updates.targets)
            declared_signals = set(self._specification.agent_updates.signals)
            if proposal.target not in declared_targets:
                raise ValueError(f"undeclared agent target {proposal.target!r}")
            if proposal.signal not in declared_signals:
                raise ValueError(f"undeclared agent signal {proposal.signal!r}")
            assert proposal.owner_id is not None
            try:
                components = self._agent_components[proposal.owner_id]
            except KeyError as error:
                raise ValueError(
                    f"unknown coevolution agent {proposal.owner_id!r}"
                ) from error
            if proposal.target not in components:
                raise ValueError(
                    f"agent {proposal.owner_id!r} has no component {proposal.target!r}"
                )
            try:
                bound = self._agent_bounds[proposal.target]
            except KeyError as error:
                raise ValueError(
                    f"agent target {proposal.target!r} has no update bound"
                ) from error
            before = components[proposal.target]
        else:
            declared_targets = set(self._specification.environment_updates.targets)
            declared_signals = set(self._specification.environment_updates.signals)
            if proposal.target not in declared_targets:
                raise ValueError(f"undeclared environment target {proposal.target!r}")
            if proposal.signal not in declared_signals:
                raise ValueError(f"undeclared environment signal {proposal.signal!r}")
            if proposal.target not in self._environment_components:
                raise ValueError(
                    f"environment has no component {proposal.target!r}"
                )
            try:
                bound = self._environment_bounds[proposal.target]
            except KeyError as error:
                raise ValueError(
                    f"environment target {proposal.target!r} has no update bound"
                ) from error
            before = self._environment_components[proposal.target]

        if abs(proposal.delta) > bound:
            raise ValueError(
                f"update delta {proposal.delta} exceeds bound {bound} for "
                f"{proposal.target!r}"
            )
        after = before + proposal.delta
        if not isfinite(after):
            raise ValueError("coevolution update produced a non-finite component")
        return CoevolutionUpdate(
            scope=proposal.scope,
            owner_id=proposal.owner_id,
            target=proposal.target,
            signal=proposal.signal,
            before=before,
            delta=proposal.delta,
            after=after,
            bound=bound,
            normalized_delta=abs(proposal.delta) / bound,
        )

    def evolve(
        self,
        state: Any,
        actions: tuple[Action, ...],
        next_state: Any,
    ) -> CoevolutionReport:
        """Validate all proposals, then commit the complete update atomically."""

        before = self.snapshot
        proposals = tuple(self._proposal_rule(state, tuple(actions), next_state, before))
        keys = tuple((item.scope, item.owner_id, item.target) for item in proposals)
        if len(keys) != len(set(keys)):
            raise ValueError("coevolution proposals must target distinct components")
        updates = tuple(self._validated_update(proposal) for proposal in proposals)
        signals: dict[str, float] = {}
        for proposal in proposals:
            prior = signals.get(proposal.signal)
            if prior is not None and prior != proposal.signal_value:
                raise ValueError(
                    f"conflicting values for coevolution signal {proposal.signal!r}"
                )
            signals[proposal.signal] = proposal.signal_value

        agent_components = {
            owner_id: dict(components)
            for owner_id, components in self._agent_components.items()
        }
        environment_components = dict(self._environment_components)
        for update in updates:
            if update.scope == "agent":
                assert update.owner_id is not None
                agent_components[update.owner_id][update.target] = update.after
            else:
                environment_components[update.target] = update.after

        if updates:
            self._agent_components = agent_components
            self._environment_components = environment_components
            self._version += 1
        max_normalized = max(
            (update.normalized_delta for update in updates),
            default=0.0,
        )
        return CoevolutionReport(
            before_version=before.version,
            after_version=self._version,
            signals=dict(sorted(signals.items())),
            updates=updates,
            max_normalized_delta=max_normalized,
        )
