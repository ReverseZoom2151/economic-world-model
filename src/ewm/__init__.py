"""Economic World Model research package."""

from importlib.metadata import version

__version__ = version("economic-world-model")

from .api import (
    ExperimentRun,
    ScenarioHandle,
    describe,
    list_experiments,
    list_scenarios,
    make,
    rollout,
    run_experiment,
)
from .equilibrium import solve_ddge, solve_equilibrium

__all__ = [
    "ExperimentRun",
    "ScenarioHandle",
    "__version__",
    "describe",
    "list_experiments",
    "list_scenarios",
    "make",
    "rollout",
    "run_experiment",
    "solve_ddge",
    "solve_equilibrium",
]
