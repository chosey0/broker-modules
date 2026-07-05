from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import httpx

from brokers.kis import (
    Credentials,
    KisClient,
    lookup,
    names,
    parse_overseas_volume_surge_item,
)


def test_stage5_overseas_endpoint_specs_are_registered() -> None:
    assert len(names()) >= 20
    assert "domestic.chart.minute" in names()
    assert lookup("overseas.analysis.volume_surge").tr_id_mock is None
    assert lookup("overseas.chart.ohlcv").tr_id_for("mock") == "FHKST03030100"
    assert lookup("overseas.chart.index_minute").tr_id_for("mock") == "FHKST03030200"


def test_parse_overseas_volume_surge_from_document_shape() -> None:
    result = parse_overseas_volume_surge_item(
        exchange="NAS",
        row={
            "excd": "NAS",
            "symb": "AAPL",
            "knam": "애플",
            "last": "190.25",
            "diff": "1.23",
            "rate": "0.65",
            "tvol": "987654",
        },
    )

    assert result.exchange == "NAS"
    assert result.symbol == "AAPL"
    assert result.name == "애플"
    assert result.price == Decimal("190.25")
    assert result.volume == 987654


def test_client_overseas_volume_surge_uses_mock_transport() -> None:
    requests: list[httpx.Request] = []

    async def run():
        async with _client(_handler_for(requests)) as client:
            return await client.overseas.analysis.volume_surge("NAS", 1)

    rows = asyncio.run(run())

    assert len(rows) == 1
    assert rows[0].symbol == "AAPL"
    assert rows[0].price == Decimal("190.25")
    assert requests[-1].url.path == "/uapi/overseas-stock/v1/ranking/volume-surge"


def test_client_overseas_chart_normalizes_exchange_aliases() -> None:
    requests: list[httpx.Request] = []

    async def run():
        async with _client(_chart_handler_for(requests)) as client:
            return await client.overseas.chart.daily(
                "SOXL",
                exchange="AMEX",  # type: ignore[arg-type]
                start="2026-01-01",
                end="2026-06-17",
            )

    rows = asyncio.run(run())

    assert len(rows) == 1
    assert rows[0].market == "AMS"
    assert requests[-1].url.params["EXCD"] == "AMS"


def test_client_overseas_major_index_chart_uses_index_contract() -> None:
    requests: list[httpx.Request] = []

    async def run():
        async with _client(_major_index_chart_handler_for(requests)) as client:
            return await client.overseas.chart.major_index(
                ".dji",
                start=date(2025, 1, 1),
                end="2025-01-31",
                period="D",
            )

    rows = asyncio.run(run())

    assert [row.timestamp for row in rows] == ["2025-01-02", "2025-01-03"]
    assert rows[0].market == "OVERSEAS_INDEX"
    assert rows[0].symbol == ".DJI"
    assert rows[0].interval == "1d"
    assert rows[0].open == Decimal("42500.10")
    assert rows[1].close == Decimal("42800.20")
    assert rows[1].volume == 123456789

    request = requests[-1]
    assert request.url.path == "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice"
    assert request.headers["tr_id"] == "FHKST03030100"
    assert request.url.params["FID_COND_MRKT_DIV_CODE"] == "N"
    assert request.url.params["FID_INPUT_ISCD"] == ".DJI"
    assert request.url.params["FID_INPUT_DATE_1"] == "20250101"
    assert request.url.params["FID_INPUT_DATE_2"] == "20250131"
    assert request.url.params["FID_PERIOD_DIV_CODE"] == "D"


def test_client_overseas_index_minute_chart_paginates_with_tr_cont() -> None:
    requests: list[httpx.Request] = []

    async def run():
        async with _client(_index_minute_chart_handler_for(requests)) as client:
            return await client.overseas.chart.index_minute(
                "spx",
                start="2025-01-03 09:31:00",
                hour_class="0",
            )

    rows = asyncio.run(run())

    assert [(row.business_date, row.time) for row in rows] == [
        ("2025-01-03", "09:31:00"),
        ("2025-01-03", "09:32:00"),
        ("2025-01-03", "09:33:00"),
    ]
    assert rows[0].market == "OVERSEAS_INDEX"
    assert rows[0].symbol == "SPX"
    assert rows[0].open == Decimal("5901.10")
    assert rows[-1].close == Decimal("5905.30")
    assert rows[-1].volume == 1200

    first = requests[1]
    second = requests[2]
    assert first.url.path == "/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice"
    assert first.headers["tr_id"] == "FHKST03030200"
    assert "tr_cont" not in first.headers
    assert first.url.params["FID_COND_MRKT_DIV_CODE"] == "N"
    assert first.url.params["FID_INPUT_ISCD"] == "SPX"
    assert first.url.params["FID_HOUR_CLS_CODE"] == "0"
    assert first.url.params["FID_PW_DATA_INCU_YN"] == "Y"
    assert second.headers["tr_cont"] == "N"


