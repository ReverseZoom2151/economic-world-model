# Ontology Repository Study

## Scope and conclusion

This study covers all eight repository snapshots under the ignored local `ontology/` directory:

1. Akashic
2. Ontology Playground
3. Third Eye
4. ObjectStack
5. Osiris
6. Radar
7. Right of Way
8. WorldMonitor

No single repository provides an ontology architecture that should be adopted wholesale for the
Economic World Model. The useful result is a composition of several narrower ideas:

- Ontology Playground provides an editable RDF and OWL projection.
- ObjectStack provides typed executable metadata, compilation, repositories, and immutable
  artifacts.
- WorldMonitor provides the strongest provenance vocabulary and fail-closed validation.
- Right of Way provides the strongest separation between untrusted decisions and a deterministic
  world verifier.
- Third Eye provides a small advisory and human-review workflow.
- Akashic provides a useful distinction among entities, claims, evidence, sources, events, and
  relationships, but its analytical implementations are not scientifically reliable.
- Osiris provides a normalized operational entity DTO and an opaque forecast-ledger prototype.
- Radar provides live telemetry normalization and bounded snapshot patterns, not an ontology.

For EWM, the economic engine should remain the source of behavioral and market truth. A new
ontology layer should describe economic objects, connect them to runtime identities, preserve
provenance and revisions, and make runs queryable. It should not duplicate the engine or place a
generic graph database in the execution path.

## Method and coverage

The review used four passes:

1. A recursive inventory of every file in every snapshot.
2. A repository-wide full-text scan of authored text, source, schemas, manifests, prompts, tests,
   and documentation.
3. Direct reading of primary documentation and the implementation paths for schemas, parsing,
   serialization, identity, relationships, provenance, events, repositories, ingestion, review,
   verification, persistence, and tests.
4. Exact-content hashing across repositories to identify copied files and shared lineage.

Dependency, cache, and build directories were excluded from semantic review. The main exclusions
were `node_modules`, `.next`, `dist`, `build`, `coverage`, `__pycache__`, and similar generated
trees. Binary media and large data assets were inventoried but not visually inspected. Generated
source committed to a repository was searched, but file and line counts should not be read as a
measure of independently authored design.

The snapshots are ZIP-style directories without `.git` metadata. Their exact upstream revisions,
branch histories, and commit dates cannot be established from the local copies. Osiris also
contains a Python 3.14 `__pycache__` for an `engine` package without the corresponding Python
source. Its symbol strings were inspected to establish the apparent interface, but its control flow
and scientific behavior cannot be audited from this snapshot.

Tests were counted but not executed. With the exception of a vendored dependency tree inside
Osiris, the snapshots do not include installed development environments.

## Inventory

Counts below exclude dependency, build, and cache directories. Test files use strict `test` or
`spec` filename patterns and do not represent test-case counts.

| Repository | Files | Test files | CI workflows | License | Primary role |
|---|---:|---:|---:|---|---|
| Akashic | 165 | 0 | 0 | AGPL-3.0-or-later | Geospatial intelligence workspace with a proposed claim graph |
| Ontology Playground | 384 | 24 | 8 | MIT | RDF and OWL ontology designer and catalogue |
| Third Eye | 209 | 7 | 0 | MIT | Operational intelligence entity store and review loop |
| ObjectStack | 7,194 | 2,884 | 28 | Apache-2.0 | Executable business metadata platform |
| Osiris | 240 | 24 | 1 | MIT | Intelligence dashboard, normalized entity stream, compiled forecast engine |
| Radar | 163 | 1 | 3 | MIT | Aircraft and maritime telemetry application |
| Right of Way | 78 | 4 | 0 | MIT | Negotiation protocol with a deterministic orbital verifier |
| WorldMonitor | 6,186 | 1,782 | 38 | AGPL-3.0 | Large multi-source intelligence and provenance system |

## What “ontology” means in these repositories

The repositories use the same word for different concepts. Treating them as equivalent would lead
to a confused EWM design.

| Repository | Actual abstraction |
|---|---|
| Ontology Playground | A constrained RDF and OWL schema projection with classes, properties, and typed relationships |
| ObjectStack | Typed executable application metadata compiled into runtime artifacts |
| Third Eye | A discriminated union of operational records held in an in-memory repository |
| Osiris | A normalized map-entity transfer object and adapters |
| WorldMonitor | A source registry, decision-signal provenance envelope, and a small hand-built entity index |
| Akashic | Separate domain records for entities, events, claims, evidence, sources, and graph edges |
| Right of Way | A protocol and verifier contract, with no semantic ontology |
| Radar | Telemetry DTOs and caches, with no semantic ontology |

