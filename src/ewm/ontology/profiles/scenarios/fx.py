"""Ontology profile for heterogeneous foreign-exchange experiments."""

from __future__ import annotations

from ewm._version import __version__
from ewm.core.provenance.serialization import content_digest

from ...graph.model import OntologyRef
from ..contracts.base import (
    OntologyProfileContext,
    ProfileBuilder,
    ProfileProjection,
    artifact_source,
)


class FXOntologyProfile:
    """Project executable FX clearing and comparative-statistics evidence."""

    identity = "ewm.fx-ontology-profile.v1"
    experiment_ids = frozenset({"fx.rollout", "fx.comparative_statics"})
    package_versions = frozenset({__version__})
    artifact_schemas = frozenset({"ewm.run.v2"})
    source_digest = content_digest(
        {
            "profile": identity,
            "mapping_version": 2,
            "sources": (
                "ewm.scenarios.fx.runtime.fx_world_blueprint",
                "ewm.scenarios.fx.mechanism.UniformPriceBatchMechanism",
                "ewm.experiments.registry._fx",
                "ewm.experiments.registry._fx_comparative_statics",
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
            {"scenario": "fx"},
            {
                "scenario": "fx",
                "world_kind": "compiled_temporal_agent_economy",
                "adaptive_beliefs": parameters["adaptive_beliefs"],
            },
        )
        household = builder.declaration(
            "agent",
            {"scenario": "fx", "role": "household"},
            {"role": "household", "count": parameters["households"]},
        )
        firm = builder.declaration(
            "agent",
            {"scenario": "fx", "role": "firm"},
            {"role": "firm", "count": 1},
        )
        bank = builder.declaration(
            "agent",
            {"scenario": "fx", "role": "bank"},
            {"role": "bank", "count": 1},
        )
        market = builder.declaration(
            "market",
            {"scenario": "fx", "market": "spot_fx"},
            {
                "market": "spot_fx",
                "base_asset": "cash",
                "quote_asset": "foreign_currency",
                "clearing_rule": "uniform_price_batch",
            },
        )
        mechanism = builder.declaration(
            "mechanism",
            {"scenario": "fx", "mechanism": "uniform_price_batch"},
            {
                "mechanism": "uniform_price_batch",
                "tie_break": "maximum_volume_then_minimum_imbalance_then_price",
            },
        )
        learner = builder.declaration(
            "learner",
            {"scenario": "fx", "learner": "adaptive_trend_beliefs"},
            {
                "learner": "adaptive_trend_beliefs",
                "enabled": parameters["adaptive_beliefs"],
                "memory": parameters["belief_memory"],
                "trend_weight": parameters["trend_weight"],
            },
        )
        for ordinal, target in enumerate((household, firm, bank, market, mechanism, learner)):
            builder.relation(
                "DECLARES",
                world,
                target,
                {"ordinal": ordinal},
                locator=context.adapter_source,
            )
        for ordinal, agent in enumerate((household, firm, bank)):
            builder.relation(
                "PARTICIPATES_IN",
                agent,
                market,
                {"ordinal": ordinal},
                locator=context.adapter_source,
            )
        builder.relation(
            "GOVERNED_BY",
            market,
            mechanism,
            {"market": "spot_fx"},
            locator=context.adapter_source,
        )

        experiment = builder.object(
            "experiment",
            "research_evidence",
            {"experiment": context.experiment},
            {
                "experiment": context.experiment,
                "scope": "synthetic_conformance",
                "preset": context.preset,
                "seed": context.seed,
            },
            sources=(context.run_source,),
        )
        evidence = builder.object(
            "evidence_artifact",
            "research_evidence",
            {"evidence": "fx_verified_run"},
            {
                "profile_evidence": True,
                "evidence_classification": "synthetic_systems_conformance",
                "event_count": len(context.events),
                "scope": "deterministic synthetic FX runtime and accounting checks",
            },
            sources=(artifact_source(context, "events.jsonl"),),
        )
        claim = builder.object(
            "claim",
            "research_evidence",
            {"claim": "fx_synthetic_systems_conformance_observation"},
            {
                "profile_evidence": True,
                "claim_kind": "synthetic_systems_conformance_observation",
                "evidence_classification": "synthetic_systems_conformance",
                "status": "supporting_observation",
                "scope": "deterministic synthetic FX runtime and accounting checks",
                "capability_ceiling": "L2",
                "official_award": False,
                "qualification": (
                    "a sealed synthetic run is supporting evidence only; official capability "
                    "assessment remains evidence-gated"
                ),
            },
            sources=(artifact_source(context, "events.jsonl"),),
        )
        builder.relation(
            "PRODUCES",
            experiment,
            evidence,
            {"evidence": "verified_event_stream"},
            locator=artifact_source(context, "events.jsonl"),
        )
        builder.relation(
            "SUPPORTS",
            evidence,
            claim,
            {"claim": "fx_synthetic_systems_conformance_observation"},
            locator=artifact_source(context, "events.jsonl"),
        )

        if context.experiment == "fx.comparative_statics":
            self._project_comparisons(builder, context, experiment)
            provenance = builder.add_profile_provenance()
            builder.projected(
                "adapter.fx.profile_provenance",
                provenance,
                source=context.adapter_source,
            )
            builder.gap(
                "adapter.fx.transaction_counterparties",
                "unavailable",
                "comparative-statistics artifacts contain aggregate estimates, not trades",
            )
            return builder.finish()

        rollout = builder.object(
            "rollout",
            "runtime_occurrence",
            {"run": context.run_ref.id},
            {
                "semantic_roles": ("rollout",),
                "periods": parameters["periods"],
                "event_count": len(context.events),
                "status": "observed",
            },
            sources=(artifact_source(context, "events.jsonl"),),
        )
        builder.relation(
            "CONTAINS",
            context.run_ref,
            rollout,
            {"role": "fx_rollout"},
            locator=artifact_source(context, "events.jsonl"),
        )
        learning_diagnostic = builder.object(
            "stability_diagnostic",
            "learning_equilibrium",
            {"diagnostic": "adaptive_belief_configuration"},
            {
                "adaptive_beliefs": parameters["adaptive_beliefs"],
                "belief_memory": parameters["belief_memory"],
                "trend_weight": parameters["trend_weight"],
                "status": "configuration_observed",
            },
            sources=(artifact_source(context, "config.json", selector="parameters"),),
        )

        transaction_refs = []
        rejection_refs = []
        clearing_refs = []
        residual_refs = []
        validation_refs = []
        for event in context.events:
            if event.get("kind") != "step":
                continue
            sequence = int(event["sequence"])
            locator = artifact_source(
                context,
                "events.jsonl",
                selector=f"sequence={sequence}",
            )
            payload = event["payload"]
            outcomes = payload["outcomes"]
            invocation = builder.object(
                "mechanism_invocation",
                "runtime_occurrence",
                {"sequence": sequence, "mechanism": "uniform_price_batch"},
                {
                    "event_sequence": sequence,
                    "state_version": event["state_version"],
                    "accepted_count": payload["accepted_count"],
                    "submitted_count": payload["submitted_count"],
                },
                sources=(locator,),
            )
            transaction = builder.object(
                "transaction",
                "runtime_occurrence",
                {"sequence": sequence, "transaction": "aggregate_cleared_trade"},
                {
                    "transaction_kind": "aggregate_cleared_trade",
                    "event_sequence": sequence,
                    "price": outcomes["clearing_price"],
                    "volume": outcomes["volume"],
                    "accepted_order_count": outcomes["accepted_order_count"],
                    "submitted_order_count": outcomes["submitted_order_count"],
                },
                sources=(locator,),
            )
            rejection = builder.object(
                "outcome",
                "runtime_occurrence",
                {"sequence": sequence, "outcome": "order_rejections"},
                {
                    "outcome_kind": "order_rejections",
                    "event_sequence": sequence,
                    "rejected_count": outcomes["rejected_count"],
                    "violation_count": payload["violation_count"],
                    "violations": payload["violations"],
                },
                sources=(locator,),
            )
            clearing = builder.object(
                "inner_equilibrium",
                "learning_equilibrium",
                {"sequence": sequence, "equilibrium": "market_clearing"},
                {
                    "candidate_count": 1,
                    "selector": "uniform_price_max_volume_then_imbalance_then_price",
                    "status": "observed_clearing",
                    "clearing_residual": outcomes["clearing_residual"],
                    "cash_residual": outcomes["cash_residual"],
                    "foreign_residual": outcomes["foreign_residual"],
                },
                sources=(locator,),
            )
            witness = builder.object(
                "equilibrium_witness",
                "learning_equilibrium",
                {"sequence": sequence, "witness": "clearing_price"},
                {
                    "price": outcomes["clearing_price"],
                    "volume": outcomes["volume"],
                    "status": "observed",
                },
                sources=(locator,),
            )
            residual_values = (
                float(outcomes["clearing_residual"]),
                float(outcomes["cash_residual"]),
                float(outcomes["foreign_residual"]),
            )
            residual_norm = max(abs(value) for value in residual_values)
            tolerance = 1e-10
            residual = builder.object(
                "residual",
                "learning_equilibrium",
                {"sequence": sequence, "witness": witness.id},
                {
                    "value": residual_values,
                    "components": (
                        "clearing_residual",
                        "cash_conservation_residual",
                        "foreign_asset_conservation_residual",
                    ),
                    "norm": residual_norm,
                    "norm_type": "maximum_absolute_component",
                    "tolerance": tolerance,
                    "solver": "uniform_price_batch_enumeration",
                    "stopping_rule": "market-clearing and accounting residuals <= 1e-10",
                    "status": (
                        "within_tolerance"
                        if residual_norm <= tolerance
                        else "outside_tolerance"
                    ),
                },
                sources=(locator, context.adapter_source),
            )
            validation = builder.object(
                "numerical_validation",
                "learning_equilibrium",
                {"sequence": sequence, "witness": witness.id},
                {
                    "validation_method": "market_clearing_and_conservation_cross_check",
                    "status": "passed" if residual_norm <= tolerance else "failed",
                    "residual_norm": residual_norm,
                    "tolerance": tolerance,
                    "solver": "uniform_price_batch_enumeration",
                    "stopping_rule": "market-clearing and accounting residuals <= 1e-10",
                    "semantic_roles": ("numerical_validation",),
                },
                sources=(locator, context.adapter_source),
            )
            builder.relation(
                "CONTAINS",
                rollout,
                invocation,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "INSTANTIATES",
                invocation,
                mechanism,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "CLEARS",
                invocation,
                market,
                {"sequence": sequence},
                locator=locator,
            )
            for outcome_ordinal, realized in enumerate((transaction, rejection)):
                builder.relation(
                    "REALIZES",
                    invocation,
                    realized,
                    {"sequence": sequence, "ordinal": outcome_ordinal},
                    locator=locator,
                )
            builder.relation(
                "HAS_CANDIDATE",
                clearing,
                witness,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "HAS_RESIDUAL",
                witness,
                residual,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "VALIDATES",
                validation,
                witness,
                {"sequence": sequence, "target": "witness"},
                locator=locator,
            )
            builder.relation(
                "VALIDATES",
                validation,
                residual,
                {"sequence": sequence, "target": "residual"},
                locator=locator,
            )
            transaction_refs.append(transaction)
            rejection_refs.append(rejection)
            clearing_refs.append(clearing)
            residual_refs.append(residual)
            validation_refs.append(validation)

        provenance = builder.add_profile_provenance()
        builder.projected(
            "adapter.fx.transactions",
            *transaction_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.fx.accounting_residuals",
            *residual_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.fx.numerical_validations",
            *validation_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.fx.claim",
            claim,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.fx.rejections",
            *rejection_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.fx.clearings",
            *clearing_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.fx.learning_configuration",
            learning_diagnostic,
            source=artifact_source(context, "config.json", selector="parameters"),
        )
        builder.projected(
            "adapter.fx.profile_provenance",
            provenance,
            source=context.adapter_source,
        )
        builder.gap(
            "adapter.fx.transaction_counterparties",
            "unavailable",
            "the event contract retains aggregate clearing, not matched bilateral counterparties",
        )
        builder.gap(
            "adapter.fx.empirical_calibration",
            "unavailable",
            "the FX laboratory is synthetic and contains no external calibration evidence",
        )
        return builder.finish()

    @staticmethod
    def _project_comparisons(
        builder: ProfileBuilder,
        context: OntologyProfileContext,
        experiment: OntologyRef,
    ) -> None:
        for sequence, event in enumerate(context.events):
            locator = artifact_source(
                context,
                "events.jsonl",
                selector=f"sequence={sequence}",
            )
            comparison = builder.object(
                "comparison",
                "research_evidence",
                {
                    "sequence": sequence,
                    "comparison": event["comparison"],
                    "metric": event["metric"],
                },
                {
                    "comparison": event["comparison"],
                    "metric": event["metric"],
                    "paired_common_random_numbers": True,
                    "sample_size": event["sample_size"],
                    "mean_difference": event["mean_difference"],
                    "standard_error": event["standard_error"],
                    "interval": [event["interval_low"], event["interval_high"]],
                },
                sources=(locator,),
            )
            builder.relation(
                "COMPARES",
                comparison,
                experiment,
                {"sequence": sequence},
                locator=locator,
            )
        builder.projected(
            "adapter.fx.comparative_statistics",
            *(obj.ref for obj in builder.objects if obj.ref.kind == "comparison"),
            source=artifact_source(context, "events.jsonl"),
        )


FX_PROFILE = FXOntologyProfile()
