"""Boundary value analysis driven by test-data/boundary_inputs.json."""

from decimal import Decimal

import pytest

from src.utils.emi_formula import calculate_emi
from src.utils.logging_setup import get_logger
from src.utils.test_data import load_test_data


log = get_logger(__name__)

_DATA = load_test_data("boundary_inputs")


@pytest.mark.regression
@pytest.mark.boundary
@pytest.mark.parametrize("case", _DATA["principal"]["cases"])
def test_amount_boundaries(emi_page, case):
    """Setting principal at each boundary should produce an EMI matching
    the formula (or 0 for principal=0, with the slider clamped at 2cr max)."""
    log.info("--- Case: %s (principal=%s) ---", case["description"], case["value"])
    emi_page.amount.set_via_input(case["value"])
    if case["value"] == 0:
        log.info("Principal is 0 — expecting EMI = ₹0 strictly")
        emi_page.results.expect_emi_equals(Decimal("0"))
        return
    effective_principal = min(case["value"], 20_000_000)
    expected = calculate_emi(effective_principal, 9, 240)
    log.info("Computed expected EMI = ₹%s (effective principal=₹%s)", expected, effective_principal)
    emi_page.results.expect_emi_equals(expected)


@pytest.mark.regression
@pytest.mark.boundary
@pytest.mark.parametrize(
    "case",
    [c for c in _DATA["rate"]["cases"] if 5 <= c["value"] <= 20],
)
def test_rate_within_slider_range(emi_page, case):
    """Rates inside the slider's 5–20% band should round-trip to a matching
    EMI on the default loan (₹50,00,000 / 240 months)."""
    rate = case["value"]
    log.info("--- Case: %s (rate=%s%%) ---", case["description"], rate)
    emi_page.rate.set_via_input(rate)
    expected = calculate_emi(5_000_000, rate, 240)
    log.info("Computed expected EMI = ₹%s (principal=₹50,00,000, tenure=240mo)", expected)
    emi_page.results.expect_emi_equals(expected)


@pytest.mark.regression
@pytest.mark.boundary
@pytest.mark.parametrize(
    "case",
    [c for c in _DATA["tenure_years"]["cases"] if c["value"] <= 30],
)
def test_tenure_years_within_range(emi_page, case):
    """Tenure inside the 0–30y slider range, set via the Yr unit, should
    produce an EMI matching the formula evaluated at years × 12 months."""
    log.info("--- Case: %s (tenure=%s years) ---", case["description"], case["value"])
    emi_page.set_tenure_unit("Yr")
    emi_page.tenure.set_via_input(case["value"])
    months = int(case["value"]) * 12
    expected = calculate_emi(5_000_000, 9, months)
    log.info("Computed expected EMI = ₹%s (%d months)", expected, months)
    emi_page.results.expect_emi_equals(expected)


@pytest.mark.regression
@pytest.mark.boundary
@pytest.mark.parametrize(
    "case",
    [c for c in _DATA["tenure_months"]["cases"] if c["value"] <= 360],
)
def test_tenure_months_within_range(emi_page, case):
    """Mirror of `test_tenure_years_within_range` for the Mo unit, exercising
    the 0–360 month slider range (1mo, 360mo)."""
    log.info("--- Case: %s (tenure=%s months) ---", case["description"], case["value"])
    emi_page.set_tenure_unit("Mo")
    emi_page.tenure.set_via_input(case["value"])
    months = int(case["value"])
    expected = calculate_emi(5_000_000, 9, months)
    log.info("Computed expected EMI = ₹%s (%d months)", expected, months)
    emi_page.results.expect_emi_equals(expected)
