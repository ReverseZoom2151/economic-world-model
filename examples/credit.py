"""Compare the five regimes in the AI-mediated credit laboratory."""

from __future__ import annotations

from pathlib import Path

import ewm


def main() -> None:
    run = ewm.run_experiment(
        "credit.regimes",
        preset="smoke",
        seed=42,
        output_root=Path("runs/examples"),
    )
    records = {str(record["regime"]): record for record in run.result.records}

    assert len(records) == 5
    for regime, metrics in records.items():
        print(
            f"{regime:24s}  profit={metrics['profit_per_applicant']: .6f}  "
            f"approval={metrics['approval_rate']:.3f}  "
            f"adoption={metrics['adoption_rate']:.3f}  "
            f"residual={metrics['residual_norm']:.2e}"
        )
    print(f"artifacts={run.run_dir}")


if __name__ == "__main__":
    main()
