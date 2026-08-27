"""Named configurations for fast checks and larger forecasting experiments."""

from __future__ import annotations

from .model import ForecastingConfig


def smoke_config(*, feedback: float = 1.8) -> ForecastingConfig:
    """Return the deterministic, CI-sized forecasting configuration."""

    return ForecastingConfig(
        feedback=feedback,
        noise_std=0.35,
        burn_in=256,
        sample_size=4_096,
        chains=64,
        seed=123,
    )


def research_config(*, feedback: float = 1.8) -> ForecastingConfig:
    """Return a larger configuration for reported numerical experiments."""

    return ForecastingConfig(
        feedback=feedback,
        noise_std=0.35,
        burn_in=2_000,
        sample_size=131_072,
        chains=256,
        seed=123,
    )


def paper_config() -> ForecastingConfig:
    """Return Figure 4's population-map parameters and a high-precision integration grid."""

    return ForecastingConfig(
        feedback=1.8,
        noise_std=0.5,
        burn_in=3_000,
        sample_size=262_144,
        chains=512,
        seed=123,
    )


def paper_finite_sample_config(*, seed: int = 123) -> ForecastingConfig:
    """Return Figure 4(c)'s source-specified 4,000-observation round configuration."""

    return ForecastingConfig(
        feedback=1.8,
        noise_std=0.5,
        burn_in=512,
        sample_size=4_000,
        chains=1,
        seed=seed,
    )
