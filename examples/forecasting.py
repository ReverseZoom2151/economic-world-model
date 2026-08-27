"""Find the three DDGEs in the strong-feedback forecasting laboratory."""

from __future__ import annotations

import numpy as np

import ewm
from ewm.equilibrium import FixedPointConfig
from ewm.scenarios.forecasting import paper_replication_report


def main() -> None:
    scenario = ewm.make("forecasting", preset="smoke", seed=42)
    result = ewm.solve_ddge(
        scenario.ddge_problem(),
        (np.array([-1.5]), np.array([0.0]), np.array([1.5])),
        FixedPointConfig(tolerance=1e-9, max_iterations=500),
    )
    points = tuple(sorted(result.fixed_points, key=lambda point: point.theta[0]))

    assert len(points) == 3
    assert tuple(point.stable for point in points) == (True, False, True)
    for point in points:
        print(
            f"theta={point.theta[0]: .8f}  residual={point.residual_norm:.2e}  "
            f"stable={point.stable}  spectral_radius={point.spectral_radius:.6f}"
        )

    paper = paper_replication_report(seed=42, rounds=2, damping=0.5)
    assert abs(paper.population_roots[2] - 0.795) < 0.003
    print(
        f"paper_outer_root={paper.population_roots[2]:.8f}  "
        f"momentum_acf={paper.momentum_autocorrelation:.6f}  "
        f"zero_acf={paper.zero_autocorrelation:.6f}"
    )


if __name__ == "__main__":
    main()
