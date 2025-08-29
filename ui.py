import pandas as pd
from pandas.io.formats.style import Styler  # Explicit import for Styler
import streamlit as st
from typing import Union

def styled_option_chain(df: pd.DataFrame) -> Union[Styler, pd.DataFrame]:
    """
    Returns a styled Pandas DataFrame for display in Streamlit.
    Highlights Calls in red and Puts in green for better readability.
    """
    if df.empty:
        return df

    styled_df = (
        df.style
        .set_properties(**{"text-align": "center"})
        .format(precision=2)
        .background_gradient(subset=["CALL_OI"], cmap="Reds")
        .background_gradient(subset=["PUT_OI"], cmap="Greens")
        .background_gradient(subset=["CALL_IV"], cmap="Reds")
        .background_gradient(subset=["PUT_IV"], cmap="Greens")
    )
    return styled_df

def display_metrics(analytics: dict, price_prediction: tuple):
    """
    Display key market metrics in Streamlit cards.
    """
    if not analytics:
        st.warning("⚠️ No analytics available to display.")
        return

    st.subheader("📈 Market Analytics")

    col1, col2, col3 = st.columns(3)
    col1.metric("PCR", f"{analytics['pcr']:.2f}")
    col2.metric("Sentiment", analytics['sentiment'])
    col3.metric("Prediction", price_prediction[0])

    col4, col5, col6 = st.columns(3)
    col4.metric("Support", analytics["strongest_support"])
    col5.metric("Resistance", analytics["strongest_resistance"])
    col6.metric("Max Pain", analytics["max_pain"])
def display_decision_support(decision_data: dict):
    """
    Display floating decision support signals and key trading data in Streamlit.
    """
    if not decision_data:
        st.info("No decision support data to display.")
        return

    st.sidebar.markdown("## 🔍 Trading Signals")
    for s in decision_data.get("signals", []):
        st.sidebar.markdown(f"- {s}")

    st.sidebar.markdown("---")
    st.sidebar.metric("PCR", f"{decision_data.get('pcr', 0):.2f}")
    st.sidebar.metric("IV Skew", f"{decision_data.get('iv_skew', 0):.2f}")
    st.sidebar.metric("Call OI Momentum", f"{decision_data.get('call_oi_trend', 0):.2f}")
    st.sidebar.metric("Put OI Momentum", f"{decision_data.get('put_oi_trend', 0):.2f}")
    st.sidebar.metric("Support", decision_data.get("support", "N/A"))
    st.sidebar.metric("Resistance", decision_data.get("resistance", "N/A"))
    st.sidebar.metric("Max Pain", decision_data.get("max_pain", "N/A"))
def display_top_options(top_calls, top_puts, n=5):
    st.sidebar.markdown(f"## 🔥 Top {n} Calls by Open Interest")
    for call in top_calls:
        st.sidebar.write(f"Strike: {call['STRIKE']}, OI: {call['CALL_OI']}, IV: {call['CALL_IV']:.2f}, LTP: {call['CALL_LTP']:.2f}")

    st.sidebar.markdown(f"## 📉 Top {n} Puts by Open Interest")
    for put in top_puts:
        st.sidebar.write(f"Strike: {put['STRIKE']}, OI: {put['PUT_OI']}, IV: {put['PUT_IV']:.2f}, LTP: {put['PUT_LTP']:.2f}")
