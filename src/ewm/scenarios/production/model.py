"""Disclosed package instantiation of Cong's Appendix D equilibrium template.

Cong supplies household budgets, a borrowing bound, firm optimality, distributional
state, and capital and labor clearing in Equations (D.1)-(D.7). The functional forms,
parameters, finite distribution, and continuation-value closure below are authored by
this package so the incomplete template can be executed and tested.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import exp, isfinite, log, sqrt
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import brentq

from ewm.core import EquilibriumResult

PACKAGE_AUTHORED_PRIMITIVES: Mapping[str, str] = MappingProxyType(
    {
        "preferences": "CRRA consumption utility with isoelastic labor disutility",
        "continuation_value": "shifted-asset CRRA continuation approximation",
        "labor_disutility": "idiosyncratic shock divides the labor-disutility weight",
        "capital_share": "Cobb-Douglas capital exponent",
        "labor_share": "Cobb-Douglas labor exponent",
        "productivity": "aggregate productivity level",
        "depreciation": "capital depreciation rate",
        "borrowing_bound": "common lower bound on next-period assets",
        "household_distribution": "finite weighted asset and preference-shock support",
    }
)


@dataclass(frozen=True, slots=True)
class ProductionPrimitives:
    """Package-authored preferences and technology completing Appendix D."""

    risk_aversion: float = 1.0
    labor_disutility: float = 1.5
    labor_curvature: float = 1.0
    continuation_weight: float = 0.25
    capital_share: float = 0.30
    labor_share: float = 0.55
    productivity: float = 1.0
    depreciation: float = 0.08
    borrowing_bound: float = 0.0

    def __post_init__(self) -> None:
        positive = {
            "risk_aversion": self.risk_aversion,
            "labor_disutility": self.labor_disutility,
            "labor_curvature": self.labor_curvature,
            "continuation_weight": self.continuation_weight,
            "capital_share": self.capital_share,
            "labor_share": self.labor_share,
            "productivity": self.productivity,
        }
        if any(not isfinite(value) or value <= 0.0 for value in positive.values()):
            raise ValueError("production preference and technology values must be positive")
        if self.capital_share + self.labor_share >= 1.0:
            raise ValueError("Cobb-Douglas exponents must sum to less than one")
        if not isfinite(self.depreciation) or not 0.0 <= self.depreciation < 1.0:
            raise ValueError("depreciation must lie in [0, 1)")
        if not isfinite(self.borrowing_bound):
            raise ValueError("borrowing_bound must be finite")


@dataclass(frozen=True, slots=True)
class DistributionState:
    """Finite transparent approximation to Cong's cross-sectional distribution mu."""

    assets: tuple[float, ...]
    shocks: tuple[float, ...]
    weights: tuple[float, ...]

    def __post_init__(self) -> None:
        assets = tuple(float(value) for value in self.assets)
        shocks = tuple(float(value) for value in self.shocks)
        weights = tuple(float(value) for value in self.weights)
        if not assets or len(assets) != len(shocks) or len(assets) != len(weights):
            raise ValueError("distribution assets, shocks, and weights must align")
        if any(not isfinite(value) for value in assets):
            raise ValueError("distribution assets must be finite")
        if any(not isfinite(value) or value <= 0.0 for value in shocks):
            raise ValueError("distribution shocks must be finite and positive")
        if any(not isfinite(value) or value <= 0.0 for value in weights):
            raise ValueError("distribution weights must be finite and positive")
        if abs(sum(weights) - 1.0) > 1e-12:
            raise ValueError("distribution weights must sum to one")
        object.__setattr__(self, "assets", assets)
        object.__setattr__(self, "shocks", shocks)
        object.__setattr__(self, "weights", weights)


@dataclass(frozen=True, slots=True)
class HouseholdDecision:
    """One household type's feasible interior decision and optimality diagnostics."""

    current_assets: float
    shock: float
    weight: float
    consumption: float
    labor: float
    next_assets: float
    utility: float
    budget_residual: float
    savings_foc_residual: float
    labor_foc_residual: float


@dataclass(frozen=True, slots=True)
class FirmDecision:
    """Closed-form Cobb-Douglas factor demand and first-order diagnostics."""

    capital: float
    labor: float
    output: float
    profit: float
    capital_foc_residual: float
    labor_foc_residual: float


@dataclass(frozen=True, slots=True)
class ProductionEquilibrium:
    """Prices, allocations, market residuals, and disclosed numerical status."""

    rental_rate: float
    wage: float
    households: tuple[HouseholdDecision, ...]
    firm: FirmDecision
    aggregate_assets: float
    aggregate_labor: float
    capital_clearing_residual: float
    labor_clearing_residual: float
    converged: bool
    residual_norm: float
    iterations: int
    message: str

    @property
    def max_budget_residual(self) -> float:
        return max(abs(item.budget_residual) for item in self.households)

    @property
    def max_household_foc_residual(self) -> float:
        return max(
            max(abs(item.savings_foc_residual), abs(item.labor_foc_residual))
            for item in self.households
        )


