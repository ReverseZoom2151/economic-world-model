"""Ridge-logistic lender and endogenous borrower adoption."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression

from ..economy.population import CreditPopulation, assemble_features, generate_population
from ..economy.presets import CreditConfig


@dataclass(frozen=True, slots=True)
class CreditModel:
    """Explicit intercept and coefficient vector for lender screening."""

    intercept: float
    coefficients: NDArray[np.float64]

    def __post_init__(self) -> None:
        coefficients = np.array(self.coefficients, dtype=float, copy=True)
        if coefficients.ndim != 1 or not np.all(np.isfinite(coefficients)):
            raise ValueError("credit coefficients must be a finite vector")
        coefficients.setflags(write=False)
        object.__setattr__(self, "coefficients", coefficients)

    def to_vector(self) -> NDArray[np.float64]:
        return np.concatenate(([self.intercept], self.coefficients))

    @classmethod
    def from_vector(cls, theta: NDArray[np.floating]) -> CreditModel:
        candidate = np.asarray(theta, dtype=float)
        if candidate.ndim != 1 or candidate.size < 2:
            raise ValueError("credit model vector must contain an intercept and coefficients")
        return cls(float(candidate[0]), candidate[1:])

    def predict_probability(self, features: NDArray[np.floating]) -> NDArray[np.float64]:
        values = np.asarray(features, dtype=float)
        logits = self.intercept + values @ self.coefficients
        return 1.0 / (1.0 + np.exp(-np.clip(logits, -40.0, 40.0)))

    def approve(
        self,
        features: NDArray[np.floating],
        config: CreditConfig,
    ) -> NDArray[np.bool_]:
        return self.predict_probability(features) >= config.approval_threshold


def fit_credit_model(
    features: NDArray[np.floating],
    repayment: NDArray[np.bool_],
    *,
    ridge: float,
) -> CreditModel:
    """Fit a deterministic ridge-logistic model, including one-class fallback."""

    values = np.asarray(features, dtype=float)
    labels = np.asarray(repayment, dtype=bool)
    if values.ndim != 2 or labels.shape != (values.shape[0],):
        raise ValueError("credit training features and labels have incompatible shapes")
    if values.shape[0] < 2:
        raise ValueError("at least two observed borrowers are required")
    rate = float((labels.sum() + 0.5) / (labels.size + 1.0))
    if np.unique(labels).size == 1:
        return CreditModel(
            intercept=float(np.log(rate / (1.0 - rate))),
            coefficients=np.zeros(values.shape[1]),
        )
    estimator = LogisticRegression(
        C=1.0 / ridge,
        solver="lbfgs",
        fit_intercept=True,
        max_iter=500,
        tol=1e-9,
        random_state=0,
    )
    estimator.fit(values, labels)
    return CreditModel(
        intercept=float(estimator.intercept_[0]),
        coefficients=np.asarray(estimator.coef_[0], dtype=float),
    )


def fit_initial_model(config: CreditConfig) -> CreditModel:
    """Fit the pre-intervention lender on an independent historical cohort."""

    historical = generate_population(config, seed=config.seed + 10_000)
    features = assemble_features(
        historical, np.zeros(historical.size, dtype=bool)
    )
    return fit_credit_model(
        features,
        historical.potential_repayment,
        ridge=config.ridge,
    )


def adoption_mask(
    population: CreditPopulation,
    model: CreditModel,
    config: CreditConfig,
) -> NDArray[np.bool_]:
    """Adopt only when cosmetic rewriting flips a decision and covers its cost."""

    original = assemble_features(population, np.zeros(population.size, dtype=bool))
    polished = assemble_features(population, np.ones(population.size, dtype=bool))
    original_approval = model.approve(original, config)
    polished_approval = model.approve(polished, config)
    affordable = population.adoption_cost <= config.loan_benefit
    return (~original_approval) & polished_approval & affordable


def omniscient_approvals(
    population: CreditPopulation, config: CreditConfig
) -> NDArray[np.bool_]:
    """Approve from structural repayment probability, which polish cannot change."""

    return population.repayment_probability >= config.approval_threshold
