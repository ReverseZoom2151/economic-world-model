"""Verified artifact reconstruction and experiment replay."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from ewm.core import Event, ReplayReport, replay_bundle_from_events, replay_world
from ewm.scenarios.fx import FXSimulationConfig, fx_world_blueprint

from .identity import ARTIFACT_SCHEMA
from .verification import VerificationReport, verify_run

_EVENT_FIELDS = frozenset(
    {
        "event_hash",
        "kind",
        "payload",
        "previous_hash",
        "schema_version",
        "sequence",
        "state_version",
    }
)
_FX_PARAMETER_FIELDS = frozenset(
    {
        "adaptive_beliefs",
        "bank_depth",
        "bank_spread",
        "belief_memory",
        "firm_demand",
        "fundamental",
        "household_quantity",
        "households",
        "initial_spot",
        "periods",
        "trend_weight",
    }
)
_FX_INTEGER_FIELDS = frozenset({"belief_memory", "households", "periods"})
_FX_FLOAT_FIELDS = _FX_PARAMETER_FIELDS - _FX_INTEGER_FIELDS - {"adaptive_beliefs"}


class RunReplayError(ValueError):
    """Raised when a verified artifact cannot be replayed under its contract."""


def _snapshot_bytes(
    path: Path,
    *,
    expected_sha256: str,
    expected_size: int,
    label: str,
) -> bytes:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise RunReplayError(f"could not read verified {label}: {error}") from error
    if len(content) != expected_size:
        raise RunReplayError(f"verified {label} changed size before replay")
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise RunReplayError(f"verified {label} changed content before replay")
    return content


def _payload_snapshot(report: VerificationReport, filename: str) -> bytes:
    try:
        checksum = report.payloads[filename]
        expected_sha256 = checksum["sha256"]
        expected_size = checksum["size"]
    except KeyError as error:
        raise RunReplayError(f"verified run has no checksum for {filename}") from error
    if not isinstance(expected_sha256, str) or not isinstance(expected_size, int):
        raise RunReplayError(f"verified checksum metadata for {filename} is invalid")
    return _snapshot_bytes(
        report.run_dir / filename,
        expected_sha256=expected_sha256,
        expected_size=expected_size,
        label=filename,
    )


def _json_mapping(content: bytes, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunReplayError(f"verified {label} could not be parsed: {error}") from error
    if not isinstance(value, Mapping):
        raise RunReplayError(f"verified {label} must contain a JSON object")
    return cast(Mapping[str, Any], value)


def _owned_replay_inputs(
    report: VerificationReport,
) -> tuple[Mapping[str, Any], Mapping[str, Any], bytes]:
    manifest_bytes = _snapshot_bytes(
        report.run_dir / "manifest.json",
        expected_sha256=report.manifest_sha256,
        expected_size=report.manifest_size,
        label="manifest.json",
    )
    config_bytes = _payload_snapshot(report, "config.json")
    events_bytes = _payload_snapshot(report, "events.jsonl")
    manifest = _json_mapping(manifest_bytes, label="manifest.json")
    config = _json_mapping(config_bytes, label="config.json")
    if manifest.get("artifact_schema") != report.artifact_schema:
        raise RunReplayError("verified manifest schema does not match verification report")
    if manifest.get("run_hash") != report.run_hash:
        raise RunReplayError("verified manifest run hash does not match verification report")
    if manifest.get("identity_sha256") != report.identity_sha256:
        raise RunReplayError("verified manifest identity does not match verification report")
    if manifest.get("bundle_sha256") != report.bundle_sha256:
        raise RunReplayError("verified manifest bundle does not match verification report")
    return manifest, config, events_bytes


def _strict_fx_config(parameters: object) -> FXSimulationConfig:
    if not isinstance(parameters, Mapping):
        raise RunReplayError("verified FX parameters must be a JSON object")
    if frozenset(parameters) != _FX_PARAMETER_FIELDS:
        missing = sorted(_FX_PARAMETER_FIELDS - frozenset(parameters))
        extra = sorted(frozenset(parameters) - _FX_PARAMETER_FIELDS)
        raise RunReplayError(
            f"verified FX parameter fields differ: missing={missing}, extra={extra}"
        )
    values: dict[str, Any] = {}
    for field in _FX_INTEGER_FIELDS:
        value = parameters[field]
        if isinstance(value, bool) or not isinstance(value, int):
            raise RunReplayError(f"verified FX parameter {field} must be an integer")
        values[field] = value
    for field in _FX_FLOAT_FIELDS:
        value = parameters[field]
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise RunReplayError(f"verified FX parameter {field} must be numeric")
        values[field] = float(value)
    adaptive = parameters["adaptive_beliefs"]
    if not isinstance(adaptive, bool):
        raise RunReplayError("verified FX parameter adaptive_beliefs must be boolean")
    values["adaptive_beliefs"] = adaptive
    try:
        return FXSimulationConfig(**values)
    except (TypeError, ValueError) as error:
        raise RunReplayError(f"verified FX parameters are invalid: {error}") from error


def _event_records(content: bytes) -> tuple[Event, ...]:
    events: list[Event] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        record = _json_mapping(line, label=f"events.jsonl line {line_number}")
        if frozenset(record) != _EVENT_FIELDS:
            raise RunReplayError(
                f"events.jsonl line {line_number} has incompatible event fields"
            )
        sequence = record["sequence"]
        state_version = record["state_version"]
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise RunReplayError("event sequence must be an integer")
        if state_version is not None and (
            isinstance(state_version, bool) or not isinstance(state_version, int)
        ):
            raise RunReplayError("event state_version must be an integer or null")
        for field in ("event_hash", "kind", "previous_hash", "schema_version"):
            if not isinstance(record[field], str):
                raise RunReplayError(f"event {field} must be a string")
        payload = record["payload"]
        if not isinstance(payload, Mapping):
            raise RunReplayError("event payload must be a JSON object")
        events.append(
            Event(
                sequence=sequence,
                kind=record["kind"],
                payload=cast(Mapping[str, Any], payload),
                schema_version=record["schema_version"],
                state_version=state_version,
                previous_hash=record["previous_hash"],
                event_hash=record["event_hash"],
            )
        )
    return tuple(events)


def _replay_verified_fx(
    config_record: Mapping[str, Any],
    events_bytes: bytes,
) -> ReplayReport:
    if config_record.get("experiment") != "fx.rollout" or config_record.get(
        "scenario"
    ) != "fx":
        raise RunReplayError("replay currently supports only the fx.rollout experiment")
    seed = config_record.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise RunReplayError("verified FX seed must be an integer")
    config = _strict_fx_config(config_record.get("parameters"))
    events = _event_records(events_bytes)
    expected_kinds = ("reset",) + ("run_agents", "step") * config.periods
    if tuple(event.kind for event in events) != expected_kinds:
        raise RunReplayError("FX event lifecycle does not match configured periods")
    if events[0].payload.get("seed") != seed:
        raise RunReplayError("FX reset seed does not match verified run identity")
    world = fx_world_blueprint(config).compile()
    bundle = replay_bundle_from_events(world, events)
    return replay_world(world, bundle)


def verify_and_replay_run(run_dir: str | Path) -> ReplayReport:
    """Verify a sealed run snapshot and replay its supported compiled world."""

    report = verify_run(run_dir)
    if report.artifact_schema != ARTIFACT_SCHEMA or report.integrity_level != "checksummed":
        raise RunReplayError("replay requires a sealed v2 run artifact")
    try:
        _manifest, config, events_bytes = _owned_replay_inputs(report)
        return _replay_verified_fx(config, events_bytes)
    except RunReplayError:
        raise
    except (KeyError, NotImplementedError, RuntimeError, TypeError, ValueError) as error:
        raise RunReplayError(f"verified run replay failed: {error}") from error


__all__ = ["RunReplayError", "verify_and_replay_run"]
