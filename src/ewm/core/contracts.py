"""Strict execution contracts for worlds compiled from declarations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from .records import Action

SchedulerPolicy = Literal["deterministic", "submission_order", "role_priority"]
ViolationPolicy = Literal["reject_and_log", "raise"]


@dataclass(frozen=True, slots=True)
class RuntimeContract:
    """Immutable agent, action, scheduling, and violation rules for one runtime."""

    agent_roles: Mapping[str, str]
    action_kinds: Mapping[str, frozenset[str]]
    scheduler_policy: SchedulerPolicy = "deterministic"
    scheduler_priority: tuple[str, ...] = ()
    violation_policy: ViolationPolicy = "reject_and_log"

    def __post_init__(self) -> None:
        agent_roles = dict(self.agent_roles)
        action_kinds = {
            agent_id: frozenset(kinds) for agent_id, kinds in self.action_kinds.items()
        }
        if not agent_roles:
            raise ValueError("runtime contract requires declared agents")
        if any(not agent_id or not role for agent_id, role in agent_roles.items()):
            raise ValueError("runtime contract agent identifiers and roles must not be empty")
        if set(action_kinds) != set(agent_roles):
            raise ValueError("runtime contract action owners must exactly match declared agents")
        if any(not kinds or any(not kind for kind in kinds) for kinds in action_kinds.values()):
            raise ValueError("runtime contract action kinds must not be empty")
        if self.scheduler_policy not in {
            "deterministic",
            "submission_order",
            "role_priority",
        }:
            raise ValueError(f"unsupported runtime scheduler {self.scheduler_policy!r}")
        priority = tuple(self.scheduler_priority)
        if len(priority) != len(set(priority)) or any(not role for role in priority):
            raise ValueError("runtime scheduler priority roles must be nonempty and unique")
        unknown_priority = sorted(set(priority).difference(agent_roles.values()))
        if unknown_priority:
            raise ValueError(
                f"runtime scheduler priority has unknown roles: {unknown_priority}"
            )
        if self.scheduler_policy == "role_priority" and not priority:
            raise ValueError("role_priority runtime scheduler requires priority roles")
        if self.violation_policy not in {"reject_and_log", "raise"}:
            raise ValueError(
                f"unsupported runtime violation policy {self.violation_policy!r}"
            )
        object.__setattr__(
            self,
            "agent_roles",
            MappingProxyType(dict(sorted(agent_roles.items()))),
        )
        object.__setattr__(
            self,
            "action_kinds",
            MappingProxyType(dict(sorted(action_kinds.items()))),
        )
        object.__setattr__(self, "scheduler_priority", priority)

    def validate_agent_action(self, action: Action, *, owner_id: str) -> None:
        """Require one policy result to belong to its declared agent and action space."""

        if action.agent_id != owner_id:
            raise ValueError(
                f"agent {owner_id!r} returned action for {action.agent_id!r}"
            )
        self._validate_action(action)

    def validate_actions(self, actions: tuple[Action, ...]) -> None:
        """Validate ownership, kinds, and at-most-one action per declared agent."""

        seen: set[str] = set()
        for action in actions:
            self._validate_action(action)
            if action.agent_id in seen:
                raise ValueError(
                    f"agent {action.agent_id!r} submitted multiple actions in one step"
                )
            seen.add(action.agent_id)

    def _validate_action(self, action: Action) -> None:
        try:
            allowed = self.action_kinds[action.agent_id]
        except KeyError as error:
            raise ValueError(
                f"action references unknown agent {action.agent_id!r}"
            ) from error
        if action.kind not in allowed:
            raise ValueError(
                f"action kind {action.kind!r} is not declared for agent "
                f"{action.agent_id!r}"
            )

    def schedule(self, actions: tuple[Action, ...]) -> tuple[Action, ...]:
        """Apply the specification's deterministic scheduling boundary."""

        if self.scheduler_policy == "submission_order":
            return actions
        if self.scheduler_policy == "role_priority":
            ranks = {
                role: index for index, role in enumerate(self.scheduler_priority)
            }
            unprioritized = len(ranks)
            return tuple(
                sorted(
                    actions,
                    key=lambda action: (
                        ranks.get(self.agent_roles[action.agent_id], unprioritized),
                        self.agent_roles[action.agent_id],
                        action.agent_id,
                        action.kind,
                    ),
                )
            )
        return tuple(sorted(actions, key=lambda action: (action.agent_id, action.kind)))
