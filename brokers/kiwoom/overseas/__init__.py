"""Overseas high-level REST APIs accessed through ``KiwoomClient.overseas``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brokers.kiwoom.overseas.chart import OverseasChartAPI

if TYPE_CHECKING:
    from brokers.kiwoom.client import KiwoomClient


class _OverseasNamespace:
    def __init__(self, parent: "KiwoomClient") -> None:
        self.chart = OverseasChartAPI(parent)


__all__ = ["OverseasChartAPI"]
