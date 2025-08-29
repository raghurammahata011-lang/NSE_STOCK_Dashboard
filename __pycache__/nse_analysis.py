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
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading
import nest_asyncio
import pytz
import os
import sys

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# ================= CONFIG =================
SAVE_FOLDER = r"C:\Users\RAGHURAM MAHATA\Desktop\NSE_STOCK"
TELEGRAM_TOKEN = "8296278634:AAGGcgFUO3Hxqpmw-T1QXBtlr7Wvb7WjIj8"
CHAT_ID = "1771688728"

# Indices list
INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]

# Global variables for Telegram bot
telegram_app = None
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
    
    highest_iv_call = df.loc[df['CALL_IV'].idxmax(), ['STRIKE', 'CALL_IV']] if not df.empty else [0, 0]
    lowest_iv_call = df.loc[df['CALL_IV'].idxmin(), ['STRIKE', 'CALL_IV']] if not df.empty else [0, 0]
    highest_iv_put = df.loc[df['PUT_IV'].idxmax(), ['STRIKE', 'PUT_IV']] if not df.empty else [0, 0]
    lowest_iv_put = df.loc[df['PUT_IV'].idxmin(), ['STRIKE', 'PUT_IV']] if not df.empty else [0, 0]
    
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
        'highest_iv_call': highest_iv_call,
        'lowest_iv_call': lowest_iv_call,
        'highest_iv_put': highest_iv_put,
        'lowest_iv_put': lowest_iv_put,
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
        line=dict(color='red', width=2, shape='spline', smoothing=1.3),
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
    df = df.sort_values('STRIKE').reset_index(drop=True)
    
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

# ================= TELEGRAM FUNCTIONS =================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Welcome to NSE Option Chain Bot. Send me a symbol name (e.g., NIFTY, BANKNIFTY, RELIANCE) to get option chain data."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a symbol name to get option chain data. Supported symbols: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, or any stock symbol."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper().strip()
    
    if not text:
        await update.message.reply_text("Please send a valid symbol name.")
        return
    
    await update.message.reply_text(f"Fetching option chain data for {text}...")
    
    cookie_string = get_cookies_from_firefox()
    data = fetch_option_chain(text, cookie_string)
    
    if data:
        df = parse_data(text, data)
        if not df.empty:
            analytics = calculate_analytics(df)
            
            message = f"""
📊 *Option Chain Data for {text}*

📈 *Analytics:*
• PCR (Put-Call Ratio): {analytics['pcr']:.2f}
• Sentiment: {analytics['sentiment']}
• Strongest Support: {analytics['strongest_support']}
• Strongest Resistance: {analytics['strongest_resistance']}
• Max Pain: {analytics['max_pain']}
• Highest CALL IV: {analytics['highest_iv_call'][1]:.2f}%
• Highest PUT IV: {analytics['highest_iv_put'][1]:.2f}%

🔥 *Top 3 OI Buildup:*
*Calls:*
{analytics['top_3_call_oi'].to_string(index=False)}
*Puts:*
{analytics['top_3_put_oi'].to_string(index=False)}

🚀 *Top 3 Change in OI (Fresh Positions):*
*Calls:*
{analytics['top_3_call_oi_change'].to_string(index=False)}
*Puts:*
{analytics['top_3_put_oi_change'].to_string(index=False)}
            """
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
            # Create and save charts
            fig_oi, fig_oi_change, fig_max_pain = create_oi_analysis_charts(df, text)
            fig_iv, fig_iv_skew = create_iv_analysis_charts(df, text)
            fig_sr = create_support_resistance_chart(df, text, analytics['strongest_support'], analytics['strongest_resistance'])
            
            # Save charts as images and send
            if fig_oi:
                fig_oi.write_image("oi_chart.png")
                with open("oi_chart.png", "rb") as image:
                    await update.message.reply_photo(photo=image, caption="Open Interest Distribution")
            
            if fig_iv:
                fig_iv.write_image("iv_chart.png")
                with open("iv_chart.png", "rb") as image:
                    await update.message.reply_photo(photo=image, caption="Implied Volatility Analysis")
            
            if fig_sr:
                fig_sr.write_image("sr_chart.png")
                with open("sr_chart.png", "rb") as image:
                    await update.message.reply_photo(photo=image, caption="Support & Resistance Analysis")
            
            # Save and send Excel file
            excel_file = f"{text}_option_chain.xlsx"
            df.to_excel(excel_file, index=False)
            with open(excel_file, "rb") as file:
                await update.message.reply_document(document=file, caption=f"Option Chain Data for {text}")
            
        else:
            await update.message.reply_text("No data found for this symbol.")
    else:
        await update.message.reply_text("Failed to fetch option chain data.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")
    await update.message.reply_text("An error occurred while processing your request.")

def run_telegram_bot():
    """Run the Telegram bot in a separate thread"""
    global telegram_app, bot_running
    
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Create application
        telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        telegram_app.add_error_handler(error_handler)
        
        # Start the bot
        print("Telegram bot is running...")
        bot_running = True
        loop.run_until_complete(telegram_app.run_polling())
    except Exception as e:
        print(f"Error starting Telegram bot: {e}")
        bot_running = False

def start_telegram_bot():
    """Start Telegram bot in a separate thread"""
    global bot_running
    
    if not bot_running:
        thread = threading.Thread(target=run_telegram_bot)
        thread.daemon = True
        thread.start()
        return True
    return False

def stop_telegram_bot():
    """Stop Telegram bot"""
    global telegram_app, bot_running
    
    if telegram_app and bot_running:
        telegram_app.stop()
        bot_running = False
        return True
    return False

# ================= STREAMLIT APP =================
def run_streamlit_app():
    st.set_page_config(page_title="NSE Live Option Chain Dashboard", layout="wide")
    st.title("📊 NSE Live Option Chain Dashboard")

    # Telegram bot section
    st.subheader("🤖 Telegram Bot Integration")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Telegram Bot"):
            if start_telegram_bot():
                st.success("Telegram bot started! You can now send messages to your bot.")
            else:
                st.info("Telegram bot is already running.")
    
    with col2:
        if st.button("Stop Telegram Bot"):
            if stop_telegram_bot():
                st.success("Telegram bot stopped!")
            else:
                st.info("Telegram bot is not running.")

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
                    st.metric("Highest CALL IV", f"{analytics['highest_iv_call'][1]:.2f}" if isinstance(analytics['highest_iv_call'], pd.Series) else "N/A")
                
                with col3:
                    st.metric("Highest PUT IV", f"{analytics['highest_iv_put'][1]:.2f}" if isinstance(analytics['highest_iv_put'], pd.Series) else "N/A")
                    st.metric("Lowest CALL IV", f"{analytics['lowest_iv_call'][1]:.2f}" if isinstance(analytics['lowest_iv_call'], pd.Series) else "N/A")
                    st.metric("Lowest PUT IV", f"{analytics['lowest_iv_put'][1]:.2f}" if isinstance(analytics['lowest_iv_put'], pd.Series) else "N/A")
                
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
            else:
                st.warning("No data found for this symbol.")
        else:
            st.error("Failed to fetch option chain data.")

    st.caption(f"⏱️ Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ================= MAIN EXECUTION =================
if __name__ == "__main__":
    # Check if we're running in Streamlit or as a standalone script
    if 'streamlit' in sys.modules:
        run_streamlit_app()
    else:
        # Run as Telegram bot only
        print("Starting Telegram bot in standalone mode...")
        run_telegram_bot()