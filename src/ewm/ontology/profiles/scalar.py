"""Ontology profile for the executable scalar DDGE laboratory."""

from __future__ import annotations

from ewm._version import __version__
from ewm.core.serialization import content_digest

from .base import OntologyProfileContext, ProfileBuilder, ProfileProjection, artifact_source


class ScalarOntologyProfile:
    """Project scalar fixed points without conflating candidates and certificates."""

    identity = "ewm.scalar-ontology-profile.v1"
    experiment_ids = frozenset({"scalar.ddge"})
    package_versions = frozenset({__version__})
    artifact_schemas = frozenset({"ewm.run.v2"})
    source_digest = content_digest(
        {
            "profile": identity,
            "mapping_version": 2,
            "sources": (
                "ewm.scenarios.scalar.model.ScalarProblem",
                "ewm.scenarios.scalar.verification.scalar_verification_report",
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
        tolerance = float(parameters["tolerance"])
        solver = str(parameters["solver"])
        stopping_rule = str(parameters["stopping_rule"])
        selector = str(parameters["selector"])

        world = builder.declaration(
            "world",
            {"scenario": "scalar"},
            {
                "scenario": "scalar",
                "world_kind": "closed_form_ddge_laboratory",
                "paper_anchor": "Cong Appendix A.8 and Proposition A.5",
            },
        )
        agent = builder.declaration(
            "agent",
            {"scenario": "scalar", "role": "representative_agent"},
            {"role": "representative_agent", "behavior_variable": "a"},
        )
        learner = builder.declaration(
            "learner",
            {"scenario": "scalar", "learner": parameters["learner"]},
            {
                "learner": parameters["learner"],
                "learning_gain": parameters["learning_gain"],
                "map": "theta_next = learning_gain * tanh(behavior)",
            },
        )
        action = builder.declaration(
            "action",
            {"scenario": "scalar", "action": "behavior"},
            {"action": "behavior", "symbol": "a"},
        )
        for ordinal, target in enumerate((agent, learner, action)):
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
            {"correspondence": "scalar_ddge_set"},
            {
                "candidate_count": len(context.events),
                "selector": selector,
                "status": "numerically_validated",
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
                "preset": context.preset,
                "seed": context.seed,
            },
            sources=(context.run_source,),
        )
        evidence = builder.object(
            "evidence_artifact",
            "research_evidence",
            {"evidence": "scalar_independent_root_cross_check"},
            {
                "profile_evidence": True,
                "evidence_classification": "exact-replication",
                "method": "sign bracketing cross-checked against fixed-point iteration",
                "scope": "Cong Laboratory II scalar equations and targets",
            },
            sources=event_sources,
        )
        claim = builder.object(
            "claim",
            "research_evidence",
            {"claim": "cong_laboratory_ii_scalar_replication"},
            {
                "profile_evidence": True,
                "claim_kind": "exact_replication",
                "evidence_classification": "exact-replication",
                "status": "supported",
                "scope": "Cong Laboratory II scalar equations and targets",
                "qualification": (
                    "package-import-free direct-equation and bracketing oracle; "
                    "no empirical validation claim"
                ),
            },
            sources=event_sources,
        )
        builder.relation(
            "PRODUCES",
            experiment,
            evidence,
            {"evidence": "root_cross_check"},
            locator=context.run_source,
        )
        builder.relation(
            "SUPPORTS",
            evidence,
            claim,
            {"claim": "cong_laboratory_ii_scalar_replication"},
            locator=artifact_source(context, "events.jsonl"),
        )

        candidate_refs = []
        validation_refs = []
        for sequence, event in enumerate(context.events):
            locator = event_sources[sequence]
            root = float(event["root"])
            residual_value = float(event["residual"])
            candidate = builder.object(
                "ddge_candidate",
                "learning_equilibrium",
                {"sequence": sequence, "theta": root},
                {
                    "theta": root,
                    "derivative": float(event["derivative"]),
                    "stable": bool(event["stable"]),
                    "status": "numerically_validated",
                    "semantic_roles": ("ddge_candidate",),
                },
                sources=(locator,),
            )
            residual = builder.object(
                "residual",
                "learning_equilibrium",
                {"sequence": sequence, "candidate": candidate.id},
                {
                    "value": [residual_value],
                    "norm": abs(residual_value),
                    "tolerance": tolerance,
                    "solver": solver,
                    "stopping_rule": stopping_rule,
                    "status": (
                        "within_tolerance"
                        if abs(residual_value) <= tolerance
                        else "outside_tolerance"
                    ),
                },
                sources=(locator,),
            )
            validation = builder.object(
                "numerical_validation",
                "learning_equilibrium",
                {"sequence": sequence, "candidate": candidate.id},
                {
                    "validation_method": "independent_sign_bracketing_and_iteration",
                    "status": "passed" if abs(residual_value) <= tolerance else "failed",
                    "residual_norm": abs(residual_value),
                    "tolerance": tolerance,
                    "solver": solver,
                    "stopping_rule": stopping_rule,
                    "semantic_roles": ("numerical_validation",),
                },
                sources=(locator,),
            )
            builder.relation(
                "HAS_CANDIDATE",
                correspondence,
                candidate,
                {"sequence": sequence},
                locator=locator,
                properties={"selector": selector, "ordinal": sequence},
            )
            builder.relation(
                "HAS_RESIDUAL",
                candidate,
                residual,
                {"sequence": sequence},
                locator=locator,
            )
            builder.relation(
                "VALIDATES",
                validation,
                candidate,
                {"sequence": sequence, "target": "candidate"},
                locator=locator,
            )
            builder.relation(
                "VALIDATES",
                validation,
                residual,
                {"sequence": sequence, "target": "residual"},
                locator=locator,
            )
            candidate_refs.append(candidate)
            validation_refs.append(validation)

        provenance = builder.add_profile_provenance()
        builder.projected(
            "adapter.scalar.fixed_points",
            correspondence,
            *candidate_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.scalar.numerical_validations",
            *validation_refs,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.scalar.claim",
            claim,
            source=artifact_source(context, "events.jsonl"),
        )
        builder.projected(
            "adapter.scalar.profile_provenance",
            provenance,
            source=context.adapter_source,
        )
        builder.gap(
            "adapter.scalar.distance_bound",
            "unavailable",
            "the run contains no linked contraction or sensitivity certificate",
        )
        builder.gap(
            "adapter.scalar.empirical_validation",
            "unavailable",
            "the scalar laboratory is synthetic and has no external validation evidence",
        )
        return builder.finish()


SCALAR_PROFILE = ScalarOntologyProfile()
