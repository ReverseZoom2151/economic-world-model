"""Configurations for the synthetic AI-mediated credit laboratory."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreditConfig:
    """Population, lending, adoption, and retraining parameters."""

    population_size: int = 1_200
    seed: int = 314
    structured_features: int = 10
    text_features: int = 15
    structured_signal: float = 0.75
    text_signal: float = 0.55
    feature_noise: float = 1.0
    repayment_intercept: float = 0.35
    repayment_quality_slope: float = 1.25
    polish_shift: float = 1.5
    adoption_cost_max: float = 1.0
    loan_benefit: float = 0.8
    repayment_gain: float = 0.35
    default_loss: float = 1.0
    ridge: float = 2.0
    retraining_damping: float = 0.35
    ddge_tolerance: float = 1e-3
    ddge_max_iterations: int = 150

    def __post_init__(self) -> None:
        if self.population_size < 100:
            raise ValueError("population_size must be at least 100")
        if self.structured_features != 10 or self.text_features != 15:
            raise ValueError("version 0.1 fixes ten structured and fifteen text features")
        if self.feature_noise <= 0.0:
            raise ValueError("feature_noise must be positive")
        if self.polish_shift < 0.0:
            raise ValueError("polish_shift must be non-negative")
        if self.adoption_cost_max <= 0.0 or self.loan_benefit < 0.0:
            raise ValueError("adoption costs must be positive and benefit non-negative")
        if self.repayment_gain <= 0.0 or self.default_loss <= 0.0:
            raise ValueError("lending payoffs must be positive")
        if self.ridge <= 0.0:
            raise ValueError("ridge must be positive")
        if not 0.0 < self.retraining_damping <= 1.0:
            raise ValueError("retraining_damping must lie in (0, 1]")
        if self.ddge_tolerance <= 0.0 or self.ddge_max_iterations < 1:
            raise ValueError("DDGE tolerances and iterations must be positive")

    @property
    def approval_threshold(self) -> float:
        """Break-even repayment probability under the declared lending payoffs."""

        return self.default_loss / (self.repayment_gain + self.default_loss)

    @property
    def feature_count(self) -> int:
        return self.structured_features + self.text_features


def paper_like_config(*, population_size: int = 1_200) -> CreditConfig:
    """Return the named configuration used for prespecified qualitative hypotheses."""

    return CreditConfig(
        population_size=population_size,
        seed=303,
        ddge_max_iterations=200,
    )


def research_config(*, population_size: int = 10_000) -> CreditConfig:
    """Return a larger population configuration for reported experiments."""

    return CreditConfig(population_size=population_size, ddge_tolerance=5e-4)
