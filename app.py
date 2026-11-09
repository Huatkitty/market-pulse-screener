
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# ============================================================
# PAGE CONFIGURATION & CUSTOM HEARTBEAT FAVICON
# ============================================================

HEARTBEAT_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">
  <path d="M3 32 H24 L32 32 L40 12 L49 49 L59 23 L66 32 H97"
        fill="none"
        stroke="#12A89D"
        stroke-width="4"
        stroke-linecap="round"
        stroke-linejoin="round"/>
</svg>
"""

Path("heartbeat.svg").write_text(HEARTBEAT_SVG, encoding="utf-8")

st.set_page_config(
    page_title="Market Pulse | ETF Screener",
    page_icon="heartbeat.svg",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# SETTINGS
# ============================================================

ASSETS = ["SPY", "QQQ", "VGT", "VTI", "VT"]
FG_THRESH = 30
WATCH_THRESH = 40

LOOKBACK_MOMENTUM = 125
LOOKBACK_NORMALIZATION = 252

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>
    .stApp {
        background: #F4F7FA;
        color: #172B4D;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1450px;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .dashboard-header {
        background: linear-gradient(110deg, #102A43, #164E63);
        padding: 27px 32px;
        border-radius: 16px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 5px 18px rgba(16, 42, 67, 0.12);
    }

    .header-title {
        display: flex;
        align-items: center;
        gap: 15px;
        font-size: 30px;
        font-weight: 750;
        color: white;
        margin: 0;
    }

    .header-subtitle {
        color: #D7E6EE;
        font-size: 13px;
        margin-top: 8px;
        letter-spacing: 0.3px;
    }

    .section-title {
        color: #172B4D;
        font-size: 19px;
        font-weight: 700;
        margin-top: 18px;
        margin-bottom: 12px;
    }

    .metric-card {
        background: white;
        padding: 18px 20px;
        border-radius: 13px;
        border: 1px solid #E5EBF0;
        box-shadow: 0 3px 12px rgba(16, 42, 67, 0.045);
        min-height: 112px;
    }

    .metric-label {
        color: #718096;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }

    .metric-value {
        color: #172B4D;
        font-size: 27px;
        font-weight: 750;
        margin-top: 8px;
    }

    .metric-note {
        color: #718096;
        font-size: 12px;
        margin-top: 3px;
    }

    .decision-card {
        padding: 18px 20px;
        border-radius: 13px;
        margin: 10px 0 18px 0;
        border: 1px solid;
    }

    .decision-buy {
        background: #E8F7EF;
        border-color: #B8E5CB;
        color: #147D48;
    }

    .decision-watch {
        background: #FFF8E6;
        border-color: #F2DEA2;
        color: #9A6B00;
    }

    .decision-hold {
        background: #FDECEC;
        border-color: #F4C2C2;
        color: #C62828;
    }

    .decision-title {
        font-size: 17px;
        font-weight: 750;
        margin-bottom: 4px;
    }

    .decision-description {
        font-size: 13px;
        opacity: 0.9;
    }

    div.stButton > button {
        background: #12A89D;
        color: white;
        border: none;
        border-radius: 9px;
        padding: 8px 20px;
        font-weight: 650;
    }

    div.stButton > button:hover {
        background: #0D8C83;
        color: white;
        border: none;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #E5EBF0;
        border-radius: 10px;
        overflow: hidden;
    }

    .footer {
        color: #8492A6;
        font-size: 11px;
        text-align: center;
        margin-top: 35px;
        padding-top: 15px;
        border-top: 1px solid #E5EBF0;
    }

    @media (max-width: 700px) {
        .header-title {
            font-size: 23px;
        }

        .dashboard-header {
            padding: 20px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER WITH ECG HEARTBEAT LOGO
# ============================================================

st.markdown("""
<div class="dashboard-header">
    <div class="header-title">
        <svg width="75" height="48" viewBox="0 0 100 60"
             xmlns="http://www.w3.org/2000/svg">
            <path d="M3 32 H24 L32 32 L40 12 L49 49 L59 23 L66 32 H97"
                  fill="none"
                  stroke="#22D3C5"
                  stroke-width="4"
                  stroke-linecap="round"
                  stroke-linejoin="round"/>
        </svg>
        <span>Market Pulse</span>
    </div>
    <div class="header-subtitle">
        MARKET INTELLIGENCE
        &nbsp; | &nbsp;
        Fear &amp; Greed ETF Monitoring Dashboard
        &nbsp; | &nbsp;
        Powered by Yahoo Finance
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# DATA DOWNLOAD
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def download_market_data():

    tickers = ASSETS + ["^VIX"]

    raw = yf.download(
        tickers,
        period="3y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True
    )

    if raw.empty:
        raise ValueError("Yahoo Finance returned no market data.")

    result = pd.DataFrame(index=raw.index)

    for ticker in tickers:

        try:
            if isinstance(raw.columns, pd.MultiIndex):

                if (ticker, "Close") in raw.columns:
                    series = raw[(ticker, "Close")]

                elif ("Close", ticker) in raw.columns:
                    series = raw[("Close", ticker)]

                else:
                    continue

            else:
                if "Close" not in raw.columns:
                    continue

                series = raw["Close"]

            result[ticker] = series

        except (KeyError, TypeError):
            continue

    result = result.sort_index()
    result = result.ffill()

    required = ASSETS + ["^VIX"]
    missing = [ticker for ticker in required if ticker not in result.columns]

    if missing:
        raise ValueError(
            "Unable to retrieve data for: " + ", ".join(missing)
        )

    return result.dropna(subset=required)


