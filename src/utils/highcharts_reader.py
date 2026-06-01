"""Extract chart data via Highcharts JS state."""

from __future__ import annotations

from decimal import Decimal

from src.utils.logging_setup import get_logger

log = get_logger(__name__)


_DUMP_JS = """
() => {
  if (!window.Highcharts || !Highcharts.charts) return null;
  return Highcharts.charts
    .filter(c => c)
    .map(c => ({
      title: c.title && c.title.textStr ? c.title.textStr : '',
      series: c.series.map(s => ({
        name: s.name,
        type: s.type,
        data: s.points ? s.points.map(p => ({
          category: p.category,
          name: p.name,
          y: p.y,
          percentage: p.percentage,
        })) : [],
      })),
    }));
}
"""


def dump_charts(page) -> list[dict]:
    """Snapshot every Highcharts instance on the page into a JSON-safe dict.
    Raises `RuntimeError` if Highcharts isn't loaded."""
    log.info("Dumping Highcharts JS state from page")
    raw = page.evaluate(_DUMP_JS)
    if raw is None:
        log.error("Highcharts not detected on page")
        raise RuntimeError("Highcharts not detected on page")
    log.info("Dumped %d Highcharts chart(s)", len(raw))
    return raw


def yearly_chart_series(charts: list[dict]) -> dict[str, list[tuple[str, Decimal]]]:
    """Pick the first column/bar/line chart and return its series as
    `{series_name: [(category, y_value), ...]}`."""
    log.info("Extracting yearly chart series from %d charts", len(charts))
    for chart in charts:
        types = {s["type"] for s in chart.get("series") or []}
        if not ({"column", "line", "spline", "bar"} & types):
            continue
        out: dict[str, list[tuple[str, Decimal]]] = {}
        for series in chart["series"]:
            pairs = [
                (str(p.get("category") or p.get("name") or ""), Decimal(str(p["y"])))
                for p in series["data"]
                if p.get("y") is not None
            ]
            if pairs:
                out[series["name"]] = pairs
        if out:
            log.info("Found yearly series: %s", list(out.keys()))
            return out
    log.info("No yearly chart series found")
    return {}
