import time, random, requests
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns
import asyncio
import threading
import nest_asyncio
import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# ================= CONFIG =================
SAVE_FOLDER = r"C:\Users\RAGHURAM MAHATA\Desktop\NSE_STOCK"
TELEGRAM_TOKEN = "8296278634:AAGGcgFUO3Hxqpmw-T1QXBtlr7Wvb7WjIj8"
CHAT_ID = "1771688728"
WEBHOOK_URL = "https://your-domain.com/webhook"  # You need to set this up with ngrok or similar

# Indices list
INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]

# Global variables for Telegram bot
bot_running = False

# ==========================================

def get_cookies_from_firefox():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)

    st.info("Opening NSE page in Firefox to fetch cookies...")
    driver.get("https://www.nseindia.com/option-chain")
    time.sleep(10)

    cookies = driver.get_cookies()
    driver.quit()

    cookie_string = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    return cookie_string

def fetch_option_chain(symbol, cookie_string):
    if symbol in INDICES:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    else:
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/option-chain",
        "Cookie": cookie_string,
    }

    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Attempt {attempt+1} failed for {symbol}: {e}")
            time.sleep(random.randint(3, 7))
    return None

def parse_data(symbol, data):
    if not data:
        return pd.DataFrame()

    expiry_list = data.get("records", {}).get("expiryDates", [])
    if not expiry_list:
        return pd.DataFrame()

    latest_expiry = expiry_list[0]
    records = []

    for item in data.get("records", {}).get("data", []):
        if item.get("expiryDate") != latest_expiry:
            continue

        strike = item.get("strikePrice")
        ce = item.get("CE", {})
        pe = item.get("PE", {})

        records.append({
            "CALL_OI": ce.get("openInterest", 0),
            "CALL_CHNG_IN_OI": ce.get("changeinOpenInterest", 0),
            "CALL_VOLUME": ce.get("totalTradedVolume", 0),
            "CALL_IV": ce.get("impliedVolatility", 0),
            "CALL_LTP": ce.get("lastPrice", 0),
            "CALL_CHNG": ce.get("change", 0),
            "STRIKE": strike,
            "PUT_CHNG": pe.get("change", 0),
            "PUT_LTP": pe.get("lastPrice", 0),
            "PUT_IV": pe.get("impliedVolatility", 0),
            "PUT_VOLUME": pe.get("totalTradedVolume", 0),
            "PUT_CHNG_IN_OI": pe.get("changeinOpenInterest", 0),
            "PUT_OI": pe.get("openInterest", 0),
        })

    df = pd.DataFrame(records)
    
    if not df.empty:
        df = df.sort_values('STRIKE').reset_index(drop=True)
    
    return df

