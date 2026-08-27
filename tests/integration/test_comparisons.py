from __future__ import annotations

from ewm.experiments.fx import replicated_fx_comparisons
from ewm.scenarios.fx import smoke_config


def test_fx_comparisons_report_replicated_paired_intervals() -> None:
    reports = replicated_fx_comparisons(
        smoke_config(periods=4),
        seed=42,
        replications=3,
    )

    assert set(reports) == {
        "fixed_beliefs",
        "firm_demand_shock",
        "trend_intensity",
    }
    assert all(
        set(metrics)
        == {"mean_price", "rejected_orders", "total_volume", "volatility"}
        for metrics in reports.values()
    )
    assert all(
        estimate.sample_size == 3
        for metrics in reports.values()
        for estimate in metrics.values()
    )
    assert reports["firm_demand_shock"]["total_volume"].mean_difference >= 0.0


def test_fx_comparisons_reject_fewer_than_two_replications() -> None:
    try:
        replicated_fx_comparisons(
            smoke_config(periods=4),
            seed=42,
            replications=1,
        )
    except ValueError as error:
        assert str(error) == "replications must be at least two"
    else:
        raise AssertionError("expected replications validation to fail")
