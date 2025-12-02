import datetime as dt

import numpy as np
import pandas as pd
import yfinance as yf
import plotly.express as px
import streamlit as st

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Stock Analytics Dashboard",
    layout="wide",
)

# ---------- SIDEBAR ----------
st.sidebar.title("📈 Stock Analytics Dashboard")

ticker = st.sidebar.text_input("Ticker symbol", value="AAPL", help="Example: AAPL, MSFT, TSLA, SPY")
col1, col2 = st.sidebar.columns(2)

with col1:
    start_date = st.date_input("Start date", value=dt.date(2020, 1, 1))
with col2:
    end_date = st.date_input("End date", value=dt.date.today())

interval = st.sidebar.selectbox(
    "Data frequency",
    options=["1d", "1wk", "1mo"],
    format_func=lambda x: {"1d": "Daily", "1wk": "Weekly", "1mo": "Monthly"}[x],
)

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Streamlit + yfinance")

# ---------- HELPER: FETCH DATA ----------
@st.cache_data(show_spinner=True)
def load_price_data(ticker, start, end, interval):
    try:
        data = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
        if data.empty:
            return None
        data = data.rename_axis("Date").reset_index()
        return data
    except Exception:
        return None

# ---------- MAIN APP ----------
st.title("📊 Stock Analytics Dashboard")

if not ticker:
    st.info("Please enter a ticker symbol in the sidebar to begin.")
    st.stop()

data = load_price_data(ticker, start_date, end_date, interval)

if data is None:
    st.error("Could not download data. Please check the ticker symbol or try a different date range.")
    st.stop()

# Ensure we have required columns
if "Adj Close" not in data.columns:
    st.error("Downloaded data does not contain 'Adj Close' prices. Try a different ticker.")
    st.stop()

# ---------- BASIC STATS ----------
data["Return"] = data["Adj Close"].pct_change()
returns = data["Return"].dropna()

last_close = data["Adj Close"].iloc[-1]
prev_close = data["Adj Close"].iloc[-2] if len(data) > 1 else np.nan
daily_change_pct = (last_close - prev_close) / prev_close * 100 if not np.isnan(prev_close) else 0.0
annualized_vol = returns.std() * np.sqrt(252) if not returns.empty else np.nan
avg_volume = data["Volume"].mean() if "Volume" in data.columns else np.nan

st.subheader(f"Overview: {ticker.upper()}")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("Last Close", f"${last_close:,.2f}")
with kpi2:
    st.metric("Daily Change", f"{daily_change_pct:,.2f}%")
with kpi3:
    st.metric("Annualized Volatility", f"{annualized_vol * 100:,.2f}%" if not np.isnan(annualized_vol) else "N/A")
with kpi4:
    st.metric("Average Volume", f"{avg_volume:,.0f}" if not np.isnan(avg_volume) else "N/A")

st.markdown("---")

# ---------- TABS ----------
tab_price, tab_returns, tab_table = st.tabs(
    ["📉 Price & Moving Averages", "📊 Returns & Volatility", "📋 Data & Download"]
)

# ---------- TAB 1: PRICE & MAs ----------
with tab_price:
    st.subheader("Price with Moving Averages")

    ma_col1, ma_col2, ma_col3 = st.columns(3)
    with ma_col1:
        ma_short = st.number_input("Short MA (days)", min_value=5, max_value=50, value=20)
    with ma_col2:
        ma_long = st.number_input("Long MA (days)", min_value=50, max_value=200, value=50)
    with ma_col3:
        price_column = st.selectbox("Price type", options=["Adj Close", "Close", "Open"])

    data[f"MA {ma_short}"] = data[price_column].rolling(ma_short).mean()
    data[f"MA {ma_long}"] = data[price_column].rolling(ma_long).mean()

    fig_price = px.line(
        data,
        x="Date",
        y=[price_column, f"MA {ma_short}", f"MA {ma_long}"],
        labels={"value": "Price", "Date": "Date", "variable": "Series"},
        title=f"{ticker.upper()} Price and Moving Averages",
    )
    st.plotly_chart(fig_price, use_container_width=True)

# ---------- TAB 2: RETURNS & VOL ----------
with tab_returns:
    st.subheader("Daily Returns & Volatility")

    if returns.empty:
        st.warning("Not enough data to compute returns.")
    else:
        col_r1, col_r2 = st.columns([2, 1])

        with col_r1:
            fig_ret = px.line(
                data,
                x="Date",
                y="Return",
                labels={"Return": "Daily Return", "Date": "Date"},
                title="Daily Returns",
            )
            st.plotly_chart(fig_ret, use_container_width=True)

        with col_r2:
            st.write("Summary Statistics (Returns)")
            st.dataframe(returns.describe().to_frame().rename(columns={"Return": "Value"}))

        st.markdown("#### Return Distribution")
        fig_hist = px.histogram(
            returns,
            nbins=40,
            labels={"value": "Daily Return"},
            title="Histogram of Daily Returns",
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# ---------- TAB 3: DATA & DOWNLOAD ----------
with tab_table:
    st.subheader("Raw Price Data")

    st.dataframe(data.set_index("Date"))

    csv = data.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv,
        file_name=f"{ticker.upper()}_data.csv",
        mime="text/csv",
    )

    st.caption("Tip: You can open this CSV in Excel, R, Python, or any stats software.")

