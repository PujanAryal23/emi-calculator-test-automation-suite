"""Loader for JSON fixtures under <repo-root>/test-data/.

Centralizes the path math so individual tests don't repeat
`Path(__file__).resolve().parents[N] / "test-data" / ...`.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.utils.logging_setup import get_logger

log = get_logger(__name__)

_TEST_DATA_DIR = Path(__file__).resolve().parents[2] / "test-data"


def load_test_data(name: str) -> dict:
    """Load a JSON fixture by filename (with or without `.json` suffix)."""
    filename = name if name.endswith(".json") else f"{name}.json"
    path = _TEST_DATA_DIR / filename
    log.info("Loading test data: %s", path)
    data = json.loads(path.read_text())
    log.info("Loaded test data %s (%d top-level keys)", filename, len(data))
    return data
