"""Reference EMI math — Decimal only, never float."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from src.utils.logging_setup import get_logger

log = get_logger(__name__)


def _d(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def monthly_rate(annual_rate_percent) -> Decimal:
    """Convert an annual percentage rate into a per-month decimal multiplier."""
    return _d(annual_rate_percent) / Decimal("12") / Decimal("100")


def calculate_emi(principal, annual_rate_percent, tenure_months) -> Decimal:
    """Reference EMI = P·r·(1+r)^n / ((1+r)^n − 1), rounded to nearest rupee.
    Returns 0 if principal ≤ 0; raises `ValueError` if tenure ≤ 0."""
    p = _d(principal)
    n = int(tenure_months)
    log.info("Calculating EMI: principal=₹%s rate=%s%% tenure=%d months", p, annual_rate_percent, n)
    if n <= 0:
        raise ValueError("tenure_months must be positive")
    if p <= 0:
        log.info("Principal ≤ 0 → EMI = ₹0")
        return Decimal("0")

    r = monthly_rate(annual_rate_percent)
    if r == 0:
        # Straight-line repayment — formula divides by zero otherwise.
        emi = p / Decimal(n)
    else:
        growth = (Decimal(1) + r) ** n
        emi = p * r * growth / (growth - Decimal(1))
    result = emi.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    log.info("EMI calculated: ₹%s", result)
    return result
