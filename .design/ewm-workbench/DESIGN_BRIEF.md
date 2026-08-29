# EWM Research Workbench Design Brief

## Product hierarchy

Economic World Model is the product. Research Workbench is the operating surface. Ontology is a shared semantic capability inside that surface, alongside simulation, markets, learning, validation, comparison, lineage, evidence, graph, and globe views.

## Audience and purpose

The primary user is an economic AI researcher working alone with one or more verified local runs. The interface must help that researcher move from a question to an economic object, inspect behavior and outcomes, trace generated evidence, compare compatible runs, and recover exact provenance when needed.

## Experience principles

1. Start from research intent, not implementation vocabulary.
2. Keep the selected run, object, time window, and comparison synchronized across modules.
3. Show human names and scientific meaning first. Put hashes, schema identities, locator keys, and full object IDs in collapsed technical details.
4. Make commands contextual. A control appears where its effect is visible and uses the same label in every module.
5. Distinguish platform navigation, workspace navigation, and object inspection.
6. Preserve scientific absence. Missing or incompatible evidence remains explicit and is never filled by visual inference.
7. Keep every interactive state keyboard reachable, screen-reader legible, and usable at mobile, tablet, and desktop sizes.

## Platform model

The persistent platform sidebar contains:

- Product identity: EWM and Economic World Model
- Surface identity: Research Workbench
- Core research modules: Overview, Economy, Simulation, Markets, Learning, Evidence
- Advanced modules: DDGE, Compare, Lineage, Graph, Globe
- Current approved run and integrity status

The contextual header contains:

- Research Workbench breadcrumb and active module
- Controls for the object catalog and selected evidence inspector
- A compact verified-run status

The workspace contains:

- Optional object catalog on the left
- Active analytical module in the center
- Optional evidence inspector on the right
- Timeline below modules that use temporal state

## Visual direction

Retain the existing editorial research-instrument language: warm paper surfaces, near-black ink, signal green, old-style serif display type, compact technical sans type, strict rules, and dark spatial canvases. Improve usability through alignment, rhythm, hierarchy, and consistent component states rather than replacing the visual identity with generic SaaS chrome.

## Component grammar

- Navigation items use one selected state, one hover state, and one focus treatment.
- Context commands use consistent height, border, label structure, and active state.
- Analytical tiles share header, content, footer, spacing, and selection behavior.
- Status information uses a shape and text, never color alone.
- Counts are visible only when they aid a decision.
- Exact technical identities live in a reusable disclosure component.

## Critical click paths

1. Open a verified run and understand its coverage.
2. Find an economic agent and inspect its evidence.
3. Replay a bounded episode and adjust the time window.
4. Read market outcomes and rejection reasons.
5. Verify behavior-to-learning closure.
6. Audit a claim back to source locators.
7. Compare two approved runs and understand rejected alignments.
8. Trace a directed lineage path.
9. Explore a selected object in synchronized 2D and 3D graph views.
10. Inspect only explicitly anchored economic geography on the globe.

## Reference findings

MikeOSS demonstrates a useful separation between persistent platform modules, recent working context, contextual page headers, and commands scoped to the current workspace. Palantir's published Ontology patterns separate semantic objects and links from actions that apply to the selected object set. Braintrust and Langfuse organize complex technical records around stable projects and hierarchical run or trace context. EWM adopts these structural lessons without copying their appearance.

The full five-site design-language study is recorded in [DESIGN_REFERENCE_ATLAS.md](DESIGN_REFERENCE_ATLAS.md). Carbon contributes system rigor, SGDS contributes a foundations-to-templates compositional ladder, Coinbase contributes executable documentation, Geist contributes operational calm, and Swiss Typefaces contributes editorial confidence. EWM combines these principles without reproducing any reference's brand or trade dress.
