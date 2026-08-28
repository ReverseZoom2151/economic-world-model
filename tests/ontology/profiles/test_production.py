from __future__ import annotations

from ewm.ontology.compiler import ProjectionCompilation


def test_production_profile_projects_optimization_and_market_clearing(
    production_projection: ProjectionCompilation,
) -> None:
    projection = production_projection.projection
    witness = next(obj for obj in projection.objects if obj.ref.kind == "equilibrium_witness")
    residual = next(obj for obj in projection.objects if obj.ref.kind == "residual")
    constraints = tuple(obj for obj in projection.objects if obj.ref.kind == "constraint")
    markets = tuple(obj for obj in projection.objects if obj.ref.kind == "market")

    assert {market.properties["market"] for market in markets} == {"capital", "labor"}
    assert witness.properties["status"] == "numerically_validated"
    assert witness.properties["firm_optimality"]["capital_foc_residual"] < 1e-10
    assert witness.properties["household_optimality"]["max_foc_residual"] < 1e-9
    assert isinstance(residual.properties["value"], tuple)
    assert len(residual.properties["value"]) == 2
    assert residual.properties["norm"] < residual.properties["tolerance"]
    assert {constraint.properties["constraint_kind"] for constraint in constraints} >= {
        "budget_feasibility",
        "borrowing_bound",
        "market_clearing",
    }


def test_production_profile_discloses_package_authorship_and_sources(
    production_projection: ProjectionCompilation,
) -> None:
    projection = production_projection.projection
    world = next(obj for obj in projection.objects if obj.ref.kind == "world")
    gaps = {entry.field: entry for entry in projection.coverage}

    assert world.properties["paper_template"] == "Cong Appendix D"
    assert world.properties["completion_status"] == "package_authored_instantiation"
    assert world.sources[0].source_kind == "scenario_adapter"
    assert gaps["adapter.production.empirical_calibration"].status == "unavailable"
