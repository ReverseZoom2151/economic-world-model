# Paper traceability

**Document version:** 1.3
**Last reviewed:** 2026-08-28

This repository is an adaptation of two specific source versions, not a claim of author-endorsed
replication. The machine-readable registries in [`references/`](../references) make that distinction
auditable.

## Locked sources

[`papers.toml`](../references/papers.toml) records the title, authors, version, public source,
expected page count, expected SHA-256 hash, media type, and local filename for each PDF used for
implementation. Those recorded values are source locks, not observations. A stored historical
preflight value cannot prove that a current checkout contains or has read the corresponding bytes.

The release-audit copies were verified locally against their expected hashes and page counts. The
PDFs themselves remain ignored and are not redistributed, so ordinary clones and remote CI jobs do
not contain them and cannot repeat that observation without separately supplied files.

The locked sources are:

- Cong, *Economic World Models and Data-Driven Generative Equilibria*, current draft April 2026.
- Han et al., *From Economic Agents to Agentic Economies: A Systems Blueprint for Economic World
  Models*, arXiv:2608.06020v1, 6 August 2026.

## How claims are classified

[`conformance.toml`](../references/conformance.toml) maps the papers' definitions, equations,
results, laboratories, components, runtime calls, capability levels, and evaluation layers to code,
tests, and explicit limitations.

[`replication-targets.toml`](../references/replication-targets.toml) is the audited transcription
boundary for numerical facts used in replication claims. Each target records its source and locator,
classification, typed value, tolerance, implementation symbol, and executable evidence. A target is
classified as `source-stated`, `derived`, or `package-authored`. In particular, the finite-sample
forecasting damping coefficient is a disclosed package-authored choice because Cong does not state
it; its presence cannot satisfy a source-stated target.

| Label | Meaning |
|---|---|
| `source-definition` | The package represents or documents a formal object from a paper. |
| `theorem-diagnostic` | Code evaluates a paper formula or theorem implication under caller-supplied assumptions. |
| `exact-replication` | The locked paper specifies enough equations, parameters, and targets for independent numerical reproduction. |
| `conformance` | The implementation satisfies a paper protocol or invariant; it is not a numerical replication claim. |
| `paper-inspired` | The paper supplies a template and this package supplies additional primitives or choices. |
| `qualitative-reconstruction` | The package recreates the stated mechanism and qualitative comparisons, but the source omits inputs needed for exact results. |
| `survey-only` | The item is a theoretical relation or literature classification, not an executable package obligation. |

Statuses describe what is present on the referenced commit. `implemented` means the declared scope
has executable evidence. `partial` identifies both the available substrate and the missing evidence.
`blocked-external` names a precise source, proof, data, or validation dependency that the repository
cannot supply. `not-applicable` covers survey or nesting statements that create no package
obligation.

## Current executable evidence and boundaries

Cong's hard equality, hard inequality, and soft coherence classes now execute as separate scalar
checks with declared units, scales, and tolerances. Finite categorical and callable stochastic
kernels validate support and normalization and record RNG provenance. Atomic interventions record
their component target, canonical before and after hashes, and a machine-readable replacement diff.
These implementations cover the registered source definitions. They do not establish Cong's
universal approximation theorem for arbitrary learned kernel classes.

The theorem-certificate layer has a deliberately restricted scope. It can constructively verify a
declared affine self-map on a nonempty compact polyhedron, check a fixed-point residual, and keep
Euclidean contraction separate from eigenvalue stability. Cong's general Assumption 3.2 and the
general Kakutani existence argument still require model-specific mathematical proofs and remain
blocked or partial in the registry.

The Cong Laboratory III population target now has a package-import-free numerical oracle based on
a separately implemented stationary-kernel OLS calculation. This closes the earlier independence
gap for the registered population roots. The finite-sample path remains paper-inspired because its
damping coefficient is package-authored. A separate production oracle cross-checks the bounded
package-authored Appendix D instance, but that result is neither a paper target nor a proof of the
general existence proposition.

## Current hard boundary: Cong Laboratory I

