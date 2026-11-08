
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
from datetime import datetime

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
# MODERN DARK DASHBOARD THEME
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

div[data-testid="stDataFrame"] {
    border: 1px solid #263449;
    border-radius: 10px;
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
    border-color: #64748B;
    color: #FFFFFF;
}

hr {
    border-color: #263449;
}

.market-card {
    background-color: #151F32;
    border: 1px solid #263449;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 12px;
}

.buy-card {
    background-color: #123326;
    border: 1px solid #166534;
    border-radius: 12px;
    padding: 22px;
    margin-top: 12px;
    margin-bottom: 20px;
}

.wait-card {
    background-color: #1E293B;
    border: 1px solid #475569;
    border-radius: 12px;
    padding: 22px;
    margin-top: 12px;
    margin-bottom: 20px;
}

.section-label {
    color: #94A3B8;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.5px;
    margin-bottom: 8px;
}

.small-note {
    color: #94A3B8;
    font-size: 12px;
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

    df = pd.DataFrame()

    for t in ASSETS:
        df[f"{t}_Close"] = data[t]["Close"].astype(float)

    df["VIX"] = data["^VIX"]["Close"].astype(float)

    df = df.dropna()

    for t in ASSETS:
        df[f"{t}_FG"] = calculate_fg(
            df[f"{t}_Close"],
            df["VIX"]
        )

    return df


# ============================================================
# HEADER
# ============================================================

col_logo, col_refresh = st.columns([4, 1])

with col_logo:

    st.markdown("""
    <div style="padding-bottom:10px;">
        <div style="
            font-size:30px;
            font-weight:800;
            letter-spacing:1px;
            color:#F8FAFC;">
            MARKET PULSE
        </div>
        <div style="
            font-size:12px;
            letter-spacing:3px;
            color:#94A3B8;">
            FEAR & GREED DAILY SCREENER
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_refresh:

    st.write("")

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

    if df.empty:
        st.error("No market data returned. Please try again later.")
        st.stop()

except Exception as e:

    st.error(f"Unable to retrieve market data: {e}")
    st.info("Please refresh the page or try again later.")
    st.stop()


# ============================================================
# LATEST MARKET DATA
# ============================================================

latest_date = df.index[-1].strftime("%d %b %Y")

buy_signals = []

asset_data = []

for t in ASSETS:

    current_fg = df[f"{t}_FG"].iloc[-1]

    current_price = df[f"{t}_Close"].iloc[-1]

    is_buy = current_fg < FG_THRESH

    if is_buy:
        buy_signals.append(t)

    asset_data.append({
        "Asset": t,
        "Price": current_price,
        "FG Score": current_fg,
        "Signal": "BUY" if is_buy else "WAIT"
    })


# ============================================================
# MARKET OVERVIEW
# ============================================================

st.markdown(
    '<div class="section-label">MARKET OVERVIEW</div>',
    unsafe_allow_html=True
)

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

st.markdown("")

st.markdown(
    '<div class="section-label">ASSET MONITOR</div>',
    unsafe_allow_html=True
)

asset_df = pd.DataFrame(asset_data)


def colour_signal(val):

    if val == "BUY":
        return "color: #4ADE80; font-weight: bold"

    return "color: #94A3B8"


styled_df = (
    asset_df.style
    .format({
        "Price": "${:,.2f}",
        "FG Score": "{:.2f}"
    })
    .map(colour_signal, subset=["Signal"])
    .map(
        lambda x: "color: #4ADE80; font-weight: bold"
        if x < FG_THRESH else "color: #F8FAFC",
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

st.markdown("")

if buy_signals:

    st.markdown(f"""
    <div class="buy-card">

        <div style="
            color:#4ADE80;
            font-size:12px;
            font-weight:700;
            letter-spacing:2px;">
            ⚡ ACTION REQUIRED TOMORROW
        </div>

        <div style="
            color:#FFFFFF;
            font-size:28px;
            font-weight:800;
            margin-top:10px;">
            BUY {" + ".join(buy_signals)}
        </div>

        <div style="
            color:#BBF7D0;
            font-size:13px;
            margin-top:10px;">
            Execution: Next Trading Day Open
            <br>
            Suggested order type: Market-On-Open (MOO)
        </div>

    </div>
    """, unsafe_allow_html=True)

else:

    st.markdown("""
    <div class="wait-card">

        <div style="
            color:#CBD5E1;
            font-size:12px;
            font-weight:700;
            letter-spacing:2px;">
            NO BUY SIGNALS
        </div>

        <div style="
            color:#FFFFFF;
            font-size:23px;
            font-weight:700;
            margin-top:10px;">
            No action required
        </div>

        <div style="
            color:#94A3B8;
            font-size:13px;
            margin-top:10px;">
            No assets currently meet the Fear & Greed threshold.
        </div>

    </div>
    """, unsafe_allow_html=True)


# ============================================================
# RECENT SIGNAL HISTORY
# ============================================================

st.markdown("")

st.markdown(
    '<div class="section-label">'
    'RECENT SIGNAL HISTORY | LAST 10 SIGNAL DATES'
    '</div>',
    unsafe_allow_html=True
)

mask = (
    df[[f"{t}_FG" for t in ASSETS]] < FG_THRESH
).any(axis=1)

signal_days = df[mask].tail(10)

history = []

for date, row in signal_days.iterrows():

    triggered_tickers = []

    for t in ASSETS:

        if row[f"{t}_FG"] < FG_THRESH:
            triggered_tickers.append(t)

    history.append({
        "Date": date.strftime("%d %b %Y"),
        "Triggered Assets": "  ·  ".join(triggered_tickers)
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
# FEAR & GREED HISTORY CHART
# ============================================================

st.markdown("")

st.markdown(
    '<div class="section-label">FEAR & GREED TREND</div>',
    unsafe_allow_html=True
)

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
    "Historical Fear & Greed score. "
    "BUY threshold: below 30."
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
        "Data source: Yahoo Finance | Automated screening tool"
    )

st.caption(
    "Disclaimer: This dashboard provides algorithmic market "
    "indicators for informational purposes only. "
    "It is not financial advice."
)
