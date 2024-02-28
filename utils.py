# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from enum import Enum
from pprint import pprint

import numpy as np
import numpy_financial as npf


# Setup basic constants.
MONTHS = 12


class Decision(Enum):
    RENT = 1
    BUY = 2


@dataclass
class Parameters:
    # Rate of returns, interest, fees, etc.
    roi_real_estate: float = 0
    roi_stocks: float = 0
    mortgage_interest_rate: float = 0
    base_house_misc_costs: float = 0
    downpayment_ratio: int = 0
    # Real estate prices and costs.
    base_house_equity: int = 0
    price_to_rent_ratio: int = 0
    base_rent_per_year: int = 0
    # Time period for simulation.
    num_years: int = 0
    # Personal financial status.
    monthly_income: int = 0


class FinancialStatus:
    """Describes your current financial status, excess investment flow,
    net worth and additional info.

    Supports operations to simulate investment growth over a period of time, getting
    current net worth, tracking growth of various assets such as real estate and equity.
    """

    def __init__(self, decision: Decision, params: Parameters):
        self.params = params
        self.decision = decision
        self.monthly_income = self.params.monthly_income

        self.equity_real_estate = self.equity_stocks = 0
        self.latest_taxable_house_value = 0
        self.remaining_mortgage_equity = 0
        self.monthly_expenses = 0
        self._cumulative_real_estate_roi = 1.0
        self._instantiate_internal_state()

        self.time = relativedelta(months=0)

    def monthly_excess(self):
        return self.monthly_income - self.monthly_expenses

    def monthly_misc_costs(self):
        return (
            self.params.base_house_misc_costs * self.latest_taxable_house_value / MONTHS
        )
    
    def monthly_mortgage(self):
        # Returns negative for a payment.
        monthly_mortgage_rate = ((1 + self.params.mortgage_interest_rate) ** (1 / MONTHS)) - 1
        return -npf.pmt(
            monthly_mortgage_rate,
            self.params.num_years * MONTHS,
            self.params.base_house_equity * (1 - self.params.downpayment_ratio),
            fv=0,
            when="end",
        )

    def _instantiate_internal_state(self):
        if self.decision == Decision.BUY:
            self.equity_real_estate = self.params.base_house_equity
            self.latest_taxable_house_value = self.params.base_house_equity
            self.remaining_mortgage_equity = self.params.base_house_equity * (
                1.0 - self.params.downpayment_ratio
            )
            self.equity_stocks = 0
            self.monthly_expenses = get_monthly_mortgage_repayment(self.params) + self.monthly_misc_costs()
        elif self.decision == Decision.RENT:
            self.equity_real_estate = 0
            self.remaining_mortgage_equity = 0
            self.equity_stocks = (
                self.params.base_house_equity * self.params.downpayment_ratio
            )
            self.monthly_expenses = self.params.base_rent_per_year / MONTHS
        else:
            raise ValueError(f"Invalid decision: {self.decision}")

    def increment_by_month(self, roi_stocks=None, roi_real_estate=None):
        # Increment time by one month.
        self.time += relativedelta(months=1)

        # If ROIs are not provided, initialize with defaults.
        if roi_stocks is None:
            roi_stocks = self.params.roi_stocks
        if roi_real_estate is None:
            roi_real_estate = self.params.roi_real_estate

        # Model equity increase over the past month.
        self.equity_stocks *= (1 + roi_stocks) ** (1.0 / MONTHS)
        self.equity_real_estate *= (1 + roi_real_estate) ** (1.0 / MONTHS)
        # Store the cumulative real estate ROI so far.
        self._cumulative_real_estate_roi *= (1 + roi_real_estate) ** (1.0 / MONTHS)
        # Account for equity increase/decrease by adding the monthly cash flow.
        self.equity_stocks += self.monthly_excess()

        if self.decision == Decision.BUY:
            # Assume the remaining mortgage equity uniformly decreases over `num_years`.
            self.remaining_mortgage_equity -= (
                self.params.base_house_equity * (1.0 - self.params.downpayment_ratio)
            ) / (self.params.num_years * MONTHS)

        if self.time.months % MONTHS == 0:
            self.annual_reevaluations()

    def annual_reevaluations(self):
        # Update the rent, house value and any other commitments annually.
        self.latest_taxable_house_value = self.params.base_house_equity * self._cumulative_real_estate_roi
        if self.decision == Decision.BUY:
            self.monthly_expenses = self.monthly_mortgage() + self.monthly_misc_costs()
        elif self.decision == Decision.RENT:
            self.monthly_expenses = (
                self.params.base_rent_per_year * self._cumulative_real_estate_roi
            ) / MONTHS

    def net_worth(self):
        return (
            self.equity_real_estate
            + self.equity_stocks
            - self.remaining_mortgage_equity
        )

    def print_summary(self):
        """Prints internal financial state in a pretty format."""
        pprint("[SUMMARY]")
        pprint(f"decision: {self.decision}, Monthly income: {self.monthly_income}")
        pprint(f"Real Estate: {self.equity_real_estate}, Stocks: {self.equity_stocks}")
        pprint(
            f"Remaining mortgage: {self.remaining_mortgage_equity}, Monthly expense: {self.monthly_expenses}"
        )
        pprint(f"Cumulative RoI: {self._cumulative_real_estate_roi}")