# ============================================================
# FEAR & GREED CALCULATION
# ============================================================

def normalize_rolling(series, window=LOOKBACK_NORMALIZATION):

    rolling_min = series.rolling(
        window,
        min_periods=60
    ).min()

    rolling_max = series.rolling(
        window,
        min_periods=60
    ).max()

    denominator = rolling_max - rolling_min

    normalized = (
        (series - rolling_min) /
        denominator.replace(0, np.nan)
    ) * 100

    return normalized.clip(0, 100)


def calculate_fg(data, ticker):

    close = data[ticker]
    vix = data["^VIX"]

    # ETF momentum relative to its 125-day moving average
    moving_average = close.rolling(
        LOOKBACK_MOMENTUM,
        min_periods=LOOKBACK_MOMENTUM
    ).mean()

    momentum = (close / moving_average) - 1

    # VIX rolling z-score
    vix_mean = vix.rolling(
        LOOKBACK_MOMENTUM,
        min_periods=LOOKBACK_MOMENTUM
    ).mean()

    vix_std = vix.rolling(
        LOOKBACK_MOMENTUM,
        min_periods=LOOKBACK_MOMENTUM
    ).std()

    vix_zscore = (vix - vix_mean) / vix_std.replace(0, np.nan)

    # Normalize momentum and inverse VIX z-score
    momentum_score = normalize_rolling(momentum)

    inverse_vix_score = normalize_rolling(-vix_zscore)

    # Combined Fear & Greed score
    fg_score = (
        momentum_score + inverse_vix_score
    ) / 2

    return fg_score.clip(0, 100)


# ============================================================
# SIGNAL RULES
# ============================================================

def get_signal(score):

    if pd.isna(score):
        return "N/A"

    if score < FG_THRESH:
        return "BUY"

    elif score <= WATCH_THRESH:
        return "WATCH"

    else:
        return "HOLD"


def get_signal_colour(signal):

    colours = {
        "BUY": "#159957",
        "WATCH": "#B8860B",
        "HOLD": "#C62828",
        "N/A": "#718096"
    }

    return colours.get(signal, "#718096")


def get_fg_colour(score):

    if pd.isna(score):
        return "#718096"

    if score < FG_THRESH:
        return "#159957"

    elif score <= WATCH_THRESH:
        return "#B8860B"

    return "#C62828"


# ============================================================
# MANUAL REFRESH
# ============================================================

refresh_col1, refresh_col2 = st.columns([1, 5])

with refresh_col1:
    refresh_clicked = st.button(
        "↻ Refresh Market Data",
        use_container_width=True
    )

if refresh_clicked:
    download_market_data.clear()
    st.rerun()

# ============================================================
# LOAD DATA
# ============================================================

