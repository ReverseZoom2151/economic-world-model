"""Offline-capable external-evidence alignment with bounded atomic correction."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from typing import Protocol

from ewm.core import AlignmentSpecification
from ewm.core.protocols import ExternalEvidenceRecord
from ewm.core.records import freeze_value


def _finite_components(
    values: Mapping[str, float],
    label: str,
) -> dict[str, float]:
    result = {name: float(value) for name, value in values.items()}
    if any(not name for name in result):
        raise ValueError(f"{label} names must not be empty")
    if any(not isfinite(value) for value in result.values()):
        raise ValueError(f"{label} values must be finite")
    return result


@dataclass(frozen=True, slots=True)
class ExternalObservation:
    """Timestamped values returned by an external data adapter."""

    stream: str
    observed_at: datetime
    values: Mapping[str, float]
    reference: str

    def __post_init__(self) -> None:
        if not self.stream or not self.reference:
            raise ValueError("external stream and reference must not be empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("external observed_at must be timezone-aware")
        values = _finite_components(self.values, "external observation")
        if not values:
            raise ValueError("external observation values must not be empty")
        object.__setattr__(self, "values", freeze_value(values))


class AlignmentMetric(Protocol):
    """Target-specific discrepancy metric."""

    @property
    def name(self) -> str: ...

    @property
    def target(self) -> str: ...

    def measure(self, simulated: float, observed: float) -> float: ...


class ExternalDataAdapter(Protocol):
    """Retrieval boundary kept outside correction and alignment logic."""

    def fetch(self, *, as_of: datetime) -> ExternalObservation: ...


@dataclass(frozen=True, slots=True)
class AbsoluteErrorMetric:
    """Absolute state error for one declared alignment target."""

    name: str
    target: str

    def __post_init__(self) -> None:
        if not self.name or not self.target:
            raise ValueError("metric name and target must not be empty")

    def measure(self, simulated: float, observed: float) -> float:
        return abs(observed - simulated)


@dataclass(frozen=True, slots=True)
class CorrectionProposal:
    """One diagnosed bounded update to an allow-listed internal component."""

    scope: str
    owner_id: str | None
    target: str
    delta: float
    source_metric: str
    diagnosis: str

    def __post_init__(self) -> None:
        if self.scope not in {"agent", "environment"}:
            raise ValueError("correction scope must be 'agent' or 'environment'")
        if self.scope == "agent" and not self.owner_id:
            raise ValueError("agent correction requires owner_id")
        if self.scope == "environment" and self.owner_id is not None:
            raise ValueError("environment correction must not have owner_id")
        if not self.target or not self.source_metric or not self.diagnosis:
            raise ValueError("correction target, source metric, and diagnosis are required")
        if not isfinite(self.delta):
            raise ValueError("correction delta must be finite")


@dataclass(frozen=True, slots=True)
class AppliedCorrection:
    """Validated correction with before and after component values."""

    scope: str
    owner_id: str | None
    target: str
    source_metric: str
    diagnosis: str
    before: float
    delta: float
    after: float


@dataclass(frozen=True, slots=True)
class AlignmentSnapshot:
    """Immutable internal components controlled by external alignment."""

    version: int
    agent_components: Mapping[str, Mapping[str, float]]
    environment_components: Mapping[str, float]

    def __post_init__(self) -> None:
        if self.version < 0:
            raise ValueError("alignment version must be non-negative")
        object.__setattr__(self, "agent_components", freeze_value(self.agent_components))
        object.__setattr__(
            self,
            "environment_components",
            freeze_value(self.environment_components),
        )


@dataclass(frozen=True, slots=True)
class AlignmentContext:
    """Complete discrepancy context supplied to a correction planner."""

    simulated: Mapping[str, float]
    observed: Mapping[str, float]
    discrepancies: Mapping[str, float]
    breached_metrics: tuple[str, ...]
    snapshot: AlignmentSnapshot

    def __post_init__(self) -> None:
        object.__setattr__(self, "simulated", freeze_value(self.simulated))
        object.__setattr__(self, "observed", freeze_value(self.observed))
        object.__setattr__(self, "discrepancies", freeze_value(self.discrepancies))
        object.__setattr__(self, "breached_metrics", tuple(self.breached_metrics))


class CorrectionPlanner(Protocol):
    """Diagnose discrepancies and propose internal component corrections."""

    @property
    def name(self) -> str: ...

    def plan(self, context: AlignmentContext) -> tuple[CorrectionProposal, ...]: ...


@dataclass(frozen=True, slots=True)
class FunctionalCorrectionPlanner:
    """Correction planner backed by an explicit deterministic callable."""

    name: str
    function: Callable[[AlignmentContext], tuple[CorrectionProposal, ...]]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("correction planner name must not be empty")

    def plan(self, context: AlignmentContext) -> tuple[CorrectionProposal, ...]:
        return tuple(self.function(context))


@dataclass(frozen=True, slots=True)
class AlignmentProvenance:
    """Evidence and diagnostic identity for one alignment call."""

    evidence_reference: str
    stream: str
    observed_at: datetime
    aligned_at: datetime
    planner: str
    source_attribution: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AlignmentReport:
    """Discrepancies, interventions, and versions for one evidence comparison."""

    before_version: int
    after_version: int
    discrepancies: Mapping[str, float]
    tolerance: Mapping[str, float]
    within_tolerance: bool
    corrections: tuple[AppliedCorrection, ...]
    provenance: AlignmentProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "discrepancies", freeze_value(self.discrepancies))
        object.__setattr__(self, "tolerance", freeze_value(self.tolerance))
        object.__setattr__(self, "corrections", tuple(self.corrections))

    @property
    def evidence_reference(self) -> str:
        return self.provenance.evidence_reference

    @property
    def correction_count(self) -> int:
        return len(self.corrections)

    @property
    def max_discrepancy(self) -> float:
        return max(self.discrepancies.values(), default=0.0)

    @property
    def max_correction_magnitude(self) -> float:
        return max((abs(item.delta) for item in self.corrections), default=0.0)


@dataclass(frozen=True, slots=True)
class AlignmentRestoreReport:
    """Monotone version record for restoring a prior component snapshot."""

    restored_from_version: int
    source_version: int
    after_version: int
    reason: str


class BoundedAlignment:
    """Compare external evidence and atomically apply bounded corrections."""

    def __init__(
        self,
        *,
        specification: AlignmentSpecification,
        metrics: Mapping[str, AlignmentMetric],
        agent_components: Mapping[str, Mapping[str, float]],
        environment_components: Mapping[str, float],
        planner: CorrectionPlanner,
        max_evidence_age: timedelta,
    ) -> None:
        if set(metrics) != set(specification.metrics):
            raise ValueError("metric registry must exactly match alignment metrics")
        for name, metric in metrics.items():
            if metric.name != name:
                raise ValueError(f"metric registry key {name!r} does not match metric name")
            if metric.target not in specification.targets:
                raise ValueError(f"metric {name!r} references an undeclared target")
        if max_evidence_age <= timedelta(0):
            raise ValueError("max_evidence_age must be positive")
        agents = {
            owner_id: _finite_components(values, f"agent {owner_id!r} components")
            for owner_id, values in agent_components.items()
        }
        if any(not owner_id for owner_id in agents):
            raise ValueError("alignment agent identifiers must not be empty")
        environment = _finite_components(
            environment_components,
            "alignment environment components",
        )
        available_agent_targets = {
            target for components in agents.values() for target in components
        }
        missing_agent_targets = set(
            specification.correction.agent_targets
        ).difference(available_agent_targets)
        missing_environment_targets = set(
            specification.correction.environment_targets
        ).difference(environment)
        if missing_agent_targets or missing_environment_targets:
            raise ValueError(
                "alignment components omit declared correction targets: "
                f"agents={sorted(missing_agent_targets)}, "
                f"environment={sorted(missing_environment_targets)}"
            )
        self._specification = specification
        self._metrics = dict(metrics)
        self._agent_components = agents
        self._environment_components = environment
        self._planner = planner
        self._max_evidence_age = max_evidence_age
        self._version = 0
        self._history: dict[int, AlignmentSnapshot] = {0: self.snapshot}

    @property
    def version(self) -> int:
        return self._version

    @property
    def snapshot(self) -> AlignmentSnapshot:
        return AlignmentSnapshot(
            version=self._version,
            agent_components=self._agent_components,
            environment_components=self._environment_components,
        )

    def align(
        self,
        simulated: Mapping[str, float],
        evidence: ExternalEvidenceRecord,
        *,
        as_of: datetime,
    ) -> AlignmentReport:
        """Measure discrepancy and commit a complete valid correction plan."""

        if not isinstance(evidence, ExternalObservation):
            raise TypeError("bounded alignment requires an ExternalObservation")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("alignment as_of must be timezone-aware")
        if evidence.stream not in self._specification.data_sources.streams:
            raise ValueError(f"external stream {evidence.stream!r} is not declared")
        age = as_of - evidence.observed_at
        if age < timedelta(0):
            raise ValueError("external evidence is from the future")
        if age > self._max_evidence_age:
            raise ValueError("external evidence is stale")
        simulated_values = _finite_components(simulated, "simulated alignment targets")
        targets = set(self._specification.targets)
        missing_simulated = targets.difference(simulated_values)
        missing_observed = targets.difference(evidence.values)
        if missing_simulated:
            raise ValueError(
                f"simulation is missing alignment targets {sorted(missing_simulated)}"
            )
        if missing_observed:
            raise ValueError(
                f"external evidence is missing alignment targets {sorted(missing_observed)}"
            )

        discrepancies: dict[str, float] = {}
        for name in self._specification.metrics:
            metric = self._metrics[name]
            value = float(
                metric.measure(
                    simulated_values[metric.target],
                    evidence.values[metric.target],
                )
            )
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"alignment metric {name!r} must be finite and non-negative")
            discrepancies[name] = value
        breached = tuple(
            name
            for name in self._specification.metrics
            if discrepancies[name] > self._specification.tolerance[name]
        )
        before = self.snapshot
        context = AlignmentContext(
            simulated=simulated_values,
            observed=evidence.values,
            discrepancies=discrepancies,
            breached_metrics=breached,
            snapshot=before,
        )
        proposals = self._planner.plan(context) if breached else ()
        if breached and not proposals:
            raise ValueError("correction planner returned no corrections for breached metrics")
        keys = tuple((item.scope, item.owner_id, item.target) for item in proposals)
        if len(keys) != len(set(keys)):
            raise ValueError("correction proposals must target distinct components")
        corrections = tuple(self._validate(proposal, breached) for proposal in proposals)

        agent_components = {
            owner_id: dict(components)
            for owner_id, components in self._agent_components.items()
        }
        environment_components = dict(self._environment_components)
        for correction in corrections:
            if correction.scope == "agent":
                assert correction.owner_id is not None
                agent_components[correction.owner_id][correction.target] = correction.after
            else:
                environment_components[correction.target] = correction.after
        if corrections:
            self._agent_components = agent_components
            self._environment_components = environment_components
            self._version += 1
            self._history[self._version] = self.snapshot

        provenance = AlignmentProvenance(
            evidence_reference=evidence.reference,
            stream=evidence.stream,
            observed_at=evidence.observed_at,
            aligned_at=as_of,
            planner=self._planner.name,
            source_attribution=tuple(
                sorted({correction.source_metric for correction in corrections})
            ),
        )
        return AlignmentReport(
            before_version=before.version,
            after_version=self._version,
            discrepancies=discrepancies,
            tolerance=self._specification.tolerance,
            within_tolerance=not breached,
            corrections=corrections,
            provenance=provenance,
        )

    def restore(self, *, target_version: int, reason: str) -> AlignmentRestoreReport:
        """Restore approved component state while preserving a monotone audit version."""

        if not reason:
            raise ValueError("alignment restore reason must not be empty")
        try:
            source = self._history[target_version]
        except KeyError as error:
            raise ValueError(f"alignment version {target_version} is not available") from error
        restored_from = self._version
        self._agent_components = {
            owner_id: dict(components)
            for owner_id, components in source.agent_components.items()
        }
        self._environment_components = dict(source.environment_components)
        self._version += 1
        self._history[self._version] = self.snapshot
        return AlignmentRestoreReport(
            restored_from_version=restored_from,
            source_version=target_version,
            after_version=self._version,
            reason=reason,
        )

    def _validate(
        self,
        proposal: CorrectionProposal,
        breached_metrics: tuple[str, ...],
    ) -> AppliedCorrection:
        if proposal.source_metric not in breached_metrics:
            raise ValueError(
                f"correction source metric {proposal.source_metric!r} did not breach tolerance"
            )
        if abs(proposal.delta) > self._specification.correction.max_delta:
            raise ValueError(
                f"correction delta {proposal.delta} exceeds max_delta "
                f"{self._specification.correction.max_delta}"
            )
        if proposal.scope == "agent":
            if proposal.target not in self._specification.correction.agent_targets:
                raise ValueError(
                    f"agent correction target {proposal.target!r} is not allow-listed"
                )
            assert proposal.owner_id is not None
            try:
                components = self._agent_components[proposal.owner_id]
            except KeyError as error:
                raise ValueError(
                    f"unknown alignment agent {proposal.owner_id!r}"
                ) from error
            if proposal.target not in components:
                raise ValueError(
                    f"agent {proposal.owner_id!r} has no correction target "
                    f"{proposal.target!r}"
                )
            before = components[proposal.target]
        else:
            if proposal.target not in self._specification.correction.environment_targets:
                raise ValueError(
                    f"environment correction target {proposal.target!r} is not allow-listed"
                )
            if proposal.target not in self._environment_components:
                raise ValueError(
                    f"environment has no correction target {proposal.target!r}"
                )
            before = self._environment_components[proposal.target]
        after = before + proposal.delta
        if not isfinite(after):
            raise ValueError("correction produced a non-finite component")
        return AppliedCorrection(
            scope=proposal.scope,
            owner_id=proposal.owner_id,
            target=proposal.target,
            source_metric=proposal.source_metric,
            diagnosis=proposal.diagnosis,
            before=before,
            delta=proposal.delta,
            after=after,
        )
