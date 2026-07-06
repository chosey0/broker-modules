from __future__ import annotations

import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO

import brokers.kis as kis
from brokers.kis import (
    Credentials,
    KisClient,
    KisConfigError,
    MockNotSupportedError,
    parse_overseas_index_info,
    parse_overseas_minute_bar,
)
from brokers.kis.auth import IssuedToken, parse_token_response
from brokers.kis.parsers import output_rows
from brokers.kis.symbols import parse_symbol_master


def test_kis_package_exports_core_sdk_api() -> None:
    assert kis.KisClient is KisClient
    assert kis.Credentials is Credentials
    assert kis.IssuedToken is IssuedToken
    assert kis.__version__ == "0.1.0"
    domestic = {name for name in kis.names() if name.startswith("domestic.")}
    assert domestic == {
        "domestic.chart.minute",
        "domestic.realtime.orderbook",
        "domestic.realtime.trades",
    }
    assert "overseas.chart.minute" in kis.names()


def test_endpoint_registry_rejects_mock_for_unsupported_endpoint() -> None:
    spec = kis.lookup("overseas.chart.minute")

    try:
        spec.tr_id_for("mock")
    except MockNotSupportedError as exc:
        assert exc.endpoint_name == "overseas.chart.minute"
    else:
        raise AssertionError("expected MockNotSupportedError")


def test_endpoint_registry_rejects_invalid_environment() -> None:
    spec = kis.lookup("overseas.chart.minute")

    try:
        spec.tr_id_for("dev")  # type: ignore[arg-type]
    except KisConfigError as exc:
        assert "environment must be one of" in str(exc)
    else:
        raise AssertionError("expected KisConfigError")


def test_kis_parsers_normalize_rest_payloads() -> None:
    price = kis.parse_overseas_current_price(
        market="NASDAQ",
        symbol="AAPL",
        output={"name": "Apple Inc.", "last": "190.25", "curr": "USD", "tvol": "1,234"},
    )
    minute = parse_overseas_minute_bar(
        market="NASDAQ",
        symbol="AAPL",
        interval_minutes=5,
        row={
            "tymd": "20240222",
            "xymd": "20240222",
            "xhms": "160000",
            "kymd": "20240223",
            "khms": "060000",
            "open": "197.3400",
            "high": "197.4100",
            "low": "197.2800",
            "last": "197.4100",
            "evol": "5695",
            "eamt": "1123799",
        },
    )

    assert price.name == "Apple Inc."
    assert price.price == Decimal("190.25")
    assert price.volume == 1234
    assert minute.local_date == "2024-02-22"
    assert minute.korea_time == "06:00:00"


def test_kis_auth_and_response_helpers() -> None:
    issued_at = datetime(2026, 5, 13, 1, 0, tzinfo=UTC)

    token = parse_token_response(
        {
            "access_token": "secret-token",
            "token_type": "Bearer",
            "expires_in": "3600",
        },
        issued_at=issued_at,
    )

    assert token.expires_at == issued_at + timedelta(seconds=3600)
    assert output_rows({"output": {"symbol": "AAPL"}}) == [{"symbol": "AAPL"}]
    assert output_rows({"output": {"summary": "not a row"}, "output2": []}) == []


def test_kis_symbol_master_parser_handles_overseas_zip() -> None:
    zip_bytes = BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as archive:
        archive.writestr(
            "nasmst.cod",
            "\t".join(
                [
                    "US",
                    "NAS",
                    "NASDAQ",
                    "NASDAQ",
                    "AAPL",
                    "DNAAPL",
                    "애플",
                    "Apple Inc",
                    "STOCK",
                    "USD",
                    "2",
                    "0",
                    "19700",
                    "1",
                    "1",
                    "093000",
                    "160000",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            ).encode("cp949"),
        )

    records = parse_symbol_master("NASDAQ", zip_bytes.getvalue())

    assert len(records) == 1
    assert records[0].symbol == "AAPL"
    assert records[0].english_name == "Apple Inc"
    assert records[0].currency == "USD"


def test_kis_overseas_index_info_parser_handles_cp949_fixed_width_zip() -> None:
    zip_bytes = BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as archive:
        archive.writestr(
            "frgn_code.mst",
            b"\n".join(
                [
                    _overseas_index_row(
                        class_code="W",
                        symbol="US#SPX",
                        english_name="S&P 500 INDEX",
                        korean_name="미국 S&P 500",
                        industry_code="SPX",
                        dow30="0",
                        nasdaq100="0",
                        sp500="1",
                        exchange_code="NYSE",
                        country_code="840",
                    ),
                    _overseas_index_row(
                        class_code="P",
                        symbol="US#DJI",
                        english_name="Dow Jones Industrial Average",
                        korean_name="다우존스 산업지수",
                        industry_code="DOW",
                        dow30="1",
                        nasdaq100="0",
                        sp500="0",
                        exchange_code="NYSE",
                        country_code="840",
                    ),
                    (
                        "HHK:2951   JIYIHOUSE RTS                          "
                        "집일하우스홀드인터내셔널홀딩스 - 신주인수권    SEHKHK "
                    ).encode("cp949"),
                ]
            ),
        )

    records = parse_overseas_index_info(zip_bytes.getvalue())

    assert kis.OverseasIndexInfo is type(records[0])
    assert len(records) == 3
    assert records[0].symbol == "US#SPX"
    assert records[0].korean_name == "미국 S&P 500"
    assert records[0].industry_code == "SPX"
    assert records[0].is_sp500 is True
    assert records[0].is_dow30 is False
    assert records[0].exchange_code == "NYSE"
    assert records[0].country_code == "840"
    assert records[1].is_dow30 is True
    assert records[2].symbol == "HK:2951"
    assert records[2].korean_name == "집일하우스홀드인터내셔널홀딩스 - 신주인수권"
    assert records[2].exchange_code == "SEHK"
    assert records[2].country_code == "HK"


def _overseas_index_row(
    *,
    class_code: str,
    symbol: str,
    english_name: str,
    korean_name: str,
    industry_code: str,
    dow30: str,
    nasdaq100: str,
    sp500: str,
    exchange_code: str,
    country_code: str,
) -> bytes:
    values = (
        (class_code, 1),
        (symbol, 10),
        (english_name, 39),
        (korean_name, 40),
        (industry_code, 4),
        (dow30, 1),
        (nasdaq100, 1),
        (sp500, 1),
        (exchange_code, 4),
        (country_code, 3),
    )
    return b"".join(_cp949_field(value, width) for value, width in values)


def _cp949_field(value: str, width: int) -> bytes:
    encoded = value.encode("cp949")
    if len(encoded) > width:
        raise ValueError(f"{value!r} exceeds {width} cp949 bytes")
    return encoded + (b" " * (width - len(encoded)))
