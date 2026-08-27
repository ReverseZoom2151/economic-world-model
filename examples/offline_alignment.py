"""Run one bounded correction against a timestamped offline evidence fixture."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import ewm
from ewm.capabilities import (
    AbsoluteErrorMetric,
    AlignmentContext,
    BoundedAlignment,
    CorrectionProposal,
    ExternalObservation,
    FunctionalCorrectionPlanner,
)


@dataclass(frozen=True, slots=True)
class OfflinePriceFixture:
    """Deterministic retrieval adapter; it is not a live external-data contract."""

    observed_at: datetime

    def fetch(self, *, as_of: datetime) -> ExternalObservation:
        if as_of < self.observed_at:
            raise ValueError("fixture cannot be observed before its timestamp")
        return ExternalObservation(
            stream="official-price",
            observed_at=self.observed_at,
            values={"price": 1.2},
            reference="offline://official-price/2026-08-27",
        )


def plan_correction(context: AlignmentContext) -> tuple[CorrectionProposal, ...]:
    direction = 1.0 if context.observed["price"] > context.simulated["price"] else -1.0
    return (
        CorrectionProposal(
            scope="environment",
            owner_id=None,
            target="mechanism_parameters",
            delta=0.1 * direction,
            source_metric="price_error",
            diagnosis="the simulated price differs from the timestamped fixture",
        ),
    )


def main() -> None:
    as_of = datetime(2026, 8, 27, 12, tzinfo=UTC)
    fixture = OfflinePriceFixture(observed_at=as_of)
    specification = ewm.alignment(
        data_sources=ewm.data_sources(streams=["official-price"], frequency="daily"),
        targets=["price"],
        metrics=["price_error"],
        tolerance={"price_error": 0.05},
        correction=ewm.correction(
            agent_targets=[],
            environment_targets=["mechanism_parameters"],
            policy="bounded_update",
            max_delta=0.1,
        ),
    )
    aligner = BoundedAlignment(
        specification=specification,
        metrics={"price_error": AbsoluteErrorMetric("price_error", "price")},
        agent_components={},
        environment_components={"mechanism_parameters": 1.0},
        planner=FunctionalCorrectionPlanner("offline-planner", plan_correction),
        max_evidence_age=timedelta(days=1),
    )
    report = aligner.align(
        {"price": 1.0},
        fixture.fetch(as_of=as_of),
        as_of=as_of,
    )
    print(
        f"evidence={report.evidence_reference} "
        f"corrections={report.correction_count} version={report.after_version}"
    )


if __name__ == "__main__":
    main()
