import time, random, requests, io, threading
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import plotly.graph_objects as go
from PIL import Image
import dataframe_image as dfi

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
SAVE_FOLDER = r"C:\Users\RAGHURAM MAHATA\Desktop\NSE_STOCK"
INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]

# ================= TELEGRAM CONFIG =================
TELEGRAM_TOKEN = "8296278634:AAGGcgFUO3Hxqpmw-T1QXBtlr7Wvb7WjIj8"
CHAT_ID = "1771688728"

# ================= NSE FUNCTIONS =================
def get_cookies_from_firefox():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    st.info("Opening NSE page in Firefox to fetch cookies...")
    driver.get("https://www.nseindia.com/option-chain")
    time.sleep(10)
    cookies = driver.get_cookies()
    driver.quit()
    return "; ".join([f"{c['name']}={c['value']}" for c in cookies])

def fetch_option_chain(symbol, cookie_string):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}" if symbol in INDICES else f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain, */*", "Referer": "https://www.nseindia.com/option-chain", "Cookie": cookie_string}
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            st.error(f"Attempt {attempt+1} failed for {symbol}: {e}")
            time.sleep(random.randint(3, 7))
    return None

def parse_data(symbol, data):
    if not data: return pd.DataFrame()
    expiry_list = data.get("records", {}).get("expiryDates", [])
    if not expiry_list: return pd.DataFrame()
    latest_expiry = expiry_list[0]
    records = []
    for item in data.get("records", {}).get("data", []):
        if item.get("expiryDate") != latest_expiry: continue
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
    return df.sort_values('STRIKE').reset_index(drop=True) if not df.empty else df

def calculate_analytics(df):
    if df.empty: return {}
    total_put_oi = df['PUT_OI'].sum()
    total_call_oi = df['CALL_OI'].sum()
    pcr = total_put_oi / total_call_oi if total_call_oi>0 else 0
    strongest_support = df.loc[df['PUT_OI'].idxmax(), 'STRIKE']
    strongest_resistance = df.loc[df['CALL_OI'].idxmax(), 'STRIKE']
    df['TOTAL_OI'] = df['CALL_OI'] + df['PUT_OI']
    max_pain = df.loc[df['TOTAL_OI'].idxmin(), 'STRIKE']
    top_3_call_oi = df.nlargest(3, 'CALL_OI')[['STRIKE','CALL_OI']]
    top_3_put_oi = df.nlargest(3, 'PUT_OI')[['STRIKE','PUT_OI']]
    top_3_call_oi_change = df.nlargest(3, 'CALL_CHNG_IN_OI')[['STRIKE','CALL_CHNG_IN_OI']]
    top_3_put_oi_change = df.nlargest(3, 'PUT_CHNG_IN_OI')[['STRIKE','PUT_CHNG_IN_OI']]
    sentiment = "Neutral"
    if pcr>1.2: sentiment="Bullish"
    elif pcr<0.8: sentiment="Bearish"
    return {
        'pcr': pcr, 'strongest_support': strongest_support, 'strongest_resistance': strongest_resistance,
        'max_pain': max_pain, 'top_3_call_oi': top_3_call_oi, 'top_3_put_oi': top_3_put_oi,
        'top_3_call_oi_change': top_3_call_oi_change, 'top_3_put_oi_change': top_3_put_oi_change,
        'sentiment': sentiment
    }

def create_oi_analysis_charts(df, symbol):
    if df.empty or len(df)<3: return None, None, None
    df = df.sort_values('STRIKE').reset_index(drop=True)
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Scatter(x=df['STRIKE'], y=df['CALL_OI'], mode='lines+markers', name='Call OI', line=dict(color='red', width=2)))
    fig_oi.add_trace(go.Scatter(x=df['STRIKE'], y=df['PUT_OI'], mode='lines+markers', name='Put OI', line=dict(color='green', width=2)))
    fig_oi_change = go.Figure()
    fig_oi_change.add_trace(go.Bar(x=df['STRIKE'], y=df['CALL_CHNG_IN_OI'], name='Call OI Change', marker_color='rgba(255,100,100,0.7)'))
    fig_oi_change.add_trace(go.Bar(x=df['STRIKE'], y=df['PUT_CHNG_IN_OI'], name='Put OI Change', marker_color='rgba(100,200,100,0.7)'))
    df['TOTAL_OI'] = df['CALL_OI'] + df['PUT_OI']
    min_oi_strike = df.loc[df['TOTAL_OI'].idxmin(), 'STRIKE']
    fig_maxpain = go.Figure()
    fig_maxpain.add_trace(go.Scatter(x=df['STRIKE'], y=df['TOTAL_OI'], mode='lines+markers', name='Total OI', line=dict(color='blue', width=2)))
    fig_maxpain.add_vline(x=min_oi_strike, line=dict(color='black', dash='dash'), annotation_text=f'Max Pain: {min_oi_strike}')
    return fig_oi, fig_oi_change, fig_maxpain

