# EWM Ontology Research Workbench Architecture

Status: approved design for implementation  
Date: 2026-08-28  
Decision owners: project maintainer  
Target: first local-first ontology workbench release

## 1. Decision

Economic World Model will add a local-first ontology research workbench that projects verified EWM
run bundles into a typed, immutable, evidence-linked investigation model. A local read-only service
and a portable static snapshot viewer will expose the same research workflows. The existing economic
engine, equilibrium machinery, scenario implementations, and sealed `ewm.run.v2` contract remain
authoritative and do not depend on the ontology or workbench packages.

The workbench is for a solo economic AI researcher. Its purpose is to make an executable economy
inspectable across five connected questions:

1. What economic world was declared?
2. What happened when it ran?
3. How did behavior generate data and how did learning change the deployed model?
4. What equilibrium or DDGE status is supported?
5. Which artifacts, sources, tests, and limitations authorize each research claim?

The interface combines precise two-dimensional analytical views with two synchronized WebGL views:

- a deterministic three-dimensional ontology scene;
- an evidence-aware economic globe for explicitly geocoded worlds.

Neither three-dimensional view replaces tables, charts, provenance, or mathematical diagnostics.

## 2. Source and claim boundary

The design interprets and exposes semantics from both project sources:

- Lin William Cong, [*Economic World Models and Data-Driven Generative Equilibria*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6559940)
- Han et al., [*From Economic Agents to Agentic Economies: A Systems Blueprint for Economic World Models*](https://arxiv.org/abs/2608.06020v1)

Cong supplies the formal economic-world object, inner equilibrium conditions, the behavior to data
to learning closure, DDGE correspondences, fixed-point diagnostics, and the distinction between
numerical residuals and theorem-backed conclusions. Han et al. supply executable agent-world
interfaces, runtime protocols, controlled co-evolution, capability levels, and the requirement that
higher-level claims depend on observed evidence rather than the presence of named components.

The workbench inherits the repository's current claim boundaries. In particular:

- selected definitions, protocols, and targets are implemented, not both papers in full;
- Cong Laboratory I remains a disclosed qualitative reconstruction;
- exact replication is limited to the registered targets documented in `docs/replication.md`;
- Han L1 and L2 are synthetic systems conformance results;
- Han L3 through L6 remain evidence-readiness observations with no higher-level award;
- no view may turn diagnostic, fixture-backed, or readiness evidence into empirical validation.

### 2.1 Reference-repository synthesis

The local study in [`docs/ontology-repository-study.md`](../ontology-repository-study.md) informs the
workbench without making any reference implementation authoritative.

| Reference | Pattern used | Boundary retained |
|---|---|---|
| ObjectStack | Typed metadata, canonicalization, layered repositories | No business-platform or database runtime |
| WorldMonitor | Evidence manifests, source attribution, bounded visual payloads | No live news, remote telemetry, or inferred claims |
| Right of Way | Deterministic protocol verification and fail-closed orchestration | No negotiation protocol in the economic kernel |
| Third Eye | Separate claims, evidence, sources, and review state | No automatic entity or causal assertions |
| Ontology Playground | Explicit relation vocabulary and possible RDF interchange | No RDF store or reasoner in V1 |
| Osiris | Investigation layout, spatial selection, and event-ledger ideas | No remote SDK dependency or opaque ingestion |
| Radar | Bounded snapshots and source adapters | No live telemetry path in V1 |
| Akashic | Entity, event, claim, evidence, and geospatial record separation | No copied geointelligence or causal-inference claims |

The repositories are architectural references only. Their code is not copied into EWM, and their
licenses, incomplete components, generated assets, and unaudited runtime claims remain outside the
project's evidence boundary.

## 3. Product contract

### 3.1 Primary user

A solo economic AI researcher who runs experiments locally and needs to inspect worlds, mechanisms,
events, learning feedback, equilibria, comparisons, and claim provenance without operating a data
platform.

### 3.2 Core jobs

The workbench must let the researcher:

- verify and open one or more sealed run bundles;
- reconstruct the declared economic world without changing it;
- inspect agents, institutions, markets, mechanisms, constraints, state, and action spaces;
- follow a runtime episode from action through transition and market outcome;
- trace generated observations into datasets, training, parameter updates, and redeployment;
- distinguish rollout, inner equilibrium, fixed-point candidate, DDGE candidate, and certification;
- compare compatible runs without hiding differences in units, estimands, seeds, or protocols;
- audit every visible claim back to evidence and source locations;
- export a bounded, self-contained, verifiable investigation snapshot.

### 3.3 V1 boundary

V1 is local, read-only, single-user, and artifact-first. It includes the canonical ontology, all
registered scenario adapters, read-only queries, the investigation interface, the 3D ontology
scene, the economic globe capability, run comparison, and portable snapshots.

V1 does not include:

- cloud hosting, accounts, or multi-user collaboration;
- ontology authoring or mutation of run bundles;
- live remote telemetry or automatic external ingestion;
- a graph database;
- autonomous decisions or automatically generated economic claims;
- an agent framework or Mesa as a required runtime;
- arbitrary force-directed or decorative 3D presentation.

## 4. Ontology model

### 4.1 Six layers

The canonical ontology separates six layers that must not be conflated.

| Layer | Question | Representative objects |
|---|---|---|
| Schema | What vocabulary and constraints are valid? | Object type, relation type, property specification, profile, invariant |
| Economic declaration | What economy was specified? | World, agent, institution, market, asset, action, belief, objective, constraint, mechanism, kernel, learner, intervention |
| Runtime occurrence | What happened in a particular execution? | Run, episode, step, state observation, action occurrence, mechanism invocation, transaction, outcome, generated datum |
| Learning and equilibrium | How did models update and what closure was assessed? | Dataset, training run, model version, parameter version, equilibrium witness, DDGE candidate, residual, certificate, basin, stability diagnostic |
| Research and evidence | What was measured or claimed? | Experiment, protocol, comparison, estimand, measurement, claim, evidence artifact, limitation, readiness assessment |
| Provenance | Where did each assertion come from? | Projection, coverage entry, source locator, derivation, software identity, digest, paper anchor |

### 4.2 Core records

The Python model uses frozen dataclasses and immutable collections. The canonical records are:

```python
@dataclass(frozen=True)
class OntologyRef:
    id: str
    kind: str

@dataclass(frozen=True)
class SourceLocator:
    source_kind: str
    source_id: str
    artifact_path: str | None
    record_selector: str | None
    code_symbol: str | None
    paper_anchor: str | None
    payload_digest: str | None

@dataclass(frozen=True)
class OntologyObject:
    ref: OntologyRef
    layer: str
    properties: Mapping[str, CanonicalValue]
    sources: tuple[SourceLocator, ...]

@dataclass(frozen=True)
class RelationAssertion:
    ref: OntologyRef
    relation_type: str
    source: OntologyRef
    target: OntologyRef
    properties: Mapping[str, CanonicalValue]
    sources: tuple[SourceLocator, ...]

@dataclass(frozen=True)
class Measurement:
    ref: OntologyRef
    subject: OntologyRef
    name: str
    value: CanonicalValue | None
    unit: str
    status: str
    sample: Mapping[str, CanonicalValue]
    uncertainty: Mapping[str, CanonicalValue]
    sources: tuple[SourceLocator, ...]

@dataclass(frozen=True)
class OntologyProjection:
    schema: str
    source_run: OntologyRef
    objects: tuple[OntologyObject, ...]
    relations: tuple[RelationAssertion, ...]
    measurements: tuple[Measurement, ...]
    coverage: tuple[CoverageEntry, ...]
    projection_digest: str
```

`CanonicalValue` is the existing finite, JSON-compatible canonical value domain. The implementation
must reuse `ewm.core.serialization.canonical_json` and `content_digest`; it must not introduce a
second canonicalizer or digest algorithm.

### 4.3 Identity

Identity is based on kind, stable source identity, and canonical semantic keys, not display labels.
A readable prefix may be included, but the digest is authoritative:

```text
ewm:{namespace}:{kind}:{digest}
```

Runtime identities include the verified run hash and the source record sequence or stable selector.
Declaration identities include the compatible scenario adapter and declared natural key. Derived
identities include the ordered source identities, transformation type, and version.

The compiler rejects collisions, unresolved references, unstable iteration order, and duplicate
natural keys.

### 4.4 Source locators

Every assertion has one or more source locators. Locators may identify:

- a path and selector within a verified run bundle;
- an event sequence and event hash;
- a code module and symbol in a compatible installed EWM version;
- a protocol, conformance entry, or evidence artifact;
- a paper section, definition, proposition, equation, table, or laboratory.

Exported paths are normalized and relative. Absolute workstation paths are redacted. A locator is
evidence of origin, not proof that the referenced claim is true.

### 4.5 Relation vocabulary

The canonical relation vocabulary is small and typed. Profiles may specialize it without changing
its direction or meaning.

| Family | Relations |
|---|---|
| Declaration | `DECLARES`, `CONTAINS`, `PARTICIPATES_IN`, `SUBJECT_TO`, `OBSERVES`, `OPTIMIZES`, `GOVERNED_BY` |
| Runtime | `INSTANTIATES`, `PRECEDES`, `CHOOSES`, `ACTS_ON`, `INVOKES`, `TRANSITIONS_TO`, `CLEARS`, `REALIZES` |
| Data and learning | `GENERATES`, `INCLUDED_IN`, `TRAINS`, `PRODUCES`, `DEPLOYS`, `UPDATES` |
| Equilibrium | `HAS_CANDIDATE`, `WITNESSED_BY`, `SATISFIES`, `HAS_RESIDUAL`, `HAS_BASIN`, `CERTIFIES` |
| Research | `MEASURES`, `COMPARES`, `SUPPORTS`, `LIMITS`, `ASSESSES` |
| Provenance | `DERIVED_FROM`, `LOCATED_AT`, `VERIFIED_BY`, `GEO_ANCHORED_AT` |

Relation direction is part of the schema. Inverse display is a query concern, not a second stored
assertion.

### 4.6 Profiles

The canonical core is extended by bounded adapters:

- `scalar`: generic fixed-point and DDGE objects;
- `forecasting`: forecasting rules, generated samples, estimators, learned coefficients, roots,
  derivatives, phase patterns, and damping declarations;
- `fx`: trader agents, currencies, orders, executions, market clearing, rejections, prices, volumes,
  adaptive state, and protocol observations;
- `credit`: borrowers, lender or scoring policy, allocation regimes, repayment outcomes, training
  observations, locked protocol results, and disclosed reconstruction limitations;
- `production`: households, firms, capital, labor, goods, feasibility, optimization, market clearing,
  and package-authored primitive disclosures.

Unknown scenario versions are never guessed. The projector emits supported runtime and evidence
records and marks unavailable declaration semantics in the coverage ledger.

When a declaration comes from an installed scenario adapter rather than the sealed run payload, the
projection labels it `adapter_derived`, records the adapter and source digests, and never presents it
as run-authored evidence. A matching package version alone is not treated as a source-integrity
proof.

### 4.7 Geospatial extension

`GeoAnchor` is an optional, explicit ontology object. It records:

- coordinate reference system;
- latitude and longitude, geometry, or jurisdiction identifier;
- source locator and digest;
- validity interval when geographic identity changes;
- whether the anchor is observed, declared, or externally supplied.

Only `GEO_ANCHORED_AT` permits an object to appear on the globe. Synthetic currencies, abstract
markets, or inferred jurisdictions are not silently mapped to real places.

Current EWM scenarios contain no geographic identifiers. V1 therefore accepts an optional,
canonical `ewm.geo-overlay.v1` sidecar at launch. Each entry names an existing ontology identity,
supplies a `GeoAnchor`, and records a source and evidence status. The projector classifies these
anchors as `researcher_declared`, hashes the overlay into projection identity, and keeps it outside
the sealed run. Unknown identities, missing sources, duplicate anchors, and invalid coordinates fail
validation. This file contract makes the globe usable without adding an authoring interface or
claiming that the run supplied geography.

### 4.8 Invariants

The schema compiler enforces these fourteen cross-layer invariants:

1. Every stored object, relation, and measurement has a unique stable identity.
2. Every reference resolves within the projection or an explicitly declared external source.
3. Every relation uses an allowed source kind, target kind, direction, and cardinality.
4. Every assertion has a valid source locator and every runtime assertion traces to a verified run.
5. Every object belongs to exactly one ontology layer.
6. Economic declarations and runtime occurrences remain different objects linked by `INSTANTIATES`.
7. Sealed run content is immutable; projections and snapshots are separate derived artifacts.
8. Rollouts, inner equilibria, fixed-point candidates, DDGE candidates, and certified results remain
   distinct kinds.
9. Set-valued correspondences preserve all observed candidates and selector metadata.
10. The behavior to data to learning closure uses typed stages and cannot skip an unavailable stage
    without an explicit coverage entry.
11. Residuals retain vector or scalar values, norm, tolerance, solver, stopping rule, and status.
12. A residual implies a distance or welfare bound only when the required certificate is linked.
13. Declared interventions, realized interventions, and observed outcomes remain distinct.
14. Every claim links to authorizing evidence and retains its original evidence classification.

## 5. Paper-semantic views

### 5.1 Inner solution correspondence

For deployment parameter `theta`, the workbench represents the inner solution as a correspondence,
not an assumed function:

$$
E_i(\theta)
=
\left\{
(\pi,\mu)
\;\middle|\;
(\pi,\mu)\text{ satisfy the declared behavioral, belief, feasibility, and market conditions under }(\theta,i)
\right\}.
$$

The interface shows which conditions were declared, evaluated, satisfied, violated, unavailable, or
not measured. A witnessed numerical candidate does not become a general existence result.

### 5.2 Data and learner closure

The behavior to data to learning loop is stored as typed objects and relations:

$$
F_i(\theta)
=
L_i\!\left(D_i\!\left(E_i(\theta),\theta\right)\right).
$$

The runtime view follows the realized path. The learning view reconstructs which observations
entered a dataset, which training procedure consumed it, and which parameter version was deployed.
Unavailable links remain visibly unavailable.

### 5.3 DDGE status

A displayed DDGE assessment includes:

- correspondence or operator definition;
- initialization and selector metadata;
- all distinct observed candidates;
- solver and damping settings;
- scalar or vector residual;
- norm, tolerance, and stopping rule;
- basin or multistart evidence when available;
- stability diagnostics;
- theorem certificate and assumptions when present;
- explicit status: observed, candidate, numerically validated, or certified.

The interface never reduces a set-valued result to one unexplained point.

### 5.4 Han capability status

Capability objects link declared interfaces to observed protocol evidence. A named cognition,
evolution, institution, or alignment component is not sufficient to award a level. The view shows
requirements, observations, missing observations, blockers, evidence kind, and award status.

## 6. Investigation workflows

### 6.1 Verify and open

1. Select a run directory through the CLI launcher.
2. Verify the sealed bundle before projection.
3. Show artifact schema, run hash, integrity level, supported profile, projection coverage, and any
   non-fatal semantic gaps.
4. Refuse to open failed integrity or schema checks.

### 6.2 Understand the world

Start with the declared world graph. Select an agent, market, mechanism, constraint, kernel, learner,
or intervention and inspect its properties, relations, source code symbol, paper anchor, and runtime
instances.

### 6.3 Trace an episode

Choose an event or time window and follow state, observation, action, mechanism invocation,
transition, constraint evaluation, market outcome, generated data, and the next state.

### 6.4 Follow behavior to learning

Begin at a deployment parameter or policy. Traverse inner behavior, generated observations, dataset
membership, training, learned parameter, and redeployment. Missing stages remain visible as gaps.

### 6.5 Assess DDGE

Inspect candidates, solver paths, residual histories, multiplicity, basins, stability, certificates,
and claim status. Scalar analytical references and independent numerical oracles appear beside the
package solver when available.

### 6.6 Compare runs

Select two compatible runs. The comparison preflight reports differences in world identity,
protocol, seed, sample, estimator, units, intervention, and software identity before any aligned
chart is shown.

### 6.7 Audit a claim

Start from a claim and traverse supporting evidence, measurements, protocol, source artifact,
verification status, source code, paper anchor, exclusions, and limitations.

### 6.8 Export an investigation

Choose a bounded set of objects, relations, event windows, measurements, claims, evidence, camera
states, and annotations. Compile and verify a standalone HTML snapshot that works without a server
or network.

## 7. Visual system

### 7.1 Workspace composition

The application is an investigation workspace rather than a dashboard:

```text
+----------------+--------------------------------------+------------------+
| Object explorer| Active analytical or spatial lens    | Evidence inspector|
| filters/search | synchronized selection and time      | sources/claims    |
+----------------+--------------------------------------+------------------+
| Timeline, event window, run comparison, status and provenance             |
+-----------------------------------------------------------------------------+
```

The object explorer and inspector remain stable while the center switches lenses.

### 7.2 Lenses

- **World:** typed declaration graph and economic composition.
- **Runtime:** event sequence, state-action-transition flow, and market outcomes.
- **Market:** orders, transactions, clearing, volumes, prices, constraints, and rejections.
- **Learning:** generated data, datasets, training, learned parameters, and deployments.
- **DDGE:** candidates, residuals, basins, stability, fixed-point closure, and certificates.
- **Compare:** aligned and rejected comparisons with explicit comparability diagnostics.
- **Evidence:** claims, measurements, evidence status, protocols, sources, and limitations.
- **Lineage:** derivation and source paths across artifacts and code.
- **Graph:** synchronized 2D and 3D typed relations with deterministic semantic layers and time.
- **Globe:** explicitly geocoded economic objects, flows, interventions, and outcomes.

### 7.3 Visual grammar

The shell uses graphite navigation surfaces around near-white analytical canvases. Color is reserved
for ontology layer, evidence status, selection, intervention, or a declared quantitative scale.
Every state also has a shape, line pattern, label, or icon so color is not the only encoding.

The design excludes gradients, glow, ornamental animation, misleading volume, and unexplained node
size. Charts display units, sample size, uncertainty method, and source. Sparse or unavailable data
uses a textual fallback rather than an interpolated picture.

### 7.4 Two-dimensional graph

The default graph uses stable semantic lanes and profile-specific layouts. It is not initialized by
a random force simulation. Expansion is progressive and bounded. Object selection synchronizes the
inspector, timeline, charts, 2D and 3D graph, and globe.

### 7.5 Synchronized ontology graph

The graph shares selection, typed filters, clustering, neighborhood isolation, path tracing, and
semantic zoom across 2D and 3D. The 3D view assigns meaning to every coordinate:

- X: semantic lane such as agents, institutions, markets, data, or learned models;
- Y: ontology layer;
- Z: time, episode, or version when applicable.

Non-temporal declarations occupy a declared reference plane. Users can isolate layers, expand or
collapse groups, focus the camera on an object or path, switch between perspective and orthographic
cameras, and return to the canonical camera. Layout and camera state are serializable.

The implementation uses React Three Fiber, Three.js, and Drei with:

- `frameloop="demand"`;
- instanced node geometries and shared materials;
- buffer-based or batched relation lines;
- bounded, selective raycasting;
- capped device-pixel ratio;
- progressive subgraph loading;
- no automatic camera movement;
- deterministic placement independent of frame rate or hardware.

### 7.6 Economic globe

The globe renders only objects with explicit `GeoAnchor` relations. It may display:

- agents, institutions, markets, facilities, and jurisdictions;
- trade, capital, credit, information, and deployment flows;
- shocks and interventions;
- regionally measured outcomes and uncertainty;
- run comparisons and time changes.

The globe uses bundled, licensed, simplified vector geometry. It makes no remote tile, font, or data
request. Synthetic or nonspatial runs show an explanatory unavailable state.

### 7.7 Accessibility and fallback

Every 3D workflow has a 2D graph, table, or list equivalent. WebGL failure falls back to 2D without
losing the investigation. Keyboard commands can focus, traverse, select, isolate, and reset the
scene. Reduced-motion mode removes transitions. Selection and evidence remain in ordinary DOM
controls that assistive technology can reach.

## 8. Architecture

### 8.1 Style

The system is a modular monolith with two delivery modes:

1. a local Python service plus browser client;
2. a self-contained portable HTML snapshot.

There is no database, message broker, distributed service, agent framework, or simulation framework
in the workbench path.

### 8.2 Data flow

```text
candidate run directory
            |
            v
bounded file and NPZ preflight
            |
            v
existing artifact verifier
            |
            v
ontology projector -----> coverage ledger
            |
            v
immutable in-memory indexes
       |                    |
       v                    v
loopback REST API      snapshot compiler
       |                    |
       v                    v
React investigation client  self-contained HTML
```

### 8.3 Package boundaries

```text
src/ewm/ontology/
    model.py
    schema.py
    identity.py
    verification.py
    compiler.py
    projection.py
    indexes.py
    query.py
    comparison.py
    snapshot.py
    profiles/
        base.py
        scalar.py
        forecasting.py
        fx.py
        credit.py
        production.py

src/ewm/workbench/
    contracts.py
    api.py
    security.py
    server.py
    export.py
    static/

workbench/
    package.json
    package-lock.json
    vite.config.ts
    src/
    tests/
```

The Python dependency direction is:

```text
core, equilibrium, scenarios, experiments
                    |
                    v
                ontology
                    |
                    v
                workbench
                    |
                    v
                   CLI
```

Existing lower layers cannot import `ewm.ontology` or `ewm.workbench`. The root TypeScript client
depends only on versioned JSON contracts, not Python modules.

### 8.4 Dependency decisions

Python workbench dependencies are optional extras. FastAPI and Uvicorn serve a loopback API and the
built client. Core model users do not install them unless they request the workbench extra.

The frontend uses:

- React and TypeScript;
- Vite for deterministic production assets;
- Cytoscape.js for bounded 2D typed graphs;
- Vega-Lite for analytical charts;
- Three.js, React Three Fiber, and Drei for the 3D graph and globe;
- Vitest, Testing Library, axe, and Playwright for tests.

Built, reproducibly checked static assets ship inside the wheel. Runtime use does not require Node.

### 8.5 Projection bundle

An optional derived projection bundle uses schema `ewm.ontology.v1` and contains:

```text
manifest.json
projection.json
coverage.json
```

The manifest includes source run hash, artifact schema, adapter identity, EWM version, schema
version, payload digests and sizes, projection digest, and integrity level. It excludes wall-clock
time from identity. Projection is written atomically outside the sealed run directory.

### 8.6 Immutable indexes

Indexes are derived in memory from a validated projection. They cover object ID, kind, layer,
incoming and outgoing relation, run, episode, event sequence, time, source locator, measurement,
claim, and evidence status. Index construction is deterministic. No cache is authoritative.

## 9. API contract

### 9.1 Versioning

The local API is rooted at `/api/v1`. Breaking changes require `/api/v2`. Additive minor capability
changes are reported in `X-EWM-API-Minor`. Every response includes schema and projection identity.

### 9.2 Read endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/system` | Version, capabilities, limits, and security mode |
| `GET /api/v1/runs` | Approved verified runs and projection status |
| `GET /api/v1/runs/{run_id}` | Run identity, integrity, profile, and coverage |
| `GET /api/v1/objects/{object_id}` | One object and source locators |
| `GET /api/v1/objects` | Bounded filtered object page |
| `GET /api/v1/relations` | Bounded typed relation page |
| `GET /api/v1/paths` | Bounded typed path or neighborhood query |
| `GET /api/v1/events` | Paginated event window |
| `GET /api/v1/states` | Bounded state observations |
| `GET /api/v1/measurements` | Measurements with units, samples, and uncertainty |
| `GET /api/v1/claims` | Claims and evidence status |
| `GET /api/v1/evidence` | Evidence artifacts and provenance |
| `GET /api/v1/ddge-candidates` | Candidates, residuals, diagnostics, and certificates |

### 9.3 Commands

The two local commands are:

- `POST /api/v1/comparisons`
- `POST /api/v1/snapshot-exports`

They are idempotent for the same canonical request and projection identities. Neither mutates a run.
Requests have explicit size and cost limits.

### 9.4 Frontend data source

The client depends on one interface implemented twice:

```typescript
interface InvestigationDataSource {
  system(): Promise<SystemContract>
  runs(): Promise<RunSummary[]>
  object(id: string): Promise<OntologyObjectContract>
  objects(query: ObjectQuery): Promise<Page<OntologyObjectContract>>
  relations(query: RelationQuery): Promise<Page<RelationContract>>
  paths(query: PathQuery): Promise<PathResult>
  events(query: EventQuery): Promise<Page<EventContract>>
  measurements(query: MeasurementQuery): Promise<Page<MeasurementContract>>
  claims(query: ClaimQuery): Promise<Page<ClaimContract>>
  evidence(query: EvidenceQuery): Promise<Page<EvidenceContract>>
  ddge(query: DdgeQuery): Promise<DdgeResult>
  compare(request: ComparisonRequest): Promise<ComparisonResult>
}
```

`ApiDataSource` uses the loopback API. `SnapshotDataSource` reads validated embedded data. Contract
tests require semantic parity.

## 10. Portable snapshot contract

The portable format is `ewm.investigation.v1`. It is one self-contained HTML file with:

- canonical, base64-encoded investigation data;
- projection, source run, and subset digests;
- the reproducibly built client JavaScript and CSS;
- bundled vector geometry required by a selected globe view;
- serialized lens, filters, selection, time window, camera, and layout state;
- a restrictive content security policy;
- no remote references.

The viewer verifies embedded digests with Web Crypto before making data available to components.
The executable script and style blocks use fixed CSP hashes. Embedded data is non-executable and is
schema-validated after digest verification. An optional detached `.sha256` file supports external
verification.

The embedded digest detects accidental or partial corruption. It does not prove authenticity against
an attacker who can rewrite the HTML, verifier, and digest together. Authenticity requires comparing
the file digest with an expected value obtained separately. V1 does not claim digital signatures.

Snapshots are curated subsets, not large-run archives. Default hard limits are:

- 10,000 objects;
- 30,000 relations;
- 100,000 events;
- 50 MiB generated HTML.

An oversized request returns a scope-reduction diagnostic.

## 11. CLI contract

```text
ewm ontology project RUN_DIR --output PROJECTION_DIR
ewm ontology verify PROJECTION_DIR
ewm workbench RUN_DIR [RUN_DIR ...] [--geo-overlay FILE.json]
ewm snapshot export RUN_DIR --selection SELECTION_JSON --output FILE.html
ewm snapshot verify FILE.html
```

The launcher resolves approved run roots once, verifies them, creates projections and indexes, binds
to an ephemeral loopback port, and exits the service when the parent process ends. A no-store root
document delivered only as a top-level local navigation contains a one-session token in
non-executable bootstrap data. The client moves it into memory, removes the bootstrap node, and uses
the token only in API request headers.

## 12. Scientific validation

Every projection passes four gates.

### 12.1 Artifact authenticity

The workbench first checks file sizes, event-line counts, NPZ member counts, declared uncompressed
sizes, and decompression ratios without changing the run. The existing verifier then checks the
sealed bundle. Missing, modified, malformed, or non-finite payloads fail closed. Original run and
payload digests are preserved. These checks prove integrity under the bundle contract, not the
identity of the run producer.

### 12.2 Projection fidelity

Every supported source field is projected, deliberately omitted with a reason, or rejected. The
coverage ledger is part of the projection identity. The projector may normalize representation but
cannot invent an economic relationship.

### 12.3 Economic conformance

Executable profile invariants preserve behavior, beliefs, feasibility, market clearing, data
generation, learning, deployment, equilibrium, and DDGE distinctions. Scalar cases are checked
against analytical and independent numerical references. Higher-dimensional results retain their
full residual vector and declared norm.

### 12.4 Claim authorization

Each claim links to the evidence that licenses it. Existing EWM claim classifications remain
authoritative. The projector retains the applicable existing state, such as `not_run`,
`diagnostic_only`, or `not_measured`; code rejects a requested unsupported claim instead of assigning
an optimistic substitute.

## 13. Security boundaries

The trusted computing base consists of the artifact verifier, canonical serializer, ontology schema
and projector, local API, and reproducibly built client.

Controls include:

- loopback-only service binding;
- an ephemeral header token held only in browser memory;
- disabled CORS and strict `Host` and `Origin` checks;
- no token in a URL, cookie, Web Storage, or log;
- a startup-approved run registry instead of arbitrary API filesystem paths;
- normalized run-relative source locators;
- byte, archive-expansion, nesting, collection-size, query-cost, and finite-number limits;
- text-only rendering of artifact labels and evidence;
- no raw HTML or `dangerouslySetInnerHTML`;
- no remote scripts, fonts, tiles, telemetry, or data;
- strict snapshot CSP and embedded-data validation;
- no shell, subprocess, plugin execution, or arbitrary Python evaluation;
- default redaction of absolute paths and local environment details.

Malicious run bundles, projections, snapshot payloads, labels, and geometries are treated as
untrusted. Failure is a structured diagnostic, not a partial rendering.

## 14. Performance contract

Benchmarks record environment, sample size, p50, p95, p99, and peak resident memory.

| Tier | Objects | Relations | Events | Purpose |
|---|---:|---:|---:|---|
| Small | 1,000 | 3,000 | 10,000 | Development and pull-request smoke tests |
| Medium | 25,000 | 75,000 | 250,000 | V1 release gate |
| Large | 100,000 | 300,000 | 1,000,000 | Non-blocking scalability characterization |

Medium-tier release budgets on a recorded reference machine are:

- projection and index construction p95 below 5 seconds;
- projector and service peak memory below 1 GiB;
- object lookup p95 below 100 ms;
- bounded subgraph query p95 below 200 ms;
- paginated event-window query p95 below 250 ms;
- ordinary UI response below 100 ms;
- initial analytical view below 2 seconds after API readiness;
- no endpoint returns an unbounded collection.

The 2D graph initially renders at most 2,000 nodes and 5,000 edges. The 3D graph initially renders at
most 5,000 instanced nodes and 10,000 relations, with progressive expansion and a measured frame
budget. During camera or timeline interaction its p95 frame time must remain below 33 ms on the
recorded reference browser and machine. Pointer targets are further bounded. The globe uses geometry
level-of-detail and aggregated flows before exposing individual records.

Portable snapshot export is p95 below 10 seconds and opening becomes interactive within 3 seconds
for an in-budget snapshot. These numbers are release targets, not claims about the current code.

## 15. Test architecture

### 15.1 Python

- unit tests for records, schema, IDs, locators, profiles, indexes, queries, comparisons, and export;
- property tests for ordering, hashes, round trips, collisions, relation consistency, and malformed
  numeric input;
- paper-semantic conformance tests for correspondences, DDGE statuses, claim boundaries, accounting,
  solver metadata, and capability evidence;
- integration tests from verified bundles through projections, API responses, and snapshots;
- corruption tests for runs, projection manifests, and snapshots;
- import-boundary tests that prevent lower-layer dependencies on ontology or workbench.

### 15.2 Frontend

- unit tests for contracts, stores, selectors, formatters, legends, and empty states;
- API and snapshot data-source parity tests;
- component tests for all analytical lenses;
- deterministic-layout tests for 2D and 3D coordinates;
- WebGL interaction tests for selection, focus, layer isolation, camera reset, and fallback;
- globe tests that reject objects without explicit geographic anchors;
- Playwright workflows for verification, world inspection, episode tracing, learning closure, DDGE,
  comparison, claim audit, and offline snapshots;
- axe, keyboard, focus, responsive, reduced-motion, and WebGL-fallback tests;
- visual regression at representative viewports.

### 15.3 Adversarial and reproducibility

Tests cover script payloads in labels, path traversal, invalid hosts and tokens, oversized and deeply
nested JSON, non-finite numbers, malformed geometry, corrupt snapshots, and attempted remote
requests. Repeated projection, frontend build, snapshot, wheel, and source-distribution builds must
be byte-identical under the project reproducibility contract.

### 15.4 CI

Current Ruff, strict MyPy, Python 3.11 and 3.12, 85 percent branch coverage, packaging, conformance,
scientific stress, reproducible build, `pip-audit`, and Bandit gates remain. New jobs add frontend
linting, typing, unit tests, production builds, dependency audit, schema conformance, data-source
parity, offline E2E, WebGL fallback, and static-asset reproducibility. Medium performance fixtures run
on scheduled CI and before releases.

## 16. Feature priority

### 16.1 V1 required

- verified projection and coverage ledger;
- canonical ontology and all registered scenario profiles;
- immutable query and comparison engine;
- secured local API and CLI;
- World, Runtime, Market, Learning, DDGE, Compare, Evidence, and Lineage lenses;
- deterministic 3D ontology scene;
- evidence-aware economic globe capability;
- portable offline snapshot;
- scientific, security, accessibility, performance, and reproducibility gates;
- researcher and extension documentation.

### 16.2 After V1

Profile extension APIs, notebook integration, higher-dimensional DDGE slicing, structured report
export, saved local annotations, richer uncertainty views, JSON-LD or RDF export, authoring tools,
live local observation, and optional large-corpus persistence are deferred.

## 17. Delivery phases

1. Freeze architecture and dependency boundaries.
2. Implement canonical ontology records, schema, identity, and projection bundle.
3. Project verified artifacts through scalar, forecasting, FX, credit, and production adapters.
4. Add immutable indexes, queries, comparison, and CLI.
5. Add the secure loopback service and versioned contracts.
6. Build the investigation shell and primary 2D lenses.
7. Add learning, DDGE, comparison, evidence, and lineage workflows.
8. Add the deterministic 3D ontology graph and evidence-aware globe.
9. Compile and verify portable offline snapshots.
10. Complete hardening, performance, accessibility, documentation, and release audit.

Each phase must pass its own tests, use a granular commit, and be pushed to `main` before the next
phase changes the same boundary.

## 18. Alternatives rejected

### Graph database first

Rejected because current runs fit bounded immutable projections, a database would duplicate the
sealed artifact authority, and it would make portable deterministic snapshots harder. Reconsider
only after measured corpus-scale evidence.

### Dashboard framework

Rejected because the core interaction is object investigation and evidence traversal, not a grid of
aggregate KPIs.

### Agent SDK or Mesa

Rejected as a workbench dependency because the existing execution kernel already owns runtime and
agent semantics. Adapters may be considered later for separate scenario integrations.

### Web server only

Rejected because portable, verifiable, no-server investigations are a first-class research output.

### 3D-only interface

Rejected because depth introduces occlusion and accessibility costs. Three-dimensional views are
valuable only as synchronized, semantically constrained lenses alongside exact 2D and tabular views.

### Geographic inference

Rejected because assigning abstract economic objects to plausible real locations would create false
evidence. Globe placement requires an explicit sourced anchor.

## 19. Risks and controls

| Risk | Control |
|---|---|
| Projection invents unavailable semantics | Coverage ledger, compatible adapters, fail-closed invariants |
| UI overstates scientific evidence | Claim authorization, status vocabulary, evidence inspector, conformance tests |
| Multiplicity disappears in a chart | Correspondence objects, candidate collections, selector and basin metadata |
| 3D presentation creates false meaning | Deterministic semantic axes, legends, 2D parity, no decorative encodings |
| Globe implies unsupported geography | Explicit `GeoAnchor`, sourced relations, unavailable state |
| Large traces exhaust browser memory | Pagination, bounded queries, curated snapshots, progressive rendering |
| Local server becomes a browser attack target | Loopback binding, header token, host/origin checks, no CORS |
| Frontend breaks Python reproducibility | Lockfile, pinned build environment, rebuilt-asset diff, wheel inspection |
| New package contaminates economic engine | Import-boundary test and one-way dependency direction |
| Old artifacts become unreadable | Versioned adapters, runtime-only partial projection, explicit coverage gaps |

## 20. Completion criteria

The architecture is implemented only when:

- lower economic layers remain independent and all existing tests pass;
- verified run bundles project deterministically with complete coverage ledgers;
- all fourteen invariants execute and fail closed;
- all registered profiles pass paper-semantic conformance tests;
- the eight researcher workflows work through both API and snapshot data sources;
- the synchronized 2D and 3D graph is deterministic and the globe never renders unanchored objects;
- every visible claim reaches evidence and preserves its authorization status;
- portable snapshots are byte-reproducible, offline, CSP-constrained, and tamper-evident;
- security, accessibility, performance, packaging, and reproducibility gates pass;
- documentation states remaining source, replication, and capability limitations without inflation.
