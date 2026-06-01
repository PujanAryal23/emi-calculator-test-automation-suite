"""Parse Indian Rupee strings (₹1,07,96,711 — 2-2-3 lakh/crore grouping)."""

from __future__ import annotations

import re
from decimal import Decimal

from src.utils.logging_setup import get_logger

log = get_logger(__name__)

_NON_DIGITS = re.compile(r"[^\d\-.]")


def parse_inr(text: str) -> Decimal:
    """Strip ₹/commas/whitespace from `text` and return the numeric value.
    Raises `ValueError` if `text` has no parseable digits."""
    stripped = _NON_DIGITS.sub("", text)
    if stripped in ("", "-", ".", "-."):
        log.error("Cannot parse INR — no numeric content in %r", text)
        raise ValueError(f"no numeric content in {text!r}")
    value = Decimal(stripped)
    log.debug("parse_inr(%r) → %s", text, value)
    return value


def parse_percent(text: str) -> Decimal:
    """Strip the percent sign and surrounding whitespace, return as `Decimal`."""
    value = Decimal(text.replace("%", "").strip())
    log.debug("parse_percent(%r) → %s", text, value)
    return value
