# Paper traceability

**Document version:** 1.1
**Last reviewed:** 2026-08-27

This repository is an adaptation of two specific source versions, not a claim of author-endorsed
replication. The machine-readable registries in [`references/`](../references) make that distinction
auditable.

## Locked sources

[`papers.toml`](../references/papers.toml) records the title, authors, version, public source, page
count, and SHA-256 hash of each PDF used for implementation. Both local PDFs passed a structural
page preflight. The PDFs themselves remain ignored and are not redistributed.

The locked sources are:

- Cong, *Economic World Models and Data-Driven Generative Equilibria*, current draft April 2026.
- Han et al., *From Economic Agents to Agentic Economies: A Systems Blueprint for Economic World
  Models*, arXiv:2608.06020v1, 6 August 2026.

## How claims are classified

[`conformance.toml`](../references/conformance.toml) maps the papers' definitions, equations,
results, laboratories, components, runtime calls, capability levels, and evaluation layers to code,
tests, and explicit limitations.

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

## Current hard boundary: Cong Laboratory I

The paper says replication code accompanies its credit laboratory, but the locked PDF contains no
code URL. It specifies the model's feature dimensions, cohort size, learner family, decision rule,
and headline results, but omits parameters needed to recreate the exact population and fitted map.
Repository and public code searches did not locate the stated artifact as of 27 August 2026.

The package therefore calls its credit model a qualitative reconstruction. It can test the mechanism,
invariants, and prespecified qualitative sign patterns, but it cannot truthfully claim to reproduce the
paper's exact figure. This status can change if the author artifact becomes available and its source
identity is locked.

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
L2.

## Automated integrity checks

Run the registry integrity check:

```bash
python -m pytest tests/integration/test_paper_traceability.py -q
```

The test rejects duplicate or missing item IDs, unknown statuses or claim types, invalid source
hashes, and implemented/partial claims whose code or evidence paths do not exist.

Run the paper-level end-to-end suite and emit its evidence report:

```bash
python scripts/run_conformance.py
```

The report contains both source hashes, the package source fingerprint, runtime versions, fixed seed
sets, conformance test outcomes, achieved capability evidence, DDGE status, empirical-validity
status, and unresolved external dependencies. The [replication guide](replication.md) defines the
expected values and tolerances; [limitations](limitations.md) records the non-goals.
