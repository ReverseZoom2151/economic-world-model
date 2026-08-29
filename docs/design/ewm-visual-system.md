# Economic World Model visual system

**Document version:** 1.0  
**Last reviewed:** 2026-08-29  
**Editable source:** [Economic World Model design file](https://www.figma.com/design/G7201TNCRNk5AMdRMexznH)

The visual system joins a research instrument with an editorial publication. Swiss typographic
discipline keeps dense evidence legible. Original Renaissance-inspired economic scenes give each
entry point a memorable world, while restrained ink, parchment, and evidence-lime surfaces preserve
the seriousness of the underlying claims.

## Editable Figma structure

| Page or frame | Figma node | Contents |
|---|---:|---|
| Foundations | `5:19` | Color, type, spacing, labels, evidence states, and identity disclosure |
| Editorial cards | `6:7`, `6:16`, `6:25`, `6:34` | Four reusable image-first article card variants |
| Renaissance series | `5:41` | Four distinct image and typography compositions |
| Workflow storyboard | `6:45` | Research question through bounded conclusion |
| Product screens | `7:2` | Six exact release captures from the verified local run |
| README hero | `6:113` | Repository lead image |
| Open Graph | `6:120` | Social preview composition |

The product-screen page is available directly at [node `7:2`](https://www.figma.com/design/G7201TNCRNk5AMdRMexznH?node-id=7-2).

## Design grammar

### Typography

- Instrument Serif carries product titles, large editorial statements, and economic questions.
- Inter carries controls, body copy, evidence, units, and compact metadata.
- Uppercase micro-labels name stage, type, and status. They do not replace a readable title.
- Tabular numerals align measured values. Long machine identifiers never occupy the primary reading
  path.

### Color and surface

| Token role | Use |
|---|---|
| Parchment | Primary canvas and readable neutral field |
| Ink | Main text and structural rules |
| Vermilion | Active navigation, editorial emphasis, and selected world |
| Evidence lime | Verified or passing evidence only |
| Muted stone | Secondary surfaces and unavailable states |
| Signal blue | Spatial and analytical orientation |

Evidence color is semantic. Decorative artwork never changes the evidence classification of a
claim.

### Editorial card anatomy

Each image-first card contains an indexed eyebrow, a strong image field, one short title, one line of
meaningful context, and an optional state marker. A selected card uses border, contrast, and label
together. Image, title, and metadata align to one grid. Cards may vary in scale but not in reading
order.

The supplied AI research article reference informed the horizontal rhythm, image-led hierarchy,
numbered article language, and serif-to-sans contrast. EWM adapts those patterns for economic worlds,
evidence, and investigations instead of copying a publication carousel.

### Identity disclosure

Readable labels lead every view, for example `Households`, `FX spot market`, and `Training run 01`.
Short identity suffixes appear only when they disambiguate otherwise identical records. Full hashes,
digests, object keys, source locators, and event identifiers remain available under `Technical
details` so an audit loses no precision.

## Source influences

The system synthesizes principles from five official design references:

- [Carbon type sets](https://carbondesignsystem.com/elements/typography/type-sets/) for a finite,
  role-based typographic scale and dense product legibility.
- [Singapore Government Design System cards](https://www.designsystem.tech.gov.sg/components/card)
  and [token architecture](https://www.designsystem.tech.gov.sg/foundations/token-architecture) for
  predictable card anatomy and semantic token layers.
- [Coinbase MediaCard](https://cds.coinbase.com/components/cards/MediaCard/) for image-led content
  with a clear interactive boundary.
- [Geist typography](https://vercel.com/geist/typography) for compact product text, balanced
  hierarchy, and readable technical surfaces.
- [Swiss Typefaces, Suisse](https://www.swisstypefaces.com/fonts/suisse/) for neutral Swiss structure
  paired with expressive editorial scale.

These are influence references, not source code or asset dependencies. The shipped workbench makes
no remote design-system requests.

## Artwork provenance

The first four editorial scenes were generated for EWM on 2026-08-29, and the panoramic project
cover was generated on 2026-08-30, using OpenAI's built-in image generation tool. They are original
Renaissance-inspired scenes, not reproductions of historical paintings. The
prompts prohibited text, logos, watermarks, recognizable people, named-artist imitation, and copying
an existing painting.

| Tracked asset | Generation ID | Prompt direction | Product role |
|---|---|---|---|
| `workbench/src/assets/ewm-ledger-florence-v1.webp` | `exec-5334be2d-9b64-4885-a2e5-af6691191752` | Florentine counting house, communal ledgers, balances, trade routes, warm palazzo light | Economy and accounting |
| `workbench/src/assets/ewm-exchange-venice-v1.webp` | `exec-5c94bf53-55d1-40a8-8a2b-b14b52dd7d65` | Venetian maritime exchange, currencies, contracts, maps, shipping flows, silvery lagoon dawn | Markets and networks |
| `workbench/src/assets/ewm-learning-workshop-v1.webp` | `exec-e9878349-f07f-42f2-85f6-eb85c1b4cb72` | Renaissance workshop, mechanical market model, instruments, feedback, collective revision | Learning and co-evolution |
| `workbench/src/assets/ewm-civic-market-v1.webp` | `exec-df5233af-53ae-4ce4-8a4b-9847234e1232` | Tuscan civic market, households, artisans, lenders, officials, institutions and exchange | World and institutions |
| `docs/assets/workbench/ewm-renaissance-cover-background-v1.png` | `exec-b9f6697e-23e5-46f2-b49f-2b0283e0697b` | Panoramic Italian economic world, spanning ledgers, markets, roads, workshops, fields, institutions, and maritime trade | Primary repository cover |

The editable image fills and overlaid type compositions are in the Figma Renaissance Series frame.
The primary project cover remains editable in the Figma README Hero frame, where a directional
legibility wash preserves the title while revealing the full economic panorama. The committed
[series export](../assets/workbench/figma-renaissance-series.png) and [README cover](../assets/workbench/ewm-project-cover-renaissance-v1.png)
provide durable repository previews.

## Release workflow

The release story is an investigation, not a section tour:

1. Ask whether the FX economy cleared without rejected orders or material accounting drift.
2. Scope the declared agents, market, mechanisms, and accounting boundary.
3. Verify ordered decisions, clearing, and settlement events.
4. Measure price, volume, rejected orders, and accounting residuals.
5. Test whether behavior generated data that trained and redeployed a model.
6. Separate inner execution evidence from an unavailable DDGE certificate.
7. Audit the claim, source, classification, limitations, and declared lineage.
8. Investigate the same ontology through bounded 2D and semantic 3D neighborhoods.
9. Inspect only explicitly sourced geographic anchors and their uncertainty.
10. Conclude that execution passed inside this synthetic runtime while adaptive model closure remains
    unproven.

The screenshots, capture manifest, demo configuration, GIF, and MP4 are derived from the same
verified run and recorded in `docs/assets/workbench`.
