from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from ewm.core import Action, EventLog, GeneratedDataset, RunMetadata


def test_run_metadata_and_action_are_immutable() -> None:
    metadata = RunMetadata(scenario="forecasting", seed=42, run_id="test")
    action = Action(agent_id="a", kind="hold", values={"history": [1, 2]})

    assert metadata.seed == 42
    assert action.kind == "hold"
    assert action.values["history"] == (1, 2)
    with pytest.raises(FrozenInstanceError):
        metadata.seed = 7  # type: ignore[misc]
    with pytest.raises(TypeError):
        action.values["amount"] = 1.0  # type: ignore[index]


def test_generated_dataset_owns_read_only_arrays() -> None:
    features = np.array([[1.0, 2.0]])
    targets = np.array([1.0])
    dataset = GeneratedDataset(features=features, targets=targets)
    features[0, 0] = 99.0

    assert dataset.features[0, 0] == 1.0
    assert not dataset.features.flags.writeable
    with pytest.raises(ValueError):
        dataset.targets[0] = 0.0


def test_event_log_deeply_freezes_payload_and_returns_snapshot() -> None:
    payload = {"seed": 1, "nested": {"values": [1, 2]}}
    log = EventLog()
    event = log.append("reset", payload)
    payload["nested"]["values"].append(3)

    snapshot = log.snapshot()
    assert snapshot == (event,)
    assert snapshot[0].sequence == 0
    assert snapshot[0].payload["nested"]["values"] == (1, 2)
    with pytest.raises(TypeError):
        snapshot[0].payload["seed"] = 2  # type: ignore[index]