The paper says replication code accompanies its credit laboratory, but the locked PDF contains no
code URL. It specifies the model's feature dimensions, cohort size, learner family, decision rule,
and headline results, but omits parameters needed to recreate the exact population and fitted map.
Repository and public code searches did not locate the stated artifact as of 27 August 2026.

The package therefore calls its credit model a qualitative reconstruction. It can test the mechanism,
invariants, and prespecified qualitative sign patterns, but it cannot truthfully claim to reproduce the
paper's exact figure. This status can change if the author artifact becomes available and its source
identity is locked.

The repository also ships a prospectively locked local protocol for this reconstruction. Its current
quick execution completes all four fixed-seed replications but breaches the prespecified solver
residual tolerance in every replication. The report therefore returns `fail`, labels the evidence
`diagnostic_only`, and authorizes no scientific claim. Recording that failed result strengthens the
audit trail; it does not change Laboratory I's `blocked-external` replication status.

`src/ewm/scenarios/credit/provenance.py` records every fixed design fact, Figure 2 magnitude,
qualitative ordering, and missing primitive used in this determination. The comparison report exposes
numerical differences without using them as replication assertions. It also records currently
unmeasured quantities and orderings that the reconstruction does not reproduce. In particular, the
package's deterministic recent-iterate residual minimum is not Cong's finite-cohort sampling noise
floor.

## Han capability levels are evidence gates

Han's L1-L6 ladder is a systems taxonomy. A class named `Alignment` does not create an L6 economic
twin, and a fake language-model backend does not establish behavioral fidelity. The implementation
contains reusable L3-L6 substrates and assesses runtime evidence separately from interface
availability, DDGE consistency, and empirical validity. The cumulative evaluator currently awards
L2. That award is now backed by a hashed, versioned validation protocol over the compiled FX
runtime, with adaptive and fixed-belief arms, paired seeds, longitudinal observations, canonical
event chains, and separate evidence for every L1/L2 requirement. Its declared classification is
synthetic systems conformance. It explicitly excludes empirical validation and a prospective
behavioral study.

## Package engineering is not paper correspondence

Artifact v2 verification and deterministic replay protect the identity, integrity, and
reproducibility of run evidence. They are package engineering, not paper correspondence, because
neither locked source specifies this checksum format, command-line interface, or replay bundle
contract. The traceability registry maps the compiled FX execution and canonical event logging to
Han's runtime interfaces, but it does not turn the repository's sealing and replay design into a new
paper-derived claim.

## Automated integrity checks

Run the registry integrity check:

```bash
python -m pytest tests/integration/test_paper_traceability.py -q
```

The test rejects duplicate or missing item IDs, unknown statuses or claim types, malformed expected
source hashes, and implemented/partial claims whose code or evidence paths do not exist. It validates
the declared registry; it does not read an ignored PDF.

Verify any locally supplied source PDFs against the registry:

```bash
python scripts/verify_sources.py --source-dir .
```

The JSON output distinguishes `verified`, `not_present`, `hash_mismatch`,
`page_count_mismatch`, and `invalid_pdf`. Missing ignored PDFs report `not_present` and do not fail
this default metadata-friendly mode. For a strict local audit, require every source:

```bash
python scripts/verify_sources.py --source-dir . --require-all
```

Run the paper-level end-to-end suite and emit its evidence report:

```bash
python scripts/run_conformance.py
```

The report keeps `paper_sources` as the declared expected-hash map for schema compatibility and adds
an observed `source_verification` result for each registered source. A normal checkout can therefore
complete conformance with `not_present` observations. To require local source bytes as part of that
same run, use:

```bash
python scripts/run_conformance.py --source-dir . --require-sources
```

The strict form fails for missing sources and for every verification mismatch. The report also
contains the package source fingerprint, runtime versions, fixed seed sets, conformance test
outcomes, achieved capability evidence, DDGE status, empirical-validity status, and unresolved
external dependencies. The [replication guide](replication.md) defines the expected values and
tolerances; [limitations](limitations.md) records the non-goals.