try:
    with st.spinner("Retrieving latest market data..."):
        market_data = download_market_data()

except Exception as error:
    st.error("Unable to retrieve market data.")
    st.exception(error)
    st.stop()

# ============================================================
# CALCULATE SCORES FOR ALL ETFs
# ============================================================

scores = pd.DataFrame(index=market_data.index)

for ticker in ASSETS:
    scores[ticker] = calculate_fg(market_data, ticker)

scores = scores.dropna(how="all")

if scores.empty:
    st.error("Insufficient historical data to calculate Fear & Greed scores.")
    st.stop()

latest_date = scores.index[-1]

# ============================================================
# MARKET OVERVIEW
# ============================================================

st.markdown(
    '<div class="section-title">Market Overview</div>',
    unsafe_allow_html=True
)

overview_rows = []

for ticker in ASSETS:

    score = scores[ticker].dropna().iloc[-1]
    signal = get_signal(score)

    overview_rows.append({
        "ETF": ticker,
        "Fear & Greed Score": round(float(score), 2),
        "Signal": signal
    })

overview_df = pd.DataFrame(overview_rows)

cols = st.columns(len(ASSETS))

for col, row in zip(cols, overview_rows):

    score = row["Fear & Greed Score"]
    signal = row["Signal"]

    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{row["ETF"]}</div>
            <div class="metric-value"
                 style="color:{get_fg_colour(score)}">
                {score:.2f}
            </div>
            <div style="
                color:{get_signal_colour(signal)};
                font-size:13px;
                font-weight:750;
                margin-top:5px;">
                {signal}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# CURRENT MARKET SIGNAL
# ============================================================

st.markdown(
    '<div class="section-title">Market Screener</div>',
    unsafe_allow_html=True
)

buy_count = sum(
    1 for row in overview_rows if row["Signal"] == "BUY"
)

watch_count = sum(
    1 for row in overview_rows if row["Signal"] == "WATCH"
)

hold_count = sum(
    1 for row in overview_rows if row["Signal"] == "HOLD"
)

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">BUY Signals</div>
        <div class="metric-value" style="color:#159957">
            {buy_count}
        </div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">WATCH Signals</div>
        <div class="metric-value" style="color:#B8860B">
            {watch_count}
        </div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">HOLD Signals</div>
        <div class="metric-value" style="color:#C62828">
            {hold_count}
        </div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Last Data Date</div>
        <div class="metric-value" style="font-size:20px">
            {latest_date.strftime("%d %b %Y")}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# BUY / NO BUY DECISION
# ============================================================

if buy_count > 0:

    decision_class = "decision-buy"
    decision_title = "BUY SIGNAL DETECTED"
    decision_description = (
        f"{buy_count} ETF(s) currently have a Fear & Greed "
        "score below 30."
    )

elif watch_count > 0:

    decision_class = "decision-watch"
    decision_title = "WATCH MARKET"
    decision_description = (
        "No BUY signal is currently available. "
        "Some ETFs are approaching the BUY threshold."
    )

else:

    decision_class = "decision-hold"
    decision_title = "NO BUY SIGNAL"
    decision_description = (
        "All ETFs are currently above the BUY threshold. "
        "Continue monitoring the market."
    )

