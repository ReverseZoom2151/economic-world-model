"""Assembly of the package's default scenario and experiment catalog."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .models import Executor, ExperimentSpec, ScenarioPlugin, ScenarioRegistry
from .scenarios import (
    credit_config,
    credit_ddge,
    forecasting_config,
    forecasting_ddge,
    forecasting_rollout,
    fx_config,
    fx_rollout,
    scalar_config,
    scalar_ddge,
)


@dataclass(frozen=True, slots=True)
class DefaultCatalog:
    """The immutable default registry and its two public lookup views."""

    registry: ScenarioRegistry
    scenario_descriptions: Mapping[str, str]
    experiments: Mapping[str, ExperimentSpec]


def build_default_catalog(
    *,
    credit_executor: Executor,
    forecasting_executor: Executor,
    fx_comparative_statics_executor: Executor,
    fx_rollout_executor: Executor,
) -> DefaultCatalog:
    """Assemble default plugins around executors that retain stable provenance symbols."""

    credit_experiment = ExperimentSpec(
        "credit.regimes",
        "credit",
        "Compare no-AI, frozen, selective-DDGE, full-information-DDGE, and oracle credit regimes.",
        credit_executor,
    )
    forecasting_experiment = ExperimentSpec(
        "forecasting.ddge",
        "forecasting",
        "Find and independently verify the forecasting model's DDGE fixed points.",
        forecasting_executor,
    )
    fx_rollout_experiment = ExperimentSpec(
        "fx.rollout",
        "fx",
        "Run the adaptive heterogeneous FX economy and record clearing diagnostics.",
        fx_rollout_executor,
    )
    fx_comparative_statics_experiment = ExperimentSpec(
        "fx.comparative_statics",
        "fx",
        "Estimate replicated common-random-number FX effects and uncertainty intervals.",
        fx_comparative_statics_executor,
    )
    registry = ScenarioRegistry(
        (
            ScenarioPlugin(
                name="credit",
                description=(
                    "AI-mediated credit with endogenous decision-flip adoption, selective labels, "
                    "full-information retraining, and frozen and omniscient counterfactuals."
                ),
                config_factory=credit_config,
                ddge_factory=credit_ddge,
                experiments=(credit_experiment,),
            ),
            ScenarioPlugin(
                name="forecasting",
                description=(
                    "A self-fulfilling forecasting Data-Driven Generative Equilibrium with a "
                    "pitchfork multiplicity threshold and independent numerical oracles."
                ),
                config_factory=forecasting_config,
                ddge_factory=forecasting_ddge,
                rollout_factory=forecasting_rollout,
                experiments=(forecasting_experiment,),
            ),
            ScenarioPlugin(
                name="fx",
                description=(
                    "A heterogeneous household, firm, and bank economy with uniform-price batch "
                    "clearing, adaptive beliefs, balance feasibility, and conservation diagnostics."
                ),
                config_factory=fx_config,
                rollout_factory=fx_rollout,
                experiments=(
                    fx_comparative_statics_experiment,
                    fx_rollout_experiment,
                ),
            ),
            ScenarioPlugin(
                name="scalar",
                description=(
                    "Cong's closed-form scalar DDGE laboratory for displacement, multiplicity, "
                    "amplification, instability, and damping."
                ),
                config_factory=scalar_config,
                ddge_factory=scalar_ddge,
            ),
        )
    )
    return DefaultCatalog(
        registry=registry,
        scenario_descriptions=MappingProxyType(
            {name: plugin.description for name, plugin in registry.scenarios.items()}
        ),
        experiments=registry.experiments,
    )
