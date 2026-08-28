"""Typed values for the heterogeneous foreign-exchange laboratory."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

Side = Literal["buy", "sell"]


@dataclass(frozen=True, slots=True)
class HouseholdBelief:
    """Bounded-memory expected return carried in the FX world state."""

    expected_return: float = 0.0
    observations: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))


@dataclass(frozen=True, slots=True)
class FXAccount:
    """Cash and foreign-currency balances for one market participant."""

    cash: float
    foreign: float

    def __post_init__(self) -> None:
        if self.cash < -1e-12 or self.foreign < -1e-12:
            raise ValueError("FX account balances must be non-negative")


@dataclass(frozen=True, slots=True)
class FXOrder:
    """A limit order for foreign currency priced in units of cash."""

    order_id: str
    agent_id: str
    side: Side
    quantity: float
    limit_price: float

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id must not be empty")
        if not self.agent_id:
            raise ValueError("agent_id must not be empty")
        if self.side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        if self.quantity <= 0.0:
            raise ValueError("quantity must be positive")
        if self.limit_price <= 0.0:
            raise ValueError("limit_price must be positive")


@dataclass(frozen=True, slots=True)
class FXTrade:
    """One buyer-seller match settled at the uniform clearing price."""

    buyer_id: str
    seller_id: str
    quantity: float
    price: float
    buy_order_id: str
    sell_order_id: str


@dataclass(frozen=True, slots=True)
class FXRejection:
    """An order rejected by an explicit feasibility check."""

    order: FXOrder
    reason: str


@dataclass(frozen=True, slots=True)
class FXState:
    """Immutable state of the cash/foreign-currency economy."""

    period: int
    spot: float
    accounts: Mapping[str, FXAccount]
    price_history: tuple[float, ...]
    beliefs: Mapping[str, HouseholdBelief] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.period < 0:
            raise ValueError("period must be non-negative")
        if self.spot <= 0.0:
            raise ValueError("spot must be positive")
        if not self.price_history:
            raise ValueError("price_history must not be empty")
        if any(price <= 0.0 for price in self.price_history):
            raise ValueError("every historical price must be positive")
        object.__setattr__(
            self,
            "accounts",
            MappingProxyType(dict(sorted(self.accounts.items()))),
        )
        object.__setattr__(self, "price_history", tuple(self.price_history))
        object.__setattr__(
            self,
            "beliefs",
            MappingProxyType(dict(sorted(self.beliefs.items()))),
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> FXState:
        """Share this recursively immutable value across transition snapshots."""

        memo[id(self)] = self
        return self


@dataclass(frozen=True, slots=True)
class FXClearingResult:
    """Settled state plus feasibility and accounting diagnostics."""

    state: FXState
    clearing_price: float | None
    volume: float
    trades: tuple[FXTrade, ...]
    accepted_orders: tuple[FXOrder, ...]
    rejections: tuple[FXRejection, ...]
    cash_residual: float
    foreign_residual: float
    clearing_residual: float


@dataclass(frozen=True, slots=True)
class FXSimulationResult:
    """Compact deterministic record of one adaptive FX rollout."""

    prices: tuple[float, ...]
    volumes: tuple[float, ...]
    rejected_orders: tuple[int, ...]
    max_cash_residual: float
    max_foreign_residual: float

    @property
    def metrics(self) -> Mapping[str, float]:
        returns = tuple(
            (right / left) - 1.0
            for left, right in zip(self.prices[:-1], self.prices[1:], strict=True)
        )
        count = len(returns)
        mean_return = sum(returns) / count if count else 0.0
        variance = (
            sum((value - mean_return) ** 2 for value in returns) / count
            if count
            else 0.0
        )
        return MappingProxyType(
            {
                "mean_price": sum(self.prices[1:]) / max(len(self.prices) - 1, 1),
                "total_volume": sum(self.volumes),
                "volatility": variance**0.5,
                "rejected_orders": float(sum(self.rejected_orders)),
            }
        )
