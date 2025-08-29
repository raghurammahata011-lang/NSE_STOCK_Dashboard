import pandas as pd
import streamlit as st

def styled_option_chain(df: pd.DataFrame) -> pd.io.formats.style.Styler:
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