# ================= TELEGRAM FUNCTION =================
def send_telegram_photo(fig=None, df=None, caption=""):
    try:
        files = {}
        if fig:
            img_bytes = fig.to_image(format="png")
            files['photo'] = ('plot.png', img_bytes)
        elif df is not None:
            buffer = io.BytesIO()
            dfi.export(df, buffer)
            buffer.seek(0)
            files['photo'] = ('table.png', buffer.read())
        if files:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            payload = {"chat_id": CHAT_ID, "caption": caption}
            requests.post(url, data=payload, files=files)
    except Exception as e:
        print(f"Telegram send failed: {e}")

# ================= TELEGRAM HANDLER =================
async def fetch_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args)==0:
            await update.message.reply_text("Usage: /fetch SYMBOL (e.g. /fetch NIFTY)")
            return
        symbol = context.args[0].upper()
        await update.message.reply_text(f"Fetching Option Chain for {symbol}...")
        cookie_string = get_cookies_from_firefox()
        data = fetch_option_chain(symbol, cookie_string)
        if not data:
            await update.message.reply_text("Failed to fetch data.")
            return
        df = parse_data(symbol, data)
        if df.empty:
            await update.message.reply_text("No data found for this symbol.")
            return
        analytics = calculate_analytics(df)
        fig_oi, fig_oi_change, fig_maxpain = create_oi_analysis_charts(df, symbol)
        alert_caption = f"NSE Option Chain Alert for {symbol} 📊\nPCR: {analytics['pcr']:.2f}\nSentiment: {analytics['sentiment']}\nStrongest Support: {analytics['strongest_support']}\nStrongest Resistance: {analytics['strongest_resistance']}\nMax Pain: {analytics['max_pain']}\nTime: {datetime.now().strftime('%H:%M:%S')}"
        if fig_oi: send_telegram_photo(fig_oi, caption="Call/Put OI Chart")
        if fig_oi_change: send_telegram_photo(fig_oi_change, caption="Call/Put OI Change Chart")
        if fig_maxpain: send_telegram_photo(fig_maxpain, caption="Max Pain Chart")
        send_telegram_photo(df=df, caption=alert_caption)
        await update.message.reply_text("✅ Option Chain sent to Telegram!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ================= START BOT THREAD =================
import pytz
from telegram.ext import ApplicationBuilder

def start_bot():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Force pytz timezone for APScheduler
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).defaults(run_async=True).timezone(pytz.timezone("Asia/Kolkata")).build()
    app.add_handler(CommandHandler("fetch", fetch_and_send))
    app.run_polling()


# ================= STREAMLIT APP =================
st.set_page_config(page_title="NSE Live Option Chain Dashboard", layout="wide")
st.title("📊 NSE Live Option Chain Dashboard")
symbol = st.text_input("🔍 Enter Symbol", "NIFTY")

if st.button("Fetch Option Chain"):
    with st.spinner("Fetching data..."):
        cookie_string = get_cookies_from_firefox()
        data = fetch_option_chain(symbol.upper(), cookie_string)
    if data:
        df = parse_data(symbol, data)
        if not df.empty:
            analytics = calculate_analytics(df)
            col1, col2, col3 = st.columns(3)
            col1.metric("PCR", f"{analytics['pcr']:.2f}")
            col2.metric("Sentiment", analytics['sentiment'])
            col3.metric("Max Pain", analytics['max_pain'])
            fig_oi, fig_oi_change, fig_maxpain = create_oi_analysis_charts(df, symbol)
            if fig_oi: st.plotly_chart(fig_oi, use_container_width=True)
            if fig_oi_change: st.plotly_chart(fig_oi_change, use_container_width=True)
            if fig_maxpain: st.plotly_chart(fig_maxpain, use_container_width=True)
            # Send to Telegram manually
            send_telegram_photo(df=df, caption=f"NSE Option Chain for {symbol}")
