"""Ontology profile for AI-mediated credit-regime experiments."""

from __future__ import annotations

from ewm._version import __version__
from ewm.core.provenance.serialization import content_digest

from .base import OntologyProfileContext, ProfileBuilder, ProfileProjection, artifact_source


class CreditOntologyProfile:
    """Project credit regimes while retaining locked evidence limitations."""

    identity = "ewm.credit-ontology-profile.v1"
    experiment_ids = frozenset({"credit.regimes"})
    package_versions = frozenset({__version__})
    artifact_schemas = frozenset({"ewm.run.v2"})
    source_digest = content_digest(
        {
            "profile": identity,
            "mapping_version": 1,
            "sources": (
                "ewm.scenarios.credit.model.CreditDDGEProblem",
                "ewm.experiments.credit.run_credit_regimes",
                "ewm.experiments.registry._credit",
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
        metadata = context.config["metadata"]

        world = builder.declaration(
            "world",
            {"scenario": "credit"},
            {
                "scenario": "credit",
                "world_kind": "ai_mediated_credit_laboratory",
                "source_id": metadata["source_id"],
            },
        )
        applicant = builder.declaration(
            "agent",
            {"scenario": "credit", "role": "applicant"},
            {"role": "applicant", "population_size": parameters["population_size"]},
        )
        lender = builder.declaration(
            "institution",
            {"scenario": "credit", "institution": "lender"},
            {"institution": "lender", "decision": "loan_approval"},
        )
        approval = builder.declaration(
            "action",
            {"scenario": "credit", "action": "approve_loan"},
            {"action": "approve_loan", "outcome_observation": "selective"},
        )
        learner = builder.declaration(
            "learner",
            {"scenario": "credit", "learner": "ridge_credit_model"},
            {
                "learner": "ridge_credit_model",
                "ridge": parameters["ridge"],
                "retraining_damping": parameters["retraining_damping"],
            },
        )
        selective_labels = builder.declaration(
            "constraint",
            {"scenario": "credit", "constraint": "selective_labels"},
            {
                "constraint_kind": "selective_labels",
                "description": "repayment labels are observed according to the regime",
            },
        )
        for ordinal, target in enumerate(
            (applicant, lender, approval, learner, selective_labels)
        ):
            builder.relation(
                "DECLARES",
                world,
                target,
                {"ordinal": ordinal},
                locator=context.adapter_source,
            )
        builder.relation(
            "SUBJECT_TO",
            approval,
            selective_labels,
            {"constraint": "selective_labels"},
            locator=context.adapter_source,
        )

        experiment = builder.object(
            "experiment",
            "research_evidence",
            {"experiment": context.experiment},
            {
                "experiment": context.experiment,
                "configuration": metadata["configuration"],
                "claim_type": metadata["claim_type"],
                "exact_replication": metadata["exact_replication"],
            },
            sources=(context.run_source,),
        )
        evidence = builder.object(
            "evidence_artifact",
            "research_evidence",
            {"evidence": "credit_qualitative_reconstruction"},
            {
                "profile_evidence": True,
                "evidence_classification": metadata["claim_type"],
                "source_id": metadata["source_id"],
                "exact_replication": metadata["exact_replication"],
                "published_target_differences": metadata["published_target_differences"],
                "qualitative_orderings": metadata["qualitative_orderings"],
                "sampling_noise_floor": metadata["sampling_noise_floor"],
            },
            sources=(artifact_source(context, "config.json", selector="metadata"),),
        )
        limitation = builder.object(
            "limitation",
            "research_evidence",
            {"limitation": "sampling_noise_floor_not_estimated"},
            {
                "limitation": "sampling_noise_floor_not_estimated",
                "description": metadata["sampling_noise_floor_limitation"],
                "residual_floor_semantics": metadata["residual_floor_semantics"],
                "status": "unresolved",
            },
            sources=(artifact_source(context, "config.json", selector="metadata"),),
        )
        builder.relation(
            "PRODUCES",
            experiment,
            evidence,
            {"evidence": "qualitative_reconstruction"},
            locator=artifact_source(context, "config.json", selector="metadata"),
        )

        regime_refs = []
        candidate_refs = []
        for sequence, event in enumerate(context.events):
            locator = artifact_source(
                context,
                "events.jsonl",
                selector=f"sequence={sequence}",
            )
            regime = str(event["regime"])
            outcome = builder.object(
                "outcome",
                "runtime_occurrence",
                {"sequence": sequence, "regime": regime},
                {
                    "outcome_kind": "credit_regime",
                    "regime": regime,
                    "approval_rate": event["approval_rate"],
                    "adoption_rate": event["adoption_rate"],
                    "observed_rate": event["observed_rate"],
                    "profit_per_applicant": event["profit_per_applicant"],
                    "predicted_profit_per_applicant": event[
                        "predicted_profit_per_applicant"
                    ],
                    "auc": event["auc"],
                    "false_positive_rate": event["false_positive_rate"],
                    "false_negative_rate": event["false_negative_rate"],
                },
                sources=(locator,),
            )
            builder.relation(
                "CONTAINS",
                context.run_ref,
                outcome,
                {"sequence": sequence},
                locator=locator,
            )
            diagnostic = builder.object(
                "stability_diagnostic",
                "learning_equilibrium",
                {"sequence": sequence, "regime": regime},
                {
                    "regime": regime,
                    "converged": event["converged"],
                    "iterations": event["iterations"],
                    "coefficient_distance": event["coefficient_distance"],
                    "residual_norm": event["residual_norm"],
                    "residual_floor": event["residual_floor"],
                    "status": (
                        "converged" if bool(event["converged"]) else "residual_qualified"
                    ),
                },
                sources=(locator,),
            )
            builder.relation(
                "DERIVED_FROM",
                diagnostic,
                outcome,
                {"sequence": sequence},
                locator=locator,
            )
            regime_refs.append(outcome)

            if regime not in {"selective_ddge", "full_information_ddge"}:
                continue
            candidate = builder.object(
                "ddge_candidate",
                "learning_equilibrium",
                {"sequence": sequence, "regime": regime},
                {
                    "regime": regime,
                    "status": (
                        "numerically_validated"
                        if bool(event["converged"])
                        else "residual_qualified"
                    ),
                    "converged": event["converged"],
                    "iterations": event["iterations"],
                    "coefficient_distance": event["coefficient_distance"],
                    "semantic_roles": ("ddge_candidate",),
                },
                sources=(locator,),
            )
            residual = builder.object(
                "residual",
                "learning_equilibrium",
                {"sequence": sequence, "regime": regime, "residual": "outer"},
                {
                    "value": [event["residual_norm"]],
                    "norm": event["residual_norm"],
                    "tolerance": parameters["ddge_tolerance"],
                    "solver": "damped_credit_retraining_iteration",
                    "stopping_rule": "residual_norm <= tolerance or max_iterations",
                    "status": (
                        "within_tolerance"
                        if float(event["residual_norm"])
                        <= float(parameters["ddge_tolerance"])
                        else "outside_tolerance"
                    ),
                    "residual_floor": event["residual_floor"],
                },
                sources=(locator,),
            )
            builder.relation(
                "HAS_RESIDUAL",
                candidate,
                residual,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "DERIVED_FROM",
                candidate,
                outcome,
                {"sequence": sequence},
                locator=locator,
            )
            candidate_refs.append(candidate)

        provenance = builder.add_profile_provenance()
        builder.projected(
            "adapter.credit.regimes",
            *regime_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.credit.ddge_candidates",
            *candidate_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.credit.evidence_limitation",
            evidence,
            limitation,
            source=artifact_source(context, "config.json", selector="metadata"),
        )
        builder.projected(
            "adapter.credit.profile_provenance",
            provenance,
            source=context.adapter_source,
        )
        builder.gap(
            "adapter.credit.exact_replication",
            "rejected",
            "the sealed run explicitly classifies itself as a qualitative reconstruction",
            source=artifact_source(context, "config.json", selector="metadata.exact_replication"),
        )
        builder.gap(
            "adapter.credit.sampling_noise_floor",
            "unavailable",
            str(metadata["sampling_noise_floor_limitation"]),
            source=artifact_source(
                context,
                "config.json",
                selector="metadata.sampling_noise_floor",
            ),
        )
        builder.gap(
            "adapter.credit.residual_vector",
            "unavailable",
            "the sealed regime summary retains residual norms but not coefficient residual vectors",
            source=artifact_source(context, "events.jsonl"),
        )
        return builder.finish()


CREDIT_PROFILE = CreditOntologyProfile()