Only Ontology Playground uses RDF or OWL. ObjectStack is the strongest executable schema system,
but it is not a semantic-web reasoner. The operational dashboards mostly use “ontology” to mean a
common data model.

## Repository findings

### Akashic

Akashic declares a broad intelligence model in `lib/geo-intelligence/types.ts`. It separates:

- sources and evidence,
- canonical and merged entities,
- directional relationships,
- events and claims,
- investigations and hypotheses,
- alerts, timeline items, and risk scores,
- tracking observations, documents, media, and market signals.

The separation between a claim and its evidence is valuable. Relationships can carry confidence
and validity intervals. Entity resolution uses deterministic identifiers where possible, then a
name-similarity threshold. Ingestion rewrites relationship endpoints after resolution and attempts
to persist the result transactionally.

The analytical labels are much stronger than the implementations justify:

- `causal_inference.ts` groups observed events by category and treats temporal succession as a
  conditional causal edge. It selects one representative event per category and removes reverse
  edges greedily. This does not establish a directed acyclic causal model.
- `do_calculus.ts` sets one category representative's probability to zero and propagates weighted
  sums along those edges. It implements neither structural causal interventions nor do-calculus.
- `claims_veracity.ts` combines lexical similarity, small word lists, source scores, and repeated
  Bayesian-looking updates. The independence assumptions and likelihood model are not identified.
- `generator.ts` emits a hard-coded “Cross-Domain Cluster” whenever enough events exist and builds
  risk components from presentation heuristics.

The repository has no test files or CI workflows. Prisma is declared, but no `schema.prisma` is
present. `claims_veracity.ts` imports `natural`, while the manifest includes only `@types/natural`,
not the runtime package. The database-backed graph path therefore cannot be reproduced from this
snapshot as checked in.

EWM should reuse the conceptual separation among claims, evidence, sources, events, and entities.
It should not reuse the causal, probability, or veracity algorithms. Akashic is AGPL and explicitly
states that it includes adapted WorldMonitor material, so any use in the MIT EWM repository must be
a clean-room reimplementation of ideas rather than copied code.

### Ontology Playground

Ontology Playground is the only explicit semantic-schema project in the set. Its internal model
contains ontology metadata, entity types, typed properties, identifiers, relationships,
cardinalities, relationship attributes, instances used by examples, and data bindings.

The local catalogue contains 71 RDF files with the following aggregate surface:

| RDF construct | Count |
|---|---:|
| OWL classes | 478 |
| OWL object properties | 518 |
| OWL datatype properties | 2,018 |
| Custom data bindings | 3 |

The parser reads a bounded RDF/XML profile. It recognizes OWL classes, datatype properties, object
properties, and project-specific annotations for icons, colors, identifiers, units, enumerations,
property types, cardinality, endpoints, and bindings. The serializer writes the same project
profile. Round-trip and parser tests exercise this projection.

The designer store has useful local validation:

- unique and Fabric-compatible names,
- at least one identifier where required,
- valid relationship endpoints,
- cross-entity property-type consistency,
- undo and redo history.

This is not a complete OWL implementation. Unsupported axioms and semantics are ignored, there is
no reasoner, and the project does not execute instance queries against a data platform. The natural
language query module is a deterministic demonstration over schema text, with special canned
responses for the Fourth Coffee example. It does not compile general natural language into graph
or data queries.

The project's own roadmap identifies missing composite keys, temporal properties, long and GUID
types, constraints, data quality, richer bindings, relationship bindings, semantic-model import,
instance graphs, query construction, versioning, and Fabric alignment. The authoring guide also
contains contradictory notes about whether self-referential relationships are supported.

The GitHub submission flow is real, but it stores an OAuth token in browser `localStorage`. That is
not a pattern to carry into a security-sensitive tool.

For EWM, this repository is most useful as a future interchange and editing reference. A restricted
RDF export could make economic schemas portable without forcing the runtime to become an OWL
engine.

### Third Eye

Third Eye's Smart System is a compact operational pipeline:

```text
source adapters -> raw records -> mappers -> validators -> entity repository
                                         -> advisory models -> human review -> audit
```

