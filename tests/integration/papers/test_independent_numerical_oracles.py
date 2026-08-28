"""Integration contracts for independent numerical oracles."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest
from ewm.experiments.production import solve_production_equilibrium

from ewm.equilibrium import FixedPointConfig, local_linear_certificate, solve_ddge
from ewm.scenarios.forecasting import paper_config, paper_population_roots, population_update
from ewm.scenarios.production import package_authored_example
from ewm.scenarios.scalar import ScalarConfig, ScalarLearner, ScalarProblem, outer_update
from tests.oracles.forecasting_oracle import (
    FORECASTING_ORACLE_SCOPE,
    forecasting_population_roots,
    stationary_kernel_ols_update,
)
from tests.oracles.linear_algebra_oracle import right_singular_direction_expansion
from tests.oracles.production_oracle import solve_direct_production_oracle
from tests.oracles.scalar_oracle import (
    analytical_root_count,
    direct_paper_update,
    scalar_bracketed_roots,
)

ROOT = Path(__file__).parents[3]
SCALAR_UPDATE_ATOL = 1e-14
SCALAR_ROOT_ATOL = 1e-9
FORECASTING_MAP_ATOL = 4e-3
FORECASTING_ROOT_ATOL = 4e-3
PRODUCTION_PRICE_ATOL = 2e-5


def test_oracle_modules_have_an_ast_enforced_package_import_boundary() -> None:
    violations: list[str] = []
    for path in sorted((ROOT / "tests" / "oracles").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "ewm" or alias.name.startswith("ewm."):
                        violations.append(f"{path.name}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "ewm" or module.startswith("ewm."):
                    violations.append(f"{path.name}:{node.lineno} imports {module}")

    assert not violations, "oracle independence violations:\n" + "\n".join(violations)


def test_scalar_direct_equation_and_bracketing_match_iterative_package_solver() -> None:
    inner_feedback = 0.5
    learning_gain = 0.8
    config = ScalarConfig(
        kappa=inner_feedback,
        gamma=1.0,
        learning_gain=learning_gain,
        learner=ScalarLearner.TANH,
    )

    for theta in np.linspace(-0.8, 0.8, 17):
        assert direct_paper_update(
            float(theta),
            inner_feedback=inner_feedback,
            learning_gain=learning_gain,
        ) == pytest.approx(outer_update(float(theta), config), abs=SCALAR_UPDATE_ATOL)

    oracle_roots = scalar_bracketed_roots(
        inner_feedback=inner_feedback,
        learning_gain=learning_gain,
        tolerance=1e-13,
    )
    iterative = solve_ddge(
        ScalarProblem(config),
        tuple(np.array([value]) for value in (-1.0, 0.0, 1.0)),
        FixedPointConfig(tolerance=1e-12, max_iterations=10_000),
    )
    iterative_roots = tuple(
        sorted(float(point.theta[0]) for point in iterative.fixed_points)
    )

    assert analytical_root_count(config.composite_gain) == 3
    assert len(oracle_roots) == analytical_root_count(config.composite_gain)
    assert np.allclose(oracle_roots, iterative_roots, atol=SCALAR_ROOT_ATOL)


@pytest.mark.parametrize(
    ("composite_gain", "expected"),
    [(0.8, 1), (1.0, 1), (1.01, 3), (1.6, 3)],
)
def test_scalar_analytical_root_count_is_prespecified(
    composite_gain: float,
    expected: int,
) -> None:
    assert analytical_root_count(composite_gain) == expected


def test_forecasting_stationary_kernel_ols_cross_checks_population_only() -> None:
    config = paper_config()
    comparisons = []
    for theta in (0.25, 0.6, 0.795):
        oracle = stationary_kernel_ols_update(
            theta,
            feedback=1.8,
            noise_std=0.5,
            grid_bound=4.0,
            grid_size=321,
            stationary_tolerance=1e-13,
        )
        comparisons.append((oracle.update, population_update(theta, config)))
        assert oracle.stationary_residual <= 1e-12
        assert oracle.scope == FORECASTING_ORACLE_SCOPE

    assert FORECASTING_ORACLE_SCOPE == "population_stationary_kernel_ols_only"
    assert all(
        abs(oracle_update - package_update) <= FORECASTING_MAP_ATOL
        for oracle_update, package_update in comparisons
    )

    oracle_roots = forecasting_population_roots(
        feedback=1.8,
        noise_std=0.5,
        grid_bound=4.0,
        grid_size=321,
        stationary_tolerance=1e-13,
    )
    package_roots = paper_population_roots(config)
    assert np.allclose(oracle_roots, package_roots, atol=FORECASTING_ROOT_ATOL)


def test_production_objective_optimization_cross_checks_package_authored_instance() -> None:
    oracle = solve_direct_production_oracle()
    package = solve_production_equilibrium(
        package_authored_example(),
        initial_rental_rate=0.08,
        initial_wage=1.0,
    )

    assert oracle.scope == "package_authored_instance_not_paper_target"
    assert oracle.market_residual_norm <= 1e-8
    assert oracle.maximum_budget_residual <= 1e-10
    assert oracle.maximum_optimizer_gradient <= 2e-5
    assert oracle.rental_rate == pytest.approx(
        package.rental_rate,
        abs=PRODUCTION_PRICE_ATOL,
    )
    assert oracle.wage == pytest.approx(package.wage, abs=PRODUCTION_PRICE_ATOL)


def test_right_singular_direction_witnesses_non_contraction_not_instability() -> None:
    matrix = np.array([[0.0, 2.0], [0.0, 0.0]])
    oracle = right_singular_direction_expansion(matrix)
    package = local_linear_certificate(matrix)

    assert oracle.method == "eigenvector_of_transpose_times_matrix_then_direct_norm"
    assert oracle.input_norm == pytest.approx(1.0, abs=1e-14)
    assert oracle.expansion_ratio == pytest.approx(2.0, abs=1e-12)
    assert np.linalg.norm(matrix @ oracle.right_direction) == pytest.approx(
        oracle.expansion_ratio,
        abs=1e-12,
    )
    assert package.maximum_singular_value == pytest.approx(
        oracle.expansion_ratio,
        abs=1e-12,
    )
    assert package.singular_value_non_contraction
    assert package.spectrally_stable
