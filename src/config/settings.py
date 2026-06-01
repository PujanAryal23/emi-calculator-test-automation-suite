"""Environment-driven settings, loaded once per session from .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env", override=False)


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


_VALID_BROWSERS = ("chromium", "firefox", "webkit")


def _browsers(default: tuple[str, ...] = ("chromium",)) -> tuple[str, ...]:
    # BROWSERS (plural) wins over BROWSER (singular) for back-compat.
    raw = os.getenv("BROWSERS") or os.getenv("BROWSER") or ""
    parsed = tuple(b.strip().lower() for b in raw.split(",") if b.strip())
    if not parsed:
        return default
    unknown = [b for b in parsed if b not in _VALID_BROWSERS]
    if unknown:
        raise ValueError(
            f"Unknown browser(s) {unknown!r} in BROWSERS env. "
            f"Valid: {_VALID_BROWSERS}"
        )
    return parsed


@dataclass(frozen=True)
class Settings:
    base_url: str
    browsers: tuple[str, ...]
    headless: bool
    slow_mo_ms: int
    default_timeout_ms: int
    download_dir: Path

    @classmethod
    def load(cls) -> "Settings":
        download_dir = Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()
        download_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            base_url=os.getenv("BASE_URL", "https://emicalculator.net/"),
            browsers=_browsers(),
            headless=_bool("HEADLESS", False),
            slow_mo_ms=_int("SLOW_MO_MS", 0),
            default_timeout_ms=_int("DEFAULT_TIMEOUT_MS", 15000),
            download_dir=download_dir,
        )


SETTINGS = Settings.load()

# Defer the import so we don't form a cycle with logging_setup.
from src.utils.logging_setup import get_logger  # noqa: E402

get_logger(__name__).debug(
    "settings loaded: base_url=%s browsers=%s headless=%s slow_mo=%dms timeout=%dms",
    SETTINGS.base_url,
    SETTINGS.browsers,
    SETTINGS.headless,
    SETTINGS.slow_mo_ms,
    SETTINGS.default_timeout_ms,
)
