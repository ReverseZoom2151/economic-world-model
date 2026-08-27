"""Find the three DDGEs in the strong-feedback forecasting laboratory."""

from __future__ import annotations

import numpy as np

import ewm
from ewm.equilibrium import FixedPointConfig


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


if __name__ == "__main__":
    main()
