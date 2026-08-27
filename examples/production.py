"""Solve the disclosed competitive production-economy instantiation."""

from __future__ import annotations

from ewm.experiments import solve_production_equilibrium
from ewm.scenarios.production import package_authored_example


def main() -> None:
    economy = package_authored_example()
    equilibrium = solve_production_equilibrium(
        economy,
        initial_rental_rate=0.08,
        initial_wage=1.0,
    )
    print(
        f"converged={equilibrium.converged} "
        f"rental_rate={equilibrium.rental_rate:.6f} "
        f"wage={equilibrium.wage:.6f} "
        f"clearing_norm={equilibrium.residual_norm:.3e}"
    )
    print("primitive_source=package-authored; template_source=Cong Appendix D")


if __name__ == "__main__":
    main()
