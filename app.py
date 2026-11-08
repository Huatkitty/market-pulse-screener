import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(page_title="FG Screener", page_icon="📊", layout="wide")

# Custom CSS to make the tables look ultra-clean and remove visual clutter
st.markdown("""
    <style>
    /* Clean up the main container */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    /* Make dataframes minimalist */
    [data-testid="stDataFrame"] { border: none; }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# CONFIGURATION
# ============================================================
ASSETS = ["SPY", "QQQ", "VGT", "VTI", "VT"]
FG_THRESH = 30

# ============================================================
# DATA FETCHING & CACHING
# ============================================================
@st.cache_data(ttl=3600) # Cache data for 1 hour to avoid rate limits
def fetch_and_calculate():
    tickers = ASSETS + ["^VIX"]
    # Download 3 years of data
    data = yf.download(tickers, period="3y", auto_adjust=True, progress=False, group_by='ticker')
    
    df = pd.DataFrame()
    for t in ASSETS:
        df[f'{t}_Close'] = data[t]['Close'].astype(float)
    df['VIX'] = data['^VIX']['Close'].astype(float)
    df = df.dropna()
    
    # Calculate FG Index
    for t in ASSETS:
        close = df[f'{t}_Close']
        vix = df['VIX']
        
        ma125 = close.rolling(125, min_periods=1).mean()
        mom = close / ma125
        vix_z = (vix - vix.mean()) / vix.std()
        
        def _norm(s):
            lo = s.rolling(252, min_periods=1).min()
            hi = s.rolling(252, min_periods=1).max()
            return (s - lo) / (hi - lo).replace(0, 1) * 100
            
        df[f'{t}_FG'] = (_norm(mom) + _norm(-vix_z)) / 2
        
    return df

# ============================================================
# MAIN APP
# ============================================================
def main():
    st.title("Fear & Greed Daily Screener")
    
    with st.spinner("Fetching market data..."):
        df = fetch_and_calculate()
        
    latest_date = df.index[-1].strftime('%B %d, %Y')
    st.caption(f"Data as of close: **{latest_date}**")
    
    # --------------------------------------------------------
    # CURRENT SIGNALS TABLE
    # --------------------------------------------------------
    current_signals = []
    buy_signals = []
    
    for t in ASSETS:
        fg = df[f'{t}_FG'].iloc[-1]
        px = df[f'{t}_Close'].iloc[-1]
        
        if fg < FG_THRESH:
            signal = "BUY"
            buy_signals.append(t)
        else:
            signal = "WAIT"
            
        current_signals.append({
            "Asset": t,
            "Price": f"${px:,.2f}",
            "FG Score": round(fg, 2),
            "Signal": signal
        })
        
    df_current = pd.DataFrame(current_signals).set_index("Asset")
    
    # Display table with Styler (Green for BUY, grey for WAIT)
    def color_signal(val):
        if val == "BUY":
            return 'color: #00cc66; font-weight: bold;' # Professional Green
        return 'color: #888888;' # Muted Grey
        
    st.dataframe(
        df_current.style.map(color_signal, subset=["Signal"]),
        use_container_width=True,
        height=215 # Fixed height for neatness
    )
    
    # --------------------------------------------------------
    # ACTION BLOCK
    # --------------------------------------------------------
    st.markdown("---")
    if buy_signals:
        buy_list = ", ".join(buy_signals)
        st.info(f"**Action required: Buy:** `{buy_list}` **at the open.**")
    else:
        st.success("**Action required:** None. Hold cash or execute standard monthly DCA.")
        
    # --------------------------------------------------------
    # HISTORY MATRIX
    # --------------------------------------------------------
    st.markdown("### Recent Signal History (Last 10 Days)")
    
    # Create a boolean mask and filter
    mask = (df[[f'{t}_FG' for t in ASSETS]] < FG_THRESH).any(axis=1)
    signal_days = df[mask].tail(10).iloc[::-1] # Get last 10 and reverse (newest first)
    
    if len(signal_days) == 0:
        st.write("No signals found in recent history.")
    else:
        history_data = []
        for date, row in signal_days.iterrows():
            row_dict = {"Date": date.strftime('%b %d, %Y')}
            for t in ASSETS:
                if row[f'{t}_FG'] < FG_THRESH:
                    row_dict[t] = "BUY"
                else:
                    row_dict[t] = "-"
            history_data.append(row_dict)
            
        df_history = pd.DataFrame(history_data).set_index("Date")
        
        # Style the history table
        def color_history(val):
            if val == "BUY":
                return 'color: #00cc66; font-weight: bold;'
            return 'color: #cccccc;' # Very light grey for dashes
            
        st.dataframe(
            df_history.style.map(color_history),
            use_container_width=True
        )

if __name__ == "__main__":
    main()