st.markdown(f"""
<div class="decision-card {decision_class}">
    <div class="decision-title">{decision_title}</div>
    <div class="decision-description">{decision_description}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# ETF SELECTOR AND FEAR & GREED CHART
# ============================================================

st.markdown(
    '<div class="section-title">ETF Fear & Greed Analysis</div>',
    unsafe_allow_html=True
)

selected_etf = st.selectbox(
    "Select ETF",
    ASSETS,
    index=0
)

selected_scores = scores[selected_etf].dropna()
current_score = float(selected_scores.iloc[-1])
current_signal = get_signal(current_score)

chart_col1, chart_col2 = st.columns([3, 1])

with chart_col1:

    st.markdown("**Fear & Greed Trend**")

    fig = go.Figure()

    # Fear zone
    fig.add_hrect(
        y0=0, y1=30,
        fillcolor="rgba(220, 70, 70, 0.10)",
        line_width=0
    )

    # Watch zone
    fig.add_hrect(
        y0=30, y1=40,
        fillcolor="rgba(230, 180, 50, 0.12)",
        line_width=0
    )

    # Neutral zone
    fig.add_hrect(
        y0=40, y1=60,
        fillcolor="rgba(160, 170, 180, 0.08)",
        line_width=0
    )

    # Greed zone
    fig.add_hrect(
        y0=60, y1=80,
        fillcolor="rgba(60, 170, 120, 0.08)",
        line_width=0
    )

    # Extreme greed zone
    fig.add_hrect(
        y0=80, y1=100,
        fillcolor="rgba(30, 140, 100, 0.12)",
        line_width=0
    )

    fig.add_trace(go.Scatter(
        x=selected_scores.index,
        y=selected_scores.values,
        mode="lines",
        name=selected_etf,
        line=dict(
            color="#12A89D",
            width=2.5
        ),
        hovertemplate=(
            "%{x|%d %b %Y}<br>"
            "FG Score: %{y:.2f}"
            "<extra></extra>"
        )
    ))

    # Threshold lines
    for threshold, label in [
        (30, "BUY Threshold"),
        (40, "WATCH Threshold"),
        (60, "Greed"),
        (80, "Extreme Greed")
    ]:

        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="#8492A6",
            line_width=1,
            annotation_text=label,
            annotation_position="top left"
        )

    fig.update_layout(
        height=430,
        margin=dict(l=10, r=20, t=35, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(
            family="Arial",
            color="#172B4D"
        ),
        yaxis=dict(
            title="Fear & Greed Score",
            range=[0, 100],
            gridcolor="#E9EEF3",
            dtick=20
        ),
        xaxis=dict(
            title="",
            gridcolor="#F0F3F6",
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all", label="ALL")
                ],
                bgcolor="#F4F7FA",
                activecolor="#D7F3EF"
            ),
            rangeslider=dict(visible=False)
        ),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

with chart_col2:

    st.markdown("**Current Reading**")

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{selected_etf} FG Score</div>
        <div class="metric-value"
             style="color:{get_fg_colour(current_score)}">
            {current_score:.2f}
        </div>
        <div style="
            color:{get_signal_colour(current_signal)};
            font-size:16px;
            font-weight:750;
            margin-top:8px;">
            {current_signal}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    if current_signal == "BUY":
        st.success("ETF has reached the BUY zone.")

    elif current_signal == "WATCH":
        st.warning("ETF is approaching the BUY zone.")

    else:
        st.error("ETF is currently in the HOLD zone.")

# ============================================================
# HISTORICAL BUY SIGNALS
# ============================================================

st.markdown(
    '<div class="section-title">Historical BUY Signals</div>',
    unsafe_allow_html=True
)

history_rows = []

for ticker in ASSETS:

    ticker_scores = scores[ticker].dropna()

    for date, score in ticker_scores.items():

        if score < FG_THRESH:

            history_rows.append({
                "Date": date,
                "ETF": ticker,
                "Fear & Greed Score": round(float(score), 2),
                "Signal": "BUY"
            })

if history_rows:

    history_df = pd.DataFrame(history_rows)

    history_df = history_df.sort_values(
        "Date",
        ascending=False
    ).head(10)

    history_df["Date"] = history_df["Date"].dt.strftime("%d %b %Y")

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("No historical BUY signals found in the available data.")

# ============================================================
# DATA TABLE
# ============================================================

st.markdown(
    '<div class="section-title">ETF Screener Details</div>',
    unsafe_allow_html=True
)

display_df = overview_df.copy()

display_df["Fear & Greed Score"] = display_df[
    "Fear & Greed Score"
].map(lambda x: f"{x:.2f}")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

# ============================================================
# FOOTER
# ============================================================

st.markdown(f"""
<div class="footer">
    Market Pulse | ETF Fear &amp; Greed Screener<br>
    Data source: Yahoo Finance
    &nbsp; | &nbsp;
    Last retrieved: {datetime.now().strftime("%d %b %Y, %H:%M:%S")}<br>
    For informational and research purposes only. Not financial advice.
</div>
""", unsafe_allow_html=True)
