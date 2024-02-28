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
import math
from streamlit.logger import get_logger
from utils import Parameters

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import streamlit as st
import time
import utils

LOGGER = get_logger(__name__)


########################################
# Utilities to compute financial values.
########################################


def define_inputs() -> Parameters:
    # Sets up primary inputs along with the defaults. They are broadly divided into,
    # 1. Real Estate Parameters
    # 2. Equity Parameters
    # 3. Secondary Parameters: Not crucial to the primary simulation.
    params = Parameters()

    with st.expander("House Cost and Rent", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            # House equity in the first year.. Assumed to grow as `roi_real_estate`.
            params.base_house_equity = st.number_input(
                "House Value ($)",
                value=700000,
                placeholder="Enter house value in the first year.",
            )

        with col2:
            params.monthly_income = st.number_input(
                label="Monthly Income ($):",
                value=5000,
                help="Monthly Income ($) for calculations.",
            )

        params.price_to_rent_ratio = st.slider(
            label="Price to Rent Ratio:",
            min_value=1,
            max_value=100,
            value=38,
            help="Price-to-Annual-Rent Ratio for the house, average value in San Jose, CA is 38.",
        )

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("Equity Parameters", expanded=True):
            params.roi_stocks = 0.01 * st.slider(
                label="Annual Return % (Equity):",
                min_value=0.0,
                max_value=20.0,
                value=10.05,
                help="Rate of expected return in the stock market. 10.05\% is the rate of return for SP500 over the past 20 years, assuming dividend reinvestment.",
            )

    with col2:
        with st.expander("Simulation Parameters", expanded=True):
            params.num_years = st.slider(
                label="Number of years to simulate:",
                min_value=1,
                max_value=50,
                value=20,
                help="Number of years to simulate returns for.",
            )

    # Using expander for organizing inputs
    with st.expander("Real Estate Parameters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            params.roi_real_estate = 0.01 * st.slider(
                label="Annual Return % (Real Estate):",
                min_value=0.0,
                max_value=20.0,
                value=6.5,
                help="Rate of expected return in real estate. Also assumed to be the annual increase in Rent. 5.4\% YoY historically from 1992 to 2022. Can assume closer to 7\% in the past decade.",
            )
            params.mortgage_interest_rate = 0.01 * st.slider(
                label="Mortgage Interest Rate (%):",
                min_value=0.0,
                max_value=20.0,
                value=6.0,
                help="Interest rate for the real estate mortgage. Average of 4.5\% in the past decade. Between April 1971 and June 2023, 30-year fixed-rate mortgages averaged 7.74\%. The 1980s were outliers so should be accounted for.",
            )

        with col2:
            params.downpayment_ratio = 0.01 * st.slider(
                label="Downpayment (%):",
                min_value=0,
                max_value=100,
                value=20,
                help="Downpayment for the real estate, average value is 20%.",
            )
            # base house misc costs: insurance, property tax, etc.
            # Assumed to be 1% of base house equity, and 1% of base towards maintenance (amortized).
            # Let's assume insurance is ~0.
            # Based on https://www.investopedia.com/financial-edge/0411/7-homeowner-costs-renters-dont-pay.aspx.
            params.base_house_misc_costs = 0.01 * st.slider(
                label="Misc Housing Costs (%):",
                min_value=0.0,
                max_value=10.0,
                value=2.0,
                help="Misc housing costs: Insurance, Property Tax, Maintanence. Roughly around 2% according to Investopedia.",
            )

    # House rent in the first year. Assumed to grow as `roi_real_estate`.
    # San Jose price to rent ratio is 38.
    params.base_rent_per_year = params.base_house_equity / params.price_to_rent_ratio

    return params


def display_financial_info(buy: utils.FinancialStatus, rent: utils.FinancialStatus):

    with st.expander("Monthly Financial Info", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("When Buying")
            st.markdown(f"* Mortgage: ${buy.monthly_mortgage():,.2f} / month")
            st.markdown(
                f"* Misc. Costs: ${buy.monthly_misc_costs():,.2f} / month"
            )
            st.markdown(f"* Monthly Excess: ${buy.monthly_excess():,.2f} / month")

        with col2:
            st.markdown("When Renting")
            st.markdown(f"* Monthly Rent: ${rent.monthly_expenses:,.2f} / month")
            st.markdown(
                f"* Misc. Costs: ${rent.monthly_misc_costs():,.2f} / month"
            )
            st.markdown(f"* Monthly Excess: ${rent.monthly_excess():,.2f} / month")


def simulate(buy: utils.FinancialStatus, rent: utils.FinancialStatus):
    times = np.array(range(buy.params.num_years * utils.MONTHS), dtype=np.double) / utils.MONTHS

    # Calculate equity values for renting and buying.
    equity_after_buying, equity_after_renting = [], []
    for m in times:
        equity_after_buying.append(buy.net_worth())
        equity_after_renting.append(rent.net_worth())
        buy.increment_by_month()
        rent.increment_by_month()
    
    return np.array(equity_after_buying), np.array(equity_after_renting), times


def plot_comparisons(buy: np.array, rent: np.array, times: np.array):
    # Create a figure and axis for the plot
    fig, ax = plt.subplots()  
    marker_frequency = times.shape[0] / math.ceil(np.max(times))

    # Plotting the 'Buying' scenario
    ax.plot(
        times,
        buy,
        color="#1f77b4",
        label="Buying",
        marker="o",
        markevery=marker_frequency,
        alpha=0.7,
        linewidth=2,
    )
    # Adding shade
    ax.fill_between(times, buy, color="#1f77b4", alpha=0.3)

    # Plotting the 'Renting' scenario
    ax.plot(
        times,
        rent,
        color="#ff7f0e",
        label="Renting",
        linestyle="--",
        marker="x",
        markevery=marker_frequency,
        alpha=0.7,
        linewidth=2,
    )
    # Adding shade
    ax.fill_between(times, rent, color="#ff7f0e", alpha=0.3)

    # Customizing the plot
    ax.set_xlabel("Years", fontsize=12)
    ax.set_ylabel("Equity ($)", fontsize=12)
    ax.legend(frameon=True, fontsize=10)

    # Enhancing the x-ticks and y-ticks
    # Set major x-ticks at regular intervals
    ax.xaxis.set_major_locator(
        ticker.MultipleLocator(5)
    )  # Change 5 to a different number if needed
    # Set major y-ticks at regular intervals
    ax.yaxis.set_major_locator(ticker.MaxNLocator(6))  # Adjust the number of ticks
    # Format the tick labels.
    ax.tick_params(
        axis="x", rotation=45, labelsize=10
    )  # Rotate x-tick labels for better readability
    ax.tick_params(axis="y", labelsize=10)
    ax.get_yaxis().set_major_formatter(
        ticker.FuncFormatter(
            lambda x, p: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"
        )
    )

    # Remove minor ticks to declutter the plot
    ax.minorticks_off()
    # Grid adjustments
    ax.grid(True, which="major", linestyle="--", linewidth="0.5", color="grey")

    # Some last touches to the overall plot.
    ax.margins(x=0.025, y=0.025)
    ax.spines[["right", "top", "left", "bottom"]].set_visible(False)

    # Display the plot in Streamlit
    st.pyplot(fig)


def run():
    st.set_page_config(
        page_title="Hello",
        page_icon="👋",
    )

    st.write("# To Rent or To Buy?")

    params = define_inputs()
    buy = utils.FinancialStatus(decision=utils.Decision.BUY, params=params)
    rent = utils.FinancialStatus(decision=utils.Decision.RENT, params=params)

    # Add some space after the inputs.
    st.write(" ")

    display_financial_info(buy, rent)

    # Add some space after the inputs.
    st.write(" ")

    net_worth_buy, net_worth_rent, times = simulate(buy, rent)
    # with st.expander("View Plot", expanded=True):
    with st.container():
        plot_comparisons(net_worth_buy, net_worth_rent, times)

    # Streamlit widgets automatically run the script from top to bottom. Since
    # this button is not connected to any other logic, it just causes a plain
    # rerun.
    # st.button("Re-run")


if __name__ == "__main__":
    run()
