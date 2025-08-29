import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

def train_ml_models(df: pd.DataFrame):
    """Train ML models on option chain data to predict strikes and highlight top calls/puts."""

    if df.empty or len(df) < 10:
        return {}, [], []

    try:
        # ================= Features ================= #
        df["CALL_PUT_OI_RATIO"] = df["CALL_OI"] / df["PUT_OI"].replace(0, 1)
        df["CALL_PUT_LTP_RATIO"] = df["CALL_LTP"] / df["PUT_LTP"].replace(0, 1)
        df["CALL_OI_PCT"] = df["CALL_OI"].pct_change().fillna(0)
        df["PUT_OI_PCT"] = df["PUT_OI"].pct_change().fillna(0)
        df["IV_SKEW"] = df["CALL_IV"] - df["PUT_IV"]

        features = [
            "CALL_OI", "PUT_OI", "CALL_IV", "PUT_IV",
            "CALL_CHNG_IN_OI", "PUT_CHNG_IN_OI",
            "CALL_LTP", "PUT_LTP",
            "CALL_PUT_OI_RATIO", "CALL_PUT_LTP_RATIO",
            "CALL_OI_PCT", "PUT_OI_PCT",
            "IV_SKEW"
        ]

        X = df[features].fillna(0)
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

        results, predictions = {}, {}
        df["ML_PREDICTED_STRIKE"] = 0.0

        # ================= Train Models ================= #
        for name, model in models.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            acc = r2_score(y_test, y_pred)
            results[name] = {"accuracy": round(acc, 3), "model": model}
            predictions[name] = y_pred

            # Save back to dataframe
            df[f"PRED_{name}"] = model.predict(X)

        # ================= Weighted Average ================= #
        df["ML_PREDICTED_STRIKE"] = (
            0.4 * df["PRED_LinearRegression"]
            + 0.3 * df["PRED_Ridge"]
            + 0.3 * df["PRED_RandomForest"]
        )

        # ================= Feature Importance ================= #
        rf_importances = results["RandomForest"]["model"].feature_importances_
        feature_importance = dict(zip(features, rf_importances))

        # ================= Top Calls/Puts ================= #
        top_calls = (
            df.sort_values("CALL_OI", ascending=False)
              .head(5)[["STRIKE", "CALL_OI", "CALL_IV", "CALL_LTP"]]
              .to_dict("records")
        )
        top_puts = (
            df.sort_values("PUT_OI", ascending=False)
              .head(5)[["STRIKE", "PUT_OI", "PUT_IV", "PUT_LTP"]]
              .to_dict("records")
        )

        return results, top_calls, top_puts

    except Exception as e:
        print(f"⚠️ ML Training Error: {e}")
        return {}, [], []
