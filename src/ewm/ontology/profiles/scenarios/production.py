"""Ontology profile for the package-authored competitive production economy."""

from __future__ import annotations

from ewm._version import __version__
from ewm.core.provenance.serialization import content_digest

from ..contracts.base import (
    OntologyProfileContext,
    ProfileBuilder,
    ProfileProjection,
    artifact_source,
)


class ProductionOntologyProfile:
    """Project optimization, feasibility, and two-market clearing diagnostics."""

    identity = "ewm.production-ontology-profile.v1"
    experiment_ids = frozenset({"production.equilibrium"})
    package_versions = frozenset({__version__})
    artifact_schemas = frozenset({"ewm.run.v2"})
    source_digest = content_digest(
        {
            "profile": identity,
            "mapping_version": 1,
            "sources": (
                "ewm.scenarios.production.model.ProductionEconomy",
                "ewm.experiments.production.solve_production_equilibrium",
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
        primitives = parameters["primitives"]
        distribution = parameters["distribution"]
        event = context.events[0]
        locator = artifact_source(context, "events.jsonl", selector="sequence=0")

        world = builder.declaration(
            "world",
            {"scenario": "production"},
            {
                "scenario": "production",
                "world_kind": "one_period_competitive_production_economy",
                "paper_template": "Cong Appendix D",
                "completion_status": "package_authored_instantiation",
                "package_authored_primitives": primitives,
                "distribution": distribution,
            },
        )
        household = builder.declaration(
            "agent",
            {"scenario": "production", "role": "household"},
            {"role": "household", "type_count": len(distribution["assets"])},
        )
        firm = builder.declaration(
            "agent",
            {"scenario": "production", "role": "firm"},
            {
                "role": "firm",
                "technology": "Cobb-Douglas",
                "capital_share": primitives["capital_share"],
                "labor_share": primitives["labor_share"],
            },
        )
        household_objective = builder.declaration(
            "objective",
            {"scenario": "production", "objective": "household_utility"},
            {"objective": "household_utility", "preferences": "CRRA_isoelastic_labor"},
        )
        firm_objective = builder.declaration(
            "objective",
            {"scenario": "production", "objective": "firm_profit"},
            {"objective": "firm_profit", "technology": "Cobb-Douglas"},
        )
        capital_market = builder.declaration(
            "market",
            {"scenario": "production", "market": "capital"},
            {"market": "capital", "price": "rental_rate"},
        )
        labor_market = builder.declaration(
            "market",
            {"scenario": "production", "market": "labor"},
            {"market": "labor", "price": "wage"},
        )
        mechanism = builder.declaration(
            "mechanism",
            {"scenario": "production", "mechanism": "competitive_clearing"},
            {"mechanism": "competitive_clearing", "markets": ("capital", "labor")},
        )
        budget = builder.declaration(
            "constraint",
            {"scenario": "production", "constraint": "budget_feasibility"},
            {"constraint_kind": "budget_feasibility"},
        )
        borrowing = builder.declaration(
            "constraint",
            {"scenario": "production", "constraint": "borrowing_bound"},
            {
                "constraint_kind": "borrowing_bound",
                "bound": primitives["borrowing_bound"],
            },
        )
        clearing_constraint = builder.declaration(
            "constraint",
            {"scenario": "production", "constraint": "market_clearing"},
            {"constraint_kind": "market_clearing", "markets": ("capital", "labor")},
        )
        declarations = (
            household,
            firm,
            household_objective,
            firm_objective,
            capital_market,
            labor_market,
            mechanism,
            budget,
            borrowing,
            clearing_constraint,
        )
        for ordinal, target in enumerate(declarations):
            builder.relation(
                "DECLARES",
                world,
                target,
                {"ordinal": ordinal},
                locator=context.adapter_source,
            )
        builder.relation(
            "OPTIMIZES",
            household,
            household_objective,
            {"role": "household"},
            locator=context.adapter_source,
        )
        builder.relation(
            "OPTIMIZES",
            firm,
            firm_objective,
            {"role": "firm"},
            locator=context.adapter_source,
        )
        for ordinal, constraint in enumerate((budget, borrowing)):
            builder.relation(
                "SUBJECT_TO",
                household,
                constraint,
                {"ordinal": ordinal},
                locator=context.adapter_source,
            )
        for ordinal, market in enumerate((capital_market, labor_market)):
            builder.relation(
                "SUBJECT_TO",
                market,
                clearing_constraint,
                {"ordinal": ordinal},
                locator=context.adapter_source,
            )
            builder.relation(
                "GOVERNED_BY",
                market,
                mechanism,
                {"ordinal": ordinal},
                locator=context.adapter_source,
            )

        invocation = builder.object(
            "mechanism_invocation",
            "runtime_occurrence",
            {"sequence": 0, "mechanism": "competitive_clearing"},
            {
                "event_sequence": 0,
                "initial_rental_rate": parameters["initial_rental_rate"],
                "initial_wage": parameters["initial_wage"],
                "iterations": event["iterations"],
            },
            sources=(locator,),
        )
        outcome = builder.object(
            "outcome",
            "runtime_occurrence",
            {"sequence": 0, "outcome": "competitive_allocation"},
            {
                "outcome_kind": "competitive_allocation",
                "rental_rate": event["rental_rate"],
                "wage": event["wage"],
                "aggregate_assets": event["aggregate_assets"],
                "aggregate_labor": event["aggregate_labor"],
                "households": event["households"],
                "firm": event["firm"],
            },
            sources=(locator,),
        )
        inner = builder.object(
            "inner_equilibrium",
            "learning_equilibrium",
            {"equilibrium": "competitive_production"},
            {
                "candidate_count": 1,
                "selector": "scipy_root_from_declared_initial_prices",
                "status": "numerically_validated",
            },
            sources=(locator,),
        )
        witness = builder.object(
            "equilibrium_witness",
            "learning_equilibrium",
            {"equilibrium": "competitive_production", "witness": "allocation"},
            {
                "prices": {
                    "rental_rate": event["rental_rate"],
                    "wage": event["wage"],
                },
                "firm_optimality": {
                    "capital_foc_residual": abs(event["firm"]["capital_foc_residual"]),
                    "labor_foc_residual": abs(event["firm"]["labor_foc_residual"]),
                },
                "household_optimality": {
                    "max_foc_residual": max(
                        max(
                            abs(household_record["savings_foc_residual"]),
                            abs(household_record["labor_foc_residual"]),
                        )
                        for household_record in event["households"]
                    ),
                    "max_budget_residual": max(
                        abs(household_record["budget_residual"])
                        for household_record in event["households"]
                    ),
                },
                "market_clearing": {
                    "capital_residual": event["capital_clearing_residual"],
                    "labor_residual": event["labor_clearing_residual"],
                },
                "status": "numerically_validated",
            },
            sources=(locator,),
        )
        residual_vector = [
            event["capital_clearing_residual"],
            event["labor_clearing_residual"],
        ]
        residual = builder.object(
            "residual",
            "learning_equilibrium",
            {"equilibrium": "competitive_production", "residual": "market_clearing"},
            {
                "value": residual_vector,
                "norm": event["residual_norm"],
                "tolerance": parameters["tolerance"],
                "solver": parameters["solver"],
                "stopping_rule": parameters["stopping_rule"],
                "status": (
                    "within_tolerance"
                    if float(event["residual_norm"]) <= float(parameters["tolerance"])
                    else "outside_tolerance"
                ),
            },
            sources=(locator,),
        )
        builder.relation(
            "CONTAINS",
            context.run_ref,
            invocation,
            {"sequence": 0},
            locator=locator,
        )
        builder.relation(
            "INSTANTIATES",
            invocation,
            mechanism,
            {"sequence": 0},
            locator=locator,
        )
        for ordinal, market in enumerate((capital_market, labor_market)):
            builder.relation(
                "CLEARS",
                invocation,
                market,
                {"ordinal": ordinal},
                locator=locator,
            )
        builder.relation(
            "REALIZES",
            invocation,
            outcome,
            {"sequence": 0},
            locator=locator,
        )
        builder.relation(
            "HAS_CANDIDATE",
            inner,
            witness,
            {"sequence": 0},
            locator=locator,
        )
        builder.relation(
            "HAS_RESIDUAL",
            witness,
            residual,
            {"sequence": 0},
            locator=locator,
        )

        experiment = builder.object(
            "experiment",
            "research_evidence",
            {"experiment": context.experiment},
            {
                "experiment": context.experiment,
                "scope": "package_authored_synthetic_instantiation",
            },
            sources=(context.run_source,),
        )
        evidence = builder.object(
            "evidence_artifact",
            "research_evidence",
            {"evidence": "production_numerical_solution"},
            {
                "profile_evidence": True,
                "evidence_classification": "synthetic_conformance",
                "converged": event["converged"],
                "solver_message": event["message"],
            },
            sources=(locator,),
        )
        limitation = builder.object(
            "limitation",
            "research_evidence",
            {"limitation": "package_authored_completion"},
            {
                "limitation": "package_authored_completion",
                "description": (
                    "functional forms, parameters, finite distribution, and continuation-value "
                    "closure are package-authored completions of Cong Appendix D"
                ),
                "status": "disclosed",
            },
            sources=(context.adapter_source,),
        )
        builder.relation(
            "PRODUCES",
            experiment,
            evidence,
            {"evidence": "numerical_solution"},
            locator=locator,
        )

        provenance = builder.add_profile_provenance()
        builder.projected(
            "adapter.production.optimization_and_clearing",
            inner,
            witness,
            residual,
            outcome,
            source=locator,
        )
        builder.projected(
            "adapter.production.authorship_limitation",
            limitation,
            source=context.adapter_source,
        )
        builder.projected(
            "adapter.production.profile_provenance",
            provenance,
            source=context.adapter_source,
        )
        builder.gap(
            "adapter.production.empirical_calibration",
            "unavailable",
            "the package-authored finite economy has no external calibration evidence",
        )
        builder.gap(
            "adapter.production.theorem_certificate",
            "unavailable",
            "the run contains a numerical witness but no general existence certificate",
        )
        return builder.finish()


PRODUCTION_PROFILE = ProductionOntologyProfile()
