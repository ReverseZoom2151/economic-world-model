# Paper implementation matrix

**Audit version:** 1.0  
**Source review:** 2026-08-28  
**Locked sources:** Cong (72 pages) and Han et al. (44 pages), both SHA-256 verified

This matrix is the human-readable index of the repository's paper obligations. The canonical,
machine-readable record is [`references/conformance.toml`](../references/conformance.toml), which
also names implementation files, executable evidence, claim classes, and precise limitations.
The audit covers 67 auditable requirements: 39 implemented, 22 partial, 2 blocked-external, and
4 not-applicable.

`Implemented` means the deliberately stated package scope has executable evidence. `Partial` means
useful substrate exists but some locally implementable behavior or required evidence is missing.
`Blocked-external` means exact completion requires a proof, source artifact, data stream, or empirical
study the repository does not possess. `Not-applicable` marks a theorem or nesting statement that is
important to the paper but is not itself an executable package obligation.

## Cong: formal EWM and DDGE surface

| Requirement | Paper anchor | Status |
|---|---|---|
| `cong-def-2.1` | Definition 2.1, pp. 13-14 | implemented |
| `cong-eq-2.1-2.2` | Equations 2.1-2.2, p. 14 | implemented |
| `cong-def-2.3` | Definition 2.3, pp. 14-15 | implemented |
| `cong-def-2.4` | Definition 2.4, pp. 15-16 | implemented |
| `cong-def-2.6` | Definition 2.6, p. 16 | implemented |
| `cong-def-3.1` | Definition 3.1, p. 23 | implemented |
| `cong-assumption-3.2` | Assumption 3.2, p. 27 | blocked-external |
| `cong-prop-3.3` | Proposition 3.3, pp. 28, 49 | partial |
| `cong-theorem-3.4` | Theorem 3.4, pp. 29-30, 50-51 | implemented |
| `cong-eq-3.1` | Equation 3.1, pp. 29, 50-51 | implemented |
| `cong-theorem-3.5` | Theorem 3.5, pp. 30-31, 51-52 | implemented |
| `cong-prop-4.1` | Proposition 4.1, pp. 37-38, 58-59 | implemented |
| `cong-assumption-a.1` | Assumption A.1, pp. 45-46 | not-applicable |
| `cong-theorem-a.2` | Theorem A.2, pp. 45-48 | not-applicable |
| `cong-prop-a.3` | Proposition A.3, pp. 46, 48 | implemented |
| `cong-prop-a.4` | Proposition A.4, pp. 52-53 | implemented |
| `cong-eq-a.1` | Equation A.1, p. 53 | implemented |
| `cong-prop-a.5` | Proposition A.5, pp. 53-55 | implemented |
| `cong-prop-a.6` | Proposition A.6, pp. 55-56 | not-applicable |
| `cong-prop-a.8` | Proposition A.8, pp. 56-57 | implemented |
| `cong-corollary-a.9` | Corollary A.9, pp. 57-58 | implemented |
| `cong-appendix-b-algorithm` | Appendix B, p. 61 | partial |
| `cong-lab-i` | Laboratory I, pp. 62-64, 70 | blocked-external |
| `cong-lab-ii` | Laboratory II, pp. 64, 71 | implemented |
| `cong-lab-iii-population` | Laboratory III population target, pp. 65-66, 72 | implemented |
| `cong-lab-iii-finite-sample` | Laboratory III finite-sample path, pp. 65-66, 72 | partial |
| `cong-prop-d.1` | Proposition D.1, pp. 66-68 | partial |
| `cong-theorem-e.1` | Theorem E.1, pp. 68-69 | not-applicable |

The principal local gap is the general Appendix B correspondence workflow: finite declared
candidate sets have joint DDGE certificates, while generic numerical search remains single-valued.
The general Kakutani result is a model-author proof obligation. Laboratory I cannot become an exact
replication until its omitted parameters or stated author code are available. The finite-sample
forecasting and production examples remain explicitly package-authored where the paper does not
identify the numerical primitives.

## Han et al.: mathematical state and component map

| Requirement | Paper anchor | Status |
|---|---|---|
| `han-eq-1` | Equation 1, p. 3 | implemented |
| `han-eq-2` | Equation 2, p. 4 | partial |
| `han-eq-3` | Equation 3, p. 4 | implemented |
| `han-eq-4` | Equation 4, p. 4 | implemented |
| `han-eq-5` | Equation 5, p. 4 | implemented |
| `han-eq-6` | Equation 6, p. 4 | implemented |
| `han-eq-7` | Equation 7, p. 4 | partial |
| `han-component-agents` | Section 4.1, pp. 11-12 | implemented |
| `han-component-environment` | Section 4.1, pp. 11-12 | implemented |
| `han-component-coevolution` | Section 4.1, p. 12 | implemented |
| `han-component-alignment` | Section 4.1, p. 12 | partial |

Equation 2 still needs a reusable grouped state that validates aggregate variables, private states,
beliefs, and institutions as separate first-class blocks. Equation 7 has controlled and governed
institutional transitions but still lacks an endogenous, agent-driven institutional experiment.
Alignment has bounded, versioned offline correction; live or repeated external correction remains an
evidence boundary.

