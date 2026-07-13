"""Kiwoom US stock chart APIs."""

from __future__ import annotations

from datetime import date as Date
from typing import TYPE_CHECKING

from brokers.kiwoom.domestic.chart import (
    _continuation,
    _normalize_symbol,
    _request_with_rate_limit_retry,
)
from brokers.kiwoom.endpoints.registry import EndpointSpec, lookup
from brokers.kiwoom.models.ohlcv import ChartBar
from brokers.kiwoom.parsers.rest import chart_rows, format_date, parse_chart_bar, parse_date

if TYPE_CHECKING:
    from brokers.kiwoom.client import KiwoomClient

_TICK_SPEC = lookup("overseas.chart.tick")
_MINUTE_SPEC = lookup("overseas.chart.minute")
_DAILY_SPEC = lookup("overseas.chart.daily")
_WEEKLY_SPEC = lookup("overseas.chart.weekly")
_MONTHLY_SPEC = lookup("overseas.chart.monthly")
_YEARLY_SPEC = lookup("overseas.chart.yearly")
_EXCHANGES = {"NA", "ND", "NY"}


class OverseasChartAPI:
    """High-level Kiwoom US stock chart client."""

    def __init__(self, parent: "KiwoomClient") -> None:
        self._parent = parent

    async def tick(
        self,
        symbol: str,
        *,
        exchange: str,
        tick_scope: int = 1,
        adjusted: bool = True,
        apply_exchange_rate: bool = False,
        max_pages: int | None = None,
    ) -> list[ChartBar]:
        """Fetch US tick chart rows from ``usa06010``."""
        return await self._fetch(
            spec=_TICK_SPEC,
            symbol=symbol,
            exchange=exchange,
            interval=f"{_positive(tick_scope, 'tick_scope')}tick",
            body=_body(
                exchange=exchange,
                symbol=symbol,
                adjusted=adjusted,
                apply_exchange_rate=apply_exchange_rate,
                tick_scope=tick_scope,
            ),
            max_pages=max_pages,
        )

    async def minute(
        self,
        symbol: str,
        *,
        exchange: str,
        start_date: str | Date | None = None,
        interval_minutes: int = 1,
        adjusted: bool = True,
        apply_exchange_rate: bool = False,
        max_pages: int | None = None,
    ) -> list[ChartBar]:
        """Fetch US minute chart rows from ``usa06011``."""
        return await self._fetch(
            spec=_MINUTE_SPEC,
            symbol=symbol,
            exchange=exchange,
            interval=f"{_positive(interval_minutes, 'interval_minutes')}min",
            body=_body(
                exchange=exchange,
                symbol=symbol,
                start_date=start_date,
                adjusted=adjusted,
                apply_exchange_rate=apply_exchange_rate,
                tick_scope=interval_minutes,
            ),
            max_pages=max_pages,
        )

    async def daily(
        self,
        symbol: str,
        *,
        exchange: str,
        start_date: str | Date | None = None,
        adjusted: bool = True,
        apply_exchange_rate: bool = False,
        max_pages: int | None = None,
    ) -> list[ChartBar]:
        """Fetch US daily chart rows from ``usa06012``."""
        return await self._period(
            spec=_DAILY_SPEC,
            symbol=symbol,
            exchange=exchange,
            start_date=start_date,
            adjusted=adjusted,
            apply_exchange_rate=apply_exchange_rate,
            interval="1d",
            max_pages=max_pages,
        )

    async def weekly(
        self,
        symbol: str,
        *,
        exchange: str,
        start_date: str | Date | None = None,
        adjusted: bool = True,
        apply_exchange_rate: bool = False,
        max_pages: int | None = None,
    ) -> list[ChartBar]:
        """Fetch US weekly chart rows from ``usa06013``."""
        return await self._period(
            spec=_WEEKLY_SPEC,
            symbol=symbol,
            exchange=exchange,
            start_date=start_date,
            adjusted=adjusted,
            apply_exchange_rate=apply_exchange_rate,
            interval="1w",
            max_pages=max_pages,
        )

    async def monthly(
        self,
        symbol: str,
        *,
        exchange: str,
        start_date: str | Date | None = None,
        adjusted: bool = True,
        apply_exchange_rate: bool = False,
        max_pages: int | None = None,
    ) -> list[ChartBar]:
        """Fetch US monthly chart rows from ``usa06014``."""
        return await self._period(
            spec=_MONTHLY_SPEC,
            symbol=symbol,
            exchange=exchange,
            start_date=start_date,
            adjusted=adjusted,
            apply_exchange_rate=apply_exchange_rate,
            interval="1mo",
            max_pages=max_pages,
        )

    async def yearly(
        self,
        symbol: str,
        *,
        exchange: str,
        start_date: str | Date | None = None,
        adjusted: bool = True,
        apply_exchange_rate: bool = False,
        max_pages: int | None = None,
    ) -> list[ChartBar]:
        """Fetch US yearly chart rows from ``usa06015``."""
        return await self._period(
            spec=_YEARLY_SPEC,
            symbol=symbol,
            exchange=exchange,
            start_date=start_date,
            adjusted=adjusted,
            apply_exchange_rate=apply_exchange_rate,
            interval="1y",
            max_pages=max_pages,
        )

    async def _period(
        self,
        *,
        spec: EndpointSpec,
        symbol: str,
        exchange: str,
        start_date: str | Date | None,
        adjusted: bool,
        apply_exchange_rate: bool,
        interval: str,
        max_pages: int | None,
    ) -> list[ChartBar]:
        return await self._fetch(
            spec=spec,
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            body=_body(
                exchange=exchange,
                symbol=symbol,
                start_date=start_date,
                adjusted=adjusted,
                apply_exchange_rate=apply_exchange_rate,
            ),
            max_pages=max_pages,
        )

    async def _fetch(
        self,
        *,
        spec: EndpointSpec,
        symbol: str,
        exchange: str,
        interval: str,
        body: dict[str, str],
        max_pages: int | None,
    ) -> list[ChartBar]:
        normalized_symbol = _normalize_symbol(symbol)
        normalized_exchange = _normalize_exchange(exchange)
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be at least 1")

        bars: dict[str, ChartBar] = {}
        cont_yn = "N"
        next_key = ""
        seen_next_keys: set[tuple[str, str]] = set()
        page_count = 0
        while max_pages is None or page_count < max_pages:
            response = await _request_with_rate_limit_retry(
                self._parent,
                spec,
                json_body=body,
                cont_yn=cont_yn,
                next_key=next_key,
            )
            page_count += 1
            for row in chart_rows(response.payload, "overseas"):
                bar = parse_chart_bar(
                    market=normalized_exchange,
                    symbol=normalized_symbol,
                    interval=interval,
                    row=row,
                )
                bars[bar.timestamp] = bar

            next_cont_yn, next_key = _continuation(response)
            if next_cont_yn != "Y" or not next_key:
                break
            cursor = (next_cont_yn, next_key)
            if cursor in seen_next_keys:
                break
            seen_next_keys.add(cursor)
            cont_yn = next_cont_yn

        return sorted(bars.values(), key=lambda bar: bar.timestamp)


def _body(
    *,
    exchange: str,
    symbol: str,
    adjusted: bool,
    apply_exchange_rate: bool,
    start_date: str | Date | None = None,
    tick_scope: int | None = None,
) -> dict[str, str]:
    body = {
        "stex_tp": _normalize_exchange(exchange),
        "stk_cd": _normalize_symbol(symbol),
        "upd_stkpc_tp": "1" if adjusted else "0",
        "exrt_appl_tp": "1" if apply_exchange_rate else "0",
    }
    if start_date is not None:
        body["strt_dt"] = _format_start_date(start_date)
    if tick_scope is not None:
        body["tic_scope"] = str(tick_scope)
    return body


def _normalize_exchange(exchange: str) -> str:
    normalized = exchange.strip().upper()
    if normalized not in _EXCHANGES:
        allowed = ", ".join(sorted(_EXCHANGES))
        raise ValueError(f"exchange must be one of: {allowed}")
    return normalized


def _positive(value: int, name: str) -> int:
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def _format_start_date(value: str | Date) -> str:
    if isinstance(value, Date):
        return format_date(value)
    return format_date(parse_date(value))
