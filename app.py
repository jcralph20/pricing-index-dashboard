import json
from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fred_client import FredClient

st.set_page_config(page_title="Index Dashboard", layout="wide")

CONFIG = json.load(open("config.json", "r"))
TITLE = CONFIG.get("app_title", "Index Hub")

st.title(TITLE)

# Sidebar controls
series_cfg = CONFIG["series"]

categories = sorted({s["category"] for s in series_cfg})
selected_categories = st.sidebar.multiselect("Categories", categories, default=categories)

series_in_scope = [s for s in series_cfg if s["category"] in selected_categories]
series_names = [s["name"] for s in series_in_scope]

selected_series_names = st.sidebar.multiselect("Series", series_names, default=series_names)
selected_series = [s for s in series_in_scope if s["name"] in selected_series_names]

range_label = st.sidebar.selectbox("Range", ["1Y", "3Y", "5Y", "10Y", "MAX"], index=2)

def range_to_start(label: str) -> str:
    if label == "MAX":
        return ""
    years = int(label.replace("Y", ""))
    start = date.today() - relativedelta(years=years)
    return start.isoformat()

start_date = range_to_start(range_label)

show_change = st.sidebar.checkbox("Show % change cards", value=True)

client = FredClient()

# Layout: a compact grid of charts
cols = st.columns(2)

def make_line(df: pd.DataFrame, name: str, y_label: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["value"], mode="lines", name=name))
    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=40, b=35),
        xaxis_title="",
        yaxis_title=y_label,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, zeroline=False)
    return fig


def card_metrics(df: pd.DataFrame):
    if df.empty or len(df) < 2:
        return None
    last = df.iloc[-1]["value"]
    prev = df.iloc[-2]["value"]
    abs_change = last - prev
    pct_change = (abs_change / prev * 100.0) if prev != 0 else None
    return last, abs_change, pct_change


def human_units(preferred_view: str):
    return "Price" if preferred_view == "spot" else "Index"


def render_one(s, col):
    sid = s["series_id"]
    name = s["name"]
    preferred_view = s.get("preferred_view", "index")

    try:
        df = client.get_series(sid, observation_start=start_date)
    except Exception as e:
        with col:
            st.error(f"{name} ({sid})

{e}")
        return

    with col:
        st.subheader(name)
        if show_change:
            m = card_metrics(df)
            if m:
                last, abs_change, pct_change = m
                c1, c2, c3 = st.columns(3)
                c1.metric("Latest", f"{last:,.3f}")
                c2.metric("Δ vs prior", f"{abs_change:,.3f}")
                if pct_change is None:
                    c3.metric("% Δ vs prior", "—")
                else:
                    c3.metric("% Δ vs prior", f"{pct_change:,.2f}%")
            else:
                st.caption("Not enough observations for change metrics.")

        fig = make_line(df, name=name, y_label=human_units(preferred_view))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Show data table"):
            st.dataframe(df, use_container_width=True, hide_index=True)


# Render in a 2-column grid
for i, s in enumerate(selected_series):
    render_one(s, cols[i % 2])

st.caption("Data source: FRED API (St. Louis Fed) / underlying publishers noted in each series on FRED.")
