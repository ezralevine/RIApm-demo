# Portfolio Management Demo

A standalone Streamlit app for a family-office style portfolio system: public markets, private equity, operations, and a consolidated balance sheet. Every figure comes from sample data in `data/`. Swap in real files with the same columns and the whole app follows.

## Tabs

| Tab | What it shows |
|---|---|
| Public markets overview | Headline figures, value vs benchmark, monthly returns, allocation vs benchmark by asset class, country and industry, top 10 positions |
| Public markets risk factors | Volatility (rolling, VaR/CVaR, Sortino), tracking error by risk source and factor, Fama-French-Carhart regression, risk vs weight, active factor exposures |
| Attribution | Contribution to return by position and theme over 1M, 3M, YTD, 1Y and since start |
| Private equity | Commitments, paid-in, DPI/TVPI, pooled IRR, KS-PME, J-curve, projected calls, capital call notices with overdue flags |
| Operations | Guideline compliance, client restrictions with fund look-through, pre-trade check, portfolio system vs custodian reconciliation, drift and rebalancing, trade blotter, corporate actions |
| Balance sheet | All assets (public, private, homes, art, vehicles, cash) against debt and expected liabilities, liquidity, 12-month outflows |
| Holdings | Public and private holdings in one list with source or custodian |
| Market news | Market and holdings news summaries with links |

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## Deploy to Streamlit Community Cloud

1. Create a GitHub repo (private is fine) and push this folder:
   ```bash
   git init && git add . && git commit -m "Portfolio management demo"
   git branch -M main
   git remote add origin git@github.com:<you>/pm-demo.git
   git push -u origin main
   ```
2. Go to share.streamlit.io, choose **Create app**, pick the repo, branch `main`, main file `app.py`, and deploy.
3. Share the app's URL. For a private repo, add viewers by email in the app's sharing settings.

## Project layout

```
app.py              entry point: page setup and the eight tabs
pmdemo/data.py      loads every file in data/ (cached)
pmdemo/calcs.py     all calculations: exposures, compliance, reconciliation, restrictions, PE metrics, balance sheet...
pmdemo/charts.py    Plotly helpers in one visual style
pmdemo/tabs.py      one render function per tab
data/               sample data (CSV + news.json)
scripts/            generators used to build the simulated returns, risk model, PE program and attribution
```

## Using real data

Replace any file in `data/` keeping its column names. The ones you'd usually replace first:

| File | Replace with |
|---|---|
| `holdings.csv` | Positions from your portfolio system (ticker, shares, cost, price, value, weight, classifications) |
| `custodian.csv` | Custodian position exports, one row per account and security |
| `transactions.csv` | Trade blotter with settlement status |
| `pefunds.csv`, `capitalcalls.csv` | GP capital account statements and call notices |
| `otherassets.csv`, `liabilities.csv` | Property appraisals, art schedules, mortgage and loan statements |
| `restrictions.csv`, `screening.csv`, `restrictedlist.csv` | The client's investment policy and an ESG screening provider's data |
| `benchmark.csv` | Your benchmark's weights by holding, theme, industry, asset class and country |

Guideline limits live in `GUIDELINES` in `pmdemo/calcs.py`; the deferred-tax rate is `DEFERRED_TAX_RATE`.

Return-based files (`history.csv`, `dailyreturns.csv`, `volstats.csv`, `factors.csv`, `riskmodel.csv`, `attribution.csv`) are simulated. With real holdings, rebuild them from actual price history (and the Ken French factor library for the regression).

## Regenerating the simulated data

The scripts write to the current directory and read each other's outputs. From `data/`:

```bash
cd data
python ../scripts/gen.py   # holdings, history, monthly, factors, summary
python ../scripts/vol.py   # volstats, rollingvol, dailyreturns
python ../scripts/ffb.py   # adds benchmark loadings to factors
python ../scripts/attr.py  # attribution, attrsummary
python ../scripts/risk.py  # riskmodel (needs benchmark.csv)
python ../scripts/pe.py    # pefunds, pecashflows, pecalls
```

The remaining files (benchmark, custodian, transactions, restrictions, balance sheet items, news) are hand-written sample files: edit them directly.

## Market news

`data/news.json` is a snapshot. To make it live, add a function in a new `pmdemo/news.py` that calls a news API (for example MT Newswires or Bigdata.com) with your tickers and returns rows in the same shape (`date, scope, ticker, category, summary, source, url, refreshed`). Then call it from `tabs.news` in place of the file. Keep API keys in Streamlit secrets (`.streamlit/secrets.toml`, which should never be committed).

## Disclaimer

Demo software with illustrative data. Not investment, tax or legal advice.
