import streamlit as st
import pandas as pd
import numpy as np
import os
import joblib
import glob
import re
from io import BytesIO

from services.forecast_cleaner import clean_yppmpl_file
from services.plot_service import plot_consumption_vs_forecast



MODEL_PATH = "inventory_ai_api/model/inventory_model.pkl"

def show_ai_predictions_page(forecast_files, consumption_file):
    st.title("📦 AI Future Consumption Forecast (Supply Chain)")

    model = load_model()
    if model is None:
        st.error("❌ AI model file not found. Please make sure the model is properly trained and deployed.")
        return

    handle_file_upload(forecast_files)
    forecast_long = load_and_clean_forecast_data()

    if forecast_long is None:
        st.warning("Please upload valid forecast files to proceed.")
        return

    forecast_long = clean_dataframe(forecast_long)
    forecast_long.to_csv("data/merged/latest_forecast_only.csv", index=False)

    feature_cols = ['ForecastQty', 'WIP', 'Stock', 'MRP BACKLOG', 
                    'Price from Info Record', 'Price unit', 'Safety Stock']

    for col in feature_cols:
        if col not in forecast_long.columns:
            forecast_long[col] = 0

    X = forecast_long[feature_cols]
    X = X.rename(columns={"ForecastQty": "Total_MRP"})

    forecast_long['Predicted_ConsumptionQty'] = model.predict(X)
    forecast_long['Predicted_Gap'] = forecast_long['ForecastQty'] - forecast_long['Predicted_ConsumptionQty']
    forecast_long['Predicted_GapPercent'] = np.where(
        forecast_long['ForecastQty'] != 0,
        (forecast_long['Predicted_Gap'] / forecast_long['ForecastQty']) * 100,
        0
    )

    forecast_long['Risk Explanation'] = forecast_long.apply(generate_risk_explanation, axis=1)

    display_forecast_horizon(forecast_long)
    display_kpis(forecast_long)
    display_filters_and_table(forecast_long)
    display_prediction_chart(forecast_long)
    display_weekly_risk_summary(forecast_long)
    export_prediction_data(forecast_long)

@st.cache_resource
def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


def handle_file_upload(forecast_files):
    if forecast_files:
        for file in forecast_files:
            with open(os.path.join("data/raw/forecast", file.name), "wb") as f:
                f.write(file.getbuffer())

def display_forecast_horizon(df):
    st.header("📅 Forecast Horizon Summary")
    weeks = sorted(df['Week'].unique())
    st.success(f"Forecast file covers {len(weeks)} weeks: {', '.join(weeks)}")

def display_kpis(df):

    total_predicted_consumption = df['Predicted_ConsumptionQty'].sum()
    total_forecast = df['ForecastQty'].sum()
    total_gap = df['Predicted_Gap'].sum()
    avg_gap_percent = df['Predicted_GapPercent'].mean()

    col1, col2, col3 = st.columns(3)

    col1.metric("📦 Total Forecast Qty", f"{total_forecast/1e6:.2f} M")
    col2.metric("🔮 Predicted Consumption Qty", f"{total_predicted_consumption/1e6:.2f} M")
    col3.metric("📉 Avg Predicted Gap %", f"{avg_gap_percent:.2f}%")

def display_filters_and_table(df):
    st.header("📊 Forecast Prediction Table")
    plants = ["All"] + sorted(df["Plant"].unique())
    materials = ["All"] + sorted(df["Material"].unique())

    selected_plant = st.selectbox("Select Plant", plants)
    selected_material = st.selectbox("Select Material", materials)

    filtered_df = df.copy()
    if selected_plant != "All":
        filtered_df = filtered_df[filtered_df["Plant"] == selected_plant]
    if selected_material != "All":
        filtered_df = filtered_df[filtered_df["Material"] == selected_material]

    display_cols = ['Material', 'Plant', 'Week', 'ForecastQty', 'Predicted_ConsumptionQty', 'Predicted_Gap', 'Predicted_GapPercent', 'Risk Explanation']
    df_display = filtered_df[display_cols].copy()
    df_display.rename(columns={
        'ForecastQty': 'Forecast Qty',
        'Predicted_ConsumptionQty': 'Predicted Consumption Qty',
        'Predicted_Gap': 'Predicted Gap',
        'Predicted_GapPercent': 'Predicted Gap %'
    }, inplace=True)

    df_display['Forecast Qty'] = (df_display['Forecast Qty'] / 1e3).round(2)
    df_display['Predicted Consumption Qty'] = (df_display['Predicted Consumption Qty'] / 1e3).round(2)
    df_display['Predicted Gap'] = (df_display['Predicted Gap'] / 1e3).round(2)
    df_display['Predicted Gap %'] = df_display['Predicted Gap %'].round(2)

    if len(df_display) <= 500:
        def highlight_risk(val):
            if val >= 50:
                return 'background-color: #ff9999'  # red
            elif val <= -50:
                return 'background-color: #ffd699'  # orange
            else:
                return ''
        styled_df = df_display.style.applymap(highlight_risk, subset=['Predicted Gap %'])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("Large dataset detected — disabling row coloring for performance.")
        st.dataframe(df_display, use_container_width=True)

