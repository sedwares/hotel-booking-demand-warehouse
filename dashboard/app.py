"""
Hotel Booking Demand Dashboard.

Run locally (outside Docker) with:
    pip install -r requirements.txt
    streamlit run dashboard/app.py

Expects the Postgres warehouse (docker compose up) to be reachable on
localhost:5433 with the dbt marts already built (dbt run).
"""
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(".")
from scripts.db import get_engine

st.set_page_config(page_title="Hotel Booking Demand", layout="wide")
st.title("Hotel Booking Demand Warehouse")
st.caption(
    "Real PMS extract, two European hotels, arrivals Jul 2015-Aug 2017 "
    "(Antonio, Almeida & Nunes, 2019). Occupancy/RevPAR use an inferred "
    "room-capacity floor — see the README for the reasoning."
)

engine = get_engine()

# Fixed categorical color order (never cycled) so "City Hotel" and
# "Resort Hotel" keep the same color across every chart on the page.
HOTEL_COLORS = {"City Hotel": "#2a78d6", "Resort Hotel": "#eb6834"}
LEAD_TIME_ORDER = ["0 (same day)", "1-7 days", "8-30 days", "31-90 days", "91-180 days", "180+ days"]


@st.cache_data(ttl=300)
def _cancel_rates(dim: str) -> pd.DataFrame:
    # Aggregated straight from fact_bookings, NOT from mart_cancellation_risk:
    # that mart drops segment combinations with <5 bookings (to avoid noisy
    # 0%/100% rows), so re-aggregating it would silently skew rare categories.
    return pd.read_sql(
        f"select hotel, {dim}, count(*) as bookings, "
        f"sum(case when is_canceled then 1 else 0 end) as cancellations, "
        f"avg(case when is_canceled then 1.0 else 0 end) as cancellation_rate "
        f"from analytics.fact_bookings group by 1, 2",
        engine,
    )


def cancel_rates(dim: str, hotels) -> pd.DataFrame:
    df = _cancel_rates(dim)
    return df[df["hotel"].isin(hotels)].copy()


@st.cache_data(ttl=300)
def load(table: str) -> pd.DataFrame:
    return pd.read_sql(f"select * from analytics.{table}", engine)


daily = load("mart_daily_metrics")
comparison = load("mart_hotel_comparison")
cancellation = load("mart_cancellation_risk")
mismatch = load("mart_room_assignment_mismatch")

if daily.empty:
    st.warning(
        "No data found in analytics.mart_daily_metrics. "
        "Run `python scripts/load_raw_data.py` then `dbt run` first."
    )
    st.stop()

daily["date_day"] = pd.to_datetime(daily["date_day"])

# --- Sidebar filters ---
hotels = st.sidebar.multiselect("Hotels", options=list(HOTEL_COLORS), default=list(HOTEL_COLORS))
min_date, max_date = daily["date_day"].min(), daily["date_day"].max()
date_range = st.sidebar.date_input("Date range", (min_date, max_date), min_value=min_date, max_value=max_date)

daily_f = daily[daily["hotel"].isin(hotels)]
if len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    daily_f = daily_f[(daily_f["date_day"] >= start) & (daily_f["date_day"] <= end)]

tab_overview, tab_cancellation, tab_channels, tab_rooms = st.tabs(
    ["Overview", "Cancellation Risk", "Channel Mix", "Room Assignment"]
)

# --- Overview tab ---
with tab_overview:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Occupancy", f"{daily_f['occupancy_rate'].mean() * 100:.1f}%")
    col2.metric("Avg ADR", f"€{daily_f['adr'].mean():.2f}")
    col3.metric("Avg RevPAR", f"€{daily_f['revpar'].mean():.2f}")
    col4.metric("Nights in view", f"{daily_f['date_day'].nunique():,}")

    st.subheader("Occupancy rate by hotel")
    fig_occ = px.line(
        daily_f, x="date_day", y="occupancy_rate", color="hotel",
        color_discrete_map=HOTEL_COLORS,
        labels={"occupancy_rate": "Occupancy", "date_day": "Date", "hotel": "Hotel"},
    )
    fig_occ.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_occ, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("RevPAR by hotel")
        fig_revpar = px.line(
            daily_f, x="date_day", y="revpar", color="hotel",
            color_discrete_map=HOTEL_COLORS,
            labels={"revpar": "RevPAR (€)", "date_day": "Date", "hotel": "Hotel"},
        )
        st.plotly_chart(fig_revpar, use_container_width=True)
    with col_b:
        st.subheader("ADR by hotel")
        fig_adr = px.line(
            daily_f, x="date_day", y="adr", color="hotel",
            color_discrete_map=HOTEL_COLORS,
            labels={"adr": "ADR (€)", "date_day": "Date", "hotel": "Hotel"},
        )
        st.plotly_chart(fig_adr, use_container_width=True)

    st.subheader("Resort vs. City — side by side")
    display_cols = [
        "hotel", "total_bookings", "cancellation_rate", "avg_lead_time",
        "avg_adr", "avg_length_of_stay", "avg_occupancy_rate", "avg_revpar",
        "top_market_segment", "top_distribution_channel",
    ]
    st.dataframe(comparison[display_cols], use_container_width=True, hide_index=True)

