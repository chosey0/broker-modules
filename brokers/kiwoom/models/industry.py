from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class IndustryCode:
    """One row from Kiwoom ``ka10101`` industry code list response."""

    request_market_type: str
    market_code: str | None
    code: str
    name: str
    group: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndustryIndex:
    """One row from Kiwoom ``ka20003`` all-industry index response."""

    request_industry_code: str
    industry_code: str
    name: str
    current_price: Decimal | None = None
    change_signal: str | None = None
    change: Decimal | None = None
    change_rate: Decimal | None = None
    volume_thousands: int | None = None
    weight: Decimal | None = None
    amount_million: int | None = None
    limit_up_count: int | None = None
    rising_count: int | None = None
    unchanged_count: int | None = None
    falling_count: int | None = None
    limit_down_count: int | None = None
    listed_count: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RealtimeIndustryIndex:
    """One Kiwoom realtime ``0J`` industry index event."""

    market: str
    industry_code: str
    tr_id: str
    tr_key: str
    exchange_ts: str
    received_at: str
    received_seq: int
    seq: int
    current_price: Decimal | None
    volume: int | None
    change: Decimal | None = None
    change_rate: Decimal | None = None
    total_volume: int | None = None
    amount_million: int | None = None
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    change_signal: str | None = None
    volume_change: int | None = None
    raw: dict[str, str] = field(default_factory=dict)
