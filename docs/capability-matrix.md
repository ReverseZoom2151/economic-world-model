# Capability and claim matrix

**Document version:** 1.1
**Last reviewed:** 2026-08-27  
**Audience:** Researchers evaluating what version `0.1.0` does and does not establish

## Why this matrix exists

The repository implements meaningful pieces of an Economic World Model, but three stylized
laboratories are not a real-economy twin. This matrix maps executable evidence to Han et al.'s
capability ladder and keeps that engineering taxonomy separate from Cong's DDGE consistency
concept.

## Han et al. capability ladder

| Level | Defining capability | Version 0.1 status | Evidence or missing requirement |
|---|---|---|---|
| L1: fixed-rule agent world | Fixed agents interact under fixed rules and generate outcomes endogenously | Awarded for the FX kernel | Typed household, firm, and bank policies; endogenous batch clearing and settlement |
| L2: adaptive agent world | Rule-based agents adapt from interaction history and realized outcomes | Awarded for the FX laboratory | Household belief weights update from realized returns using bounded memory |
| L3: LLM-based agent world | Autonomous agents reason with explicit cognitive state, language, and memory | Substrate implemented; level not awarded | Provider-neutral cognition, beliefs, memory, tools, schemas, retries, and provenance pass fake-backend tests. No controlled language-model behavioral evaluation exists |
| L4: self-evolving agent world | Agents persistently acquire strategies, skills, tools, or behavioral routines | Substrate implemented; level not awarded | Content-addressed proposals, evaluation gates, persistence, promotion, and rollback are tested. No agent has demonstrated persistent capability improvement |
| L5: evolving economic world | Institutions, mechanisms, contracts, or governing rules evolve endogenously | Substrate implemented; level not awarded | Governed transitions enforce authority and constitutional checks. No endogenous institutional experiment has evaluated resulting outcomes |
| L6: sim-to-real economic twin | Online comparison with real observations repeatedly corrects the running world | Offline protocol implemented; level not awarded | Timestamp, discrepancy, bounded correction, provenance, and restoration are tested against a fixture. No live data contract or repeated out-of-sample validation exists |

The highest evidence-awarded Han level is **L2**, and only for the temporal FX laboratory. The
forecasting and credit modules are DDGE laboratories rather than complete capability-level worlds.
The presence of a symbolic GenAI intervention in credit does not make its borrowers LLM agents.

The package enforces this distinction in `ewm.capabilities.assess_capability`. The assessment is
cumulative: evidence for L4 cannot skip a missing L3 requirement. Interfaces and self-reported
labels never suffice. L3 requires controlled language-model and behavioral evidence; L4 and L5
require repeated outcome evidence; L6 requires an external-validation class, an external data
contract, and repeated observations.

## Engineering desiderata

| Desideratum from Han et al. | Status | Evidence | Limitation |
|---|---|---|---|
| Endogenous closure | Implemented for declared mechanisms | FX prices and allocations clear from orders; forecasting aggregates and credit selection depend on deployed models | The laboratories are partial economies, not a complete macroeconomic system |
| Behavioral fidelity | Synthetic only | Heterogeneous roles, incentives, constraints, bounded-memory adaptation, and endogenous adoption | No empirical behavioral calibration or validation against human subjects |
| Evolving dynamics | Partial | FX beliefs adapt; gated capability and institution-transition substrates are implemented | No experiment establishes persistent skill improvement or endogenous institutional outcomes |
| Reality alignment | Offline protocol only | A timestamped fixture exercises discrepancy, correction, provenance, and restoration | No live source, repeated holdout evaluation, or empirical twin claim |

## DDGE consistency is a separate axis

Han et al.'s levels describe systems capability. DDGE describes whether behavior, beliefs, generated
data, and learned components are mutually consistent. A high-level agent system can fail DDGE, and
a small mathematical laboratory can solve a DDGE without being an L3 to L6 world.

