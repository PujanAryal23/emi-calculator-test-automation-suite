"""Yearly amortization table reader, with on-demand monthly expansion."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from src.utils.inr_format import parse_inr, parse_percent
from src.utils.logging_setup import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class YearRow:
    """One parsed row from the yearly amortization table."""

    year: int
    principal: Decimal
    interest: Decimal
    total_payment: Decimal
    balance: Decimal
    loan_paid_pct: Decimal


@dataclass(frozen=True)
class MonthRow:
    """One parsed row from an expanded year's monthly sub-table.

    `month_label` is just the month name as shown on the page ("Jan", "Feb"
    …) — the page omits the year inside an expanded year section."""

    month_label: str
    principal: Decimal
    interest: Decimal
    total_payment: Decimal
    balance: Decimal
    loan_paid_pct: Decimal


class AmortizationTable:
    """Reader for the page's yearly amortization breakdown table."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.year_rows = page.locator("tr.yearlypaymentdetails")

    def all_years(self) -> list[YearRow]:
        """Parse every yearly row currently rendered in the table."""
        count = self.year_rows.count()
        log.info("Reading all %d year rows from amortization table", count)
        rows = [self._parse_year_row(self.year_rows.nth(i)) for i in range(count)]
        log.info("Parsed %d year rows from table", len(rows))
        return rows

    def expand_year(self, year: int) -> list[MonthRow]:
        """Click the year header to reveal its monthly sub-table, then
        parse every monthly row inside it. Returns rows in calendar order."""
        log.info("Expanding year %d to read monthly rows", year)
        self.page.locator(f"#year{year}").click()
        # The monthly sub-table is the first sibling <tr> with the
        # `monthlypaymentdetails` class immediately after the year header.
        monthly_container = self.page.locator(f"#year{year}").locator(
            "xpath=ancestor::tr/following-sibling::tr[contains(@class,'monthlypaymentdetails')][1]"
        )
        expect(monthly_container).to_be_visible()
        rows = monthly_container.locator("table tr")
        parsed: list[MonthRow] = []
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td")
            if cells.count() < 6:
                continue  # skip header / spacer rows
            parsed.append(MonthRow(
                month_label=_text(cells.nth(0)),
                principal=parse_inr(_text(cells.nth(1))),
                interest=parse_inr(_text(cells.nth(2))),
                total_payment=parse_inr(_text(cells.nth(3))),
                balance=parse_inr(_text(cells.nth(4))),
                loan_paid_pct=parse_percent(_text(cells.nth(5))),
            ))
        log.info("Year %d expanded: %d monthly rows parsed", year, len(parsed))
        return parsed

    def all_monthly_rows(self) -> list[MonthRow]:
        """Expand every year and return all monthly rows concatenated in
        chronological order. Slower than `all_years()` (one click + parse
        per year) but yields per-month resolution for exact reconciliation."""
        log.info("Reading every monthly row by expanding all years in order")
        monthly: list[MonthRow] = []
        for year_row in self.all_years():
            monthly.extend(self.expand_year(year_row.year))
        log.info("Collected %d monthly rows across all years", len(monthly))
        return monthly

    def _parse_year_row(self, row: Locator) -> YearRow:
        cells = row.locator("td")
        if cells.count() < 6:
            raise ValueError(f"unexpected year row layout: {cells.count()} cells")
        return YearRow(
            year=int(_text(row.locator("td.paymentyear"))),
            principal=parse_inr(_text(cells.nth(1))),
            interest=parse_inr(_text(cells.nth(2))),
            total_payment=parse_inr(_text(cells.nth(3))),
            balance=parse_inr(_text(cells.nth(4))),
            loan_paid_pct=parse_percent(_text(cells.nth(5))),
        )


def _text(loc: Locator) -> str:
    return loc.inner_text().replace("\xa0", " ").strip()
