"""End-to-end checks that the downloaded Excel workbook is consistent with
what the EMI calculator shows in the browser.

The workbook has three sections we verify here:

  1. **Loan Details** (header rows 1–3) — input echo: Home Loan Amount,
     Interest Rate (%), Loan Tenure (months).
  2. **Payment Summary** (header rows 6–8) — computed totals: Loan EMI,
     Total Interest Payable, Total Payment (Principal + Interest).
  3. **Loan Amortization Table** (row 12 onwards) — month-by-month
     schedule with Principal / Interest / Total / Balance / % paid.

Each section gets its own test for clear failure attribution.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from playwright.sync_api import expect

from src.utils.excel_validator import find_summary_cell, load, monthly_schedule
from src.utils.logging_setup import get_logger


log = get_logger(__name__)


@pytest.fixture
def excel_file(emi_page, tmp_path) -> Path:
    """Click the page's 'Download Excel' button and return the saved path."""
    log.info("Triggering Excel download to tmp dir: %s", tmp_path)
    # Precondition: download trigger must be on the page.
    expect(emi_page.page.get_by_role("button", name="Download Excel")).to_be_visible()
    path = emi_page.download_excel(tmp_path)
    log.info("Excel saved to: %s (%d bytes)", path, path.stat().st_size)
    return path


# ---------------------------------------------------------------------------
# 1. Smoke
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_excel_download_produces_non_empty_file(excel_file: Path):
    """Clicking 'Download Excel' should produce a workbook of at least 1KB
    on disk — the cheapest possible signal that the export pipeline runs."""
    log.info("Verifying downloaded Excel exists and is > 1024 bytes")
    assert excel_file.exists(), f"excel file missing: {excel_file}"

    file_size_bytes = excel_file.stat().st_size
    log.info("Excel file size: %d bytes", file_size_bytes)
    assert file_size_bytes > 1024, f"excel file is suspiciously small: {file_size_bytes} bytes"
    log.info("Excel download present and non-empty")


# ---------------------------------------------------------------------------
# 2. Loan Details (workbook section 1) ↔ page inputs
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.cross_feature
def test_excel_loan_details_section_matches_ui_inputs(emi_page, excel_file: Path):
    """The 'Loan Details' section of the workbook (Home Loan Amount,
    Interest Rate, Loan Tenure in months) must echo back exactly what the
    user has entered into the three input fields on the page."""
    summary = load(excel_file)

    # --- read what the page currently shows --------------------------------
    page_amount_inr = emi_page.amount.read_input()
    page_rate_pct = emi_page.rate.read_input()
    page_tenure_in_months = Decimal(emi_page.current_tenure_months())

    # --- read what the workbook claims via the labelled summary cells -----
    excel_amount_inr = find_summary_cell(summary, "Home Loan Amount")
    excel_rate_pct = find_summary_cell(summary, "Interest Rate")
    excel_tenure_in_months = find_summary_cell(summary, "Loan Tenure")

    log.info(
        "Loan Details comparison — amount: page=%s excel=%s | rate: page=%s excel=%s | tenure: page=%s excel=%s",
        page_amount_inr, excel_amount_inr,
        page_rate_pct, excel_rate_pct,
        page_tenure_in_months, excel_tenure_in_months,
    )

    # --- assert each cell echoes the corresponding input ------------------
    assert excel_amount_inr == page_amount_inr, (
        f"Loan amount mismatch — page input shows ₹{page_amount_inr}, "
        f"workbook 'Home Loan Amount' shows ₹{excel_amount_inr}"
    )
    assert excel_rate_pct == page_rate_pct, (
        f"Interest rate mismatch — page input shows {page_rate_pct}%, "
        f"workbook 'Interest Rate' shows {excel_rate_pct}%"
    )
    assert excel_tenure_in_months == page_tenure_in_months, (
        f"Tenure mismatch — page input represents {page_tenure_in_months} months, "
        f"workbook 'Loan Tenure' shows {excel_tenure_in_months}"
    )
    log.info("Loan Details section reconciles with UI inputs")