def calculate_analytics(df):
    if df.empty:
        return {}
    
    total_put_oi = df['PUT_OI'].sum()
    total_call_oi = df['CALL_OI'].sum()
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
    
    strongest_support = df.loc[df['PUT_OI'].idxmax(), 'STRIKE'] if not df.empty else 0
    strongest_resistance = df.loc[df['CALL_OI'].idxmax(), 'STRIKE'] if not df.empty else 0
    
    df['TOTAL_OI'] = df['CALL_OI'] + df['PUT_OI']
    max_pain = df.loc[df['TOTAL_OI'].idxmin(), 'STRIKE'] if not df.empty else 0
    
    # Fix for deprecated Series indexing - use .iloc instead of direct indexing
    highest_iv_call_strike = df.loc[df['CALL_IV'].idxmax(), 'STRIKE'] if not df.empty else 0
    highest_iv_call_value = df['CALL_IV'].max() if not df.empty else 0
    lowest_iv_call_strike = df.loc[df['CALL_IV'].idxmin(), 'STRIKE'] if not df.empty else 0
    lowest_iv_call_value = df['CALL_IV'].min() if not df.empty else 0
    highest_iv_put_strike = df.loc[df['PUT_IV'].idxmax(), 'STRIKE'] if not df.empty else 0
    highest_iv_put_value = df['PUT_IV'].max() if not df.empty else 0
    lowest_iv_put_strike = df.loc[df['PUT_IV'].idxmin(), 'STRIKE'] if not df.empty else 0
    lowest_iv_put_value = df['PUT_IV'].min() if not df.empty else 0
    
    top_3_call_oi = df.nlargest(3, 'CALL_OI')[['STRIKE', 'CALL_OI']]
    top_3_put_oi = df.nlargest(3, 'PUT_OI')[['STRIKE', 'PUT_OI']]
    top_3_call_oi_change = df.nlargest(3, 'CALL_CHNG_IN_OI')[['STRIKE', 'CALL_CHNG_IN_OI']]
    top_3_put_oi_change = df.nlargest(3, 'PUT_CHNG_IN_OI')[['STRIKE', 'PUT_CHNG_IN_OI']]
    
    if pcr > 1.2:
        sentiment = "Bullish"
        sentiment_color = "green"
    elif pcr < 0.8:
        sentiment = "Bearish"
        sentiment_color = "red"
    else:
        sentiment = "Neutral"
        sentiment_color = "yellow"
    
    return {
        'pcr': pcr,
        'strongest_support': strongest_support,
        'strongest_resistance': strongest_resistance,
        'max_pain': max_pain,
        'highest_iv_call_strike': highest_iv_call_strike,
        'highest_iv_call_value': highest_iv_call_value,
        'lowest_iv_call_strike': lowest_iv_call_strike,
        'lowest_iv_call_value': lowest_iv_call_value,
        'highest_iv_put_strike': highest_iv_put_strike,
        'highest_iv_put_value': highest_iv_put_value,
        'lowest_iv_put_strike': lowest_iv_put_strike,
        'lowest_iv_put_value': lowest_iv_put_value,
        'top_3_call_oi': top_3_call_oi,
        'top_3_put_oi': top_3_put_oi,
        'top_3_call_oi_change': top_3_call_oi_change,
        'top_3_put_oi_change': top_3_put_oi_change,
        'sentiment': sentiment,
        'sentiment_color': sentiment_color
    }

# Add these imports for smooth graphs
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

