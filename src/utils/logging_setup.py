"""Project logger factory.

We don't configure handlers here — pytest owns that via `log_cli_*` and
`log_file_*` in pytest.ini. This module exists so every module gets a
namespaced logger with one consistent prefix (`emi.*`) instead of the
default `__name__` (which becomes `src.pages.components.loan_slider` —
noisy in CI logs).
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return `emi.<short-name>` logger.

    `short-name` strips the leading `src.` package prefix and keeps the rest
    so a slider log line reads `emi.pages.components.loan_slider` rather
    than `src.pages.components.loan_slider`.
    """
    if name == "__main__":
        return logging.getLogger("emi")
    cleaned = name.removeprefix("src.")
    return logging.getLogger(f"emi.{cleaned}")