# ---------------------------------------------------------------------------
# 3. Payment Summary (workbook section 2) ↔ page results panel
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.cross_feature
def test_excel_payment_summary_section_matches_ui_results_panel(emi_page, excel_file: Path):
    """The 'Payment Summary' section of the workbook (Loan EMI, Total
    Interest Payable, Total Payment) must equal the three tiles the page
    shows in its results panel — both are computed from the same inputs."""
    summary = load(excel_file)

    # --- read what the page's results panel shows --------------------------
    page_emi = emi_page.results.emi()
    page_total_interest = emi_page.results.total_interest()
    page_total_payment = emi_page.results.total_payment()

    # --- read what the workbook's summary section claims -------------------
    excel_emi = find_summary_cell(summary, "Loan EMI")
    excel_total_interest = find_summary_cell(summary, "Total Interest Payable")
    excel_total_payment = find_summary_cell(summary, "Total Payment")

    log.info(
        "Payment Summary comparison — EMI: page=%s excel=%s | interest: page=%s excel=%s | total: page=%s excel=%s",
        page_emi, excel_emi,
        page_total_interest, excel_total_interest,
        page_total_payment, excel_total_payment,
    )

    assert excel_emi == page_emi, (
        f"EMI mismatch — page tile shows ₹{page_emi}, workbook shows ₹{excel_emi}"
    )
    assert excel_total_interest == page_total_interest, (
        f"Total Interest mismatch — page tile shows ₹{page_total_interest}, "
        f"workbook shows ₹{excel_total_interest}"
    )
    assert excel_total_payment == page_total_payment, (
        f"Total Payment mismatch — page tile shows ₹{page_total_payment}, "
        f"workbook shows ₹{excel_total_payment}"
    )
    log.info("Payment Summary section reconciles with UI results panel")


# ---------------------------------------------------------------------------
# 4. Monthly Amortization Table (workbook section 3) ↔ page expanded rows
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.cross_feature
def test_excel_monthly_schedule_matches_page_expanded_rows(emi_page, excel_file: Path):
    """Reconcile every monthly row in the workbook against the page's
    amortization table, year by year, by clicking each year header to
    reveal its monthly sub-table. Both sources round to whole rupees and
    flow from the same engine — so every Principal, Interest, Total,
    Balance, and % paid value must match **exactly**."""
    # Precondition: the table itself must be rendered before we can expand it.
    expect(emi_page.table.year_rows.first).to_be_visible()

    # --- gather every monthly row from each side --------------------------
    excel_monthlies = monthly_schedule(load(excel_file))
    page_monthlies = emi_page.table.all_monthly_rows()

    log.info(
        "Row counts — excel: %d monthly rows, page: %d monthly rows",
        len(excel_monthlies), len(page_monthlies),
    )

    # --- structural check: same loan length on both sides ------------------
    assert len(excel_monthlies) == len(page_monthlies), (
        f"row-count mismatch: excel has {len(excel_monthlies)} monthly rows, "
        f"page has {len(page_monthlies)}"
    )

    # --- pair them in order and assert every numeric field is exact -------
    # Both lists are in chronological order from the loan's first month, so
    # zipping pairs each Excel `MonthlyEntry` with the same calendar month
    # on the page.
    for excel_row, page_row in zip(excel_monthlies, page_monthlies):
        month_id = f"{excel_row.month_label} (#{excel_row.month_index})"
        assert excel_row.principal == page_row.principal, (
            f"{month_id} principal mismatch — excel=₹{excel_row.principal}, page=₹{page_row.principal}"
        )
        assert excel_row.interest == page_row.interest, (
            f"{month_id} interest mismatch — excel=₹{excel_row.interest}, page=₹{page_row.interest}"
        )
        assert excel_row.total_payment == page_row.total_payment, (
            f"{month_id} total payment mismatch — excel=₹{excel_row.total_payment}, page=₹{page_row.total_payment}"
        )
        assert excel_row.balance == page_row.balance, (
            f"{month_id} balance mismatch — excel=₹{excel_row.balance}, page=₹{page_row.balance}"
        )
        assert excel_row.loan_paid_pct == page_row.loan_paid_pct, (
            f"{month_id} % paid mismatch — excel={excel_row.loan_paid_pct}%, page={page_row.loan_paid_pct}%"
        )
    log.info("All %d monthly rows reconciled exactly with the page table", len(excel_monthlies))
