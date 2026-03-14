import streamlit as st
import pandas as pd

def init_paper_trading():
    if "paper_portfolio" not in st.session_state:
        st.session_state.paper_portfolio = {
            "cash": 10000.0,
            "positions": {},
            "history": []
        }

def buy_stock(symbol, price, qty):
    cost = price * qty
    pf = st.session_state.paper_portfolio
    if cost > pf["cash"]:
        st.error("Not enough cash.")
        return

    pf["cash"] -= cost
    if symbol not in pf["positions"]:
        pf["positions"][symbol] = {"qty": 0, "avg_price": 0.0}

    pos = pf["positions"][symbol]
    new_qty = pos["qty"] + qty
    pos["avg_price"] = ((pos["qty"] * pos["avg_price"]) + cost) / new_qty
    pos["qty"] = new_qty

    pf["history"].append({
        "time": pd.Timestamp.now(),
        "type": "BUY",
        "symbol": symbol,
        "qty": qty,
        "price": price
    })
    st.success(f"Bought {qty} shares of {symbol} at ${price:.2f}")

def sell_stock(symbol, price, qty, allow_short=True):
    pf = st.session_state.paper_portfolio
    if symbol not in pf["positions"]:
        pf["positions"][symbol] = {"qty": 0, "avg_price": 0.0}

    pos = pf["positions"][symbol]

    if pos["qty"] < qty and not allow_short:
        st.error("Not enough shares to sell.")
        return

    proceeds = price * qty
    pf["cash"] += proceeds
    pos["qty"] -= qty

    if pos["qty"] == 0:
        pos["avg_price"] = 0.0

    pf["history"].append({
        "time": pd.Timestamp.now(),
        "type": "SELL",
        "symbol": symbol,
        "qty": qty,
        "price": price
    })
    st.success(f"Sold {qty} shares of {symbol} at ${price:.2f}")

def render_paper_trading(symbol, latest_price, capital_default, summary):
    pf = st.session_state.paper_portfolio

    col1, col2, col3, col4 = st.columns(4)
    if st.button("Reset Paper Account"):
        st.session_state.paper_portfolio = {
            "cash": capital_default,
            "positions": {},
            "history": []
        }
        st.success("Paper account reset.")
        st.rerun()

    with col1:
        st.metric("Cash", f"${pf['cash']:,.2f}")
    with col2:
        total_position_value = 0.0
        for sym, pos in pf["positions"].items():
            if sym == symbol:
                total_position_value += pos["qty"] * latest_price
            else:
                total_position_value += pos["qty"] * pos["avg_price"]
        st.metric("Position Value", f"${total_position_value:,.2f}")
    with col3:
        equity = pf["cash"] + total_position_value
        st.metric("Total Equity", f"${equity:,.2f}")
    with col4:
        st.metric("Model Signal", summary["signal"])

    st.markdown("#### Trade Ticket")
    qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="trade_qty")

    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"Paper BUY {symbol}"):
            buy_stock(symbol, latest_price, qty)
    with c2:
        if st.button(f"Paper SELL {symbol}"):
            sell_stock(symbol, latest_price, qty, allow_short=True)

    st.markdown("#### Open Positions")
    rows = []
    for sym, pos in pf["positions"].items():
        if pos["qty"] != 0:
            market_price = latest_price if sym == symbol else pos["avg_price"]
            unrealized = (market_price - pos["avg_price"]) * pos["qty"]
            rows.append({
                "Symbol": sym,
                "Qty": pos["qty"],
                "Avg Price": round(pos["avg_price"], 2),
                "Market Price": round(market_price, 2),
                "Unrealized P/L": round(unrealized, 2)
            })
    st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Symbol", "Qty", "Avg Price", "Market Price", "Unrealized P/L"]), use_container_width=True)

    st.markdown("#### Trade History")
    hist = pd.DataFrame(pf["history"])
    st.dataframe(hist if not hist.empty else pd.DataFrame(columns=["time", "type", "symbol", "qty", "price"]), use_container_width=True)
