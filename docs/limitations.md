# Limitations and non-goals

**Document version:** 1.0
**Last reviewed:** 2026-08-27
**Applies to:** `economic-world-model` version `0.1.0`

## Research scope

The package executes synthetic economies and verifies declared mathematical, accounting, and systems
contracts. It has no empirical calibration dataset, field data feed, human-subject study, causal
policy design, or production decision connector. Results describe the configured mechanisms and
random seeds. They do not estimate effects in an observed economy.

Do not use version `0.1.0` to make lending, trading, employment, pricing, regulatory, or public-policy
decisions.

## Paper adaptation boundaries

### Cong Laboratory I

The credit laboratory is a qualitative reconstruction. The locked PDF specifies feature dimensions,
the learner family, cohort size, cutoff rule, feedback mechanism, and headline comparisons. It does
not identify the numerical population and learning primitives required to recreate its fitted map.
No companion-code URL appears in the PDF, and a public artifact was not located as of 27 August 2026.

The missing inputs include feature loadings and noise laws, repayment parameters, text-enhancement
parameters, adoption costs, payoffs, regularization, damping, seeds, and the sampling-noise
estimator. The package's residual floor is a deterministic recent-iterate diagnostic, not the paper's
finite-cohort sampling-noise floor.

### Cong Laboratory III

The paper fixes the self-fulfilling forecasting equations and Figure 4 parameters, but it does not
state the damping coefficient used in the finite-sample retraining paths. The package uses damping
0.5 and labels it as package-authored. Exact claims cover the specified roots, parameters, and
reported patterns, not the omitted damping choice.

### Cong Appendix D

Appendix D is an equilibrium template rather than a calibrated numerical model. The package adds
CRRA preferences, a continuation approximation, a finite household distribution, decreasing-returns
Cobb-Douglas production, and all parameter values. The numerical equilibrium validates this finite
instance only. It does not reproduce a paper value or prove the general existence proposition.

### Han systems blueprint

Han et al. define system components, runtime interfaces, a capability ladder, and evaluation layers.
They do not specify a single numerical economy that the package could replicate. The repository
therefore tests protocol conformance and keeps capability awards separate from interface presence.

## Capability evidence

The highest evidence-awarded Han capability is L2 for the adaptive FX agent world.

| Level | Implemented substrate | Evidence still missing |
|---|---|---|
| L3 | Explicit cognitive state, memory, tools, action schemas, retry safety, and provenance | Controlled execution with a language model plus behavioral evaluation against declared criteria |
| L4 | Content-addressed capability proposals, evaluation and safety gates, persistence, promotion, and rollback | Repeated evidence that an agent proposes and retains a capability that improves measured performance |
| L5 | Governed institutional proposals, authority checks, constitutional validators, atomic application, and rollback | Endogenous institutional proposals and measured economic outcomes under accepted changes |
| L6 | Timestamped evidence, discrepancy metrics, bounded correction, provenance, and restoration | A live external-data contract, repeated out-of-sample alignment, drift monitoring, and correction-performance evidence |

A fake model backend cannot award L3. A stored capability manifest cannot award L4. A class that
changes rules cannot award L5. One offline correction cannot award L6.

## Numerical scope

The generic DDGE solver accepts a single-valued outer update map and uses multistart fixed-point
iteration. It records distinct roots reached from declared starts, but it cannot certify that no
other roots exist outside the searched region. Scenario-specific independent bracketing closes that
gap only for the low-dimensional scalar and forecasting cases.

Finite declared equilibrium correspondences can be exhaustively verified for behavioral, belief,
feasibility, aggregate, and learning consistency. The package does not implement a general Kakutani
solver or an infinite-dimensional equilibrium proof system.

Finite-difference Jacobians provide local iteration diagnostics. Their stability classifications can
depend on the difference step in noisy or extreme regimes. Damping changes the numerical iteration;
it does not prove existence, uniqueness, economic stability, or welfare performance.

Theorem-derived displacement and welfare bounds require caller-supplied contraction and sensitivity
constants. The package evaluates the formulas and checks their domains. It does not infer those
assumptions from arbitrary economic code.

## Scenario limitations

The FX laboratory is a small synchronous batch market with symbolic agents, bounded-memory belief
updates, one asset pair, and no order-book latency, strategic exchange operator, regulatory layer, or
external market data. Its intervention intervals are Monte Carlo summaries under a synthetic
configuration.

The credit laboratory uses synthetic latent quality, generated features, a ridge-logistic lender,
and a stylized binary approval decision. It omits legal obligations, fairness assessment, strategic
lender behavior, macroeconomic conditions, loan pricing, and portfolio dynamics. Selective-label
feedback can produce a small discontinuity cycle, so some states are residual-qualified
approximations.

The production instance uses a finite three-type distribution and a package-authored continuation
approximation rather than a solved infinite-horizon household value function. It solves one aggregate
state and does not update the distribution, productivity, or institutional regime over time.

The forecasting laboratory uses a one-dimensional aggregate process. Predictive fit within a
self-generated regime does not establish performance under intervention, regime change, or external
data.

## Runtime and scaling

Version `0.1.0` executes agents serially to preserve deterministic ordering and owned random-number
streams. A `parallel` declaration is logged but does not activate parallel execution. The package has
no distributed runtime, database, web service, dashboard, job queue, or checkpoint coordinator.

The 50-replication FX comparative-statics workload is the main local performance bottleneck. Current
benchmarks are development-machine measurements, not portability guarantees or latency objectives.

## Evaluation limits

The five-layer evaluator combines event-derived metrics with provenance-bearing external
measurements. It does not invent missing values. `not_measured` means that the current run has no
evidence for that metric; it does not mean zero error or perfect performance.

Behavioral fidelity, belief calibration, institutional quality, real-time trend alignment, and many
scaling measures remain unmeasured in the bundled laboratories. Passing the test suite shows that the
software follows its declared contracts. It does not validate the contracts' economic realism.

## Software maturity

The project is a research alpha. Public APIs are typed and tested, but compatibility is not yet
guaranteed across minor releases. Numerical behavior can shift when package-authored primitives or
solver defaults change. Reproducible run identities include the source fingerprint and runtime
versions so such changes do not share an artifact identity.

Security review, privacy review, model-risk governance, and operational resilience testing are out
of scope for this release. The offline cognitive and alignment examples must not be interpreted as
safe deployment templates.