def _client(handler) -> KisClient:
    return KisClient(
        credentials=Credentials("app-key", "app-secret"),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _handler_for(requests: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token",
                    "token_type": "Bearer",
                    "expires_in": 86400,
                },
            )
        if request.url.path.endswith("/volume-surge"):
            return httpx.Response(
                200,
                json={
                    "rt_cd": "0",
                    "output": [
                        {
                            "excd": "NAS",
                            "symb": "AAPL",
                            "knam": "애플",
                            "last": "190.25",
                            "diff": "1.23",
                            "rate": "0.65",
                            "tvol": "987654",
                        }
                    ],
                },
            )
        return httpx.Response(404, json={"rt_cd": "1", "msg1": "unexpected"})

    return handler


def _index_minute_chart_handler_for(requests: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token",
                    "token_type": "Bearer",
                    "expires_in": 86400,
                },
            )
        if request.url.path.endswith("/inquire-time-indexchartprice"):
            if request.headers.get("tr_cont") == "N":
                return httpx.Response(
                    200,
                    headers={"tr_cont": ""},
                    json={
                        "rt_cd": "0",
                        "output1": {"hts_kor_isnm": "S&P 500", "stck_shrn_iscd": "SPX"},
                        "output2": [
                            _index_minute_row("093200", "5903.30", "900"),
                            _index_minute_row("093100", "5901.30", "800"),
                            _index_minute_row("093000", "5900.30", "700"),
                        ],
                    },
                )
            return httpx.Response(
                200,
                headers={"tr_cont": "M"},
                json={
                    "rt_cd": "0",
                    "output1": {"hts_kor_isnm": "S&P 500", "stck_shrn_iscd": "SPX"},
                    "output2": [
                        _index_minute_row("093300", "5905.30", "1200"),
                        _index_minute_row("093200", "5903.30", "900"),
                    ],
                },
            )
        return httpx.Response(404, json={"rt_cd": "1", "msg1": "unexpected"})

    return handler


def _index_minute_row(time: str, close: str, volume: str) -> dict[str, str]:
    return {
        "stck_bsop_date": "20250103",
        "stck_cntg_hour": time,
        "optn_prpr": close,
        "optn_oprc": "5901.10",
        "optn_hgpr": "5906.00",
        "optn_lwpr": "5900.00",
        "cntg_vol": volume,
    }


def _major_index_chart_handler_for(requests: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token",
                    "token_type": "Bearer",
                    "expires_in": 86400,
                },
            )
        if request.url.path.endswith("/inquire-daily-chartprice"):
            return httpx.Response(
                200,
                json={
                    "rt_cd": "0",
                    "output1": {
                        "hts_kor_isnm": "다우존스 산업지수",
                        "stck_shrn_iscd": ".DJI",
                    },
                    "output2": [
                        {
                            "stck_bsop_date": "20250103",
                            "ovrs_nmix_oprc": "42700.50",
                            "ovrs_nmix_hgpr": "42900.00",
                            "ovrs_nmix_lwpr": "42600.00",
                            "ovrs_nmix_prpr": "42800.20",
                            "acml_vol": "123456789",
                            "ovrs_nmix_prdy_vrss": "100.10",
                            "prdy_ctrt": "0.23",
                        },
                        {
                            "stck_bsop_date": "20250102",
                            "ovrs_nmix_oprc": "42500.10",
                            "ovrs_nmix_hgpr": "42750.00",
                            "ovrs_nmix_lwpr": "42400.00",
                            "ovrs_nmix_prpr": "42700.10",
                            "acml_vol": "98765432",
                        },
                    ],
                },
            )
        return httpx.Response(404, json={"rt_cd": "1", "msg1": "unexpected"})

    return handler


def _chart_handler_for(requests: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token",
                    "token_type": "Bearer",
                    "expires_in": 86400,
                },
            )
        if request.url.path.endswith("/dailyprice"):
            return httpx.Response(
                200,
                json={
                    "rt_cd": "0",
                    "output2": [
                        {
                            "xymd": "20260617",
                            "open": "10.00",
                            "high": "11.00",
                            "low": "9.00",
                            "clos": "10.50",
                            "tvol": "12345",
                        }
                    ],
                },
            )
        return httpx.Response(404, json={"rt_cd": "1", "msg1": "unexpected"})

    return handler
