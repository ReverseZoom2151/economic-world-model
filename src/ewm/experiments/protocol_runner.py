"""Execution of the shipped, prospectively locked local credit protocol."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Literal

import numpy as np

from ewm.scenarios.credit import CreditRegime, cong_qualitative_reconstruction

from .credit import run_credit_regimes
from .protocols import (
    ProtocolIssue,
    ProtocolMode,
    ScientificProtocol,
    audit_protocol_execution,
)
from .statistics import holm_correction, robust_paired_estimate, wilson_interval

MetricSeries = dict[str, list[float]]


def run_locked_protocol(
    protocol: ScientificProtocol,
    *,
    mode: ProtocolMode,
) -> dict[str, object]:
    """Execute the exact fixed-sample local protocol and return a JSON-ready report."""

    if protocol.experiment != "credit.qualitative_reconstruction.local":
        raise ValueError(f"unsupported protocol experiment {protocol.experiment!r}")
    replication_count = protocol.replication_count(mode)
    population_size = protocol.population_size(mode)
    executed_seeds = protocol.seed_manifest.seeds[:replication_count]
    metric_series: MetricSeries = {
        "no_genai.profit_per_applicant": [],
        "frozen.profit_per_applicant": [],
        "selective_ddge.profit_per_applicant": [],
        "full_information_ddge.profit_per_applicant": [],
    }
    selective_repairs: list[bool] = []
    full_information_repairs: list[bool] = []
    tolerance_breaches: list[str] = []
    execution_failures: list[ProtocolIssue] = []
    completed_replications = 0
    maximum_solver_residual = 0.0
    solver_tolerance = protocol.tolerance("solver_residual")
    comparison_slack = protocol.tolerance("comparison_slack")

    for seed in executed_seeds:
        try:
            config = replace(
                cong_qualitative_reconstruction(population_size=population_size),
                seed=seed,
            )
            regimes = run_credit_regimes(config)
        except (RuntimeError, ValueError, np.linalg.LinAlgError) as error:
            execution_failures.append(
                ProtocolIssue("replication_error", f"seed={seed}: {error}")
            )
            continue
        baseline = regimes[CreditRegime.NO_GENAI]
        frozen = regimes[CreditRegime.FROZEN]
        selective = regimes[CreditRegime.SELECTIVE]
        full_information = regimes[CreditRegime.FULL_INFORMATION]
        metric_series["no_genai.profit_per_applicant"].append(
            baseline.profit_per_applicant
        )
        metric_series["frozen.profit_per_applicant"].append(
            frozen.profit_per_applicant
        )
        metric_series["selective_ddge.profit_per_applicant"].append(
            selective.profit_per_applicant
        )
        metric_series["full_information_ddge.profit_per_applicant"].append(
            full_information.profit_per_applicant
        )
        selective_repairs.append(
            selective.profit_per_applicant + comparison_slack
            >= frozen.profit_per_applicant
        )
        full_information_repairs.append(
            full_information.profit_per_applicant + comparison_slack
            >= frozen.profit_per_applicant
        )
        residual = max(selective.residual_norm, full_information.residual_norm)
        maximum_solver_residual = max(maximum_solver_residual, residual)
        if (
            not selective.converged
            or not full_information.converged
            or residual > solver_tolerance
        ):
            tolerance_breaches.append(f"solver_residual:seed={seed}")
        completed_replications += 1

    outcomes: dict[str, object] = {}
    paired_p_values: list[float] = []
    if completed_replications >= 2:
        paired_index = 0
        for outcome in protocol.outcomes:
            metadata = {
                "direction": outcome.direction,
                "interpretation": outcome.interpretation,
                "null": outcome.null,
                "unit": outcome.unit,
            }
            if outcome.kind == "paired_continuous":
                if outcome.baseline_metric is None or outcome.intervention_metric is None:
                    raise ValueError(f"paired outcome {outcome.name!r} has no metric mapping")
                paired_estimate = robust_paired_estimate(
                    np.asarray(metric_series[outcome.baseline_metric]),
                    np.asarray(metric_series[outcome.intervention_metric]),
                    confidence=protocol.confidence,
                    bootstrap_resamples=protocol.bootstrap_resamples(mode),
                    bootstrap_seed=protocol.bootstrap.seeds[paired_index],
                )
                paired_index += 1
                paired_p_values.append(paired_estimate.p_value)
                outcomes[outcome.name] = metadata | asdict(paired_estimate)
            elif outcome.name == "selective_repair_rate":
                binomial_estimate = wilson_interval(
                    successes=sum(selective_repairs),
                    trials=len(selective_repairs),
                    confidence=protocol.confidence,
                )
                outcomes[outcome.name] = metadata | asdict(binomial_estimate)
            elif outcome.name == "full_information_repair_rate":
                binomial_estimate = wilson_interval(
                    successes=sum(full_information_repairs),
                    trials=len(full_information_repairs),
                    confidence=protocol.confidence,
                )
                outcomes[outcome.name] = metadata | asdict(binomial_estimate)
            else:
                raise ValueError(f"unsupported binary outcome {outcome.name!r}")

    correction = (
        holm_correction(tuple(paired_p_values), alpha=protocol.alpha)
        if paired_p_values
        else None
    )
    audit = audit_protocol_execution(
        protocol,
        mode=mode,
        observed_protocol_sha256=protocol.content_sha256,
        executed_seeds=executed_seeds,
        completed_replications=completed_replications,
        observed_outcomes=tuple(outcomes),
        stopped_early=False,
        tolerance_breaches=tuple(tolerance_breaches),
    )
    failures = audit.failures + tuple(execution_failures)
    analysis_valid = (
        completed_replications == replication_count
        and not tolerance_breaches
        and not execution_failures
    )
    claim_authorized = analysis_valid and not audit.deviations and not failures
    status: Literal["pass", "fail"] = (
        "pass" if claim_authorized else "fail"
    )
    multiplicity: dict[str, object] = {
        "alpha": protocol.alpha,
        "family": protocol.multiplicity.family,
        "method": protocol.multiplicity.method,
    }
    if correction is not None:
        multiplicity.update(asdict(correction))
    return {
        "schema_version": "ewm.local-protocol-report.v1",
        "protocol_id": protocol.protocol_id,
        "protocol_version": protocol.protocol_version,
        "protocol_sha256": protocol.content_sha256,
        "protocol_semantic_sha256": protocol.semantic_sha256,
        "lock_status": protocol.lock_status,
        "sample_size_rationale": protocol.sample_size_rationale,
        "mode": mode,
        "status": status,
        "analysis_valid": analysis_valid,
        "claim_authorized": claim_authorized,
        "evidence_status": "validated_local_analysis" if claim_authorized else "diagnostic_only",
        "completed_replications": completed_replications,
        "executed_seeds": executed_seeds,
        "bootstrap_seeds": protocol.bootstrap.seeds,
        "stopping": asdict(protocol.stopping),
        "tolerances": tuple(asdict(item) for item in protocol.tolerances),
        "maximum_solver_residual": maximum_solver_residual,
        "outcomes": outcomes,
        "multiplicity": multiplicity,
        "deviations": tuple(asdict(issue) for issue in audit.deviations),
        "failures": tuple(asdict(issue) for issue in failures),
    }
