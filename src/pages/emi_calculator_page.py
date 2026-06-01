"""Top-level page object for the EMI calculator widget."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from playwright.sync_api import Page, expect

from src.pages.components.amortization_table import AmortizationTable
from src.pages.components.breakup_chart import BreakupChart
from src.pages.components.loan_slider import LoanSlider
from src.pages.components.results_panel import ResultsPanel
from src.utils.logging_setup import get_logger

log = get_logger(__name__)


class EmiCalculatorPage:
    """Top-level page object composing the amount / rate / tenure inputs,
    results panel, chart, and amortization table for emicalculator.net."""

    EMI_TILE = "#emiamount p span"
    YR_RADIO = "#loanyears"
    MO_RADIO = "#loanmonths"

    def __init__(self, page: Page, base_url: str) -> None:
        """Wire up sub-components against `page` rooted at `base_url`."""
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.amount = LoanSlider(page, label="Home Loan Amount")
        self.rate = LoanSlider(page, label="Interest Rate")
        self.tenure = LoanSlider(page, label="Loan Tenure")
        self.results = ResultsPanel(page)
        self.charts = BreakupChart(page)
        self.table = AmortizationTable(page)

    def open(self) -> "EmiCalculatorPage":
        """Navigate to the calculator and wait for the EMI tile to render."""
        log.info("Opening calculator page: %s", self.base_url)
        self.page.goto(self.base_url, wait_until="domcontentloaded")
        expect(self.page.locator(self.EMI_TILE)).to_be_visible()
        log.info("Calculator ready (EMI tile visible)")
        return self

    def current_tenure_months(self) -> int:
        """Return the tenure input as a count of months regardless of which
        unit (Yr / Mo) the toggle is currently set to."""
        is_years = self.page.locator(self.YR_RADIO).is_checked()
        raw = self.tenure.read_input()
        months = int(raw) * 12 if is_years else int(raw)
        log.info("Current tenure (months): %d (unit=%s, input=%s)", months, "Yr" if is_years else "Mo", raw)
        return months

    def set_tenure_unit(self, unit: Literal["Yr", "Mo"]) -> None:
        """Toggle the Yr/Mo radio and wait for the radio to register checked."""
        log.info("Setting tenure unit to: %s", unit)
        self.page.get_by_text(unit, exact=True).click()
        radio = self.page.locator(self.YR_RADIO if unit == "Yr" else self.MO_RADIO)
        expect(radio).to_be_checked()
        log.info("Tenure unit set and confirmed: %s", unit)

    def configure(
        self,
        principal=None,
        rate=None,
        tenure_years=None,
        tenure_months=None,
    ) -> None:
        """Set one or more inputs in a single call; only non-`None` args apply.
        `tenure_months` wins over `tenure_years` when both are provided."""
        if principal is None and rate is None and tenure_years is None and tenure_months is None:
            raise ValueError("configure() called with no arguments")
        log.info(
            "configure: principal=%s rate=%s tenure_years=%s tenure_months=%s",
            principal, rate, tenure_years, tenure_months,
        )
        if principal is not None:
            self.amount.set_via_input(principal)
        if rate is not None:
            self.rate.set_via_input(rate)
        if tenure_months is not None:
            self.set_tenure_unit("Mo")
            self.tenure.set_via_input(tenure_months)
        elif tenure_years is not None:
            self.set_tenure_unit("Yr")
            self.tenure.set_via_input(tenure_years)

    def download_excel(self, target_dir: Path) -> Path:
        """Click the Excel download button and save the file under `target_dir`.
        Returns the absolute path of the saved workbook."""
        target_dir.mkdir(parents=True, exist_ok=True)
        log.info("Triggering Excel download → %s", target_dir)
        with self.page.expect_download() as info:
            self.page.get_by_role("button", name="Download Excel").click()
        download = info.value
        out = target_dir / (download.suggested_filename or "loan_amortization_schedule.xlsx")
        download.save_as(out)
        log.info("Downloaded Excel: %s (%d bytes)", out, out.stat().st_size)
        return out
