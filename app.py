import streamlit as st
import pandas as pd
from streamlit.components.v1 import html
from data_fetching import get_cookies_from_firefox, fetch_option_chain, parse_data
from analytics import calculate_advanced_analytics, predict_price_direction
from ml_models import train_ml_models
from visualization import create_oi_chart, create_iv_chart
from decision_support import generate_decision_support, get_top_n_options

st.set_page_config(page_title="📊 NSE Option Chain Dashboard", layout="wide")

# Sidebar
with st.sidebar:
    symbol = st.text_input("Symbol", "NIFTY").upper()
    ml_enabled = st.checkbox("Enable ML Models", value=True)

# Fetch data
with st.spinner("Fetching NSE Option Chain Data..."):
    cookie = get_cookies_from_firefox()
    data = fetch_option_chain(symbol, cookie)

if not data:
    st.error("Failed to fetch NSE data")
    st.stop()

df = parse_data(symbol, data)

# === Analytics & Decision Support ===
analytics = calculate_advanced_analytics(df)
prediction = predict_price_direction(df, analytics)
decision_data = generate_decision_support(analytics, prediction)
top_calls, top_puts = get_top_n_options(df, n=5)

# Convert top options to DataFrames
top_calls_df = pd.DataFrame(top_calls)
top_puts_df = pd.DataFrame(top_puts)

# === ML Models ===
ml_results, ml_top_calls, ml_top_puts = {}, pd.DataFrame(), pd.DataFrame()
if ml_enabled:
    # Sanitize data for ML (replace inf/-inf with NaN and drop)
    df_clean = df.replace([float('inf'), float('-inf')], pd.NA).dropna()
    if not df_clean.empty:
        ml_results, ml_top_calls, ml_top_puts = train_ml_models(df_clean)
    else:
        st.warning("ML training skipped: no valid data after cleaning.")

# Charts
oi_chart = create_oi_chart(df).to_html(include_plotlyjs='cdn')
iv_chart = create_iv_chart(df).to_html(include_plotlyjs=False)

# Helper: DataFrame to Bootstrap HTML Table
def df_to_html_table(df, title):
    if df.empty:
        return f"<div class='card mb-3'><div class='card-header bg-primary text-white'>{title}</div><div class='card-body'>No data available</div></div>"
    html_table = df.to_html(index=False, classes="table table-striped table-hover", border=0)
    return f"""
    <div class="card mb-3">
        <div class="card-header bg-primary text-white">{title}</div>
        <div class="card-body">{html_table}</div>
    </div>
    """

top_calls_html = df_to_html_table(top_calls_df, "Top 5 Calls")
top_puts_html = df_to_html_table(top_puts_df, "Top 5 Puts")

# Decision Support Cards
decision_html = ""
for key, value in decision_data.items():
    decision_html += f"""
    <div class="card mb-2">
        <div class="card-body">
            <strong>{key}</strong>: {value}
        </div>
    </div>
    """

# ML Models Cards
ml_html = ""
for model, details in ml_results.items():
    r2 = details.get('r2_score', 0) * 100
    color = "success" if r2 >= 70 else "warning" if r2 >= 50 else "danger"
    ml_html += f"""
    <div class="col-md-3">
        <div class="card text-center mb-3">
            <div class="card-body">
                <strong>{model}</strong><br>
                <span class="badge bg-{color}" style="font-size:1rem;">R²: {r2:.2f}%</span>
            </div>
        </div>
    </div>
    """

# Top ML Predictions
def options_with_badges(df, title, oi_col):
    if df.empty:
        return ""
    rows = ""
    for _, row in df.iterrows():
        direction = "↑" if row.get("Signal","")=="Call" else "↓"
        color = "success" if direction=="↑" else "danger"
        rows += f"""
        <tr>
            <td>{row.get('STRIKE', 'N/A')}</td>
            <td>{row.get(oi_col, 0)}</td>
            <td><span class="badge bg-{color}">{direction}</span></td>
        </tr>
        """
    return f"""
    <div class="card mb-3">
        <div class="card-header bg-info text-white">{title}</div>
        <div class="card-body">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Strike</th>
                        <th>OI</th>
                        <th>Signal</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>
    """

ml_calls_html = options_with_badges(ml_top_calls, "Top ML Predicted Calls", "CALL_OI")
ml_puts_html = options_with_badges(ml_top_puts, "Top ML Predicted Puts", "PUT_OI")

# Get volatility value safely
volatility_value = analytics.get('volatility', 'N/A')
if isinstance(volatility_value, (int, float)):
    volatility_display = f"{volatility_value:.2f}%"
else:
    volatility_display = str(volatility_value)

# Get current price safely
current_price = analytics.get('current_price', analytics.get('underlying', 'N/A'))
if isinstance(current_price, (int, float)):
    current_price_display = f"₹{current_price:.2f}"
else:
    current_price_display = str(current_price)

# === Full HTML Dashboard ===
dashboard_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NSE Option Chain Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{background-color: #f5f6fa; font-family: 'Segoe UI', sans-serif; padding:20px;}}
        .metric-card {{padding:15px; border-radius:12px; box-shadow:0 4px 8px rgba(0,0,0,0.1); margin-bottom:15px;}}
        .metric-title {{font-weight:bold; color:#34495e;}}
        .metric-value {{font-size:1.5rem; color:#e74c3c;}}
        h1 {{color:#2c3e50; font-weight:bold; margin-bottom:30px;}}
        .card {{border-radius:12px; box-shadow:0 4px 8px rgba(0,0,0,0.1);}}
        .card-header {{font-weight:bold;}}
    </style>
</head>
<body>
    <h1>📊 NSE Option Chain Dashboard - {symbol}</h1>

    <!-- Metrics Row -->
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="metric-card bg-white text-center">
                <div class="metric-title">Current Price</div>
                <div class="metric-value">{current_price_display}</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="metric-card bg-white text-center">
                <div class="metric-title">Predicted Direction</div>
                <div class="metric-value">{prediction}</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="metric-card bg-white text-center">
                <div class="metric-title">Volatility</div>
                <div class="metric-value">{volatility_display}</div>
            </div>
        </div>
    </div>

    <!-- Charts Row -->
    <div class="row mb-4">
        <div class="col-md-6">{oi_chart}</div>
        <div class="col-md-6">{iv_chart}</div>
    </div>

    <!-- Top Calls & Puts -->
    <div class="row mb-4">
        <div class="col-md-6">{top_calls_html}</div>
        <div class="col-md-6">{top_puts_html}</div>
    </div>

    <!-- ML Models Accuracy -->
    <h3>🤖 ML Models Accuracy</h3>
    <div class="row mb-4">{ml_html}</div>

    <!-- Top ML Predictions -->
    <div class="row mb-4">
        <div class="col-md-6">{ml_calls_html}</div>
        <div class="col-md-6">{ml_puts_html}</div>
    </div>

    <!-- Decision Support -->
    <h3>💡 Decision Support</h3>
    {decision_html}

</body>
</html>
"""

# Render the full HTML
html(dashboard_html, height=1500)