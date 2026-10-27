"""Portfolio management demo: public and private holdings, risk, operations and a family balance sheet.

Run locally:  streamlit run app.py
All figures are sample data from ./data; see README.md to swap in real files.
"""
import streamlit as st

from pmdemo import tabs
from pmdemo.data import load

st.set_page_config(page_title="Portfolio Management Demo", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
      [data-testid="stMetricValue"] { font-size: 1.6rem; }
      [data-testid="stMetricDelta"] svg { display: none; }
      .block-container { padding-top: 1.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Portfolio dashboard")
st.caption("Demo with **sample data**: positions, prices, funds, custodians and liabilities are illustrative; "
           "news items are real headlines summarized as of the date shown.")

data = load()

names = ["Public markets overview", "Public markets risk factors", "Attribution", "Private equity",
         "Operations", "Balance sheet", "Holdings", "Market news"]
renderers = [tabs.overview, tabs.risk, tabs.attribution, tabs.private_equity,
             tabs.operations, tabs.balance_sheet, tabs.holdings, tabs.news]

for tab, render in zip(st.tabs(names), renderers):
    with tab:
        render(data)
