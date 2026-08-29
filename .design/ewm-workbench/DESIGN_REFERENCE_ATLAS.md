# EWM Design Reference Atlas

## Scope

This atlas records a full public-site study of five design-language references on 29 August 2026:

- [Carbon Design System](https://carbondesignsystem.com/)
- [Singapore Government Design System](https://www.designsystem.tech.gov.sg/)
- [Coinbase Design System](https://cds.coinbase.com/)
- [Geist Design System](https://vercel.com/geist/introduction)
- [Swiss Typefaces](https://www.swisstypefaces.com/)

The study is an input to EWM's own design system. It is not a request to reproduce any reference's brand, components, copy, imagery, or trade dress.

## Method

The scan reconciled published sitemaps with in-page navigation and internal links. Swiss Typefaces does not publish a working sitemap, so its route set was discovered from the homepage, catalogue, global navigation, and recursively linked public pages.

For every HTML route, the scan collected:

- response and final URL
- document title and language
- all visible headings and heading levels
- navigation, table-of-contents, control, and landmark labels
- semantic section labels and heights
- internal links
- representative computed typography, color, and radius values
- document dimensions
- visual captures at the top, middle, and end of the page

The visual review covered every distinct page family and the longest visual outliers. Repeated component-documentation shells were treated as one family with many content variants, not as hundreds of unrelated aesthetics.

## Coverage

| Reference | Public targets | Successful HTML | Other outcomes | Main route families |
| --- | ---: | ---: | --- | --- |
| Carbon | 319 | 319 | None in the indexed site | Components, developing, elements, patterns, community, data visualization, guidelines |
| Singapore Government Design System | 246 | 246 | None after preserving its extensionless URLs | Foundations, components, blocks, templates, AI guidance, stories |
| Coinbase Design System | 180 | 176 | Four blog routes blocked by Cloudflare | Components, hooks, getting started, guides, extras |
| Geist | 76 | 76 | None | Foundations, brands, components |
| Swiss Typefaces | 102 discovered targets | 75 HTML | 23 specimen or licence PDFs and four stale links | Fonts, in use, read, licensing, support, language coverage |

The scan attempted 923 public targets. It produced 2,700 top, middle, and end captures across the 900 HTML route attempts. The 23 Swiss PDF targets were inventoried as downloadable source material rather than misclassified as web pages.

### Integrity notes

- Singapore's extensionless routes redirect to a branded 404 when a trailing slash is appended, while still returning HTTP 200. URL identity and page meaning therefore had to be checked together.
- Coinbase's design-system documentation was available. Only its four blog routes presented a Cloudflare challenge.
- Carbon links to Storybook implementations and a preview host. Those are adjacent products, not pages within the indexed documentation site, and were kept outside the five-site page count.
- Swiss Typefaces exposed four stale internal destinations. They were recorded as broken links rather than counted as reviewed pages.

## Reference grammars

### Carbon

Carbon is strongest as a system of systems. It makes a clear distinction between elements, components, patterns, community assets, data visualization, and implementation guidance. Component documentation consistently separates usage, style, code, and accessibility. Large black title fields create a stable orientation point, while the left navigation exposes the system's full depth.

The useful lesson for EWM is structural rigor:

- separate primitives, components, economic patterns, and complete workflows
- document intent before implementation
- make accessibility and behavior first-class documentation surfaces
- use stable navigation and predictable page anatomy across a large corpus
- provide searchable libraries for dense symbol sets

EWM should not copy Carbon's dense documentation chrome or IBM visual identity. The workbench needs more room for simulation state and scientific evidence than a documentation site does.

### Singapore Government Design System

SGDS provides the clearest compositional ladder in the study: foundations, components, blocks, and full templates. It also documents purpose, anatomy, usage, accessibility, and updates. Its isolated block previews make larger compositions understandable without hiding the components that create them.

The useful lesson for EWM is compositional clarity:

- expose reusable analytical blocks between small components and whole workspaces
- distinguish a component specification from a workflow template
- show an isolated preview before asking users to reason about a whole screen
- include purpose, anatomy, usage, accessibility, and change history
- treat AI-facing context and machine-readable guidance as part of the system

EWM should not inherit SGDS's general-government appearance or rely on rounded white cards as a universal container.

### Coinbase Design System

Coinbase combines expressive visual covers with detailed, executable component references. Documentation surfaces package identity, platform availability, source, Storybook, Figma, machine-readable copy, related components, examples, props, and styles in one predictable record. Its chart pages and color-pairing tool are especially strong examples of documentation that is also an instrument.

The useful lesson for EWM is executable documentation:

- show live economic and visualization examples beside their specification
- expose source, version, compatibility, and related objects without dominating the primary task
- keep web and mobile or compact and expanded modes explicit
- make chart documentation interactive and data-bearing
- provide machine-readable descriptions for agents without weakening human presentation

EWM should not copy Coinbase's crypto palette, decorative component covers, or card-on-card density. EWM's dark surfaces belong to graph, globe, replay, and evidence contexts where darkness improves analytical contrast.

### Geist

Geist is the calmest operational reference. A compact persistent sidebar, restrained top bar, strict grid, low-noise surfaces, and consistent example panels make a large component catalogue feel predictable. Its materials page explicitly maps fills, borders, radii, and elevation to semantic use. Composite components such as Entity, Command Menu, Browser, File Tree, and JSON View are documented as product behavior, not only visual styling.

The useful lesson for EWM is disciplined quiet:

- use a stable operating shell with low visual noise
- reserve strong color for status, selection, and data
- define surface and elevation semantics instead of accumulating arbitrary cards
- document composite research objects, not only buttons and inputs
- keep examples, code disclosure, and best practices in a repeated grammar

EWM should not become a generic Vercel clone. Its typography, paper palette, economic semantics, and spatial visualizations must remain recognizably its own.

### Swiss Typefaces

Swiss Typefaces treats type as the primary visual material. Scale, spacing, image sequence, and abrupt field-color changes create rhythm with very little interface decoration. Font pages move between monumental specimens, readable essays, technical information, and product actions. In-use and editorial pages let imagery carry the narrative while the navigation remains thin and stable.

The useful lesson for EWM is editorial confidence:

- let a few high-value moments use truly large display type
- pair monumental type with original imagery rather than decorative interface chrome
- build rhythm through scale and fields, not through a pile of interchangeable cards
- allow editorial and technical typography to have different jobs
- keep global navigation quiet when the content itself is expressive

This mode belongs in EWM's repository hero, research covers, demo titles, and major narrative transitions. It does not belong inside dense controls, tables, evidence inspectors, or provenance records.

## EWM synthesis

EWM needs three coordinated visual modes.

### 1. Research instrument

The daily workbench should use Geist's operational calm, Carbon's information rigor, and EWM's existing warm-paper identity. It should prioritize research state, selection, comparison, evidence, and actions. Technical IDs stay inside a reusable details disclosure.

### 2. System documentation

The design and product documentation should use SGDS's foundations-to-components-to-blocks-to-templates ladder, combined with Carbon's usage, behavior, code, and accessibility depth. Economic objects, analytical tiles, evidence records, graph controls, and complete research workflows should all have explicit specifications.

### 3. Editorial identity

Repository imagery, demo titles, launch material, and key narrative surfaces should use Swiss Typefaces' confidence in scale and imagery, interpreted through EWM's original Renaissance economic artwork and its serif display voice. Coinbase's expressive covers are useful as proof that technical documentation can still have energy, but EWM should use fewer and more meaningful covers.

## Binding implementation rules

1. Economic World Model is always the product name. Research Workbench is the operating surface. Ontology is one capability within it.
2. The workbench shell remains quiet. Monumental serif typography is reserved for identity and narrative moments.
3. A surface needs a semantic role before it receives a border, fill, radius, or shadow.
4. Foundations, components, analytical blocks, workflow templates, and product screens are documented as separate levels.
5. Every reusable analytical block documents purpose, anatomy, states, data requirements, actions, accessibility, and provenance behavior.
6. Color is not the only carrier of run integrity, selection, warnings, or comparison status.
7. Dark spatial canvases are reserved for graph, globe, replay, and other views where contrast supports interpretation.
8. Exact hashes, schema keys, and long identifiers are secondary details. Human meaning and scientific consequence come first.
9. Repeated cards are not a layout strategy. Use grids, rules, fields, tables, lists, and spatial canvases according to the information relationship.
10. Brand imagery must be original or properly licensed. Reference systems inform principles, never copied compositions.

## Immediate design-system consequences

- Keep the existing Cormorant Garamond display and DM Sans technical pairing for the Figma visual suite.
- Add explicit material tokens for paper, raised paper, technical panel, dark spatial canvas, selected object, and evidence warning.
- Define component specifications for platform navigation, context commands, run status, analytical tile, evidence record, technical details, timeline, graph controls, globe controls, and empty or incompatible evidence states.
- Define reusable blocks for run overview, agent inspection, market outcome, behavior-to-learning closure, evidence audit, run comparison, lineage path, 2D graph, 3D graph, and globe investigation.
- Define workflow templates for opening a verified run, inspecting an object, replaying an episode, comparing runs, and tracing a claim to source evidence.
- Use the editorial image system for the repository hero, social card, workbench cover, research-cycle banner, and demo title card, not as a background behind dense operating controls.
