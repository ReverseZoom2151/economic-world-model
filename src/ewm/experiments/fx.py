"""Replicated comparative statics for the synthetic FX laboratory."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

import numpy as np

from ewm.scenarios.fx import FXSimulationConfig, run_fx_simulation

from .statistics import PairedEstimate, paired_estimate

_METRICS = ("mean_price", "rejected_orders", "total_volume", "volatility")


def replicated_fx_comparisons(
    config: FXSimulationConfig,
    *,
    seed: int,
    replications: int,
) -> Mapping[str, Mapping[str, PairedEstimate]]:
    """Estimate intervention-minus-baseline effects with paired simulation seeds."""

    if replications < 2:
        raise ValueError("replications must be at least two")

    variants = {
        "fixed_beliefs": replace(config, adaptive_beliefs=False),
        "firm_demand_shock": replace(
            config,
            firm_demand=config.firm_demand * 1.5,
        ),
        "trend_intensity": replace(
            config,
            trend_weight=config.trend_weight * 1.5,
        ),
    }
    baseline_samples: dict[str, list[float]] = {
        metric: [] for metric in _METRICS
    }
    intervention_samples: dict[str, dict[str, list[float]]] = {
        name: {metric: [] for metric in _METRICS} for name in variants
    }

    for replication in range(replications):
        replication_seed = seed + replication
        baseline = run_fx_simulation(config, seed=replication_seed).metrics
        interventions = {
            name: run_fx_simulation(variant, seed=replication_seed).metrics
            for name, variant in variants.items()
        }
        for metric in _METRICS:
            baseline_samples[metric].append(baseline[metric])
            for name, metrics in interventions.items():
                intervention_samples[name][metric].append(metrics[metric])

    return MappingProxyType(
        {
            name: MappingProxyType(
                {
                    metric: paired_estimate(
                        np.asarray(baseline_samples[metric]),
                        np.asarray(samples[metric]),
                    )
                    for metric in _METRICS
                }
            )
            for name, samples in intervention_samples.items()
        }
    )
