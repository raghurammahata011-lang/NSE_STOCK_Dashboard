import pandas as pd

def calculate_advanced_analytics(df: pd.DataFrame) -> dict:
    """Calculate option chain analytics like PCR, sentiment, support/resistance, IV skew, momentum"""
    if df.empty:
        return {}

    # Derived columns
    df['TOTAL_OI'] = df['CALL_OI'] + df['PUT_OI']
    df['OI_RATIO'] = df['PUT_OI'] / df['CALL_OI'].replace(0, 1)
    df['DELTA_CALL'] = df['CALL_OI'] / df['TOTAL_OI'].replace(0, 1)
    df['DELTA_PUT'] = df['PUT_OI'] / df['TOTAL_OI'].replace(0, 1)
    df['IV_DIFF'] = df['CALL_IV'] - df['PUT_IV']
    df['PRICE_RATIO'] = df['CALL_LTP'] / df['PUT_LTP'].replace(0, 1)

    # PCR
    total_put_oi = df['PUT_OI'].sum()
    total_call_oi = df['CALL_OI'].sum()
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

    # Sentiment classification
    if pcr > 2.0:
        sentiment, score, confidence = "Extremely Bullish", 3, 0.95
    elif pcr > 1.5:
        sentiment, score, confidence = "Very Bullish", 2, 0.85
    elif pcr > 1.2:
        sentiment, score, confidence = "Bullish", 1, 0.75
    elif pcr < 0.3:
        sentiment, score, confidence = "Extremely Bearish", -3, 0.95
    elif pcr < 0.5:
        sentiment, score, confidence = "Very Bearish", -2, 0.85
    elif pcr < 0.8:
        sentiment, score, confidence = "Bearish", -1, 0.75
    else:
        sentiment, score, confidence = "Neutral", 0, 0.6

    # Key levels
    strongest_support = df.loc[df['PUT_OI'].idxmax(), 'STRIKE']
    strongest_resistance = df.loc[df['CALL_OI'].idxmax(), 'STRIKE']
    max_pain = df.loc[df['TOTAL_OI'].idxmin(), 'STRIKE']

    # Confidence of levels
    support_conf = df['PUT_OI'].max() / df['PUT_OI'].mean() if df['PUT_OI'].mean() > 0 else 0
    resistance_conf = df['CALL_OI'].max() / df['CALL_OI'].mean() if df['CALL_OI'].mean() > 0 else 0

    # Volumes
    total_call_vol = df['CALL_CHNG_IN_OI'].sum()
    total_put_vol = df['PUT_CHNG_IN_OI'].sum()
    volume_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 0

    # IV analysis
    iv_skew = df['CALL_IV'].mean() - df['PUT_IV'].mean()

    # OI momentum
    call_oi_trend = df['CALL_CHNG_IN_OI'].sum() / df['CALL_OI'].sum() if df['CALL_OI'].sum() > 0 else 0
    put_oi_trend = df['PUT_CHNG_IN_OI'].sum() / df['PUT_OI'].sum() if df['PUT_OI'].sum() > 0 else 0

    # Price momentum
    call_price_mom = df['CALL_LTP'].pct_change().mean() * 100 if len(df) > 1 else 0
    put_price_mom = df['PUT_LTP'].pct_change().mean() * 100 if len(df) > 1 else 0

    return {
        "pcr": pcr,
        "sentiment": sentiment,
        "sentiment_score": score,
        "confidence": confidence,
        "strongest_support": strongest_support,
        "strongest_resistance": strongest_resistance,
        "support_confidence": min(support_conf, 1.0),
        "resistance_confidence": min(resistance_conf, 1.0),
        "max_pain": max_pain,
        "volume_ratio": volume_ratio,
        "iv_skew": iv_skew,
        "call_oi_trend": call_oi_trend,
        "put_oi_trend": put_oi_trend,
        "call_price_momentum": call_price_mom,
        "put_price_momentum": put_price_mom,
        "df": df
    }

def predict_price_direction(df: pd.DataFrame, analytics: dict):
    """Predict short-term price direction based on PCR, OI momentum, IV skew"""
    if df.empty:
        return "Insufficient data", 0, "⚪"

    call_oi_mom = df['CALL_CHNG_IN_OI'].sum()
    put_oi_mom = df['PUT_CHNG_IN_OI'].sum()
    iv_diff = df['CALL_IV'].mean() - df['PUT_IV'].mean()

    score = 0
    # PCR impact
    pcr = analytics.get("pcr", 1)
    if pcr > 1.5:
        score += 2
    elif pcr > 1.2:
        score += 1
    elif pcr < 0.5:
        score -= 2
    elif pcr < 0.8:
        score -= 1

    # OI momentum
    if call_oi_mom > put_oi_mom * 1.5:
        score -= 1.5
    elif put_oi_mom > call_oi_mom * 1.5:
        score += 1.5

    # IV skew
    if iv_diff > 5:
        score -= 1
    elif iv_diff < -5:
        score += 1

    if score >= 2:
        return "Strongly Bullish", score, "🟢"
    elif score >= 1:
        return "Bullish", score, "🟡"
    elif score <= -2:
        return "Strongly Bearish", score, "🔴"
    elif score <= -1:
        return "Bearish", score, "🟠"
    else:
        return "Neutral/Ranging", score, "⚪"
