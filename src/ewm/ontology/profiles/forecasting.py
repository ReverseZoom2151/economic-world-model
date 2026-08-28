"""Ontology profile for the self-fulfilling forecasting DDGE experiment."""

from __future__ import annotations

from ewm._version import __version__
from ewm.core.serialization import content_digest

from .base import OntologyProfileContext, ProfileBuilder, ProfileProjection, artifact_source


class ForecastingOntologyProfile:
    """Preserve every observed forecasting root and its learned coefficient."""

    identity = "ewm.forecasting-ontology-profile.v1"
    experiment_ids = frozenset({"forecasting.ddge"})
    package_versions = frozenset({__version__})
    artifact_schemas = frozenset({"ewm.run.v2"})
    source_digest = content_digest(
        {
            "profile": identity,
            "mapping_version": 2,
            "sources": (
                "ewm.scenarios.forecasting.model.ForecastingProblem",
                "ewm.scenarios.forecasting.oracles.oracle_report",
                "ewm.experiments.registry._forecasting",
            ),
        }
    )

    def project(self, context: OntologyProfileContext) -> ProfileProjection:
        builder = ProfileBuilder(
            context,
            profile_identity=self.identity,
            source_digest=self.source_digest,
        )
        parameters = context.config["parameters"]
        selector = "retain_all_independently_bracketed_roots"

        world = builder.declaration(
            "world",
            {"scenario": "forecasting"},
            {
                "scenario": "forecasting",
                "world_kind": "self_fulfilling_forecast_economy",
                "paper_anchor": "Cong DDGE forecasting laboratory",
            },
        )
        agent = builder.declaration(
            "agent",
            {"scenario": "forecasting", "role": "representative_population"},
            {"role": "representative_population", "behavior": "forecast_response"},
        )
        belief = builder.declaration(
            "belief",
            {"scenario": "forecasting", "belief": "deployed_forecast"},
            {"belief": "deployed_forecast", "coefficient_name": "forecast"},
        )
        learner = builder.declaration(
            "learner",
            {"scenario": "forecasting", "learner": "population_mean"},
            {
                "learner": "population_mean",
                "feedback": parameters["feedback"],
                "sample_size": parameters["sample_size"],
            },
        )
        action = builder.declaration(
            "action",
            {"scenario": "forecasting", "action": "forecast_response"},
            {
                "action": "forecast_response",
                "typed_parameter": "deployed_forecast_coefficient",
                "retained_runtime_scope": "stationary_population_summary",
            },
        )
        for ordinal, target in enumerate((agent, belief, learner, action)):
            builder.relation(
                "DECLARES",
                world,
                target,
                {"ordinal": ordinal},
                locator=context.adapter_source,
            )

        event_sources = tuple(
            artifact_source(context, "events.jsonl", selector=f"sequence={sequence}")
            for sequence in range(len(context.events))
        )
        correspondence = builder.object(
            "inner_equilibrium",
            "learning_equilibrium",
            {"correspondence": "forecasting_ddge_roots"},
            {
                "candidate_count": len(context.events),
                "selector": selector,
                "status": "numerically_validated",
            },
            sources=event_sources,
        )
        model = builder.object(
            "model_version",
            "learning_equilibrium",
            {"model": "forecasting_population_mean", "run": context.run_ref.id},
            {
                "model_family": "population_mean_forecaster",
                "status": "candidate_set",
                "candidate_count": len(context.events),
                "retention_scope": "population_fixed_point_summary",
            },
            sources=event_sources,
        )
        experiment = builder.object(
            "experiment",
            "research_evidence",
            {"experiment": context.experiment},
            {
                "experiment": context.experiment,
                "scope": "synthetic_conformance",
                "root_oracles": ("bracketing", "fixed_point_iteration"),
            },
            sources=(context.run_source,),
        )
        evidence = builder.object(
            "evidence_artifact",
            "research_evidence",
            {"evidence": "forecasting_root_cross_validation"},
            {
                "profile_evidence": True,
                "evidence_classification": "exact-replication",
                "max_root_gap": context.metrics["max_root_gap"],
                "derivative_error": context.metrics["derivative_error"],
                "scope": "population stationary-kernel OLS roots",
                "excluded_scope": "finite-sample damping and empirical validation",
            },
            sources=(artifact_source(context, "metrics.json"),),
        )
        claim = builder.object(
            "claim",
            "research_evidence",
            {"claim": "cong_laboratory_iii_population_replication"},
            {
                "profile_evidence": True,
                "claim_kind": "exact_replication",
                "evidence_classification": "exact-replication",
                "status": "supported",
                "scope": "population stationary-kernel OLS roots",
                "qualification": (
                    "finite-sample damping remains package-authored and excluded; "
                    "no empirical validation claim"
                ),
            },
            sources=(artifact_source(context, "metrics.json"),),
        )
        builder.relation(
            "PRODUCES",
            experiment,
            evidence,
            {"evidence": "root_cross_validation"},
            locator=artifact_source(context, "metrics.json"),
        )
        builder.relation(
            "SUPPORTS",
            evidence,
            claim,
            {"claim": "cong_laboratory_iii_population_replication"},
            locator=artifact_source(context, "metrics.json"),
        )

        dataset = builder.object(
            "dataset",
            "learning_equilibrium",
            {"dataset": "retained_fixed_point_summaries"},
            {
                "dataset_kind": "retained_fixed_point_summary_set",
                "record_count": len(context.events),
                "raw_behavior_data_retained": False,
                "evidence_scope": "sealed fixed-point event summaries",
            },
            sources=event_sources,
        )
        training = builder.object(
            "training_run",
            "learning_equilibrium",
            {"training": "population_mean_update_reconstruction"},
            {
                "learner": "population_mean",
                "status": "adapter_reconstructed_from_summary",
                "sample_size": parameters["sample_size"],
                "raw_training_sample_retained": False,
            },
            sources=event_sources,
        )

        candidates = []
        parameter_versions = []
        action_occurrences = []
        generated_data = []
        validations = []
        for sequence, event in enumerate(context.events):
            locator = event_sources[sequence]
            root = float(event["root"])
            candidate = builder.object(
                "ddge_candidate",
                "learning_equilibrium",
                {"sequence": sequence, "theta": root},
                {
                    "theta": root,
                    "derivative": float(event["derivative"]),
                    "stable": bool(event["stable"]),
                    "first_autocorrelation": float(event["first_autocorrelation"]),
                    "status": "numerically_validated",
                    "semantic_roles": ("ddge_candidate",),
                },
                sources=(locator,),
            )
            parameter = builder.object(
                "parameter_version",
                "learning_equilibrium",
                {"sequence": sequence, "coefficient": "forecast"},
                {
                    "coefficient_name": "forecast",
                    "value": root,
                    "candidate_ordinal": sequence,
                    "deployment_status": "candidate",
                },
                sources=(locator,),
            )
            action_occurrence = builder.object(
                "action_occurrence",
                "runtime_occurrence",
                {"sequence": sequence, "action": "stationary_population_response"},
                {
                    "event_sequence": sequence,
                    "occurrence_kind": "stationary_population_response_evaluation",
                    "deployed_parameter": root,
                    "raw_behavior_data_retained": False,
                },
                sources=(locator,),
            )
            datum = builder.object(
                "generated_datum",
                "runtime_occurrence",
                {"sequence": sequence, "datum": "population_learning_summary"},
                {
                    "event_sequence": sequence,
                    "datum_kind": "stationary_population_learning_summary",
                    "root": root,
                    "derivative": float(event["derivative"]),
                    "stable": bool(event["stable"]),
                    "first_autocorrelation": float(event["first_autocorrelation"]),
                    "raw_sample_retained": False,
                },
                sources=(locator,),
            )
            validation = builder.object(
                "numerical_validation",
                "learning_equilibrium",
                {"sequence": sequence, "candidate": candidate.id},
                {
                    "validation_method": "bracketing_iteration_and_derivative_cross_check",
                    "validation_scope": "aggregate_maximum_across_retained_roots",
                    "status": "passed",
                    "max_root_gap": context.metrics["max_root_gap"],
                    "derivative_error": context.metrics["derivative_error"],
                    "tolerance": 1e-10,
                    "solver": "brentq_and_multistart_fixed_point_iteration",
                    "stopping_rule": "residual_norm <= 1e-10 or 1000 iterations",
                    "semantic_roles": ("numerical_validation",),
                },
                sources=(locator, context.adapter_source),
            )
            builder.relation(
                "HAS_CANDIDATE",
                correspondence,
                candidate,
                {"sequence": sequence},
                locator=locator,
                properties={"ordinal": sequence, "selector": selector},
            )
            builder.relation(
                "CHOOSES",
                agent,
                action_occurrence,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "INSTANTIATES",
                action_occurrence,
                action,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "GENERATES",
                action_occurrence,
                datum,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "INCLUDED_IN",
                datum,
                dataset,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "DEPLOYS",
                model,
                parameter,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "DERIVED_FROM",
                candidate,
                parameter,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "VALIDATES",
                validation,
                candidate,
                {"sequence": sequence},
                locator=locator,
            )
            candidates.append(candidate)
            parameter_versions.append(parameter)
            action_occurrences.append(action_occurrence)
            generated_data.append(datum)
            validations.append(validation)

        closure_locator = artifact_source(context, "events.jsonl")
        builder.relation(
            "TRAINS",
            dataset,
            training,
            {"source": "retained_summary_dataset"},
            locator=closure_locator,
        )
        builder.relation(
            "TRAINS",
            learner,
            training,
            {"source": "declared_population_mean_learner"},
            locator=closure_locator,
        )
        builder.relation(
            "PRODUCES",
            training,
            model,
            {"model": "population_mean_forecaster"},
            locator=closure_locator,
        )

        provenance = builder.add_profile_provenance()
        builder.projected(
            "adapter.forecasting.roots",
            correspondence,
            *candidates,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.forecasting.learning_closure",
            dataset,
            training,
            *action_occurrences,
            *generated_data,
            source=closure_locator,
        )
        builder.projected(
            "adapter.forecasting.numerical_validations",
            *validations,
            source=closure_locator,
        )
        builder.projected(
            "adapter.forecasting.claim",
            claim,
            source=artifact_source(context, "metrics.json"),
        )
        builder.projected(
            "adapter.forecasting.learned_coefficients",
            model,
            *parameter_versions,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.forecasting.profile_provenance",
            provenance,
            source=context.adapter_source,
        )
        builder.gap(
            "adapter.forecasting.raw_behavior_data",
            "unavailable",
            "the sealed summary retains fixed-point statistics, not the simulated microdata",
        )
        builder.gap(
            "adapter.forecasting.welfare_bound",
            "unavailable",
            "no theorem certificate authorizes a welfare bound",
        )
        builder.gap(
            "adapter.forecasting.external_validation",
            "unavailable",
            "the experiment is synthetic and contains no external validation evidence",
        )
        return builder.finish()


FORECASTING_PROFILE = ForecastingOntologyProfile()
