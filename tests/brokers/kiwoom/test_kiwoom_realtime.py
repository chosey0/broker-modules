from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from brokers.kiwoom import (
    KiwoomRealtimeError,
    OrderBookSnapshot,
    RealtimeIndustryIndex,
    RealtimeSession,
    RealtimeTick,
    parse_realtime_message,
)
from brokers.kiwoom.realtime.frame import RealtimeFrameProcessor
from brokers.kiwoom.realtime.subscription import (
    SubscriptionRegistry,
    subscription_for,
)


def test_subscription_for_maps_supported_realtime_channels() -> None:
    trade = subscription_for("trades", "005930")
    orderbook = subscription_for("orderbook", "005930")
    industry_index = subscription_for("industry_index", "001")

    assert trade.tr_id == "0B"
    assert trade.tr_key == "005930"
    assert orderbook.tr_id == "0D"
    assert orderbook.tr_key == "005930"
    assert industry_index.tr_id == "0J"
    assert industry_index.tr_key == "001"


def test_subscription_for_rejects_invalid_inputs() -> None:
    with pytest.raises(KiwoomRealtimeError, match="channel must be one of"):
        subscription_for("unknown", "005930")

    with pytest.raises(KiwoomRealtimeError, match="symbol must not be empty"):
        subscription_for("trades", " ")


def test_parse_stock_trade_realtime_frame() -> None:
    event = parse_realtime_message(
        {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0B",
                    "name": "주식체결",
                    "item": "005930",
                    "values": {
                        "20": "093015",
                        "10": "-72000",
                        "11": "-500",
                        "12": "-0.69",
                        "15": "+10",
                        "13": "1,234,567",
                        "14": "88,888,888",
                        "16": "-71900",
                        "17": "+72400",
                        "18": "-71800",
                        "27": "+72100",
                        "28": "-72000",
                    },
                }
            ],
        },
        received_at="2026-07-09T00:00:00+00:00",
    )[0]

    assert isinstance(event, RealtimeTick)
    assert event.market == "KRX"
    assert event.symbol == "005930"
    assert event.tr_id == "0B"
    assert event.tr_key == "005930"
    assert event.exchange_ts == "09:30:15"
    assert event.received_seq == 1
    assert event.price == Decimal("72000")
    assert event.volume == 10
    assert event.side == "buy"
    assert event.change == Decimal("-500")
    assert event.change_rate == Decimal("-0.69")
    assert event.total_volume == 1234567
    assert event.amount == Decimal("88888888")
    assert event.open == Decimal("71900")
    assert event.high == Decimal("72400")
    assert event.low == Decimal("71800")
    assert event.ask_price == Decimal("72100")
    assert event.bid_price == Decimal("72000")
    assert event.raw["10"] == "-72000"


def test_parse_stock_orderbook_realtime_frame() -> None:
    values = {
        "21": "093016",
        "121": "3,000",
        "125": "4,000",
        "122": "-50",
        "126": "+70",
        "23": "-71950",
        "24": "120",
    }
    for level in range(1, 11):
        values[str(40 + level)] = str(72000 + level)
        values[str(50 + level)] = str(71900 - level)
        values[str(60 + level)] = str(100 + level)
        values[str(70 + level)] = str(200 + level)
        values[str(80 + level)] = str(-level)
        values[str(90 + level)] = str(level)

    event = parse_realtime_message(
        {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0D",
                    "name": "주식호가잔량",
                    "item": "005930",
                    "values": values,
                }
            ],
        },
        received_at="2026-07-09T00:00:00+00:00",
    )[0]

    assert isinstance(event, OrderBookSnapshot)
    assert event.symbol == "005930"
    assert event.tr_id == "0D"
    assert event.exchange_ts == "09:30:16"
    assert len(event.asks) == 10
    assert event.asks[0].ask_price == Decimal("72001")
    assert event.asks[0].bid_price == Decimal("71899")
    assert event.asks[0].ask_volume == 101
    assert event.asks[0].bid_volume == 201
    assert event.asks[0].ask_change == -1
    assert event.asks[0].bid_change == 1
    assert event.total_ask_volume == 3000
    assert event.total_bid_volume == 4000
    assert event.total_ask_change == -50
    assert event.total_bid_change == 70
    assert event.expected_price == Decimal("71950")
    assert event.expected_volume == 120


def test_parse_industry_index_realtime_frame() -> None:
    event = parse_realtime_message(
        {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0J",
                    "name": "업종지수",
                    "item": "001",
                    "values": {
                        "20": "110430",
                        "10": "-1762.61",
                        "11": "-189.51",
                        "12": "-9.71",
                        "15": "2800",
                        "13": "725277",
                        "14": "60711859",
                        "16": "-1949.04",
                        "17": "+1961.28",
                        "18": "-1756.13",
                        "25": "5",
                        "26": "-1482363",
                    },
                }
            ],
        },
        received_at="2026-07-09T00:00:00+00:00",
        received_seq_start=7,
    )[0]

    assert isinstance(event, RealtimeIndustryIndex)
    assert event.market == "KRX"
    assert event.industry_code == "001"
    assert event.tr_id == "0J"
    assert event.tr_key == "001"
    assert event.exchange_ts == "11:04:30"
    assert event.received_seq == 7
    assert event.seq == 7
    assert event.current_price == Decimal("1762.61")
    assert event.change == Decimal("-189.51")
    assert event.change_rate == Decimal("-9.71")
    assert event.volume == 2800
    assert event.total_volume == 725277
    assert event.amount_million == 60711859
    assert event.open == Decimal("1949.04")
    assert event.high == Decimal("1961.28")
    assert event.low == Decimal("1756.13")
    assert event.change_signal == "5"
    assert event.volume_change == -1482363
    assert event.raw["10"] == "-1762.61"


def test_frame_processor_validates_industry_index_subscription() -> None:
    registry = SubscriptionRegistry()
    registry.add(subscription_for("industry_index", "001"))
    processor = RealtimeFrameProcessor(registry)

    events = processor.process(
        {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0J",
                    "item": "001",
                    "values": {"20": "110430", "10": "-1762.61", "15": "2800"},
                }
            ],
        }
    )

    assert len(events) == 1
    assert isinstance(events[0], RealtimeIndustryIndex)

    with pytest.raises(KiwoomRealtimeError, match="unsubscribed"):
        processor.process(
            {
                "trnm": "REAL",
                "data": [
                    {
                        "type": "0J",
                        "item": "002",
                        "values": {"20": "110431", "10": "-1000", "15": "1"},
                    }
                ],
            }
        )


def test_frame_processor_preserves_received_seq_for_equal_received_at_events() -> None:
    registry = SubscriptionRegistry()
    registry.add(subscription_for("trades", "005930"))
    registry.add(subscription_for("industry_index", "001"))
    processor = RealtimeFrameProcessor(registry)

    first_events = processor.process(
        {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0B",
                    "item": "005930",
                    "values": {"20": "093015", "10": "72000", "15": "+10"},
                },
                {
                    "type": "0J",
                    "item": "001",
                    "values": {"20": "093015", "10": "-1762.61", "15": "2800"},
                },
            ],
        }
    )
    next_events = processor.process(
        {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0B",
                    "item": "005930",
                    "values": {"20": "093015", "10": "72010", "15": "-3"},
                }
            ],
        }
    )

    events = first_events + next_events
    assert [event.received_seq for event in events] == [1, 2, 3]
    assert len({event.received_at for event in first_events}) == 1
    assert sorted(events, key=lambda event: (event.received_at, event.received_seq)) == [
        *events
    ]


def test_session_subscribe_industry_index_registers_0j_subscription() -> None:
    session = RealtimeSession(_Client())

    subscription = asyncio.run(session.subscribe_industry_index("001"))

    assert subscription.channel == "industry_index"
    assert subscription.tr_id == "0J"
    assert session._subscriptions.all() == (subscription,)


class _Client:
    environment = "mock"

    async def ensure_token(self) -> str:
        return "token"