Every entity carries a kind, source, observation timestamp, confidence, classification,
provenance, audit trail, and tags. The provenance includes adapter identity, source category,
upstream identifier, ingestion time, ordered pipeline steps, and a simulation marker. Advisory
model outputs are explicitly marked advisory-only and enter a review queue. Human decisions are
stored as typed entities and also appended to an audit log. Tests cover the end-to-end advisory
path.

The “ontology” is an in-memory `Map<string, AnyEntity>`, not a graph. It has no edge or relation
model. Several details prevent it from being a trustworthy long-lived record system:

- The map key is only `id`, so independently sourced records can collide.
- Upsert builds history from the incoming entity rather than preserving the stored entity's full
  audit history.
- Snapshot replacement bypasses validation.
- Mapping allocates new local identifiers instead of preserving a stable source-scoped identity.
- Provenance mapping marks records as simulated even for adapters described as real-shaped feeds.
- Repository, review queue, and audit log are in memory and have no concurrency or transaction
  contract.

The useful EWM idea is the explicit boundary between model recommendation and human decision. The
repository itself is too weak for run identity, economic lineage, or scientific audit.

### ObjectStack

ObjectStack is the largest and most mature architecture in the set. It treats metadata as an
executable application contract, expressed through Zod schemas and compiled into runtime
artifacts. Its principal layers are:

- ObjectQL and data metadata,
- kernel lifecycle, dependency injection, and events,
- UI and view metadata,
- permissions and policies,
- actions, flows, state machines, and automation,
- agents, tools, MCP exposure, and audit concerns,
- metadata repositories, overlays, migrations, and artifacts.

The strongest patterns are concrete implementation contracts:

- `MetaRef` identifies organization, metadata type, name, and optional version.
- `MetadataItem` carries canonical content, parent identity, hashes, sequence, and schema version.
- `MetadataEvent` describes create, update, delete, rename, publish, and revert events with actor,
  source, and timestamp.
- The repository interface requires atomic writes, monotonic sequence numbers, optimistic locking,
  canonical hashing, ordered resumable watches, tombstones, and shutdown behavior.
- Layered repositories support read-through overlays with a designated writable layer.
- Environment artifacts separate compiled metadata from runtime configuration and secrets, and use
  a SHA-256 checksum.

The checkout contains 74 package manifests, 79 workspace manifests, 209 `*.zod.ts` schema files,
132 architecture-decision records, and 2,884 strictly named test files. The README's claim of 45
packages is stale relative to this snapshot. Some architecture documents explicitly retain
historical statements, so source and current package structure must win over summary prose.

ObjectStack calls this a business ontology, but it is not RDF, OWL, or a logical reasoner. Its
relationships are application metadata such as lookups and master-detail fields. Its scope is also
far larger than EWM needs.

EWM should adapt the small set of foundational patterns: typed specs, stable references, a compiler,
content-addressed artifacts, optimistic versioning, append-only metadata events, and explicit
runtime configuration. It should not import ObjectStack's full application platform, UI metadata,
agent framework, or plugin infrastructure.

### Osiris

Osiris contains three distinct systems.

The primary application is a Next.js intelligence dashboard with many upstream adapters. A
`PolybolosEntity` normalizes tracks, facilities, events, sensors, signals, and intelligence products
across air, sea, land, space, cyber, electronic warfare, and subsurface domains. Each record carries
position, threat, classification, source, timestamp, properties, and display hints. Adapters exist
for OSIRIS feeds and a simulated Lattice-compatible stream.

The external ingestion and SSE implementation is only a prototype:

- Ingested entities are stored in a process-global in-memory map.
- Payloads use `any` and minimum-field checks rather than the declared TypeScript contract.
- Truthiness validation rejects legitimate latitude or longitude values of zero.
- A confidence of zero is replaced with the default because `||` is used.
- Display metadata is mixed into the canonical domain entity.
- Random identifiers are used when upstream identity is absent.
- The Lattice adapter puts its token in an EventSource query string.
- Threat-level comparisons use string enums as if they had an ordinal ordering.

The `/api/entity/expand` route is a proxy to a separate `intel` service. It does not implement an
ontology locally.

The third system is a compiled Python 3.14 package named PYTHIA whose source files are absent. Its
symbol strings indicate the following intended pipeline:

```text
Osiris feeds -> normalized WorldEvent -> WorldBrief -> local LLM forecasts
             -> optional persona council -> append-only JSONL ledger -> later resolution
```

