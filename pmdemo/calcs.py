"""Every calculation the app shows, as plain functions over the data files.

Each function mirrors one panel of the dashboard so it can be tested and
swapped out independently (for example, replace `compliance` limits with a
client's real investment policy).
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

DEFERRED_TAX_RATE = 0.238  # US federal long-term rate incl. 3.8% NIIT; state tax not included


# ---------- Public markets ----------

def kpis(summary: pd.DataFrame) -> dict:
    s = summary.iloc[0]
    gain = s.totalValue - s.totalCost
    return {
        **s.to_dict(),
        "gain": gain,
        "gainPct": gain / s.totalCost,
        "excess": s.portReturn - s.benchReturn,
    }


def holding_active(holdings: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    bw = benchmark[benchmark.dimension == "holding"].set_index("group").benchWeight
    out = holdings[["ticker", "weight"]].copy()
    out["benchWeight"] = out.ticker.map(bw).fillna(0.0)
    out["active"] = out.weight - out.benchWeight
    return out


def exposure(holdings: pd.DataFrame, benchmark: pd.DataFrame, industrymap: pd.DataFrame) -> pd.DataFrame:
    """Portfolio vs benchmark weight by theme, industry, asset class and country."""
    rows = []
    for dim in ["theme", "industry", "assetClass", "country"]:
        if dim == "industry":
            m = industrymap.merge(holdings[["ticker", "weight"]], on="ticker")
            m["w"] = m.weight * m.share
            port = m.groupby("industry").w.sum()
        elif dim == "assetClass":
            g = np.where(holdings.assetClass == "Equity",
                         np.where(holdings.country == "US", "US equity", "International equity"),
                         holdings.assetClass)
            port = holdings.assign(g=g).groupby("g").weight.sum()
        else:
            port = holdings.groupby(dim).weight.sum()
        bench = benchmark[benchmark.dimension == dim].set_index("group").benchWeight
        groups = list(dict.fromkeys(list(port.index) + list(bench.index)))
        for g in groups:
            w, b = float(port.get(g, 0.0)), float(bench.get(g, 0.0))
            rows.append({"dimension": dim, "group": g, "weight": w, "benchWeight": b, "active": w - b})
    return pd.DataFrame(rows)


def top_theme(exp: pd.DataFrame) -> pd.Series:
    return exp[exp.dimension == "theme"].sort_values("weight", ascending=False).iloc[0]


def top_active_theme(exp: pd.DataFrame) -> pd.Series:
    return exp[exp.dimension == "theme"].sort_values("active", ascending=False).iloc[0]


def te_split(riskmodel: pd.DataFrame) -> dict:
    return {
        "predictedTE": riskmodel.teContribution.sum(),
        "factorShare": riskmodel[riskmodel.group != "Specific"].pctOfTE.sum(),
        "specificShare": riskmodel[riskmodel.group == "Specific"].pctOfTE.sum(),
    }


def te_groups(riskmodel: pd.DataFrame) -> pd.DataFrame:
    return (riskmodel.groupby("group", as_index=False)[["pctOfTE", "teContribution"]].sum()
            .sort_values("pctOfTE", ascending=False))


def attr_theme(attribution: pd.DataFrame) -> pd.DataFrame:
    return attribution.groupby(["window", "theme"], as_index=False).contribution.sum()


def attr_wide(attribution: pd.DataFrame, holdings: pd.DataFrame) -> pd.DataFrame:
    w = attribution.pivot_table(index="ticker", columns="window", values="contribution")
    out = holdings[["ticker", "theme", "weight"]].set_index("ticker").join(w).reset_index()
    order = ["1M", "3M", "YTD", "1Y", "Since start"]
    return out[["ticker", "theme", "weight"] + [c for c in order if c in out]]


# ---------- Operations ----------

GUIDELINES = [  # name, kind, limit, unit
    ("Max single position", "max", 0.10, "pct"),
    ("Max single theme", "max", 0.35, "pct"),
    ("Top-five concentration", "max", 0.45, "pct"),
    ("Max single non-US country", "max", 0.15, "pct"),
    ("Max equity", "max", 0.90, "pct"),
    ("Min cash & T-bills", "min", 0.05, "pct"),
    ("Max predicted tracking error", "max", 0.08, "pct"),
    ("Max beta to benchmark", "max", 1.20, "num"),
]


def compliance(holdings, exp, summary, te) -> pd.DataFrame:
    s = summary.iloc[0]
    top = holdings.sort_values("weight", ascending=False).iloc[0]
    theme = exp[exp.dimension == "theme"].sort_values("weight", ascending=False).iloc[0]
    nonus = exp[(exp.dimension == "country") & ~exp.group.isin(["US", "International"])].sort_values("weight", ascending=False).iloc[0]
    w = lambda cls: holdings[holdings.assetClass.isin(cls)].weight.sum()
    current = {
        "Max single position": (top.weight, top.ticker),
        "Max single theme": (theme.weight, theme.group),
        "Top-five concentration": (s.top5Weight, "five largest holdings"),
        "Max single non-US country": (nonus.weight, nonus.group),
        "Max equity": (w(["Equity"]), "equities and equity ETFs"),
        "Min cash & T-bills": (w(["Cash"]), "T-bill ETF"),
        "Max predicted tracking error": (te["predictedTE"], "risk model"),
        "Max beta to benchmark": (s.beta, "realized, 2 years"),
    }
    rows = []
    for name, kind, limit, unit in GUIDELINES:
        cur, driver = current[name]
        headroom = limit - cur if kind == "max" else cur - limit
        status = "Breach" if headroom < 0 else "Watch" if headroom < limit * 0.1 else "OK"
        lim = ("≤ " if kind == "max" else "≥ ") + (f"{limit:.0%}" if unit == "pct" else f"{limit:.2f}")
        rows.append({"status": status, "rule": name, "limit": lim, "current": cur, "headroom": headroom, "unit": unit, "driver": driver})
    return pd.DataFrame(rows)


def rebalance(holdings, targets, band=0.005) -> pd.DataFrame:
    total = holdings.value.sum()
    t = targets.set_index("ticker").targetWeight
    df = holdings[["ticker", "weight", "price"]].copy()
    df["target"] = df.ticker.map(t).fillna(0.0)
    df["drift"] = df.weight - df.target
    flagged = df.drift.abs() > band
    df["shares"] = np.where(flagged, np.round(-df.drift * total / df.price), 0).astype(int)
    df["tradeValue"] = df.shares * df.price
    df["action"] = np.where(df.shares > 0, "Buy", np.where(df.shares < 0, "Sell", "Hold"))
    return df


def recon(holdings, custodian, transactions) -> pd.DataFrame:
    """Portfolio system vs custodian positions, with explanations from open trades."""
    as_of = custodian.asOf.iloc[0]
    tickers = list(dict.fromkeys(list(holdings.ticker) + list(custodian.ticker)))
    h = holdings.set_index("ticker")
    rows = []
    for tk in tickers:
        cs = custodian[custodian.ticker == tk]
        in_pms = tk in h.index
        pms_sh = float(h.shares[tk]) if in_pms else 0.0
        cust_sh = float(cs.shares.sum())
        pms_px = float(h.price[tk]) if in_pms else None
        cust_px = float(cs.price.iloc[0]) if len(cs) else None
        pms_val = float(h.value[tk]) if in_pms else 0.0
        cust_val = float(cs.marketValue.sum())
        diff = pms_sh - cust_sh
        status, note = "Matched", ""
        if not in_pms:
            status, note = "Break", "At custodian, not in portfolio system: book the position"
        elif not len(cs):
            status, note = "Break", "In portfolio system, not at any custodian: confirm delivery"
        elif abs(diff) > 1e-6:
            tr = transactions[(transactions.ticker == tk) & (transactions.status != "Settled") & (pd.to_numeric(transactions.quantity, errors="coerce") == diff)]
            if tr.empty:
                status, note = "Break", "Unexplained quantity difference: investigate"
            else:
                tr = tr.iloc[0]
                when = datetime.strptime(tr.settleDate, "%Y-%m-%d").strftime("%b %-d")
                if tr.status == "Failed":
                    status, note = "Break", f"Failed {tr.type.lower()} {tr.id} still booked in portfolio system: rebook or cancel"
                elif tr.settleDate > as_of:
                    status, note = "Timing", f"Pending {tr.type.lower()} {tr.id} settles {when}"
                else:
                    status, note = "Break", f"{tr.type} {tr.id} was due {when} and not received: chase custodian"
        elif pms_px and cust_px and abs(cust_px / pms_px - 1) > 0.001:
            status, note = "Break", "Price differs from the portfolio system: check pricing source"
        held_at = ", ".join(dict.fromkeys(c.split(" · ")[0].replace("Custodian ", "") for c in cs.custodian))
        rows.append({"status": status, "position": tk, "heldAt": held_at, "pmsQty": pms_sh, "custodianQty": cust_sh, "qtyDiff": diff,
                     "pmsPrice": pms_px, "custodianPrice": cust_px, "pmsValue": pms_val, "custodianValue": cust_val,
                     "valueDiff": pms_val - cust_val, "explanation": note})
    return pd.DataFrame(rows)


def restrict_check(restrictions, screening, holdings) -> pd.DataFrame:
    total = holdings.value.sum()
    w = holdings.set_index("ticker").weight
    rows = []
    for _, r in restrictions.iterrows():
        sc = screening[(screening.category == r.category) & screening.ticker.isin(w.index)]
        direct = sc[(sc.basis == "Revenue share") & (sc.share >= r.threshold)].ticker.tolist()
        via = sc[(sc.basis == "Fund look-through") & (sc.share > 0)]
        indirect = float((via.ticker.map(w) * via.share).sum())
        look = bool(re.search("look-through", r.scope, re.I))
        funds = ", ".join(via.ticker)
        if direct:
            status, action = "Breach", "Sell " + ", ".join(direct)
        elif indirect > 0 and look:
            status, action = "Breach", f"Replace {funds} with screened index funds"
        elif indirect > 0:
            status, action = "Review", f"No direct holdings; indirect via {funds}: confirm with client"
        else:
            status, action = "Compliant", "No exposure"
        label = r.restriction + (f" (over {r.threshold:.0%} of revenue)" if r.threshold > 0 else " (zero tolerance)")
        rows.append({"status": status, "restriction": label, "appliesTo": r.scope, "directHoldings": ", ".join(direct) or "None",
                     "indirectExposure": indirect, "indirectValue": indirect * total, "action": action})
    return pd.DataFrame(rows)


def pre_trade(restrictedlist, transactions, rebal, holdings) -> dict:
    lst = set(restrictedlist.ticker)
    trades = [t for t in transactions.ticker if t] + rebal[rebal.action != "Hold"].ticker.tolist()
    hits = sorted({t for t in trades + holdings.ticker.tolist() if t in lst})
    return {"screened": len(trades), "held": len(holdings), "listSize": len(lst), "hits": hits}


# ---------- Private equity ----------

def pe_funds(pefunds: pd.DataFrame) -> pd.DataFrame:
    df = pefunds.copy()
    df["unfunded"] = df.commitment - df.called
    df["dpi"] = df.distributed / df.called
    df["rvpi"] = df.nav / df.called
    df["tvpi"] = df.dpi + df.rvpi
    return df


def pe_quarterly(pecashflows: pd.DataFrame) -> pd.DataFrame:
    q = pecashflows.groupby("quarter", as_index=False)[["calls", "distributions"]].sum().sort_values("quarter")
    q["net"] = q.distributions - q.calls
    q["cumulative"] = q.net.cumsum()
    return q


def irr(cashflows, periods_per_year=4) -> float:
    npv = lambda r: sum(c / (1 + r) ** (i / periods_per_year) for i, c in enumerate(cashflows))
    lo, hi = -0.9, 2.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def pe_summary(funds: pd.DataFrame, quarterly: pd.DataFrame) -> dict:
    c, called, dist, nav = funds.commitment.sum(), funds.called.sum(), funds.distributed.sum(), funds.nav.sum()
    cf = quarterly.net.tolist()
    cf[-1] += nav
    return {"funds": len(funds), "commitment": c, "called": called, "calledPct": called / c, "distributed": dist, "nav": nav,
            "unfunded": c - called, "dpi": dist / called, "rvpi": nav / called, "tvpi": (dist + nav) / called,
            "irr": irr(cf), "pme": float((funds.ksPME * funds.nav).sum() / nav), "navDate": funds.navDate.iloc[0]}


def capital_calls(capitalcalls: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c in capitalcalls.iterrows():
        d = lambda s: date.fromisoformat(s)
        as_of, due = d(c.asOf), d(c.dueDate)
        paid = float(c.paidAmount or 0)
        out = float(c.amount) - paid
        if out > 0.005 and due < as_of:
            status, days = "Overdue", (as_of - due).days
            label = f"{days} days overdue" + (" (partly paid)" if paid else "")
        elif out > 0.005:
            status, days = "Pending", (due - as_of).days
            label = f"due in {days} days"
        elif c.paidDate and d(c.paidDate) > due:
            status, days = "Paid late", (d(c.paidDate) - due).days
            label = f"paid {days} days late"
        else:
            status, days, label = "Paid", 0, "paid on time"
        rows.append({"status": status, "notice": c.callId, "fund": c.fund, "noticeDate": c.noticeDate, "dueDate": c.dueDate,
                     "called": float(c.amount), "outstanding": out, "timing": label, "days": days, "asOf": c.asOf})
    return pd.DataFrame(rows)


# ---------- Whole portfolio ----------

def all_holdings(holdings, custodian, funds, active) -> pd.DataFrame:
    pub_total, priv_total = holdings.value.sum(), funds.nav.sum()
    total = pub_total + priv_total
    act = active.set_index("ticker")
    rows = []
    for _, h in holdings.iterrows():
        accts = list(dict.fromkeys(custodian[custodian.ticker == h.ticker].custodian))
        rows.append({"holding": h.ticker, "name": h["name"], "market": "Public", "category": f"{h.assetClass} · {h.sector}",
                     "quantity": h.shares, "price": h.price, "value": h.value, "weight": h.value / total, "gain": h.gainPct,
                     "benchWeight": act.benchWeight.get(h.ticker), "active": act.active.get(h.ticker),
                     "source": " + ".join(accts) if accts else "Not at any custodian", "asOf": custodian.asOf.iloc[0]})
    for _, f in funds.iterrows():
        rows.append({"holding": f.fund, "name": f"{f.strategy} fund, {f.vintage} vintage", "market": "Private",
                     "category": f"Private equity · {f.strategy}", "quantity": f.commitment, "price": None, "value": f.nav,
                     "weight": f.nav / total, "gain": (f.distributed + f.nav - f.called) / f.called, "benchWeight": None,
                     "active": None, "source": "GP capital account statement", "asOf": f.navDate})
    return pd.DataFrame(rows)


def balance_sheet(holdings, funds, otherassets, liabilities) -> tuple[pd.DataFrame, dict]:
    cat = lambda c: otherassets[otherassets.category == c].value.sum()
    pub, pe = holdings.value.sum(), funds.nav.sum()
    assets = [("Bank cash", cat("Cash"), "Liquid"), ("Public markets (at market)", pub, "Liquid"),
              ("Private equity (at NAV)", pe, "Illiquid"), ("Real estate", cat("Real estate"), "Illiquid"),
              ("Art & collectibles", cat("Art & collectibles"), "Mixed"), ("Vehicles", cat("Vehicles"), "Semi-liquid")]
    ta = sum(a[1] for a in assets)
    debt = [(r["name"], r.balance) for _, r in liabilities[liabilities.kind == "Debt"].iterrows()]
    td = sum(d[1] for d in debt)
    gains = (holdings.value - holdings.costBasis).clip(lower=0).sum()
    expected = [(r["name"], r.balance) for _, r in liabilities[liabilities.kind == "Expected"].iterrows()]
    expected += [("Deferred tax on unrealized public gains", gains * DEFERRED_TAX_RATE),
                 ("Unfunded private-fund commitments", funds.unfunded.sum())]
    te = sum(e[1] for e in expected)
    rows = [("Assets", None, "section", "")] + [(a[0], a[1], "item", a[2]) for a in assets] + [("Total assets", ta, "subtotal", "")]
    rows += [("Debt", None, "section", "")] + [(d[0], -d[1], "item", "") for d in debt] + [("Total debt", -td, "subtotal", "")]
    rows += [("Net worth before expected liabilities", ta - td, "subtotal", "")]
    rows += [("Expected liabilities", None, "section", "")] + [(e[0], -e[1], "item", "") for e in expected]
    rows += [("Total expected liabilities", -te, "subtotal", ""), ("Net worth", ta - td - te, "total", "")]
    df = pd.DataFrame(rows, columns=["line", "value", "kind", "liquidity"])
    df["shareOfAssets"] = df.value.abs() / ta
    liquid = pub + cat("Cash")
    semi = otherassets[otherassets.liquidity == "Semi-liquid"].value.sum()
    illiquid = pe + otherassets[otherassets.liquidity == "Illiquid"].value.sum()
    summary = {"totalAssets": ta, "debt": td, "expected": te, "netWorth": ta - td - te, "netWorthBefore": ta - td,
               "liquid": liquid, "semiLiquid": semi, "illiquid": illiquid, "liquidShare": liquid / ta, "debtToAssets": td / ta}
    return df, summary


def outflows_12m(outflows: pd.DataFrame, pecalls: pd.DataFrame) -> pd.DataFrame:
    calls = pecalls.groupby("quarter", as_index=False).projectedCall.sum().rename(columns={"projectedCall": "amount"})
    calls["type"] = "Private-fund capital calls"
    return pd.concat([outflows, calls[["quarter", "type", "amount"]]]).groupby(["quarter", "type"], as_index=False).amount.sum()
