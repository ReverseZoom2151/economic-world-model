"""AI-mediated credit with endogenous adoption and selective retraining."""

from .learner import (
    CreditModel,
    adoption_mask,
    fit_credit_model,
    fit_initial_model,
    omniscient_approvals,
)
from .model import CreditDDGEProblem, CreditMetrics, CreditRegime, run_credit_regimes
from .oracles import (
    CreditOracleReport,
    CreditSensitivityCase,
    credit_oracle_report,
    sensitivity_report,
)
from .population import CreditPopulation, assemble_features, generate_population
from .presets import CreditConfig, paper_like_config, research_config

__all__ = [
    "CreditConfig",
    "CreditDDGEProblem",
    "CreditMetrics",
    "CreditModel",
    "CreditOracleReport",
    "CreditPopulation",
    "CreditRegime",
    "CreditSensitivityCase",
    "adoption_mask",
    "assemble_features",
    "credit_oracle_report",
    "fit_credit_model",
    "fit_initial_model",
    "generate_population",
    "omniscient_approvals",
    "paper_like_config",
    "research_config",
    "run_credit_regimes",
    "sensitivity_report",
]
