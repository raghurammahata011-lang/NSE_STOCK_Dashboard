import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

def train_ml_models(df: pd.DataFrame):
    """Train ML models on option chain data to predict strikes and highlight top calls/puts."""
    
    if df.empty or len(df) < 10:
        return {}, pd.DataFrame(), pd.DataFrame()

    try:
        # ================= Features ================= #
        # Avoid division by zero & replace inf with NaN
        df["CALL_PUT_OI_RATIO"] = df["CALL_OI"] / df["PUT_OI"].replace(0, np.nan)
        df["CALL_PUT_LTP_RATIO"] = df["CALL_LTP"] / df["PUT_LTP"].replace(0, np.nan)
        df["CALL_OI_PCT"] = df["CALL_OI"].pct_change()
        df["PUT_OI_PCT"] = df["PUT_OI"].pct_change()
        df["IV_SKEW"] = df["CALL_IV"] - df["PUT_IV"]

        # Replace infinite or NaN values
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)

        features = [
            "CALL_OI", "PUT_OI", "CALL_IV", "PUT_IV",
            "CALL_CHNG_IN_OI", "PUT_CHNG_IN_OI",
            "CALL_LTP", "PUT_LTP",
            "CALL_PUT_OI_RATIO", "CALL_PUT_LTP_RATIO",
            "CALL_OI_PCT", "PUT_OI_PCT",
            "IV_SKEW"
        ]

        X = df[features]
        y = df["STRIKE"]

        # ================= Train/Test Split ================= #
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42
        )

        models = {
            "LinearRegression": LinearRegression(),
            "Ridge": Ridge(alpha=1.0),
            "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42)
        }

        results = {}
        predictions = {}

        # ================= Train Models ================= #
        for name, model in models.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            r2 = r2_score(y_test, y_pred)
            results[name] = {"r2_score": round(r2, 3), "model": model}
            predictions[name] = y_pred

        # ================= Top Calls/Puts ================= #
        top_calls = (
            df.sort_values("CALL_OI", ascending=False)
              .head(5)[["STRIKE", "CALL_OI", "CALL_IV", "CALL_LTP"]]
        )
        top_puts = (
            df.sort_values("PUT_OI", ascending=False)
              .head(5)[["STRIKE", "PUT_OI", "PUT_IV", "PUT_LTP"]]
        )

        return results, top_calls, top_puts

    except Exception as e:
        print(f"⚠️ ML Training Error: {e}")
        return {}, pd.DataFrame(), pd.DataFrame()
