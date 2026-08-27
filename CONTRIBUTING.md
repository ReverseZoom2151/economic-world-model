# Contributing

Thank you for considering a contribution to Economic World Model. This project values
reproducible engineering, explicit scientific boundaries, and small reviewable changes.

Last reviewed: 2026-08-28.

## Before opening a change

Use GitHub Issues for bug reports and bounded feature proposals. Security reports must follow
[SECURITY.md](SECURITY.md) and must not be filed as public issues.

For scientific changes, identify whether the change is an implementation, a numerical check, an
experiment, or a claim about external evidence. Local tests and simulations do not replace a
proof, independent replication, or external benchmark result.

## Development setup

The supported Python versions are 3.11 and 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

Run the ordinary local gates before requesting review:

```bash
ruff check .
mypy src
coverage run -m pytest -q
coverage report
python -m build
python -m twine check dist/*
python scripts/check_distribution.py dist
```

The security, property, and mutation workflows are intentionally separate from ordinary CI. Their
local commands are documented in the corresponding workflow files and can be run when relevant.

## Pull requests

- Keep a pull request focused on one concern.
- Add or update tests for behavior changes.
- Preserve deterministic seeds and record tolerances for numerical work.
- State any failed, skipped, or unavailable verification explicitly.
- Do not commit generated runs, credentials, private data, or local paper PDFs.
- Update `CHANGELOG.md` when a user-visible behavior or release surface changes.
- Complete the pull request template and link the relevant issue when one exists.

The maintainer may ask for a smaller change, additional evidence, or an explicit claim-boundary
note before merging.

## Review and decisions

Current review authority and project decision rules are described in [GOVERNANCE.md](GOVERNANCE.md)
and [MAINTAINERS.md](MAINTAINERS.md). Participation is governed by
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
