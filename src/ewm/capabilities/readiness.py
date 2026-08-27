"""Machine-checkable Han L3-L6 evidence readiness without capability awards."""

from __future__ import annotations

import hashlib
import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

import numpy as np

from ewm.core import (
    AgentSpecification,
    AlignmentSpecification,
    CorrectionSpecification,
    DataSourcesSpecification,
    content_digest,
)
from ewm.core.evidence import EvidenceStatus, ValidatedEvidenceArtifact
from ewm.core.records import freeze_value

from .alignment import (
    AbsoluteErrorMetric,
    AlignmentContext,
    BoundedAlignment,
    CorrectionProposal,
    ExternalObservation,
    FunctionalCorrectionPlanner,
)
from .cognition import (
    ActionSchema,
    CognitiveAgent,
    FunctionalCognitiveTool,
    ModelRequest,
    ModelResponse,
)
from .evolution import (
    CapabilityKind,
    CapabilityManifest,
    EvolutionProposal,
    EvolutionRegistry,
    GateEvidence,
    PromotionPolicy,
)
from .institutions import (
    GovernedInstitutions,
    InstitutionCheck,
    InstitutionKind,
    InstitutionManifest,
    InstitutionPolicy,
    InstitutionProposal,
    InstitutionSnapshot,
    InstitutionValidator,
)
from .levels import (
    LEVEL_REQUIREMENTS,
    CapabilityLevel,
    EvidenceKind,
    LevelRequirement,
    requirement_gate,
)

HAN_L3_L6_PROTOCOL_SCHEMA = "ewm.han-l3-l6-readiness.protocol.v1"
HAN_L3_L6_REPORT_SCHEMA = "ewm.han-l3-l6-readiness.report.v1"
DEFAULT_HAN_L3_L6_PROTOCOL = Path(__file__).with_name("han-l3-l6-readiness-v1.toml")
_CLASSIFICATION = "evidence_readiness_only"
_OPERATORS = frozenset({"eq", "gte", "lte"})
_PROBES = frozenset({"alignment", "cognition", "evolution", "institution"})
_HIGHER_LEVELS = (
    CapabilityLevel.L3,
    CapabilityLevel.L4,
    CapabilityLevel.L5,
    CapabilityLevel.L6,
)
_HIGHER_REQUIREMENTS = frozenset(
    requirement for level in _HIGHER_LEVELS for requirement in LEVEL_REQUIREMENTS[level]
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "classification",
        "protocol_filename",
        "protocol_version",
        "report_schema",
        "requirement",
        "schema_version",
        "seed",
        "source_files",
    }
)
_REQUIREMENT_KEYS = frozenset(
    {"blocker", "classification", "criterion", "level", "probe", "requirement"}
)
_CRITERION_KEYS = frozenset({"metric", "operator", "value"})
_NOW = datetime(2026, 8, 27, 12, tzinfo=UTC)


class ReadinessClassification(StrEnum):
    """Truthful strength labels for local, non-awarding substrate evidence."""

    SYNTHETIC_SUBSTRATE = "synthetic_substrate"
    FIXTURE_ONLY = "fixture_only"
    NOT_OBSERVED = "not_observed"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return cast(Mapping[str, Any], value)


def _sequence(value: Any, *, label: str) -> tuple[Any, ...]:
    if not isinstance(value, list | tuple):
        raise TypeError(f"{label} must be a sequence")
    return tuple(value)


def _string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{label} must be a nonempty string")
    return value


