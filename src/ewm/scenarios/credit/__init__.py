"""AI-mediated credit with endogenous adoption and selective retraining."""

from ewm._internal.imports import register_module_aliases

from .economy.model import (
    CreditDDGEProblem,
    CreditMetrics,
    CreditRegime,
    evaluate_credit_model,
    evaluate_omniscient,
)
from .economy.population import CreditPopulation, assemble_features, generate_population
from .economy.presets import (
    CreditConfig,
    cong_qualitative_reconstruction,
    paper_like_config,
    research_config,
)
from .learning.learner import (
    CreditModel,
    adoption_mask,
    fit_credit_model,
    fit_initial_model,
    omniscient_approvals,
)
from .learning.oracles import CreditSensitivityCase, sensitivity_report
from .learning.provenance import (
    CONG_LAB_I_PROVENANCE,
    CreditLaboratoryProvenance,
    MissingCreditPrimitive,
    PublishedCreditOrdering,
    PublishedCreditTarget,
)

register_module_aliases(
    __name__,
    {
        "population": "economy.population",
        "presets": "economy.presets",
        "learner": "learning.learner",
        "model": "economy.model",
        "oracles": "learning.oracles",
        "provenance": "learning.provenance",
    },
)

__all__ = [
    "CONG_LAB_I_PROVENANCE",
    "CreditConfig",
    "CreditDDGEProblem",
    "CreditLaboratoryProvenance",
    "CreditMetrics",
    "CreditModel",
    "CreditPopulation",
    "CreditRegime",
    "CreditSensitivityCase",
    "MissingCreditPrimitive",
    "PublishedCreditOrdering",
    "PublishedCreditTarget",
    "adoption_mask",
    "assemble_features",
    "cong_qualitative_reconstruction",
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
