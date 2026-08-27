from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from ewm.scenarios.credit import (
    CreditDDGEProblem,
    CreditRegime,
    adoption_mask,
    assemble_features,
    credit_oracle_report,
    fit_initial_model,
    generate_population,
    omniscient_approvals,
    paper_like_config,
    run_credit_regimes,
    sensitivity_report,
)


def test_genai_polish_changes_text_but_not_quality_or_potential_outcomes() -> None:
    config = paper_like_config(population_size=500)
    population = generate_population(config)
    quality = population.quality.copy()
    repayment = population.potential_repayment.copy()
    original_text = population.text.copy()

    _ = assemble_features(population, np.ones(population.size, dtype=bool))

    assert not np.array_equal(population.text, population.polished_text)
    assert np.array_equal(population.quality, quality)
    assert np.array_equal(population.potential_repayment, repayment)
    assert np.array_equal(population.text, original_text)
    assert np.allclose(
        population.polished_text - population.text,
        config.polish_shift * population.polish_direction,
    )


def test_adoption_requires_a_decision_flip_and_affordable_cost() -> None:
    config = paper_like_config(population_size=800)
    population = generate_population(config)
    model = fit_initial_model(config)

    adopted = adoption_mask(population, model, config)
    original_approval = model.approve(
        assemble_features(population, np.zeros(800, dtype=bool)), config
    )
    polished_approval = model.approve(
        assemble_features(population, np.ones(800, dtype=bool)), config
    )

    assert adopted.any()
    assert np.all(~original_approval[adopted])
    assert np.all(polished_approval[adopted])
    assert np.all(population.adoption_cost[adopted] <= config.loan_benefit)


def test_selective_and_full_information_training_masks_are_distinct() -> None:
    config = paper_like_config(population_size=600)
    population = generate_population(config)
    model = fit_initial_model(config)

    selective = CreditDDGEProblem(config, population, CreditRegime.SELECTIVE)
    full = CreditDDGEProblem(config, population, CreditRegime.FULL_INFORMATION)
    theta = model.to_vector()
    adoption = adoption_mask(population, model, config)
    approvals = model.approve(assemble_features(population, adoption), config)

    assert np.array_equal(selective.training_mask(theta), approvals)
    assert np.all(full.training_mask(theta))
    assert selective.training_mask(theta).sum() < full.training_mask(theta).sum()


def test_omniscient_screener_is_invariant_to_polish() -> None:
    config = paper_like_config(population_size=500)
    unpolished = generate_population(replace(config, polish_shift=0.0))
    heavily_polished = generate_population(replace(config, polish_shift=5.0))

    before = omniscient_approvals(unpolished, config)
    after = omniscient_approvals(heavily_polished, config)

    assert np.array_equal(unpolished.quality, heavily_polished.quality)
    assert np.array_equal(before, after)


def test_five_regimes_report_residuals_and_selective_observation() -> None:
    config = paper_like_config(population_size=800)
    results = run_credit_regimes(config)

    assert set(results) == {
        CreditRegime.NO_GENAI,
        CreditRegime.FROZEN,
        CreditRegime.SELECTIVE,
        CreditRegime.FULL_INFORMATION,
        CreditRegime.OMNISCIENT,
    }
    assert results[CreditRegime.NO_GENAI].adoption_rate == 0.0
    assert results[CreditRegime.OMNISCIENT].adoption_rate == 0.0
    assert results[CreditRegime.SELECTIVE].observed_rate == pytest.approx(
        results[CreditRegime.SELECTIVE].approval_rate
    )
    assert results[CreditRegime.FULL_INFORMATION].observed_rate == 1.0
    assert results[CreditRegime.SELECTIVE].residual_norm < 2e-2
    assert results[CreditRegime.FULL_INFORMATION].residual_norm < 2e-3
    assert results[CreditRegime.SELECTIVE].residual_floor <= (
        results[CreditRegime.SELECTIVE].residual_norm
    )


def test_paper_like_oracle_exposes_frozen_sign_reversal_and_ddge_repair() -> None:
    report = credit_oracle_report(paper_like_config(population_size=1_200))

    assert report.frozen_predicted_profit_change > 0.0
    assert report.frozen_realized_profit_change < 0.0
    assert report.selective_realized_profit >= report.frozen_realized_profit
    assert report.full_information_realized_profit >= report.frozen_realized_profit
    assert report.one_step_residual > report.selective_residual


def test_sensitivity_report_retains_a_boundary_without_sign_reversal() -> None:
    cases = sensitivity_report(
        paper_like_config(population_size=600),
        polish_shifts=(0.0, 0.75, 1.5),
    )

    assert len(cases) == 3
    assert any(not case.frozen_sign_reversal for case in cases)
    assert cases[0].adoption_rate == 0.0
