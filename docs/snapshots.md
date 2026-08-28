# Portable investigation snapshots

**Document version:** 1.0  
**Last reviewed:** 2026-08-29  
**Schema:** `ewm.investigation.v1`

A snapshot is a deterministic standalone HTML investigation compiled from one verified run and an
explicit bounded selection. It embeds canonical ontology data, the built workbench client, CSS, and
optional globe geometry. The recipient can open it without Python, a local server, or a network.

## Export

Create a selection file such as `selection.json`:

```json
{
  "object_ids": [],
  "relation_ids": [],
  "event_ids": [],
  "lens": "world",
  "filters": {"kinds": [], "layers": [], "query": ""},
  "time_window": null,
  "camera": null,
  "layout": {}
}
```

An empty identity selection includes the complete bounded projection. A nonempty selection includes
the chosen objects, incident selected relations, related measurements, and applicable coverage.
Supported lenses are `world`, `runtime`, `market`, `learning`, `ddge`, `compare`, `evidence`,
`lineage`, `scene`, and `globe`.

Export and verify:

```bash
ewm snapshot export runs/<run_hash> \
  --selection selection.json \
  --output investigations/fx-smoke.html

ewm snapshot verify investigations/fx-smoke.html
```

Export first verifies the sealed run, selects its compatible source-digested profile, compiles and
validates the ontology, computes the subset digest, embeds canonical bytes, writes the HTML
atomically, and creates `fx-smoke.html.sha256`. Failure returns structured JSON and does not publish
a partial target.

## Selection state

| Field | Contract |
|---|---|
| `object_ids` | Stable ontology identities to include |
| `relation_ids` | Explicit relations whose endpoints are included |
| `event_ids` | Runtime object identities counted against the event budget |
| `lens` | Initial analytical or spatial lens |
| `filters` | Canonical kind, layer, and text-query state |
| `time_window` | Finite start and end values, normalized in ascending order |
| `camera` | Perspective or orthographic mode plus finite 3-vector position and target |
| `layout` | Canonical deterministic layout state |

Unknown fields, unknown identities, invalid lenses, nonfinite coordinates, excessive nesting,
container cycles, and noncanonical values fail validation.

## Hard limits

Default export limits are 10,000 objects, 30,000 relations, 100,000 events, and 50 MiB for the
complete HTML file. Canonical nested data is capped at depth 32 and one million visited values.
Globe geometry accepts at most 10,000 GeoJSON features and only valid EPSG:4326 Polygon or
MultiPolygon coordinates.

An oversized selection raises a machine-readable diagnostic with requested counts, limits, and
specific scope reductions. The exporter does not truncate evidence without telling the researcher.

## Integrity layers

The HTML carries several related identities:

| Identity | Purpose |
|---|---|
| Source run and bundle SHA-256 | Names the sealed evidence from which projection began |
| Profile identity and digest | Names the compatible ontology adapter |
| Projection digest | Names the complete validated ontology projection |
| Subset digest | Names the canonical selected investigation data |
| Embedded SHA-256 | Detects mutation of the base64 payload inside the HTML |
| Full-file SHA-256 | Names every byte of the portable HTML |
| CSP hashes | Authorize the exact embedded script and style bytes |

### Corruption detection

`ewm snapshot verify` recomputes the full-file digest, embedded payload digest, canonical subset
digest, script and style Content Security Policy hashes, schema, and source identities. It rejects
malformed HTML, invalid base64, changed embedded data, changed executable assets, external resource
references, schema drift, and digest mismatch.

### Authenticity

A digest found inside the same file cannot identify who supplied that file. Pass a full-file SHA-256
obtained through a separate trusted channel:

```bash
ewm snapshot verify investigations/fx-smoke.html \
  --expected-sha256 <64-lowercase-hex-characters>
```

This proves that the file matches the separately obtained digest. It is not a digital signature and
does not authenticate an author, institution, timestamp, or scientific claim. The verification
report therefore keeps `authenticity_verified`, `digital_signature_present`, and
`authenticity_claim` separate from corruption checks.

## Offline behavior

The document uses a restrictive Content Security Policy with `default-src 'none'` and
`connect-src 'none'`. Scripts and styles are inline and hash-authorized. Images and fonts may use
embedded data only. The client verifies the canonical payload with browser Web Crypto before React
renders the investigation. A failed bootstrap shows an integrity error and refuses the data source.

The release browser suite opens generated files with all network routes aborted in Chromium and
Firefox. It also confirms that a corrupted payload does not render. The interface retains 2D
fallbacks when WebGL is unavailable.

## Globe snapshots

Globe geometry is bundled only when `lens` is `globe` and validated geometry was supplied to the
snapshot compiler. An ontology object still requires an explicit `GEO_ANCHORED_AT` relation to a
sourced `GeoAnchor`. Bundling a map does not make an unanchored object geographically eligible.

## Sharing protocol

1. Keep the original sealed run and projection identities with the research record.
2. Export the smallest selection needed to review the result.
3. Run `ewm snapshot verify` before transfer.
4. Send the HTML and expected full-file digest through separate channels if origin matters.
5. Ask the recipient to verify with `--expected-sha256` before opening the result.
6. State the claim classification and limitations outside the file when the snapshot supports a
   publication or review.

The snapshot is a derived view. It does not replace the source run, its manifest, a strict source
audit, or the commands in the [replication guide](replication.md).

## Troubleshooting

| Error | Meaning and response |
|---|---|
| `snapshot_scope_exceeded` | Reduce the reported object, relation, or event selection. |
| `snapshot_file_size_exceeded` | Reduce data, geometry, comparisons, or selected lenses. |
| Embedded payload digest mismatch | Treat the file as corrupted and obtain a new copy. |
| Expected file digest mismatch | The received file differs from the separately trusted identity. |
| CSP hash mismatch | Embedded executable bytes changed; do not open the investigation. |
| External resource reference | The file violates the standalone contract. |
| Source compilation failure | Verify the source run and compatible profile before exporting again. |

See the [ontology guide](ontology.md) for source semantics and the [workbench guide](workbench.md)
for the interactive lenses.
