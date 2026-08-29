# Ontology research workbench

**Document version:** 1.0  
**Last reviewed:** 2026-08-29  
**Scope:** Local, read-only investigation of approved ontology projections

The workbench opens verified economic runs as a coordinated object explorer, analytical lens,
evidence inspector, and timeline. It uses the same bounded contracts through a loopback API or a
portable snapshot. It does not mutate runs, infer missing evidence, contact model providers, or make
remote requests for data, tiles, fonts, scripts, or telemetry.

The interface makes no remote requests.

## Installation

The economic engine and ontology compiler use the base installation. The local HTTP service adds an
optional FastAPI and Uvicorn extra:

```bash
python -m pip install -e ".[workbench]"
```

Frontend development and browser tests require Node 22 and npm 10. The built client is already
included in the Python wheel, so researchers do not need Node to inspect a run or open a snapshot.

```bash
cd workbench
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

## Prepare an approved run

Create a source run and verify it before projection:

```bash
ewm run fx.rollout --preset smoke --seed 42 --output runs
ewm verify-run runs/<run_hash>
ewm ontology project --run-dir runs/<run_hash> --output projections/fx-smoke
ewm ontology verify --bundle projections/fx-smoke
```

The API cannot receive a filesystem path. A local launcher must compile or load each approved
projection before the server binds, construct an immutable `ApprovedRunRegistry`, and retain the
source and profile identities. This prevents a browser request from selecting new local files.

The package exposes the launcher primitives for a Python entry point:

```python
from pathlib import Path

from ewm.ontology import DEFAULT_PROFILES, compile_run_projection
from ewm.workbench.http.api import ApprovedRun, ApprovedRunRegistry
from ewm.workbench.http.server import WorkbenchServerConfig, bind_workbench_server

compiled = compile_run_projection(Path("runs/<run_hash>"), adapters=DEFAULT_PROFILES)
provenance = compiled.provenance
registry = ApprovedRunRegistry(
    (
        ApprovedRun(
            run_id=provenance.source_run_hash,
            projection=compiled.projection,
            source_run_hash=provenance.source_run_hash,
            profile_identity=provenance.adapter_identity,
            integrity_level="checksummed",
        ),
    )
)
bound = bind_workbench_server(registry, WorkbenchServerConfig())
print(f"Open {bound.origin} in a local browser")
bound.server.run(sockets=[bound.socket])
```

The browser receives its session token only in the no-store top-level bootstrap document. The token
does not appear in the URL, a cookie, Web Storage, or a log.

## Eight investigation workflows

### Verify and open

Open only a sealed source run that passes artifact verification and has a compatible profile. Read
the run hash, projection digest, profile identity, integrity level, and coverage ledger before using
any chart.

### Understand the world

Use the Economy lens to inspect declared agents, institutions, markets, mechanisms, constraints,
kernels, learners, and interventions. Selection stays synchronized with the explorer and evidence
inspector. Adapter-derived declarations show their profile and source digest.

### Trace an episode

Use the Simulation lens and timeline to follow observed states, action occurrences, mechanism
invocations, transitions, market outcomes, generated data, and event order. Runtime records remain
separate from economic declarations.

### Follow behavior to learning

Use the Learning lens to traverse a parameter version, behavior, generated observations, dataset
membership, training, learned parameters, and deployment. Missing stages appear as coverage gaps
instead of inferred edges.

### Assess DDGE

Use the DDGE lens to inspect candidates, residual histories, tolerances, basins, stability evidence,
and certificates. The lens distinguishes a recorded candidate, a numerical validation, and a
certificate. A solver result cannot become a theorem or welfare claim through visualization.

### Compare runs

Use the Compare lens only after the preflight checks world, protocol, software, seed design,
intervention, estimand, unit, sample, and estimator identities. Incompatible measurements remain
unaligned with explicit reasons. The implementation does not align by display label or coerce units.

### Audit a claim

Use the Evidence and Lineage lenses to traverse claims, classifications, supporting artifacts,
measurements, source locators, code symbols, paper anchors, exclusions, and limitations. The visible
classification is inherited from the source evidence.

### Export an investigation

Choose a bounded object, relation, event, lens, comparison, and camera selection. Export it with
`ewm snapshot export`, verify it with `ewm snapshot verify`, then share the HTML and its detached
digest through separate channels when authenticity comparison matters. The [snapshot guide](snapshots.md)
defines the file contract.

These are workflow contracts over available evidence. Their browser tests exercise navigation,
selection, fallback, integrity, and bounded data access; they do not assert that every scenario has
evidence for every lens.

## Analytical lenses

| Lens | Reads |
|---|---|
| Overview | Task-first run integrity, coverage, and investigation entry points |
| Economy | Economic declarations and their typed relations |
| Simulation | Events, state-action-transition paths, outcomes, and ordering |
| Markets | Prices, volumes, clearing, constraints, transactions, and rejections |
| Learning | Generated data, datasets, training, model versions, and deployment |
| DDGE | Candidates, residuals, basins, stability diagnostics, and certificates |
| Compare | Compatible aligned measurements and rejected alignments |
| Evidence | Claims, classifications, protocols, measurements, sources, and limitations |
| Lineage | Bounded derivation paths across run records, adapters, code, and papers |
| Graph | Synchronized 2D and 3D typed relations, clusters, paths, and neighborhoods |
| Globe | Explicit sourced geography, validity, uncertainty, and flows |

Sparse evidence produces a textual unavailable state. The interface does not fabricate a chart from
absent or incompatible data.

## Versioned API

The local API uses schema `ewm.workbench.api.v1` and prefix `/api/v1`. Every response contains
`ok`, `schema`, `projection_digests`, and either `data` or a structured `error`. The server also
returns `X-EWM-API-Minor`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/system` | API version, mode, and approved-run count |
| GET | `/runs`, `/runs/{run_id}` | Approved projection metadata and coverage |
| GET | `/objects`, `/objects/{object_id}` | Bounded typed records |
| GET | `/relations`, `/paths` | Bounded directed relations and traversals |
| GET | `/events`, `/states`, `/measurements` | Runtime and quantitative records |
| GET | `/claims`, `/evidence`, `/ddge-candidates` | Scientific evidence views |
| POST | `/comparisons` | Idempotent compatibility preflight and alignment |
| POST | `/snapshot-exports` | Idempotent export plan for an explicit selection |