################################################################################
# Legacy functions taking a time and providing the equity through calculations.
################################################################################


def get_monthly_mortgage_repayment(params: Parameters):
    # Returns negative for a payment.
    monthly_mortgage_rate = ((1 + params.mortgage_interest_rate) ** (1 / MONTHS)) - 1
    return -npf.pmt(
        monthly_mortgage_rate,
        params.num_years * MONTHS,
        params.base_house_equity * (1 - params.downpayment_ratio),
        fv=0,
        when="end",
    )


def get_current_equity_after_buying(time_in_years, params: Parameters):
    # Consider value of house after annual compounding for `time_in_years`.
    cumulative_growth = (1 + params.roi_real_estate) ** time_in_years
    value_of_house = params.base_house_equity * cumulative_growth
    total_mortgage_payments = (
        get_monthly_mortgage_repayment(params) * time_in_years * MONTHS
    )
    total_house_misc_costs = (
        params.base_house_misc_costs * params.base_house_equity * time_in_years
    )
    return value_of_house - total_mortgage_payments - total_house_misc_costs


def get_current_equity_after_renting(time_in_years, params: Parameters):
    # Consider value of investments, only consider difference vs the buying scenario.
    year_idx = np.array(range(time_in_years + 1))
    annual_savings_by_not_buying = (get_monthly_mortgage_repayment(params) * MONTHS) + (
        params.base_house_misc_costs * params.base_house_equity
    )
    # Rent increases by `roi_real_estate` every year.
    rent_by_year = params.base_rent_per_year * np.power(
        1 + params.roi_real_estate, year_idx
    )
    excess_capital_by_year = annual_savings_by_not_buying - rent_by_year
    # In the first year, we have an excess of the house downpayment.
    excess_capital_by_year[0] += params.downpayment_ratio * params.base_house_equity
    # Stock investment growth by year. Year 0 would have the highest as it would see the most compounding.
    cumulative_growth = np.power((1 + params.roi_stocks), time_in_years - year_idx)
    return np.sum(excess_capital_by_year * cumulative_growth)


def calculate_monthly_financials(params: Parameters):
    # Monthly mortgage repayment
    monthly_mortgage = get_monthly_mortgage_repayment(params)

    # Monthly rent, assuming it's a fraction of the property value based on the price-to-rent ratio
    monthly_rent = params.base_house_equity / params.price_to_rent_ratio / MONTHS

    # Monthly miscellaneous costs (assumed to be a percentage of the property value)
    monthly_misc_costs = (
        params.base_house_misc_costs * params.base_house_equity / MONTHS
    )

    return monthly_mortgage, monthly_rent, monthly_misc_costs
