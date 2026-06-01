"""Text input wrapper for the loan amount / rate / tenure fields.

Setting the input fires the page's recalculation; we wait for the EMI tile
to update before returning.
"""

from __future__ import annotations

from decimal import Decimal

from playwright.sync_api import Page, expect

from src.utils.inr_format import parse_inr
from src.utils.logging_setup import get_logger

log = get_logger(__name__)


class LoanSlider:
    """Wrapper for one of the three labeled inputs (Amount, Rate, Tenure).
    Setting the input triggers the page's recalculation."""

    def __init__(self, page: Page, label: str) -> None:
        """Resolve the input by its visible `<label>` text via `get_by_label`."""
        self.page = page
        self.label = label
        self.input = page.get_by_label(label, exact=True)

    def read_input(self) -> Decimal:
        """Return the input's current value as a `Decimal`, stripping any
        INR formatting (`₹`, commas, whitespace)."""
        value = parse_inr(self.input.input_value())
        log.info("Read %s input value: %s", self.label, value)
        return value

    def set_via_input(self, value) -> None:
        """Click, fill, and blur the input, then wait for the EMI tile to refresh."""
        log.info("Setting %s = %s (via input field)", self.label, value)
        prior = self._emi_text()
        self.input.click()
        self.input.fill(str(value))
        self.input.blur()
        self._wait_for_recalc(prior)
        log.info("Recalculation settled after setting %s = %s", self.label, value)

    def _emi_text(self) -> str:
        return self.page.locator("#emiamount p span").inner_text()

    def _wait_for_recalc(self, prior: str) -> None:
        try:
            expect(self.page.locator("#emiamount p span")).not_to_have_text(
                prior, timeout=500
            )
        except AssertionError:
            pass
        self.page.wait_for_timeout(50)