# --- Cancellation Risk tab ---
with tab_cancellation:
    st.subheader("Cancellation rate by lead time")
    lead_time_agg = cancel_rates("lead_time_bucket", hotels)
    lead_time_agg["lead_time_bucket"] = pd.Categorical(
        lead_time_agg["lead_time_bucket"], categories=LEAD_TIME_ORDER, ordered=True
    )
    lead_time_agg = lead_time_agg.sort_values("lead_time_bucket")

    fig_lead = px.bar(
        lead_time_agg, x="lead_time_bucket", y="cancellation_rate", color="hotel",
        color_discrete_map=HOTEL_COLORS, barmode="group",
        labels={"cancellation_rate": "Cancellation Rate", "lead_time_bucket": "Booking Lead Time", "hotel": "Hotel"},
    )
    fig_lead.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_lead, use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("By deposit type")
        deposit_agg = cancel_rates("deposit_type", hotels)
        fig_dep = px.bar(
            deposit_agg, x="deposit_type", y="cancellation_rate", color="hotel",
            color_discrete_map=HOTEL_COLORS, barmode="group",
            labels={"cancellation_rate": "Cancellation Rate", "deposit_type": "Deposit Type", "hotel": "Hotel"},
        )
        fig_dep.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig_dep, use_container_width=True)
    with col_d:
        st.subheader("By customer type")
        cust_agg = cancel_rates("customer_type", hotels)
        fig_cust = px.bar(
            cust_agg, x="customer_type", y="cancellation_rate", color="hotel",
            color_discrete_map=HOTEL_COLORS, barmode="group",
            labels={"cancellation_rate": "Cancellation Rate", "customer_type": "Customer Type", "hotel": "Hotel"},
        )
        fig_cust.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig_cust, use_container_width=True)

    with st.expander("Full segmented cancellation-risk table"):
        st.dataframe(
            cancellation[cancellation["hotel"].isin(hotels)].sort_values("cancellation_rate", ascending=False),
            use_container_width=True, hide_index=True,
        )

# --- Channel Mix tab ---
with tab_channels:
    st.subheader("Bookings by market segment")
    segment_agg = (
        cancellation[cancellation["hotel"].isin(hotels)]
        .groupby(["hotel", "market_segment"], as_index=False)["bookings"].sum()
    )
    fig_seg = px.bar(
        segment_agg, x="market_segment", y="bookings", color="hotel",
        color_discrete_map=HOTEL_COLORS, barmode="group",
        labels={"bookings": "Bookings", "market_segment": "Market Segment", "hotel": "Hotel"},
    )
    st.plotly_chart(fig_seg, use_container_width=True)

# --- Room Assignment tab ---
with tab_rooms:
    st.subheader("Reserved vs. assigned room type (honored stays)")
    mismatch_f = mismatch[mismatch["hotel"].isin(hotels)]
    mismatch_summary = (
        mismatch_f.groupby("hotel", as_index=False)
        .apply(
            lambda g: pd.Series({
                "total_bookings": g["bookings"].sum(),
                "mismatched_bookings": g.loc[~g["is_match"], "bookings"].sum(),
            }),
            include_groups=False,
        )
    )
    mismatch_summary["mismatch_rate"] = mismatch_summary["mismatched_bookings"] / mismatch_summary["total_bookings"]

    col_e, col_f = st.columns(2)
    for i, row in mismatch_summary.iterrows():
        (col_e if i % 2 == 0 else col_f).metric(
            f"{row['hotel']} — room reassignment rate", f"{row['mismatch_rate'] * 100:.1f}%"
        )

    st.dataframe(
        mismatch_f[~mismatch_f["is_match"]].sort_values("bookings", ascending=False),
        use_container_width=True, hide_index=True,
    )
