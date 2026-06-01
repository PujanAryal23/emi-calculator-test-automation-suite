"""Site-displayed EMI must match the formula oracle exactly (to the rupee).

The single parametrized test below is driven by
`test-data/emi_calculation_inputs.json`, which organises scenarios into
five categories so a failure tells you which dimension regressed:

  * `common_scenarios`        — representative real-world home loans
  * `boundary_principal`      — BVA on the loan amount (₹1, ₹100, near UI max, UI max)
  * `boundary_rate`           — BVA on the interest rate (slider min/max + one-step inside each)
  * `boundary_tenure_months`  — BVA on the tenure (1mo, 2mo, 12mo, 360mo max)
  * `equivalence_partitions`  — small / medium / large loan partitions to
                                confirm calculation scales correctly

All categories are flattened into a single parametrize so they run as
one suite of cases against the live site. The assertion is strict
equality — the displayed EMI must equal the formula oracle to the
rupee, no tolerance.
"""

import pytest

from src.utils.emi_formula import calculate_emi
from src.utils.logging_setup import get_logger
from src.utils.test_data import load_test_data


log = get_logger(__name__)

_DATA = load_test_data("emi_calculation_inputs")

# Flatten every category into a single parametrize feed. Each scenario
# already carries its own `description`, so the category boundaries are
# preserved via that human-readable label in the logs and failure messages.
_ALL_SCENARIOS = (
    _DATA["common_scenarios"]
    + _DATA["boundary_principal"]
    + _DATA["boundary_rate"]
    + _DATA["boundary_tenure_months"]
    + _DATA["equivalence_partitions"]
)


@pytest.mark.regression
@pytest.mark.calculation
@pytest.mark.parametrize("scenario", _ALL_SCENARIOS)
def test_site_emi_matches_formula(emi_page, scenario):
    """Verify the page's EMI tile equals the formula oracle exactly for
    every scenario in the JSON fixture — covering the default common
    loans, BVA at each input's boundaries (principal, rate, tenure), and
    equivalence partitions across small / medium / large loan sizes.
    Each scenario specifies tenure as either `tenure_years` or
    `tenure_months`; the test normalizes to months for the oracle."""
    # Normalize tenure to months so the formula oracle can be called
    # consistently regardless of how the scenario expressed it.
    tenure_in_months = (
        int(scenario["tenure_months"])
        if "tenure_months" in scenario
        else int(scenario["tenure_years"]) * 12
    )
    log.info(
        "--- Scenario: %s (P=Rs.%s R=%s%% N=%dmo) ---",
        scenario["description"],
        scenario["principal"],
        scenario["rate"],
        tenure_in_months,
    )

    # Drive the page with the scenario's values. `configure()` picks the
    # tenure unit based on whichever of `tenure_years` / `tenure_months`
    # is present (months wins when both are passed).
    emi_page.configure(
        principal=scenario["principal"],
        rate=scenario["rate"],
        tenure_years=scenario.get("tenure_years"),
        tenure_months=scenario.get("tenure_months"),
    )

    # Compute the oracle EMI from the same inputs the page just received.
    expected_emi_rupees = calculate_emi(
        scenario["principal"],
        scenario["rate"],
        tenure_in_months,
    )
    log.info(
        "Computed expected EMI = Rs.%s for %s",
        expected_emi_rupees,
        scenario["description"],
    )

    # Strict equality — site EMI must match the oracle to the rupee.
    emi_page.results.expect_emi_equals(expected_emi_rupees)
