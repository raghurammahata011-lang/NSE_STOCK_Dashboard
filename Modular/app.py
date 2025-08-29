import os
import time
from datetime import datetime
import streamlit as st

# === Import our custom modules ===
from data_fetching import get_cookies_from_firefox, fetch_option_chain, parse_data
from analytics import calculate_advanced_analytics, predict_price_direction
from ml_models import train_ml_models
from visualization import create_oi_chart, create_iv_chart, create_technical_analysis_chart, create_volatility_surface
from excel_export import save_to_excel
from ui import styled_option_chain, display_metrics

# === Config ===
SAVE_FOLDER = r"C:\Users\RAGHURAM MAHATA\Desktop\NSE_STOCK"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def run_app():
    st.set_page_config(page_title="📊 NSE Option Chain Analyzer", layout="wide")
    st.title("📊 NSE Option Chain Analyzer")

    # Sidebar Controls
    with st.sidebar:
        symbol = st.text_input("Symbol", "NIFTY").upper()
        ml_enabled = st.checkbox("Enable ML Models", value=True)
        tech_enabled = st.checkbox("Show Technical Analysis", value=True)
        vol_surface = st.checkbox("Show Volatility Surface", value=False)
        auto_refresh = st.checkbox("Auto Refresh (30s)", value=False)

    if auto_refresh:
        time.sleep(30)
        st.rerun()

    if st.button("🚀 Analyze", type="primary"):
        with st.spinner("Fetching Option Chain Data..."):
            cookie_string = get_cookies_from_firefox()
            data = fetch_option_chain(symbol, cookie_string)

        if not data:
            st.error("❌ Failed to fetch data from NSE.")
            return

        df = parse_data(symbol, data)
        if df.empty:
            st.warning("⚠️ No option chain data found.")
            return

        # === Analytics ===
        analytics = calculate_advanced_analytics(df)
        price_prediction = predict_price_direction(df, analytics)

        # === ML Models ===
        ml_results, top_calls, top_puts = {}, [], []
        if ml_enabled:
            ml_results, top_calls, top_puts = train_ml_models(df)

        # === Display Metrics ===
        display_metrics(analytics, price_prediction)

        # === Charts ===
        st.subheader("📊 Charts")
        st.plotly_chart(create_oi_chart(df), use_container_width=True)
        st.plotly_chart(create_iv_chart(df), use_container_width=True)

        if tech_enabled:
            st.plotly_chart(create_technical_analysis_chart(df), use_container_width=True)

        if vol_surface:
            st.plotly_chart(create_volatility_surface(df), use_container_width=True)

        # === Data Table ===
        st.subheader("📋 Option Chain Data")
        st.dataframe(styled_option_chain(df), use_container_width=True, height=450)

        # === ML Results ===
        if ml_enabled and ml_results:
            st.subheader("🤖 ML Models Accuracy")
            for model, details in ml_results.items():
                st.write(f"**{model}** → Accuracy: {details['accuracy']*100:.2f}%")

            st.subheader("🔥 Top Calls & Puts by OI")
            col1, col2 = st.columns(2)
            with col1:
                st.write("📈 **Top Calls**")
                st.table(top_calls)
            with col2:
                st.write("📉 **Top Puts**")
                st.table(top_puts)

        # === Export Excel ===
        file_path = save_to_excel(df, analytics, symbol, ml_results, top_calls, top_puts)
        if file_path:
            with open(file_path, "rb") as f:
                st.download_button(
                    "📥 Download Excel Report",
                    f,
                    file_name=os.path.basename(file_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.success(f"✅ Report saved at: {file_path}")

if __name__ == "__main__":
    run_app()
