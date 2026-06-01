"""Root pytest configuration.

`pytest-playwright` already provides `page`, `browser`, `context`. We add a
ready-to-use `emi_page` that lands on the calculator and a failure-time
screenshot hook.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.config.settings import SETTINGS  # noqa: E402
from src.pages.emi_calculator_page import EmiCalculatorPage  # noqa: E402
from src.utils.logging_setup import get_logger  # noqa: E402

log = get_logger(__name__)


@pytest.fixture(scope="session")
def base_url(pytestconfig) -> str:
    cli = pytestconfig.getoption("--base-url", default=None)
    return cli or SETTINGS.base_url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "accept_downloads": True,
        "locale": "en-IN",
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, pytestconfig):
    # `--headed` on the CLI always wins; otherwise honour HEADLESS env (default
    # is headed locally, headless in CI via the workflow's HEADLESS=true).
    headed_flag = pytestconfig.getoption("--headed", default=False)
    return {
        **browser_type_launch_args,
        "headless": False if headed_flag else SETTINGS.headless,
        "slow_mo": SETTINGS.slow_mo_ms,
    }


def pytest_configure(config):
    # Expand BROWSERS env into pytest-playwright's --browser, but only if the
    # user didn't already pass --browser on the CLI (CLI always wins).
    cli_browsers = list(config.getoption("--browser", default=[]) or [])
    if not cli_browsers:
        for browser in SETTINGS.browsers:
            if browser not in config.option.browser:
                config.option.browser.append(browser)


def pytest_sessionstart(session):
    selected = list(session.config.option.browser) or list(SETTINGS.browsers)
    headed_flag = session.config.getoption("--headed", default=False)
    headless = False if headed_flag else SETTINGS.headless
    log.info(
        "session config: base_url=%s browsers=%s headless=%s slow_mo=%dms timeout=%dms",
        SETTINGS.base_url,
        ",".join(selected),
        headless,
        SETTINGS.slow_mo_ms,
        SETTINGS.default_timeout_ms,
    )


@pytest.fixture
def emi_page(page, base_url) -> EmiCalculatorPage:
    page.set_default_timeout(SETTINGS.default_timeout_ms)
    calculator = EmiCalculatorPage(page, base_url)
    calculator.open()
    return calculator


_test_started_at: dict[str, float] = {}


def pytest_runtest_logstart(nodeid):
    _test_started_at[nodeid] = time.monotonic()
    log.info("▶ start  %s", nodeid)


def pytest_runtest_logfinish(nodeid):
    started = _test_started_at.pop(nodeid, None)
    elapsed_ms = int((time.monotonic() - started) * 1000) if started else 0
    log.info("◼ finish %s  (%dms)", nodeid, elapsed_ms)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()
    if result.when != "call" or not result.failed:
        return

    if call.excinfo is not None:
        log.error(
            "✗ FAIL %s — %s: %s",
            item.nodeid,
            call.excinfo.typename,
            call.excinfo.value,
        )

    page = item.funcargs.get("page")
    if page is None:
        return
    artifacts = Path("test-results") / item.nodeid.replace("/", "_").replace("::", "_")
    artifacts.mkdir(parents=True, exist_ok=True)
    screenshot_path = artifacts / "failure.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        log.info("screenshot saved: %s", screenshot_path)
    except Exception as exc:
        log.warning("failed to capture failure screenshot for %s: %s", item.nodeid, exc)
