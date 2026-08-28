"""Unit contracts for equilibrium correspondences."""

from __future__ import annotations

import numpy as np
import pytest

from ewm.core import DDGECandidate
from ewm.equilibrium import EquilibriumCorrespondence


def _candidate(policy: str, belief: str, theta: float, aggregate: float = 1.0) -> DDGECandidate:
    return DDGECandidate(
        policies={"household": policy},
        beliefs={"household": belief},
        theta=np.array([theta]),
        aggregates={"price": aggregate},
    )


def _correspondence() -> EquilibriumCorrespondence:
    def behavioral(candidate: DDGECandidate) -> float:
        return 0.0 if candidate.policies["household"] in {"save", "consume"} else 1.0

    def beliefs(candidate: DDGECandidate) -> float:
        expected = f"price={candidate.aggregates['price']:.1f}"
        return 0.0 if candidate.beliefs["household"] == expected else 1.0

    def feasibility(candidate: DDGECandidate) -> float:
        return max(0.0, -float(candidate.aggregates["price"]))

    def aggregates(candidate: DDGECandidate) -> float:
        return abs(float(candidate.aggregates["price"]) - 1.0)

    def learn(candidate: DDGECandidate) -> np.ndarray:
        value = 0.5 if candidate.policies["household"] == "consume" else 0.0
        return np.array([value])

    return EquilibriumCorrespondence(
        behavioral_residual=behavioral,
        belief_residual=beliefs,
        feasibility_residual=feasibility,
        aggregate_residual=aggregates,
        learning_update=learn,
        tolerance=1e-10,
    )


def test_inner_equilibrium_is_a_nonempty_set_and_selector_surfaces_ambiguity() -> None:
    correspondence = _correspondence()
    theta = np.array([0.0])
    candidates = (
        _candidate("save", "price=1.0", 0.0),
        _candidate("consume", "price=1.0", 0.0),
        _candidate("borrow", "price=1.0", 0.0),
        _candidate("save", "price=2.0", 0.0),
    )

    equilibria = correspondence.inner_equilibria(theta, candidates)

    assert [candidate.policies["household"] for candidate in equilibria] == [
        "save",
        "consume",
    ]
    with pytest.raises(ValueError, match="set-valued"):
        correspondence.select(theta, candidates)


def test_selector_returns_the_unique_inner_equilibrium() -> None:
    correspondence = _correspondence()
    expected = _candidate("save", "price=1.0", 0.0)

    selected = correspondence.select(
        np.array([0.0]),
        (expected, _candidate("borrow", "price=1.0", 0.0)),
    )

    assert selected is expected


def test_consistency_certificate_checks_every_ddge_condition() -> None:
    correspondence = _correspondence()
    consistent = _candidate("save", "price=1.0", 0.0)
    outer_only = _candidate("borrow", "wrong", 0.0)

    certificate = correspondence.verify(consistent)
    rejected = correspondence.verify(outer_only)

    assert certificate.consistent
    assert certificate.failed_components == ()
    assert certificate.max_residual == 0.0
    assert rejected.check("learning").passed
    assert not rejected.check("behavioral_optimality").passed
    assert not rejected.check("belief_consistency").passed
    assert not rejected.consistent
    assert set(rejected.failed_components) == {
        "behavioral_optimality",
        "belief_consistency",
    }


def test_learning_consistency_is_not_part_of_the_inner_equilibrium_filter() -> None:
    correspondence = _correspondence()
    candidate = _candidate("consume", "price=1.0", 0.0)

    assert correspondence.inner_equilibria(np.array([0.0]), (candidate,)) == (candidate,)
    certificate = correspondence.verify(candidate)
    assert not certificate.check("learning").passed
    assert np.isclose(certificate.check("learning").residual, 0.5)


def test_candidate_owns_theta_and_declared_blocks() -> None:
    theta = np.array([0.0])
    policies = {"household": "save"}
    candidate = DDGECandidate(policies=policies, beliefs={}, theta=theta)
    theta[0] = 2.0
    policies["household"] = "consume"

    assert np.array_equal(candidate.theta, np.array([0.0]))
    assert candidate.policies["household"] == "save"
    with pytest.raises(ValueError):
        candidate.theta[0] = 1.0


def test_correspondence_rejects_mismatched_theta_and_invalid_residuals() -> None:
    correspondence = _correspondence()
    candidate = _candidate("save", "price=1.0", 0.0)

    with pytest.raises(ValueError, match="candidate theta"):
        correspondence.inner_equilibria(np.array([1.0]), (candidate,))

    invalid = EquilibriumCorrespondence(
        behavioral_residual=lambda _candidate: -1.0,
        belief_residual=lambda _candidate: 0.0,
        learning_update=lambda candidate: candidate.theta,
    )
    with pytest.raises(ValueError, match="non-negative"):
        invalid.verify(candidate)
