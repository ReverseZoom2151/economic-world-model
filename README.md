# Economic World Model

`economic-world-model` is a research-oriented Python package for transparent Economic World Model
(EWM) and Data-Driven Generative Equilibrium (DDGE) experiments.

The initial release implements three self-contained synthetic laboratories:

- self-fulfilling forecasting and learning-generated multiplicity;
- a heterogeneous multi-agent foreign-exchange market;
- AI-mediated credit with endogenous adoption and selective retraining.

The package keeps rollout, fixed-environment equilibrium, retraining, and DDGE solution as distinct
operations. Shared typed state, constraints, mechanisms, random-number ownership, fixed-point
diagnostics, and experiment provenance prevent each laboratory from rebuilding infrastructure.

## Scientific scope

Version 0.1 is intended to validate transparent mechanisms and qualitative theory under synthetic
configurations. It is not an empirically calibrated economy, a policy oracle, a production trading or
lending system, or a sim-to-real economic twin.

The detailed approved design is in
[`docs/plans/2026-08-27-ewm-prototype-design.md`](docs/plans/2026-08-27-ewm-prototype-design.md).

## Status

Active initial implementation. Public APIs and runnable examples will be documented as each
laboratory lands.

## License

MIT

