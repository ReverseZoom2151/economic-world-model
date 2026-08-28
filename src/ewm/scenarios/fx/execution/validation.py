"""Machine-checkable synthetic systems conformance for Han levels L1 and L2."""

from __future__ import annotations

import hashlib
import json
import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from ewm.core import Event, canonical_json, content_digest, state_digest, verify_event_chain
from ewm.core.evidence import EvidenceStatus, ValidatedEvidenceArtifact
from ewm.core.records import freeze_value

from ..economy.model import FXState
from ..economy.presets import smoke_config
from .runtime import fx_world_blueprint

HAN_L1_L2_PROTOCOL_SCHEMA = "ewm.han-l1-l2.protocol.v1"
HAN_L1_L2_REPORT_SCHEMA = "ewm.han-l1-l2.report.v1"
DEFAULT_HAN_L1_L2_PROTOCOL = Path(__file__).parents[1] / "han-l1-l2-validation-v1.toml"
_CLASSIFICATION = "synthetic_systems_conformance"
_EXCLUDED_CLAIMS = (
    "empirical_validation",
    "prospective_behavioral_study",
)
_REQUIREMENTS = frozenset(
    {
        "agent_world_execution",
        "endogenous_environment",
        "economic_invariants",
        "adaptive_agent_state",
        "longitudinal_persistence",
    }
)
_OPERATORS = frozenset({"eq", "gte", "lte"})
_ARMS = ("adaptive", "fixed_beliefs")
_TOP_LEVEL_KEYS = frozenset(
    {
        "arms",
        "classification",
        "excluded_claims",
        "periods",
        "protocol_filename",
        "protocol_version",
        "report_schema",
        "requirement",
        "scenario",
        "schema_version",
        "seeds",
        "source_files",
    }
)
_REQUIREMENT_KEYS = frozenset(
    {"criteria", "evidence_kind", "level", "minimum_observations", "requirement"}
)
_CRITERION_KEYS = frozenset({"metric", "operator", "value"})


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
    directory = Path(__file__).parents[1]
    for name in sorted(source_files):
        path = Path(name)
        if (
            path.is_absolute()
            or path.suffix != ".py"
            or path.as_posix() != name
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise ValueError("validation source files must be safe local Python paths")
        source = directory / name
        if not source.is_file():
            raise FileNotFoundError(f"validation source file is missing: {name}")
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class HanValidationCriterion:
    """One declared metric threshold in the shipped validation contract."""

    metric: str
    operator: str
    value: float

    def __post_init__(self) -> None:
        if not self.metric:
            raise ValueError("validation criterion metric must not be empty")
        if self.operator not in _OPERATORS:
            raise ValueError(f"unsupported validation operator {self.operator!r}")
        if not math.isfinite(self.value):
            raise ValueError("validation criterion value must be finite")


@dataclass(frozen=True, slots=True)
class HanRequirementProtocol:
    """Evidence class, observation floor, and criteria for one Han requirement."""

    requirement: str
    level: str
    evidence_kind: str
    minimum_observations: int
    criteria: tuple[HanValidationCriterion, ...]

    def __post_init__(self) -> None:
        if self.requirement not in _REQUIREMENTS:
            raise ValueError(f"unsupported Han requirement {self.requirement!r}")
        expected_kind = "synthetic_test" if self.level == "L1" else "controlled_experiment"
        if self.level not in {"L1", "L2"} or self.evidence_kind != expected_kind:
            raise ValueError("Han L1/L2 evidence class does not match its declared level")
        if self.minimum_observations < 1:
            raise ValueError("minimum observations must be positive")
        if not self.criteria:
            raise ValueError("every Han requirement must declare criteria")
        object.__setattr__(self, "criteria", tuple(self.criteria))


@dataclass(frozen=True, slots=True)
class HanValidationProtocol:
    """Owned, hashed configuration for one deterministic validation execution."""

    schema_version: str
    protocol_version: int
    protocol_filename: str
    report_schema: str
    classification: str
    excluded_claims: tuple[str, ...]
    scenario: str
    seeds: tuple[int, ...]
    periods: int
    arms: tuple[str, ...]
    source_files: tuple[str, ...]
    requirements: tuple[HanRequirementProtocol, ...]
    protocol_sha256: str
    source_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != HAN_L1_L2_PROTOCOL_SCHEMA:
            raise ValueError(f"unsupported Han validation protocol {self.schema_version!r}")
        if self.protocol_version != 1:
            raise ValueError(
                f"unsupported Han validation protocol version {self.protocol_version!r}"
            )
        if self.protocol_filename != DEFAULT_HAN_L1_L2_PROTOCOL.name:
            raise ValueError("Han validation protocol filename does not match version 1")
        if self.report_schema != HAN_L1_L2_REPORT_SCHEMA:
            raise ValueError(f"unsupported Han validation report {self.report_schema!r}")
        if self.classification != _CLASSIFICATION:
            raise ValueError("Han validation must be labeled synthetic systems conformance")
        if self.excluded_claims != _EXCLUDED_CLAIMS:
            raise ValueError("Han validation must explicitly exclude empirical study claims")
        if self.scenario != "fx":
            raise ValueError("Han L1/L2 validation requires the compiled FX scenario")
        if len(self.seeds) < 2 or len(self.seeds) != len(set(self.seeds)):
            raise ValueError("Han validation requires at least two unique seeds")
        if self.periods < 2:
            raise ValueError("Han validation requires at least two periods")
        if self.arms != _ARMS:
            raise ValueError("Han L2 validation requires adaptive and fixed-belief arms")
        if not self.source_files or len(self.source_files) != len(set(self.source_files)):
            raise ValueError("Han validation source files must be unique and nonempty")
        names = tuple(item.requirement for item in self.requirements)
        if len(names) != len(set(names)) or set(names) != _REQUIREMENTS:
            raise ValueError("Han validation must declare each L1/L2 requirement once")
        for digest in (self.protocol_sha256, self.source_sha256):
            if len(digest) != 64:
                raise ValueError("Han validation identities must be SHA-256 digests")
        object.__setattr__(self, "seeds", tuple(self.seeds))
        object.__setattr__(self, "arms", tuple(self.arms))
        object.__setattr__(self, "source_files", tuple(self.source_files))
        object.__setattr__(self, "requirements", tuple(self.requirements))


@dataclass(frozen=True, slots=True)
class HanCriterionResult:
    """One observed metric compared with its prespecified threshold."""

    metric: str
    operator: str
    expected: float
    observed: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "expected": self.expected,
            "metric": self.metric,
            "observed": self.observed,
            "operator": self.operator,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class HanRequirementResult:
    """Independent observed result for one capability requirement."""

    requirement: str
    level: str
    evidence_kind: str
    observations: int
    passed: bool
    criteria: tuple[HanCriterionResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "criteria", tuple(self.criteria))

    def as_dict(self) -> dict[str, Any]:
        return {
            "criteria": [item.as_dict() for item in self.criteria],
            "evidence_kind": self.evidence_kind,
            "level": self.level,
            "observations": self.observations,
            "passed": self.passed,
            "requirement": self.requirement,
        }


@dataclass(frozen=True, slots=True)
class HanRunEvidence:
    """Canonical events and longitudinal state observations for one seed."""

    arm: str
    seed: int
    agent_ids: tuple[str, ...]
    state_observations: tuple[Mapping[str, Any], ...]
    events: tuple[Mapping[str, Any], ...]
    event_chain_hash: str

    def __post_init__(self) -> None:
        if self.arm not in _ARMS:
            raise ValueError(f"unsupported Han validation arm {self.arm!r}")
        if len(self.event_chain_hash) != 64:
            raise ValueError("Han run event identity must be a SHA-256 digest")
        object.__setattr__(self, "agent_ids", tuple(self.agent_ids))
        object.__setattr__(
            self,
            "state_observations",
            tuple(
                cast(Mapping[str, Any], freeze_value(dict(item)))
                for item in self.state_observations
            ),
        )
        object.__setattr__(
            self,
            "events",
            tuple(cast(Mapping[str, Any], freeze_value(dict(item))) for item in self.events),
        )

    def as_dict(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            _json_data(
                {
                    "arm": self.arm,
                    "agent_ids": self.agent_ids,
                    "event_chain_hash": self.event_chain_hash,
                    "events": self.events,
                    "seed": self.seed,
                    "state_observations": self.state_observations,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class HanValidationReport:
    """Hashed synthetic conformance report derived from compiled FX executions."""

    schema_version: str
    protocol_schema: str
    classification: str
    excluded_claims: tuple[str, ...]
    protocol_sha256: str
    source_sha256: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    metrics: Mapping[str, float]
    runs: tuple[HanRunEvidence, ...]
    requirements: tuple[HanRequirementResult, ...]
    report_sha256: str = ""

    def __post_init__(self) -> None:
        if self.report_sha256 and len(self.report_sha256) != 64:
            raise ValueError("Han report identity must be a SHA-256 digest")
        object.__setattr__(self, "excluded_claims", tuple(self.excluded_claims))
        object.__setattr__(self, "seeds", tuple(self.seeds))
        object.__setattr__(self, "arms", tuple(self.arms))
        object.__setattr__(
            self,
            "metrics",
            cast(Mapping[str, float], freeze_value(dict(self.metrics))),
        )
        object.__setattr__(self, "runs", tuple(self.runs))
        object.__setattr__(self, "requirements", tuple(self.requirements))

    def as_dict(self, *, include_report_hash: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "arms": list(self.arms),
            "classification": self.classification,
            "excluded_claims": list(self.excluded_claims),
            "metrics": dict(self.metrics),
            "protocol_schema": self.protocol_schema,
            "protocol_sha256": self.protocol_sha256,
            "requirements": [item.as_dict() for item in self.requirements],
            "runs": [item.as_dict() for item in self.runs],
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "source_sha256": self.source_sha256,
        }
        if include_report_hash:
            result["report_sha256"] = self.report_sha256
        return cast(dict[str, Any], _json_data(result))


def load_han_l1_l2_protocol(
    protocol_path: Path = DEFAULT_HAN_L1_L2_PROTOCOL,
) -> HanValidationProtocol:
    """Load and validate the shipped synthetic-systems contract."""

    content = protocol_path.read_bytes()
    raw = _mapping(
        tomllib.loads(content.decode("utf-8")),
        label="Han validation protocol",
    )
    _require_exact_keys(raw, _TOP_LEVEL_KEYS, label="Han protocol")
    protocol_filename = _string(
        raw["protocol_filename"],
        label="protocol filename",
    )
    if protocol_path.name != protocol_filename:
        raise ValueError("Han validation protocol path does not match declared filename")
    requirements: list[HanRequirementProtocol] = []
    for index, item in enumerate(_sequence(raw["requirement"], label="Han protocol requirements")):
        record = _mapping(item, label=f"Han requirement {index}")
        _require_exact_keys(
            record,
            _REQUIREMENT_KEYS,
            label=f"Han requirement {index}",
        )
        criteria: list[HanValidationCriterion] = []
        for criterion_index, raw_criterion in enumerate(
            _sequence(record["criteria"], label="Han requirement criteria")
        ):
            criterion = _mapping(
                raw_criterion,
                label=f"Han validation criterion {criterion_index}",
            )
            _require_exact_keys(
                criterion,
                _CRITERION_KEYS,
                label=f"Han validation criterion {criterion_index}",
            )
            criteria.append(
                HanValidationCriterion(
                    metric=_string(criterion["metric"], label="criterion metric"),
                    operator=_string(
                        criterion["operator"],
                        label="criterion operator",
                    ),
                    value=_number(criterion["value"], label="criterion value"),
                )
            )
        requirements.append(
            HanRequirementProtocol(
                requirement=_string(record["requirement"], label="requirement"),
                level=_string(record["level"], label="requirement level"),
                evidence_kind=_string(
                    record["evidence_kind"],
                    label="requirement evidence kind",
                ),
                minimum_observations=_integer(
                    record["minimum_observations"],
                    label="minimum observations",
                ),
                criteria=tuple(criteria),
            )
        )
    sources = tuple(
        _string(item, label="validation source file")
        for item in _sequence(raw["source_files"], label="validation source files")
    )
    return HanValidationProtocol(
        schema_version=_string(raw["schema_version"], label="protocol schema"),
        protocol_version=_integer(
            raw["protocol_version"],
            label="protocol version",
        ),
        protocol_filename=protocol_filename,
        report_schema=_string(raw["report_schema"], label="report schema"),
        classification=_string(raw["classification"], label="classification"),
        excluded_claims=tuple(
            _string(item, label="excluded claim")
            for item in _sequence(raw["excluded_claims"], label="excluded claims")
        ),
        scenario=_string(raw["scenario"], label="scenario"),
        seeds=tuple(
            _integer(item, label="validation seed")
            for item in _sequence(raw["seeds"], label="validation seeds")
        ),
        periods=_integer(raw["periods"], label="validation periods"),
        arms=tuple(
            _string(item, label="validation arm")
            for item in _sequence(raw["arms"], label="validation arms")
        ),
        source_files=sources,
        requirements=tuple(requirements),
        protocol_sha256=_sha256(content),
        source_sha256=_source_sha256(sources),
    )


def _json_data(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _event_record(event: Event) -> Mapping[str, Any]:
    return cast(
        Mapping[str, Any],
        _json_data(
            {
                "event_hash": event.event_hash,
                "kind": event.kind,
                "payload": event.payload,
                "previous_hash": event.previous_hash,
                "schema_version": event.schema_version,
                "sequence": event.sequence,
                "state_version": event.state_version,
            }
        ),
    )


def _state_observation(state: FXState, codec: Any) -> Mapping[str, Any]:
    belief_lengths = tuple(len(item.observations) for item in state.beliefs.values())
    return {
        "account_ids": tuple(state.accounts),
        "adapted_household_count": sum(length > 0 for length in belief_lengths),
        "belief_observation_count": sum(belief_lengths),
        "maximum_belief_observations": max(belief_lengths, default=0),
        "period": state.period,
        "spot": state.spot,
        "state_digest": state_digest(codec, state),
    }


def _run_seed(
    protocol: HanValidationProtocol,
    *,
    seed: int,
    arm: str,
) -> HanRunEvidence:
    config = smoke_config(periods=protocol.periods)
    if arm == "fixed_beliefs":
        config = replace(config, adaptive_beliefs=False)
    elif arm != "adaptive":
        raise ValueError(f"unsupported Han validation arm {arm!r}")
    world = fx_world_blueprint(config).compile()
    codec = world.state_codec
    if codec is None:
        raise RuntimeError("compiled FX validation world requires a state codec")
    state = world.reset(seed=seed)
    if not isinstance(state, FXState):
        raise TypeError("compiled FX validation world returned a non-FX state")
    observations: list[Mapping[str, Any]] = [_state_observation(state, codec)]
    for _ in range(protocol.periods):
        state = world.step(world.run_agents(state)).state
        if not isinstance(state, FXState):
            raise TypeError("compiled FX validation transition returned a non-FX state")
        observations.append(_state_observation(state, codec))
    events = world.events.snapshot()
    return HanRunEvidence(
        arm=arm,
        seed=seed,
        agent_ids=world.agent_ids,
        state_observations=tuple(observations),
        events=tuple(_event_record(event) for event in events),
        event_chain_hash=verify_event_chain(events),
    )


def _event_from_record(record: Mapping[str, Any]) -> Event:
    state_version = record.get("state_version")
    return Event(
        sequence=_integer(record.get("sequence"), label="event sequence"),
        kind=_string(record.get("kind"), label="event kind"),
        payload=_mapping(record.get("payload"), label="event payload"),
        schema_version=_string(record.get("schema_version"), label="event schema"),
        state_version=(
            None if state_version is None else _integer(state_version, label="event state version")
        ),
        previous_hash=_string(record.get("previous_hash"), label="event previous hash"),
        event_hash=_string(record.get("event_hash"), label="event hash"),
    )


def _derive_metrics(runs: tuple[HanRunEvidence, ...]) -> dict[str, float]:
    step_events = tuple(
        event for run in runs for event in run.events if event.get("kind") == "step"
    )
    outcomes = tuple(
        _mapping(
            _mapping(event.get("payload"), label="step payload").get("outcomes"),
            label="step outcomes",
        )
        for event in step_events
    )
    state_digests = {
        str(observation["state_digest"]) for run in runs for observation in run.state_observations
    }
    state_transition_count = sum(
        _mapping(event["payload"], label="step payload")["before_state_digest"]
        != _mapping(event["payload"], label="step payload")["after_state_digest"]
        for event in step_events
    )
    period_advance_count = sum(
        int(right["period"]) == int(left["period"]) + 1
        for run in runs
        for left, right in zip(
            run.state_observations[:-1],
            run.state_observations[1:],
            strict=True,
        )
    )
    adaptive_arm_observations = tuple(
        observation
        for run in runs
        if run.arm == "adaptive"
        for observation in run.state_observations[1:]
    )
    fixed_arm_observations = tuple(
        observation
        for run in runs
        if run.arm == "fixed_beliefs"
        for observation in run.state_observations[1:]
    )
    adaptive_household_observations = sum(
        int(item["adapted_household_count"]) for item in adaptive_arm_observations
    )
    fixed_household_observations = sum(
        int(item["adapted_household_count"]) for item in fixed_arm_observations
    )
    seeds_by_arm = {arm: {run.seed for run in runs if run.arm == arm} for arm in _ARMS}
    paired_seeds = seeds_by_arm["adaptive"] & seeds_by_arm["fixed_beliefs"]
    persistent_runs = sum(
        all(
            set(str(item) for item in observation["account_ids"]) == set(run.agent_ids)
            for observation in run.state_observations
        )
        for run in runs
    )
    return {
        "accepted_action_count": float(
            sum(
                int(_mapping(event["payload"], label="step payload")["accepted_count"])
                for event in step_events
            )
        ),
        "adaptation_observation_contrast": float(
            adaptive_household_observations - fixed_household_observations
        ),
        "adaptive_arm_adapted_household_observation_count": float(adaptive_household_observations),
        "adaptive_arm_state_observation_count": float(len(adaptive_arm_observations)),
        "canonical_event_chain_count": float(len(runs)),
        "compiled_run_count": float(len(runs)),
        "completed_step_count": float(len(step_events)),
        "distinct_state_digest_count": float(len(state_digests)),
        "fixed_arm_adapted_household_observation_count": float(fixed_household_observations),
        "longitudinal_observation_count": float(sum(len(run.state_observations) for run in runs)),
        "max_belief_observations": float(
            max(
                int(observation["maximum_belief_observations"])
                for run in runs
                for observation in run.state_observations
            )
        ),
        "max_cash_residual": max(
            (abs(float(item["cash_residual"])) for item in outcomes),
            default=0.0,
        ),
        "max_clearing_residual": max(
            (abs(float(item["clearing_residual"])) for item in outcomes),
            default=0.0,
        ),
        "max_foreign_residual": max(
            (abs(float(item["foreign_residual"])) for item in outcomes),
            default=0.0,
        ),
        "minimum_run_observations": float(
            min((len(run.state_observations) for run in runs), default=0)
        ),
        "period_advance_count": float(period_advance_count),
        "paired_seed_count": float(len(paired_seeds)),
        "persistent_agent_run_count": float(persistent_runs),
        "rejected_order_count": float(sum(int(item["rejected_count"]) for item in outcomes)),
        "state_transition_count": float(state_transition_count),
    }


def _criterion_passes(criterion: HanValidationCriterion, observed: float) -> bool:
    if criterion.operator == "eq":
        return observed == criterion.value
    if criterion.operator == "gte":
        return observed >= criterion.value
    if criterion.operator == "lte":
        return observed <= criterion.value
    raise AssertionError("validated Han criterion operator became unreachable")


def _observation_count(requirement: str, metrics: Mapping[str, float]) -> int:
    metric = {
        "agent_world_execution": "completed_step_count",
        "endogenous_environment": "state_transition_count",
        "economic_invariants": "completed_step_count",
        "adaptive_agent_state": "adaptive_arm_state_observation_count",
        "longitudinal_persistence": "longitudinal_observation_count",
    }[requirement]
    return int(metrics[metric])


def _evaluate_requirements(
    protocol: HanValidationProtocol,
    metrics: Mapping[str, float],
) -> tuple[HanRequirementResult, ...]:
    results: list[HanRequirementResult] = []
    for requirement in protocol.requirements:
        criteria = tuple(
            HanCriterionResult(
                metric=criterion.metric,
                operator=criterion.operator,
                expected=criterion.value,
                observed=metrics[criterion.metric],
                passed=_criterion_passes(criterion, metrics[criterion.metric]),
            )
            for criterion in requirement.criteria
        )
        observations = _observation_count(requirement.requirement, metrics)
        results.append(
            HanRequirementResult(
                requirement=requirement.requirement,
                level=requirement.level,
                evidence_kind=requirement.evidence_kind,
                observations=observations,
                passed=(
                    observations >= requirement.minimum_observations
                    and all(item.passed for item in criteria)
                ),
                criteria=criteria,
            )
        )
    return tuple(results)


def run_han_l1_l2_validation(
    *,
    protocol_path: Path = DEFAULT_HAN_L1_L2_PROTOCOL,
) -> HanValidationReport:
    """Execute the prespecified compiled FX runs and return observed evidence."""

    protocol = load_han_l1_l2_protocol(protocol_path)
    runs = tuple(
        _run_seed(protocol, seed=seed, arm=arm) for arm in protocol.arms for seed in protocol.seeds
    )
    metrics = _derive_metrics(runs)
    report = HanValidationReport(
        schema_version=protocol.report_schema,
        protocol_schema=protocol.schema_version,
        classification=protocol.classification,
        excluded_claims=protocol.excluded_claims,
        protocol_sha256=protocol.protocol_sha256,
        source_sha256=protocol.source_sha256,
        seeds=protocol.seeds,
        arms=protocol.arms,
        metrics=metrics,
        runs=runs,
        requirements=_evaluate_requirements(protocol, metrics),
    )
    report = replace(
        report,
        report_sha256=content_digest(report.as_dict(include_report_hash=False)),
    )
    verify_han_l1_l2_report(report, protocol_path=protocol_path)
    return report


def verify_han_l1_l2_report(
    report: HanValidationReport,
    *,
    protocol_path: Path = DEFAULT_HAN_L1_L2_PROTOCOL,
) -> None:
    """Reject report, protocol, source, event, metric, or criterion tampering."""

    expected_report_hash = content_digest(report.as_dict(include_report_hash=False))
    if report.report_sha256 != expected_report_hash:
        raise ValueError("Han validation report SHA-256 does not match its contents")
    protocol = load_han_l1_l2_protocol(protocol_path)
    if report.protocol_sha256 != protocol.protocol_sha256:
        raise ValueError("Han validation protocol SHA-256 does not match")
    if report.source_sha256 != protocol.source_sha256:
        raise ValueError("Han validation source SHA-256 does not match")
    if (
        report.schema_version != protocol.report_schema
        or report.protocol_schema != protocol.schema_version
        or report.classification != protocol.classification
        or report.excluded_claims != protocol.excluded_claims
        or report.seeds != protocol.seeds
        or report.arms != protocol.arms
    ):
        raise ValueError("Han validation report identity does not match its protocol")
    expected_runs = tuple((arm, seed) for arm in protocol.arms for seed in protocol.seeds)
    if tuple((run.arm, run.seed) for run in report.runs) != expected_runs:
        raise ValueError("Han validation arms and seeds do not match the protocol")
    for run in report.runs:
        events = tuple(_event_from_record(item) for item in run.events)
        if verify_event_chain(events) != run.event_chain_hash:
            raise ValueError("Han validation canonical event chain does not match")
    expected_metrics = _derive_metrics(report.runs)
    if dict(report.metrics) != expected_metrics:
        raise ValueError("Han validation metrics do not match observed runs")
    expected_requirements = _evaluate_requirements(protocol, expected_metrics)
    if tuple(item.as_dict() for item in report.requirements) != tuple(
        item.as_dict() for item in expected_requirements
    ):
        raise ValueError("Han validation requirement results do not match criteria")


def han_l1_l2_artifacts(
    report: HanValidationReport,
    *,
    protocol_path: Path = DEFAULT_HAN_L1_L2_PROTOCOL,
) -> tuple[ValidatedEvidenceArtifact, ...]:
    """Construct one independent artifact from each actual requirement result."""

    verify_han_l1_l2_report(report, protocol_path=protocol_path)
    return tuple(
        ValidatedEvidenceArtifact.from_observation(
            subject=f"capability:{requirement.requirement}",
            status=(EvidenceStatus.PASS if requirement.passed else EvidenceStatus.FAIL),
            provenance=f"{protocol_path.name}:{report.report_sha256}",
            payload={
                "protocol_sha256": report.protocol_sha256,
                "report_schema": report.schema_version,
                "report_sha256": report.report_sha256,
                "requirement_result": requirement.as_dict(),
                "source_sha256": report.source_sha256,
            },
            observations=requirement.observations,
        )
        for requirement in report.requirements
    )