## Han et al.: specification and runtime protocol

| Requirement | Paper anchor | Status |
|---|---|---|
| `han-spec-agent` | Section 4.2.1 and Figure 9, p. 13 | implemented |
| `han-spec-environment` | Section 4.2.2 and Figure 11, pp. 14-15 | implemented |
| `han-spec-coevolution` | Section 4.2.3 and Figure 13, pp. 15-16 | implemented |
| `han-spec-alignment` | Section 4.2.4 and Figure 15, pp. 16-17 | implemented |
| `han-spec-evaluation` | Section 4.2.5, pp. 17-19 | implemented |
| `han-runtime-reset` | Figure 8, pp. 12-13 | implemented |
| `han-runtime-run-agents` | Figures 8 and 10, pp. 12-14 | implemented |
| `han-runtime-step` | Figures 8 and 12, pp. 12, 15 | implemented |
| `han-runtime-coevolve` | Figures 8 and 14, pp. 12, 16 | implemented |
| `han-runtime-align` | Figures 8 and 16, pp. 12, 18 | implemented |
| `han-runtime-evaluate` | Figures 8 and 17, pp. 12, 19 | partial |
| `han-runtime-log` | Figure 8, p. 12 | implemented |

The compact runtime is present. Its remaining integration gap is that `world.evaluate()` returns a
legacy compact report while the complete five-layer report is obtained from a separate experiment
function. Agent execution also accepts `parallel=True` but deliberately runs serially until random
number ownership and event identity can remain deterministic under parallel execution.

## Han et al.: capability ladder

| Requirement | Paper anchor | Status |
|---|---|---|
| `han-level-l1` | Section 3.1, p. 7 | implemented |
| `han-level-l2` | Section 3.1, p. 7 | implemented |
| `han-level-l3` | Section 3.1, pp. 7-8 | partial |
| `han-level-l4` | Section 3.1, p. 8 | partial |
| `han-level-l5` | Section 3.1, pp. 8-9 | partial |
| `han-level-l6` | Section 3.1, p. 9 | partial |

The conformance harness awards L2 only. L3 needs controlled language-model behavioral evidence;
L4 needs persistent measured capability improvement; L5 needs an endogenous institutional-outcome
experiment; and L6 needs a real external-data contract plus repeated out-of-sample drift and
correction evidence. Interfaces or deterministic fakes cannot satisfy those evidence gates.

## Han et al.: five-layer evaluation

| Requirement | Paper anchor | Status |
|---|---|---|
| `han-eval-agents` | Table 3, p. 18 | partial |
| `han-eval-environment` | Table 3, p. 18 | partial |
| `han-eval-coevolution` | Table 3, p. 18 | partial |
| `han-eval-alignment` | Table 3, p. 18 | partial |
| `han-eval-efficiency` | Table 3, p. 18 | partial |

The report schema represents every paper metric without fabricating missing measurements. The next
implementation stage must generate belief calibration, behavioral diversity, mechanism-specific
clearing and settlement metrics, adaptation gain, policy change, trend error, and benchmark evidence
from the same versioned trajectory rather than attaching fragmented evidence after execution.

## Han et al.: five engineering waves

| Requirement | Paper anchor | Status |
|---|---|---|
| `han-wave-feature` | Section 5.1 and Table 4, pp. 19-20 | partial |
| `han-wave-data` | Section 5.2 and Table 4, pp. 19-20 | partial |
| `han-wave-prompt` | Section 5.3 and Table 4, pp. 19-20 | partial |
| `han-wave-context` | Section 5.4 and Table 4, pp. 19, 21 | partial |
| `han-wave-environment` | Section 5.5 and Table 4, pp. 19, 21 | partial |

The waves now have explicit conformance identities. Feature engineering needs reusable typed
transformations and lineage. Data engineering needs versioned economic datasets, temporal splits,
leakage checks, and training lineage. Prompt engineering needs versioned role and decision templates.
Context engineering needs retrieval, reflection, freshness, and evidence provenance. Environment
engineering must integrate the complete agent, co-evolution, institutional, alignment, and evaluation
loops in one executable economy.

## Completion order

Locally implementable gaps will be closed in dependency order:

1. establish stable package boundaries and a reusable grouped economic state;
2. implement feature and dataset contracts with temporal and provenance safeguards;
3. unify rule-based and cognitive agents behind one role/objective/belief/context/action boundary;
4. add versioned prompt, retrieval, reflection, and context-assembly contracts;
5. run co-evolution, institutional evolution, bounded alignment, and five-layer evaluation from one
   trajectory protocol;
6. complete the general finite-correspondence DDGE workflow and all scenario adapters;
7. execute local L3-L5 experiments and preserve failures as evidence;
8. keep L6, empirical validation, the general Kakutani proof, and exact credit replication blocked
   until their named external dependencies actually exist.

This ordering is an implementation plan, not a claim that every partial item can be promoted. A
requirement changes status only when its registered executable evidence satisfies its stated scope.
