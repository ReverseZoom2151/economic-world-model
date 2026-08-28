"""Runtime contracts for stochastic kernels."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pytest
from ewm.core.kernels import CallableStochasticKernel, CategoricalKernel


def test_categorical_kernel_validates_and_exposes_each_probability_row() -> None:
    kernel = CategoricalKernel(
        name="employment_transition",
        support=("employed", "unemployed"),
        probabilities={
            "employed": {"employed": 0.9, "unemployed": 0.1},
            "unemployed": {"employed": 0.4, "unemployed": 0.6},
        },
    )

    row = kernel.probabilities("employed")

    assert dict(row) == {"employed": 0.9, "unemployed": 0.1}
    with pytest.raises(TypeError):
        row["employed"] = 0.0  # type: ignore[index]
    with pytest.raises(KeyError, match="unknown kernel input"):
        kernel.probabilities("retired")


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ({"up": 0.8, "down": 0.3}, "sum to one"),
        ({"up": 1.1, "down": -0.1}, "finite and non-negative"),
        ({"up": 1.0000000000005, "down": 0.0}, "must not exceed one"),
        ({"up": float("nan"), "down": 0.0}, "finite and non-negative"),
        ({"up": 0.5, "outside": 0.5}, "outside declared support"),
        ({"up": 0.0, "down": 0.0}, "positive total mass"),
        ({}, "must not be empty"),
    ],
)
def test_categorical_kernel_rejects_invalid_probability_measures(
    row: Mapping[str, float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        CategoricalKernel(
            name="invalid",
            support=("up", "down"),
            probabilities={"state": row},
        )


def test_categorical_draw_matches_direct_inverse_cdf_and_records_rng_provenance() -> None:
    kernel = CategoricalKernel(
        name="binary_outcome",
        support=("loss", "gain"),
        probabilities={"state": {"loss": 0.25, "gain": 0.75}},
    )
    independent_rng = np.random.default_rng(91)
    uniform = float(independent_rng.random())
    expected = "loss" if uniform < 0.25 else "gain"
    first_rng = np.random.default_rng(91)
    second_rng = np.random.default_rng(91)

    first = kernel.sample("state", rng=first_rng, stream_id="replicate-0/kernel")
    repeated = kernel.sample("state", rng=second_rng, stream_id="replicate-0/kernel")
    next_draw = kernel.sample("state", rng=first_rng, stream_id="replicate-0/kernel")

    assert first.value == expected
    assert first.uniform == uniform
    assert first.probability == (0.25 if expected == "loss" else 0.75)
    assert first.provenance == repeated.provenance
    assert first.provenance.kernel_name == "binary_outcome"
    assert first.provenance.stream_id == "replicate-0/kernel"
    assert first.provenance.bit_generator == "PCG64"
    assert len(first.provenance.state_before_sha256) == 64
    assert first.provenance.state_after_sha256 == next_draw.provenance.state_before_sha256


def test_callable_kernel_validates_each_generated_distribution() -> None:
    def distribution(state: dict[str, float]) -> Mapping[str, float]:
        probability = state["probability"]
        return {"no_default": 1.0 - probability, "default": probability}

    kernel = CallableStochasticKernel(
        name="default_kernel",
        support=("no_default", "default"),
        distribution=distribution,
    )

    assert dict(kernel.probabilities({"probability": 0.2})) == {
        "no_default": 0.8,
        "default": 0.2,
    }
    with pytest.raises(ValueError, match="finite and non-negative"):
        kernel.probabilities({"probability": 1.2})


def test_callable_kernel_revalidates_the_exact_distribution_used_for_sampling() -> None:
    calls = 0

    def changing_distribution(_state: str) -> Mapping[str, float]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"inside": 1.0}
        return {"outside": 1.0}

    kernel = CallableStochasticKernel(
        name="changing_support",
        support=("inside",),
        distribution=changing_distribution,
    )

    assert dict(kernel.probabilities("state")) == {"inside": 1.0}
    with pytest.raises(ValueError, match="outside declared support"):
        kernel.sample(
            "state",
            rng=np.random.default_rng(1),
            stream_id="validation-race",
        )


def test_kernel_domain_and_rng_provenance_must_be_explicit() -> None:
    with pytest.raises(ValueError, match="name must not be empty"):
        CategoricalKernel("", ("state",), {"input": {"state": 1.0}})
    with pytest.raises(ValueError, match="support must not be empty"):
        CategoricalKernel("empty", (), {"input": {}})
    with pytest.raises(ValueError, match="support values must be unique"):
        CategoricalKernel(
            "duplicate",
            ("state", "state"),
            {"input": {"state": 1.0}},
        )
    kernel = CategoricalKernel("identity", ("state",), {"input": {"state": 1.0}})
    assert kernel.normalization_tolerance == 1e-12
    with pytest.raises(ValueError, match="stream_id must not be empty"):
        kernel.sample("input", rng=np.random.default_rng(1), stream_id="")


@pytest.mark.parametrize("tolerance", [1.0, 2.0, float("inf"), float("nan"), -0.1])
def test_kernel_rejects_unbounded_normalization_tolerance(tolerance: float) -> None:
    with pytest.raises(ValueError, match="finite, non-negative, and less than one"):
        CategoricalKernel(
            "invalid_tolerance",
            ("state",),
            {"input": {"state": 1.0}},
            normalization_tolerance=tolerance,
        )


def test_callable_kernel_exposes_its_normalization_contract_read_only() -> None:
    kernel = CallableStochasticKernel(
        "identity",
        ("state",),
        lambda _state: {"state": 1.0},
        normalization_tolerance=1e-9,
    )

    assert kernel.normalization_tolerance == 1e-9
    with pytest.raises(AttributeError):
        kernel.normalization_tolerance = 0.5  # type: ignore[misc]
