# Runnable examples

Each top-level Python file is a small, local entry point for one supported research workflow:

- `scalar.py`, `forecasting.py`, `credit.py`, `production.py`, and `fx.py` exercise economic
  scenarios;
- `cognitive_agent.py` demonstrates the provider-neutral cognitive-agent boundary;
- `offline_alignment.py` demonstrates bounded correction against timestamped offline evidence.

The `extensions/` directory contains package-extension examples that define new scenario behavior.
Examples are cited by tests and paper evidence, so existing paths are compatibility contracts.
