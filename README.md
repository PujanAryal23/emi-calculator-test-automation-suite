# EMI Calculator — QA Automation Suite

Automated test framework for the Home Loan EMI Calculator at
[emicalculator.net](https://emicalculator.net/). Built with Playwright +
Python + pytest. Targets the Home Loan tab; covers EMI calculation parity,
slider boundary handling, chart/table consistency, and Excel-export parity.

## What's in here

```
.
├── conftest.py                  # root pytest config: fixtures, browser context, base URL
├── pyproject.toml               # dependencies
├── pytest.ini                   # markers, reporter, addopts, logging config
├── src/
│   ├── config/settings.py       # .env-driven settings (one place for all knobs)
│   ├── pages/                   # POM — one component per testable concern
│   │   ├── emi_calculator_page.py
│   │   └── components/
│   │       ├── loan_slider.py        # text-input wrapper + recalc-wait
│   │       ├── results_panel.py      # EMI tile + expect_emi_close_to / expect_emi_equals
│   │       ├── breakup_chart.py      # yearly bar chart via Highcharts JS state
│   │       └── amortization_table.py # yearly amortization rows
│   └── utils/
│       ├── emi_formula.py       # the calculation oracle (Decimal, not float)
│       ├── inr_format.py        # Indian-rupee 2-2-3 grouping parser
│       ├── excel_validator.py   # openpyxl wrapper for the downloaded workbook
│       ├── highcharts_reader.py # reads chart data via Highcharts JS state, not SVG
│       ├── test_data.py         # load_test_data() helper for test-data/*.json fixtures
│       └── logging_setup.py     # namespaced `emi.*` logger factory
├── tests/
│   ├── slider_values/                  # @regression @boundary — slider extremes & ranges
│   ├── emi_calculation/                # @regression @calculation — formula parity
│   ├── chart_table_consistency/        # @regression @cross_feature — chart ↔ table parity
│   └── excel_file_checks/              # @smoke + @regression @cross_feature — Excel export:
│                                       #   loan details, payment summary, monthly schedule
├── test-data/                          # JSON fixtures, loaded via load_test_data("name")
│   ├── boundary_inputs.json            # principal/rate/tenure boundary cases
│   └── emi_calculation_inputs.json     # scenarios for site-vs-formula parity
└── .github/workflows/tests.yml  # smoke on PR, sanity on merge, regression nightly
```

## Architecture: Page Object Model

The suite is built on a classic **Page Object Model (POM)** layout, with
four concentric layers of responsibility. Each layer knows only about the
one beneath it, so a markup change in the AUT ripples through exactly one
file instead of every test.

```
┌─────────────────────────────────────────────────────────────┐
│  tests/                                                     │   intent
│    "what should the user observe?"                          │   (assertions,
│    e.g. test_site_emi_matches_formula                       │    parametrize)
└──────────────────┬──────────────────────────────────────────┘
                   │ uses fixtures + page objects
┌──────────────────▼──────────────────────────────────────────┐
│  src/pages/emi_calculator_page.py                           │   workflows
│    "how does the user drive the page?"                      │   (configure,
│    EmiCalculatorPage — composes the sub-components below    │    open, download)
└──────────────────┬──────────────────────────────────────────┘
                   │ delegates to components
┌──────────────────▼──────────────────────────────────────────┐
│  src/pages/components/                                      │   widgets
│    LoanSlider · ResultsPanel · BreakupChart ·               │   (one class
│    AmortizationTable                                        │    per widget)
└──────────────────┬──────────────────────────────────────────┘
                   │ uses utilities
┌──────────────────▼──────────────────────────────────────────┐
│  src/utils/                                                 │   primitives
│    emi_formula · inr_format · excel_validator ·             │   (pure
│    highcharts_reader · logging_setup · test_data            │    functions)
└─────────────────────────────────────────────────────────────┘
```

### Responsibilities by layer

| Layer | What lives here | What stays out |
|---|---|---|
| **Tests** | Scenario setup, parametrize data, assertions that express user intent | Selectors, browser interactions, click flow |
| **Top-level page** (`EmiCalculatorPage`) | Multi-component workflows (`configure`, `download_excel`, `set_tenure_unit`), URL/loading | Per-widget click/parse details |
| **Components** (`LoanSlider`, `ResultsPanel`, `BreakupChart`, `AmortizationTable`) | Locators, click/fill, parsing, `expect_*` helpers for the one widget they own | Multi-widget orchestration; the EMI formula |
| **Utils** | Pure Python — math oracle, INR/percent parsing, Highcharts/Excel readers, logger factory, JSON test-data loader | Anything Playwright-specific |

### Why this shape

- **Tests read like specs.** `emi_page.configure(principal=…, rate=…, tenure_years=…)` then `emi_page.results.expect_emi_close_to(expected, ±tol)` — no selectors, no clicks, no waits. A test reads the same whether the AUT swaps its DOM, its slider library, or its rounding mode.
- **One place to fix a markup change.** If the EMI tile moves from `#emiamount p span` to `[data-testid="emi"]`, only `ResultsPanel.EMI_SELECTOR` changes. Tests and workflows are untouched.
- **Components compose, not inherit.** `EmiCalculatorPage` *holds* a `LoanSlider` for each input rather than subclassing a base page. New widgets plug in as new attributes, no class hierarchy to refactor.
- **Pure utilities are unit-testable in isolation.** `calculate_emi`, `parse_inr`, `aggregate_to_yearly` have no Playwright dependency — they can be exercised without a browser, and they're the same code the UI tests use as their oracle.
- **`expect_*` helpers replace `assert` for UI state.** Each component exposes Playwright-`expect()`-backed assertions (`expect_emi_close_to`, etc.) that auto-retry until the predicate holds or the timeout fires — no `sleep()`, no flaky waits.

### A test's call path

A single line like `emi_page.amount.set_via_input(5_000_000)` walks the layers:

```
test (tests/.../*.py)
  └─ EmiCalculatorPage.amount                  ← top-level page object
       └─ LoanSlider.set_via_input(value)      ← widget component
            ├─ self.input.fill(...)            ← Playwright Locator
            └─ self._wait_for_recalc(prior)    ← Playwright expect() retry
                 └─ logs via emi.pages.components.loan_slider
                                               ← utils/logging_setup.get_logger
```

Each transition is one method call; each layer logs its own step, so
`reports/pytest.log` reads as a narrative top-to-bottom.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium firefox webkit   # install whichever you'll use
cp .env.example .env       # edit if you need to override defaults
```

## Run tests

Local default is **headed on chromium**, so a plain `pytest` opens a real
browser window. CI sets `HEADLESS=true` to override.

```bash
# Everything
pytest

# Just one suite
pytest tests/slider_values
pytest tests/emi_calculation
pytest tests/chart_table_consistency
pytest tests/excel_file_checks

# A single parametrized case
pytest tests/slider_values/test_boundaries.py::test_rate_within_slider_range -k "lower"

# Smoke (gates a PR) — currently the Excel-download smoke check
pytest -m smoke

# Full regression
pytest -m regression

# By feature marker
pytest -m boundary
pytest -m calculation
pytest -m cross_feature

# Parallel
pytest -m regression -n 4
```

### Headed vs headless

| You want | How |
|---|---|
| Headed (default) | `pytest -m smoke` |
| Headed via flag | `pytest --headed -m smoke` |
| Headless (one run) | `HEADLESS=true pytest -m smoke` |
| Headless (persistent) | set `HEADLESS=true` in `.env` |
| Slow down for eyeballs | `SLOW_MO_MS=400 pytest --headed` |

`--headed` on the CLI always wins over the `HEADLESS` env var. CI workflows
set `HEADLESS=true` on every browser job so headed-default doesn't crash on
runners without a display server.

### Cross-browser

Each test runs once per browser listed. Set browsers via env var **or** via
the standard pytest-playwright `--browser` flag (CLI wins):

```bash
# Run on Firefox only
BROWSERS=firefox pytest -m smoke

# Fan out across all three engines in one invocation
BROWSERS=chromium,firefox,webkit pytest -m smoke

# Same thing via CLI (overrides BROWSERS)
pytest -m smoke --browser chromium --browser firefox --browser webkit
```

Valid browsers: `chromium`, `firefox`, `webkit`. Each must be installed via
`playwright install <browser>` first.

The pytest-html report at `reports/report.html` includes the browser name
in each test's node id (e.g. `test_rate_within_slider_range[chromium-lower slider bound]`),
so you can spot browser-specific failures at a glance.

Reports land in `reports/report.html` (single-file HTML) and screenshots on
failure go to `test-results/`.

## Logging

The suite ships with structured logging wired through pytest's built-in
log machinery — nothing extra to set up. Every page object, component, and
utility uses `src.utils.logging_setup.get_logger(__name__)`, which returns
a logger namespaced under `emi.*` (e.g. `emi.pages.components.loan_slider`).

**Two sinks, configured in `pytest.ini`:**

| Sink | Level | Format | Where |
|---|---|---|---|
| Terminal (live) | `INFO` | `HH:MM:SS [LEVEL] emi.<module> — msg` | stderr, while tests run |
| File | `DEBUG` | full timestamp + line number | `reports/pytest.log` (replaced each run) |

**A typical test run reads like a narrative:**

```
17:33:40 [INFO ] emi.conftest — session config: base_url=https://emicalculator.net/ browsers=chromium headless=False slow_mo=0ms timeout=15000ms
17:33:40 [INFO ] emi.conftest — ▶ start  tests/slider_values/test_boundaries.py::test_rate_within_slider_range[chromium-lower slider bound]
17:33:42 [INFO ] emi.pages.emi_calculator_page — Opening calculator page: https://emicalculator.net
17:33:49 [INFO ] emi.pages.emi_calculator_page — Calculator ready (EMI tile visible)
17:33:49 [INFO ] emi.tests.slider_values.test_boundaries — --- Case: lower slider bound (rate=5%) ---
17:33:49 [INFO ] emi.pages.components.loan_slider — Setting loaninterest = 5 (via input field)
17:33:49 [INFO ] emi.pages.components.loan_slider — Recalculation settled after setting loaninterest = 5
17:33:49 [INFO ] emi.utils.emi_formula — Calculating EMI: principal=₹5000000 rate=5% tenure=240 months
17:33:49 [INFO ] emi.utils.emi_formula — EMI calculated: ₹32998
17:33:49 [INFO ] emi.tests.slider_values.test_boundaries — Computed expected EMI = ₹32998 (principal=₹50,00,000, tenure=240mo)
17:33:49 [INFO ] emi.pages.components.results_panel — Verifying EMI strictly equals ₹32998
17:33:49 [INFO ] emi.pages.components.results_panel — Verifying EMI within ±₹0 of expected ₹32998 (timeout=5000ms)
17:33:49 [INFO ] emi.pages.components.results_panel — ✓ EMI verified: actual=₹32998 expected=₹32998 diff=₹0
17:33:50 [INFO ] emi.conftest — ◼ finish tests/slider_values/test_boundaries.py::test_rate_within_slider_range[chromium-lower slider bound]  (9465ms)
```

Each test logs `▶ start` / `◼ finish` with elapsed milliseconds. On a
failure you also get `✗ FAIL <nodeid> — <ExceptionClass>: <message>` plus a
`screenshot saved: …` line pointing at the artifact under `test-results/`.

**Where the logs come from:** logging lives in the page objects and helpers,
not the tests. A test reads as a narrative because each step (setting an
input, computing the oracle value, verifying the EMI tile) emits its own
INFO line from the layer that owns the work. Tests only log their own
high-level commentary ("Computed expected EMI = ...", "--- Case: ... ---").

**Adjusting the level:**

```bash
# Turn the terminal up to DEBUG for one run (slider sets, chart dumps, etc.)
pytest -m regression --log-cli-level=DEBUG

# Quiet everything down to warnings only
pytest -m smoke --log-cli-level=WARNING

# Send the file log somewhere else
pytest -m smoke --log-file=/tmp/run.log --log-file-level=DEBUG
```

The file log captures `DEBUG` regardless of the terminal level, so any
failure can be replayed end-to-end from `reports/pytest.log` even when the
CI terminal only showed `INFO` lines.

**Using the logger in new code:**

```python
from src.utils.logging_setup import get_logger

log = get_logger(__name__)

def open_settings_modal(self):
    log.info("Opening settings modal")
    ...
    log.debug("modal locator: %s", self._modal_selector)
```

Prefer `log.info` for user-visible state changes (navigation, downloads,
configuration, verification outcomes), `log.debug` for fine-grained
interactions (parsed values, low-level locator events), and
`log.warning`/`log.error` only when something the test relies on misbehaves.

## Locator strategy

Page objects prefer Playwright's semantic locators (`get_by_label`,
`get_by_role`, `get_by_text`) over CSS selectors. They survive markup
churn better and read like the user's mental model of the page:

| Element | Locator |
|---|---|
| Amount input | `page.get_by_label("Home Loan Amount", exact=True)` |
| Rate input | `page.get_by_label("Interest Rate", exact=True)` |
| Tenure input | `page.get_by_label("Loan Tenure", exact=True)` |
| Yr / Mo toggle | `page.get_by_text("Yr", exact=True)` / `"Mo"` |
| Download Excel | `page.get_by_role("button", name="Download Excel")` |

CSS selectors are kept only where the AUT exposes no semantic anchor:

| Element | Why CSS |
|---|---|
| `#emiamount p span` (EMI tile) | display span, no role/label |
| `tr.yearlypaymentdetails` (year rows) | structural class-based filtering of `<tr>` rows |
| `td.paymentyear`, `td:nth(...)` | column-positional cell access |
| `#loanyears` / `#loanmonths` (radios) | wrapping `<label>`s carry no `for` attribute, so `get_by_label` doesn't apply |

If new selectors are added, prefer `get_by_role` → `get_by_label` →
`get_by_text` → `get_by_test_id` → CSS, in that order. Reach for CSS only
when the markup genuinely has no semantic hook.

## Test data

Data-driven cases live in `test-data/` at the repo root and load through the
`load_test_data(name)` helper in `src/utils/test_data.py`:

```python
from src.utils.test_data import load_test_data

_DATA = load_test_data("boundary_inputs")   # loads test-data/boundary_inputs.json
```

| File | Used by | Shape |
|---|---|---|
| `boundary_inputs.json` | `tests/slider_values/test_boundaries.py` | `{principal, rate, tenure_years, tenure_months}.cases[]` — each with `value` + `description` |
| `emi_calculation_inputs.json` | `tests/emi_calculation/test_emi_against_formula.py` | Five categorised arrays of scenarios — `common_scenarios`, `boundary_principal`, `boundary_rate`, `boundary_tenure_months`, `equivalence_partitions` — each scenario carrying `principal`, `rate`, `description`, and either `tenure_years` or `tenure_months`. All five are flattened into a single parametrized test |

To add a case: edit the JSON; pytest re-parametrizes on next run. Each
case carries a `description` field which the test logs in the body — that
narrative line is the source of truth for "which case is this", rather
than the auto-generated pytest node id (`case0`, `scenario3`, …).


## Regression strategy for EMI calculation logic

The EMI calculator is a **logic-first product**: every output (EMI,
total interest, total payment, amortization rows) is a deterministic
function of three inputs (principal, rate, tenure). The suite is
therefore designed as a **data-driven regression**.

The reference formula:

```
EMI = P · r · (1 + r)^n  /  ((1 + r)^n − 1)

  P = principal,  r = monthly rate (= annual_rate / 12 / 100),  n = months
```

When `r = 0` (zero-interest), the formula divides by zero — the
implementation must fall back to **straight-line** `EMI = P / n`. Many
calculators silently fail this case.

### Test categories (each catches a different failure mode)

- **Golden dataset** — 5–10 hand-picked real-world loans with verified
  expected values. Quickest signal that something regressed.
- **Boundary Value Analysis (BVA)** — min, min+ε, max−ε, max for every
  input field. Catches off-by-one, overflow, slider clamping.
- **Equivalence partitioning** — one case per loan-size bucket
  (small ₹10K–1L · medium ₹5L–10L · large ₹1Cr+). Proves the
  calculation scales without precision loss.
- **Mathematical property tests** (invariants) — EMI grows with `P` and
  `r`, shrinks with `n`; total interest grows with `n`. Catches subtle
  formula regressions even when every individual case passes.
- **Precision & rounding** — odd-shaped inputs (rate 8.75%, tenure
  137 mo) to stress the rounding policy (half-up vs banker's, ₹ vs
  paise).
- **Negative / defensive inputs** — `P ≤ 0`, `r < 0`, `n ≤ 0`, null,
  empty, non-numeric. The AUT must reject cleanly, never silently
  zero-out or NaN.

### Current regression coverage in this repo

| Category | Where | Status |
|---|---|---|
| Golden / common scenarios | `emi_calculation_inputs.json:common_scenarios` | 7 cases |
| BVA — principal | `…:boundary_principal` | 4 cases (₹1 → UI slider max) |
| BVA — rate | `…:boundary_rate` | 4 cases (5%, 5.25%, 19.75%, 20%) |
| BVA — tenure | `…:boundary_tenure_months` | 4 cases (1, 2, 12, 360 mo) |
| Equivalence partitions | `…:equivalence_partitions` | 7 cases (₹10K → ₹2Cr) |
| Amortization reconciliation (UI ↔ Excel) | `tests/excel_file_checks/` | every month, **exact** (no tolerance) |
| Slider boundary handling | `tests/slider_values/` | min, max, out-of-range, step validation — **exact** EMI assertion |
| Chart ↔ table consistency | `tests/chart_table_consistency/` | yearly chart vs amortization table — **exact** after rounding chart float to whole rupees |

**Assertion policy across the suite:** every EMI / amortization / Excel
value is asserted **exactly** (to the rupee, no tolerance). The
calculation oracle uses `Decimal` with `ROUND_HALF_UP`, and the site's
displayed values round identically — so any drift fails loudly instead
of being silently absorbed.


## Markers

Declared in `pytest.ini`. Currently used by the suite:

| Marker | What it means | When it runs |
|---|---|---|
| `smoke` | minimal happy-path check | every PR |
| `regression` | full P0+P1 suite | nightly + pre-release |
| `boundary` | BVA at slider/input limits | feature marker |
| `calculation` | site EMI vs formula oracle | feature marker |

## Execution steps for a reviewer

1. `python3.12 -m venv .venv && source .venv/bin/activate`
2. `pip install -e .`
3. `playwright install chromium`
4. `pytest -m smoke` — quick Excel-download smoke check against the live site
5. `pytest` — runs all 42 tests (~6 min headed against the live site)
6. Open `reports/report.html` for a human-readable run summary
7. Tail `reports/pytest.log` for the full DEBUG trace of the most recent run

## CI

`.github/workflows/tests.yml` defines jobs for `smoke`, `sanity`,
`regression`, and `extended`. Reports + screenshots are uploaded as
artifacts on every run.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| BASE_URL | `https://emicalculator.net/` | Override for staging/local |
| BROWSERS | `chromium` | Comma-separated list: `chromium`, `firefox`, `webkit`. CLI `--browser` overrides. |
| BROWSER | _(unset)_ | Single-browser back-compat alias for BROWSERS. Use BROWSERS instead. |
| HEADLESS | `false` | Default is headed locally. CI sets `true`. `--headed` flag overrides. |
| SLOW_MO_MS | `0` | Slow Playwright down for debugging (ms between actions) |
| DEFAULT_TIMEOUT_MS | `15000` | Per-locator timeout |
