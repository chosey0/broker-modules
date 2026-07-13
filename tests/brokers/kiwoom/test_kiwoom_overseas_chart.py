from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from brokers.kiwoom import Credentials, KiwoomClient
from brokers.kiwoom._internal.http import HttpResponse
from brokers.kiwoom.overseas.chart import OverseasChartAPI


def _tick_row(timestamp: str) -> dict[str, str]:
    return {
        "cntr_tm": timestamp,
        "cur_prc": "201.3900",
        "trde_qty": "1000",
        "open_pric": "200.0000",
        "high_pric": "202.0000",
        "low_pric": "199.0000",
    }


def _period_row(date: str) -> dict[str, str]:
    return {
        "dt": date,
        "cur_prc": "201.3900",
        "acc_trde_qty": "1000",
        "acc_trde_prica": "100000",
        "open_pric": "200.0000",
        "high_pric": "202.0000",
        "low_pric": "199.0000",
    }

@pytest.mark.parametrize(
    (
        "method_name",
        "kwargs",
        "api_id",
        "request_body",
        "interval",
        "row",
        "amount",
    ),
    [
        (
            "tick",
            {"exchange": "ND", "tick_scope": 3, "max_pages": 1},
            "usa06010",
            {
                "stex_tp": "ND",
                "stk_cd": "NVDA",
                "upd_stkpc_tp": "1",
                "exrt_appl_tp": "0",
                "tic_scope": "3",
            },
            "3tick",
            _tick_row("20260624080700"),
            None,
        ),
        (
            "minute",
            {
                "exchange": "ND",
                "start_date": "2026-06-24",
                "interval_minutes": 5,
                "adjusted": False,
                "apply_exchange_rate": True,
                "max_pages": 1,
            },
            "usa06011",
            {
                "stex_tp": "ND",
                "stk_cd": "NVDA",
                "upd_stkpc_tp": "0",
                "exrt_appl_tp": "1",
                "strt_dt": "20260624",
                "tic_scope": "5",
            },
            "5min",
            _tick_row("20260624080800"),
            None,
        ),
        (
            "daily",
            {"exchange": "ND", "start_date": "2026-06-24", "max_pages": 1},
            "usa06012",
            {
                "stex_tp": "ND",
                "stk_cd": "NVDA",
                "upd_stkpc_tp": "1",
                "exrt_appl_tp": "0",
                "strt_dt": "20260624",
            },
            "1d",
            _period_row("20260624"),
            Decimal("100000"),
        ),
        (
            "weekly",
            {"exchange": "ND", "start_date": "2026-06-22", "max_pages": 1},
            "usa06013",
            {
                "stex_tp": "ND",
                "stk_cd": "NVDA",
                "upd_stkpc_tp": "1",
                "exrt_appl_tp": "0",
                "strt_dt": "20260622",
            },
            "1w",
            _period_row("20260622"),
            Decimal("100000"),
        ),
        (
            "monthly",
            {"exchange": "ND", "start_date": "2026-06-01", "max_pages": 1},
            "usa06014",
            {
                "stex_tp": "ND",
                "stk_cd": "NVDA",
                "upd_stkpc_tp": "1",
                "exrt_appl_tp": "0",
                "strt_dt": "20260601",
            },
            "1mo",
            _period_row("20260601"),
            Decimal("100000"),
        ),
        (
            "yearly",
            {"exchange": "ND", "start_date": "2026-01-01", "max_pages": 1},
            "usa06015",
            {
                "stex_tp": "ND",
                "stk_cd": "NVDA",
                "upd_stkpc_tp": "1",
                "exrt_appl_tp": "0",
                "strt_dt": "20260101",
            },
            "1y",
            _period_row("20260102"),
            Decimal("100000"),
        ),
    ],
)
def test_us_chart_contracts(
    method_name: str,
    kwargs: dict[str, object],
    api_id: str,
    request_body: dict[str, str],
    interval: str,
    row: dict[str, str],
    amount: Decimal | None,
) -> None:
    parent = _ChartParent(rows=[row])
    method = getattr(OverseasChartAPI(parent), method_name)

    bars = asyncio.run(method("NVDA", **kwargs))

    assert parent.api_id == api_id
    assert parent.path == "/api/us/websocket"
    assert parent.json_body == request_body
    assert bars[0].market == "ND"
    assert bars[0].symbol == "NVDA"
    assert bars[0].interval == interval
    assert bars[0].volume == 1000
    assert bars[0].amount == amount


def test_us_chart_follows_continuation_headers() -> None:
    parent = _PagedChartParent()

    bars = asyncio.run(
        OverseasChartAPI(parent).minute(
            "NVDA",
            exchange="ND",
            start_date="2026-06-24",
        )
    )

    assert parent.calls == [("N", ""), ("Y", "page-2")]
    assert [bar.timestamp for bar in bars] == [
        "2026-06-24 08:07:00",
        "2026-06-24 08:08:00",
    ]


def test_us_chart_validates_exchange_and_scope() -> None:
    api = OverseasChartAPI(_ChartParent(rows=[]))

    with pytest.raises(ValueError, match="exchange must be one of: NA, ND, NY"):
        asyncio.run(api.daily("NVDA", exchange="NAS"))
    with pytest.raises(ValueError, match="interval_minutes must be at least 1"):
        asyncio.run(api.minute("NVDA", exchange="ND", interval_minutes=0))


def test_kiwoom_client_exposes_overseas_chart_api() -> None:
    client = KiwoomClient(Credentials(app_key="app", secret_key="secret"))

    assert isinstance(client.overseas.chart, OverseasChartAPI)


class _ChartParent:
    def __init__(self, *, rows: list[dict[str, str]]) -> None:
        self.rows = rows
        self.api_id = ""
        self.path = ""
        self.json_body: dict[str, str] = {}

    async def request_raw(self, spec, *args, **kwargs) -> HttpResponse:
        self.api_id = spec.api_id
        self.path = spec.path
        self.json_body = kwargs["json_body"]
        return _response(self.rows)


class _PagedChartParent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def request_raw(self, spec, *args, **kwargs) -> HttpResponse:
        self.calls.append((kwargs["cont_yn"], kwargs["next_key"]))
        if len(self.calls) == 1:
            return _response(
                [_tick_row("20260624080800")],
                headers={"cont-yn": "Y", "next-key": "page-2"},
            )
        return _response([_tick_row("20260624080700")])


def _response(
    rows: list[dict[str, str]],
    *,
    headers: dict[str, str] | None = None,
) -> HttpResponse:
    return HttpResponse(
        payload={"return_code": "0", "result_list": rows},
        headers=headers or {},
        status_code=200,
    )
