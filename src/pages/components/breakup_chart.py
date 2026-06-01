"""Yearly bar chart reader. Data read from Highcharts JS state, not SVG."""

from __future__ import annotations

from decimal import Decimal

from playwright.sync_api import Page

from src.utils.highcharts_reader import dump_charts, yearly_chart_series
from src.utils.logging_setup import get_logger

log = get_logger(__name__)


class BreakupChart:
    """Yearly bar chart reader. Pulls data from Highcharts' JS state
    (`Highcharts.charts`) rather than parsing the rendered SVG."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def yearly_series(self) -> dict[str, list[tuple[str, Decimal]]]:
        """Return `{series_name: [(year, value), ...]}` for the yearly bar chart."""
        log.info("Reading yearly chart series from Highcharts state")
        series = yearly_chart_series(dump_charts(self.page))
        log.info("Yearly series series-sizes: %s", {n: len(pts) for n, pts in series.items()})
        return series
