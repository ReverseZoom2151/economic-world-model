"""Build a cobweb DDGE using only the public EWM interfaces."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

import ewm
from ewm.core import (
    Action,
    ConstraintSet,
    FunctionalAgent,
    FunctionalConstraint,
    FunctionalMechanism,
    World,
)
from ewm.equilibrium import FixedPointConfig


@dataclass(frozen=True, slots=True)
class CobwebConfig:
    """Linear demand and forecast-conditioned supply parameters."""

    demand_intercept: float = 10.0
    demand_slope: float = 2.0
    supply_intercept: float = 1.0
    supply_slope: float = 1.0

    def __post_init__(self) -> None:
        if self.demand_slope <= 0.0 or self.supply_slope < 0.0:
            raise ValueError("demand slope must be positive and supply slope non-negative")
        if self.demand_intercept <= self.supply_intercept:
            raise ValueError("the demand intercept must exceed the supply intercept")

    @property
    def theoretical_theta(self) -> float:
        """Return the rational-expectations price for the linear economy."""

        return (self.demand_intercept - self.supply_intercept) / (
            self.demand_slope + self.supply_slope
        )


@dataclass(frozen=True, slots=True)
class CobwebState:
    """Expected price and the most recent market allocation."""

    expected_price: float
    price: float = 0.0
    quantity: float = 0.0


def make_cobweb_world(expected_price: float, config: CobwebConfig) -> World:
    """Compose an external economy from public agents, constraints, and mechanisms."""

    def consumer_policy(
        _state: CobwebState,
        _rng: np.random.Generator,
    ) -> Action:
        return Action(
            "consumer",
            "demand_schedule",
            {
                "intercept": config.demand_intercept,
                "slope": config.demand_slope,
            },
        )

    def producer_policy(
        state: CobwebState,
        _rng: np.random.Generator,
    ) -> Action:
        quantity = config.supply_intercept + config.supply_slope * state.expected_price
        return Action("producer", "supply", {"quantity": quantity})

    def schedule_is_feasible(_state: CobwebState, action: Action) -> str | None:
        if action.kind == "supply" and float(action.values["quantity"]) < 0.0:
            return "supply must be non-negative"
        if action.kind == "demand_schedule":
            if float(action.values["intercept"]) <= 0.0:
                return "demand intercept must be positive"
            if float(action.values["slope"]) <= 0.0:
                return "demand slope must be positive"
        return None

    def clear_market(
        state: CobwebState,
        actions: tuple[Action, ...],
        _rng: np.random.Generator,
    ) -> tuple[CobwebState, dict[str, float]]:
        by_kind = {action.kind: action for action in actions}
        demand = by_kind["demand_schedule"]
        supply = float(by_kind["supply"].values["quantity"])
        price = (float(demand.values["intercept"]) - supply) / float(demand.values["slope"])
        if price <= 0.0:
            raise ValueError("the submitted schedules imply a non-positive price")
        next_state = CobwebState(
            expected_price=state.expected_price,
            price=price,
            quantity=supply,
        )
        demand_quantity = float(demand.values["intercept"]) - float(demand.values["slope"]) * price
        return next_state, {
            "price": price,
            "quantity": supply,
            "clearing_residual": demand_quantity - supply,
        }

    return World(
        initial_state=lambda _rng: CobwebState(expected_price=expected_price),
        agents=(
            FunctionalAgent("consumer", consumer_policy),
            FunctionalAgent("producer", producer_policy),
        ),
        constraints=ConstraintSet(
            (FunctionalConstraint("feasible_schedule", schedule_is_feasible),)
        ),
        mechanism=FunctionalMechanism(clear_market),
    )


@dataclass(frozen=True, slots=True)
class CobwebProblem:
    """Naive price retraining map induced by one market-clearing transition."""

    config: CobwebConfig

    @property
    def dimension(self) -> int:
        return 1

    def update(
        self,
        theta: NDArray[np.floating[Any]],
    ) -> NDArray[np.floating[Any]]:
        if theta.shape != (1,):
            raise ValueError("theta must be a one-dimensional price forecast")
        world = make_cobweb_world(float(theta[0]), self.config)
        state = world.reset(seed=0)
        transition = world.step(state, world.run_agents(state))
        return np.asarray([transition.outcomes["price"]], dtype=float)


def solve_cobweb(config: CobwebConfig) -> tuple[float, float, float, bool, float]:
    """Solve the expectation-market-learning closure for one declared regime."""

    result = ewm.solve_ddge(
        CobwebProblem(config),
        (np.array([0.0]), np.array([4.0]), np.array([6.0])),
        FixedPointConfig(tolerance=1e-12, max_iterations=200),
    )
    assert len(result.fixed_points) == 1
    point = result.fixed_points[0]
    assert point.stable is not None
    assert point.spectral_radius is not None
    theta = float(point.theta[0])

    world = make_cobweb_world(theta, config)
    state = world.reset(seed=0)
    transition = world.step(state, world.run_agents(state))
    price = float(transition.outcomes["price"])
    quantity = float(transition.outcomes["quantity"])
    residual = float(transition.outcomes["clearing_residual"])

    assert np.isclose(theta, config.theoretical_theta, atol=1e-10)
    assert np.isclose(price, theta, atol=1e-10)
    assert abs(residual) < 1e-12
    return theta, price, quantity, point.stable, point.spectral_radius


def main() -> None:
    baseline = CobwebConfig()
    regimes = (
        ("baseline", baseline),
        (
            "demand_intervention",
            replace(baseline, demand_intercept=13.0),
        ),
    )
    for name, config in regimes:
        theta, price, quantity, stable, radius = solve_cobweb(config)
        print(
            f"{name} theta={theta:.6f} price={price:.6f} "
            f"quantity={quantity:.6f} stable={stable} "
            f"spectral_radius={radius:.6f}"
        )


if __name__ == "__main__":
    main()
