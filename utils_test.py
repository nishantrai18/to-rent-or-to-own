import unittest
import utils

from utils import Decision, FinancialStatus, Parameters


def get_default_parameters() -> Parameters:
    return Parameters(0.05, 0.07, 0.04, 2, 0.2, 500000, 25, 20000, 30, 0)


def get_balanced_rent_no_growth_parameters(house_value=500000) -> Parameters:
    num_years = 30
    downpayment = 0.2
    rent = house_value * (1 - downpayment) / num_years
    price_to_rent = house_value / rent if rent > 0 else 0
    return Parameters(
        0.0, 0.0, 0.0, 0, downpayment, house_value, price_to_rent, rent, num_years, 0
    )


class TestFinancialCalculations(unittest.TestCase):
    def test_mortgage_repayment_for_zero_interest_correct(self):
        params = get_balanced_rent_no_growth_parameters()
        result = utils.get_monthly_mortgage_repayment(params)
        self.assertAlmostEqual(
            result * params.num_years * utils.MONTHS,
            params.base_house_equity * (1 - params.downpayment_ratio),
        )

    def test_equity_after_rent_or_buy_in_first_year_always_equal(self):
        params = get_default_parameters()
        buy = utils.FinancialStatus(decision=Decision.BUY, params=params)
        rent = utils.FinancialStatus(decision=Decision.RENT, params=params)
        # Regardless of the starting parameters, the net worth in the first year should be the same.
        self.assertAlmostEqual(buy.net_worth(), rent.net_worth())

    def test_equity_in_free_scenario_always_equal(self):
        # Situation where rent and mortgage are the same and there's no interest rates and equity growth.
        params = get_balanced_rent_no_growth_parameters(house_value=0)
        buy = utils.FinancialStatus(decision=Decision.BUY, params=params)
        rent = utils.FinancialStatus(decision=Decision.RENT, params=params)
        # When there is no equity, real estate growth, and no interest rate. The net worth must be the same at every timestep.
        for _ in range(params.num_years * utils.MONTHS):
            self.assertAlmostEqual(buy.net_worth(), rent.net_worth())
            buy.increment_by_month()
            rent.increment_by_month()

    def test_buy_net_worth_in_no_growth_scenario_always_constant(self):
        # Situation where rent and mortgage are the same and there's no interest rates and equity growth.
        params = get_balanced_rent_no_growth_parameters()
        buy = utils.FinancialStatus(decision=Decision.BUY, params=params)
        # When there is no equity, real estate growth, and no interest rate. The net worth must be the same at every timestep.
        for _ in range(params.num_years * utils.MONTHS):
            self.assertAlmostEqual(
                buy.net_worth(), params.base_house_equity * params.downpayment_ratio
            )
            buy.increment_by_month()

    def test_rent_net_worth_in_no_growth_scenario_uniformly_decreases(self):
        # Situation where rent and mortgage are the same and there's no interest rates and equity growth.
        params = get_balanced_rent_no_growth_parameters()
        rent = utils.FinancialStatus(decision=Decision.RENT, params=params)
        initial_net_worth = rent.net_worth()
        # When there is no equity, real estate growth, and no interest rate. The net worth must be the same at every timestep.
        for month in range(params.num_years * utils.MONTHS):
            self.assertAlmostEqual(
                rent.net_worth(),
                initial_net_worth - (month * params.base_rent_per_year / utils.MONTHS),
            )
            rent.increment_by_month()


if __name__ == "__main__":
    unittest.main()