def display_prediction_chart(df):
    st.header("📈 Forecast vs Predicted Consumption Trend")

    # Build compatible dataframe for plot
    plot_df = df.groupby("Week").agg({
        "ForecastQty": "sum",
        "Predicted_ConsumptionQty": "sum"
    }).reset_index()

    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df["Week"], y=plot_df["ForecastQty"], mode='lines+markers', name='ForecastQty'))
    fig.add_trace(go.Scatter(x=plot_df["Week"], y=plot_df["Predicted_ConsumptionQty"], mode='lines+markers', name='PredictedConsumption'))

    fig.update_layout(title="Forecast vs Predicted Consumption (Weekly)", xaxis_title="Week", yaxis_title="Quantity")
    st.plotly_chart(fig, use_container_width=True)


def display_weekly_risk_summary(df):
    st.header("🚩 Weekly Risk Summary")
    summary = df.groupby("Week").agg(
        Total_Materials=("Material", "count"),
        High_Risk=("Predicted_GapPercent", lambda x: (abs(x) >= 50).sum()),
        Avg_Gap_Percent=("Predicted_GapPercent", "mean")
    ).reset_index()
    summary['High Risk %'] = (summary['High_Risk'] / summary['Total_Materials'] * 100).round(2)

    st.dataframe(summary, use_container_width=True)

def export_prediction_data(df):
    export_cols = ['Material', 'Plant', 'Week', 'ForecastQty', 'Predicted_ConsumptionQty', 'Predicted_Gap', 'Predicted_GapPercent', 'Risk Explanation']
    export_df = df[export_cols].copy()

    output = BytesIO()
    export_df.to_excel(output, index=False, engine='openpyxl')
    st.download_button(
        label="📥 Download Prediction Results",
        data=output.getvalue(),
        file_name="forecast_predictions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@st.cache_data
def load_and_clean_forecast_data():
    all_forecast_dfs = []
    for forecast_path in glob.glob("data/raw/forecast/*.xlsx"):
        with open(forecast_path, 'rb') as f:
            raw_df = safe_read_file(f)
        match = re.search(r"W(\d{2})-(\d{2})", os.path.basename(forecast_path))
        if not match:
            continue
        current_week = int(match.group(1))
        current_year = 2000 + int(match.group(2))
        week_str = match.group(0)
        cleaned_df = clean_yppmpl_file(raw_df, week_str, current_week, current_year)
        all_forecast_dfs.append(cleaned_df)

    if not all_forecast_dfs:
        return None

    forecast_long = pd.concat(all_forecast_dfs, ignore_index=True)
    forecast_long['ForecastQty'] = pd.to_numeric(forecast_long['ForecastQty'], errors='coerce')
    forecast_long = forecast_long.dropna(subset=['ForecastQty'])

    return forecast_long

def safe_read_file(uploaded_file):
    try:
        return pd.read_excel(uploaded_file, engine='openpyxl')
    except:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file)

def clean_dataframe(df):
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.fillna(0)

def generate_risk_explanation(row):
    if abs(row.get('Predicted_GapPercent', 0)) < 50:
        return "Low risk"
    if row.get('MRP BACKLOG', 0) > 10000:
        return "High backlog — supplier delays likely"
    if row.get('WIP', 0) < 500 and row.get('Stock', 0) < 500:
        return "Low WIP & Stock — supply shortage risk"
    if row.get('Safety Stock', 0) > 5000 and row.get('Predicted_ConsumptionQty', 0) < (0.5 * row.get('ForecastQty', 1)):
        return "Over-forecasting with high safety stock"
    return "Forecast deviation — needs investigation"
