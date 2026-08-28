"""Versioned scenario profiles for verified ontology projection."""

from .base import (
    OntologyProfile,
    OntologyProfileContext,
    ProfileBuilder,
    ProfileProjection,
    artifact_source,
    profile_digest,
)
from .credit import CREDIT_PROFILE, CreditOntologyProfile
from .forecasting import FORECASTING_PROFILE, ForecastingOntologyProfile
from .fx import FX_PROFILE, FXOntologyProfile
from .production import PRODUCTION_PROFILE, ProductionOntologyProfile
from .scalar import SCALAR_PROFILE, ScalarOntologyProfile

DEFAULT_PROFILES: tuple[OntologyProfile, ...] = (
    CREDIT_PROFILE,
    FORECASTING_PROFILE,
    FX_PROFILE,
    PRODUCTION_PROFILE,
    SCALAR_PROFILE,
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
