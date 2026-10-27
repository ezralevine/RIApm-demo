"""One function per tab. Each takes the loaded data dict and renders with Streamlit."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from . import calcs as C
from . import charts as K

usd = lambda v: f"${v:,.0f}"
usdk = lambda v: f"${v / 1000:,.0f}k" if abs(v) < 1e6 else f"${v / 1e6:,.2f}M"
pct = lambda v: f"{v:.1%}"
spct = lambda v: f"{v:+.1%}"
pts = lambda v: f"{v * 100:+.2f} pts"
esc = lambda s: str(s).replace("$", "\\$")
fdate = lambda s: datetime.strptime(str(s)[:10], "%Y-%m-%d").strftime("%b %-d, %Y")


def metrics(items: list[tuple[str, str, str | None]], help_: dict | None = None):
    cols = st.columns(len(items))
    for c, (label, value, sub) in zip(cols, items):
        c.metric(label, value, sub, delta_color="off", help=(help_ or {}).get(label))


def card(title: str, note: str | None = None):
    st.markdown(f"#### {esc(title)}")
    if note:
        st.caption(esc(note))


def status_style(df: pd.DataFrame, col: str = "status"):
    colors = {"Breach": "#d64545", "Overdue": "#d64545", "Break": "#d64545", "Failed": "#d64545",
              "Watch": "#c98a14", "Review": "#c98a14", "Timing": "#c98a14", "Pending": "#c98a14", "Paid late": "#c98a14",
              "OK": "#2e9e6a", "Compliant": "#2e9e6a", "Matched": "#2e9e6a", "Paid": "#2e9e6a", "Settled": "#2e9e6a"}
    return df.style.map(lambda v: f"color: {colors.get(v, 'inherit')}; font-weight: 600", subset=[col])


# ---------------------------------------------------------------- Overview
def overview(d):
    k = C.kpis(d["summary"])
    exp = C.exposure(d["holdings"], d["benchmark"], d["industrymap"])
    tt, ta = C.top_theme(exp), C.top_active_theme(exp)
    st.markdown(esc(f"The portfolio is worth **{usd(k['totalValue'])}**, has returned **{pct(k['portReturn'])}** a year against "
                f"**{pct(k['benchReturn'])}** for the benchmark, and its largest theme is **{tt.group}** at **{pct(tt.weight)}** of assets. "
                f"The biggest bet against the benchmark is **{ta.group}**, overweight by **{spct(ta.active)}**."))
    metrics([("Market value", usd(k["totalValue"]), f"as of {fdate(k['asOf'])}"),
             ("Unrealized gain", "+" + usd(k["gain"]), f"{spct(k['gainPct'])} on cost basis"),
             ("Annualized return, 2 yrs", pct(k["portReturn"]), f"{spct(k['excess'])} vs benchmark"),
             ("Sharpe ratio", f"{k['portSharpe']:.2f}", f"benchmark {k['benchSharpe']:.2f}"),
             ("Max drawdown", pct(k["portMaxDD"]), f"benchmark {pct(k['benchMaxDD'])}"),
             ("Beta to benchmark", f"{k['beta']:.2f}", f"volatility {pct(k['portVol'])}")])
    c1, c2 = st.columns(2)
    with c1:
        card("Value vs benchmark", "Portfolio value and the same starting amount in the benchmark, weekly, last 2 years.")
        st.plotly_chart(K.lines(d["history"], "date", [("benchmark", "Benchmark", K.ORANGE), ("portfolio", "Portfolio", K.BLUE)], prefix="$"), width="stretch")
    with c2:
        card("Monthly returns", "Each month's return, portfolio beside benchmark.")
        st.plotly_chart(K.grouped_bars(d["monthly"], "month", [("portfolio", "Portfolio", K.BLUE), ("benchmark", "Benchmark", K.ORANGE)]), width="stretch")

    st.markdown("### Allocation & exposure")
    c1, c2 = st.columns(2)
    order = {"assetClass": ("By asset class", "Equity split into US and international by company domicile. Benchmark: 50% US equity, 35% international equity, 10% bonds, 5% T-bills."),
             "country": ("By country", "Where each company is domiciled; non-US remainder of the index and the international ETF shown as one bucket."),
             "industry": ("By industry", "Broad index funds are split into their underlying industries.")}
    for i, (dim, (title, note)) in enumerate(order.items()):
        with (c1 if i % 2 == 0 else c2):
            card(title, note)
            df = exp[exp.dimension == dim].sort_values("weight", ascending=False)
            st.plotly_chart(K.compare_hbars(df, "group", "weight", "benchWeight"), width="stretch")
    with c2:
        card("Top 10 positions", "Largest holdings by market value against their benchmark weight.")
        act = C.holding_active(d["holdings"], d["benchmark"]).sort_values("weight", ascending=False).head(10)
        st.plotly_chart(K.compare_hbars(act, "ticker", "weight", "benchWeight"), width="stretch")


# ---------------------------------------------------------------- Risk
def risk(d):
    v = d["volstats"].set_index("metric")
    f = lambda m, col="portfolio": f"{v.loc[m, col]:.2f}" if v.loc[m, "unit"] == "num" else pct(v.loc[m, col])
    st.markdown("### Volatility")
    var_usd = v.loc["1-day VaR (95%)", "portfolio"] * d["summary"].totalValue.iloc[0]
    metrics([("Annualized volatility", f("Annualized volatility"), f"benchmark {f('Annualized volatility', 'benchmark')}"),
             ("Volatility, last 3 months", f("Vol, last 3 months"), f"benchmark {f('Vol, last 3 months', 'benchmark')}"),
             ("Downside deviation", f("Downside deviation"), f"benchmark {f('Downside deviation', 'benchmark')}"),
             ("Sortino ratio", f("Sortino ratio"), f"benchmark {f('Sortino ratio', 'benchmark')}"),
             ("1-day VaR (95%)", f("1-day VaR (95%)"), f"−{usd(abs(var_usd))} on today's value"),
             ("1-day CVaR (95%)", f("1-day CVaR (95%)"), "average of the worst 5% of days")])
    c1, c2 = st.columns(2)
    with c1:
        card("Rolling volatility", "Annualized volatility over the trailing 63 trading days, weekly.")
        st.plotly_chart(K.lines(d["rollingvol"], "date", [("benchmark", "Benchmark", K.ORANGE), ("portfolio", "Portfolio", K.BLUE)], yfmt=".0%"), width="stretch")
    with c2:
        card("Daily return distribution", "Trading days by return, last 2 years. Dashed lines mark the 95% VaR and CVaR.")
        st.plotly_chart(K.histogram_with_lines(d["dailyreturns"].portfolio, [(v.loc["1-day VaR (95%)", "portfolio"], "VaR"), (v.loc["1-day CVaR (95%)", "portfolio"], "CVaR")]), width="stretch")
    with st.expander("Volatility profile: every measure, portfolio vs benchmark"):
        t = d["volstats"].copy()
        for c in ["portfolio", "benchmark"]:
            t[c] = [f"{x:.2f}" if u == "num" else f"{x:.2%}" for x, u in zip(t[c], t.unit)]
        st.dataframe(t[["metric", "portfolio", "benchmark"]].rename(columns=str.capitalize), hide_index=True, width="stretch")

    st.markdown("### Tracking error & factors")
    te = C.te_split(d["riskmodel"])
    s = d["summary"].iloc[0]
    active_beta = d["riskmodel"].set_index("factor").activeExposure.astype(float)["Market (beta)"]
    metrics([("Predicted tracking error", pct(te["predictedTE"]), "risk model, annualized"),
             ("Realized tracking error", pct(s.trackingError), "daily returns, 2 years"),
             ("Factor risk", pct(te["factorShare"]), "of tracking-error variance"),
             ("Stock-specific risk", pct(te["specificShare"]), "of tracking-error variance"),
             ("Active beta", f"{active_beta:+.2f}", "portfolio minus benchmark")])
    c1, c2 = st.columns(2)
    with c1:
        card("Tracking error by risk source", "Share of tracking-error variance from each factor group; shares add to 100%.")
        g = C.te_groups(d["riskmodel"])
        st.plotly_chart(K.diverging(g, "group", "pctOfTE", fmt=".1%"), width="stretch")
    with c2:
        card("Contribution by factor", "Each factor's share of tracking-error variance.")
        rm = d["riskmodel"][d["riskmodel"].group != "Specific"].copy()
        groups = ["All"] + sorted(rm.group.unique())
        pick = st.segmented_control("Factor group", groups, default="All", key="te_group", label_visibility="collapsed")
        sub = rm if pick in (None, "All") else rm[rm.group == pick]
        sub = sub.reindex(sub.pctOfTE.abs().sort_values(ascending=False).index).head(12)
        st.plotly_chart(K.diverging(sub, "factor", "pctOfTE", fmt=".1%", neg=K.ORANGE), width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        fa = d["factors"]
        alpha = fa.set_index("factor").loading["Alpha (ann.)"]
        card("Fama-French-Carhart regression", f"Daily portfolio excess returns on market, size, value and momentum. Annualized alpha {spct(alpha)}, R² {s.r2:.2f}.")
        ff = fa[fa.factor != "Alpha (ann.)"].copy()
        ff["label"] = [f"{l:+.2f} (t {t:.1f})" for l, t in zip(ff.loading, ff.tStat)]
        fig = K.hbars(ff, "factor", "loading", fmt=".2f", colors=[K.BLUE if abs(t) >= 2 else K.ORANGE for t in ff.tStat])
        fig.update_traces(text=ff.label.iloc[::-1])
        st.plotly_chart(fig, width="stretch")
    with c2:
        card("Total risk contribution vs weight", f"Share of portfolio volatility each holding drives against its share of value. Top five holdings are {pct(s.top5Weight)} of value.")
        h = d["holdings"].sort_values("riskContribution", ascending=False)
        st.plotly_chart(K.compare_hbars(h, "ticker", "riskContribution", "weight", "Risk share", "Weight"), width="stretch")
    card("Active factor exposures", "Portfolio and benchmark exposure to every factor in the model.")
    st.dataframe(d["riskmodel"], hide_index=True, width="stretch",
                 column_config={"factorVol": st.column_config.NumberColumn("Factor vol", format="%.1f%%"),
                                "teContribution": st.column_config.NumberColumn("TE contrib.", format="%.4f"),
                                "pctOfTE": st.column_config.ProgressColumn("Share of TE", min_value=-0.1, max_value=0.5, format="%.3f")})


# ---------------------------------------------------------------- Attribution
def attribution(d):
    win = st.segmented_control("Period", ["1M", "3M", "YTD", "1Y", "Since start"], default="3M", key="attr_win")
    win = win or "3M"
    s = d["attrsummary"].set_index("window").loc[win]
    a = d["attribution"][d["attribution"].window == win].sort_values("contribution", ascending=False)
    metrics([("Portfolio return", spct(s.portReturn), f"{fdate(s.start)} to {fdate(s.end)}"),
             ("Benchmark return", spct(s.benchReturn), "same period"),
             ("Excess return", spct(s.excess), "portfolio minus benchmark"),
             ("Top contributor", a.ticker.iloc[0], pts(a.contribution.iloc[0])),
             ("Top detractor", a.ticker.iloc[-1], pts(a.contribution.iloc[-1]))])
    c1, c2 = st.columns(2)
    with c1:
        card("Contribution by position", "Weight × daily return, linked so the bars add up to the portfolio return.")
        st.plotly_chart(K.diverging(a, "ticker", "contribution", fmt=".2%"), width="stretch")
    with c2:
        card("Contribution by theme")
        th = C.attr_theme(d["attribution"])
        st.plotly_chart(K.diverging(th[th.window == win], "theme", "contribution", fmt=".2%"), width="stretch")
    card("Contribution across periods", "Percentage points of portfolio return; green added, red detracted.")
    w = C.attr_wide(d["attribution"], d["holdings"]).sort_values("Since start", ascending=False)
    cols = ["1M", "3M", "YTD", "1Y", "Since start"]
    st.dataframe(K.heat_style(w, cols).format({"weight": "{:.1%}"}), hide_index=True, width="stretch")


# ---------------------------------------------------------------- Private equity
def private_equity(d):
    f = C.pe_funds(d["pefunds"])
    q = C.pe_quarterly(d["pecashflows"])
    s = C.pe_summary(f, q)
    calls = C.capital_calls(d["capitalcalls"])
    od = calls[calls.status == "Overdue"]
    metrics([("Commitments", usd(s["commitment"]), f"{s['funds']} funds"),
             ("Paid-in capital", usd(s["called"]), f"{pct(s['calledPct'])} of commitments"),
             ("Distributions", usd(s["distributed"]), f"DPI {s['dpi']:.2f}×"),
             ("Net asset value", usd(s["nav"]), f"as of {fdate(s['navDate'])}"),
             ("Unfunded commitments", usd(s["unfunded"]), "still callable")])
    metrics([("TVPI", f"{s['tvpi']:.2f}×", f"RVPI {s['rvpi']:.2f}×"),
             ("Net IRR, pooled", pct(s["irr"]), "since inception"),
             ("KS-PME", f"{s['pme']:.2f}", "above 1 beats public equity"),
             ("Overdue capital calls", usd(od.outstanding.sum()), f"{len(od)} notices past due")])
    c1, c2 = st.columns(2)
    with c1:
        card("Cash flows and J-curve", "Calls (down), distributions (up) and cumulative net cash flow.")
        st.plotly_chart(K.jcurve(q), width="stretch")
    with c2:
        card("Multiple by fund", "TVPI split into DPI (returned) and RVPI (still held). Dashed line is 1.0×.")
        st.plotly_chart(K.stacked_hbars(f.sort_values("tvpi", ascending=False), "fund", [("dpi", "DPI", K.BLUE), ("rvpi", "RVPI", K.ORANGE)], fmt=".2f", ref=1.0), width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        card("Public market equivalent", f"Kaplan-Schoar PME by fund; above 1.0 beat public equity. Whole program {s['pme']:.2f}.")
        pm = f[["fund", "ksPME"]].assign(rel=f.ksPME - 1)
        fig = K.diverging(pm, "fund", "rel", fmt=".2f", neg=K.RED)
        fig.update_traces(text=[f"{v + 1:.2f}" for v in pm.sort_values("rel").rel], hovertemplate="%{y}: PME %{text}<extra></extra>")
        fig.update_xaxes(tickformat=".2f", title="PME − 1")
        st.plotly_chart(fig, width="stretch")
    with c2:
        card("Projected capital calls", "Expected calls over the next four quarters.")
        pc = d["pecalls"].groupby("quarter", as_index=False).projectedCall.sum()
        cash = d["holdings"][d["holdings"].assetClass == "Cash"].value.sum()
        st.caption(f"Cash & T-bills cover them {cash / pc.projectedCall.sum():.1f} times over.")
        st.plotly_chart(K.grouped_bars(pc, "quarter", [("projectedCall", "Projected calls", K.ORANGE)], yfmt="$,.0f", height=260), width="stretch")
    card("Capital call notices", f"Status as of {fdate(calls.asOf.iloc[0])}. A call is overdue once its due date passes with any amount unpaid.")
    order = {"Overdue": 0, "Pending": 1, "Paid late": 2, "Paid": 3}
    cv = calls.sort_values("status", key=lambda s_: s_.map(order)).drop(columns=["days", "asOf"])
    st.dataframe(status_style(cv).format({"called": "${:,.0f}", "outstanding": lambda v: f"${v:,.0f}" if v > 0.005 else ""}), hide_index=True, width="stretch")
    card("Funds", "Performance by fund, net of fees, at the latest NAV.")
    st.dataframe(f[["fund", "strategy", "vintage", "commitment", "called", "distributed", "nav", "unfunded", "dpi", "tvpi", "netIRR", "ksPME"]]
                 .style.format({"commitment": "${:,.0f}", "called": "${:,.0f}", "distributed": "${:,.0f}", "nav": "${:,.0f}", "unfunded": "${:,.0f}",
                                "dpi": "{:.2f}×", "tvpi": "{:.2f}×", "netIRR": "{:.1%}", "ksPME": "{:.2f}"}), hide_index=True, width="stretch")


# ---------------------------------------------------------------- Operations
def operations(d):
    h = d["holdings"]
    exp = C.exposure(h, d["benchmark"], d["industrymap"])
    te = C.te_split(d["riskmodel"])
    comp = C.compliance(h, exp, d["summary"], te)
    rb = C.rebalance(h, d["targets"])
    rc = C.recon(h, d["custodian"], d["transactions"])
    tx = d["transactions"]
    cash = h[h.assetClass == "Cash"]
    pend = tx[tx.status == "Pending"]
    total = h.value.sum()
    metrics([("Guideline breaches", str((comp.status == "Breach").sum()), f"{(comp.status == 'Watch').sum()} on watch"),
             ("Reconciliation breaks", str((rc.status == "Break").sum()), f"{(rc.status == 'Timing').sum()} timing differences"),
             ("Pending settlements", ("+" if pend.amount.sum() >= 0 else "−") + usd(abs(pend.amount.sum())), f"{len(pend)} trades, net cash"),
             ("Failed trades", str((tx.status == "Failed").sum()), "need rebooking"),
             ("Cash & T-bills", usd(cash.value.sum()), f"{pct(cash.weight.sum())} of assets"),
             ("Rebalance turnover", pct(rb.tradeValue.abs().sum() / 2 / total), "to reach targets")])

    card("Guideline compliance", "Investment guidelines checked against current positions and the risk model. Watch = within 10% of the limit.")
    cv = comp.copy()
    cv["current"] = [pct(c) if u == "pct" else f"{c:.2f}" for c, u in zip(cv.current, cv.unit)]
    cv["headroom"] = [spct(c) if u == "pct" else f"{c:+.2f}" for c, u in zip(cv.headroom, cv.unit)]
    st.dataframe(status_style(cv.drop(columns="unit").sort_values("status", key=lambda s: s.map({"Breach": 0, "Watch": 1, "OK": 2}))), hide_index=True, width="stretch")

    card("Client restrictions", "Exclusions from the client's investment policy, screened directly and through index funds where the rule says so.")
    xr = C.restrict_check(d["restrictions"], d["screening"], h)
    st.dataframe(status_style(xr).format({"indirectExposure": lambda v: f"{v:.2%}" if v else "None", "indirectValue": lambda v: usd(v) if v else ""}),
                 hide_index=True, width="stretch")
    p = C.pre_trade(d["restrictedlist"], tx, rb, h)
    st.caption(esc(f"Pre-trade check: {p['screened']} pending, recent and proposed trades and {p['held']} holdings screened against a restricted list of "
               f"{p['listSize']} securities: " + ("**restricted: " + ", ".join(p["hits"]) + "**" if p["hits"] else "**no matches**.")))

    card("Holdings reconciliation: portfolio system vs custodians",
         f"Portfolio system {usd(rc.pmsValue.sum())} vs custodians {usd(rc.custodianValue.sum())}, a difference of {rc.valueDiff.sum():+,.2f}.")
    c1, c2 = st.columns([3, 2])
    with c1:
        nm = rc[rc.status != "Matched"]
        fig = K.diverging(nm, "position", "valueDiff", fmt=",.0f")
        fig.update_traces(marker_color=[K.RED if s == "Break" else K.ORANGE for s in nm.sort_values("valueDiff").status])
        st.plotly_chart(fig, width="stretch")
    with c2:
        ct = d["custodian"].groupby("custodian", as_index=False).agg(positions=("ticker", "count"), marketValue=("marketValue", "sum"))
        st.dataframe(ct.style.format({"marketValue": "${:,.0f}"}), hide_index=True, width="stretch")
    rv = rc.sort_values("status", key=lambda s: s.map({"Break": 0, "Timing": 1, "Matched": 2}))
    st.dataframe(status_style(rv).format({"pmsQty": "{:,.2f}", "custodianQty": "{:,.2f}", "qtyDiff": "{:+,.2f}", "pmsPrice": "${:,.2f}", "custodianPrice": "${:,.2f}",
                                          "pmsValue": "${:,.0f}", "custodianValue": "${:,.0f}", "valueDiff": "{:+,.2f}"}, na_rep=""), hide_index=True, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        card("Drift from target", "Current weight minus target; beyond ±0.5 points is flagged.")
        st.plotly_chart(K.diverging(rb, "ticker", "drift", fmt=".1%", pos=K.RED, neg=K.BLUE), width="stretch")
    with c2:
        card("Rebalancing trades", "Trades that would bring each flagged position back to target, at current prices.")
        st.dataframe(rb[rb.action != "Hold"][["ticker", "action", "drift", "shares", "tradeValue"]].sort_values("tradeValue", key=abs, ascending=False)
                     .style.format({"drift": "{:+.1%}", "shares": "{:+,}", "tradeValue": "${:+,.0f}"}), hide_index=True, width="stretch")
    card("Trade blotter", "Recent trades and cash movements with settlement status.")
    st.dataframe(status_style(tx).format({"price": "${:,.2f}", "amount": "{:+,.2f}", "quantity": "{:,.0f}"}, na_rep=""), hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        card("Expected dividend income", "Estimated cash dividends on current shares, by pay month.")
        ca = d["corpactions"]
        inc = ca[ca.estCash > 0].assign(month=lambda x: x.payDate.str[:7]).groupby("month", as_index=False).estCash.sum()
        st.plotly_chart(K.grouped_bars(inc, "month", [("estCash", "Estimated cash", K.BLUE)], yfmt="$,.0f", height=260), width="stretch")
    with c2:
        card("Upcoming corporate actions")
        st.dataframe(d["corpactions"].style.format({"amountPerShare": "${:.2f}", "estCash": "${:,.2f}"}), hide_index=True, width="stretch")


# ---------------------------------------------------------------- Balance sheet
def balance_sheet(d):
    f = C.pe_funds(d["pefunds"])
    bs, sm = C.balance_sheet(d["holdings"], f, d["otherassets"], d["liabilities"])
    out = C.outflows_12m(d["outflows"], d["pecalls"])
    metrics([("Net worth", usd(sm["netWorth"]), f"{usd(sm['netWorthBefore'])} before expected liabilities"),
             ("Total assets", usd(sm["totalAssets"]), f"{pct(sm['liquidShare'])} liquid"),
             ("Debt", usd(sm["debt"]), f"{pct(sm['debtToAssets'])} of assets"),
             ("Expected liabilities", usd(sm["expected"]), "taxes, pledges, PE commitments"),
             ("Outflows, next 12 months", usd(out.amount.sum()), "debt service, taxes, calls, pledges"),
             ("Liquidity coverage", f"{sm['liquid'] / out.amount.sum():.1f}×", "liquid assets ÷ 12-month outflows")])
    c1, c2 = st.columns([1, 1])
    with c1:
        card("Consolidated balance sheet", f"Deferred tax uses a {C.DEFERRED_TAX_RATE:.1%} federal rate on public-market gains only; state tax excluded.")
        styl = bs.copy()
        styl["Value"] = [("" if v is None or pd.isna(v) else usd(v)) for v in styl.value]
        styl["% of assets"] = [("" if pd.isna(v) else pct(v)) for v in styl.shareOfAssets]
        def row_style(r):
            k = bs.loc[r.name, "kind"]
            s = {"section": "font-weight:600; color:#8a8f98", "subtotal": "font-weight:600", "total": "font-weight:700; font-size:1.05em; border-top:2px solid"}.get(k, "")
            return [s] * len(r)
        st.dataframe(styl[["line", "Value", "% of assets"]].rename(columns={"line": "Line"}).style.apply(row_style, axis=1),
                     hide_index=True, width="stretch", height=min(800, 36 * len(styl) + 40))
    with c2:
        card("Assets by type", "Colored by how quickly each could become cash.")
        items = bs[(bs.kind == "item") & (bs.value > 0)].sort_values("value", ascending=False)
        cmap = {"Liquid": K.BLUE, "Semi-liquid": K.ORANGE, "Illiquid": K.PURPLE, "Mixed": K.TEAL}
        st.plotly_chart(K.hbars(items, "line", "value", fmt="$,.0f", colors=[cmap.get(l, K.TEAL) for l in items.liquidity]), width="stretch")
        card("Liquidity vs commitments", "Assets by liquidity against 12-month outflows and all debt plus expected liabilities.")
        lq = pd.DataFrame({"bucket": ["Liquid", "Semi-liquid", "Illiquid"], "value": [sm["liquid"], sm["semiLiquid"], sm["illiquid"]]})
        fig = K.hbars(lq, "bucket", "value", fmt="$,.0f", colors=[K.BLUE, K.ORANGE, K.PURPLE])
        fig.add_vline(x=out.amount.sum(), line_dash="dash", annotation_text="12-mo outflows")
        fig.add_vline(x=sm["debt"] + sm["expected"], annotation_text="Debt + expected")
        st.plotly_chart(fig, width="stretch")
    card("Expected cash outflows, next 12 months", "Debt service, taxes, insurance, pledges and projected capital calls by quarter.")
    st.plotly_chart(K.stacked_bars(out, "quarter", "type", "amount"), width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        card("Real assets and other holdings")
        st.dataframe(d["otherassets"].drop(columns="id").style.format({"value": "${:,.0f}"}), hide_index=True, width="stretch")
    with c2:
        card("Liabilities")
        st.dataframe(d["liabilities"].drop(columns="id").style.format({"balance": "${:,.0f}", "rate": lambda v: f"{v:.2%}" if v else "", "nextPayment": "${:,.0f}"}),
                     hide_index=True, width="stretch")


# ---------------------------------------------------------------- Holdings
def holdings(d):
    f = C.pe_funds(d["pefunds"])
    ah = C.all_holdings(d["holdings"], d["custodian"], f, C.holding_active(d["holdings"], d["benchmark"]))
    pub, priv = ah[ah.market == "Public"].value.sum(), ah[ah.market == "Private"].value.sum()
    metrics([("Total portfolio", usd(pub + priv), f"{len(ah)} holdings"),
             ("Public markets", usd(pub), f"{pct(pub / (pub + priv))} of total, at market"),
             ("Private equity", usd(priv), f"{pct(priv / (pub + priv))} of total, at NAV"),
             ("Unfunded commitments", usd(f.unfunded.sum()), "not included in total")])
    c1, c2 = st.columns([1, 2])
    seg = c1.segmented_control("Market", ["All", "Public", "Private"], default="All", key="hold_seg") or "All"
    q = c2.text_input("Search holdings", placeholder="Ticker, name, category or custodian", label_visibility="collapsed")
    v = ah if seg == "All" else ah[ah.market == seg]
    if q:
        v = v[v[["holding", "name", "category", "source"]].apply(lambda r: q.lower() in " ".join(map(str, r)).lower(), axis=1)]
    st.dataframe(v.sort_values("value", ascending=False), hide_index=True, width="stretch", height=620,
                 column_config={"quantity": st.column_config.NumberColumn("Quantity", help="Shares, or commitment for private funds", format="%,.0f"),
                                "price": st.column_config.NumberColumn("Price", format="$%.2f"),
                                "value": st.column_config.NumberColumn("Value", format="$%,.0f"),
                                "weight": st.column_config.ProgressColumn("Weight", min_value=0, max_value=0.15, format="%.3f"),
                                "gain": st.column_config.NumberColumn("Gain", format="%.3f"),
                                "benchWeight": st.column_config.NumberColumn("Bench wt", format="%.4f"),
                                "active": st.column_config.NumberColumn("Active", format="%+.4f"),
                                "source": st.column_config.TextColumn("Source / custodian"),
                                "asOf": st.column_config.TextColumn("As of")})


# ---------------------------------------------------------------- News
def news(d):
    n = d["news"]
    st.caption(f"Refreshed {datetime.fromisoformat(n.refreshed.max()).strftime('%b %-d, %Y %-I:%M %p')} · {len(n)} items. "
               "Summaries are brief; follow each link for the full story. Replace data/news.json (or wire up a news API in pmdemo/news.py) to update.")
    w = d["holdings"].set_index("ticker").weight
    c1, c2 = st.columns(2)
    with c1:
        card("Market news", "Markets, rates, the economy and sector moves, newest first.")
        for _, r in n[n.scope == "Market"].sort_values("date", ascending=False).iterrows():
            st.caption(f"{fdate(r.date)} · {esc(r.category)} · [{esc(r.source)}]({r.url})")
            st.markdown(esc(r.summary))
            st.divider()
    with c2:
        card("News on your holdings", "Company news and upcoming earnings, largest holdings first.")
        hn = n[n.scope == "Holding"].copy()
        hn["w"] = hn.ticker.map(w).fillna(0)
        tickers = list(hn.sort_values("w", ascending=False).ticker.unique())
        pick = st.segmented_control("Holding", ["All"] + tickers, default="All", key="news_tk", label_visibility="collapsed") or "All"
        if pick != "All":
            hn = hn[hn.ticker == pick]
        for _, r in hn.sort_values(["w", "date"], ascending=[False, False]).iterrows():
            st.caption(f"**{r.ticker}** · {fdate(r.date)} · {esc(r.category)} · [{esc(r.source)}]({r.url})")
            st.markdown(esc(r.summary))
            st.divider()
        quiet = [t for t in w.index if t not in tickers]
        if quiet:
            st.caption("No recent news found for " + ", ".join(quiet) + ".")
