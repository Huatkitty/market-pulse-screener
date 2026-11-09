
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Market Pulse | ETF Screener",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# THEME / CSS
# ============================================================

st.markdown("""
<style>

/* MAIN APPLICATION */

.stApp {
    background: #F4F6FA;
    color: #17243A;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}

h1, h2, h3, p, label {
    color: #17243A;
}

h1 {
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.8px;
}

h2 {
    font-size: 1.35rem !important;
    font-weight: 750 !important;
}

h3 {
    font-size: 1.05rem !important;
    font-weight: 700 !important;
}

/* HEADER */

.dashboard-header {
    background: linear-gradient(115deg, #14243A, #203D5C);
    padding: 28px 32px;
    border-radius: 16px;
    margin-bottom: 24px;
    box-shadow: 0 5px 18px rgba(20,36,58,0.12);
}

.dashboard-header h1 {
    color: #FFFFFF !important;
    margin-bottom: 5px;
}

.dashboard-header p {
    color: #B9C9DC !important;
    font-size: 0.9rem;
    margin-bottom: 0;
}

.header-tag {
    display: inline-block;
    background: rgba(45,212,191,0.15);
    color: #5EEAD4;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 10px;
}

/* METRIC CARDS */

div[data-testid="stMetric"] {
    background: #FFFFFF !important;
    padding: 20px 22px !important;
    border-radius: 13px !important;
    border: 1px solid #E7ECF3 !important;
    box-shadow: 0 3px 12px rgba(25,42,70,0.045);
}

div[data-testid="stMetric"] label,
div[data-testid="stMetric"] label *,
div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] *,
div[data-testid="stMetricDelta"],
div[data-testid="stMetricDelta"] * {
    color: #17243A !important;
}

div[data-testid="stMetric"] label {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
}

/* SECTION DIVIDERS */

hr {
    border-color: #E2E8F0 !important;
    margin-top: 1.5rem !important;
    margin-bottom: 1.5rem !important;
}

/* BUTTONS */

.stButton > button {
    border-radius: 9px !important;
    font-weight: 700 !important;
    min-height: 42px;
}

.stButton > button[kind="primary"] {
    background: #167D91 !important;
    border: 1px solid #167D91 !important;
    color: white !important;
}

.stButton > button[kind="primary"]:hover {
    background: #116477 !important;
    border-color: #116477 !important;
}

/* SELECT BOX */

div[data-baseweb="select"] > div {
    background: #FFFFFF;
    border-radius: 9px;
    border-color: #DCE3ED;
}

/* DATA TABLE */

div[data-testid="stDataFrame"] {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E7ECF3;
    overflow: hidden;
}

/* ALERTS */

div[data-testid="stAlert"] {
    border-radius: 12px;
}

/* CUSTOM DECISION CARD */

.decision-card {
    padding: 22px 25px;
    border-radius: 13px;
    margin-top: 8px;
    margin-bottom: 12px;
}

.decision-buy {
    background: #ECFDF5;
    border: 1px solid #A7F3D0;
    border-left: 5px solid #059669;
}

.decision-hold {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-left: 5px solid #3B82F6;
}

.decision-card h3 {
    margin: 0 0 10px 0;
}

.decision-card p {
    margin: 4px 0;
    font-size: 0.92rem;
}

.decision-buy h3,
.decision-buy p {
    color: #065F46;
}

.decision-hold h3,
.decision-hold p {
    color: #1E40AF;
}

/* FOOTER */

.footer-text {
    color: #8290A3;
    font-size: 0.78rem;
    text-align: center;
    line-height: 1.8;
}

/* CAPTIONS */

.stCaption, [data-testid="stCaptionContainer"] {
    color: #718096;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SCREENER SETTINGS - UNCHANGED
# ============================================================

ASSETS = ["SPY", "QQQ", "VGT", "VTI", "VT"]

FG_THRESH = 30


# ============================================================
# FEAR & GREED CALCULATION - UNCHANGED
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
        ) * 100

    return (
        _norm(mom) +
        _norm(-vix_z)
    ) / 2


# ============================================================
# DOWNLOAD MARKET DATA
# AUTOMATIC CACHE EXPIRY: 1 HOUR
# ============================================================

@st.cache_data(ttl=3600)
def download_market_data():

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
            "No market data returned by Yahoo Finance."
        )

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

        elif ticker in data.columns:
            return data["Close"].astype(float)

        raise ValueError(
            f"Unable to retrieve closing price for {ticker}"
        )

    close_data = pd.DataFrame({
        ticker: get_close(ticker)
        for ticker in ASSETS
    })

    vix = get_close("^VIX")

    combined = close_data.copy()
    combined["VIX"] = vix

    return combined.dropna()


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="dashboard-header">

    <div class="header-tag">
        MARKET INTELLIGENCE
    </div>

    <h1>📊 Market Pulse</h1>

    <p>
        Fear & Greed ETF Monitoring Dashboard
        &nbsp; | &nbsp;
        Powered by Yahoo Finance
    </p>

</div>
""", unsafe_allow_html=True)