def _integer(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    return value


def _number(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _require_exact_keys(
    record: Mapping[str, Any],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    actual = frozenset(record)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(
            f"{label} keys do not match the protocol schema: "
            f"missing={missing!r}, unknown={unknown!r}"
        )


def _source_sha256(source_files: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    directory = Path(__file__).parent
    for name in sorted(source_files):
        path = Path(name)
        if path.name != name or path.suffix != ".py":
            raise ValueError("readiness source files must be local Python filenames")
        source = directory / name
        if not source.is_file():
            raise FileNotFoundError(f"readiness source file is missing: {name}")
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ReadinessCriterion:
    """One local metric check that never substitutes for an official gate."""

    metric: str
    operator: str
    value: float

    def __post_init__(self) -> None:
        if not self.metric:
            raise ValueError("readiness metric must not be empty")
        if self.operator not in _OPERATORS:
            raise ValueError(f"unsupported readiness operator {self.operator!r}")
        if not math.isfinite(self.value):
            raise ValueError("readiness criterion must be finite")


@dataclass(frozen=True, slots=True)
class HanReadinessDeclaration:
    """One prespecified local probe for a higher-level requirement."""

    requirement: LevelRequirement
    level: CapabilityLevel
    probe: str
    classification: ReadinessClassification
    blocker: str
    criterion: ReadinessCriterion

    def __post_init__(self) -> None:
        if self.level not in _HIGHER_LEVELS:
            raise ValueError("readiness declaration must target Han L3-L6")
        if self.requirement not in LEVEL_REQUIREMENTS[self.level]:
            raise ValueError("readiness requirement does not match levels policy")
        if self.probe not in _PROBES:
            raise ValueError(f"unsupported readiness probe {self.probe!r}")
        if not self.blocker:
            raise ValueError("readiness blocker must not be empty")


@dataclass(frozen=True, slots=True)
class HanReadinessProtocol:
    """Strict, content-identified contract for L3-L6 readiness probes."""

    schema_version: str
    protocol_version: int
    protocol_filename: str
    report_schema: str
    classification: str
    seed: int
    source_files: tuple[str, ...]
    requirements: tuple[HanReadinessDeclaration, ...]
    protocol_sha256: str
    source_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != HAN_L3_L6_PROTOCOL_SCHEMA:
            raise ValueError(f"unsupported Han readiness protocol {self.schema_version!r}")
        if self.protocol_version != 1:
            raise ValueError(
                f"unsupported Han readiness protocol version {self.protocol_version!r}"
            )
        if self.protocol_filename != DEFAULT_HAN_L3_L6_PROTOCOL.name:
            raise ValueError("Han readiness filename does not match version 1")
        if self.report_schema != HAN_L3_L6_REPORT_SCHEMA:
            raise ValueError(f"unsupported Han readiness report {self.report_schema!r}")
        if self.classification != _CLASSIFICATION:
            raise ValueError("Han L3-L6 harness must be labeled evidence readiness only")
        if self.seed < 0:
            raise ValueError("readiness seed must be non-negative")
        if not self.source_files or len(self.source_files) != len(set(self.source_files)):
            raise ValueError("readiness source files must be unique and nonempty")
        requirements = tuple(item.requirement for item in self.requirements)
        if len(requirements) != len(set(requirements)):
            raise ValueError("readiness requirements must be unique")
        if set(requirements) != _HIGHER_REQUIREMENTS:
            raise ValueError("readiness protocol must declare every L3-L6 requirement")
        if len(self.protocol_sha256) != 64 or len(self.source_sha256) != 64:
            raise ValueError("readiness identities must be SHA-256 digests")
        object.__setattr__(self, "source_files", tuple(self.source_files))
        object.__setattr__(self, "requirements", tuple(self.requirements))


@dataclass(frozen=True, slots=True)
class HanReadinessResult:
    """Observed local readiness result with an explicit official-evidence blocker."""

    requirement: LevelRequirement
    level: CapabilityLevel
    probe: str
    classification: ReadinessClassification
    required_evidence_kind: EvidenceKind
    required_observations: int
    metric: str
    operator: str
    expected: float
    observed_value: float
    observations: int
    local_criterion_passed: bool
    blocked: bool
    officially_awarded: bool
    blocker: str

    def __post_init__(self) -> None:
        if not self.blocked or self.officially_awarded:
            raise ValueError("readiness results must remain blocked and non-awarding")
        if self.observations < 0 or self.required_observations < 1:
            raise ValueError("readiness observation counts are invalid")
        if not self.blocker:
            raise ValueError("readiness result must state its blocker")

    def as_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "blocker": self.blocker,
            "classification": self.classification.value,
            "expected": self.expected,
            "level": self.level.name,
            "local_criterion_passed": self.local_criterion_passed,
            "metric": self.metric,
            "observations": self.observations,
            "observed_value": self.observed_value,
            "officially_awarded": self.officially_awarded,
            "operator": self.operator,
            "probe": self.probe,
            "required_evidence_kind": self.required_evidence_kind.value,
            "required_observations": self.required_observations,
            "requirement": self.requirement.value,
        }


@dataclass(frozen=True, slots=True)
class HanReadinessReport:
    """Immutable, self-identified report of deterministic substrate readiness."""

    schema_version: str
    protocol_schema: str
    classification: str
    protocol_sha256: str
    source_sha256: str
    seed: int
    metrics: Mapping[str, float]
    results: tuple[HanReadinessResult, ...]
    report_sha256: str = ""

    def __post_init__(self) -> None:
        if self.report_sha256 and len(self.report_sha256) != 64:
            raise ValueError("readiness report identity must be a SHA-256 digest")
        object.__setattr__(
            self,
            "metrics",
            cast(Mapping[str, float], freeze_value(dict(self.metrics))),
        )
        object.__setattr__(self, "results", tuple(self.results))

    def as_dict(self, *, include_report_hash: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "classification": self.classification,
            "metrics": dict(self.metrics),
            "protocol_schema": self.protocol_schema,
            "protocol_sha256": self.protocol_sha256,
            "results": [item.as_dict() for item in self.results],
            "schema_version": self.schema_version,
            "seed": self.seed,
            "source_sha256": self.source_sha256,
        }
        if include_report_hash:
            result["report_sha256"] = self.report_sha256
        return result


def load_han_l3_l6_protocol(
    protocol_path: Path = DEFAULT_HAN_L3_L6_PROTOCOL,
) -> HanReadinessProtocol:
    """Load the strict installed L3-L6 readiness contract."""

    content = protocol_path.read_bytes()
    raw = _mapping(tomllib.loads(content.decode("utf-8")), label="readiness protocol")
    _require_exact_keys(raw, _TOP_LEVEL_KEYS, label="readiness protocol")
    protocol_filename = _string(raw["protocol_filename"], label="protocol filename")
    if protocol_path.name != protocol_filename:
        raise ValueError("readiness path does not match declared protocol filename")

    declarations: list[HanReadinessDeclaration] = []
    for index, raw_declaration in enumerate(
        _sequence(raw["requirement"], label="readiness requirements")
    ):
        declaration = _mapping(
            raw_declaration,
            label=f"readiness requirement {index}",
        )
        _require_exact_keys(
            declaration,
            _REQUIREMENT_KEYS,
            label=f"readiness requirement {index}",
        )
        raw_criteria = _sequence(
            declaration["criterion"],
            label="readiness criterion",
        )
        if len(raw_criteria) != 1:
            raise ValueError("each readiness requirement must declare exactly one criterion")
        criterion = _mapping(raw_criteria[0], label="readiness criterion")
        _require_exact_keys(criterion, _CRITERION_KEYS, label="readiness criterion")
        level_name = _string(declaration["level"], label="readiness level")
        try:
            level = CapabilityLevel[level_name]
        except KeyError as error:
            raise ValueError(f"unsupported readiness level {level_name!r}") from error
        requirement = LevelRequirement(
            _string(declaration["requirement"], label="readiness requirement")
        )
        classification_name = _string(
            declaration["classification"],
            label="readiness classification",
        )
        try:
            classification = ReadinessClassification(classification_name)
        except ValueError as error:
            raise ValueError(
                f"unsupported local readiness classification {classification_name!r}"
            ) from error
        declarations.append(
            HanReadinessDeclaration(
                requirement=requirement,
                level=level,
                probe=_string(declaration["probe"], label="readiness probe"),
                classification=classification,
                blocker=_string(declaration["blocker"], label="readiness blocker"),
                criterion=ReadinessCriterion(
                    metric=_string(criterion["metric"], label="readiness metric"),
                    operator=_string(criterion["operator"], label="readiness operator"),
                    value=_number(criterion["value"], label="readiness value"),
                ),
            )
        )
    source_files = tuple(
        _string(item, label="readiness source file")
        for item in _sequence(raw["source_files"], label="readiness source files")
    )
    return HanReadinessProtocol(
        schema_version=_string(raw["schema_version"], label="protocol schema"),
        protocol_version=_integer(raw["protocol_version"], label="protocol version"),
        protocol_filename=protocol_filename,
        report_schema=_string(raw["report_schema"], label="report schema"),
        classification=_string(raw["classification"], label="classification"),
        seed=_integer(raw["seed"], label="readiness seed"),
        source_files=source_files,
        requirements=tuple(declarations),
        protocol_sha256=_sha256(content),
        source_sha256=_source_sha256(source_files),
    )


@dataclass(slots=True)
class _FixtureBackend:
    requests: list[ModelRequest] = field(default_factory=list)
    name: str = "fixture-backend"
    model: str = "deterministic-fixture-v1"

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        price = float(request.observation["public"]["price"])
        return ModelResponse(
            action_kind="hold",
            action_values={},
            belief_updates={"expected_price": price},
            rationale="deterministic fixture response",
            request_id=f"fixture-{len(self.requests)}",
        )


def _cognition_metrics(seed: int) -> dict[str, float]:
    backend = _FixtureBackend()
    tool_calls = 0

    def price_tool(observation: Mapping[str, Any]) -> Mapping[str, float]:
        nonlocal tool_calls
        tool_calls += 1
        return {"price": float(observation["public"]["price"])}

    tool = FunctionalCognitiveTool("price_reader", price_tool)
    specification = AgentSpecification(
        role="observer",
        objective="Exercise deterministic cognitive state plumbing.",
        state_variables=("expected_price",),
        information_channels={"public": ("price",)},
        action_space=("hold",),
        tools=(tool.name,),
        memory_window=2,
    )
    agent = CognitiveAgent(
        agent_id="observer-0",
        specification=specification,
        backend=backend,
        initial_beliefs={"expected_price": 1.0},
        tools={tool.name: tool},
        action_schema=ActionSchema(required_values={"hold": ()}),
    )
    rng = np.random.default_rng(seed)
    belief_observations = 0
    for price in (1.05, 1.10):
        agent.act({"public": {"price": price}}, rng)
        if agent.last_decision is not None:
            belief_observations += 1
    return {
        "cognition_belief_state_observation_count": float(belief_observations),
        "cognition_fixture_backend_call_count": float(len(backend.requests)),
        "cognition_fixture_behavior_observation_count": float(len(backend.requests)),
        "cognition_memory_and_tool_observation_count": float(min(len(agent.memory), tool_calls)),
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _gate_evidence(label: str) -> tuple[GateEvidence, ...]:
    return tuple(
        GateEvidence(
            gate=gate,
            passed=True,
            evaluator="readiness-fixture",
            evidence_reference=f"fixture://evolution/{label}/{gate}",
            score=1.0,
            threshold=1.0,
        )
        for gate in ("sandbox", "safety")
    )


def _evolution_metrics() -> dict[str, float]:
    registry = EvolutionRegistry(PromotionPolicy())
    proposals = tuple(
        EvolutionProposal(
            proposal_id=f"readiness-capability-v{version}",
            candidate=CapabilityManifest(
                capability_id="readiness.strategy",
                kind=CapabilityKind.STRATEGY,
                version=version,
                content_hash=_digest(f"readiness-capability-v{version}"),
                description=f"readiness fixture strategy v{version}",
                artifact_reference=f"fixture://evolution/v{version}",
            ),
            parent_version=None if version == 1 else version - 1,
            evidence=_gate_evidence(f"v{version}"),
        )
        for version in (1, 2)
    )
    promotions = tuple(registry.evaluate_and_promote(item) for item in proposals)
    restored = EvolutionRegistry.from_json(registry.to_json(), policy=registry.policy)
    registry.rollback("readiness.strategy", target_version=1)
    return {
        "evolution_fixture_proposal_count": float(len(proposals)),
        "evolution_persisted_version_count": float(
            len(restored.approved_versions("readiness.strategy"))
        ),
        "evolution_promoted_version_count": float(sum(item.promoted for item in promotions)),
        "evolution_rollback_count": 1.0,
    }


def _institution_metrics() -> dict[str, float]:
    policy = InstitutionPolicy(authorities={InstitutionKind.MECHANISM: ("readiness-governor",)})

    def validator(name: str) -> InstitutionValidator:
        def validate(
            _proposal: InstitutionProposal,
            _snapshot: InstitutionSnapshot,
        ) -> InstitutionCheck:
            return InstitutionCheck(
                check=name,
                passed=True,
                evaluator="readiness-fixture",
                evidence_reference=f"fixture://institution/{name}",
            )

        return validate

    engine = GovernedInstitutions(
        policy=policy,
        validators={name: validator(name) for name in policy.required_checks},
    )
    proposals = tuple(
        InstitutionProposal(
            proposal_id=f"readiness-institution-v{version}",
            proposer_id="fixture-diagnostic",
            proposer_type="diagnostic",
            authority="readiness-governor",
            parent_version=None if version == 1 else version - 1,
            candidate=InstitutionManifest(
                institution_id="readiness.mechanism",
                kind=InstitutionKind.MECHANISM,
                version=version,
                content_hash=_digest(f"readiness-institution-v{version}"),
                description=f"readiness fixture institution v{version}",
                artifact_reference=f"fixture://institution/v{version}",
            ),
        )
        for version in (1, 2)
    )
    transitions = tuple(engine.evolve(item) for item in proposals)
    return {
        "institution_accepted_fixture_change_count": float(
            sum(item.accepted for item in transitions)
        ),
        "institution_constitutional_check_count": float(
            sum(len(item.checks) for item in transitions)
        ),
        "institution_fixture_proposal_count": float(len(proposals)),
        "institution_outcome_observation_count": 0.0,
    }


def _alignment_metrics() -> dict[str, float]:
    specification = AlignmentSpecification(
        data_sources=DataSourcesSpecification(
            streams=("fixture-price",),
            frequency="one-off fixture",
        ),
        targets=("price",),
        metrics=("price_error",),
        tolerance={"price_error": 0.05},
        correction=CorrectionSpecification(
            agent_targets=(),
            environment_targets=("mechanism_parameters",),
            policy="bounded_update",
            max_delta=0.1,
        ),
    )

    def plan(_context: AlignmentContext) -> tuple[CorrectionProposal, ...]:
        return (
            CorrectionProposal(
                scope="environment",
                owner_id=None,
                target="mechanism_parameters",
                delta=0.1,
                source_metric="price_error",
                diagnosis="single deterministic fixture discrepancy",
            ),
        )

    engine = BoundedAlignment(
        specification=specification,
        metrics={"price_error": AbsoluteErrorMetric("price_error", "price")},
        agent_components={},
        environment_components={"mechanism_parameters": 1.0},
        planner=FunctionalCorrectionPlanner("readiness-fixture", plan),
        max_evidence_age=timedelta(days=1),
    )
    report = engine.align(
        {"price": 1.0},
        ExternalObservation(
            stream="fixture-price",
            observed_at=_NOW,
            values={"price": 1.2},
            reference="fixture://alignment/single-observation",
        ),
        as_of=_NOW,
    )
    return {
        "alignment_external_fixture_count": 1.0,
        "alignment_fixture_correction_count": float(report.correction_count),
        "alignment_fixture_discrepancy_count": float(bool(report.discrepancies)),
        "alignment_fixture_observation_count": 1.0,
    }


def _run_probes(seed: int) -> dict[str, float]:
    metrics = {
        **_cognition_metrics(seed),
        **_evolution_metrics(),
        **_institution_metrics(),
        **_alignment_metrics(),
    }
    return dict(sorted(metrics.items()))


def _criterion_passes(criterion: ReadinessCriterion, observed: float) -> bool:
    if criterion.operator == "eq":
        return observed == criterion.value
    if criterion.operator == "gte":
        return observed >= criterion.value
    if criterion.operator == "lte":
        return observed <= criterion.value
    raise AssertionError("validated readiness operator became unreachable")


def _build_report(protocol: HanReadinessProtocol) -> HanReadinessReport:
    metrics = _run_probes(protocol.seed)
    results: list[HanReadinessResult] = []
    for declaration in protocol.requirements:
        if declaration.criterion.metric not in metrics:
            raise ValueError(f"readiness metric {declaration.criterion.metric!r} was not observed")
        observed = metrics[declaration.criterion.metric]
        gate = requirement_gate(declaration.requirement)
        results.append(
            HanReadinessResult(
                requirement=declaration.requirement,
                level=declaration.level,
                probe=declaration.probe,
                classification=declaration.classification,
                required_evidence_kind=gate.minimum_kind,
                required_observations=gate.minimum_observations,
                metric=declaration.criterion.metric,
                operator=declaration.criterion.operator,
                expected=declaration.criterion.value,
                observed_value=observed,
                observations=int(observed),
                local_criterion_passed=_criterion_passes(
                    declaration.criterion,
                    observed,
                ),
                blocked=True,
                officially_awarded=False,
                blocker=declaration.blocker,
            )
        )
    report = HanReadinessReport(
        schema_version=protocol.report_schema,
        protocol_schema=protocol.schema_version,
        classification=protocol.classification,
        protocol_sha256=protocol.protocol_sha256,
        source_sha256=protocol.source_sha256,
        seed=protocol.seed,
        metrics=metrics,
        results=tuple(results),
    )
    return replace(
        report,
        report_sha256=content_digest(report.as_dict(include_report_hash=False)),
    )


def run_han_l3_l6_readiness(
    *,
    protocol_path: Path = DEFAULT_HAN_L3_L6_PROTOCOL,
) -> HanReadinessReport:
    """Execute local deterministic substrates without awarding Han L3-L6."""

    protocol = load_han_l3_l6_protocol(protocol_path)
    report = _build_report(protocol)
    verify_han_l3_l6_report(report, protocol_path=protocol_path)
    return report


def verify_han_l3_l6_report(
    report: HanReadinessReport,
    *,
    protocol_path: Path = DEFAULT_HAN_L3_L6_PROTOCOL,
) -> None:
    """Reject report, source, policy, classification, or self-resealed tampering."""

    expected_hash = content_digest(report.as_dict(include_report_hash=False))
    if report.report_sha256 != expected_hash:
        raise ValueError("Han readiness report SHA-256 does not match its contents")
    protocol = load_han_l3_l6_protocol(protocol_path)
    if report.protocol_sha256 != protocol.protocol_sha256:
        raise ValueError("Han readiness protocol SHA-256 does not match")
    if report.source_sha256 != protocol.source_sha256:
        raise ValueError("Han readiness source SHA-256 does not match")
    if (
        report.schema_version != protocol.report_schema
        or report.protocol_schema != protocol.schema_version
        or report.classification != protocol.classification
        or report.seed != protocol.seed
    ):
        raise ValueError("Han readiness report identity does not match its protocol")
    expected = _build_report(protocol)
    if report.as_dict() != expected.as_dict():
        raise ValueError("Han readiness report does not match deterministic substrate observations")


def han_l3_l6_artifacts(
    report: HanReadinessReport,
    *,
    protocol_path: Path = DEFAULT_HAN_L3_L6_PROTOCOL,
) -> tuple[ValidatedEvidenceArtifact, ...]:
    """Content-address each local result under a non-capability readiness subject."""

    verify_han_l3_l6_report(report, protocol_path=protocol_path)
    return tuple(
        ValidatedEvidenceArtifact.from_observation(
            subject=f"readiness:{result.requirement.value}",
            status=(EvidenceStatus.PASS if result.local_criterion_passed else EvidenceStatus.FAIL),
            provenance=f"{protocol_path.name}:{report.report_sha256}",
            payload={
                "protocol_sha256": report.protocol_sha256,
                "readiness_result": result.as_dict(),
                "report_schema": report.schema_version,
                "report_sha256": report.report_sha256,
                "source_sha256": report.source_sha256,
            },
            observations=max(1, result.observations),
        )
        for result in report.results
    )
