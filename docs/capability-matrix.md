# Capability and claim matrix

**Document version:** 1.3
**Last reviewed:** 2026-08-28
**Audience:** Researchers evaluating what release 0.2.0 establishes

## Two separate axes

Han et al.'s L1 to L6 ladder classifies systems capability. Cong's Data-Driven Generative
Equilibrium (DDGE) asks whether behavior, beliefs, generated data, and learned components are
mutually consistent. A small laboratory can solve a DDGE without being an L3 system. A capable
agent world can fail DDGE.

The package reports these axes separately and refuses higher capability awards when required
evidence is missing.

## Han capability ladder

| Level | Defining capability | Release 0.2.0 status | Evidence boundary |
|---|---|---|---|
| L1: fixed-rule agent world | Fixed agents interact under fixed rules and produce endogenous outcomes | Awarded for compiled FX | A hashed validation runs adaptive and fixed-belief arms under paired seeds, records canonical events, and checks economic invariants |
| L2: adaptive agent world | Rule-based agents adapt from interaction history and realized outcomes | Awarded for compiled FX | The same protocol observes household belief-state changes and longitudinal persistence. Its classification is synthetic systems conformance |
| L3: LLM-based agent world | Autonomous agents use explicit cognitive state, language, memory, and tools | Substrate ready; level withheld | Four readiness probes cover execution, cognitive state, memory and tools, and behavioral evaluation. Fixture execution is not a controlled language-model study |
| L4: self-evolving agent world | Agents acquire persistent strategies, skills, tools, or routines | Substrate ready; level withheld | Four probes cover proposals, gated promotion, persistence, and rollback. Authored fixtures do not show persistent measured improvement |
| L5: evolving economic world | Institutions, mechanisms, contracts, or governing rules evolve endogenously | Substrate ready; level withheld | Four probes cover proposals, constitutional gates, accepted changes, and outcomes. No endogenous proposal experiment or post-change outcome study exists |
| L6: sim-to-real economic twin | New external observations repeatedly diagnose and correct the running world | Offline substrate ready; level withheld | Four probes cover an external contract, repeated holdout alignment, drift monitoring, and correction performance. Only one offline fixture is available |

The L3 to L6 readiness harness is versioned and content-addressed. It emits 16 blocked readiness
artifacts, one per official requirement, and awards zero higher-level capabilities. The artifacts use
`readiness:` subjects, so they cannot cross the official `capability:` evidence boundary.

The highest awarded Han level is L2, and only for the compiled temporal FX laboratory. Forecasting,
scalar, production, and credit modules are mathematical laboratories rather than complete
capability-level worlds.

## Engineering desiderata

| Desideratum from Han et al. | Current support | Missing evidence |
|---|---|---|
| Endogenous closure | FX prices and allocations clear from submitted orders; forecasting and credit outcomes depend on deployed models | The laboratories are partial economies rather than a macroeconomic system |
| Behavioral fidelity | Heterogeneous symbolic roles, incentives, constraints, and bounded-memory adaptation | No empirical behavioral calibration or controlled language-model comparison |
| Evolving dynamics | FX beliefs adapt; capability and institutional transition substrates are executable | No repeated capability-improvement or institutional-outcome experiment |
| Reality alignment | Timestamped discrepancy, bounded correction, restoration, and provenance are tested offline | No live data contract, repeated holdout evaluation, or measured correction performance |

## DDGE and numerical evidence

| Laboratory | Learned component | DDGE status | Independent route and boundary |
|---|---|---|---|
| Scalar | Scalar linear or saturating learner | Solved | A package-import-free direct equation and sign-bracketing solver agree with iteration; an analytical concavity argument prespecifies one or three roots |
| Forecasting population | Zero-intercept forecasting slope | Solved with multistart | A package-import-free stationary Markov kernel and OLS map reproduce the three population roots; no finite-sample path claim follows |
| Forecasting finite sample | Realized retrained slope | Path simulated | Cong specifies 4,000 observations but not damping, so the path remains paper-inspired |
| Credit | Ridge-logistic screening system | Residual-qualified only | The prospectively locked local quick protocol breaches its solver tolerance for all four seeds. `analysis_valid=false`, and results are diagnostic only |
| FX | Beliefs adapt within rollout | No outer learned-system DDGE | Compiled execution preserves characterized pre-compiler outputs; conservation properties and the L1/L2 validation test the declared mechanism |
| Production | No learned component in the package instance | Not applicable | A package-import-free optimizer and direct market-clearing solve cross-check one package-authored finite instance, not a paper target |

