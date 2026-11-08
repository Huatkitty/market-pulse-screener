
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

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
# DARK DASHBOARD THEME
# ============================================================

st.markdown("""
<style>
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

h1, h2, h3 {
    color: #F8FAFC !important;
}

p, label {
    color: #CBD5E1;
}

[data-testid="stMetric"] {
    background: #151F32;
    border: 1px solid #263449;
    padding: 18px;
    border-radius: 12px;
}

[data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
}

[data-testid="stMetricValue"] {
    color: #F8FAFC !important;
}

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

div[data-testid="stDataFrame"] {
    border: 1px solid #263449;
    border-radius: 10px;
}

hr {
    border-color: #263449;
}

div[data-testid="stAlert"] {
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# FEAR & GREED CALCULATION
# ORIGINAL LOGIC - UNCHANGED
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
# DOWNLOAD AND PROCESS MARKET DATA
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
        raise ValueError("Yahoo Finance returned no market data.")

    df = pd.DataFrame()

    for ticker in ASSETS:

        if ticker not in data.columns.get_level_values(0):
            raise ValueError(f"Missing market data for {ticker}.")

        df[f"{ticker}_Close"] = data[ticker]["Close"].astype(float)

    if "^VIX" not in data.columns.get_level_values(0):
        raise ValueError("VIX market data is unavailable.")

    df["VIX"] = data["^VIX"]["Close"].astype(float)

    df = df.dropna()

    if df.empty:
        raise ValueError("No complete market data available.")

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

    if st.button("↻ Refresh Data", use_container_width=True):

        st.cache_data.clear()
        st.rerun()

st.divider()


# ============================================================
# LOAD MARKET DATA
# ============================================================

try:

    with st.spinner("Fetching market data from Yahoo Finance..."):

        df = load_market_data()

except Exception as error:

    st.error(f"Unable to retrieve market data: {error}")

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
    st.metric("SIGNAL DATE", latest_date)

with m2:
    st.metric("BUY SIGNALS", len(buy_signals))

with m3:
    st.metric("FG THRESHOLD", f"< {FG_THRESH}")

with m4:
    st.metric("ASSETS MONITORED", len(ASSETS))


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
        f"⚡ ACTION REQUIRED TOMORROW\n\n"
        f"BUY {' + '.join(buy_signals)}\n\n"
        f"Execution: Next Trading Day Open\n\n"
        f"Suggested order type: Market-On-Open (MOO)"
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
        "Triggered Assets": " · ".join(triggered_tickers)
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
# FEAR & GREED TREND
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

st.line_chart(
    chart_df,
    color="#4ADE80"
)

st.caption(
    "Historical Fear & Greed score | BUY threshold: below 30"
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
