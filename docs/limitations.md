# Limitations and non-goals

**Document version:** 1.2
**Last reviewed:** 2026-08-29
**Applies to:** `economic-world-model` release 0.2.0

## Research scope

The package executes synthetic economies and verifies declared mathematical, accounting, artifact,
and systems contracts. It has no empirical calibration dataset, field feed, human-subject study,
causal policy design, or production decision connector. Results describe configured mechanisms and
seeds. They do not estimate effects in an observed economy.

Do not use release 0.2.0 for lending, trading, employment, pricing, regulatory, or public-policy
decisions.

## Paper adaptation boundaries

### Cong Laboratory I

The credit laboratory is a qualitative reconstruction. The locked PDF specifies feature dimensions,
the learner family, cohort size, cutoff rule, feedback mechanism, and headline comparisons. It does
not identify the population and learning primitives required to recreate the fitted map. No
companion-code URL appears in the PDF, and the stated public artifact had not been located as of 27
August 2026.

Missing inputs include feature loadings and noise laws, repayment parameters, text-enhancement
parameters, adoption costs, payoffs, regularization, damping, seeds, and the sampling-noise
estimator. The package's residual floor is a deterministic recent-iterate diagnostic, not the paper's
finite-cohort sampling-noise floor.

The shipped v1 local protocol was locked before execution. Its quick mode completes all four fixed
seeds but breaches the prespecified solver residual tolerance in every replication. The report sets
`analysis_valid=false`, `claim_authorized=false`, and `evidence_status=diagnostic_only`. The outcome
summaries do not support inference, and the observed failure does not authorize retuning the locked
protocol.

### Cong Laboratory III

The population equations and Figure 4 parameters identify the registered slopes. A
package-import-free stationary-kernel OLS oracle reproduces those population roots. Cong does not
state the damping coefficient used in the finite-sample retraining paths. The package uses damping
0.5 and labels every resulting path as paper-inspired. Exact claims do not extend from the population
targets to finite-sample trajectory replication.

### Cong Appendix D

Appendix D is an equilibrium template rather than a calibrated numerical model. The package adds
CRRA preferences, a continuation approximation, a finite household distribution, decreasing-returns
Cobb-Douglas production, and all parameter values. A package-import-free objective optimizer and
market-clearing solve cross-check this bounded instance. They do not reproduce a paper value or
prove the general existence proposition.

### Han systems blueprint

Han et al. define system components, runtime interfaces, capability levels, and evaluation layers.
They do not specify one numerical economy for exact replication. The repository therefore tests
protocol conformance and keeps capability awards separate from substrate presence.

## Capability evidence

The highest evidence-awarded Han capability is L2 for the compiled FX agent world. The fixed
two-arm, two-seed validation is classified as synthetic systems conformance. It is not an empirical
validation or a prospective behavioral study.

| Level | Local substrate and readiness evidence | Evidence still required for an award |
|---|---|---|
| L3 | Four probes cover fixture execution, cognitive state, memory and tools, and behavior observations | Controlled language-model execution plus declared behavioral evaluation |
| L4 | Four probes cover capability proposals, promotion, persistence, and rollback | Repeated controlled evidence of persistent capability improvement |
| L5 | Four probes cover institution proposals, constitutional gates, accepted changes, and outcome measurement | Endogenous proposals and measured post-change economic outcomes |
| L6 | Four probes cover an external contract, repeated alignment, drift, and correction performance | A live external-data contract and repeated out-of-sample validation |

All 16 L3 to L6 readiness results remain blocked and non-awarding. A fake model backend cannot award
L3. A stored capability manifest cannot award L4. A fixture rule change cannot award L5. One offline
correction cannot award L6.

## Numerical scope

The generic DDGE solver accepts a single-valued outer update and uses multistart fixed-point
iteration. It retains roots reached from declared starts but cannot certify that no other root exists
outside the search region. The scalar and forecasting population oracles close the root-count gap
only for their declared one-dimensional domains.

Finite declared equilibrium correspondences can be exhaustively checked for behavioral, belief,
feasibility, aggregate, and learning consistency. The package has no general Kakutani solver or
infinite-dimensional proof system.

Restricted theorem certificates cover declared affine self-maps on nonempty compact polyhedra. They
check assumption provenance, invariant domains, fixed-point residuals, and solver residuals. They
keep Euclidean non-contraction, measured through the maximum singular value, separate from spectral
stability, measured through eigenvalues. General Assumption 3.2 and general existence still require
model-specific proofs.

Finite-difference Jacobians are local iteration diagnostics. Their classifications can depend on the
difference step in noisy or extreme regimes. Damping changes the numerical iteration; it does not
prove existence, uniqueness, economic stability, or welfare performance.

Theorem-derived displacement and welfare bounds require supplied contraction and sensitivity
constants. The package validates formula domains and arithmetic. It does not infer those assumptions
from arbitrary economic code.

## Scenario limitations

The FX laboratory is a small synchronous batch market with symbolic agents, bounded-memory belief
updates, one asset pair, and no external market data. Its compiled runtime preserves the
characterized pre-compiler numerical path for declared seeds and adds event and replay contracts.
That parity is a software migration check, not an independent economic model.