# ============================================================
# REFRESH CONTROLS
# ============================================================

refresh_col, info_col = st.columns([1, 3])

with refresh_col:

    refresh_clicked = st.button(
        "↻  Refresh Market Data",
        use_container_width=True,
        type="primary"
    )

if refresh_clicked:

    download_market_data.clear()

    st.cache_data.clear()

    st.rerun()

with info_col:

    st.caption(
        "Automatic refresh: Every 1 hour  |  "
        "Use the refresh button to retrieve the latest available data."
    )


# ============================================================
# CALCULATE FEAR & GREED SCORES
# ============================================================

try:

    with st.spinner("Loading market intelligence..."):

        market_data = download_market_data()

        vix_series = market_data["VIX"]

        fg_data = pd.DataFrame(
            index=market_data.index
        )

        for ticker in ASSETS:

            fg_data[ticker] = calculate_fg(
                market_data[ticker],
                vix_series
            )

        fg_data = fg_data.dropna()

        if fg_data.empty:
            raise ValueError(
                "No valid Fear & Greed data available."
            )

        latest_fg = fg_data.iloc[-1]

        latest_date = fg_data.index[-1]

        triggered_assets = [
            ticker
            for ticker in ASSETS
            if latest_fg[ticker] < FG_THRESH
        ]

        buy_count = len(triggered_assets)

except Exception as e:

    st.error(
        f"Unable to retrieve market data: {e}"
    )

    st.stop()


# ============================================================
# SIGNAL CLASSIFICATION
# ============================================================

def get_signal(score):

    if score < 30:
        return "BUY"

    elif score <= 40:
        return "WATCH"

    else:
        return "HOLD"


# ============================================================
# MARKET OVERVIEW
# ============================================================

st.markdown("## Market Overview")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Assets Monitored",
        len(ASSETS)
    )

with col2:

    st.metric(
        "BUY Opportunities",
        buy_count,
        delta=f"{buy_count} of {len(ASSETS)} ETFs"
    )

with col3:

    st.metric(
        "Fear Threshold",
        f"< {FG_THRESH}"
    )

st.caption(
    f"Latest market data: "
    f"{latest_date.strftime('%A, %d %B %Y')}"
)

st.divider()


# ============================================================
# MARKET SCREENER
# ============================================================

st.markdown("## Market Screener")

st.caption(
    "ETF Fear & Greed readings and current trading signals."
)

screener_df = pd.DataFrame({

    "Asset": ASSETS,

    "FG Score": [
        f"{float(latest_fg[ticker]):.2f}"
        for ticker in ASSETS
    ],

    "Signal": [
        get_signal(float(latest_fg[ticker]))
        for ticker in ASSETS
    ]

})


# ============================================================
# TABLE COLOUR FORMATTING
# ============================================================

def colour_fg(value):

    score = float(value)

    if score < 30:
        return (
            "color: #15803D; "
            "font-weight: 800;"
            "background-color: #F0FDF4;"
        )

    elif score <= 40:
        return (
            "color: #B77900; "
            "font-weight: 800;"
            "background-color: #FFFBEB;"
        )

    else:
        return (
            "color: #17243A; "
            "font-weight: 700;"
            "background-color: #FFFFFF;"
        )


def colour_signal(value):

    if value == "BUY":
        return (
            "color: #15803D; "
            "font-weight: 800;"
            "background-color: #F0FDF4;"
        )

    elif value == "WATCH":
        return (
            "color: #B77900; "
            "font-weight: 800;"
            "background-color: #FFFBEB;"
        )

    else:
        return (
            "color: #DC2626; "
            "font-weight: 800;"
            "background-color: #FEF2F2;"
        )


