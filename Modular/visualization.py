import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ================== Open Interest Chart ================== #
def create_oi_chart(df: pd.DataFrame):
    """Create OI Distribution Chart (Calls vs Puts)."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Calls OI
    fig.add_trace(go.Bar(
        x=df["STRIKE"], y=df["CALL_OI"], name="Call OI",
        marker_color="red", opacity=0.6
    ))

    # Puts OI
    fig.add_trace(go.Bar(
        x=df["STRIKE"], y=df["PUT_OI"], name="Put OI",
        marker_color="green", opacity=0.6
    ))

    fig.update_layout(
        title="Open Interest (OI) Distribution",
        xaxis_title="Strike Price",
        yaxis_title="Open Interest",
        barmode="group",
        template="plotly_white"
    )

    return fig

# ================== Implied Volatility Chart ================== #
def create_iv_chart(df: pd.DataFrame):
    """Create IV Chart for Calls and Puts."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["STRIKE"], y=df["CALL_IV"],
        mode="lines+markers", name="Call IV",
        line=dict(color="red")
    ))

    fig.add_trace(go.Scatter(
        x=df["STRIKE"], y=df["PUT_IV"],
        mode="lines+markers", name="Put IV",
        line=dict(color="green")
    ))

    fig.update_layout(
        title="Implied Volatility (IV) Curve",
        xaxis_title="Strike Price",
        yaxis_title="Implied Volatility (%)",
        template="plotly_white"
    )

    return fig

# ================== Technical Analysis Chart ================== #
def create_technical_analysis_chart(df: pd.DataFrame):
    """Combine OI Change and Price Momentum for Calls and Puts."""
    if df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.15,
        subplot_titles=("OI Change", "Price Momentum")
    )

    # OI Change
    fig.add_trace(go.Bar(
        x=df["STRIKE"], y=df["CALL_CHNG_IN_OI"],
        name="Call OI Change", marker_color="red"
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df["STRIKE"], y=df["PUT_CHNG_IN_OI"],
        name="Put OI Change", marker_color="green"
    ), row=1, col=1)

    # Price Momentum
    fig.add_trace(go.Scatter(
        x=df["STRIKE"], y=df["CALL_LTP"],
        mode="lines+markers", name="Call LTP",
        line=dict(color="red")
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=df["STRIKE"], y=df["PUT_LTP"],
        mode="lines+markers", name="Put LTP",
        line=dict(color="green")
    ), row=2, col=1)

    fig.update_layout(
        title="Technical Analysis: OI Change & Price Momentum",
        template="plotly_white",
        height=600
    )

    return fig

# ================== Volatility Surface (Optional) ================== #
def create_volatility_surface(df: pd.DataFrame):
    """Create 3D Volatility Surface for Calls and Puts."""
    if df.empty:
        return go.Figure()

    strikes = df["STRIKE"].values
    call_iv = df["CALL_IV"].values
    put_iv = df["PUT_IV"].values

    fig = go.Figure(data=[
        go.Surface(
            z=[call_iv, put_iv],
            x=[strikes, strikes],
            y=[["Call"]*len(strikes), ["Put"]*len(strikes)],
            colorscale="Viridis"
        )
    ])

    fig.update_layout(
        title="Volatility Surface",
        scene=dict(
            xaxis_title="Strike Price",
            yaxis_title="Option Type",
            zaxis_title="IV (%)"
        ),
        height=600
    )

    return fig
