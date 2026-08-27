# Governance

Last reviewed: 2026-08-28.

## Project model

Economic World Model currently uses a single-maintainer governance model. The maintainer listed in
[MAINTAINERS.md](MAINTAINERS.md) has final responsibility for repository access, releases,
security coordination, scope, and merge decisions.

This document describes current authority. It does not imply the existence of a foundation,
steering committee, employer sponsor, or external maintainers.

## Decision process

Routine changes are decided through pull request review. Material changes should begin with a
GitHub Issue that records the problem, alternatives, scientific or compatibility implications,
and verification plan.

The maintainer seeks technically grounded discussion and may defer a decision when evidence is
insufficient. Final decisions consider:

- scientific truthfulness and explicit claim boundaries;
- reproducibility and deterministic verification;
- backward compatibility and migration cost;
- security and supply-chain risk;
- maintenance burden and project scope.

When consensus is not reached, the maintainer records the decision and rationale in the issue or
pull request.

## Roles

Contributors may report issues, propose designs, review changes, and submit pull requests.
Maintainer status is not earned automatically through contribution volume. Adding or removing a
maintainer requires a public update to `MAINTAINERS.md` and this governance record by a current
maintainer.

## Releases and security

Only a maintainer may authorize a release or change repository security settings. Release
automation validates existing tags and produces GitHub release assets. Package-index publication
is not configured. Security reports follow [SECURITY.md](SECURITY.md).

## Governance changes

Governance changes use the same review process as code changes and must be explicit. If the project
gains multiple maintainers, this document should be revised before shared decision authority is
assumed.
