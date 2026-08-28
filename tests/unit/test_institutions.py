"""Evidence-bound unit contracts for institutional evolution."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping

import pytest

from ewm.capabilities import (
    GovernedInstitutions,
    InstitutionCheck,
    InstitutionKind,
    InstitutionManifest,
    InstitutionPolicy,
    InstitutionProposal,
    InstitutionSnapshot,
)
from ewm.core import FunctionalMechanism, World


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _manifest(version: int, label: str = "baseline") -> InstitutionManifest:
    return InstitutionManifest(
        institution_id="market.clearing",
        kind=InstitutionKind.MECHANISM,
        version=version,
        content_hash=_digest(label),
        description=f"clearing institution {label}",
        artifact_reference=f"institutions/{label}.json",
    )


def _proposal(
    version: int,
    label: str,
    *,
    parent_version: int | None,
    authority: str = "market-governor",
) -> InstitutionProposal:
    return InstitutionProposal(
        proposal_id=f"proposal-{label}",
        proposer_id="diagnostic-1",
        proposer_type="diagnostic",
        authority=authority,
        parent_version=parent_version,
        candidate=_manifest(version, label),
    )


def _policy() -> InstitutionPolicy:
    return InstitutionPolicy(
        authorities={
            InstitutionKind.MECHANISM: ("market-governor",),
            InstitutionKind.CONSTRAINT: ("risk-committee",),
        }
    )


Validator = Callable[[InstitutionProposal, InstitutionSnapshot], InstitutionCheck]


def _validators(*, failed: str | None = None) -> Mapping[str, Validator]:
    def build(name: str) -> Validator:
        def validate(
            _proposal: InstitutionProposal,
            _snapshot: InstitutionSnapshot,
        ) -> InstitutionCheck:
            passed = name != failed
            return InstitutionCheck(
                check=name,
                passed=passed,
                evaluator=f"{name}-validator",
                evidence_reference=f"checks/{name}.json",
                detail=None if passed else f"counterexample for {name}",
            )

        return validate

    return {name: build(name) for name in _policy().required_checks}


def _engine(*, failed: str | None = None) -> GovernedInstitutions:
    return GovernedInstitutions(policy=_policy(), validators=_validators(failed=failed))


def test_all_constitutional_checks_pass_before_atomic_transition() -> None:
    engine = _engine()

    report = engine.evolve(_proposal(1, "v1", parent_version=None))

    assert report.accepted
    assert report.before_regime_version == 0
    assert report.after_regime_version == 1
    assert report.before_institution_version is None
    assert report.after_institution_version == 1
    assert tuple(check.check for check in report.checks) == _policy().required_checks
    assert engine.active("market.clearing") == _manifest(1, "v1")


def test_feasibility_counterexample_cannot_bypass_hard_coherence() -> None:
    engine = _engine(failed="feasibility")
    before = engine.snapshot

    report = engine.evolve(_proposal(1, "infeasible-v1", parent_version=None))

    assert not report.accepted
    assert report.reasons == ("required check 'feasibility' did not pass",)
    assert report.after_regime_version == report.before_regime_version
    assert engine.snapshot == before


def test_unauthorized_proposer_is_rejected_before_transition() -> None:
    engine = _engine()

    report = engine.evolve(
        _proposal(1, "v1", parent_version=None, authority="ordinary-agent")
    )

    assert not report.accepted
    assert report.reasons == (
        "authority 'ordinary-agent' cannot change institution kind 'mechanism'",
    )
    assert engine.version == 0
    assert engine.active("market.clearing") is None


def test_only_approved_institution_versions_can_be_rolled_back() -> None:
    engine = _engine()
    engine.evolve(_proposal(1, "v1", parent_version=None))
    engine.evolve(_proposal(2, "v2", parent_version=1))

    report = engine.rollback(
        "market.clearing",
        target_version=1,
        authority="market-governor",
    )

    assert report.accepted
    assert report.before_regime_version == 2
    assert report.after_regime_version == 3
    assert report.before_institution_version == 2
    assert report.after_institution_version == 1
    assert engine.active("market.clearing") == _manifest(1, "v1")
    with pytest.raises(ValueError, match="not an approved version"):
        engine.rollback(
            "market.clearing",
            target_version=9,
            authority="market-governor",
        )


def test_world_records_reproducible_regime_transition() -> None:
    engine = _engine()
    world = World(
        initial_state=lambda _rng: {"cash": 1.0},
        agents=(),
        mechanism=FunctionalMechanism(lambda state, _actions, _rng: (state, {})),
        institutional_evolution=engine,
    )
    world.reset(seed=5)

    report = world.evolve_institutions(_proposal(1, "v1", parent_version=None))
    event = world.events.snapshot()[-1]

    assert report.accepted
    assert world.institution_version == 1
    assert event.kind == "institution_evolve"
    assert event.payload == {
        "accepted": True,
        "after_institution_version": 1,
        "after_regime_version": 1,
        "before_institution_version": None,
        "before_regime_version": 0,
        "institution_id": "market.clearing",
        "proposal_id": "proposal-v1",
        "reasons": (),
    }


def test_world_without_institution_engine_rejects_evolution_call() -> None:
    world = World(
        initial_state=lambda _rng: {},
        agents=(),
        mechanism=FunctionalMechanism(lambda state, _actions, _rng: (state, {})),
    )
    world.reset(seed=0)

    with pytest.raises(RuntimeError, match="institutional evolution is not configured"):
        world.evolve_institutions(_proposal(1, "v1", parent_version=None))
