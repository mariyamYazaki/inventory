# services/plot_service.py
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

import plotly.express as px
import pandas as pd

def plot_gap_by_plant(df: pd.DataFrame):
    fig = px.bar(
        df,
        x="Plant",
        y="GapPercent",
        text="GapPercent",
        color="GapPercent",
        color_continuous_scale="RdBu",
        title="Deviation % by Plant"
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(
        yaxis_title="Deviation %",
        xaxis_title="Plant",
        uniformtext_minsize=8,
        uniformtext_mode='hide',
        template="simple_white",
        height=450
    )
    return fig

def plot_forecast_vs_prediction(df: pd.DataFrame):
    df_long = df.melt(
        id_vars=['Week'],
        value_vars=['ForecastQty', 'AI_Prediction'],
        var_name='Type',
        value_name='Quantity'
    )
    fig = px.line(df_long, x='Week', y='Quantity', color='Type', markers=True, title="Forecast vs AI Prediction")
    fig.update_layout(xaxis_tickangle=-45)
    return fig

def plot_prediction_distribution(df: pd.DataFrame):
    fig = px.histogram(df, x='AI_Prediction', nbins=30, title="AI Prediction Distribution", marginal="box", color_discrete_sequence=["#2196F3"])
    return fig

def plot_consumption_vs_forecast(df: pd.DataFrame, plant_filter=None, material_filter=None):
    if plant_filter:
        df = df[df['Plant'] == plant_filter]
    if material_filter:
        df = df[df['Material'] == material_filter]

    df = df.sort_values("Week")
    agg_df = df.groupby("Week").agg({
        "ForecastQty": "sum",
        "ConsumptionQty": "sum"
    }).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=agg_df["Week"],
        y=agg_df["ForecastQty"],
        mode="lines+markers",
        name="ForecastQty",
        line=dict(color="royalblue", width=3)
    ))
    fig.add_trace(go.Scatter(
        x=agg_df["Week"],
        y=agg_df["ConsumptionQty"],
        mode="lines+markers",
        name="ConsumptionQty",
        line=dict(color="darkblue", width=3)
    ))
    fig.add_trace(go.Scatter(
        x=agg_df["Week"].tolist() + agg_df["Week"].tolist()[::-1],
        y=agg_df["ForecastQty"].tolist() + agg_df["ConsumptionQty"].tolist()[::-1],
        fill='toself',
        fillcolor='rgba(255, 99, 132, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        name="Gap",
        showlegend=True
    ))

    fig.update_layout(
        title="Forecast vs Consumption (Gap Highlighted)",
        xaxis_title="Week",
        yaxis_title="Quantity",
        template="simple_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig