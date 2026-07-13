"""Endpoint specs for Kiwoom US stock chart REST APIs."""

from __future__ import annotations

from brokers.kiwoom.endpoints.registry import EndpointSpec, register


def _chart(name: str, api_id: str) -> EndpointSpec:
    return register(
        EndpointSpec(
            name=name,
            method="POST",
            path="/api/us/websocket",
            api_id=api_id,
            supports_continuation=True,
        )
    )


TICK = _chart("overseas.chart.tick", "usa06010")
MINUTE = _chart("overseas.chart.minute", "usa06011")
DAILY = _chart("overseas.chart.daily", "usa06012")
WEEKLY = _chart("overseas.chart.weekly", "usa06013")
MONTHLY = _chart("overseas.chart.monthly", "usa06014")
YEARLY = _chart("overseas.chart.yearly", "usa06015")