The apparent model includes horizon, probability, baseline probability, reasoning, location,
persona votes, split or disagreement state, and a brief reference. The ledger appears to retain
forecasts, later resolutions, Brier scores, and persona scorecards. The local `runs/ledger.jsonl`
contains unresolved example forecasts.

This is an interesting research-product direction, but it is not auditable here. There are no
Python sources or engine tests, and the Python 3.14 bytecode cannot be treated as an inspectable
scientific implementation. EWM can independently implement a forecast ledger, baselines,
resolution rules, and calibration scores. It should not use or distribute the opaque bytecode.

### Radar

Radar is a React and Express telemetry application. Its useful backend patterns are source adapters,
typed aircraft records, short-lived snapshots, a bounded maritime snapshot, separate detail and
history retrieval, stale-object purging, and in-flight stream state.

It has no ontology, relation model, provenance envelope, revision model, or durable event ledger.
Only one strict test file is present.

Two implementation details are warnings for EWM:

- The generic cache returns `null` after expiry, so the ADSB.lol error path's attempt to retrieve a
  stale cached value cannot succeed.
- The flight endpoint silently substitutes 400 synthetic records when the upstream fails. An
  `X-Cache: FALLBACK` header is the only top-level distinction. Scientific systems should keep
  simulated and observed records impossible to confuse in the payload and artifact identity.

Radar may inform streaming and payload-size work later. It contributes no ontology architecture.

### Right of Way

Right of Way is not an ontology project. It is a domain-independent negotiation protocol with an
orbital reference implementation. Its central rule is valuable for EWM: agents negotiate intent,
while a deterministic referee owns physical truth.

The roles and flow are explicit:

```text
screen -> negotiate -> verify -> commit -> re-screen -> repair or finish
```

Pydantic contracts define scenarios, objects, states, conflicts, maneuver proposals, messages,
frames, and timeline events. The physics core is deterministic and does not mutate its inputs. It
propagates orbital states, screens pairwise conjunctions, rejects over-budget burns, and returns a
new scenario after a maneuver. The orchestrator preserves messages, applies a hard iteration cap,
uses a deterministic fallback, audits false capability claims against referee state, and emits a
replayable timeline.

The protocol document is slightly stronger than the orchestrator. It says an accepted action is
verified for both feasibility and effectiveness before commitment. The orchestrator itself always
checks fuel feasibility, but it relies on the negotiator or fallback to have checked effectiveness.
An injected negotiator can return an ineffective but affordable action; the loop will commit it and
discover the problem only on re-screen. That is repairable, but it is not pre-commit effectiveness
verification.

Pairwise repair is appropriate for conjunctions but not a general substitute for simultaneous
market clearing or multi-agent equilibrium. EWM should adapt the trust boundary and invariant
verification, not the orbital action model or pairwise allocation assumption.

### WorldMonitor

WorldMonitor is not an ontology system, but it contains the strongest evidence and provenance work
in the set.

Its source-attribution manifest contains 878 entries:

| Manifest status | Count |
|---|---:|
| Reviewed | 88 |
| Terms review required | 665 |
| Excluded transport or presentation source | 125 |

The decision-signal provenance contract defines 17 mandatory dimensions:

- publisher,
- source URL and original reference,
- original language and translation state,
- observation, effective, publication, and retrieval times,
- revision and supersession,
- extraction and classification confidence,
- corroboration,
- transport and content freshness,
- derivation.

Every claim must be explicitly `known`, `unknown`, or `not_applicable`. Family declarations decide
which status is legal for every dimension. Unknown and not-applicable claims require a reason and
cannot carry a hidden value. Runtime validation checks exact keys, source-registry references,
credential-free HTTPS URLs, time roles, revision and supersession semantics, confidence ranges,
corroboration identities, freshness combinations, and derivation inputs. The same validated wire
shape is used for cache, API, MCP, and UI adapters. Positive and adversarial fixtures are included
in the required test path.

This design gets several important distinctions right:

- publisher authority is not model confidence,
- extraction confidence is not classification confidence,
- official publication is not independent corroboration,
- transport freshness is not content freshness,
- publication time is not observation or retrieval time,
- a revision is not the same as supersession,
- a derived output must name its inputs and method version.

