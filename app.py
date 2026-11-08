
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import plotly.graph_objects as go

warnings.filterwarnings("ignore")


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Market Pulse | Fear & Greed",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CONFIGURATION
# ============================================================

ASSETS = ["SPY", "QQQ", "VGT", "VTI", "VT"]
FG_THRESH = 30


# ============================================================
# DASHBOARD THEME
# ============================================================

st.markdown("""
<style>

/* Main background */

.stApp {
    background-color: #0B1120;
    color: #F8FAFC;
}

header[data-testid="stHeader"] {
    background-color: #0B1120;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* Headings */

h1, h2, h3 {
    color: #F8FAFC !important;
}

p, label {
    color: #CBD5E1;
}

/* White Market Overview cards */

[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #D1D5DB;
    padding: 18px;
    border-radius: 12px;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p {
    color: #374151 !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] div {
    color: #111827 !important;
}

/* White Trading Decision alert */

div[data-testid="stAlert"] {
    background-color: #FFFFFF !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 12px;
}

div[data-testid="stAlert"] p,
div[data-testid="stAlert"] div,
div[data-testid="stAlert"] span {
    color: #111827 !important;
}

/* Buttons */

.stButton > button {
    background-color: #1E293B;
    color: #FFFFFF;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px 20px;
}

.stButton > button:hover {
    background-color: #334155;
    color: #FFFFFF;
    border-color: #64748B;
}

/* Dataframes */

div[data-testid="stDataFrame"] {
    border: 1px solid #263449;
    border-radius: 10px;
}

/* Dividers */

hr {
    border-color: #263449;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# FEAR & GREED CALCULATION
# ORIGINAL FORMULA - UNCHANGED
# ============================================================

def calculate_fg(close_series, vix_series):

    ma125 = close_series.rolling(
        125, min_periods=1
    ).mean()

    mom = close_series / ma125

    vix_z = (
        vix_series - vix_series.mean()
    ) / vix_series.std()

    def _norm(s):

        lo = s.rolling(
            252, min_periods=1
        ).min()

        hi = s.rolling(
            252, min_periods=1
        ).max()

        return (
            (s - lo) /
            (hi - lo).replace(0, 1)
            * 100
        )

    return (_norm(mom) + _norm(-vix_z)) / 2


# ============================================================
# MARKET DATA DOWNLOAD
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_market_data():

    tickers = ASSETS + ["^VIX"]

    data = yf.download(
        tickers,
        period="3y",
        auto_adjust=True,
        progress=False,
        group_by="ticker"
    )

    if data.empty:
        raise ValueError(
            "Yahoo Finance returned no market data."
        )

    # Handle either MultiIndex column arrangement
    def get_close(ticker):

        if isinstance(data.columns, pd.MultiIndex):

            if ticker in data.columns.get_level_values(0):
                return data[ticker]["Close"].astype(float)

            if ticker in data.columns.get_level_values(1):
                return data.xs(
                    ticker,
                    axis=1,
                    level=1
                )["Close"].astype(float)

            raise ValueError(
                f"Missing market data for {ticker}."
            )

        raise ValueError(
            "Unexpected Yahoo Finance data format."
        )

    df = pd.DataFrame()

    for ticker in ASSETS:
        df[f"{ticker}_Close"] = get_close(ticker)

    df["VIX"] = get_close("^VIX")

    # Preserve original complete-row filtering
    df = df.dropna()

    if df.empty:
        raise ValueError(
            "No complete market data available."
        )

    # Calculate Fear & Greed for each ETF
    for ticker in ASSETS:

        df[f"{ticker}_FG"] = calculate_fg(
            df[f"{ticker}_Close"],
            df["VIX"]
        )

    return df


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns([4, 1])

with header_left:

    st.markdown("# 📈 MARKET PULSE")

    st.caption("FEAR & GREED DAILY SCREENER")

with header_right:

    st.write("")

    if st.button(
        "↻ Refresh Data",
        use_container_width=True
    ):

        st.cache_data.clear()
        st.rerun()

st.divider()


# ============================================================
# LOAD MARKET DATA
# ============================================================

try:

    with st.spinner(
        "Fetching market data from Yahoo Finance..."
    ):

        df = load_market_data()

except Exception as error:

    st.error(
        f"Unable to retrieve market data: {error}"
    )

    st.info(
        "Please wait a moment and refresh the application. "
        "If the problem persists, check the deployment logs."
    )

    st.stop()


# ============================================================
# LATEST MARKET DATA
# ============================================================

latest_date = df.index[-1].strftime("%d %b %Y")

buy_signals = []

asset_data = []

for ticker in ASSETS:

    current_fg = df[f"{ticker}_FG"].iloc[-1]

    current_price = df[f"{ticker}_Close"].iloc[-1]

    is_buy = current_fg < FG_THRESH

    if is_buy:
        buy_signals.append(ticker)

    asset_data.append({
        "Asset": ticker,
        "Price": current_price,
        "FG Score": current_fg,
        "Signal": "BUY" if is_buy else "WAIT"
    })


# ============================================================
# MARKET OVERVIEW
# ============================================================

st.subheader("Market Overview")

m1, m2, m3, m4 = st.columns(4)

with m1:

    st.metric(
        "SIGNAL DATE",
        latest_date
    )

with m2:

    st.metric(
        "BUY SIGNALS",
        len(buy_signals)
    )

with m3:

    st.metric(
        "FG THRESHOLD",
        f"< {FG_THRESH}"
    )

with m4:

    st.metric(
        "ASSETS MONITORED",
        len(ASSETS)
    )


# ============================================================
# ASSET MONITOR
# ============================================================

st.divider()

st.subheader("Asset Monitor")

asset_df = pd.DataFrame(asset_data)


def colour_signal(value):

    if value == "BUY":
        return "color: #4ADE80; font-weight: bold"

    return "color: #94A3B8"


styled_df = (
    asset_df.style
    .format({
        "Price": "${:,.2f}",
        "FG Score": "{:.2f}"
    })
    .map(
        colour_signal,
        subset=["Signal"]
    )
    .map(
        lambda value:
            "color: #4ADE80; font-weight: bold"
            if value < FG_THRESH
            else "color: #F8FAFC",
        subset=["FG Score"]
    )
)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# TRADING DECISION
# ============================================================

st.divider()

st.subheader("Trading Decision")

if buy_signals:

    st.success(
        "⚡ ACTION REQUIRED TOMORROW\n\n"
        f"BUY {' + '.join(buy_signals)}\n\n"
        "Execution: Next Trading Day Open"
    )

else:

    st.info(
        "NO BUY SIGNALS\n\n"
        "No action required.\n\n"
        "No assets currently meet the Fear & Greed threshold."
    )


# ============================================================
# RECENT SIGNAL HISTORY
# ============================================================

st.divider()

st.subheader("Recent Signal History")

st.caption("Last 10 historical signal dates")

mask = (
    df[[f"{ticker}_FG" for ticker in ASSETS]]
    < FG_THRESH
).any(axis=1)

signal_days = df[mask].tail(10)

history = []

for date, row in signal_days.iterrows():

    triggered_tickers = []

    for ticker in ASSETS:

        if row[f"{ticker}_FG"] < FG_THRESH:
            triggered_tickers.append(ticker)

    history.append({
        "Date": date.strftime("%d %b %Y"),
        "Triggered Assets": " · ".join(
            triggered_tickers
        )
    })

if history:

    history_df = pd.DataFrame(history)

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("No historical signals found.")


# ============================================================
# FEAR & GREED TREND WITH COLOUR ZONES
# ============================================================

st.divider()

st.subheader("Fear & Greed Trend")

chart_asset = st.selectbox(
    "Select ETF",
    ASSETS,
    index=0
)

chart_df = df[
    [f"{chart_asset}_FG"]
].tail(252).copy()

chart_df.columns = ["Fear & Greed Score"]

fig = go.Figure()


# ------------------------------------------------------------
# COLOUR ZONES
# ------------------------------------------------------------

# Red: 0–30
fig.add_hrect(
    y0=0,
    y1=30,
    fillcolor="rgba(239, 68, 68, 0.28)",
    line_width=0,
    layer="below"
)

# Light yellow: 30–40
fig.add_hrect(
    y0=30,
    y1=40,
    fillcolor="rgba(250, 204, 21, 0.25)",
    line_width=0,
    layer="below"
)

# Neutral: 40–60
# Remains dark background intentionally

# Light green: 60–80
fig.add_hrect(
    y0=60,
    y1=80,
    fillcolor="rgba(134, 239, 172, 0.22)",
    line_width=0,
    layer="below"
)

# Green: 80–100
fig.add_hrect(
    y0=80,
    y1=100,
    fillcolor="rgba(34, 197, 94, 0.30)",
    line_width=0,
    layer="below"
)


# ------------------------------------------------------------
# FEAR & GREED LINE
# ------------------------------------------------------------

fig.add_trace(
    go.Scatter(
        x=chart_df.index,
        y=chart_df["Fear & Greed Score"],
        mode="lines",
        name="Fear & Greed",
        line=dict(
            color="#FFFFFF",
            width=2.5
        ),
        hovertemplate=(
            "Date: %{x|%d %b %Y}<br>"
            "FG Score: %{y:.2f}"
            "<extra></extra>"
        )
    )
)


# ------------------------------------------------------------
# REFERENCE THRESHOLD LINES
# ------------------------------------------------------------

for level, label in [
    (30, "FG 30"),
    (40, "FG 40"),
    (60, "FG 60"),
    (80, "FG 80")
]:

    fig.add_hline(
        y=level,
        line_dash="dash",
        line_color="#CBD5E1",
        line_width=1,
        annotation_text=label,
        annotation_position="top right",
        annotation_font_color="#FFFFFF"
    )


# ------------------------------------------------------------
# CHART LAYOUT
# ------------------------------------------------------------

fig.update_layout(

    height=480,

    template="plotly_dark",

    paper_bgcolor="#0B1120",

    plot_bgcolor="#151F32",

    margin=dict(
        l=20,
        r=35,
        t=40,
        b=25
    ),

    xaxis_title="Date",

    yaxis_title="Fear & Greed Score",

    yaxis=dict(
        range=[0, 100],
        tickmode="linear",
        dtick=10,
        gridcolor="#263449"
    ),

    xaxis=dict(
        gridcolor="#263449"
    ),

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),

    hovermode="x unified"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ------------------------------------------------------------
# CHART LEGEND
# ------------------------------------------------------------

st.markdown(
    """
    **Fear & Greed Zones**

    🔴 Below 30 — Extreme Fear / BUY zone

    🟡 30–40 — Fear

    ⚫ 40–60 — Neutral

    🟢 60–80 — Greed

    🟩 Above 80 — Extreme Greed
    """
)

st.caption(
    "Historical Fear & Greed score | "
    "BUY threshold: below 30"
)


# ============================================================
# FOOTER
# ============================================================

st.divider()

footer_left, footer_right = st.columns(2)

with footer_left:

    st.caption(
        f"MARKET PULSE | Last data date: {latest_date}"
    )

with footer_right:

    st.caption(
        "Data source: Yahoo Finance"
    )

st.caption(
    "Disclaimer: This dashboard provides algorithmic market "
    "indicators for informational purposes only. "
    "It is not financial advice."
)