styled_df = (

    screener_df.style

    .set_properties(
        subset=["Asset"],
        **{
            "color": "#17243A",
            "font-weight": "800",
            "background-color": "#FFFFFF",
            "text-align": "left",
            "padding": "13px"
        }
    )

    .set_properties(
        subset=["FG Score"],
        **{
            "text-align": "left",
            "padding-left": "22px",
            "padding-top": "13px",
            "padding-bottom": "13px"
        }
    )

    .set_properties(
        subset=["Signal"],
        **{
            "text-align": "center",
            "padding": "13px"
        }
    )

    .set_table_styles([

        {
            "selector": "th",
            "props": [
                ("background-color", "#EAF0F6"),
                ("color", "#334155"),
                ("font-weight", "800"),
                ("text-align", "left"),
                ("padding", "13px")
            ]
        },

        {
            "selector": "td",
            "props": [
                ("border-bottom", "1px solid #EDF1F5"),
                ("font-size", "14px")
            ]
        }

    ])

    .map(
        colour_fg,
        subset=["FG Score"]
    )

    .map(
        colour_signal,
        subset=["Signal"]
    )

)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "BUY: FG below 30  |  "
    "WATCH: FG 30–40  |  "
    "HOLD: FG above 40"
)

st.divider()


# ============================================================
# TRADING DECISION
# ============================================================

st.markdown("## Trading Decision")

