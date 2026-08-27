"""AI-mediated credit with endogenous adoption and selective retraining."""

from .learner import (
    CreditModel,
    adoption_mask,
    fit_credit_model,
    fit_initial_model,
    omniscient_approvals,
)
from .model import (
    CreditDDGEProblem,
    CreditMetrics,
    CreditRegime,
    evaluate_credit_model,
    evaluate_omniscient,
)
from .oracles import CreditSensitivityCase, sensitivity_report
from .population import CreditPopulation, assemble_features, generate_population
from .presets import CreditConfig, paper_like_config, research_config

__all__ = [
    "CreditConfig",
    "CreditDDGEProblem",
    "CreditMetrics",
    "CreditModel",
    "CreditPopulation",
    "CreditRegime",
    "CreditSensitivityCase",
    "adoption_mask",
    "assemble_features",
    "evaluate_credit_model",
    "evaluate_omniscient",
    "fit_credit_model",
    "fit_initial_model",
    "generate_population",
    "omniscient_approvals",
    "paper_like_config",
    "research_config",
    "sensitivity_report",
]
