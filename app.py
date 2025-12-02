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

# ---------- FETCH DATA ----------
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

# ---------- MAIN ----------
st.title("📊 Stock Analytics Dashboard")

data = load_price_data(ticker, start_date, end_date, interval)

if data is None:
    st.error("Could not download data. Check ticker or date range.")
    st.stop()

# Ensure Close exists
if "Close" not in data.columns:
    st.error("The dataset does not include a 'Close' price. Cannot continue.")
    st.stop()

# ---------- BASIC STATS ----------
data["Return"] = data["Close"].pct_change()
returns = data["Return"].dropna()

# ---------- FIXED KPI SECTION ----------
data["Return"] = data["Close"].pct_change()
returns = data["Return"].dropna()

# Safe last/prev close
if len(data) >= 2:
    last_close = float(data["Close"].iloc[-1])
    prev_close = float(data["Close"].iloc[-2])
    daily_change_pct = ((last_close - prev_close) / prev_close) * 100
else:
    last_close = float(data["Close"].iloc[-1])
    prev_close = float("nan")
    daily_change_pct = 0.0

# Safe avg volume
if "Volume" in data.columns:
    avg_volume = float(data["Volume"].mean())
else:
    avg_volume = float("nan")

if returns.empty:
    annualized_vol = float("nan")
else:
    annualized_vol = float(returns.std() * np.sqrt(252))

# ----- Display KPIs -----
k1, k2, k3, k4 = st.columns(4)

k1.metric("Last Close", f"${last_close:,.2f}")
k2.metric("Daily Change (%)", f"{daily_change_pct:,.2f}%")
k3.metric("Annualized Volatility", f"{annualized_vol * 100:,.2f}%" if not np.isnan(annualized_vol) else "N/A")

# Volume display
if np.isnan(avg_volume):
    avg_vol_display = "N/A"
else:
    avg_vol_display = f"{avg_volume:,.0f}"

k4.metric("Average Volume", avg_vol_display)


# ---------- TABS ----------
tab_price, tab_returns, tab_table = st.tabs(["📉 Price & Moving Averages", "📊 Returns & Volatility", "📋 Data & Download"])

# ---------- PRICE & MAs ----------
with tab_price:
    st.subheader("Price with Moving Averages")

    c1, c2, c3 = st.columns(3)
    with c1:
        ma_short = st.number_input("Short MA (days)", min_value=5, max_value=50, value=20)
    with c2:
        ma_long = st.number_input("Long MA (days)", min_value=50, max_value=200, value=50)
    with c3:
        price_column = st.selectbox("Price type", options=["Close", "Open", "High", "Low"])

    data[f"MA{ma_short}"] = data[price_column].rolling(ma_short).mean()
    data[f"MA{ma_long}"] = data[price_column].rolling(ma_long).mean()

    fig_price = px.line(
        data,
        x="Date",
        y=[price_column, f"MA{ma_short}", f"MA{ma_long}"],
        title=f"{ticker.upper()} Price & Moving Averages",
        labels={"value": "Price", "Date": "Date", "variable": "Series"}
    )
    st.plotly_chart(fig_price, use_container_width=True)

# ---------- RETURNS ----------
with tab_returns:
    st.subheader("Daily Returns & Volatility")

    if returns.empty:
        st.warning("Not enough data for returns.")
    else:
        col_r1, col_r2 = st.columns([2, 1])

        with col_r1:
            fig_ret = px.line(
                data,
                x="Date",
                y="Return",
                title="Daily Returns",
            )
            st.plotly_chart(fig_ret, use_container_width=True)

        with col_r2:
            st.write("Return Summary Statistics")
            st.dataframe(returns.describe().to_frame().rename(columns={"Return": "Value"}))

        st.markdown("#### Return Distribution")
        fig_hist = px.histogram(
            returns,
            nbins=40,
            title="Histogram of Daily Returns",
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# ---------- DATA ----------
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

    st.caption("You can open the CSV in Excel, Python, or R.")

