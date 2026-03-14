import streamlit as st
import pandas as pd

def init_alerts():
    if "alerts" not in st.session_state:
        st.session_state.alerts = []

def render_alerts(symbol, latest_price, summary):
    with st.expander("Create Alert", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            alert_type = st.selectbox("Alert Type", ["Price Above", "Price Below", "Signal Is"])
        with col2:
            price_target = st.number_input("Price Target", min_value=0.0, value=float(latest_price), step=0.1)
        with col3:
            signal_target = st.selectbox("Signal Target", ["BUY", "HOLD", "SELL"])

        if st.button("Add Alert"):
            st.session_state.alerts.append({
                "symbol": symbol,
                "alert_type": alert_type,
                "price_target": price_target,
                "signal_target": signal_target
            })
            st.success("Alert added.")

    triggered = []
    for alert in st.session_state.alerts:
        if alert["symbol"] != symbol:
            continue

        if alert["alert_type"] == "Price Above" and latest_price > alert["price_target"]:
            triggered.append(f"{symbol} is above ${alert['price_target']:.2f}")
        elif alert["alert_type"] == "Price Below" and latest_price < alert["price_target"]:
            triggered.append(f"{symbol} is below ${alert['price_target']:.2f}")
        elif alert["alert_type"] == "Signal Is" and summary["signal"] == alert["signal_target"]:
            triggered.append(f"{symbol} signal is now {alert['signal_target']}")

    if triggered:
        for t in triggered:
            st.warning(f"Triggered: {t}")
    else:
        st.info("No alerts triggered.")

    st.markdown("#### Saved Alerts")
    alerts_df = pd.DataFrame(st.session_state.alerts)
    st.dataframe(
        alerts_df if not alerts_df.empty else pd.DataFrame(columns=["symbol", "alert_type", "price_target", "signal_target"]),
        use_container_width=True
    )