| Laboratory | Temporal agent world | Endogenous learned component | DDGE solved | Independent checks |
|---|---|---|---|---|
| Forecasting | No, scalar aggregate process | Forecasting slope | Yes, population map with multistart | Analytical derivative and Brent bracketing |
| FX | Yes, L2 symbolic agents | Beliefs adapt within rollout, but no outer learned-system DDGE | No | Conservation property tests and replicated paired intervals |
| Credit | No, synthetic cohort equilibrium | Ridge-logistic screening model | Yes, selective and full-information regimes | Frozen/realized sign test, omniscient oracle, and sensitivity boundary |

## Public capability matrix

| Capability | Available | Evidence |
|---|---|---|
| Typed economic actions and immutable transitions | Yes | `ewm.core` records and runtime tests |
| Feasibility before mechanism execution | Yes | Constraint rejection tests and FX reservation checks |
| Deterministic owned random-number generators | Yes | RNG and repeatability tests |
| Inner equilibrium root solving | Yes | SciPy-preserving wrapper and independent unit comparison |
| DDGE iteration, damping, multistart, and diagnostics | Yes | Fixed-point and diagnostic test suite |
| Reproducible local experiment bundles | Yes | Stable facade, CLI, artifact schema, and byte-identity integration test |
| Provider-neutral cognitive agent substrate | Yes | Structured actions, explicit beliefs, bounded memory, tools, retry safety, and decision provenance |
| Evidence-gated capability registry | Yes | Content-addressed proposals, sandbox and safety gates, persistence, promotion, and rollback |
| Governed institutional transition substrate | Yes | Authority, feasibility, accounting, safety, acceptance, audit, and rollback tests |
| Offline external-alignment protocol | Yes | Timestamp, target discrepancy, bounded atomic correction, event provenance, and restoration tests |
| Machine-checkable L1 to L6 evidence gates | Yes | Cumulative adversarial gate tests and separate DDGE and empirical-validity assessments |
| Empirical calibration | No | No external economic data is bundled or consumed |
| Policy recommendation | No | Synthetic mechanisms do not establish policy validity |
| Live trading or lending | No | Research-only local package with no execution connector |
| Dashboard, web app, or database | No | Explicitly outside the initial model package |
| Distributed or parallel runtime | No | Synchronous deterministic version 0.1 runtime |
| Finite set-valued equilibrium verification | Yes | Separate behavior, belief, feasibility, aggregate, and learning certificates over declared candidates |
| General arbitrary equilibrium correspondence solver | No | Finite verification plus a single-valued update solver; no generic Kakutani algorithm |

## Claims permitted for version 0.1

- The package implements transparent synthetic EWM and DDGE mechanisms inspired by both papers.
- The forecasting laboratory reproduces its prespecified mathematical fixed-point behavior.
- The FX mechanism enforces its declared feasibility and conservation invariants.
- The named credit configuration reproduces prespecified qualitative feedback patterns and exposes
  sensitivity boundaries.
- Runs are reproducible under the documented package version, parameters, and seed.
- The package implements testable L3 through L6 engineering substrates while withholding those
  capability awards until their stronger evidence gates are met.

## Claims not permitted

- The package is a calibrated model of an observed economy.
- The synthetic FX series forecasts actual exchange rates.
- The credit results justify a real lending decision or policy.
- A small residual alone proves a small welfare error.
- L2 adaptive behavior makes the package an L3, L4, L5, or L6 system.
- Passing fake-backend, promotion, governance, or one-shot alignment tests awards L3, L4, L5, or L6.
- The implementation is an exact numerical replication released or endorsed by the paper authors.

## Evidence locations

- [Mathematical contract](mathematical-contract.md)
- [Experiment and artifact guide](experiments.md)
- [Local product-validation report](product-validation.md)
- [Approved design](plans/2026-08-27-ewm-prototype-design.md)
- [Audited dependency map](architecture/ewm_foundations_dependency_map.md)
- [`tests/`](../tests)
