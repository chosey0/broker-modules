from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SymbolRecord:
    """Normalized symbol master entry for one listing.

    Covers domestic and overseas listings from KIS symbol master files. The `raw`
    field preserves the source row so cli/services can re-serialize or
    diff against the upstream master.
    """

    market: str
    symbol: str
    standard_code: str = ""
    realtime_symbol: str = ""
    korean_name: str = ""
    english_name: str = ""
    security_type: str = ""
    currency: str = "KRW"
    exchange_id: str = ""
    exchange_code: str = ""
    exchange_name: str = ""
    country_code: str = "KR"
    listed_date: str = ""
    base_price: int | None = None
    lot_size: int | None = None
    raw_source: str = ""
    raw: dict[str, str] = field(default_factory=dict)
    downloaded_at: str = ""

    def with_downloaded_at(self, downloaded_at: str) -> "SymbolRecord":
        return SymbolRecord(**{**self.__dict__, "downloaded_at": downloaded_at})


@dataclass(frozen=True)
class OverseasIndexInfo:
    """KIS overseas stock index information entry from ``frgn_code.mst``."""

    class_code: str
    symbol: str
    english_name: str = ""
    korean_name: str = ""
    industry_code: str = ""
    is_dow30: bool = False
    is_nasdaq100: bool = False
    is_sp500: bool = False
    exchange_code: str = ""
    country_code: str = ""
    raw_source: str = "frgn_code.mst"
    raw: dict[str, str] = field(default_factory=dict)
    downloaded_at: str = ""

    def with_downloaded_at(self, downloaded_at: str) -> "OverseasIndexInfo":
        return OverseasIndexInfo(**{**self.__dict__, "downloaded_at": downloaded_at})
