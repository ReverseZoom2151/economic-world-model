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
            "mapping_version": 1,
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
        for ordinal, target in enumerate((agent, belief, learner)):
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
                "selector": "retain_all_independently_bracketed_roots",
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
                "evidence_classification": "synthetic_conformance",
                "max_root_gap": context.metrics["max_root_gap"],
                "derivative_error": context.metrics["derivative_error"],
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

        candidates = []
        parameter_versions = []
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
            builder.relation(
                "HAS_CANDIDATE",
                correspondence,
                candidate,
                {"sequence": sequence},
                locator=locator,
                properties={"ordinal": sequence},
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
            candidates.append(candidate)
            parameter_versions.append(parameter)

        provenance = builder.add_profile_provenance()
        builder.projected(
            "adapter.forecasting.roots",
            correspondence,
            *candidates,
            source=artifact_source(context, "events.jsonl"),
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
        for relation_type in ("generates", "included_in", "trains"):
            builder.gap(
                f"closure.{relation_type}",
                "unavailable",
                "the sealed forecasting summary does not retain this closure-stage record",
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
