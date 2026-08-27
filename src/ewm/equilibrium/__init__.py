"""Inner-equilibrium and Data-Driven Generative Equilibrium solvers."""

from .damping import damped_eigenvalue, damped_update
from .ddge import solve_ddge
from .diagnostics import (
    finite_difference_jacobian,
    fixed_point_residual,
    local_modulus,
    posteriori_distance_bound,
    spectral_radius,
)
from .fixed_point import FixedPointConfig, iterate_fixed_point, solve_multistart
from .inner import solve_equilibrium

__all__ = [
    "FixedPointConfig",
    "damped_eigenvalue",
    "damped_update",
    "finite_difference_jacobian",
    "fixed_point_residual",
    "iterate_fixed_point",
    "local_modulus",
    "posteriori_distance_bound",
    "solve_ddge",
    "solve_equilibrium",
    "solve_multistart",
    "spectral_radius",
]
