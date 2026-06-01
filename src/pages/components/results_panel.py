"""Reads the EMI tile and provides Playwright-backed assertion helpers."""

from __future__ import annotations

from decimal import Decimal

from playwright.sync_api import Page, expect

from src.utils.inr_format import parse_inr
from src.utils.logging_setup import get_logger

log = get_logger(__name__)


class ResultsPanel:
    """Reads the EMI / Total Interest / Total Payment tiles and exposes
    Playwright-backed `expect_*` helpers that poll with auto-retry."""

    EMI_SELECTOR = "#emiamount p span"
    TOTAL_INTEREST_SELECTOR = "#emitotalinterest p span"
    TOTAL_PAYMENT_SELECTOR = "#emitotalamount p span"

    def __init__(self, page: Page) -> None:
        """Bind to the three results-panel tile spans."""
        self.page = page
        self.emi_value = page.locator(self.EMI_SELECTOR)
        self.total_interest_value = page.locator(self.TOTAL_INTEREST_SELECTOR)
        self.total_payment_value = page.locator(self.TOTAL_PAYMENT_SELECTOR)

    def emi(self) -> Decimal:
        """Return the currently displayed EMI as a `Decimal` (₹-stripped)."""
        value = parse_inr(self.emi_value.inner_text())
        log.info("Read EMI from page: %s", value)
        return value

    def total_interest(self) -> Decimal:
        """Return the currently displayed Total Interest tile as a `Decimal`."""
        value = parse_inr(self.total_interest_value.inner_text())
        log.info("Read Total Interest from page: %s", value)
        return value

    def total_payment(self) -> Decimal:
        """Return the currently displayed Total Payment tile as a `Decimal`."""
        value = parse_inr(self.total_payment_value.inner_text())
        log.info("Read Total Payment from page: %s", value)
        return value

    def expect_emi_close_to(
        self,
        expected: Decimal,
        tolerance: Decimal,
        *,
        timeout_ms: int = 5_000,
    ) -> Decimal:
        """Polls the EMI tile via Playwright until |actual - expected| ≤ tolerance.

        Uses `expect()` for the visibility precondition and `wait_for_function`
        for the numeric tolerance check (so it benefits from Playwright's
        auto-retry rather than a one-shot Python `assert`).
        """
        log.info(
            "Verifying EMI within ±₹%s of expected ₹%s (timeout=%dms)",
            tolerance, expected, timeout_ms,
        )
        expect(self.emi_value).to_be_visible()
        try:
            self.page.wait_for_function(
                """({selector, expected, tolerance}) => {
                    const el = document.querySelector(selector);
                    if (!el) return false;
                    const n = Number(el.innerText.replace(/[^0-9.\\-]/g, ''));
                    return Number.isFinite(n) && Math.abs(n - expected) <= tolerance;
                }""",
                arg={
                    "selector": self.EMI_SELECTOR,
                    "expected": float(expected),
                    "tolerance": float(tolerance),
                },
                timeout=timeout_ms,
            )
        except Exception as exc:
            actual = parse_inr(self.emi_value.inner_text())
            log.error(
                "✗ EMI verification FAILED: actual=₹%s expected=₹%s diff=₹%s (tolerance ±₹%s)",
                actual, expected, abs(actual - expected), tolerance,
            )
            raise AssertionError(
                f"EMI not within ±₹{tolerance} of ₹{expected}: got ₹{actual}"
            ) from exc

        actual = parse_inr(self.emi_value.inner_text())
        log.info(
            "✓ EMI verified: actual=₹%s expected=₹%s diff=₹%s",
            actual, expected, abs(actual - expected),
        )
        return actual

    def expect_emi_equals(self, expected: Decimal) -> Decimal:
        """Strict equality (no tolerance) — for documented defaults like ₹44,986."""
        log.info("Verifying EMI strictly equals ₹%s", expected)
        return self.expect_emi_close_to(expected, Decimal("0"))