WorldMonitor also has a small registry of 66 entities: 38 companies, 11 countries, 6 commodities,
5 sectors, 3 market indices, and 3 cryptocurrencies. Entity extraction uses precompiled alias
regular expressions and keyword matching. The `related` graph is a hand-authored list. This is an
efficient product index, not a general knowledge graph. Broad keywords can associate a headline
with an entity at only 0.7 confidence, and relation semantics are not typed or evidenced.

Other useful engineering ideas include source-owned cache keys, content-age contracts, explicit
last-good data, source tags, closed-world validation, non-vacuous guard tests, generated RPC
contracts, and freshness health checks.

WorldMonitor is AGPL. EWM should write its own smaller provenance vocabulary from first principles,
using the conceptual distinctions above and the needs of economic research.

## Lineage and independence

Exact-content hashing found 17 cross-repository groups after common license files and lockfiles were
excluded.

- Fifteen groups join Third Eye and Osiris. They include shared CCTV routes, OSINT utilities,
  security code, and the same submarine-cable dataset. These repositories share direct lineage and
  should not count as independent validation of a design.
- Two small groups join Ontology Playground and Radar, consisting of starter CSS and a TypeScript
  configuration. They are ordinary scaffold material, not architectural lineage.
- Akashic's license explicitly declares adapted WorldMonitor material. Exact hashes are no longer
  common in the scanned text, but the declared derivation is decisive.

The eight folders therefore represent fewer than eight independent architectural experiments.

## Capability comparison

| Capability | Akashic | Ontology Playground | Third Eye | ObjectStack | Osiris | Radar | Right of Way | WorldMonitor |
|---|---|---|---|---|---|---|---|---|
| Typed domain schema | Strong on paper | Strong | Moderate | Strong | Moderate | Narrow | Strong protocol types | Strong contracts |
| Typed relations | Yes | Yes | No | Application relations | No | No | Conflict pairs only | Hand-built related IDs |
| RDF or OWL | No | Yes, constrained | No | No | No | No | No | No |
| Source provenance | Partial | Minimal | Moderate | Metadata authorship | Basic source field | Minimal | Referee transcript | Strong |
| Revision and supersession | Weak | Missing | Weak | Strong metadata events | Missing | Missing | Timeline only | Strong |
| Content-addressed artifacts | No | No | No | Yes | No | No | Replay timeline, not hashed | Partial elsewhere |
| Deterministic verifier | No | Schema validation | Basic validation | Schema and repository contracts | No | No | Strong | Strong contract validation |
| Human review | Investigation concepts | Designer workflow | Yes | Approval and action framework | No | No | Escalation fallback | Product workflows |
| Durable scientific audit | No | No | No | Metadata audit foundation | Opaque JSONL forecast ledger | No | Replayable episode | Strong provenance, broad product scope |
| Evidence from tests | None | Good for its scope | Small but relevant | Extensive | Dashboard tests, not compiled engine | Very thin | Focused protocol tests | Extensive |

## Architecture derived for EWM

The ontology feature should be a bounded package layer around the existing model, compiler, event
chain, and artifact system.

```text
Economic ontology spec
        |
        v
Schema validator and compiler -----> content-addressed ontology artifact
        |                                      |
        v                                      v
Runtime identity registry <----> existing EWM world compiler and scenarios
        |
        +----> provenance claims and revisions
        |
        +----> canonical economic event ledger
        |
        +----> query and inspection API
        |
        +----> optional RDF export and import boundary
```

### 1. Economic vocabulary

The first version should define a small closed vocabulary tied to the papers and current package:

- `EconomicWorld`, `Scenario`, `Regime`, and `Intervention`
- `Agent`, `Population`, `Institution`, `Market`, and `Contract`
- `State`, `InformationSet`, `Belief`, `Policy`, `Action`, and `Outcome`
- `Asset`, `Endowment`, `Order`, `Trade`, `Price`, and `Allocation`
- `Constraint`, `MarketClearingCondition`, `Equilibrium`, and `Residual`
- `Observation`, `Dataset`, `Learner`, `Model`, and `ParameterVector`
- `Run`, `Event`, `Artifact`, `Claim`, `Evidence`, `Source`, and `Revision`

The relation vocabulary should be typed and directional. Initial examples are `participates_in`,
`owns`, `observes`, `believes`, `chooses`, `constrained_by`, `clears_in`, `generates`, `trained_on`,
`deploys`, `transitions_to`, `intervenes_on`, `derived_from`, `supersedes`, `satisfies`, and
`violates`.

### 2. Stable identity

Identity should be namespaced and source-scoped, never an unqualified string:

```text
namespace / kind / local-id / optional-version
```

An observation's upstream identity, the canonical economic object identity, and a run-local
instance identity must remain distinct. Resolution should produce an explicit assertion with
method, score, evidence, and reviewer state. It should never silently merge records because a name
similarity crossed a threshold.

### 3. Time and revision

At minimum, records need event time and record time. Economic datasets also need observation,
effective, publication, and retrieval roles where applicable. Corrections and supersession should
append new records while leaving historical vintages addressable.

### 4. Provenance claims

EWM should use an explicit status for every required provenance dimension. Missing data must not
be interpreted as current, official, verified, independent, or zero. Confidence should be split by
meaning, for example extraction, identity resolution, model prediction, and numerical solver
confidence. Derivations should name input artifact hashes and method versions.

### 5. Compilation rather than duplicated execution

The ontology spec should compile to immutable runtime metadata that references existing EWM classes,
scenario definitions, constraints, and codecs. It should not reimplement agent behavior, market
clearing, transitions, learning, or DDGE search. A compiler check should fail if an ontology object
claims a runtime binding that does not exist or has the wrong type.

### 6. Verification and audit

Model outputs and agent statements should be treated as proposals. Existing EWM constraints,
accounting identities, market-clearing checks, event-chain checksums, and deterministic replay act
as the referee. Every accepted proposal should pass both feasibility and consequence checks before
it changes an authoritative artifact. Failures and fallbacks belong in the same append-only record.

### 7. Interchange

RDF should be optional. The native Python schema and canonical JSON artifact should remain the
execution contract. A later RDF adapter can export classes, fields, relations, identifiers, and
provenance for external tools. Unsupported RDF semantics must fail or be reported as loss, not
silently disappear.

## Recommended feature sequence

No dashboard or web application is required for these steps.

1. Write an ontology architecture decision record that fixes scope, vocabulary ownership, identity,
   temporal semantics, provenance, and the native serialization contract.
2. Add typed Python specs for economic types, fields, relations, bindings, and provenance claims.
3. Add a validator and compiler that emits a canonical, hashed ontology artifact.
4. Bind the initial vocabulary to the existing FX, forecasting, credit, production, equilibrium,
   and DDGE objects without changing their economic behavior.
5. Project canonical runtime events into a queryable economic event ledger while preserving the
   current event-chain identity.
6. Add explicit identity-resolution assertions and revision or supersession events.
7. Expose a read-only Python query API for types, relations, lineage, runs, and evidence.
8. Add a constrained RDF export only after the native contract and round-trip loss rules are stable.

## Reuse and licensing decisions

| Source | Decision |
|---|---|
| Ontology Playground, MIT | Concepts and, if needed, small attributed code only after a separate dependency and design review |
| Third Eye, MIT | Reimplement the advisory and review state machine in EWM's existing event architecture |
| ObjectStack, Apache-2.0 | Adapt spec, compiler, artifact, repository, and metadata-event concepts at a much smaller scale |
| Osiris, MIT | Reimplement forecast-ledger concepts; do not use bytecode or unvalidated entity-stream code |
| Radar, MIT | Consider bounded snapshot techniques only when EWM adds live data |
| Right of Way, MIT | Adapt the deterministic referee and verified-proposal pattern |
| Akashic, AGPL | Clean-room concepts only; do not copy code |
| WorldMonitor, AGPL | Clean-room provenance design only; do not copy code or generated contracts |

License compatibility is not the only filter. Even permissively licensed code should not be copied
when its abstraction, validation level, or dependencies do not fit the scientific package.

## Evidence paths

The highest-value implementation evidence in the ignored local snapshots is listed here so the
next design session can return to it quickly.

### Akashic

- `ontology/Akashic-main/Akashic-main/lib/geo-intelligence/types.ts`
- `ontology/Akashic-main/Akashic-main/lib/geo-intelligence/resolution.ts`
- `ontology/Akashic-main/Akashic-main/lib/geo-intelligence/ingest.ts`
- `ontology/Akashic-main/Akashic-main/lib/geo-intelligence/claims_veracity.ts`
- `ontology/Akashic-main/Akashic-main/lib/geo-intelligence/causal_inference.ts`
- `ontology/Akashic-main/Akashic-main/lib/geo-intelligence/do_calculus.ts`

### Ontology Playground

