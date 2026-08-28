# Mathematical contract

**Document version:** 1.3
**Last reviewed:** 2026-08-28
**Audience:** Economic-AI researchers and contributors

## Purpose and claim boundary

This document states the mathematical objects that release 0.2.0 makes executable. It separates
notation taken from the source papers from scenario equations introduced by this implementation.
The package is a synthetic research laboratory. None of the equations below is an empirical model
of an actual economy unless a future calibration explicitly establishes that claim.

## Source provenance

| Source | Contribution used here |
|---|---|
| Cong, *Economic World Models and Data-Driven Generative Equilibria* | Formal EWM objects, fixed-environment equilibrium, behavior-data-learning closure, DDGE, multiplicity, stability, and residual diagnostics |
| Han et al., *From Economic Agents to Agentic Economies* | Executable agents and environments, typed state transitions, co-evolution, evaluation, and the six-level capability ladder |
| This package | Single-valued numerical protocols, solver choices, the FX equations, missing credit primitives, and the functional forms used to instantiate Cong's Appendix D template |

The two papers are linked in the repository [README](../README.md#source-credit).

Source provenance has two separate checks. [`papers.toml`](../references/papers.toml) declares the
expected identity, hash, page count, and local filename for each paper; observed verification hashes
and parses only PDFs actually supplied to the local command. A missing ignored PDF is therefore
`not_present`, not silently treated as verified. [`replication-targets.toml`](../references/replication-targets.toml)
records each audited numerical fact, its locator and tolerance, and whether it is source-stated,
derived, or package-authored. This keeps a package choice from being counted as paper evidence.

## Economic World Model objects

Cong's Definition 2.6 defines an EWM as a structured tuple. Its exact blocks are:

| Object | Meaning |
|---|---|
| $\mathcal{S}$, $\mathcal{A}$, $\mathcal{Y}$ | State, action, and outcome spaces |
| $\mathcal{I}$ | Set of interventions or regimes |
| $N$ | Number of agents |
| $\mathcal{I}_t^n$ | Information available to agent $n$ at time $t$ |
| $\Pi^n$ | Admissible policies for agent $n$ |
| $\mu_t^n$ | Agent $n$'s belief representation at time $t$ |
| $\mathcal{C}$ | Economic coherence conditions |
| $T_{\theta}$, $O_{\theta}$ | Learned transition and observation kernels |
| $\Psi$ | Intervention semantics |

Release 0.2.0 realizes these ideas through typed records, agent policies, constraints, mechanisms,
transitions, observations, and explicit scenario configurations. It does not claim that every block is
learned or active in every laboratory.

The public `EconomicWorldModelDefinition` record encodes the complete tuple as named, immutable
blocks. `AgentBlock` groups each agent's information, admissible policies, and beliefs in the paper's
population notation

$$
\left\{(\mathcal{I}_t^n,\Pi^n,\mu_t^n)\right\}_{n=1}^N.
$$

`CoherenceCondition` distinguishes hard equalities, inequalities, and soft diagnostics.
`InterventionSemantics` names the parts of the world that each declared regime may change. This
object is a validated model declaration. Runtime conformance still depends on the world and scenario
implementations enforcing the declaration.

## Inner equilibrium and outer learning

Let $\pi$ denote the profile of agent policies, $\mu$ the profile of beliefs, $\theta\in\Theta$ the
learned system components, and $i$ the regime. Cong defines $E_i(\theta)$ as the set of
behavior-belief pairs satisfying behavioral optimality and belief consistency while $\theta$ is held
fixed. When this equilibrium is unique, its selector is

$$
S_i(\theta)=(\pi_i(\theta),\mu_i(\theta)).
$$

If $D$ generates data and $L$ retrains the learned component, the induced outer map is

$$
F_i(\theta)=L(D(S_i(\theta),\theta;i)).
$$

A full DDGE $(\pi^{\star},\mu^{\star},\theta^{\star})$ satisfies behavioral optimality, belief
consistency, and learning consistency:

$$
\theta^{\star}=L(D(\pi^{\star},\mu^{\star},\theta^{\star};i)).
$$

Under a single-valued selector, the outer condition reduces to

$$
\theta^{\star}=F_i(\theta^{\star}).
$$

The implementation reports the fixed-point residual

$$
r_i(\theta)=\lVert F_i(\theta)-\theta\rVert_2.
$$

A small residual establishes local model-data consistency only. Cong's welfare bound additionally
requires contraction and sensitivity assumptions. The package therefore never reports a residual as
a welfare guarantee by itself.

## Assumption-explicit theorem diagnostics

The package exposes Cong's bounds as certificates whose inputs name every required constant. Under
a contraction modulus $\lambda<1$, Theorem 3.4 gives

$$
\lVert\theta_i^{\star}-\bar\theta\rVert
\leq \frac{r_i(\bar\theta)}{1-\lambda}.
$$

Given discount factor $\beta$, utility sensitivity $K_u$, transition sensitivity $K_M$, and bounded
utility $\bar u$, the certificate also reports

$$
\lVert V_{i,\bar\theta}-V_{i,\theta_i^{\star}}\rVert_\infty
\leq
\left(
\frac{K_u}{1-\beta}
+\frac{2\beta\bar u K_M}{(1-\beta)^2}
\right)
\frac{r_i(\bar\theta)}{1-\lambda}.
$$

For a supplied averaged Jacobian $\bar J_i(\bar\theta)$ with operator norm below one,
`linear_center_displacement` evaluates Equation 3.1 directly:

$$
\theta_i^{\star}-\bar\theta
=
\left(I-\bar J_i(\bar\theta)\right)^{-1}
\left(F_i(\bar\theta)-\bar\theta\right).
$$

The primitive contraction certificate evaluates Proposition A.8,

$$
\lambda\leq L_L\left(L_{D,S}L_S+L_{D,\theta}\right),
$$

and the a posteriori certificate extends Corollary A.9 from remaining parameter distance to the
welfare bound. Tests compare these formulas with direct linear fixed-point solves and independently
solved Bellman systems.

For transition uncertainty of total-variation radius $\delta$, Proposition 4.1 is reported as

$$
\lVert V^\pi(T^\star)-V^\pi(T_\theta)\rVert_\infty
\leq \frac{2\beta\bar r}{(1-\beta)^2}\delta,
\qquad
\operatorname{Regret}_{\mathrm{rob}}
\leq \frac{4\beta\bar r}{(1-\beta)^2}\delta.
$$

Finally, `damping_stability_certificate` applies Appendix A.10 to every Jacobian eigenvalue. It
reports damping as capable of restoring local convergence only when every eigenvalue has real part
strictly below one. A real eigenvalue at or above one remains a repelling direction for every
positive damping level.

Constructive certificates are restricted to declared affine self-maps on nonempty compact
polyhedra. They validate invariant-domain assumptions, supplied provenance, fixed-point residuals,
and solver residuals. `local_linear_certificate` reports the maximum singular value and spectral
radius separately: a map can be spectrally stable while failing Euclidean contraction. These
routines do not prove Cong's general Assumption 3.2 or the general Kakutani existence result.

## Executable operations

```text
fixed theta and regime
        |
        v
solve inner equilibrium -> generate data -> retrain once
        ^                                      |
        |                                      v
        +------------ solve outer DDGE <-------+
```

| Operation | Contract |
|---|---|
| `rollout` | Generate a trajectory under a configured world and declared within-world adaptation |
| `solve_equilibrium` | Solve an inner residual $g(z;\theta,i)=0$ while $\theta$ and $i$ remain fixed |
| `retrain` | Apply one data-generation and learning update $\theta'=F_i(\theta)$ |
| `solve_ddge` | Search for all distinct outer fixed points reached from declared initializations |

The four operations are not interchangeable. In particular, trajectory convergence does not prove
economic equilibrium, and inner equilibrium does not prove learning consistency.

## Release 0.2.0 numerical scope

The theory permits set-valued correspondences. For finite declared candidate sets,
`EquilibriumCorrespondence` enumerates every inner behavior-belief equilibrium and refuses to select
silently when the set is empty or contains several candidates. Its `verify` method returns a
`DDGEConsistencyCertificate` with separate residual checks for behavioral optimality, belief
consistency, feasibility, aggregate consistency, and learning consistency. A candidate that satisfies
only the outer learned-parameter equation therefore fails certification.

The numerical solver remains deliberately narrower. It accepts a single-valued
`DDGEProblem.update` map and uses multistart iteration to retain distinct fixed points and their
initialization basins. It records failed starts, residual histories, damping, finite-difference
Jacobians, spectral radii, and local stability. The package verifies finite set-valued candidate sets;
it does not claim a general Kakutani or infinite-dimensional correspondence solver.

For a differentiable update $F$, the local diagnostic is

$$
J_F(\theta)=\frac{\partial F(\theta)}{\partial\theta},
\qquad
\rho(J_F(\theta^{\star}))<1
$$

for local stability of undamped fixed-point iteration. Damping changes the numerical update to

$$
\theta_{k+1}=(1-\eta)\theta_k+\eta F(\theta_k),
\qquad 0<\eta\leq 1.
$$

Damping is an algorithmic choice. It is not an existence, uniqueness, or welfare proof.

## Constraint-preserving transitions

Cong's Proposition A.3 starts from an unconstrained candidate next state
$\widetilde S_{t+1}$ and a reconciliation map whose codomain is the economically feasible set
$\Gamma(S_t,A_t,i_t)$. The realized transition is

$$
S_{t+1}
=
\Pi_{\Gamma(S_t,A_t,i_t)}\!\left(\widetilde S_{t+1}\right),
\qquad
\widetilde S_{t+1}
\sim
\widetilde T_{\theta}(\cdot\mid S_t,A_t,i_t).
$$

`StateReconciler` represents $\Pi_\Gamma$. When configured, `World.reset` rejects an infeasible
initial state. Each `World.step` passes the mechanism's candidate through the reconciler and checks
the resulting feasibility predicate before committing the new state or incrementing its version.
Starting from a feasible state, the test runs repeated candidate transitions and verifies feasibility
at every date, which is the induction in Proposition A.3. A faulty projection fails before state
commit.

## Han runtime and evaluation contract

Han et al. organize an EWM around economic agents and an executable environment. In the package,
the joint action profile at time $t$ is

$$
A_t=\bigl(a_t^1,\ldots,a_t^N\bigr),
$$

and the environment transition has the protocol-level form

$$
S_{t+1}=\mathcal{M}(S_t,A_t).
$$

Agent policies may use permitted observations, explicit beliefs, and private state:

$$
a_t^n=\pi^n\!\left(\mathcal{I}_t^n,\mu_t^n,s_t^n\right).
$$

The package expresses these relations through typed specifications and seven runtime calls:

```text
reset -> run_agents -> step -> coevolve -> align -> evaluate -> log
```

Each call emits a versioned event. `step` validates actions before the mechanism clears and settles.
`coevolve` changes only declared bounded components. `align` requires timestamped evidence and uses
atomic correction. `evaluate` reads an event snapshot without changing world state.

Han's five evaluation layers are agents, environment, co-evolution, alignment, and efficiency. A
metric has a value only when it carries event-derived or supplied provenance. An absent measurement
has status `not_measured`, value `None`, sample size zero, and no fabricated numerical value.

This contract establishes systems-protocol conformance. It does not establish L3 language-model
behavior, L4 persistent improvement, L5 endogenous institutional outcomes, or L6 real-world twin
validity. The [capability matrix](capability-matrix.md) records those evidence gates.

## Cong Laboratory II: scalar DDGE

The scalar module implements Appendix equation (A.1) directly:

$$
a=\kappa b+\theta+\delta,
\qquad
b=\gamma a,
\qquad
\theta^+=\Lambda\tanh(a).
$$

With inner feedback $\phi=\kappa\gamma$ and $|\phi|<1$, its fixed-environment solution and
composite gain are

$$
a^\star(\theta)=\frac{\theta+\delta}{1-\phi},
\qquad
b^\star(\theta)=\frac{\gamma(\theta+\delta)}{1-\phi},
\qquad
g=\frac{\Lambda}{1-\phi}.
$$

The implementation checks the exact linear intervention displacement, the one-versus-three-root
threshold at $g=1$, the near-onset expansion, stability of all branches, self-confirming versus
contrarian damping, and the a posteriori distance bound. A package-import-free oracle evaluates the
paper equation directly, proves the root count from oddness and strict concavity on the positive
axis, and finds the nonzero roots by sign bracketing. Package fixed-point iteration is the second
numerical route. The tests reproduce the error ranges reported for Figure 3, including the near-onset
approximation and first-order saturating displacement.

## Cong Laboratory III: self-fulfilling forecasting

The implementation defines

$$
a_t=\theta X_t,
\qquad
X_{t+1}=\tanh(c\theta X_t)+\sigma\varepsilon_{t+1}.
$$

The population retraining map is the zero-intercept OLS coefficient under the stationary law induced
by $\theta$:

$$
F(\theta)=
\frac{\mathbb{E}_{\theta}[X_t\tanh(c\theta X_t)]}
     {\mathbb{E}_{\theta}[X_t^2]}.
$$

Antithetic common random numbers preserve $F(0)=0$ and the analytical derivative $F'(0)=c$ in the
numerical population map. The named strong-feedback preset has three fixed points, with stable outer
branches and an unstable origin. A package-import-free oracle builds a discretized stationary Markov
kernel, solves its stationary law, evaluates the zero-intercept OLS map, and brackets the population
roots. A separate realized finite-sample update retains sampling noise and can leave the unstable
origin.

The named `paper_config` locks Figure 4's reported $c=1.8$ and $\sigma=0.5$. Its population
integration reproduces the three slopes $\{-0.795,0,+0.795\}$ within $0.003$, checks
$F'(0)=c$ within one percent, and verifies stable outer branches. The population implementation
uses the model's analytical odd symmetry, so the two outer roots are exact negatives rather than
independent Monte Carlo approximations.

`paper_finite_sample_config` uses the source-specified 4,000 observations per retraining round.
Seeded paths from $\theta_1^{(0)}=\pm0.10$ select the matching outer branch, while sampling noise
ejects an initialization at zero. The deployed momentum root produces a first autocorrelation near
the fitted slope, while the zero model produces a nearly flat ACF. Cong does not report the damping
coefficient used for this panel. The replication-target registry classifies the selected value as
package-authored, and every replication report records it as an implementation choice. It affects
the numerical path but cannot satisfy a source-stated target.

## Foreign-exchange laboratory

At candidate price $p$, aggregate executable demand and supply are

$$
B(p)=\sum_{o\in\mathcal{B}}q_o\,\mathbf{1}\{p_o\geq p\},
\qquad
S(p)=\sum_{o\in\mathcal{S}}q_o\,\mathbf{1}\{p_o\leq p\}.
$$

The uniform-price batch mechanism selects a candidate limit price that maximizes

$$
V(p)=\min(B(p),S(p)),
$$

then uses declared deterministic tie-breaking and pro-rata allocation on the long side. Feasibility is
checked against aggregate reserved cash or foreign currency before settlement. With no declared
external asset flow, every clearing event must satisfy

$$
\sum_n c_n'=\sum_n c_n,
\qquad
\sum_n f_n'=\sum_n f_n.
$$

The tests cover example books and generated feasible books, including budget and inventory
rejections, clearing equality, deterministic matching, and both conservation identities. The
compiled runtime preserves characterized pre-compiler outputs for declared seeds and adds strict
action contracts, state codecs, canonical event chains, and deterministic replay. Prespecified
firm-demand, trend-intensity, and fixed-belief interventions are paired with the adaptive baseline by
common random numbers. This compatibility experiment reports mean differences and
normal-approximation Monte Carlo intervals without a p-value claim. New locked protocols use
Student-t, paired bootstrap, Wilson, and Holm methods.

## AI-mediated credit laboratory

Each borrower has latent quality, ten structured features, fifteen text features, an adoption cost,
and a common potential repayment outcome. Polish changes only the text block. A borrower adopts
only when polish changes the lender's decision from rejection to approval and the private cost does
not exceed the loan benefit.

The lender uses ridge-logistic probabilities and approves at the zero-profit threshold

$$
\tau=\frac{\ell}{g+\ell},
$$

where $g$ is repayment gain and $\ell$ is loss given default. Selective retraining observes outcomes
only for approved applicants; full-information retraining observes the whole cohort. With retraining
damping $\eta$, the outer map is

$$
F(\theta)=(1-\eta)\theta+\eta\widehat{\theta}(D_{\theta}).
$$

The five regimes are no GenAI, frozen model, selective-observation DDGE, full-information DDGE,
and an omniscient quality oracle. `cong_qualitative_reconstruction` exhibits a frozen
predicted-versus-realized profit sign reversal and DDGE repair. The compatibility name
`paper_like_config` resolves to the same function, but package metadata always uses the explicit
name. Sensitivity cases retain parameter regions where the sign pattern does not occur.

This configuration is not an exact paper preset. Cong fixes 10 structured features, 15 text
features, a 26-dimensional ridge-logistic parameter, 40,000 applications per retraining round, and
the zero-profit cutoff. The locked PDF omits the numerical feature loadings and noise laws,
repayment link, enhancement parameters, adoption-cost law, payoffs, ridge penalty, damping,
initialization details, seeds, and sampling-noise estimator. The provenance registry and target
report retain these omissions and show package-versus-paper differences. A small deterministic
discontinuity cycle can produce a recent-iterate residual floor in this implementation; that value is
not relabeled as the paper's sampling noise floor.

The shipped, prospectively locked local v1 protocol fixes seeds, sample sizes, outcomes, stopping,
multiplicity, and solver tolerance before execution. Quick mode completes all four replications but
breaches the solver tolerance for every seed. The report sets `analysis_valid=false`, retains
summaries as `diagnostic_only`, and authorizes no claim.

## Cong Appendix D: competitive production template

Cong's Appendix D defines a household problem with consumption $c$, labor $\ell$, current assets
$a$, next-period assets $a'$, idiosyncratic state $e$, and prices $(r,w)$. Equations (D.1) through
(D.4) have the form

$$
V(a,e;Z,\mu,\kappa)
=
\max_{c,\ell,a'}
\left\{
u(c,\ell)
+\beta\,\mathbb{E}\!\left[V(a',e';Z,\mu,\kappa)\mid e\right]
\right\},
$$

subject to

$$
c+a'=w\ell+(1+r)a,
\qquad
a'\geq \underline a,
\qquad
e'\sim P(\cdot\mid e).
$$

The representative firm solves Equation (D.5):

$$
\max_{K,L}
\left\{
ZF(K,L)-(r+\delta)K-wL
\right\}.
$$

Equations (D.6) and (D.7) close capital and labor markets:

$$
K=\int a\,\mathrm{d}\mu,
\qquad
L=\int \ell\,\mathrm{d}\mu.
$$

The paper leaves the functional forms, parameter values, cross-sectional distribution, and
continuation solution open. The executable package instance supplies

$$
u(c,\ell;e)
=
\operatorname{CRRA}(c;\sigma)
-\frac{\chi}{e}\frac{\ell^{1+\nu}}{1+\nu},
$$

and uses the disclosed continuation approximation

$$
\omega\,\operatorname{CRRA}(a'-\underline a;\sigma),
$$

with decreasing-returns production

$$
Y=ZK^{\alpha}L^{\gamma},
\qquad
\alpha+\gamma<1.
$$

The solver works in transformed prices

$$
x_1=\log(r+\delta),
\qquad
x_2=\log w,
$$

and solves both market residuals with the shared inner-equilibrium solver. A package-import-free
oracle solves household and firm objectives directly, then clears both markets with a separate
least-squares route. Tests also check household budgets, borrowing feasibility, first-order
conditions, and both clearing equations. This is a paper-inspired instantiation of the Appendix D
template, not an exact numerical replication and not a proof of the general existence proposition.

## Evidence map

| Claim or invariant | Implementation | Independent evidence |
|---|---|---|
| Scalar fixed-point multiplicity and stability | `ewm.equilibrium`, `ewm.scenarios.scalar` | Analytical root count plus package-import-free direct equation and bracketing in `tests/integration/test_independent_numerical_oracles.py` |
| Forecasting population roots and derivative | `ewm.scenarios.forecasting` | Package-import-free stationary-kernel OLS oracle plus package iteration in `tests/integration/test_independent_numerical_oracles.py` |
| FX feasibility and conservation | `ewm.scenarios.fx` | Example and Hypothesis property tests in `tests/scenarios` and `tests/properties` |
| FX comparative statics | `ewm.experiments.fx` | Replicated common-random-number effects and interval tests in `tests/integration/test_comparisons.py` |
| Credit provenance, adoption, observation, and claim boundaries | `ewm.scenarios.credit`, `ewm.experiments.credit` | Source-target and economic-invariant tests in `tests/scenarios/test_credit_paper_targets.py` and `tests/scenarios/test_credit.py` |
| Appendix D production instantiation | `ewm.scenarios.production`, `ewm.experiments.production` | Package-import-free objective optimization and market clearing in `tests/integration/test_independent_numerical_oracles.py` |
| Han seven-call runtime protocol | `ewm.core.world`, `ewm.core.specs`, `ewm.core.events` | End-to-end event-order and version checks in `tests/integration/test_han_runtime_protocol.py` and `tests/conformance/test_han_conformance.py` |
| Five-layer evaluation | `ewm.experiments.evaluation` | Provenance, missingness, and read-only tests in `tests/integration/test_layered_evaluation.py` |
| L3 to L6 substrate boundaries | `ewm.capabilities`, `ewm.experiments.claims` | Sixteen blocked readiness artifacts plus adversarial evidence gates in `tests/conformance/test_han_l3_l6_readiness.py` and `tests/unit/test_capability_levels.py` |
| Constraint-preserving transitions | `ewm.core.reconciliation`, `ewm.core.world` | Induction and atomic-failure checks in `tests/unit/test_reconciliation.py` |
| Paper source locks and observed local verification | `references/papers.toml`, `ewm.experiments.source_verification`, `ewm.conformance`, `scripts/verify_sources.py`, `scripts/run_conformance.py` | Registry, mismatch, absence, and conformance-report checks in `tests/unit/test_source_verification.py`, `tests/integration/test_paper_traceability.py`, and `tests/integration/test_conformance_source_verification.py` |
| Audited replication targets | `references/replication-targets.toml` | Classification, symbol, evidence-path, and exact-claim coverage checks in `tests/integration/test_replication_targets.py` |
| One-way dependencies | Package layer boundaries | AST enforcement in `tests/test_architecture.py` |
| Reproducible public runs | `ewm.api`, `ewm.experiments`, `ewm.cli` | Integration tests for identical artifacts and public flows |
| Sealed artifact verification and FX replay | `ewm.experiments.verification`, `ewm.experiments.replay`, `ewm.core.replay` | Tamper, collision, installed-wheel, and deterministic replay tests in `tests/integration/test_artifact_integrity.py`, `tests/integration/test_run_cli.py`, and `tests/integration/test_run_replay.py` |
