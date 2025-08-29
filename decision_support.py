def generate_decision_support(analytics: dict, price_prediction: tuple) -> dict:
    """
    Generates summarized trading signals and highlights key floating data points
    for decision making based on analytics and price predictions.
    """
    if not analytics:
        return {}

    signals = []

    pcr = analytics.get("pcr", 1)
    sentiment = analytics.get("sentiment", "Neutral")
    support = analytics.get("strongest_support", None)
    resistance = analytics.get("strongest_resistance", None)
    max_pain = analytics.get("max_pain", None)
    iv_skew = analytics.get("iv_skew", 0)
    call_oi_trend = analytics.get("call_oi_trend", 0)
    put_oi_trend = analytics.get("put_oi_trend", 0)

    # PCR based signal
    if pcr > 1.5:
        signals.append("Bullish sentiment (PCR High)")
    elif pcr < 0.5:
        signals.append("Bearish sentiment (PCR Low)")

    # Price prediction
    if price_prediction:
        signals.append(f"Price Trend: {price_prediction[0]}")

    # Support/Resistance observation
    if support and resistance:
        signals.append(f"Strong Support at {support}")
        signals.append(f"Strong Resistance at {resistance}")

    # IV skew interpretation
    if iv_skew > 5:
        signals.append("High Call IV skew - possible bearish pressure")
    elif iv_skew < -5:
        signals.append("High Put IV skew - possible bullish pressure")

    # OI momentum hints
    if call_oi_trend > put_oi_trend:
        signals.append("Call OI Momentum stronger")
    elif put_oi_trend > call_oi_trend:
        signals.append("Put OI Momentum stronger")

    # Max pain reference for expiry trading
    if max_pain:
        signals.append(f"Max Pain Strike: {max_pain}")

    return {
        "signals": signals,
        "pcr": pcr,
        "iv_skew": iv_skew,
        "call_oi_trend": call_oi_trend,
        "put_oi_trend": put_oi_trend,
        "support": support,
        "resistance": resistance,
        "max_pain": max_pain
    }
def get_top_n_options(df, n=5):
    if df.empty:
        return [], []

    top_calls = df.sort_values("CALL_OI", ascending=False).head(n)
    top_puts = df.sort_values("PUT_OI", ascending=False).head(n)

    return top_calls[["STRIKE", "CALL_OI", "CALL_IV", "CALL_LTP"]].to_dict("records"), \
           top_puts[["STRIKE", "PUT_OI", "PUT_IV", "PUT_LTP"]].to_dict("records")
