# Machine-readable references

This directory is intentionally small and flat:

- `papers.toml` locks source identity and expected PDF metadata;
- `conformance.toml` maps paper requirements to implementation, evidence, status, and limitations;
- `replication-targets.toml` records source-stated, derived, and package-authored numerical targets.

The registries are scientific evidence contracts. Update them transactionally with their code,
tests, and human-readable traceability documentation.

Ignored local source copies belong in `references/local/`. Both source-verification commands use
that directory by default; `--source-dir` remains available when papers live elsewhere.
