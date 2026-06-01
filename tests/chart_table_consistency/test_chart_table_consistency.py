"""The bar chart and the amortization table draw from the same dataset.
For every year, the chart's Principal / Interest / Balance values must
match the corresponding table cells exactly (to the rupee).
"""

from decimal import Decimal, ROUND_HALF_UP

import pytest
from playwright.sync_api import expect

from src.utils.logging_setup import get_logger


log = get_logger(__name__)

# The Highcharts data points are unrounded floats; the on-page table is
# integer rupees. Round the chart values to whole rupees the same way the
# UI displays them (half-up) so we can assert strict equality.
_RUPEE = Decimal("1")


def _round_to_rupee(value: Decimal) -> Decimal:
    """Round a chart Decimal to a whole rupee using ROUND_HALF_UP — the
    same convention the page applies when rendering the table cell."""
    return value.quantize(_RUPEE, rounding=ROUND_HALF_UP)


@pytest.mark.regression
@pytest.mark.cross_feature
def test_chart_year_values_match_table(emi_page):
    """For every year present in both the bar chart's Highcharts state
    and the amortization table, the Principal / Interest / Balance
    values must equal the corresponding table cells exactly once the
    chart's float values are rounded to whole rupees."""
    log.info("Verifying every yearly chart point matches the corresponding table row exactly")
    expect(emi_page.table.year_rows.first).to_be_visible()

    chart_series = emi_page.charts.yearly_series()
    table_rows = emi_page.table.all_years()
    assert chart_series, "expected at least one named series in the yearly chart"
    log.info("Chart series: %s | table years: %d", list(chart_series.keys()), len(table_rows))

    chart_by_year_principal = {int(yr): val for yr, val in chart_series.get("Principal", [])}
    chart_by_year_interest = {int(yr): val for yr, val in chart_series.get("Interest", [])}
    chart_by_year_balance = {int(yr): val for yr, val in chart_series.get("Balance", [])}

    log.info("Comparing %d table years against chart series (exact, no tolerance)", len(table_rows))

    for row in table_rows:
        if row.year in chart_by_year_principal:
            rounded = _round_to_rupee(chart_by_year_principal[row.year])
            assert rounded == row.principal, (
                f"year {row.year} principal mismatch: chart={rounded} table={row.principal}"
            )
        if row.year in chart_by_year_interest:
            rounded = _round_to_rupee(chart_by_year_interest[row.year])
            assert rounded == row.interest, (
                f"year {row.year} interest mismatch: chart={rounded} table={row.interest}"
            )
        if row.year in chart_by_year_balance:
            rounded = _round_to_rupee(chart_by_year_balance[row.year])
            assert rounded == row.balance, (
                f"year {row.year} balance mismatch: chart={rounded} table={row.balance}"
            )
    log.info("All chart year values match the table exactly")