The conformance report assesses DDGE claims per scenario. A failed or unrun conformance suite emits
no supported DDGE evidence and awards L0. A passing suite currently supports the registered scalar
and forecasting-population claims while retaining the credit result as `diagnostic_only`.

## Public capability inventory

| Capability | Available | Evidence scope |
|---|---|---|
| Complete named EWM declaration blocks | Yes | Typed state, action, outcome, intervention, agent, coherence, kernel, and intervention-semantic records |
| Declaration-to-runtime compilation | Yes | Strict action ownership, scheduling, constraint policy, state codecs, rollback, and RNG restoration tests |
| Constraint-preserving transitions | Yes | Reconciliation induction and atomic failure tests |
| Finite set-valued equilibrium verification | Yes | Separate behavior, belief, feasibility, aggregate, and learning certificates over declared candidates |
| Restricted affine and polyhedral theorem certificates | Yes | Assumption provenance, invariant-domain checks, solver residuals, and Euclidean contraction diagnostics |
| General arbitrary correspondence solver | No | No general Kakutani or infinite-dimensional proof engine |
| Multistart DDGE iteration and diagnostics | Yes | Roots, basins, failed starts, damping, residuals, Jacobians, singular values, and spectral radii |
| Reproducible run bundles | Yes | Sealed `ewm.run.v2` payload hashes and canonical identity |
| Legacy artifact inspection | Yes | `ewm.run.v1` is structurally verified in read-only, unsealed compatibility mode |
| Deterministic artifact replay | Partial | `replay-run` supports sealed v2 `fx.rollout` bundles |
| Independent numerical oracles | Yes | Scalar, forecasting-population, production-instance, and singular-direction oracles cannot import `ewm` |
| Five-layer Han evaluation report | Yes | Provenance-bearing agent, environment, co-evolution, alignment, and efficiency metrics; absent values stay `not_measured` |
| Empirical calibration | No | No external economic dataset is bundled or consumed |
| Policy recommendation | No | Synthetic mechanisms do not establish causal or policy validity |
| Live trading or lending | No | No execution connector exists |
| Distributed runtime | No | Execution remains synchronous and deterministic |

## Claims permitted for release 0.2.0

- The package implements selected EWM and DDGE definitions, protocols, and numerical targets from
  both locked papers.
- The scalar and forecasting-population laboratories reproduce their registered exact targets with
  package-import-free numerical checks.
- The compiled FX runtime preserves the declared direct mechanism outputs and tests L1/L2 synthetic
  systems conformance.
- Sealed v2 runs can be verified, and sealed FX rollouts can be replayed deterministically.
- L3 through L6 substrates have a 16-item readiness harness whose results remain blocked and
  non-awarding.

## Claims not permitted

- The package is a calibrated representation of an observed economy.
- Synthetic FX output forecasts exchange rates or validates a trading strategy.
- Credit output supports a lending decision or policy.
- A small residual proves behavioral optimality, welfare accuracy, or general equilibrium existence.
- The finite-sample forecasting path exactly replicates Cong's path.
- Fixture-backed cognition, promotion, governance, or alignment awards L3, L4, L5, or L6.
- Package-authored production prices are paper targets.
- The implementation is released or endorsed by either paper's authors.

## Evidence locations

- [Mathematical contract](mathematical-contract.md)
- [Replication guide](replication.md)
- [Limitations and non-goals](limitations.md)
- [Paper traceability](paper-traceability.md)
- [Experiment and artifact guide](experiments.md)
- [Local product-validation report](product-validation.md)
- [`tests/oracles/`](../tests/oracles)
- [`tests/conformance/`](../tests/conformance)
