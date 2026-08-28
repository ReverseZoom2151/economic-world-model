"""Versioned scenario profiles for verified ontology projection."""

from ewm._internal.imports import register_module_aliases

from .contracts.base import (
    OntologyProfile,
    OntologyProfileContext,
    ProfileBuilder,
    ProfileProjection,
    artifact_source,
    profile_digest,
)
from .scenarios.credit import CREDIT_PROFILE, CreditOntologyProfile
from .scenarios.forecasting import FORECASTING_PROFILE, ForecastingOntologyProfile
from .scenarios.fx import FX_PROFILE, FXOntologyProfile
from .scenarios.production import PRODUCTION_PROFILE, ProductionOntologyProfile
from .scenarios.scalar import SCALAR_PROFILE, ScalarOntologyProfile

DEFAULT_PROFILES: tuple[OntologyProfile, ...] = (
    CREDIT_PROFILE,
    FORECASTING_PROFILE,
    FX_PROFILE,
    PRODUCTION_PROFILE,
    SCALAR_PROFILE,
)

register_module_aliases(
    __name__,
    {
        "base": "contracts.base",
        "credit": "scenarios.credit",
        "forecasting": "scenarios.forecasting",
        "fx": "scenarios.fx",
        "production": "scenarios.production",
        "scalar": "scenarios.scalar",
    },
)

__all__ = [
    "CREDIT_PROFILE",
    "DEFAULT_PROFILES",
    "FORECASTING_PROFILE",
    "FX_PROFILE",
    "PRODUCTION_PROFILE",
    "SCALAR_PROFILE",
    "CreditOntologyProfile",
    "FXOntologyProfile",
    "ForecastingOntologyProfile",
    "OntologyProfile",
    "OntologyProfileContext",
    "ProductionOntologyProfile",
    "ProfileBuilder",
    "ProfileProjection",
    "ScalarOntologyProfile",
    "artifact_source",
    "profile_digest",
]
