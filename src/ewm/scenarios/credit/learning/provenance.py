"""Locked-source provenance for Cong's Laboratory I credit model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublishedCreditTarget:
    """One numerical magnitude stated in Cong's Laboratory I discussion."""

    identifier: str
    value: float
    unit: str
    source_page: int
    description: str


@dataclass(frozen=True, slots=True)
class PublishedCreditOrdering:
    """One qualitative mechanism or ordering stated by the paper."""

    identifier: str
    statement: str
    source_page: int


@dataclass(frozen=True, slots=True)
class MissingCreditPrimitive:
    """An input needed for exact replication but absent from the locked PDF."""

    identifier: str
    consequence: str


@dataclass(frozen=True, slots=True)
class CreditLaboratoryProvenance:
    """Machine-readable boundary between published facts and package choices."""

    source_id: str
    claim_type: str
    source_pages: tuple[int, ...]
    structured_features: int
    text_features: int
    model_parameter_dimension: int
    applications_per_round: int
    approval_cutoff: str
    exact_replication_identified: bool
    published_targets: tuple[PublishedCreditTarget, ...]
    qualitative_orderings: tuple[PublishedCreditOrdering, ...]
    missing_primitives: tuple[MissingCreditPrimitive, ...]


CONG_LAB_I_PROVENANCE = CreditLaboratoryProvenance(
    source_id="cong-2026",
    claim_type="qualitative-reconstruction",
    source_pages=(62, 63, 64, 70),
    structured_features=10,
    text_features=15,
    model_parameter_dimension=26,
    applications_per_round=40_000,
    approval_cutoff="LGD / (r + LGD)",
    exact_replication_identified=False,
    published_targets=(
        PublishedCreditTarget(
            "baseline_profit_per_applicant", 0.055, "USD/applicant", 63,
            "Baseline screening profit.",
        ),
        PublishedCreditTarget(
            "baseline_auc", 0.792, "fraction", 63,
            "Baseline AUC using structured and text features.",
        ),
        PublishedCreditTarget(
            "structured_only_auc", 0.763, "fraction", 63,
            "Baseline AUC using structured characteristics alone.",
        ),
        PublishedCreditTarget(
            "frozen_predicted_profit_change", 0.0074, "USD/applicant", 63,
            "Profit change predicted by the frozen learned component.",
        ),
        PublishedCreditTarget(
            "frozen_realized_profit_change", -0.0183, "USD/applicant", 63,
            "Realized profit change under frozen deployment.",
        ),
        PublishedCreditTarget(
            "selective_ddge_profit_change", -0.0055, "USD/applicant", 63,
            "Realized profit change after selective-retraining closure.",
        ),
        PublishedCreditTarget(
            "frozen_adoption_rate", 0.130, "fraction", 63,
            "Adoption under frozen deployment.",
        ),
        PublishedCreditTarget(
            "selective_ddge_adoption_rate", 0.077, "fraction", 63,
            "Adoption at the selective-retraining DDGE.",
        ),
        PublishedCreditTarget(
            "baseline_false_positive_rate", 0.136, "fraction", 63,
            "Baseline false-positive rate.",
        ),
        PublishedCreditTarget(
            "frozen_false_positive_rate", 0.268, "fraction", 63,
            "False-positive rate under frozen deployment.",
        ),
        PublishedCreditTarget(
            "selective_ddge_false_positive_rate", 0.151, "fraction", 63,
            "False-positive rate after selective-retraining closure.",
        ),
        PublishedCreditTarget(
            "full_information_profit_change", -0.0101, "USD/applicant", 63,
            "Profit change at the full-information retrained equilibrium.",
        ),
        PublishedCreditTarget(
            "one_step_residual", 0.48, "parameter norm", 63,
            "One-retraining-step residual at the frozen learned component.",
        ),
        PublishedCreditTarget(
            "residual_to_sampling_noise_ratio", 6.5, "ratio", 63,
            "One-step residual relative to the reported sampling noise floor.",
        ),
        PublishedCreditTarget(
            "local_retraining_modulus", 0.27, "dimensionless", 64,
            "Common-random-numbers estimate of the local retraining modulus.",
        ),
        PublishedCreditTarget(
            "damped_map_modulus", 0.63, "dimensionless", 64,
            "Reported modulus of the damped retraining map.",
        ),
    ),
    qualitative_orderings=(
        PublishedCreditOrdering(
            "endogenous_adoption",
            "Rejected marginal borrowers adopt when enhancement flips approval and "
            "benefit covers cost.",
            62,
        ),
        PublishedCreditOrdering(
            "selective_outcome_observation",
            "The selective learner observes repayment only for approved loans.",
            62,
        ),
        PublishedCreditOrdering(
            "frozen_predicted_realized_sign_reversal",
            "Frozen predictions imply a gain while realized profit falls.",
            63,
        ),
        PublishedCreditOrdering(
            "selective_ddge_partial_repair",
            "Selective DDGE closure reduces but does not eliminate the frozen loss.",
            63,
        ),
        PublishedCreditOrdering(
            "full_information_underperforms_selective",
            "Full-information retraining produces a larger loss than selective retraining.",
            63,
        ),
        PublishedCreditOrdering(
            "omniscient_intervention_invariance",
            "Quality-based screening has zero adoption and no intervention profit effect.",
            63,
        ),
        PublishedCreditOrdering(
            "adoption_falls_after_selective_retraining",
            "Adoption declines when the retrained screener discounts polish.",
            63,
        ),
        PublishedCreditOrdering(
            "text_informativeness_declines",
            "The incremental AUC contribution of text declines along retraining.",
            63,
        ),
        PublishedCreditOrdering(
            "false_positive_rate_partially_recovers",
            "The false-positive rate rises under frozen deployment and partly "
            "recovers at the DDGE.",
            63,
        ),
    ),
    missing_primitives=(
        MissingCreditPrimitive(
            "feature_loadings", "The vectors beta_x, gamma_z, and u are not numerically specified."
        ),
        MissingCreditPrimitive(
            "feature_noise_laws", "The feature-noise distributions and scales are omitted."
        ),
        MissingCreditPrimitive(
            "repayment_link", "The Phi-shaped repayment link and its parameters are omitted."
        ),
        MissingCreditPrimitive(
            "enhancement_parameters", "The intervention parameters p0 and p1 are omitted."
        ),
        MissingCreditPrimitive(
            "adoption_cost_distribution", "The heterogeneous adoption-cost law is omitted."
        ),
        MissingCreditPrimitive(
            "payoff_parameters", "The loan benefit, return r, and LGD values are omitted."
        ),
        MissingCreditPrimitive(
            "ridge_penalty", "The ridge-logistic regularization strength is omitted."
        ),
        MissingCreditPrimitive(
            "retraining_damping", "The damping coefficient is omitted."
        ),
        MissingCreditPrimitive(
            "historical_sample",
            "The regime-0 sample construction and initialization are incomplete.",
        ),
        MissingCreditPrimitive(
            "random_seeds", "Random seeds and exact stochastic draws are omitted."
        ),
        MissingCreditPrimitive(
            "sampling_noise_estimator", "The sampling-noise-floor estimator is not specified."
        ),
        MissingCreditPrimitive(
            "replication_code_url", "The PDF says code accompanies it but gives no code URL."
        ),
    ),
)
