from __future__ import annotations

from dataclasses import dataclass

from brokers.kiwoom.exceptions import KiwoomRealtimeError

_CHANNEL_TO_TR_ID = {
    "industry_index": "0J",
    "trades": "0B",
    "orderbook": "0D",
    "us_trades": "FE",
    "us_orderbook": "FT",
}


@dataclass(frozen=True)
class RealtimeSubscription:
    channel: str
    market: str
    symbol: str
    tr_id: str
    tr_key: str
    exchange: str | None = None


def subscription_for(
    channel: str,
    symbol: str,
    *,
    market: str = "KRX",
    exchange: str | None = None,
) -> RealtimeSubscription:
    try:
        tr_id = _CHANNEL_TO_TR_ID[channel]
    except KeyError as exc:
        allowed = ", ".join(sorted(_CHANNEL_TO_TR_ID))
        raise KiwoomRealtimeError(f"channel must be one of: {allowed}") from exc
    normalized_symbol = symbol.strip()
    if not normalized_symbol:
        raise KiwoomRealtimeError("symbol must not be empty")
    normalized_exchange = (exchange or "").strip().upper()
    if tr_id in {"FE", "FT"} and not normalized_exchange:
        raise KiwoomRealtimeError("exchange must not be empty for US realtime channels")
    return RealtimeSubscription(
        channel=channel,
        market=market,
        symbol=normalized_symbol,
        tr_id=tr_id,
        tr_key=normalized_symbol,
        exchange=normalized_exchange or None,
    )


class SubscriptionRegistry:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], RealtimeSubscription] = {}

    def add(self, subscription: RealtimeSubscription) -> None:
        self._items[(subscription.tr_id, subscription.tr_key)] = subscription

    def remove(self, subscription: RealtimeSubscription) -> None:
        self._items.pop((subscription.tr_id, subscription.tr_key), None)

    def get(self, tr_id: str, tr_key: str) -> RealtimeSubscription | None:
        return self._items.get((tr_id, tr_key))

    def validate(self, *, tr_id: str, tr_key: str) -> RealtimeSubscription:
        subscription = self.get(tr_id, tr_key)
        if subscription is None:
            raise KiwoomRealtimeError(
                f"received unsubscribed Kiwoom realtime event: {tr_id} {tr_key}"
            )
        return subscription

    def all(self) -> tuple[RealtimeSubscription, ...]:
        return tuple(self._items.values())
