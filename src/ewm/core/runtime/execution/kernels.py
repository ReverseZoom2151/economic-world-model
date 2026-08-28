"""Finite stochastic kernels with complete draw provenance."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from math import isclose, isfinite
from types import MappingProxyType
from typing import Generic, TypeVar

import numpy as np

from ...provenance.serialization import canonical_json, content_digest

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT", bound=Hashable)


@dataclass(frozen=True, slots=True)
class RNGProvenance:
    """Identity of the generator stream and its state around one draw."""

    kernel_name: str
    stream_id: str
    bit_generator: str
    state_before_sha256: str
    state_after_sha256: str


@dataclass(frozen=True, slots=True)
class KernelDraw(Generic[OutputT]):
    """One inverse-CDF draw and its probability and RNG provenance."""

    value: OutputT
    probability: float
    uniform: float
    provenance: RNGProvenance


def _validate_kernel_contract(
    name: str,
    support: Sequence[OutputT],
    normalization_tolerance: float,
) -> tuple[OutputT, ...]:
    if not name:
        raise ValueError("kernel name must not be empty")
    owned_support = tuple(support)
    if not owned_support:
        raise ValueError("kernel support must not be empty")
    try:
        unique_count = len(set(owned_support))
    except TypeError as error:
        raise TypeError("kernel support values must be hashable") from error
    if unique_count != len(owned_support):
        raise ValueError("kernel support values must be unique")
    for value in owned_support:
        canonical_json(value)
    if (
        not isfinite(normalization_tolerance)
        or normalization_tolerance < 0.0
        or normalization_tolerance >= 1.0
    ):
        raise ValueError("normalization_tolerance must be finite, non-negative, and less than one")
    return owned_support


def _validated_row(
    row: Mapping[OutputT, float],
    *,
    support: tuple[OutputT, ...],
    normalization_tolerance: float,
) -> Mapping[OutputT, float]:
    if not row:
        raise ValueError("kernel probability row must not be empty")
    unsupported = set(row).difference(support)
    if unsupported:
        raise ValueError("kernel probability row contains values outside declared support")
    probabilities: dict[OutputT, float] = {}
    for value in support:
        if value not in row:
            continue
        probability = float(row[value])
        if not isfinite(probability) or probability < 0.0:
            raise ValueError("kernel probabilities must be finite and non-negative")
        probabilities[value] = probability
    if any(probability > 1.0 for probability in probabilities.values()):
        raise ValueError("individual kernel probabilities must not exceed one")
    total = sum(probabilities.values())
    if total <= 0.0:
        raise ValueError("kernel probability row must have positive total mass")
    if not isclose(total, 1.0, rel_tol=0.0, abs_tol=normalization_tolerance):
        raise ValueError("kernel probabilities must sum to one")
    return MappingProxyType(probabilities)


def _draw(
    *,
    kernel_name: str,
    support: tuple[OutputT, ...],
    probabilities: Mapping[OutputT, float],
    rng: np.random.Generator,
    stream_id: str,
) -> KernelDraw[OutputT]:
    if not stream_id:
        raise ValueError("kernel RNG stream_id must not be empty")
    state_before = content_digest(rng.bit_generator.state)
    uniform = float(rng.random())
    state_after = content_digest(rng.bit_generator.state)
    cumulative = 0.0
    chosen_index = -1
    fallback_index = -1
    for index, value in enumerate(support):
        probability = probabilities.get(value, 0.0)
        if probability > 0.0:
            fallback_index = index
        cumulative += probability
        if chosen_index < 0 and uniform < cumulative:
            chosen_index = index
    if chosen_index < 0:
        chosen_index = fallback_index
    if chosen_index < 0:
        raise RuntimeError("validated kernel row has no positive probability")
    value = support[chosen_index]
    return KernelDraw(
        value=value,
        probability=probabilities.get(value, 0.0),
        uniform=uniform,
        provenance=RNGProvenance(
            kernel_name=kernel_name,
            stream_id=stream_id,
            bit_generator=type(rng.bit_generator).__name__,
            state_before_sha256=state_before,
            state_after_sha256=state_after,
        ),
    )


class CategoricalKernel(Generic[InputT, OutputT]):
    """A finite input-indexed table of categorical probability measures."""

    def __init__(
        self,
        name: str,
        support: Sequence[OutputT],
        probabilities: Mapping[InputT, Mapping[OutputT, float]],
        *,
        normalization_tolerance: float = 1e-12,
    ) -> None:
        self._name = name
        self._support = _validate_kernel_contract(
            name,
            support,
            normalization_tolerance,
        )
        if not probabilities:
            raise ValueError("categorical kernel input domain must not be empty")
        self._normalization_tolerance = normalization_tolerance
        self._rows: Mapping[InputT, Mapping[OutputT, float]] = MappingProxyType(
            {
                input_value: _validated_row(
                    row,
                    support=self._support,
                    normalization_tolerance=normalization_tolerance,
                )
                for input_value, row in probabilities.items()
            }
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def support(self) -> tuple[OutputT, ...]:
        return self._support

    @property
    def normalization_tolerance(self) -> float:
        """Absolute error allowed for the unit-mass validation."""

        return self._normalization_tolerance

    def probabilities(self, input_value: InputT) -> Mapping[OutputT, float]:
        """Return the validated probability measure for one domain point."""

        try:
            return self._rows[input_value]
        except KeyError as error:
            raise KeyError(f"unknown kernel input {input_value!r}") from error

    def sample(
        self,
        input_value: InputT,
        *,
        rng: np.random.Generator,
        stream_id: str,
    ) -> KernelDraw[OutputT]:
        """Sample one value using only the explicitly supplied RNG stream."""

        return _draw(
            kernel_name=self.name,
            support=self.support,
            probabilities=self.probabilities(input_value),
            rng=rng,
            stream_id=stream_id,
        )


class CallableStochasticKernel(Generic[InputT, OutputT]):
    """A finite kernel whose probability measure is computed per input."""

    def __init__(
        self,
        name: str,
        support: Sequence[OutputT],
        distribution: Callable[[InputT], Mapping[OutputT, float]],
        *,
        normalization_tolerance: float = 1e-12,
    ) -> None:
        self._name = name
        self._support = _validate_kernel_contract(
            name,
            support,
            normalization_tolerance,
        )
        self._distribution = distribution
        self._normalization_tolerance = normalization_tolerance

    @property
    def name(self) -> str:
        return self._name

    @property
    def support(self) -> tuple[OutputT, ...]:
        return self._support

    @property
    def normalization_tolerance(self) -> float:
        """Absolute error allowed for each generated unit-mass validation."""

        return self._normalization_tolerance

    def probabilities(self, input_value: InputT) -> Mapping[OutputT, float]:
        """Compute and validate the probability measure for one input."""

        return _validated_row(
            self._distribution(input_value),
            support=self.support,
            normalization_tolerance=self._normalization_tolerance,
        )

    def sample(
        self,
        input_value: InputT,
        *,
        rng: np.random.Generator,
        stream_id: str,
    ) -> KernelDraw[OutputT]:
        """Validate and sample the exact measure returned for this draw."""

        probabilities = self.probabilities(input_value)
        return _draw(
            kernel_name=self.name,
            support=self.support,
            probabilities=probabilities,
            rng=rng,
            stream_id=stream_id,
        )
