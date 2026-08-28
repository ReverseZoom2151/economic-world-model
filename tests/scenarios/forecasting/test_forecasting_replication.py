from __future__ import annotations

import pytest

from ewm.scenarios.forecasting import (
    finite_sample_retraining_path,
    paper_config,
    paper_finite_sample_config,
    paper_replication_report,
    population_update,
    sample_first_autocorrelation,
)


def test_paper_preset_locks_figure_4_source_parameters() -> None:
    population = paper_config()
    finite = paper_finite_sample_config(seed=42)

    assert population.feedback == 1.8
    assert population.noise_std == 0.5
    assert finite.feedback == 1.8
    assert finite.noise_std == 0.5
    assert finite.sample_size == 4_000


def test_population_map_reproduces_three_reported_self_validating_slopes() -> None:
    report = paper_replication_report(seed=42, rounds=40, damping=0.5)

    assert report.population_roots[0] == pytest.approx(-0.795, abs=0.003)
    assert report.population_roots[1] == 0.0
    assert report.population_roots[2] == pytest.approx(0.795, abs=0.003)
    assert report.population_roots[0] == pytest.approx(
        -report.population_roots[2], abs=1e-12
    )
    assert max(report.fixed_point_residuals) < 1e-10
    assert report.stable == (True, False, True)
    assert report.reported_outer_slope == 0.795
    assert report.outer_slope_absolute_error < 0.003


def test_origin_derivative_matches_behavioral_gain_within_paper_tolerance() -> None:
    config = paper_config()
    step = 1e-5
    numerical = (
        population_update(step, config) - population_update(-step, config)
    ) / (2.0 * step)

    assert numerical == pytest.approx(config.feedback, rel=0.01)


@pytest.mark.parametrize("seed", [42, 101])
def test_finite_sample_paths_select_sign_basins_and_noise_ejects_zero(seed: int) -> None:
    config = paper_finite_sample_config(seed=seed)
    negative = finite_sample_retraining_path(
        -0.1, config, rounds=40, damping=0.5, seed=seed
    )
    positive = finite_sample_retraining_path(
        0.1, config, rounds=40, damping=0.5, seed=seed
    )
    knife_edge = finite_sample_retraining_path(
        0.0, config, rounds=40, damping=0.5, seed=seed
    )

    assert negative[-1] < -0.7
    assert positive[-1] > 0.7
    assert knife_edge[1] != 0.0
    assert abs(knife_edge[-1]) > 0.7


def test_deployed_model_manufactures_the_acf_it_estimates() -> None:
    config = paper_finite_sample_config(seed=42)
    outer_root = paper_replication_report(seed=42, rounds=2).population_roots[2]

    momentum_acf = sample_first_autocorrelation(outer_root, config, seed=42)
    zero_acf = sample_first_autocorrelation(0.0, config, seed=42)

    assert momentum_acf == pytest.approx(outer_root, abs=0.03)
    assert abs(zero_acf) < 0.03
    assert momentum_acf - zero_acf > 0.7


def test_replication_report_discloses_finite_sample_implementation_choices() -> None:
    report = paper_replication_report(seed=42, rounds=40, damping=0.5)

    assert report.finite_sample_size == 4_000
    assert report.finite_sample_rounds == 40
    assert report.finite_sample_seed == 42
    assert report.finite_sample_damping == 0.5
    assert report.damping_provenance == "package-authored: coefficient omitted from paper"
    assert report.negative_path[-1] < 0.0
    assert report.positive_path[-1] > 0.0
    assert abs(report.zero_path[-1]) > 0.7
