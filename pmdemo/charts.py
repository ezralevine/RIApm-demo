"""Plotly chart helpers shared by every tab, in one consistent style."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

BLUE = "#2f6fde"
ORANGE = "#e8833a"
RED = "#d64545"
GREEN = "#2e9e6a"
PURPLE = "#7a5bd6"
TEAL = "#1a9aa0"
GREY = "#8a8f98"
SERIES = [BLUE, ORANGE, TEAL, PURPLE, GREEN, "#c2507a", "#b8902c", GREY]

def pyfmt(v, fmt: str, sign: bool = False) -> str:
    """Format like a d3/Plotly spec (e.g. '$,.0f', '.1%') in Python."""
    pre = "$" if fmt.startswith("$") else ""
    f = fmt.lstrip("$")
    if sign:
        s = format(abs(v), f)
        return ("+" if v >= 0 else "−") + pre + s
    return ("−" if v < 0 and pre else "") + pre + format(abs(v) if pre else v, f)


FONT = dict(family="Inter, -apple-system, Segoe UI, sans-serif", size=13)


def _layout(fig: go.Figure, height: int, **kw) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=8, b=8), font=FONT, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.08, x=0, title=None),
                      hoverlabel=dict(font=FONT), **kw)
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    return fig


def lines(df: pd.DataFrame, x: str, series: list[tuple[str, str, str]], yfmt: str = ",.0f", height=340, prefix="") -> go.Figure:
    """series: (column, label, color)."""
    fig = go.Figure()
    for col, label, color in series:
        fig.add_scatter(x=pd.to_datetime(df[x]), y=df[col], name=label, mode="lines", line=dict(color=color, width=2),
                        hovertemplate=f"%{{x|%b %d, %Y}}<br>{label}: {prefix}%{{y:{yfmt}}}<extra></extra>")
    fig.update_yaxes(tickformat=yfmt, tickprefix=prefix)
    return _layout(fig, height, hovermode="x unified")


def grouped_bars(df: pd.DataFrame, x: str, series: list[tuple[str, str, str]], yfmt=".1%", height=340) -> go.Figure:
    fig = go.Figure()
    for col, label, color in series:
        fig.add_bar(x=df[x], y=df[col], name=label, marker_color=color, hovertemplate=f"%{{x}}<br>{label}: %{{y:{yfmt}}}<extra></extra>")
    fig.update_yaxes(tickformat=yfmt)
    return _layout(fig, height, barmode="group", bargap=0.25)


def compare_hbars(df: pd.DataFrame, label: str, a: str, b: str, a_name="Portfolio", b_name="Benchmark", fmt=".1%", height=None) -> go.Figure:
    """Two horizontal bars per row (e.g. portfolio vs benchmark weight), with active shown in hover."""
    d = df.iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=d[label], x=d[b], name=b_name, orientation="h", marker_color=ORANGE, hovertemplate=f"%{{y}}<br>{b_name}: %{{x:{fmt}}}<extra></extra>")
    fig.add_bar(y=d[label], x=d[a], name=a_name, orientation="h", marker_color=BLUE, text=[pyfmt(v, fmt) for v in d[a]], textposition="outside",
                customdata=(d[a] - d[b]), hovertemplate=f"%{{y}}<br>{a_name}: %{{x:{fmt}}}<br>Active: %{{customdata:+{fmt}}}<extra></extra>")
    fig.update_xaxes(tickformat=fmt)
    return _layout(fig, height or max(220, 46 * len(df) + 60), barmode="group", bargap=0.3, bargroupgap=0.05)


def diverging(df: pd.DataFrame, label: str, value: str, fmt=".2%", height=None, pos=BLUE, neg=RED, hover=None) -> go.Figure:
    d = df.sort_values(value)
    colors = [pos if v >= 0 else neg for v in d[value]]
    fig = go.Figure(go.Bar(y=d[label], x=d[value], orientation="h", marker_color=colors, text=[pyfmt(v, fmt, sign=True) for v in d[value]],
                           textposition="outside", hovertemplate=hover or f"%{{y}}: %{{x:+{fmt}}}<extra></extra>"))
    fig.add_vline(x=0, line_color=GREY, line_width=1)
    fig.update_xaxes(tickformat=fmt)
    return _layout(fig, height or max(220, 28 * len(df) + 60), showlegend=False)


def hbars(df: pd.DataFrame, label: str, value: str, fmt=".1%", colors=None, height=None, text_fmt=None) -> go.Figure:
    d = df.iloc[::-1]
    c = colors[::-1] if colors is not None else BLUE
    fig = go.Figure(go.Bar(y=d[label], x=d[value], orientation="h", marker_color=c,
                           text=[pyfmt(v, text_fmt or fmt) for v in d[value]], textposition="outside",
                           hovertemplate=f"%{{y}}: %{{x:{fmt}}}<extra></extra>"))
    fig.update_xaxes(tickformat=fmt)
    return _layout(fig, height or max(200, 34 * len(df) + 50), showlegend=False)


def stacked_hbars(df: pd.DataFrame, label: str, parts: list[tuple[str, str, str]], fmt=",.0f", ref=None, height=None) -> go.Figure:
    d = df.iloc[::-1]
    fig = go.Figure()
    for col, name, color in parts:
        fig.add_bar(y=d[label], x=d[col], name=name, orientation="h", marker_color=color, hovertemplate=f"%{{y}}<br>{name}: %{{x:{fmt}}}<extra></extra>")
    if ref is not None:
        fig.add_vline(x=ref, line_dash="dash", line_color=GREY, annotation_text=f"{ref:g}×", annotation_position="top")
    fig.update_xaxes(tickformat=fmt)
    return _layout(fig, height or max(220, 38 * len(df) + 70), barmode="stack", bargap=0.35)


def stacked_bars(df: pd.DataFrame, x: str, color: str, value: str, fmt=",.0f", height=320, prefix="$") -> go.Figure:
    fig = go.Figure()
    for i, (name, g) in enumerate(df.groupby(color, sort=False)):
        fig.add_bar(x=g[x], y=g[value], name=name, marker_color=SERIES[i % len(SERIES)],
                    hovertemplate=f"%{{x}}<br>{name}: {prefix}%{{y:{fmt}}}<extra></extra>")
    fig.update_yaxes(tickformat=fmt, tickprefix=prefix)
    return _layout(fig, height, barmode="stack", bargap=0.4)


def histogram_with_lines(values: pd.Series, marks: list[tuple[float, str]], height=320) -> go.Figure:
    fig = go.Figure(go.Histogram(x=values, xbins=dict(size=0.0025), marker_color=BLUE, hovertemplate="%{x}<br>%{y} days<extra></extra>"))
    for v, lab in marks:
        fig.add_vline(x=v, line_dash="dash", line_color=RED, annotation_text=lab, annotation_position="top left")
    fig.update_xaxes(tickformat="+.0%")
    return _layout(fig, height, showlegend=False, bargap=0.05)


def jcurve(q: pd.DataFrame, height=360) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=q.quarter, y=q.distributions, name="Distributions", marker_color=BLUE, hovertemplate="%{x}<br>Distributions: $%{y:,.0f}<extra></extra>")
    fig.add_bar(x=q.quarter, y=-q.calls, name="Calls", marker_color=ORANGE, hovertemplate="%{x}<br>Calls: $%{y:,.0f}<extra></extra>")
    fig.add_scatter(x=q.quarter, y=q.cumulative, name="Cumulative net", mode="lines", line=dict(color=PURPLE, width=2.5),
                    hovertemplate="%{x}<br>Cumulative net: $%{y:,.0f}<extra></extra>")
    t = q.loc[q.cumulative.idxmin()]
    fig.add_annotation(x=t.quarter, y=t.cumulative, text=f"Trough ${t.cumulative:,.0f}", showarrow=True, arrowhead=0, ay=30)
    fig.update_yaxes(tickformat=",.0f", tickprefix="$")
    return _layout(fig, height, barmode="relative", bargap=0.2)


def heat_style(df: pd.DataFrame, cols: list[str], scale=0.03):
    """Pandas Styler that shades contributions green/red by size."""
    def color(v):
        if pd.isna(v):
            return ""
        a = min(1, abs(v) / scale) * 0.35
        rgb = "46,158,106" if v >= 0 else "214,69,69"
        return f"background-color: rgba({rgb},{a:.2f})"
    return df.style.map(color, subset=cols).format({c: (lambda v: f"{v * 100:+.2f}") for c in cols})
