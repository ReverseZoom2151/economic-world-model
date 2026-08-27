from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import ewm
from ewm.capabilities import (
    AbsoluteErrorMetric,
    AlignmentContext,
    BoundedAlignment,
    CorrectionProposal,
    ExternalObservation,
    FunctionalCorrectionPlanner,
)
from ewm.core import FunctionalMechanism, World

NOW = datetime(2026, 8, 27, 12, tzinfo=UTC)


def _specification(*, max_delta: float = 0.1):
    return ewm.alignment(
        data_sources=ewm.data_sources(streams=["official-price"], frequency="daily"),
        targets=["price"],
        metrics=["price_error"],
        tolerance={"price_error": 0.05},
        correction=ewm.correction(
            agent_targets=["belief"],
            environment_targets=["mechanism_parameters"],
            policy="bounded_update",
            max_delta=max_delta,
        ),
    )


def _planner(delta: float = 0.1, *, target: str = "mechanism_parameters"):
    def plan(context: AlignmentContext) -> tuple[CorrectionProposal, ...]:
        direction = 1.0 if context.observed["price"] > context.simulated["price"] else -1.0
        return (
            CorrectionProposal(
                scope="environment",
                owner_id=None,
                target=target,
                delta=direction * delta,
                source_metric="price_error",
                diagnosis="simulated price is biased relative to official evidence",
            ),
        )

    return FunctionalCorrectionPlanner("offline-price-planner", plan)


def _engine(
    *,
    delta: float = 0.1,
    target: str = "mechanism_parameters",
) -> BoundedAlignment:
    return BoundedAlignment(
        specification=_specification(),
        metrics={"price_error": AbsoluteErrorMetric("price_error", "price")},
        agent_components={"dealer-0": {"belief": 1.0}},
        environment_components={"mechanism_parameters": 1.0},
        planner=_planner(delta, target=target),
        max_evidence_age=timedelta(days=2),
    )


def _evidence(*, observed_at: datetime = NOW) -> ExternalObservation:
    return ExternalObservation(
        stream="official-price",
        observed_at=observed_at,
        values={"price": 1.2},
        reference="fixtures/official-price-2026-08-27.json",
    )


def test_alignment_applies_allow_listed_bounded_correction_atomically() -> None:
    engine = _engine()

    report = engine.align({"price": 1.0}, _evidence(), as_of=NOW)

    assert not report.within_tolerance
    assert report.before_version == 0
    assert report.after_version == 1
    assert report.discrepancies == {"price_error": pytest.approx(0.2)}
    assert report.correction_count == 1
    assert report.provenance.evidence_reference.endswith("2026-08-27.json")
    assert report.provenance.source_attribution == ("price_error",)
    assert engine.snapshot.environment_components["mechanism_parameters"] == pytest.approx(
        1.1
    )


def test_observation_within_tolerance_is_a_version_preserving_no_op() -> None:
    engine = _engine()

    report = engine.align({"price": 1.17}, _evidence(), as_of=NOW)

    assert report.within_tolerance
    assert report.before_version == report.after_version == 0
    assert report.corrections == ()
    assert engine.version == 0


def test_stale_or_future_evidence_is_rejected() -> None:
    engine = _engine()

    with pytest.raises(ValueError, match="stale"):
        engine.align(
            {"price": 1.0},
            _evidence(observed_at=NOW - timedelta(days=3)),
            as_of=NOW,
        )
    with pytest.raises(ValueError, match="future"):
        engine.align(
            {"price": 1.0},
            _evidence(observed_at=NOW + timedelta(minutes=1)),
            as_of=NOW,
        )


def test_missing_evidence_target_is_rejected() -> None:
    engine = _engine()
    missing = ExternalObservation(
        stream="official-price",
        observed_at=NOW,
        values={"volume": 4.0},
        reference="fixtures/missing-price.json",
    )

    with pytest.raises(ValueError, match="missing alignment targets"):
        engine.align({"price": 1.0}, missing, as_of=NOW)


@pytest.mark.parametrize(
    ("delta", "target", "message"),
    [
        (0.2, "mechanism_parameters", "exceeds max_delta"),
        (0.1, "undeclared_parameter", "not allow-listed"),
    ],
)
def test_invalid_corrections_leave_alignment_state_unchanged(
    delta: float,
    target: str,
    message: str,
) -> None:
    engine = _engine(delta=delta, target=target)
    before = engine.snapshot

    with pytest.raises(ValueError, match=message):
        engine.align({"price": 1.0}, _evidence(), as_of=NOW)

    assert engine.snapshot == before


def test_alignment_can_restore_an_earlier_component_snapshot() -> None:
    engine = _engine()
    engine.align({"price": 1.0}, _evidence(), as_of=NOW)

    report = engine.restore(target_version=0, reason="correction degraded holdout error")

    assert report.restored_from_version == 1
    assert report.source_version == 0
    assert report.after_version == 2
    assert engine.snapshot.environment_components["mechanism_parameters"] == 1.0


def test_world_align_records_evidence_and_correction_versions() -> None:
    engine = _engine()
    world = World(
        initial_state=lambda _rng: {"price": 1.0},
        agents=(),
        mechanism=FunctionalMechanism(lambda state, _actions, _rng: (state, {})),
        alignment=engine,
    )
    world.reset(seed=8)

    report = world.align({"price": 1.0}, _evidence(), as_of=NOW)
    event = world.events.snapshot()[-1]

    assert report.after_version == 1
    assert world.alignment_version == 1
    assert event.kind == "align"
    assert event.payload == {
        "after_version": 1,
        "before_version": 0,
        "correction_count": 1,
        "evidence_reference": "fixtures/official-price-2026-08-27.json",
        "max_discrepancy": pytest.approx(0.2),
        "within_tolerance": False,
    }
