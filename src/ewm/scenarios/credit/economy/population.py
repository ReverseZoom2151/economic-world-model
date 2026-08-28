"""Synthetic borrowers, potential outcomes, and cosmetic text intervention."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .presets import CreditConfig


def _readonly_float(values: NDArray[np.floating]) -> NDArray[np.float64]:
    result = np.array(values, dtype=float, copy=True)
    result.setflags(write=False)
    return result


def _readonly_bool(values: NDArray[np.bool_]) -> NDArray[np.bool_]:
    result = np.array(values, dtype=bool, copy=True)
    result.setflags(write=False)
    return result


@dataclass(frozen=True, slots=True)
class CreditPopulation:
    """Borrower cohort with immutable features and common potential outcomes."""

    quality: NDArray[np.float64]
    structured: NDArray[np.float64]
    text: NDArray[np.float64]
    polished_text: NDArray[np.float64]
    polish_direction: NDArray[np.float64]
    adoption_cost: NDArray[np.float64]
    repayment_probability: NDArray[np.float64]
    potential_repayment: NDArray[np.bool_]

    def __post_init__(self) -> None:
        object.__setattr__(self, "quality", _readonly_float(self.quality))
        object.__setattr__(self, "structured", _readonly_float(self.structured))
        object.__setattr__(self, "text", _readonly_float(self.text))
        object.__setattr__(self, "polished_text", _readonly_float(self.polished_text))
        object.__setattr__(self, "polish_direction", _readonly_float(self.polish_direction))
        object.__setattr__(self, "adoption_cost", _readonly_float(self.adoption_cost))
        object.__setattr__(
            self,
            "repayment_probability",
            _readonly_float(self.repayment_probability),
        )
        object.__setattr__(
            self,
            "potential_repayment",
            _readonly_bool(self.potential_repayment),
        )

    @property
    def size(self) -> int:
        return int(self.quality.size)


def _sigmoid(value: NDArray[np.float64]) -> NDArray[np.float64]:
    return 1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0)))


def generate_population(
    config: CreditConfig,
    *,
    seed: int | None = None,
) -> CreditPopulation:
    """Generate one cohort with common repayment draws across all regimes."""

    rng = np.random.default_rng(config.seed if seed is None else seed)
    quality = rng.normal(size=config.population_size)
    structured_loadings = np.linspace(
        config.structured_signal,
        0.4 * config.structured_signal,
        config.structured_features,
    )
    text_loadings = np.linspace(
        config.text_signal,
        0.35 * config.text_signal,
        config.text_features,
    )
    structured = (
        quality[:, None] * structured_loadings
        + config.feature_noise
        * rng.normal(size=(config.population_size, config.structured_features))
    )
    text = (
        quality[:, None] * text_loadings
        + config.feature_noise
        * rng.normal(size=(config.population_size, config.text_features))
    )
    polish_direction = text_loadings / np.linalg.norm(text_loadings)
    polished_text = text + config.polish_shift * polish_direction
    adoption_cost = rng.uniform(0.0, config.adoption_cost_max, config.population_size)
    repayment_probability = _sigmoid(
        config.repayment_intercept + config.repayment_quality_slope * quality
    )
    repayment_uniform = rng.uniform(size=config.population_size)
    potential_repayment = repayment_uniform < repayment_probability
    return CreditPopulation(
        quality=quality,
        structured=structured,
        text=text,
        polished_text=polished_text,
        polish_direction=polish_direction,
        adoption_cost=adoption_cost,
        repayment_probability=repayment_probability,
        potential_repayment=potential_repayment,
    )


def assemble_features(
    population: CreditPopulation,
    adoption: NDArray[np.bool_],
) -> NDArray[np.float64]:
    """Assemble observed features without mutating borrower primitives or outcomes."""

    adopted = np.asarray(adoption, dtype=bool)
    if adopted.shape != (population.size,):
        raise ValueError("adoption mask has the wrong shape")
    observed_text = np.where(
        adopted[:, None], population.polished_text, population.text
    )
    return np.column_stack((population.structured, observed_text))