def create_oi_analysis_charts(df, symbol):
    """Create Open Interest analysis charts"""
    if df.empty or len(df) < 3:
        return None, None, None
    
    # Sort by strike price for smoother graphs
    df = df.sort_values('STRIKE').reset_index(drop=True)
    
    # 1. OI Distribution Chart
    fig_oi = go.Figure()
    
    # Add call OI
    fig_oi.add_trace(go.Scatter(
        x=df['STRIKE'],
        y=df['CALL_OI'],
        name='Call OI',
        mode='lines+markers',
        line=dict(color='red', width=2, shape='spline', smoothing=1.3),
        marker=dict(size=4),
        hovertemplate='Strike: %{x}<br>Call OI: %{y:,.0f}<extra></extra>'
    ))
    
    # Add put OI
    fig_oi.add_trace(go.Scatter(
        x=df['STRIKE'],
        y=df['PUT_OI'],
        name='Put OI',
        mode='lines+markers',
        line=dict(color='green', width=2, shape='spline', smoothing=1.3),
        marker=dict(size=4),
        hovertemplate='Strike: %{x}<br>Put OI: %{y:,.0f}<extra></extra>'
    ))
    
    fig_oi.update_layout(
        title=f'{symbol} - Open Interest Distribution',
        xaxis_title='Strike Price',
        yaxis_title='Open Interest',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 2. OI Change Chart
    fig_oi_change = go.Figure()
    
    # Add call OI change
    fig_oi_change.add_trace(go.Bar(
        x=df['STRIKE'],
        y=df['CALL_CHNG_IN_OI'],
        name='Call OI Change',
        marker_color='rgba(255, 100, 100, 0.7)',
        hovertemplate='Strike: %{x}<br>Call OI Change: %{y:,.0f}<extra></extra>'
    ))
    
    # Add put OI change
    fig_oi_change.add_trace(go.Bar(
        x=df['STRIKE'],
        y=df['PUT_CHNG_IN_OI'],
        name='Put OI Change',
        marker_color='rgba(100, 200, 100, 0.7)',
        hovertemplate='Strike: %{x}<br>Put OI Change: %{y:,.0f}<extra></extra>'
    ))
    
    fig_oi_change.update_layout(
        title=f'{symbol} - Open Interest Change',
        xaxis_title='Strike Price',
        yaxis_title='Change in OI',
        barmode='group',
        bargap=0.3,
        height=400
    )
    
    # 3. Max Pain Chart
    df['TOTAL_OI'] = df['CALL_OI'] + df['PUT_OI']
    min_oi_strike = df.loc[df['TOTAL_OI'].idxmin(), 'STRIKE'] if not df.empty else 0
    
    fig_max_pain = go.Figure()
    
    fig_max_pain.add_trace(go.Scatter(
        x=df['STRIKE'],
        y=df['TOTAL_OI'],
        mode='lines+markers',
        name='Total OI',
        line=dict(color='blue', width=2, shape='spline', smoothing=1.3),
        marker=dict(size=4),
        hovertemplate='Strike: %{x}<br>Total OI: %{y:,.0f}<extra></extra>'
    ))
    
    # Highlight max pain point
    fig_max_pain.add_trace(go.Scatter(
        x=[min_oi_strike],
        y=[df[df['STRIKE'] == min_oi_strike]['TOTAL_OI'].values[0] if not df.empty else 0],
        mode='markers+text',
        marker=dict(color='red', size=10),
        text=['Max Pain'],
        textposition='top center',
        name='Max Pain',
        showlegend=False
    ))
    
    fig_max_pain.update_layout(
        title=f'{symbol} - Max Pain Analysis',
        xaxis_title='Strike Price',
        yaxis_title='Total OI (Call + Put)',
        height=400
    )
    
    return fig_oi, fig_oi_change, fig_max_pain

def create_iv_analysis_charts(df, symbol):
    """Create IV analysis charts"""
    if df.empty or len(df) < 3:
        return None, None
    
    # Sort by strike price for smoother graphs
    df = df.sort_values('STRIKE').reset_index(drop=True)
    
    # 1. IV Comparison Chart
    fig_iv = go.Figure()
    
    # Add call IV
    fig_iv.add_trace(go.Scatter(
        x=df['STRIKE'],
        y=df['CALL_IV'],
        mode='lines+markers',
        name='Call IV',
        line=dict(color='red', width = 2, shape='spline', smoothing=1.3),
        marker=dict(size=4),
        hovertemplate='Strike: %{x}<br>Call IV: %{y:.2f}%<extra></extra>'
    ))
    
    # Add put IV
    fig_iv.add_trace(go.Scatter(
        x=df['STRIKE'],
        y=df['PUT_IV'],
        mode='lines+markers',
        name='Put IV',
        line=dict(color='green', width=2, shape='spline', smoothing=1.3),
        marker=dict(size=4),
        hovertemplate='Strike: %{x}<br>Put IV: %{y:.2f}%<extra></extra>'
    ))
    
    fig_iv.update_layout(
        title=f'{symbol} - Implied Volatility Analysis',
        xaxis_title='Strike Price',
        yaxis_title='Implied Volatility (%)',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 2. IV Skew Chart (Put IV - Call IV)
    df['IV_SKEW'] = df['PUT_IV'] - df['CALL_IV']
    
    fig_iv_skew = go.Figure()
    
    fig_iv_skew.add_trace(go.Scatter(
        x=df['STRIKE'],
        y=df['IV_SKEW'],
        mode='lines+markers',
        name='IV Skew (Put - Call)',
        line=dict(color='purple', width=2, shape='spline', smoothing=1.3),
        marker=dict(size=4),
        hovertemplate='Strike: %{x}<br>IV Skew: %{y:.2f}%<extra></extra>'
    ))
    
    # Add zero reference line
    fig_iv_skew.add_hline(y=0, line_dash="dash", line_color="gray")
    
    fig_iv_skew.update_layout(
        title=f'{symbol} - IV Skew Analysis',
        xaxis_title='Strike Price',
        yaxis_title='IV Skew (Put IV - Call IV)',
        height=400
    )
    
    return fig_iv, fig_iv_skew

def create_support_resistance_chart(df, symbol, strongest_support, strongest_resistance):
    """Create support resistance chart based on OI"""
    if df.empty:
        return None
    
    # Sort by strike price for smoother graphs
    df = df.sort_values('STRIKE').reset_index(dop=True)
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.1, 
                       subplot_titles=('Call OI - Resistance Levels', 'Put OI - Support Levels'))
    
    # Call OI for resistance
    fig.add_trace(go.Scatter(
        x=df['STRIKE'],
        y=df['CALL_OI'],
        name='Call OI',
        mode='lines+markers',
        line=dict(color='red', width=2, shape='spline', smoothing=1.3),
        marker=dict(size=4),
        hovertemplate='Strike: %{x}<br>Call OI: %{y:,.0f}<extra></extra>'
    ), row=1, col=1)
    
    # Highlight strongest resistance
    if strongest_resistance in df['STRIKE'].values:
        resistance_oi = df[df['STRIKE'] == strongest_resistance]['CALL_OI'].values[0]
        fig.add_trace(go.Scatter(
            x=[strongest_resistance],
            y=[resistance_oi],
            mode='markers+text',
            marker=dict(color='darkred', size=12),
            text=['Strongest Resistance'],
            textposition='top center',
            name='Strongest Resistance',
            showlegend=False
        ), row=1, col=1)
    
    # Put OI for support
    fig.add_trace(go.Scatter(
        x=df['STRIKE'],
        y=df['PUT_OI'],
        name='Put OI',
        mode='lines+markers',
        line=dict(color='green', width=2, shape='spline', smoothing=1.3),
        marker=dict(size=4),
        hovertemplate='Strike: %{x}<br>Put OI: %{y:,.0f}<extra></extra>'
    ), row=2, col=1)
    
    # Highlight strongest support
    if strongest_support in df['STRIKE'].values:
        support_oi = df[df['STRIKE'] == strongest_support]['PUT_OI'].values[0]
        fig.add_trace(go.Scatter(
            x=[strongest_support],
            y=[support_oi],
            mode='markers+text',
            marker=dict(color='darkgreen', size=12),
            text=['Strongest Support'],
            textposition='top center',
            name='Strongest Support',
            showlegend=False
        ), row=2, col=1)
    
    fig.update_layout(
        title_text=f'{symbol} - Support & Resistance Analysis',
        height=600,
        showlegend=False
    )
    
    fig.update_xaxes(title_text='Strike Price', row=2, col=1)
    fig.update_yaxes(title_text='Call OI', row=1, col=1)
    fig.update_yaxes(title_text='Put OI', row=2, col=1)
    
    return fig

# ================= SIMPLE TELEGRAM BOT =================
def send_telegram_message(message):
    """Send a simple message via Telegram bot"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def send_telegram_document(file_path, caption=""):
    """Send a document via Telegram bot"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        with open(file_path, "rb") as file:
            files = {"document": file}
            data = {"chat_id": CHAT_ID, "caption": caption}
            response = requests.post(url, files=files, data=data)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram document: {e}")
        return False

def get_telegram_updates():
    """Get recent messages from Telegram bot"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error getting Telegram updates: {e}")
        return None

def process_telegram_command(command, symbol):
    """Process command from Telegram"""
    if command == "/start":
        return "Hello! Welcome to NSE Option Chain Bot. Send me a symbol name to get option chain data."
    elif command == "/help":
        return "Send me a symbol name to get option chain data. Supported symbols: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, or any stock symbol."
    else:
        # Fetch data for the symbol
        cookie_string = get_cookies_from_firefox()
        data = fetch_option_chain(symbol.upper(), cookie_string)
        
        if data:
            df = parse_data(symbol, data)
            if not df.empty:
                analytics = calculate_analytics(df)
                
                message = f"""
📊 Option Chain Data for {symbol}

📈 Analytics:
• PCR (Put-Call Ratio): {analytics['pcr']:.2f}
• Sentiment: {analytics['sentiment']}
• Strongest Support: {analytics['strongest_support']}
• Strongest Resistance: {analytics['strongest_resistance']}
• Max Pain: {analytics['max_pain']}
• Highest CALL IV: {analytics['highest_iv_call_value']:.2f}%
• Highest PUT IV: {analytics['highest_iv_put_value']:.2f}%

🔥 Top 3 OI Buildup:
Calls:
{analytics['top_3_call_oi'].to_string(index=False)}
Puts:
{analytics['top_3_put_oi'].to_string(index=False)}

🚀 Top 3 Change in OI (Fresh Positions):
Calls:
{analytics['top_3_call_oi_change'].to_string(index=False)}
Puts:
{analytics['top_3_put_oi_change'].to_string(index=False)}
                """
                
                # Save and send Excel file
                excel_file = f"{symbol}_option_chain.xlsx"
                df.to_excel(excel_file, index=False)
                send_telegram_document(excel_file, f"Option Chain Data for {symbol}")
                
                return message
            else:
                return "No data found for this symbol."
        else:
            return "Failed to fetch option chain data."

# ================= SIMPLE TELEGRAM WEBHOOK SERVER =================
class TelegramHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update = json.loads(post_data.decode('utf-8'))
        
        try:
            message = update['message']['text']
            chat_id = update['message']['chat']['id']
            
            if message.startswith('/'):
                command = message.split()[0]
                symbol = message[len(command):].strip()
                if not symbol:
                    symbol = "NIFTY"  # Default symbol
                
                response = process_telegram_command(command, symbol)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                # Send response back to user
                send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": response,
                    "parse_mode": "HTML"
                }
                requests.post(send_url, json=payload)
                
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            print(f"Error processing Telegram update: {e}")
            self.send_response(200)
            self.end_headers()

def run_telegram_webhook():
    """Run a simple webhook server for Telegram"""
    server = HTTPServer(('localhost', 8443), TelegramHandler)
    print("Telegram webhook server running on port 8443")
    server.serve_forever()

def setup_telegram_webhook():
    """Setup Telegram webhook"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
        payload = {
            "url": WEBHOOK_URL,
            "max_connections": 1
        }
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error setting up webhook: {e}")
        return False

# ================= STREAMLIT APP =================
def run_streamlit_app():
    st.set_page_config(page_title="NSE Live Option Chain Dashboard", layout="wide")
    st.title("📊 NSE Live Option Chain Dashboard")

    # Telegram bot section
    st.subheader("🤖 Telegram Bot Integration")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Setup Telegram Webhook"):
            if setup_telegram_webhook():
                st.success("Telegram webhook setup successfully!")
            else:
                st.error("Failed to setup Telegram webhook")
    
    with col2:
        if st.button("Check Telegram Messages"):
            updates = get_telegram_updates()
            if updates and 'result' in updates:
                st.info(f"Found {len(updates['result'])} messages")
                for update in updates['result']:
                    if 'message' in update and 'text' in update['message']:
                        st.write(f"Message: {update['message']['text']}")
            else:
                st.info("No messages found or error retrieving messages")

    # Manual Telegram message sending
    st.subheader("💬 Send Manual Telegram Message")
    telegram_message = st.text_input("Message to send to Telegram")
    if st.button("Send to Telegram"):
        if telegram_message:
            if send_telegram_message(telegram_message):
                st.success("Message sent to Telegram!")
            else:
                st.error("Failed to send message to Telegram")
        else:
            st.warning("Please enter a message to send")

    # Symbol selection
    st.subheader("🔍 Web Interface")
    symbol = st.text_input("Enter Symbol (e.g. NIFTY, BANKNIFTY, RELIANCE, HDFCBANK)", "NIFTY")

    if st.button("Fetch Option Chain"):
        with st.spinner("Fetching data..."):
            cookie_string = get_cookies_from_firefox()
            data = fetch_option_chain(symbol.upper(), cookie_string)

        if data:
            df = parse_data(symbol, data)
            if not df.empty:
                st.success(f"Showing data for {symbol.upper()} (Nearest Expiry)")
                
                analytics = calculate_analytics(df)
                
                st.subheader("📈 Analytics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("PCR (Put-Call Ratio)", f"{analytics['pcr']:.2f}")
                    st.metric("Sentiment", analytics['sentiment'])
                    st.metric("Strongest Support", analytics['strongest_support'])
                
                with col2:
                    st.metric("Strongest Resistance", analytics['strongest_resistance'])
                    st.metric("Max Pain", analytics['max_pain'])
                    st.metric("Highest CALL IV", f"{analytics['highest_iv_call_value']:.2f}%")
                
                with col3:
                    st.metric("Highest PUT IV", f"{analytics['highest_iv_put_value']:.2f}%")
                    st.metric("Lowest CALL IV", f"{analytics['lowest_iv_call_value']:.2f}%")
                    st.metric("Lowest PUT IV", f"{analytics['lowest_iv_put_value']:.2f}%")
                
                st.subheader("🔥 Top 3 OI Buildup")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("Calls:")
                    st.dataframe(analytics['top_3_call_oi'])
                
                with col2:
                    st.write("Puts:")
                    st.dataframe(analytics['top_3_put_oi'])
                
                st.subheader("🚀 Top 3 Change in OI (Fresh Positions)")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("Calls:")
                    st.dataframe(analytics['top_3_call_oi_change'])
                
                with col2:
                    st.write("Puts:")
                    st.dataframe(analytics['top_3_put_oi_change'])
                
                st.subheader("📋 Option Chain Data")
                st.dataframe(df)
                
                # Display charts
                st.subheader("📊 Market Analytics Charts")
                
                # Create and display charts
                fig_oi, fig_oi_change, fig_max_pain = create_oi_analysis_charts(df, symbol.upper())
                fig_iv, fig_iv_skew = create_iv_analysis_charts(df, symbol.upper())
                fig_sr = create_support_resistance_chart(df, symbol.upper(), 
                                                        analytics['strongest_support'], 
                                                        analytics['strongest_resistance'])
                
                # Display OI charts
                if fig_oi and fig_oi_change and fig_max_pain:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.plotly_chart(fig_oi, use_container_width=True)
                    with col2:
                        st.plotly_chart(fig_oi_change, use_container_width=True)
                    
                    st.plotly_chart(fig_max_pain, use_container_width=True)
                
                # Display IV charts
                if fig_iv and fig_iv_skew:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.plotly_chart(fig_iv, use_container_width=True)
                    with col2:
                        st.plotly_chart(fig_iv_skew, use_container_width=True)
                
                # Display Support Resistance chart
                if fig_sr:
                    st.plotly_chart(fig_sr, use_container_width=True)
                
                # Save CSV
                filename = f"{SAVE_FOLDER}\\{symbol.upper()}.csv"
                df.to_csv(filename, index=False)
                st.info(f"Saved to {filename}")
                
                # Send to Telegram option
                if st.button("Send Data to Telegram"):
                    message = f"Option chain data for {symbol} fetched successfully!\nPCR: {analytics['pcr']:.2f}, Sentiment: {analytics['sentiment']}"
                    if send_telegram_message(message):
                        st.success("Data sent to Telegram!")
                    else:
                        st.error("Failed to send data to Telegram")
            else:
                st.warning("No data found for this symbol.")
        else:
            st.error("Failed to fetch option chain data.")

    st.caption(f"⏱️ Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ================= MAIN EXECUTION =================
if __name__ == "__main__":
    run_streamlit_app()