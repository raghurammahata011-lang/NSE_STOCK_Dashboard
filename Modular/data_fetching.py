import time, random, requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import streamlit as st

INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]

@st.cache_data(ttl=300)
def get_cookies_from_firefox():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    st.info("Opening NSE page in Firefox to fetch cookies...")
    driver.get("https://www.nseindia.com/option-chain")
    time.sleep(8)
    cookies = driver.get_cookies()
    driver.quit()
    return "; ".join([f"{c['name']}={c['value']}" for c in cookies])

def fetch_option_chain(symbol, cookie_string):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}" if symbol in INDICES else f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*", 
        "Referer": "https://www.nseindia.com/option-chain", 
        "Cookie": cookie_string
    }
    for attempt in range(3):
        try:
            session = requests.Session()
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            resp = session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            time.sleep(random.randint(2, 4))
    return None

def parse_data(symbol, data):
    if not data: return pd.DataFrame()
    expiry_dates = data.get("records", {}).get("expiryDates", [])
    if not expiry_dates: return pd.DataFrame()
    expiry = expiry_dates[0]
    
    records = []
    for item in data.get("records", {}).get("data", []):
        if item.get("expiryDate") != expiry: continue
        ce, pe = item.get("CE", {}), item.get("PE", {})
        records.append({
            "STRIKE": item["strikePrice"],
            "CALL_OI": ce.get("openInterest", 0),
            "CALL_CHNG_IN_OI": ce.get("changeinOpenInterest", 0),
            "CALL_IV": ce.get("impliedVolatility", 0),
            "CALL_LTP": ce.get("lastPrice", 0),
            "PUT_OI": pe.get("openInterest", 0),
            "PUT_CHNG_IN_OI": pe.get("changeinOpenInterest", 0),
            "PUT_IV": pe.get("impliedVolatility", 0),
            "PUT_LTP": pe.get("lastPrice", 0)
        })
    
    df = pd.DataFrame(records)
    return df.sort_values("STRIKE").reset_index(drop=True) if not df.empty else df
