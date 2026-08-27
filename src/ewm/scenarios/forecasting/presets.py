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
