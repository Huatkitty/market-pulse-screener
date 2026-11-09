
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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

    /* MARKET OVERVIEW CARDS */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
    }

    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] label *,
    div[data-testid="stMetric"] [data-testid="stMetricValue"],
    div[data-testid="stMetric"] [data-testid="stMetricValue"] *,
    div[data-testid="stMetric"] [data-testid="stMetricDelta"],
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] * {
        color: #111827 !important;
    }

    /* DATA TABLE */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF;
        border-radius: 10px;
    }

    /* ALERT TEXT */
    div[data-testid="stAlert"] p {
        color: #111827 !important;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# ORIGINAL SCREENER SETTINGS — UNCHANGED
# ============================================================

ASSETS = ["SPY", "QQQ", "VGT", "VTI", "VT"]

FG_THRESH = 30


# ============================================================
# ORIGINAL FEAR & GREED CALCULATION — UNCHANGED
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
# DASHBOARD HEADER
# ============================================================

st.title("📊 Market Pulse Screener")

st.caption(
    "Fear & Greed ETF Monitoring | "
    "Data powered by Yahoo Finance"
)


# ============================================================
# MANUAL MARKET DATA REFRESH
# ============================================================

refresh_col, info_col = st.columns([1, 2])

with refresh_col:

    refresh_clicked = st.button(
        "🔄 Refresh Market Data",
        use_container_width=True,
        type="primary"
    )

if refresh_clicked:

    with st.spinner("Downloading fresh market data..."):

        # Clear only this function's cached data
        download_market_data.clear()

        # Rerun the app to download fresh data
        st.rerun()

with info_col:

    st.caption(
        "Automatic data cache expiry: 1 hour. "
        "Use Refresh Market Data to download immediately."
    )

st.divider()


# ============================================================
# CALCULATE FEAR & GREED SCORES
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

    if fg_data.empty:
        raise ValueError("No valid Fear & Greed data available.")

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

st.caption(
    f"Latest market data date: {latest_date.strftime('%d %b %Y')}"
)

st.divider()


# ============================================================
# MARKET SCREENER
# ============================================================

st.subheader("Market Screener")


# Determine signal based on FG score

def get_signal(score):

    if score < 30:
        return "BUY"

    elif score <= 40:
        return "WATCH"

    else:
        return "HOLD"


# Prepare screener data

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


# FG score text colours

def colour_fg(value):

    score = float(value)

    if score < 30:
        return "color: #15803D; font-weight: bold"

    elif score <= 40:
        return "color: #E67451 ; font-weight: bold"

    else:
        return "color: #DC2626; font-weight: bold"


# Signal text colours

def colour_signal(value):

    if value == "BUY":
        return "color: #15803D; font-weight: bold"

    elif value == "WATCH":
        return "color: #E67451; font-weight: bold"

    else:
        return "color: #DC2626; font-weight: bold"


# Table styling

styled_df = (
    screener_df.style

    .set_properties(
        subset=["Asset"],
        **{
            "color": "#111827",
            "background-color": "#FFFFFF",
            "text-align": "left"
        }
    )

    .set_properties(
        subset=["FG Score"],
        **{
            "color": "#111827",
            "background-color": "#FFFFFF",
            "text-align": "left",
            "padding-left": "18px"
        }
    )

    .set_properties(
        subset=["Signal"],
        **{
            "color": "#111827",
            "background-color": "#FFFFFF",
            "text-align": "center"
        }
    )

    .set_table_styles([
        {
            "selector": "th",
            "props": [
                ("color", "#111827"),
                ("background-color", "#F1F5F9"),
                ("font-weight", "bold"),
                ("text-align", "left")
            ]
        },
        {
            "selector": "td",
            "props": [
                ("border-color", "#E5E7EB")
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
        BUY threshold.

        Continue monitoring.
        """
    )

st.divider()


# ============================================================
# HISTORICAL BUY SIGNALS
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

historical_df = pd.DataFrame(historical_signals)

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
# FEAR & GREED TREND — INDIVIDUAL ETF SELECTION
# ============================================================

st.subheader("Fear & Greed Trend")

st.caption(
    "Select an ETF to view its individual Fear & Greed trend. "
    "Only one ETF is displayed at a time."
)

selected_asset = st.selectbox(
    "Select ETF",
    options=ASSETS,
    index=0,
    key="fg_selected_asset"
)


# ETF line colours

line_colours = {
    "SPY": "#2563EB",
    "QQQ": "#7C3AED",
    "VGT": "#0891B2",
    "VTI": "#D97706",
    "VT": "#DB2777"
}

selected_colour = line_colours[selected_asset]

selected_fg = fg_data[selected_asset]


# Create graph

fig = go.Figure()


# Background zones

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


# Selected ETF trend line

fig.add_trace(
    go.Scatter(
        x=selected_fg.index,
        y=selected_fg.values,
        mode="lines",
        name=selected_asset,
        line=dict(
            color=selected_colour,
            width=3,
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


# Light theme layout

fig.update_layout(

    template="plotly_white",

    height=520,

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
            size=18,
            color="#0F172A"
        ),
        x=0.02,
        xanchor="left"
    ),

    hovermode="x unified",

    showlegend=False,

    margin=dict(
        l=45,
        r=85,
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


# Render graph

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
