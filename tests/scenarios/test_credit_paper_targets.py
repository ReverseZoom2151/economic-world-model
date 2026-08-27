from __future__ import annotations

import numpy as np
import pytest

from ewm.experiments import credit_paper_target_report, run_credit_regimes
from ewm.scenarios.credit import (
    CONG_LAB_I_PROVENANCE,
    CreditRegime,
    assemble_features,
    cong_qualitative_reconstruction,
    evaluate_credit_model,
    fit_initial_model,
    generate_population,
    paper_like_config,
)


def test_cong_credit_provenance_records_fixed_and_missing_inputs() -> None:
    provenance = CONG_LAB_I_PROVENANCE

    assert provenance.source_id == "cong-2026"
    assert provenance.claim_type == "qualitative-reconstruction"
    assert provenance.source_pages == (62, 63, 64, 70)
    assert provenance.structured_features == 10
    assert provenance.text_features == 15
    assert provenance.model_parameter_dimension == 26
    assert provenance.applications_per_round == 40_000
    assert provenance.approval_cutoff == "LGD / (r + LGD)"
    assert provenance.exact_replication_identified is False
    assert len(provenance.published_targets) >= 15
    assert {target.identifier for target in provenance.published_targets} >= {
        "baseline_profit_per_applicant",
        "frozen_predicted_profit_change",
        "frozen_realized_profit_change",
        "selective_ddge_profit_change",
        "local_retraining_modulus",
        "damped_map_modulus",
    }
    assert {primitive.identifier for primitive in provenance.missing_primitives} >= {
        "feature_loadings",
        "feature_noise_laws",
        "repayment_link",
        "enhancement_parameters",
        "adoption_cost_distribution",
        "payoff_parameters",
        "ridge_penalty",
        "retraining_damping",
        "random_seeds",
        "replication_code_url",
    }


def test_old_paper_like_name_is_an_exact_compatibility_alias() -> None:
    assert paper_like_config is cong_qualitative_reconstruction


def test_reconstruction_matches_supported_mechanism_orderings() -> None:
    config = cong_qualitative_reconstruction(population_size=1_200)
    report = credit_paper_target_report(config)
    matches = {comparison.identifier: comparison.matches for comparison in report.orderings}

    assert matches["endogenous_adoption"]
    assert matches["selective_outcome_observation"]
    assert matches["frozen_predicted_realized_sign_reversal"]
    assert matches["selective_ddge_partial_repair"]
    assert matches["omniscient_intervention_invariance"]
    assert matches["adoption_falls_after_selective_retraining"]
    assert matches["false_positive_rate_partially_recovers"]


def test_published_magnitudes_are_differences_not_replication_assertions() -> None:
    report = credit_paper_target_report(
        cong_qualitative_reconstruction(population_size=1_200)
    )

    measured = [comparison for comparison in report.targets if comparison.measured]
    unavailable = [comparison for comparison in report.targets if not comparison.measured]
    assert measured
    assert unavailable
    assert all(comparison.difference is not None for comparison in measured)
    for comparison in measured:
        assert comparison.reconstructed_value is not None
        assert comparison.difference == pytest.approx(
            comparison.reconstructed_value - comparison.published_value
        )
    assert all(comparison.difference is None for comparison in unavailable)
    assert report.exact_replication_claimed is False


def test_profit_cutoff_and_per_applicant_metric_have_declared_semantics() -> None:
    config = cong_qualitative_reconstruction(population_size=500)
    population = generate_population(config)
    model = fit_initial_model(config)
    adoption = np.zeros(population.size, dtype=bool)
    features = assemble_features(population, adoption)
    probabilities = model.predict_probability(features)
    approvals = probabilities >= config.approval_threshold
    payoff = np.where(
        population.potential_repayment,
        config.repayment_gain,
        -config.default_loss,
    )

    metrics = evaluate_credit_model(
        population,
        model,
        config,
        adoption=adoption,
    )

    assert config.approval_threshold == pytest.approx(
        config.default_loss / (config.repayment_gain + config.default_loss)
    )
    assert metrics.profit_per_applicant == pytest.approx(np.mean(approvals * payoff))


def test_residual_floor_is_not_mislabeled_as_paper_sampling_noise() -> None:
    config = cong_qualitative_reconstruction(population_size=1_200)
    report = credit_paper_target_report(config)
    regimes = run_credit_regimes(config)

    assert report.one_step_residual > report.terminal_residual_floor
    assert report.terminal_residual_floor == pytest.approx(
        regimes[CreditRegime.SELECTIVE].residual_floor
    )
    assert report.sampling_noise_floor is None
    assert "not estimated" in report.sampling_noise_floor_limitation
