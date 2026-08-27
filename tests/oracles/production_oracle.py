"""Direct objective-optimization oracle for the package-authored production instance."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares, minimize
from scipy.special import expit

RISK_AVERSION = 1.0
LABOR_DISUTILITY = 1.5
LABOR_CURVATURE = 1.0
CONTINUATION_WEIGHT = 0.25
CAPITAL_SHARE = 0.30
LABOR_SHARE = 0.55
PRODUCTIVITY = 1.0
DEPRECIATION = 0.08
BORROWING_BOUND = 0.0
ASSETS = np.array([0.20, 0.80, 1.60])
SHOCKS = np.array([0.75, 1.00, 1.35])
WEIGHTS = np.array([0.30, 0.40, 0.30])


@dataclass(frozen=True, slots=True)
class _HouseholdOptimum:
    labor: float
    consumption: float
    next_assets: float
    budget_residual: float
    gradient_norm: float


@dataclass(frozen=True, slots=True)
class _FirmOptimum:
    capital: float
    labor: float
    gradient_norm: float


@dataclass(frozen=True, slots=True)
class ProductionOracleResult:
    """Prices and independent optimizer residuals for one disclosed package instance."""

    rental_rate: float
    wage: float
    market_residual_norm: float
    maximum_budget_residual: float
    maximum_optimizer_gradient: float
    scope: str = "package_authored_instance_not_paper_target"


def _household_optimum(
    *,
    current_assets: float,
    shock: float,
    rental_rate: float,
    wage: float,
) -> _HouseholdOptimum:
    labor_weight = LABOR_DISUTILITY / shock

    def allocation(candidate: NDArray[np.float64]) -> tuple[float, float, float, float]:
        labor = exp(float(candidate[0]))
        saving_fraction = float(expit(candidate[1]))
        resources = (1.0 + rental_rate) * current_assets + wage * labor
        next_assets = BORROWING_BOUND + saving_fraction * (
            resources - BORROWING_BOUND
        )
        consumption = resources - next_assets
        return labor, consumption, next_assets, resources

    def negative_objective(candidate: NDArray[np.float64]) -> float:
        labor, consumption, next_assets, _resources = allocation(candidate)
        continuation_resources = next_assets - BORROWING_BOUND
        utility = (
            log(consumption)
            + CONTINUATION_WEIGHT * log(continuation_resources)
            - labor_weight * labor ** (1.0 + LABOR_CURVATURE)
            / (1.0 + LABOR_CURVATURE)
        )
        return -utility

    def negative_objective_gradient(
        candidate: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        labor, _consumption, _next_assets, resources = allocation(candidate)
        saving_fraction = float(expit(candidate[1]))
        labor_gradient = (
            (1.0 + CONTINUATION_WEIGHT) * wage * labor / resources
            - labor_weight * labor ** (1.0 + LABOR_CURVATURE)
        )
        saving_gradient = CONTINUATION_WEIGHT - (
            1.0 + CONTINUATION_WEIGHT
        ) * saving_fraction
        return -np.array([labor_gradient, saving_gradient])

    solved = minimize(
        negative_objective,
        np.array([log(0.5), log(CONTINUATION_WEIGHT)]),
        jac=negative_objective_gradient,
        method="L-BFGS-B",
        bounds=((-12.0, 4.0), (-12.0, 12.0)),
        options={
            "ftol": 1e-12,
            "gtol": 1e-8,
            "maxiter": 2_000,
            "maxls": 50,
        },
    )
    if not solved.success or solved.jac is None:
        raise RuntimeError(f"household objective optimization failed: {solved.message}")
    labor, consumption, next_assets, resources = allocation(solved.x)
    return _HouseholdOptimum(
        labor=labor,
        consumption=consumption,
        next_assets=next_assets,
        budget_residual=consumption + next_assets - resources,
        gradient_norm=float(np.linalg.norm(solved.jac, ord=np.inf)),
    )


def _firm_optimum(*, rental_rate: float, wage: float) -> _FirmOptimum:
    user_cost = rental_rate + DEPRECIATION

    def negative_profit(candidate: NDArray[np.float64]) -> float:
        capital = exp(float(candidate[0]))
        labor = exp(float(candidate[1]))
        output = PRODUCTIVITY * capital**CAPITAL_SHARE * labor**LABOR_SHARE
        return -(output - user_cost * capital - wage * labor)

    def negative_profit_gradient(
        candidate: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        capital = exp(float(candidate[0]))
        labor = exp(float(candidate[1]))
        output = PRODUCTIVITY * capital**CAPITAL_SHARE * labor**LABOR_SHARE
        return -np.array(
            [
                CAPITAL_SHARE * output - user_cost * capital,
                LABOR_SHARE * output - wage * labor,
            ]
        )

    solved = minimize(
        negative_profit,
        np.log(np.array([float(WEIGHTS @ ASSETS), 1.0])),
        jac=negative_profit_gradient,
        method="L-BFGS-B",
        bounds=((-12.0, 8.0), (-12.0, 8.0)),
        options={
            "ftol": 1e-12,
            "gtol": 1e-8,
            "maxiter": 2_000,
            "maxls": 50,
        },
    )
    if not solved.success or solved.jac is None:
        raise RuntimeError(f"firm objective optimization failed: {solved.message}")
    return _FirmOptimum(
        capital=exp(float(solved.x[0])),
        labor=exp(float(solved.x[1])),
        gradient_norm=float(np.linalg.norm(solved.jac, ord=np.inf)),
    )


def _allocations(
    log_prices: NDArray[np.float64],
) -> tuple[tuple[_HouseholdOptimum, ...], _FirmOptimum, float, float]:
    rental_rate = exp(float(log_prices[0])) - DEPRECIATION
    wage = exp(float(log_prices[1]))
    households = tuple(
        _household_optimum(
            current_assets=float(asset),
            shock=float(shock),
            rental_rate=rental_rate,
            wage=wage,
        )
        for asset, shock in zip(ASSETS, SHOCKS, strict=True)
    )
    firm = _firm_optimum(rental_rate=rental_rate, wage=wage)
    return households, firm, rental_rate, wage


def solve_direct_production_oracle() -> ProductionOracleResult:
    """Clear both markets using direct household and firm objective optimizers."""

    aggregate_assets = float(WEIGHTS @ ASSETS)

    def market_residual(log_prices: NDArray[np.float64]) -> NDArray[np.float64]:
        households, firm, _rental_rate, _wage = _allocations(log_prices)
        aggregate_labor = sum(
            float(weight) * household.labor
            for weight, household in zip(WEIGHTS, households, strict=True)
        )
        return np.array(
            [firm.capital - aggregate_assets, firm.labor - aggregate_labor]
        )

    solved = least_squares(
        market_residual,
        np.log(np.array([0.08 + DEPRECIATION, 1.0])),
        bounds=(np.log(np.array([0.03, 0.05])), np.log(np.array([5.0, 5.0]))),
        ftol=1e-12,
        xtol=1e-12,
        gtol=1e-12,
        diff_step=1e-2,
        max_nfev=200,
    )
    if not solved.success:
        raise RuntimeError(f"market-clearing optimization failed: {solved.message}")
    households, firm, rental_rate, wage = _allocations(solved.x)
    residual = market_residual(solved.x)
    return ProductionOracleResult(
        rental_rate=rental_rate,
        wage=wage,
        market_residual_norm=float(np.linalg.norm(residual, ord=np.inf)),
        maximum_budget_residual=max(
            abs(household.budget_residual) for household in households
        ),
        maximum_optimizer_gradient=max(
            firm.gradient_norm,
            *(household.gradient_norm for household in households),
        ),
    )
