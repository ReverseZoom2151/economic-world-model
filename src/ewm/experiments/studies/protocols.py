"""Contracts for prospectively locked scientific protocols."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Literal, cast

import numpy as np

ProtocolMode = Literal["quick", "full"]
OutcomeKind = Literal["paired_continuous", "binary"]
DEFAULT_PROTOCOL_PATH = Path(__file__).resolve().parents[2] / "protocols" / (
    "credit-mechanism-v1.toml"
)


class ProtocolValidationError(ValueError):
    """Raised when a protocol file does not satisfy the locked schema."""


@dataclass(frozen=True, slots=True)
class SampleSizeSpec:
    """Fixed replication and population sizes for both execution modes."""

    quick_replications: int
    full_replications: int
    quick_population: int
    full_population: int


@dataclass(frozen=True, slots=True)
class StoppingSpec:
    """Immutable fixed-sample stopping rule."""

    rule: str
    interim_looks: int
    stop_on_failure: bool


@dataclass(frozen=True, slots=True)
class MultiplicitySpec:
    """Prespecified family-wise error correction."""

    method: str
    family: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SeedManifest:
    """Exact integer seeds derived from NumPy SeedSequence children."""

    method: str
    entropy: int
    spawn_count: int
    seeds: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class BootstrapSpec:
    """Owned bootstrap randomness and fixed resampling counts."""

    method: str
    quick_resamples: int
    full_resamples: int
    seed_method: str
    seed_entropy: int
    seeds: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class OutcomeSpec:
    """One immutable outcome and its analysis method."""

    name: str
    kind: OutcomeKind
    method: str
    direction: str
    unit: str
    null: str
    interpretation: str
    baseline_metric: str | None = None
    intervention_metric: str | None = None
    robustness: str | None = None
    success_definition: str | None = None


@dataclass(frozen=True, slots=True)
class ToleranceSpec:
    """One named non-negative numerical acceptance tolerance."""

    name: str
    maximum: float


@dataclass(frozen=True, slots=True)
class ScientificProtocol:
    """Fully parsed immutable local scientific protocol."""

    schema_version: str
    protocol_id: str
    protocol_version: int
    lock_status: str
    experiment: str
    confidence: float
    alpha: float
    sample_size_rationale: str
    sample_sizes: SampleSizeSpec
    stopping: StoppingSpec
    multiplicity: MultiplicitySpec
    seed_manifest: SeedManifest
    bootstrap: BootstrapSpec
    outcomes: tuple[OutcomeSpec, ...]
    tolerances: tuple[ToleranceSpec, ...]
    content_sha256: str
    semantic_sha256: str

    def replication_count(self, mode: ProtocolMode) -> int:
        """Return the locked replication count for an execution mode."""

        return (
            self.sample_sizes.quick_replications
            if mode == "quick"
            else self.sample_sizes.full_replications
        )

    def population_size(self, mode: ProtocolMode) -> int:
        """Return the locked synthetic population size for an execution mode."""

        return (
            self.sample_sizes.quick_population
            if mode == "quick"
            else self.sample_sizes.full_population
        )

    def bootstrap_resamples(self, mode: ProtocolMode) -> int:
        """Return the locked bootstrap resampling count for an execution mode."""

        return (
            self.bootstrap.quick_resamples
            if mode == "quick"
            else self.bootstrap.full_resamples
        )

    def tolerance(self, name: str) -> float:
        """Return a named locked tolerance, failing closed when it is absent."""

        for tolerance in self.tolerances:
            if tolerance.name == name:
                return tolerance.maximum
        raise ProtocolValidationError(f"protocol does not define tolerance {name!r}")


@dataclass(frozen=True, slots=True)
class ProtocolIssue:
    """Machine-readable execution deviation or failure."""

    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class ProtocolAudit:
    """Deviations from the plan and scientific failures, kept separate."""

    deviations: tuple[ProtocolIssue, ...]
    failures: tuple[ProtocolIssue, ...]

    @property
    def passed(self) -> bool:
        """Only exact, failure-free execution passes."""

        return not self.deviations and not self.failures


def spawn_seed_manifest(*, entropy: int, count: int) -> tuple[int, ...]:
    """Generate exact uint64 seeds from independent SeedSequence children."""

    if entropy < 0:
        raise ValueError("entropy must be non-negative")
    if count < 1:
        raise ValueError("count must be positive")
    children = np.random.SeedSequence(entropy).spawn(count)
    return tuple(
        int(child.generate_state(1, dtype=np.uint64)[0]) for child in children
    )


def load_protocol(path: str | Path) -> ScientificProtocol:
    """Load, hash, and validate a versioned TOML protocol without mutable defaults."""

    protocol_path = Path(path)
    raw_bytes = protocol_path.read_bytes()
    normalized_bytes = raw_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    content_sha256 = hashlib.sha256(normalized_bytes).hexdigest()
    try:
        parsed = cast(dict[str, object], tomllib.loads(normalized_bytes.decode("utf-8")))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ProtocolValidationError(f"invalid protocol TOML: {error}") from error
    semantic_bytes = json.dumps(
        parsed,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    semantic_sha256 = hashlib.sha256(semantic_bytes).hexdigest()
    _require_exact_keys(
        parsed,
        {
            "alpha",
            "bootstrap",
            "confidence",
            "experiment",
            "lock_status",
            "multiplicity",
            "outcomes",
            "protocol_id",
            "protocol_version",
            "sample_size_rationale",
            "sample_sizes",
            "schema_version",
            "seed_manifest",
            "stopping",
            "tolerances",
        },
        "protocol",
    )

    schema_version = _string(parsed["schema_version"], "schema_version")
    protocol_id = _string(parsed["protocol_id"], "protocol_id")
    protocol_version = _integer(parsed["protocol_version"], "protocol_version")
    lock_status = _string(parsed["lock_status"], "lock_status")
    experiment = _string(parsed["experiment"], "experiment")
    confidence = _number(parsed["confidence"], "confidence")
    alpha = _number(parsed["alpha"], "alpha")
    sample_size_rationale = _string(
        parsed["sample_size_rationale"], "sample_size_rationale"
    )
    if schema_version != "ewm.local-scientific-protocol.v1":
        raise ProtocolValidationError("unsupported protocol schema_version")
    if protocol_version < 1 or not protocol_path.stem.endswith(f"-v{protocol_version}"):
        raise ProtocolValidationError("protocol filename and protocol_version must agree")
    if lock_status != "prospectively locked locally":
        raise ProtocolValidationError("protocol lock_status is not recognized")
    _validate_probability(confidence, "confidence")
    _validate_probability(alpha, "alpha")

    sample_sizes = _parse_sample_sizes(parsed["sample_sizes"])
    stopping = _parse_stopping(parsed["stopping"])
    multiplicity = _parse_multiplicity(parsed["multiplicity"])
    seed_manifest = _parse_seed_manifest(parsed["seed_manifest"])
    bootstrap = _parse_bootstrap(parsed["bootstrap"])
    outcomes = _parse_outcomes(parsed["outcomes"])
    tolerances = _parse_tolerances(parsed["tolerances"])
    _validate_cross_fields(
        sample_sizes=sample_sizes,
        stopping=stopping,
        multiplicity=multiplicity,
        seed_manifest=seed_manifest,
        bootstrap=bootstrap,
        outcomes=outcomes,
        tolerances=tolerances,
    )
    return ScientificProtocol(
        schema_version=schema_version,
        protocol_id=protocol_id,
        protocol_version=protocol_version,
        lock_status=lock_status,
        experiment=experiment,
        confidence=confidence,
        alpha=alpha,
        sample_size_rationale=sample_size_rationale,
        sample_sizes=sample_sizes,
        stopping=stopping,
        multiplicity=multiplicity,
        seed_manifest=seed_manifest,
        bootstrap=bootstrap,
        outcomes=outcomes,
        tolerances=tolerances,
        content_sha256=content_sha256,
        semantic_sha256=semantic_sha256,
    )


def audit_protocol_execution(
    protocol: ScientificProtocol,
    *,
    mode: ProtocolMode,
    observed_protocol_sha256: str,
    executed_seeds: tuple[int, ...],
    completed_replications: int,
    observed_outcomes: tuple[str, ...],
    stopped_early: bool,
    tolerance_breaches: tuple[str, ...],
) -> ProtocolAudit:
    """Compare observed execution with the locked contract and retain every issue."""

    expected_count = protocol.replication_count(mode)
    expected_seeds = protocol.seed_manifest.seeds[:expected_count]
    expected_outcomes = tuple(outcome.name for outcome in protocol.outcomes)
    deviations: list[ProtocolIssue] = []
    failures: list[ProtocolIssue] = []
    if observed_protocol_sha256 != protocol.content_sha256:
        deviations.append(
            ProtocolIssue("protocol_hash_mismatch", "executed protocol hash differs from lock")
        )
    if executed_seeds != expected_seeds:
        deviations.append(
            ProtocolIssue("seed_manifest_mismatch", "executed seeds differ from locked prefix")
        )
    if completed_replications != expected_count:
        deviations.append(
            ProtocolIssue(
                "sample_size_mismatch",
                f"completed {completed_replications}, expected {expected_count}",
            )
        )
    if stopped_early:
        deviations.append(
            ProtocolIssue("unplanned_early_stop", "fixed-sample protocol stopped early")
        )
    missing = tuple(name for name in expected_outcomes if name not in observed_outcomes)
    unexpected = tuple(name for name in observed_outcomes if name not in expected_outcomes)
    if missing:
        failures.append(ProtocolIssue("missing_outcomes", ", ".join(missing)))
    if unexpected:
        failures.append(ProtocolIssue("unexpected_outcomes", ", ".join(unexpected)))
    if tolerance_breaches:
        failures.append(
            ProtocolIssue("tolerance_breach", ", ".join(tolerance_breaches))
        )
    return ProtocolAudit(deviations=tuple(deviations), failures=tuple(failures))


def _parse_sample_sizes(value: object) -> SampleSizeSpec:
    table = _table(value, "sample_sizes")
    keys = {
        "full_population",
        "full_replications",
        "quick_population",
        "quick_replications",
    }
    _require_exact_keys(table, keys, "sample_sizes")
    spec = SampleSizeSpec(
        quick_replications=_integer(table["quick_replications"], "quick_replications"),
        full_replications=_integer(table["full_replications"], "full_replications"),
        quick_population=_integer(table["quick_population"], "quick_population"),
        full_population=_integer(table["full_population"], "full_population"),
    )
    if (
        spec.quick_replications < 2
        or spec.full_replications < spec.quick_replications
        or spec.quick_population < 100
        or spec.full_population < spec.quick_population
    ):
        raise ProtocolValidationError("sample_sizes must be ordered fixed positive sizes")
    return spec


def _parse_stopping(value: object) -> StoppingSpec:
    table = _table(value, "stopping")
    _require_exact_keys(table, {"interim_looks", "rule", "stop_on_failure"}, "stopping")
    return StoppingSpec(
        rule=_string(table["rule"], "stopping.rule"),
        interim_looks=_integer(table["interim_looks"], "stopping.interim_looks"),
        stop_on_failure=_boolean(table["stop_on_failure"], "stopping.stop_on_failure"),
    )


def _parse_multiplicity(value: object) -> MultiplicitySpec:
    table = _table(value, "multiplicity")
    _require_exact_keys(table, {"family", "method"}, "multiplicity")
    return MultiplicitySpec(
        method=_string(table["method"], "multiplicity.method"),
        family=_string_tuple(table["family"], "multiplicity.family"),
    )


def _parse_seed_manifest(value: object) -> SeedManifest:
    table = _table(value, "seed_manifest")
    _require_exact_keys(
        table,
        {"entropy", "method", "seeds", "spawn_count"},
        "seed_manifest",
    )
    manifest = SeedManifest(
        method=_string(table["method"], "seed_manifest.method"),
        entropy=_integer(table["entropy"], "seed_manifest.entropy"),
        spawn_count=_integer(table["spawn_count"], "seed_manifest.spawn_count"),
        seeds=_integer_tuple(table["seeds"], "seed_manifest.seeds"),
    )
    if manifest.method != "numpy.random.SeedSequence.spawn":
        raise ProtocolValidationError("seed manifest method is not supported")
    if manifest.seeds != spawn_seed_manifest(
        entropy=manifest.entropy,
        count=manifest.spawn_count,
    ):
        raise ProtocolValidationError("seed manifest does not match SeedSequence.spawn")
    return manifest


def _parse_bootstrap(value: object) -> BootstrapSpec:
    table = _table(value, "bootstrap")
    _require_exact_keys(
        table,
        {
            "full_resamples",
            "method",
            "quick_resamples",
            "seed_entropy",
            "seed_method",
            "seeds",
        },
        "bootstrap",
    )
    spec = BootstrapSpec(
        method=_string(table["method"], "bootstrap.method"),
        quick_resamples=_integer(table["quick_resamples"], "bootstrap.quick_resamples"),
        full_resamples=_integer(table["full_resamples"], "bootstrap.full_resamples"),
        seed_method=_string(table["seed_method"], "bootstrap.seed_method"),
        seed_entropy=_integer(table["seed_entropy"], "bootstrap.seed_entropy"),
        seeds=_integer_tuple(table["seeds"], "bootstrap.seeds"),
    )
    if spec.method != "paired_percentile" or spec.seed_method != (
        "numpy.random.SeedSequence.spawn"
    ):
        raise ProtocolValidationError("bootstrap methods are not supported")
    if spec.quick_resamples < 1 or spec.full_resamples < spec.quick_resamples:
        raise ProtocolValidationError("bootstrap resampling counts must be ordered and positive")
    if spec.seeds != spawn_seed_manifest(entropy=spec.seed_entropy, count=len(spec.seeds)):
        raise ProtocolValidationError("bootstrap seed manifest does not match SeedSequence.spawn")
    return spec


def _parse_outcomes(value: object) -> tuple[OutcomeSpec, ...]:
    rows = _list(value, "outcomes")
    outcomes: list[OutcomeSpec] = []
    for index, row_value in enumerate(rows):
        row = _table(row_value, f"outcomes[{index}]")
        kind = _string(row.get("kind"), f"outcomes[{index}].kind")
        if kind == "paired_continuous":
            _require_exact_keys(
                row,
                {
                    "baseline_metric",
                    "direction",
                    "interpretation",
                    "intervention_metric",
                    "kind",
                    "method",
                    "name",
                    "null",
                    "robustness",
                    "unit",
                },
                f"outcomes[{index}]",
            )
            outcomes.append(
                OutcomeSpec(
                    name=_string(row["name"], f"outcomes[{index}].name"),
                    kind="paired_continuous",
                    method=_string(row["method"], f"outcomes[{index}].method"),
                    direction=_string(
                        row["direction"], f"outcomes[{index}].direction"
                    ),
                    unit=_string(row["unit"], f"outcomes[{index}].unit"),
                    null=_string(row["null"], f"outcomes[{index}].null"),
                    interpretation=_string(
                        row["interpretation"], f"outcomes[{index}].interpretation"
                    ),
                    baseline_metric=_string(
                        row["baseline_metric"], f"outcomes[{index}].baseline_metric"
                    ),
                    intervention_metric=_string(
                        row["intervention_metric"],
                        f"outcomes[{index}].intervention_metric",
                    ),
                    robustness=_string(
                        row["robustness"], f"outcomes[{index}].robustness"
                    ),
                )
            )
        elif kind == "binary":
            _require_exact_keys(
                row,
                {
                    "direction",
                    "interpretation",
                    "kind",
                    "method",
                    "name",
                    "null",
                    "success_definition",
                    "unit",
                },
                f"outcomes[{index}]",
            )
            outcomes.append(
                OutcomeSpec(
                    name=_string(row["name"], f"outcomes[{index}].name"),
                    kind="binary",
                    method=_string(row["method"], f"outcomes[{index}].method"),
                    direction=_string(
                        row["direction"], f"outcomes[{index}].direction"
                    ),
                    unit=_string(row["unit"], f"outcomes[{index}].unit"),
                    null=_string(row["null"], f"outcomes[{index}].null"),
                    interpretation=_string(
                        row["interpretation"], f"outcomes[{index}].interpretation"
                    ),
                    success_definition=_string(
                        row["success_definition"],
                        f"outcomes[{index}].success_definition",
                    ),
                )
            )
        else:
            raise ProtocolValidationError(f"outcomes[{index}].kind is not supported")
    if not outcomes:
        raise ProtocolValidationError("protocol must define outcomes")
    return tuple(outcomes)


def _parse_tolerances(value: object) -> tuple[ToleranceSpec, ...]:
    rows = _list(value, "tolerances")
    tolerances: list[ToleranceSpec] = []
    for index, row_value in enumerate(rows):
        row = _table(row_value, f"tolerances[{index}]")
        _require_exact_keys(row, {"maximum", "name"}, f"tolerances[{index}]")
        maximum = _number(row["maximum"], f"tolerances[{index}].maximum")
        if maximum < 0.0:
            raise ProtocolValidationError("tolerances must be non-negative")
        tolerances.append(
            ToleranceSpec(
                name=_string(row["name"], f"tolerances[{index}].name"),
                maximum=maximum,
            )
        )
    return tuple(tolerances)


def _validate_cross_fields(
    *,
    sample_sizes: SampleSizeSpec,
    stopping: StoppingSpec,
    multiplicity: MultiplicitySpec,
    seed_manifest: SeedManifest,
    bootstrap: BootstrapSpec,
    outcomes: tuple[OutcomeSpec, ...],
    tolerances: tuple[ToleranceSpec, ...],
) -> None:
    if stopping != StoppingSpec("fixed_sample", 0, False):
        raise ProtocolValidationError("new protocols require fixed sampling without interim looks")
    if seed_manifest.spawn_count != sample_sizes.full_replications:
        raise ProtocolValidationError("seed manifest must cover the full fixed sample")
    outcome_names = tuple(outcome.name for outcome in outcomes)
    if len(set(outcome_names)) != len(outcome_names):
        raise ProtocolValidationError("outcome names must be unique")
    paired_names = tuple(
        outcome.name for outcome in outcomes if outcome.kind == "paired_continuous"
    )
    if multiplicity.method != "holm" or multiplicity.family != paired_names:
        raise ProtocolValidationError("Holm family must list all paired outcomes in order")
    if len(bootstrap.seeds) != len(paired_names):
        raise ProtocolValidationError("bootstrap seeds must cover every paired outcome")
    for outcome in outcomes:
        if outcome.kind == "paired_continuous" and (
            outcome.method != "paired_student_t_two_sided"
            or outcome.robustness != "paired_percentile_bootstrap"
        ):
            raise ProtocolValidationError("paired outcomes require Student-t and paired bootstrap")
        if outcome.kind == "binary" and outcome.method != "wilson":
            raise ProtocolValidationError("binary outcomes require Wilson intervals")
    tolerance_names = tuple(tolerance.name for tolerance in tolerances)
    if len(set(tolerance_names)) != len(tolerance_names):
        raise ProtocolValidationError("tolerance names must be unique")
    if set(tolerance_names) != {"comparison_slack", "solver_residual"}:
        raise ProtocolValidationError("protocol requires solver and comparison tolerances")


def _require_exact_keys(
    table: dict[str, object],
    expected: set[str],
    context: str,
) -> None:
    actual = set(table)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ProtocolValidationError(
            f"{context} keys differ; missing={missing}, unknown={unknown}"
        )


def _table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ProtocolValidationError(f"{context} must be a table")
    return cast(dict[str, object], value)


def _list(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise ProtocolValidationError(f"{context} must be an array")
    return cast(list[object], value)


def _string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProtocolValidationError(f"{context} must be a non-empty string")
    return value


def _boolean(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise ProtocolValidationError(f"{context} must be a boolean")
    return value


def _integer(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolValidationError(f"{context} must be an integer")
    return value


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ProtocolValidationError(f"{context} must be numeric")
    result = float(value)
    if not isfinite(result):
        raise ProtocolValidationError(f"{context} must be finite")
    return result


def _string_tuple(value: object, context: str) -> tuple[str, ...]:
    values = _list(value, context)
    return tuple(_string(item, context) for item in values)


def _integer_tuple(value: object, context: str) -> tuple[int, ...]:
    values = _list(value, context)
    return tuple(_integer(item, context) for item in values)


def _validate_probability(value: float, context: str) -> None:
    if not 0.0 < value < 1.0:
        raise ProtocolValidationError(f"{context} must lie in (0, 1)")
