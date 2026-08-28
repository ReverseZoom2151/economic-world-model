"""Inner-equilibrium and Data-Driven Generative Equilibrium solvers."""

from ewm._internal.imports import register_module_aliases

from .analysis.certificates import (
    AffinePolyhedralCertificate,
    LocalLinearCertificate,
    ObligationStatus,
    TheoremObligation,
    affine_polyhedral_certificate,
    local_linear_certificate,
)
from .analysis.correspondence import EquilibriumCorrespondence
from .analysis.diagnostics import (
    CenterDisplacementCertificate,
    FrozenCounterfactualBounds,
    OuterContractionCertificate,
    PosterioriWelfareBounds,
    TransitionRobustnessBounds,
    finite_difference_jacobian,
    fixed_point_residual,
    fragility_upper_bound,
    frozen_counterfactual_bounds,
    linear_center_displacement,
    local_modulus,
    outer_contraction_certificate,
    posteriori_distance_bound,
    posteriori_welfare_bounds,
    spectral_radius,
    transition_robustness_bounds,
)
from .solvers.damping import (
    DampingStabilityCertificate,
    damped_eigenvalue,
    damped_update,
    damping_stability_certificate,
)
from .solvers.ddge import solve_ddge
from .solvers.fixed_point import FixedPointConfig, iterate_fixed_point, solve_multistart
from .solvers.inner import solve_equilibrium

register_module_aliases(
    __name__,
    {
        "certificates": "analysis.certificates",
        "correspondence": "analysis.correspondence",
        "damping": "solvers.damping",
        "ddge": "solvers.ddge",
        "diagnostics": "analysis.diagnostics",
        "fixed_point": "solvers.fixed_point",
        "inner": "solvers.inner",
    },
)

__all__ = [
    "AffinePolyhedralCertificate",
    "CenterDisplacementCertificate",
    "DampingStabilityCertificate",
    "EquilibriumCorrespondence",
    "FixedPointConfig",
    "FrozenCounterfactualBounds",
    "LocalLinearCertificate",
    "ObligationStatus",
    "OuterContractionCertificate",
    "PosterioriWelfareBounds",
    "TheoremObligation",
    "TransitionRobustnessBounds",
    "affine_polyhedral_certificate",
    "damped_eigenvalue",
    "damped_update",
    "damping_stability_certificate",
    "finite_difference_jacobian",
    "fixed_point_residual",
    "fragility_upper_bound",
    "frozen_counterfactual_bounds",
    "iterate_fixed_point",
    "linear_center_displacement",
    "local_linear_certificate",
    "local_modulus",
    "outer_contraction_certificate",
    "posteriori_distance_bound",
    "posteriori_welfare_bounds",
    "solve_ddge",
    "solve_equilibrium",
    "solve_multistart",
    "spectral_radius",
    "transition_robustness_bounds",
]
