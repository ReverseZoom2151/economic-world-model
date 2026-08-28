# Evidence-safe repository organization plan

**Status:** complete
**Baseline:** 574 tests passing; Ruff clean; mypy clean  
**Branch:** `main`

## Objective

Make ownership and navigation clearer across `src`, tests, documentation, examples, scripts, and
references without changing economic behavior, public imports, scientific classifications, or the
meaning of existing evidence artifacts.

## Constraints discovered during the audit

- Python relative paths contribute to the package source fingerprint and therefore to future run
  identities.
- Han v1 validation protocols hash fixed co-located source filenames. Their capability and FX source
  files cannot be moved as an ordinary refactor; that requires an explicit v2 evidence migration.
- The conformance registry records implementation and test paths for all 67 paper requirements.
- `ewm`, `ewm.core`, and `ewm.equilibrium` are documented extension surfaces. Existing aggregate
  exports and direct import paths remain compatibility contracts.
- Ontology profile class module names contribute to projection provenance and identity.
- Tests, scripts, examples, and references are already grouped by semantic purpose. Cosmetic bulk
  moves would create traceability churn without improving ownership.

## Target organization

The public top-level packages remain stable:

```text
ewm/
  core/          shared economic records, declarations, protocols, and runtime
  equilibrium/   inner equilibrium, DDGE, fixed points, certificates, diagnostics
  capabilities/  evidence-bound Han L3-L6 substrates (v1 paths retained)
  scenarios/     economy-owned models, presets, mechanisms, and validation
  experiments/   catalog, run artifacts, analyses, studies, and lab executors
  ontology/      domain records, validation, bundles, compilation, and profiles
  workbench/     read-only investigation service and export surfaces
```

Within those boundaries, private implementation concerns may move into nested packages only when
the former path remains a tested facade or when the moved symbol was never public. There must be
one implementation location; facades may re-export but may not duplicate logic.

## Refactoring sequence

1. Lock aggregate exports, historical direct imports, resource loading, class module names, and
   ontology projection identity with characterization tests.
2. Remove the ontology projection-verification import cycle by extracting projection digest logic
   into `ontology/bundles/`, while preserving the public function at its old module path.
3. Split the experiment registry into `experiments/catalog/` models, adapters, executors, and catalog
   assembly. Keep public registry types in `ewm.experiments.registry` so module identity remains
   stable.
4. Extract conformance report construction into an installable package and retain
   `scripts/run_conformance.py` as the documented thin entry point.
5. Add ownership indexes for source packages and the large non-source directories. These indexes
   define what belongs in each location and identify compatibility or evidence-bound paths.
6. Add recursive documentation structure checks while treating historical plans separately from
   current release prose.
7. Run the full test, type, lint, conformance, scientific-stress, and distribution gates.

## Explicit non-moves

- Do not move `src/ewm/capabilities/*.py`, its Han v1 TOML, or the six source files named by the FX
  L1-L2 protocol.
- Do not rename current top-level source packages.
- Do not bulk-mirror `tests/unit/` to the source tree; top-level test categories describe evidence
  intent and are referenced by registries and automation.
- Do not subdivide the eight stable script entry points or the small references and examples
  collections merely for symmetry.
- Do not move current public documentation URLs in this refactor.

## Per-change verification

Every structural change is followed by focused tests plus:

```bash
python -m pytest tests/test_architecture.py tests/test_package.py \
  tests/integration/test_public_api.py -q
ruff check src tests
mypy src
```

The final gate runs all 574 baseline tests, strict source verification, paper conformance,
scientific stress, and installed-distribution checks. A changed future run hash is expected after a
Python source-tree change and is recorded as provenance; numerical outputs and public behavior must
remain unchanged.

## Outcome

Completed on 2026-08-28 with the following structural results:

- Added package and directory ownership maps for `src/ewm`, tests, documentation, examples,
  references, and scripts.
- Added characterization contracts for public exports, historical import paths, installed protocol
  resources, ontology profile identities, and the ignored local paper cache.
- Removed the ontology projection and verification import cycle through the shared
  `ewm.ontology.bundles` identity boundary.
- Split experiment catalog models, scenario adapters, and default assembly into
  `ewm.experiments.catalog` while keeping provenance-bound executors at their historical paths.
- Moved reusable conformance report construction into `ewm.conformance`; the repository script is
  now a thin compatibility entry point.
- Moved both untracked paper PDFs into the single ignored `references/local/` cache and made source
  verification commands use it by default.
- Preserved evidence-bound Han v1 files, public modules, documentation URLs, and test paths. Those
  paths require explicit evidence-version migrations rather than cosmetic moves.

Final verification: 582 tests passed, Ruff passed, mypy passed, 82 strict conformance evidence tests
passed, both paper sources verified, all quick scientific stress checks passed, and the 0.2.0 wheel
and source distribution validated.