class ProductionEconomy:
    """One-period competitive equilibrium over a transparent household distribution."""

    def __init__(
        self,
        *,
        primitives: ProductionPrimitives,
        distribution: DistributionState,
    ) -> None:
        if any(asset < primitives.borrowing_bound for asset in distribution.assets):
            raise ValueError("current household assets violate the borrowing bound")
        self._primitives = primitives
        self._distribution = distribution

    @property
    def primitives(self) -> ProductionPrimitives:
        return self._primitives

    @property
    def distribution(self) -> DistributionState:
        return self._distribution

    @property
    def package_authored_primitives(self) -> Mapping[str, str]:
        return PACKAGE_AUTHORED_PRIMITIVES

    def household_decisions(
        self,
        *,
        rental_rate: float,
        wage: float,
    ) -> tuple[HouseholdDecision, ...]:
        """Solve every household's interior FOCs under the Appendix D budget."""

        self._validate_prices(rental_rate, wage)
        return tuple(
            self._household_decision(
                current_assets=asset,
                shock=shock,
                weight=weight,
                rental_rate=rental_rate,
                wage=wage,
            )
            for asset, shock, weight in zip(
                self._distribution.assets,
                self._distribution.shocks,
                self._distribution.weights,
                strict=True,
            )
        )

    def firm_decision(self, *, rental_rate: float, wage: float) -> FirmDecision:
        """Evaluate closed-form factor demand from the two firm FOCs."""

        self._validate_prices(rental_rate, wage)
        primitives = self._primitives
        user_cost = rental_rate + primitives.depreciation
        alpha = primitives.capital_share
        gamma = primitives.labor_share
        determinant = 1.0 - alpha - gamma
        capital_rhs = log(user_cost / (alpha * primitives.productivity))
        labor_rhs = log(wage / (gamma * primitives.productivity))
        log_capital = (
            (gamma - 1.0) * capital_rhs - gamma * labor_rhs
        ) / determinant
        log_labor = (
            -alpha * capital_rhs + (alpha - 1.0) * labor_rhs
        ) / determinant
        capital = exp(log_capital)
        labor = exp(log_labor)
        output = primitives.productivity * capital**alpha * labor**gamma
        capital_marginal_product = alpha * output / capital
        labor_marginal_product = gamma * output / labor
        profit = output - user_cost * capital - wage * labor
        return FirmDecision(
            capital=capital,
            labor=labor,
            output=output,
            profit=profit,
            capital_foc_residual=capital_marginal_product - user_cost,
            labor_foc_residual=labor_marginal_product - wage,
        )

    def residual(self, candidate: NDArray[np.floating]) -> NDArray[np.float64]:
        """Capital and labor excess demand in transformed positive price coordinates."""

        log_prices = np.asarray(candidate, dtype=float)
        if log_prices.shape != (2,) or not np.all(np.isfinite(log_prices)):
            raise ValueError("production price candidate must have two finite values")
        rental_rate = exp(float(log_prices[0])) - self._primitives.depreciation
        wage = exp(float(log_prices[1]))
        households = self.household_decisions(
            rental_rate=rental_rate,
            wage=wage,
        )
        firm = self.firm_decision(rental_rate=rental_rate, wage=wage)
        assets = sum(
            weight * asset
            for asset, weight in zip(
                self._distribution.assets,
                self._distribution.weights,
                strict=True,
            )
        )
        labor = sum(item.weight * item.labor for item in households)
        return np.array([firm.capital - assets, firm.labor - labor], dtype=float)

    def initial_price_candidate(
        self,
        *,
        initial_rental_rate: float,
        initial_wage: float,
    ) -> NDArray[np.float64]:
        """Transform an economic price guess into the solver's positive coordinates."""

        self._validate_prices(initial_rental_rate, initial_wage)
        return np.array(
            [
                log(initial_rental_rate + self._primitives.depreciation),
                log(initial_wage),
            ],
            dtype=np.float64,
        )

    def equilibrium_from_result(
        self,
        numerical: EquilibriumResult,
    ) -> ProductionEquilibrium:
        """Convert a generic numerical result into economic allocations and checks."""

        if numerical.solution.shape != (2,):
            raise ValueError("production equilibrium result must contain two log prices")
        rental_rate = exp(float(numerical.solution[0])) - self._primitives.depreciation
        wage = exp(float(numerical.solution[1]))
        households = self.household_decisions(
            rental_rate=rental_rate,
            wage=wage,
        )
        firm = self.firm_decision(rental_rate=rental_rate, wage=wage)
        aggregate_assets = sum(
            weight * asset
            for asset, weight in zip(
                self._distribution.assets,
                self._distribution.weights,
                strict=True,
            )
        )
        aggregate_labor = sum(item.weight * item.labor for item in households)
        return ProductionEquilibrium(
            rental_rate=rental_rate,
            wage=wage,
            households=households,
            firm=firm,
            aggregate_assets=aggregate_assets,
            aggregate_labor=aggregate_labor,
            capital_clearing_residual=firm.capital - aggregate_assets,
            labor_clearing_residual=firm.labor - aggregate_labor,
            converged=numerical.converged,
            residual_norm=numerical.residual_norm,
            iterations=numerical.iterations,
            message=numerical.message,
        )

    def _household_decision(
        self,
        *,
        current_assets: float,
        shock: float,
        weight: float,
        rental_rate: float,
        wage: float,
    ) -> HouseholdDecision:
        primitives = self._primitives
        savings_ratio = primitives.continuation_weight ** (
            1.0 / primitives.risk_aversion
        )
        shifted_resources = (
            (1.0 + rental_rate) * current_assets - primitives.borrowing_bound
        )
        labor_weight = primitives.labor_disutility / shock

        if primitives.risk_aversion == 1.0 and primitives.labor_curvature == 1.0:
            coefficient_a = labor_weight * wage
            coefficient_b = labor_weight * shifted_resources
            coefficient_c = -wage * (1.0 + savings_ratio)
            discriminant = coefficient_b**2 - 4.0 * coefficient_a * coefficient_c
            labor = (-coefficient_b + sqrt(discriminant)) / (2.0 * coefficient_a)
        else:
            lower = max(0.0, -shifted_resources / wage) + 1e-12

            def labor_foc(candidate: float) -> float:
                consumption = (
                    wage * candidate + shifted_resources
                ) / (1.0 + savings_ratio)
                return float(
                    labor_weight * candidate**primitives.labor_curvature
                    - wage * consumption ** (-primitives.risk_aversion)
                )

            upper = max(1.0, lower * 2.0)
            while labor_foc(upper) <= 0.0:
                upper *= 2.0
                if upper > 1e8:
                    raise RuntimeError("failed to bracket household labor choice")
            labor = float(brentq(labor_foc, lower, upper))

        consumption = (
            wage * labor + shifted_resources
        ) / (1.0 + savings_ratio)
        next_assets = primitives.borrowing_bound + savings_ratio * consumption
        budget_residual = (
            consumption
            + next_assets
            - wage * labor
            - (1.0 + rental_rate) * current_assets
        )
        consumption_marginal_utility = consumption ** (-primitives.risk_aversion)
        continuation_resources = next_assets - primitives.borrowing_bound
        continuation_marginal_value = (
            primitives.continuation_weight
            * continuation_resources ** (-primitives.risk_aversion)
        )
        savings_foc_residual = (
            consumption_marginal_utility - continuation_marginal_value
        )
        labor_foc_residual = (
            wage * consumption_marginal_utility
            - labor_weight * labor**primitives.labor_curvature
        )
        utility = (
            _crra(consumption, primitives.risk_aversion)
            + primitives.continuation_weight
            * _crra(continuation_resources, primitives.risk_aversion)
            - labor_weight
            * labor ** (1.0 + primitives.labor_curvature)
            / (1.0 + primitives.labor_curvature)
        )
        return HouseholdDecision(
            current_assets=current_assets,
            shock=shock,
            weight=weight,
            consumption=consumption,
            labor=labor,
            next_assets=next_assets,
            utility=utility,
            budget_residual=budget_residual,
            savings_foc_residual=savings_foc_residual,
            labor_foc_residual=labor_foc_residual,
        )

    def _validate_prices(self, rental_rate: float, wage: float) -> None:
        if not isfinite(rental_rate) or not isfinite(wage):
            raise ValueError("production prices must be finite")
        if rental_rate + self._primitives.depreciation <= 0.0:
            raise ValueError("capital user cost must be positive")
        if 1.0 + rental_rate <= 0.0:
            raise ValueError("gross household asset return must be positive")
        if wage <= 0.0:
            raise ValueError("wage must be positive")


def _crra(value: float, risk_aversion: float) -> float:
    if value <= 0.0:
        raise ValueError("CRRA argument must be positive")
    if risk_aversion == 1.0:
        return log(value)
    return float(value ** (1.0 - risk_aversion) / (1.0 - risk_aversion))


def package_authored_example() -> ProductionEconomy:
    """Return the documented tractable instance used by tests and examples."""

    return ProductionEconomy(
        primitives=ProductionPrimitives(),
        distribution=DistributionState(
            assets=(0.20, 0.80, 1.60),
            shocks=(0.75, 1.00, 1.35),
            weights=(0.30, 0.40, 0.30),
        ),
    )
