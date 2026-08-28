"""Constructive theorem certificates for affine maps on polyhedra."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linprog


class ObligationStatus(StrEnum):
    """Status of one named mathematical proof obligation."""

    VERIFIED = "verified"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class TheoremObligation:
    """One assumption or conclusion with explicit provenance and residual."""

    name: str
    status: ObligationStatus
    provenance: str
    residual: float | None = None
    tolerance: float | None = None


@dataclass(frozen=True, slots=True)
class LocalLinearCertificate:
    """Separate Euclidean contraction and eigenvalue stability diagnostics."""

    maximum_singular_value: float
    spectral_radius: float
    euclidean_contraction: bool
    singular_value_non_contraction: bool
    spectrally_stable: bool


@dataclass(frozen=True, slots=True)
class AffinePolyhedralCertificate:
    """Constructive fixed-point certificate within a declared affine/polyhedral scope."""

    matrix: NDArray[np.float64]
    offset: NDArray[np.float64]
    constraint_matrix: NDArray[np.float64]
    constraint_bounds: NDArray[np.float64]
    fixed_point: NDArray[np.float64]
    fixed_point_residual: float
    maximum_linear_program_residual: float
    maximum_domain_violation: float
    maximum_self_map_violation: float
    tolerance: float
    linear_diagnostics: LocalLinearCertificate
    obligations: tuple[TheoremObligation, ...]

    def obligation(self, name: str) -> TheoremObligation:
        """Return one named obligation without silently accepting an absent check."""

        for obligation in self.obligations:
            if obligation.name == name:
                return obligation
        raise KeyError(name)

    @property
    def restricted_existence_certified(self) -> bool:
        """Whether the constructive fixed point and restricted assumptions all pass."""

        required = (
            "restricted:affine_map",
            "restricted:nonempty_compact_polyhedron",
            "restricted:linear_program_residuals",
            "restricted:self_map",
            "restricted:fixed_point_residual",
            "restricted:fixed_point_in_domain",
        )
        return all(
            self.obligation(name).status is ObligationStatus.VERIFIED
            for name in required
        )

    @property
    def restricted_uniqueness_certified(self) -> bool:
        """Whether restricted existence and Euclidean contraction both pass."""

        return (
            self.restricted_existence_certified
            and self.obligation("restricted:euclidean_contraction").status
            is ObligationStatus.VERIFIED
        )


def _readonly(value: NDArray[np.floating]) -> NDArray[np.float64]:
    result = np.array(value, dtype=float, copy=True)
    result.setflags(write=False)
    return result


def _matrix(value: NDArray[np.floating], name: str) -> NDArray[np.float64]:
    result = np.asarray(value, dtype=float)
    if result.ndim != 2 or 0 in result.shape:
        raise ValueError(f"{name} must be a nonempty two-dimensional array")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


def _vector(value: NDArray[np.floating], name: str) -> NDArray[np.float64]:
    result = np.asarray(value, dtype=float)
    if result.ndim != 1 or result.size == 0:
        raise ValueError(f"{name} must be a nonempty one-dimensional array")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


def _provenance(value: str, name: str) -> str:
    if not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value


def _tolerance(value: float) -> float:
    result = float(value)
    if not isfinite(result) or result <= 0.0:
        raise ValueError("tolerance must be finite and positive")
    return result


def local_linear_certificate(
    matrix: NDArray[np.floating],
) -> LocalLinearCertificate:
    """Diagnose a linearization without conflating singular values and eigenvalues."""

    linear_map = _matrix(matrix, "matrix")
    if linear_map.shape[0] != linear_map.shape[1]:
        raise ValueError("matrix must be square")
    maximum_singular_value = float(np.linalg.svd(linear_map, compute_uv=False)[0])
    radius = float(np.max(np.abs(np.linalg.eigvals(linear_map))))
    return LocalLinearCertificate(
        maximum_singular_value=maximum_singular_value,
        spectral_radius=radius,
        euclidean_contraction=maximum_singular_value < 1.0,
        singular_value_non_contraction=maximum_singular_value >= 1.0,
        spectrally_stable=radius < 1.0,
    )


def _verify_nonempty_bounded_polyhedron(
    constraint_matrix: NDArray[np.float64],
    constraint_bounds: NDArray[np.float64],
) -> float:
    dimension = constraint_matrix.shape[1]
    unrestricted = [(None, None)] * dimension
    feasibility = linprog(
        np.zeros(dimension),
        A_ub=constraint_matrix,
        b_ub=constraint_bounds,
        bounds=unrestricted,
        method="highs",
    )
    if feasibility.status == 2:
        raise ValueError("polyhedral domain must be nonempty")
    if not feasibility.success or feasibility.x is None or feasibility.fun is None:
        raise ValueError(f"polyhedral feasibility solver failed: {feasibility.message}")
    maximum_solver_residual = _linear_program_residual(
        point=feasibility.x,
        objective=np.zeros(dimension),
        reported_objective=float(feasibility.fun),
        constraint_matrix=constraint_matrix,
        constraint_bounds=constraint_bounds,
    )
    for coordinate in range(dimension):
        basis = np.zeros(dimension)
        basis[coordinate] = 1.0
        for objective in (basis, -basis):
            result = linprog(
                objective,
                A_ub=constraint_matrix,
                b_ub=constraint_bounds,
                bounds=unrestricted,
                method="highs",
            )
            if result.status == 3:
                raise ValueError("polyhedral domain must be bounded")
            if not result.success or result.x is None or result.fun is None:
                raise ValueError(f"polyhedral boundedness solver failed: {result.message}")
            maximum_solver_residual = max(
                maximum_solver_residual,
                _linear_program_residual(
                    point=result.x,
                    objective=objective,
                    reported_objective=float(result.fun),
                    constraint_matrix=constraint_matrix,
                    constraint_bounds=constraint_bounds,
                ),
            )
    return maximum_solver_residual


def _linear_program_residual(
    *,
    point: NDArray[np.floating],
    objective: NDArray[np.floating],
    reported_objective: float,
    constraint_matrix: NDArray[np.float64],
    constraint_bounds: NDArray[np.float64],
) -> float:
    primal_violation = max(
        0.0,
        float(np.max(constraint_matrix @ point - constraint_bounds)),
    )
    objective_residual = abs(float(objective @ point) - reported_objective)
    return max(primal_violation, objective_residual)


def _maximum_self_map_violation(
    matrix: NDArray[np.float64],
    offset: NDArray[np.float64],
    constraint_matrix: NDArray[np.float64],
    constraint_bounds: NDArray[np.float64],
) -> tuple[float, float]:
    dimension = matrix.shape[0]
    unrestricted = [(None, None)] * dimension
    violations: list[float] = []
    maximum_solver_residual = 0.0
    for row, bound in zip(constraint_matrix, constraint_bounds, strict=True):
        image_objective = row @ matrix
        result = linprog(
            -image_objective,
            A_ub=constraint_matrix,
            b_ub=constraint_bounds,
            bounds=unrestricted,
            method="highs",
        )
        if not result.success or result.x is None or result.fun is None:
            raise ValueError(f"self-map solver failed: {result.message}")
        maximum_solver_residual = max(
            maximum_solver_residual,
            _linear_program_residual(
                point=result.x,
                objective=-image_objective,
                reported_objective=float(result.fun),
                constraint_matrix=constraint_matrix,
                constraint_bounds=constraint_bounds,
            ),
        )
        maximum = float(image_objective @ result.x + row @ offset - bound)
        violations.append(maximum)
    return max(0.0, max(violations)), maximum_solver_residual


def affine_polyhedral_certificate(
    *,
    matrix: NDArray[np.floating],
    offset: NDArray[np.floating],
    constraint_matrix: NDArray[np.floating],
    constraint_bounds: NDArray[np.floating],
    map_provenance: str,
    domain_provenance: str,
    tolerance: float = 1e-10,
) -> AffinePolyhedralCertificate:
    """Certify only a declared affine map on a nonempty compact polyhedron.

    The domain is ``{x: constraint_matrix @ x <= constraint_bounds}``. Linear
    programs verify compactness and the self-map property globally on that domain.
    General set-valued Assumption 3.2 and Kakutani obligations remain blocked.
    """

    affine_matrix = _matrix(matrix, "matrix")
    affine_offset = _vector(offset, "offset")
    constraints = _matrix(constraint_matrix, "constraint_matrix")
    bounds = _vector(constraint_bounds, "constraint_bounds")
    map_source = _provenance(map_provenance, "map_provenance")
    domain_source = _provenance(domain_provenance, "domain_provenance")
    checked_tolerance = _tolerance(tolerance)
    dimension = affine_matrix.shape[0]
    if affine_matrix.shape != (dimension, dimension):
        raise ValueError("matrix must be square")
    if affine_offset.size != dimension:
        raise ValueError("matrix and offset dimensions must match")
    if constraints.shape[1] != dimension or bounds.size != constraints.shape[0]:
        raise ValueError("polyhedral constraints must match the affine-map dimension")

    domain_solver_residual = _verify_nonempty_bounded_polyhedron(constraints, bounds)
    self_map_violation, self_map_solver_residual = _maximum_self_map_violation(
        affine_matrix,
        affine_offset,
        constraints,
        bounds,
    )
    fixed_point = np.linalg.lstsq(
        np.eye(dimension) - affine_matrix,
        affine_offset,
        rcond=None,
    )[0]
    solve_residual = float(
        np.linalg.norm(
            (np.eye(dimension) - affine_matrix) @ fixed_point - affine_offset,
            ord=np.inf,
        )
    )
    domain_violation = max(
        0.0,
        float(np.max(constraints @ fixed_point - bounds)),
    )
    diagnostics = local_linear_certificate(affine_matrix)
    solver_source = "numpy.linalg.lstsq; residual recomputed by direct substitution"
    polyhedron_solver_source = (
        f"{domain_source}; scipy.optimize.linprog(method='highs')"
    )
    maximum_solver_residual = max(
        domain_solver_residual,
        self_map_solver_residual,
    )
    obligations = (
        TheoremObligation(
            "restricted:affine_map",
            ObligationStatus.VERIFIED,
            map_source,
        ),
        TheoremObligation(
            "restricted:nonempty_compact_polyhedron",
            ObligationStatus.VERIFIED,
            polyhedron_solver_source,
        ),
        TheoremObligation(
            "restricted:linear_program_residuals",
            (
                ObligationStatus.VERIFIED
                if maximum_solver_residual <= checked_tolerance
                else ObligationStatus.FAILED
            ),
            "scipy.optimize.linprog(method='highs'); primal feasibility and objective "
            "residuals recomputed from returned solutions",
            maximum_solver_residual,
            checked_tolerance,
        ),
        TheoremObligation(
            "restricted:self_map",
            (
                ObligationStatus.VERIFIED
                if self_map_violation <= checked_tolerance
                else ObligationStatus.FAILED
            ),
            f"{map_source}; {polyhedron_solver_source}",
            self_map_violation,
            checked_tolerance,
        ),
        TheoremObligation(
            "restricted:fixed_point_residual",
            (
                ObligationStatus.VERIFIED
                if solve_residual <= checked_tolerance
                else ObligationStatus.FAILED
            ),
            solver_source,
            solve_residual,
            checked_tolerance,
        ),
        TheoremObligation(
            "restricted:fixed_point_in_domain",
            (
                ObligationStatus.VERIFIED
                if domain_violation <= checked_tolerance
                else ObligationStatus.FAILED
            ),
            domain_source,
            domain_violation,
            checked_tolerance,
        ),
        TheoremObligation(
            "restricted:euclidean_contraction",
            (
                ObligationStatus.VERIFIED
                if diagnostics.euclidean_contraction
                else ObligationStatus.FAILED
            ),
            f"{map_source}; numpy.linalg.svd",
            diagnostics.maximum_singular_value,
            1.0,
        ),
        TheoremObligation(
            "general:assumption_3_2_correspondence",
            ObligationStatus.BLOCKED,
            "external model-specific compactness, convexity, continuity, and "
            "upper-hemicontinuity proof required",
        ),
        TheoremObligation(
            "general:kakutani_existence",
            ObligationStatus.BLOCKED,
            "external correspondence proof required; restricted affine certificate is not "
            "a generic Kakutani solver",
        ),
    )
    return AffinePolyhedralCertificate(
        matrix=_readonly(affine_matrix),
        offset=_readonly(affine_offset),
        constraint_matrix=_readonly(constraints),
        constraint_bounds=_readonly(bounds),
        fixed_point=_readonly(fixed_point),
        fixed_point_residual=solve_residual,
        maximum_linear_program_residual=maximum_solver_residual,
        maximum_domain_violation=domain_violation,
        maximum_self_map_violation=self_map_violation,
        tolerance=checked_tolerance,
        linear_diagnostics=diagnostics,
        obligations=obligations,
    )