- `ontology/Ontology-Playground-main/Ontology-Playground-main/src/data/ontology.ts`
- `ontology/Ontology-Playground-main/Ontology-Playground-main/src/lib/rdf/parser.ts`
- `ontology/Ontology-Playground-main/Ontology-Playground-main/src/lib/rdf/serializer.ts`
- `ontology/Ontology-Playground-main/Ontology-Playground-main/src/store/designerStore.ts`
- `ontology/Ontology-Playground-main/Ontology-Playground-main/docs/authoring-guide.md`
- `ontology/Ontology-Playground-main/Ontology-Playground-main/docs/TODO-full-ontology-format.md`

### Third Eye

- `ontology/Third-Eye-main/Third-Eye-main/docs/SMART_SYSTEM.md`
- `ontology/Third-Eye-main/Third-Eye-main/src/smart_system/ontology/entities.ts`
- `ontology/Third-Eye-main/Third-Eye-main/src/smart_system/ontology/repository.ts`
- `ontology/Third-Eye-main/Third-Eye-main/src/smart_system/ingestion/ingestion_service.ts`
- `ontology/Third-Eye-main/Third-Eye-main/src/smart_system/review/review_service.ts`
- `ontology/Third-Eye-main/Third-Eye-main/src/smart_system/__tests__/integration.test.ts`

### ObjectStack

- `ontology/objectstack-main/objectstack-main/ARCHITECTURE.md`
- `ontology/objectstack-main/objectstack-main/content/docs/concepts/north-star.mdx`
- `ontology/objectstack-main/objectstack-main/packages/metadata-core/src/types.ts`
- `ontology/objectstack-main/objectstack-main/packages/metadata-core/src/repository.ts`
- `ontology/objectstack-main/objectstack-main/packages/metadata-core/src/canonicalize.ts`
- `ontology/objectstack-main/objectstack-main/packages/metadata-core/src/layered-repository.ts`
- `ontology/objectstack-main/objectstack-main/packages/spec/src/system/environment-artifact.zod.ts`

### Osiris

- `ontology/osiris-master/osiris-master/src/lib/sdk/types.ts`
- `ontology/osiris-master/osiris-master/src/lib/sdk/LatticeAdapter.ts`
- `ontology/osiris-master/osiris-master/src/lib/sdk/PolybolosClient.ts`
- `ontology/osiris-master/osiris-master/src/app/api/sdk/ingest/route.ts`
- `ontology/osiris-master/osiris-master/src/app/api/sdk/stream/route.ts`
- `ontology/osiris-master/osiris-master/runs/ledger.jsonl`

### Radar

- `ontology/radar-main/radar-main/server/src/types/flights.ts`
- `ontology/radar-main/radar-main/server/src/core/cache.ts`
- `ontology/radar-main/radar-main/server/src/routes/flights.ts`
- `ontology/radar-main/radar-main/server/src/routes/maritime.ts`
- `ontology/radar-main/radar-main/server/src/core/source/aisstream.ts`

### Right of Way

- `ontology/right-of-way-main/right-of-way-main/PROTOCOL.md`
- `ontology/right-of-way-main/right-of-way-main/row/contracts.py`
- `ontology/right-of-way-main/right-of-way-main/row/orchestrator/loop.py`
- `ontology/right-of-way-main/right-of-way-main/row/physics/core.py`
- `ontology/right-of-way-main/right-of-way-main/row/physics/screening.py`
- `ontology/right-of-way-main/right-of-way-main/tests/test_orchestrator.py`

### WorldMonitor

- `ontology/worldmonitor-main/worldmonitor-main/ARCHITECTURE.md`
- `ontology/worldmonitor-main/worldmonitor-main/CONCEPTS.md`
- `ontology/worldmonitor-main/worldmonitor-main/docs/decision-signal-provenance.mdx`
- `ontology/worldmonitor-main/worldmonitor-main/shared/decision-signal-provenance-contract.ts`
- `ontology/worldmonitor-main/worldmonitor-main/shared/decision-signal-provenance.ts`
- `ontology/worldmonitor-main/worldmonitor-main/shared/source-provenance.ts`
- `ontology/worldmonitor-main/worldmonitor-main/shared/source-attribution-manifest.json`
- `ontology/worldmonitor-main/worldmonitor-main/shared/entity-extraction-core.js`
- `ontology/worldmonitor-main/worldmonitor-main/shared/entity-registry.js`
- `ontology/worldmonitor-main/worldmonitor-main/tests/decision-signal-provenance.test.mts`