if triggered_assets:

    buy_text = ", ".join(triggered_assets)

    st.markdown(
        f"""
        <div class="decision-card decision-buy">

            <h3>⚡ ACTION REQUIRED TOMORROW</h3>

            <p>
                <b>BUY OPPORTUNITIES:</b>
                {buy_text}
            </p>

            <p>
                <b>Execution:</b>
                Next Trading Day Open
            </p>

            <p>
                <b>Number of triggered ETFs:</b>
                {buy_count}
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )

else:

    st.markdown(
        """
        <div class="decision-card decision-hold">

            <h3>NO BUY SIGNAL</h3>

            <p>
                No monitored ETF currently meets the
                Fear & Greed BUY threshold.
            </p>

            <p>
                Continue monitoring the market.
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()


# ============================================================
# HISTORICAL BUY SIGNALS
# ============================================================

st.markdown("## Historical BUY Signals")

st.caption(
    "Most recent historical dates when at least one ETF "
    "reached the BUY threshold."
)

historical_signals = []

for date, row in fg_data.iterrows():

    triggered = [
        ticker
        for ticker in ASSETS
        if row[ticker] < FG_THRESH
    ]

    if triggered:

        historical_signals.append({

            "Date": date.strftime("%d %b %Y"),

            "Triggered Assets": ", ".join(triggered),

            "Number of Signals": len(triggered)

        })


historical_df = pd.DataFrame(
    historical_signals
)

if not historical_df.empty:

    historical_df = historical_df.tail(10)

    historical_df = historical_df.iloc[::-1]

    st.dataframe(
        historical_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("No historical BUY signals found.")


st.divider()


# ============================================================
# FEAR & GREED TREND
# ============================================================

st.markdown("## Fear & Greed Trend")

st.caption(
    "Explore individual ETF Fear & Greed readings "
    "over time. Select an ETF below."
)

selected_asset = st.selectbox(
    "Select ETF",
    options=ASSETS,
    index=0,
    key="fg_selected_asset"
)


# ============================================================
# ETF COLOURS
# ============================================================

line_colours = {

    "SPY": "#2563EB",

    "QQQ": "#7C3AED",

    "VGT": "#0891B2",

    "VTI": "#D97706",

    "VT": "#DB2777"

}

selected_colour = line_colours[selected_asset]

selected_fg = fg_data[selected_asset]


# ============================================================
# SELECTED ETF CURRENT SCORE
# ============================================================

current_score = float(latest_fg[selected_asset])

current_signal = get_signal(current_score)

score_col, signal_col = st.columns(2)

with score_col:

    st.metric(
        f"{selected_asset} Current FG Score",
        f"{current_score:.2f}"
    )

with signal_col:

    st.metric(
        "Current Signal",
        current_signal
    )


# ============================================================
# CREATE CHART
# ============================================================

fig = go.Figure()


# Background zones

zones = [

    (0, 30, "rgba(239,68,68,0.10)"),

    (30, 40, "rgba(245,158,11,0.12)"),

    (40, 60, "rgba(148,163,184,0.09)"),

    (60, 80, "rgba(16,185,129,0.08)"),

    (80, 100, "rgba(34,197,94,0.11)")

]

for y0, y1, fill in zones:

    fig.add_hrect(
        y0=y0,
        y1=y1,
        fillcolor=fill,
        line_width=0,
        layer="below"
    )


# FG trend line

fig.add_trace(

    go.Scatter(

        x=selected_fg.index,

        y=selected_fg.values,

        mode="lines",

        name=selected_asset,

        line=dict(
            color=selected_colour,
            width=2.8,
            shape="linear"
        ),

        hovertemplate=(

            "<b>" + selected_asset + "</b><br>"

            "Date: %{x|%d %b %Y}<br>"

            "FG Score: %{y:.2f}"

            "<extra></extra>"

        )

    )

)


# Threshold lines

thresholds = [

    (30, "#DC2626", "BUY Threshold"),

    (40, "#D97706", "Fear"),

    (60, "#64748B", "Neutral"),

    (80, "#16A34A", "Greed")

]

for value, colour, label in thresholds:

    fig.add_hline(

        y=value,

        line_dash="dot",

        line_color=colour,

        line_width=1.2,

        annotation_text=label,

        annotation_position="right",

        annotation_font_color=colour,

        annotation_font_size=10

    )


# Chart layout

fig.update_layout(

    template="plotly_white",

    height=500,

    paper_bgcolor="#FFFFFF",

    plot_bgcolor="#FFFFFF",

    font=dict(

        family="Arial, sans-serif",

        color="#334155",

        size=12

    ),

    title=dict(

        text=f"{selected_asset} Fear & Greed Index",

        font=dict(

            size=19,

            color="#17243A"

        ),

        x=0.02,

        xanchor="left"

    ),

    hovermode="x unified",

    showlegend=False,

    margin=dict(

        l=50,

        r=90,

        t=100,

        b=50

    ),

    dragmode=False,

    xaxis=dict(

        title="Date",

        showgrid=True,

        gridcolor="#EDF1F5",

        gridwidth=1,

        zeroline=False,

        showline=True,

        linecolor="#DCE3ED",

        tickfont=dict(color="#64748B"),

        fixedrange=True,

        rangeselector=dict(

            buttons=[

                dict(

                    count=1,

                    label="1M",

                    step="month",

                    stepmode="backward"

                ),

                dict(

                    count=3,

                    label="3M",

                    step="month",

                    stepmode="backward"

                ),

                dict(

                    count=6,

                    label="6M",

                    step="month",

                    stepmode="backward"

                ),

                dict(

                    count=1,

                    label="1Y",

                    step="year",

                    stepmode="backward"

                ),

                dict(

                    step="all",

                    label="ALL"

                )

            ],

            bgcolor="#F1F5F9",

            activecolor="#C7DDF4",

            bordercolor="#DCE3ED",

            borderwidth=1,

            font=dict(

                color="#334155",

                size=11

            ),

            x=1,

            xanchor="right",

            y=1.15

        )

    ),

    yaxis=dict(

        title="Fear & Greed Score",

        range=[0, 100],

        tickmode="linear",

        tick0=0,

        dtick=10,

        showgrid=True,

        gridcolor="#EDF1F5",

        gridwidth=1,

        zeroline=False,

        showline=True,

        linecolor="#DCE3ED",

        tickfont=dict(color="#64748B"),

        fixedrange=True

    )

)


# ============================================================
# RENDER CHART
# ============================================================

st.plotly_chart(

    fig,

    use_container_width=True,

    config={

        "scrollZoom": False,

        "displayModeBar": False,

        "staticPlot": False,

        "doubleClick": False,

        "responsive": True

    }

)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="footer-text">

        <b>MARKET PULSE SCREENER</b><br>

        Market intelligence powered by Yahoo Finance.<br>

        Signals are based on historical price and volatility
        data and are for informational purposes only.

    </div>
    """,
    unsafe_allow_html=True
)
