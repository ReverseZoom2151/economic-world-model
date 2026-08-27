"""Roll out the adaptive heterogeneous foreign-exchange economy."""

from __future__ import annotations

import ewm
from ewm.scenarios.fx import FXSimulationResult


def main() -> None:
    scenario = ewm.make("fx", preset="smoke", seed=42)
    result = ewm.rollout(scenario, periods=24)

    assert isinstance(result, FXSimulationResult)
    assert result.max_cash_residual <= 1e-10
    assert result.max_foreign_residual <= 1e-10
    print(f"periods={len(result.volumes)}")
    print(f"final_price={result.prices[-1]:.6f}")
    print(f"total_volume={result.metrics['total_volume']:.6f}")
    print(f"volatility={result.metrics['volatility']:.6f}")
    print(f"max_cash_residual={result.max_cash_residual:.2e}")
    print(f"max_foreign_residual={result.max_foreign_residual:.2e}")


if __name__ == "__main__":
    main()
