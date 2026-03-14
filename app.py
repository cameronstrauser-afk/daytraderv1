import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from strategy_engine import (
    download_data,
    run_all_strategies,
    get_top_strategies,
    aggregate_signal,
    scan_watchlist
)
from paper_trading import init_paper_trading, render_paper_trading
from alerts import init_alerts, render_alerts

st.set_page_config(
    page_title="Day Trading Predictor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- STYLES ----------
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0e1117;
    color: #e6edf3;
}
.main-title {
    font-size: 34px;
    font-weight: 800;
    color: #e6edf3;
    margin-bottom: 0.2rem;
}
.subtle {
    color: #9aa4b2;
    font-size: 14px;
}
.metric-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 14px;
    padding: 16px;
}
.section-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 16px;
}
.buy {
    color: #2ecc71;
    font-weight: 700;
}
.sell {
    color: #ff5c5c;
    font-weight: 700;
}
.hold {
    color: #f1c40f;
    font-weight: 700;
}
.small-label {
    color: #9aa4b2;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
init_paper_trading()
init_alerts()

if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "META"]

# ---------- HEADER ----------
st.markdown('<div class="main-title">Day Trading Stock Predictor</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">TradingView-inspired dashboard • strategy voting • confidence scoring • paper trading</div>', unsafe_allow_html=True)
st.markdown("---")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.header("Controls")
    symbol = st.text_input("Ticker", value="AAPL").upper().strip()
    interval = st.selectbox("Interval", ["1m", "2m", "5m", "15m", "30m", "60m"], index=2)
    period_map = {
        "1m": "7d",
        "2m": "30d",
        "5m": "30d",
        "15m": "60d",
        "30m": "60d",
        "60m": "730d"
    }
    period = period_map[interval]

    capital = st.number_input("Paper Trading Starting Cash", min_value=100.0, value=10000.0, step=100.0)
    allow_short = st.toggle("Enable Short Selling", value=True)
    use_top_n = st.slider("Top Strategies Used for Final Vote", min_value=3, max_value=10, value=5)
    refresh = st.button("Run Predictor")

    st.markdown("---")
    st.subheader("Watchlist")
    watchlist_input = st.text_area(
        "Comma-separated tickers",
        value=", ".join(st.session_state.watchlist),
        height=100
    )
    if st.button("Update Watchlist"):
        st.session_state.watchlist = [x.strip().upper() for x in watchlist_input.split(",") if x.strip()]
        st.success("Watchlist updated.")

# ---------- MAIN ----------
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### Live Chart")
    tv_symbol = f"NASDAQ:{symbol}" if symbol else "NASDAQ:AAPL"
    tradingview_widget = f"""
    <iframe
        src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_1&symbol={tv_symbol}&interval={interval.replace('m','') if 'm' in interval else interval}&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=0e1117&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&hideideas=1&studies=[]"
        width="100%"
        height="520"
        frameborder="0"
        allowtransparency="true"
        scrolling="no">
    </iframe>
    """
    st.components.v1.html(tradingview_widget, height=540)

with col2:
    st.markdown("### Snapshot")

    if refresh or "latest_run" not in st.session_state or st.session_state.get("last_symbol") != symbol:
        df = download_data(symbol, period=period, interval=interval)
        if df.empty:
            st.error("No data returned for that ticker/interval.")
            st.stop()

        results = run_all_strategies(df, allow_short=allow_short)
        top_results = get_top_strategies(results, top_n=use_top_n)
        summary = aggregate_signal(top_results)

        st.session_state.latest_run = {
            "df": df,
            "all_results": results,
            "top_results": top_results,
            "summary": summary
        }
        st.session_state.last_symbol = symbol
    else:
        df = st.session_state.latest_run["df"]
        results = st.session_state.latest_run["all_results"]
        top_results = st.session_state.latest_run["top_results"]
        summary = st.session_state.latest_run["summary"]

    latest_price = float(df["Close"].iloc[-1])

    signal_class = summary["signal"].lower()
    st.markdown(f"""
    <div class="metric-card">
        <div class="small-label">Current Price</div>
        <div style="font-size:28px;font-weight:800;">${latest_price:,.2f}</div>
        <br>
        <div class="small-label">Action</div>
        <div class="{signal_class}" style="font-size:26px;">{summary["signal"]}</div>
        <br>
        <div class="small-label">Confidence</div>
        <div style="font-size:24px;font-weight:700;">{summary["confidence"]:.1f}%</div>
        <br>
        <div class="small-label">Risk Level</div>
        <div style="font-size:20px;font-weight:700;">{summary["risk_level"]}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------- SIGNAL BREAKDOWN ----------
st.markdown("### Vote Breakdown")
v1, v2, v3, v4 = st.columns(4)
v1.metric("BUY %", f"{summary['buy_pct']:.1f}%")
v2.metric("HOLD %", f"{summary['hold_pct']:.1f}%")
v3.metric("SELL %", f"{summary['sell_pct']:.1f}%")
v4.metric("Strategy Count", f"{len(top_results)}")

# ---------- TOP STRATEGIES ----------
st.markdown("### Top 5 Strategy Reasons")
for i, strat in enumerate(top_results, start=1):
    with st.container():
        st.markdown(f"""
        <div class="section-card">
            <div style="font-size:18px;font-weight:700;">#{i} {strat['name']}</div>
            <div class="small-label">Signal: <span class="{strat['signal'].lower()}">{strat['signal']}</span> | 
            Win Rate: {strat['win_rate']:.2f}% | 
            Score: {strat['score']:.2f} | 
            Risk: {strat['risk_level']}</div>
            <br>
            <div><strong>Reason:</strong> {strat['reason']}</div>
            <div><strong>Confidence Contribution:</strong> {strat['confidence_contribution']:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

# ---------- DATA TABLE ----------
st.markdown("### Top Strategy Table")
top_df = pd.DataFrame(top_results)[[
    "name", "signal", "win_rate", "score", "risk_level", "confidence_contribution", "reason"
]]
st.dataframe(top_df, use_container_width=True)

# ---------- WATCHLIST SCANNER ----------
st.markdown("### Watchlist Scanner")
scanner_df = scan_watchlist(st.session_state.watchlist, interval=interval, allow_short=allow_short)
st.dataframe(scanner_df, use_container_width=True)

# ---------- PAPER TRADING ----------
st.markdown("### Paper Trading Mode")
render_paper_trading(symbol=symbol, latest_price=latest_price, capital_default=capital, summary=summary)

# ---------- ALERTS ----------
st.markdown("### Alerts")
render_alerts(symbol=symbol, latest_price=latest_price, summary=summary)

# ---------- FOOTER ----------
st.markdown("---")
st.caption(
    "Educational use only. This is not financial advice. "
    "This app uses yfinance market data for signals and embeds a TradingView chart widget for visualization."
)