The credit laboratory uses synthetic latent quality, generated features, a ridge-logistic lender,
and a stylized binary approval decision. It omits legal obligations, fairness assessment,
macroeconomic conditions, loan pricing, and portfolio dynamics. Selective-label feedback can
produce a small discontinuity cycle, so some results are residual-qualified approximations.

The production instance uses three household types and a package-authored continuation approximation
rather than an infinite-horizon household value function. It solves one aggregate state and does not
update the distribution, productivity, or institutional regime over time.

The forecasting laboratory uses a one-dimensional aggregate process. Predictive fit within a
self-generated regime does not establish performance under intervention, regime change, or external
data.

## Runtime, artifacts, and replay

Release 0.2.0 executes agents serially to preserve deterministic ordering and owned random-number
streams. A `parallel` declaration is logged but does not activate concurrent execution. There is no
distributed runtime or checkpoint coordinator.

Current experiment runs use sealed `ewm.run.v2` bundles. Checksums detect accidental or hostile
mutation after publication, but they do not authenticate who produced a run. Legacy `ewm.run.v1`
compatibility is structural and read-only; those bundles remain unsealed.

Deterministic `replay-run` support currently covers sealed v2 `fx.rollout` artifacts. Other
experiments can be verified but not reconstructed through that command. Exact replay also depends on
the supported package and numerical runtime encoded by the implementation.

## Ontology and workbench limits

The ontology is a read-only derived view over verified `ewm.run.v2` evidence. Legacy v1 bundles can
be diagnosed but cannot be projected. Each scenario profile accepts exact experiment, package, and
artifact-schema versions. Unknown versions fail closed rather than receiving a best-effort mapping.

The five built-in profiles cover scalar, forecasting, FX, credit, and production experiments.
Coverage records semantic gaps, but a gap cannot reconstruct a missing declaration or observation.
Adapter-derived declarations come from installed package code and are not run-authored evidence.
Passing fourteen schema invariants establishes structural consistency, not truth, causal validity,
or completeness of the economic model.

The workbench is local, read-only, single-user, and bounded. It has no hosted service, account
system, collaboration, annotation persistence, ontology authoring, graph database, live telemetry,
remote data ingestion, model-provider integration, or automatic claim generation. The HTTP snapshot
endpoint returns an idempotent export plan; the explicit `ewm snapshot export` CLI performs file
publication.

The API caps collection reads and graph traversal. Portable snapshots default to 10,000 objects,
30,000 relations, 100,000 events, and 50 MiB of complete HTML. Nested canonical data, GeoJSON feature
count, source payload size, event lines, NPZ members, and request bodies also have hard limits. Large
runs require smaller selections or offline analysis outside the workbench.

The 3D ontology graph encodes semantic lane, ontology layer, and time. Position is an investigation aid, not
an estimated economic distance, causal effect, or embedding. WebGL availability and device limits
can reduce the rendered subset; the 2D fallback remains authoritative for the selected records.

The globe displays only objects linked to an explicit sourced `GeoAnchor`. Current built-in runs
have no run-authored geographic identifiers and show an unavailable state unless a researcher adds
a validated sidecar. A researcher-declared anchor retains that classification. Bundled simplified
Natural Earth boundaries provide visual context and are not a source for an object's location,
jurisdiction, policy status, or economic identity.

Snapshot digests and Content Security Policy hashes detect changed or malformed bytes. They do not
authenticate an author, institution, timestamp, or claim. A full-file digest obtained separately
supports file comparison only; release 0.2.0 has no digital-signature or transparency-log protocol.

### Reference performance environment

The 29 August 2026 small-tier observation used WSL2 Linux 5.15 on x86_64, Python 3.12.3, and 64
reported CPUs. The fixture was `fx.rollout` smoke at seed 73 with 242 objects, 335 relations, and 6
measurements. Across three repeats, p95 projection time was 0.850 seconds, a bounded 200-object query
was 0.000382 seconds, and standalone snapshot export was 2.398 seconds. Maximum traced Python memory
was 20.9 MB for projection and 54.9 MB for export.

These are observations from one machine and a small synthetic fixture. They are not service-level
objectives and do not predict medium, large, browser-rendering, or concurrent workloads. The
benchmark records interactive-open and 3D-frame budgets as targets because it does not measure those
operations.

## Evaluation limits

The five-layer evaluator combines event-derived metrics with provenance-bearing supplied
measurements. `not_measured` means that a run contains no evidence for that metric. It does not mean
zero error or perfect performance.

Behavioral fidelity, belief calibration, institutional quality, live alignment, and many scaling
measures remain unmeasured. Passing tests shows that code follows declared contracts. It does not
validate the economic realism or representativeness of those contracts.

## Software maturity

The project remains a research alpha. Public APIs are typed and tested, but compatibility across
minor releases is not guaranteed. Artifact identities include package, source, parameters, and
runtime versions so materially different executions do not share an identity.

The repository has automated dependency and source scanning plus a private vulnerability-reporting
policy. It has not undergone an external security, privacy, model-risk, or operational-resilience
audit. Offline cognition and alignment examples are protocol fixtures, not safe deployment
templates.