Collection reads use capped limits and opaque cursors. Path queries cap depth and visited records.
Comparison and export requests require an `Idempotency-Key` header. API calls require the exact
`X-EWM-Token` header. Cross-origin requests, unapproved hosts, oversized request bodies, secret query
parameters, and filesystem selectors fail before business logic executes.

Generate the complete deterministic OpenAPI 3.1 contract with:

```bash
python -c 'import json; from ewm.workbench.http.contracts import openapi_document; print(json.dumps(openapi_document(), sort_keys=True))' \
  > workbench-openapi.json
```

## Synchronized ontology graph

The Graph lens renders one typed, evidence-linked graph model in either 2D or 3D. Selection,
visible ontology layers, relation-type filters, neighborhood depth, isolated focus, path targets,
and evidence inspection carry across both dimensions. The 2D mode offers semantic, force, and
hierarchy layouts. Semantic zoom keeps overview labels representative and exposes the fuller bounded
subset in detail mode.

The 3D mode is a graph view, not a second copy of the Economy lens. Nodes and typed edges are the
same bounded records shown in 2D. Its coordinates have declared meanings:

| Coordinate | Meaning |
|---|---|
| X axis | Semantic lane such as agents, institutions, markets, data, or learned models |
| Y axis | One of the six ontology layers |
| Z axis | Time, episode, or version, with non-temporal declarations on a reference plane |

Placement is a pure function of ontology semantics and identity. It does not depend on a random
force simulation, frame rate, GPU, or browser. Node and relation budgets bound the rendered subset.

The controls support orbit, pan, zoom, selection, focus, perspective or orthographic projection,
and camera reset. Camera state can be included in a snapshot. The renderer uses demand-driven frames
and capped pixel density. Reduced-motion mode removes transitions, and WebGL failure returns the
equivalent bounded table while the synchronized 2D graph remains available.

## Globe eligibility

An economic object appears on the globe only when a `GEO_ANCHORED_AT` relation targets an explicit,
sourced `GeoAnchor`. The anchor records EPSG:4326 coordinates, observed or declared basis, evidence
classification, uncertainty, source digest, and validity interval. The renderer never infers a
country from a currency label, an institution name, or a scenario description.

Current built-in scenarios contain no run-authored geographic identifiers. Without an explicit
`ewm.geo-overlay.v1` sidecar, the Globe lens displays an unavailable state. Overlays reject unknown
object identities, missing sources, duplicates, invalid coordinates, unsupported geometry, and
nonfinite values. Bundled Natural Earth boundaries provide context without remote tiles.

## Offline and security behavior

The local service binds to loopback only and disables CORS, access logs, proxy headers, remote
resources, and API documentation routes. Content Security Policy, no-store caching, host and origin
checks, header token authentication, bounded bodies, and strict response envelopes reduce the local
browser attack surface.

Portable snapshots set `connect-src 'none'` and embed the selected data, client code, style, and
optional globe geometry. Browser tests disable networking in Chromium and Firefox and require the
investigation to remain usable. No interface path writes to the sealed run.

## Reproduce the showcase captures

The repository showcase uses a 1,920 by 1,440 browser viewport and a verified research-preset FX
projection. With an approved workbench server already running, capture the same interface states:

```bash
cd workbench
npm run capture:showcase -- http://127.0.0.1:8765 ../docs/assets/workbench
```

The script uses Playwright and writes eight stills plus `capture-manifest.json`. The committed
`demo-config.json` records the 60 fps scene sequence, cursor path, camera motion, and source images
used for the MP4. FFmpeg encodes the final H.264 asset. The [showcase record](assets/workbench/showcase-run.json)
preserves the run identity, replay result, projection digest, and displayed metrics. The separate
[geography declaration](assets/workbench/showcase-geography.md) states the limits of the illustrative
coordinate overlay.

## Troubleshooting

| Symptom | Resolution |
|---|---|
| Empty run selector | Approve at least one verified projection before binding the server. |
| Browser reports launcher required | Open the bound server origin, not `workbench/index.html` directly. |
| API returns 401 | Reload the top-level document so the in-memory token is refreshed. |
| API returns 403 | Use the exact loopback origin and same-origin browser request. |
| A lens is empty | Inspect the coverage ledger; the profile may record the field as unavailable. |
| Comparison is rejected | Read the preflight mismatch instead of coercing the records. |
| 3D graph is unavailable | Use the synchronized 2D graph or table fallback. |
| Globe is unavailable | Supply a valid explicit geo overlay for existing ontology identities. |
| Snapshot refuses export | Reduce selected objects, relations, events, geometry, or comparisons. |

Scientific and operational limits are collected in [Limitations and non-goals](limitations.md).
