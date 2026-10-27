"""Load the demo's data files.

Every number in the app comes from a file in ./data. Replace a file with real
data in the same columns and the whole app follows.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FILES = {
    "holdings": "holdings.csv",
    "history": "history.csv",
    "monthly": "monthly.csv",
    "factors": "factors.csv",
    "summary": "summary.csv",
    "benchmark": "benchmark.csv",
    "riskmodel": "riskmodel.csv",
    "transactions": "transactions.csv",
    "corpactions": "corpactions.csv",
    "targets": "targets.csv",
    "volstats": "volstats.csv",
    "rollingvol": "rollingvol.csv",
    "dailyreturns": "dailyreturns.csv",
    "pefunds": "pefunds.csv",
    "pecashflows": "pecashflows.csv",
    "pecalls": "pecalls.csv",
    "industrymap": "industrymap.csv",
    "custodian": "custodian.csv",
    "restrictions": "restrictions.csv",
    "screening": "screening.csv",
    "restrictedlist": "restrictedlist.csv",
    "otherassets": "otherassets.csv",
    "liabilities": "liabilities.csv",
    "outflows": "outflows.csv",
    "capitalcalls": "capitalcalls.csv",
    "attribution": "attribution.csv",
    "attrsummary": "attrsummary.csv",
}


@st.cache_data(show_spinner=False)
def load(data_dir: str = str(DATA_DIR)) -> dict[str, pd.DataFrame]:
    d = Path(data_dir)
    out: dict[str, pd.DataFrame] = {}
    for key, name in FILES.items():
        df = pd.read_csv(d / name, keep_default_na=False, na_values=[""])
        out[key] = df
    out["news"] = pd.DataFrame(json.loads((d / "news.json").read_text()))
    # Empty strings that should stay text
    for key, cols in {"transactions": ["ticker"], "news": ["ticker"], "capitalcalls": ["paidDate"], "liabilities": ["due"]}.items():
        for c in cols:
            if c in out[key]:
                out[key][c] = out[key][c].fillna("")
    return out
