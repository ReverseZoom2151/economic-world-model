"""Backend-independent economic mechanism implementations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from .records import Action


@dataclass(frozen=True, slots=True)
class FunctionalMechanism:
    """An institutional mechanism backed by a pure-ish transition function."""

    clearing_function: Callable[
        [Any, tuple[Action, ...], np.random.Generator],
        tuple[Any, Mapping[str, Any]],
    ]

    def clear(
        self,
        state: Any,
        actions: tuple[Action, ...],
        rng: np.random.Generator,
    ) -> tuple[Any, Mapping[str, Any]]:
        return self.clearing_function(state, actions, rng)
