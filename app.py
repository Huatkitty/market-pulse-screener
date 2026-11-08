
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
    page_title="Market Pulse Screener",
    page_icon="📊",
    layout="wide"
)

# ============================================================
# DASHBOARD STYLING
# ============================================================

st.markdown("""
<style>
    .stApp {
        background-color: #101827;
        color: #F8FAFC;
    }

    h1, h2, h3, p, label {
        color: #F8FAFC;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
    }

    div[data-testid="stMetric"] label {
        color: #111827 !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #111827 !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #374151 !important;
    }

    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    div[data-testid="stAlert"] p {
        color: #111827 !important;
    }

    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# ORIGINAL SCREENER SETTINGS — DO NOT CHANGE
# ============================================================

ASSETS = ["SPY", "QQQ", "VGT", "VTI", "VT"]

FG_THRESH = 30

# ============================================================
# FEAR & GREED CALCULATION — ORIGINAL LOGIC
# ============================================================

def calculate_fg(close_series, vix_series):

    ma125 = close_series.rolling(
        125,
        min_periods=1
    ).mean()

    mom = close_series / ma125

    vix_z = (
        vix_series - vix_series.mean()
    ) / vix_series.std()

    def _norm(s):

        lo = s.rolling(
            252,
            min_periods=1
        ).min()

        hi = s.rolling(
            252,
            min_periods=1
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
# DATA DOWNLOAD
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
        raise ValueError("No market data returned by Yahoo Finance.")

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
            f"Unable to retrieve closing price for {ticker}"
        )

    close_data = pd.DataFrame({
        ticker: get_close(ticker)
        for ticker in ASSETS
    })

    vix = get_close("^VIX")

    combined = close_data.copy()
    combined["VIX"] = vix

    combined = combined.dropna()

    return combined


# ============================================================
# CALCULATE SCREENER RESULTS
# ============================================================

try:

    market_data = download_market_data()

    vix_series = market_data["VIX"]

    fg_data = pd.DataFrame(index=market_data.index)

    for ticker in ASSETS:

        fg_data[ticker] = calculate_fg(
            market_data[ticker],
            vix_series
        )

    fg_data = fg_data.dropna()

    latest_fg = fg_data.iloc[-1]

    latest_date = fg_data.index[-1]

    triggered_assets = [
        ticker
        for ticker in ASSETS
        if latest_fg[ticker] < FG_THRESH
    ]

    buy_count = len(triggered_assets)

except Exception as e:

    st.error(f"Unable to retrieve market data: {e}")
    st.stop()


# ============================================================
# DASHBOARD HEADER
# ============================================================

st.title("📊 Market Pulse Screener")

st.caption(
    f"Fear & Greed ETF Monitoring | "
    f"Latest data: {latest_date.strftime('%d %b %Y')}"
)

st.divider()


# ============================================================
# MARKET OVERVIEW
# ============================================================

st.subheader("Market Overview")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Assets Monitored",
        len(ASSETS)
    )

with col2:

    st.metric(
        "BUY Opportunities",
        buy_count
    )

with col3:

    st.metric(
        "Fear Threshold",
        f"< {FG_THRESH}"
    )


st.divider()


# ============================================================
# MARKET SCREENER
# ============================================================

st.subheader("Market Screener")

screener_df = pd.DataFrame({
    "Asset": ASSETS,
    "FG Score": [
        round(float(latest_fg[ticker]), 2)
        for ticker in ASSETS
    ],
    "Signal": [
        "BUY"
        if latest_fg[ticker] < FG_THRESH
        else "WAIT"
        for ticker in ASSETS
    ]
})

def colour_signal(value):

    if value == "BUY":
        return "color: #15803D; font-weight: bold"

    return "color: #111827; font-weight: bold"


def colour_fg(value):

    if value < FG_THRESH:
        return "color: #15803D; font-weight: bold"

    return "color: #111827"


styled_df = (
    screener_df.style
    .set_properties(
        **{
            "color": "#111827",
            "background-color": "#FFFFFF",
            "text-align": "center",
            "border-color": "#E5E7EB"
        }
    )
    .set_table_styles([
        {
            "selector": "th",
            "props": [
                ("color", "#111827"),
                ("background-color", "#F1F5F9"),
                ("font-weight", "bold"),
                ("text-align", "center")
            ]
        },
        {
            "selector": "td",
            "props": [
                ("color", "#111827"),
                ("background-color", "#FFFFFF")
            ]
        }
    ])
    .map(
        colour_signal,
        subset=["Signal"]
    )
    .map(
        colour_fg,
        subset=["FG Score"]
    )
)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True
)


st.divider()


# ============================================================
# TRADING DECISION
# ============================================================

st.subheader("Trading Decision")

if triggered_assets:

    buy_text = ", ".join(triggered_assets)

    st.success(
        f"""
        ⚡ ACTION REQUIRED TOMORROW

        BUY: {buy_text}

        Execution: Next Trading Day Open
        """
    )

else:

    st.info(
        """
        NO BUY SIGNAL

        No monitored ETF currently meets the Fear & Greed
        threshold.

        Continue monitoring.
        """
    )


st.divider()


# ============================================================
# HISTORICAL TRIGGER SUMMARY
# ============================================================

st.subheader("Historical BUY Signals")

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
            "Triggered Assets": ", ".join(triggered)
        })

historical_df = pd.DataFrame(
    historical_signals
)

if not historical_df.empty:

    historical_df = historical_df.tail(10)

    st.dataframe(
        historical_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.write("No historical BUY signals found.")


st.divider()


# ============================================================
# FEAR & GREED TREND — LIGHT THEME
# ============================================================

st.subheader("Fear & Greed Trend")

st.caption(
    "Historical Fear & Greed scores for all monitored ETFs. "
    "Lower readings indicate stronger fear conditions."
)

fig = go.Figure()

# Soft background zones

fig.add_hrect(
    y0=0,
    y1=30,
    fillcolor="rgba(239, 68, 68, 0.12)",
    line_width=0,
    layer="below"
)

fig.add_hrect(
    y0=30,
    y1=40,
    fillcolor="rgba(249, 115, 22, 0.10)",
    line_width=0,
    layer="below"
)

fig.add_hrect(
    y0=40,
    y1=60,
    fillcolor="rgba(148, 163, 184, 0.10)",
    line_width=0,
    layer="below"
)

fig.add_hrect(
    y0=60,
    y1=80,
    fillcolor="rgba(34, 197, 94, 0.09)",
    line_width=0,
    layer="below"
)

fig.add_hrect(
    y0=80,
    y1=100,
    fillcolor="rgba(22, 163, 74, 0.12)",
    line_width=0,
    layer="below"
)


# Professional colour palette for each ETF

line_colours = {
    "SPY": "#2563EB",
    "QQQ": "#7C3AED",
    "VGT": "#0891B2",
    "VTI": "#D97706",
    "VT": "#DB2777"
}


# Plot all ETF trend lines

for ticker in ASSETS:

    fig.add_trace(
        go.Scatter(
            x=fg_data.index,
            y=fg_data[ticker],
            mode="lines",
            name=ticker,
            line=dict(
                color=line_colours[ticker],
                width=2.5,
                shape="linear"
            ),
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Date: %{x|%d %b %Y}<br>"
                "FG Score: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )


# Threshold reference lines

thresholds = [
    (30, "#DC2626", "BUY Threshold"),
    (40, "#EA580C", "Fear"),
    (60, "#64748B", "Neutral"),
    (80, "#16A34A", "Greed")
]

for value, colour, label in thresholds:

    fig.add_hline(
        y=value,
        line_dash="dash",
        line_color=colour,
        line_width=1,
        annotation_text=label,
        annotation_position="right",
        annotation_font_color=colour,
        annotation_font_size=10
    )


# Light chart layout

fig.update_layout(

    template="plotly_white",

    height=560,

    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",

    font=dict(
        family="Arial, sans-serif",
        color="#334155",
        size=12
    ),

    title=dict(
        text="ETF Fear & Greed Index",
        font=dict(
            size=18,
            color="#0F172A"
        ),
        x=0.02,
        xanchor="left"
    ),

    hovermode="x unified",

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        bgcolor="rgba(255,255,255,0)",
        font=dict(
            color="#334155",
            size=11
        )
    ),

    margin=dict(
        l=45,
        r=70,
        t=90,
        b=45
    ),

    dragmode=False,

    xaxis=dict(
        title="Date",
        showgrid=True,
        gridcolor="#E2E8F0",
        gridwidth=1,
        zeroline=False,
        showline=True,
        linecolor="#CBD5E1",
        tickfont=dict(color="#475569"),
        fixedrange=True,

        rangeselector=dict(
            buttons=list([
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
            ]),
            bgcolor="#F1F5F9",
            activecolor="#BFDBFE",
            bordercolor="#CBD5E1",
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
        gridcolor="#E2E8F0",
        gridwidth=1,
        zeroline=False,
        showline=True,
        linecolor="#CBD5E1",
        tickfont=dict(color="#475569"),
        fixedrange=True
    )
)


# Disable zoom, pan and mode bar.
# Users can still use the date-range buttons above.

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

st.caption(
    "Market Pulse Screener | Data powered by Yahoo Finance"
)

st.caption(
    "Signals are based on historical price and volatility data. "
    "This dashboard is for informational purposes only."
)
