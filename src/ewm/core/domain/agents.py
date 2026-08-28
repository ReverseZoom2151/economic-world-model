"""Backend-independent economic agent implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from .records import Action


@dataclass(frozen=True, slots=True)
class FunctionalAgent:
    """An economic agent backed by a plain policy function."""

    agent_id: str
    policy: Callable[[Any, np.random.Generator], Action]

    def act(self, observation: Any, rng: np.random.Generator) -> Action:
        action = self.policy(observation, rng)
        if action.agent_id != self.agent_id:
            raise ValueError(
                f"policy for {self.agent_id!r} returned action for {action.agent_id!r}"
            )
        return action
