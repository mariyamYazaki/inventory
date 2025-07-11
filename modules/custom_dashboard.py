import streamlit as st
import pandas as pd
import os
import re
import numpy as np

from services.OEM_project import OEMMapper

from services.forecast_cleaner import clean_yppmpl_file,clean_yppmpl_file_cached
from services.data_service import merge_forecast_and_consumption, summarize_gap_by_plant
from services.plot_service import plot_gap_by_plant, plot_consumption_vs_forecast
from services.kpi_service import calculate_kpis, get_worst_plants

def show_custom_dashboard_page():
    st.header("🧪 Custom Dashboard")
    load_custom_dashboard_data()

    if os.path.exists("data/custom/merged/latest.csv"):
        custom_df = pd.read_csv("data/custom/merged/latest.csv")

        st.subheader("📊 Custom KPIs")
        total_gap, abs_total_gap, average_deviation_percent = calculate_kpis(custom_df)
        plant_over, plant_under = get_worst_plants(custom_df)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Gap", f"{abs_total_gap:,}", delta=f"{'+' if total_gap >= 0 else '-'}{abs(total_gap):,}")
        col2.metric("Avg Deviation %", f"{average_deviation_percent:.2f}%", delta="High" if average_deviation_percent > 50 else "Low")
        col3.metric("Over/Under Forecast", f"⬆️ {plant_over} / ⬇️ {plant_under}")

        st.subheader("📉 Custom Deviation % by Plant")
        gap_df = summarize_gap_by_plant(custom_df)
        gap_df = gap_df.rename(columns={"RealQty": "ConsumptionQty"})
        gap_df["GapPercent"] = ((gap_df["ForecastQty"] - gap_df["ConsumptionQty"]) / gap_df["ForecastQty"]) * 100
        gap_df["GapPercent"] = gap_df["GapPercent"].round(2)
        st.dataframe(gap_df, use_container_width=True)
        st.plotly_chart(plot_gap_by_plant(gap_df), use_container_width=True)

        st.subheader("🔍 Custom Forecast vs Consumption")
        with st.expander("Filter Options"):
            plant_options = np.append(["All"], sorted(custom_df["Plant"].unique()))
            material_options = np.append(["All"], sorted(custom_df["Material"].unique()))
            selected_plant = st.selectbox("Select Plant", plant_options, key="custom_plant")
            selected_material = st.selectbox("Select Material", material_options, key="custom_material")

        plant_filter = None if selected_plant == "All" else selected_plant
        material_filter = None if selected_material == "All" else selected_material
        st.plotly_chart(plot_consumption_vs_forecast(custom_df, plant_filter, material_filter), use_container_width=True)

def load_custom_dashboard_data():
    custom_forecast = st.file_uploader("📊 Upload Forecast File(s)", type=None, accept_multiple_files=True, key="custom_forecast")
    custom_consumption = st.file_uploader("📈 Upload Consumption File", type=None, key="custom_consumption")

    if custom_forecast and custom_consumption:
        all_forecast_dfs = []
        for forecast_file in custom_forecast:
            raw_df = safe_read_file(forecast_file)
            forecast_path = os.path.join("data/custom/raw/forecast", forecast_file.name)
            with open(forecast_path, "wb") as f:
                f.write(forecast_file.getbuffer())

            match = re.search(r"W(\d{2})-(\d{2})", forecast_file.name)
            if not match:
                st.warning(f"⚠️ Could not extract week from {forecast_file.name}")
                continue
            current_week = int(match.group(1))
            current_year = 2000 + int(match.group(2))
            week_str = match.group(0)
            cleaned_df = clean_yppmpl_file_cached(raw_df, week_str, current_week, current_year)
            all_forecast_dfs.append(cleaned_df)

        forecast_df = pd.concat(all_forecast_dfs, ignore_index=True)
        forecast_df["ForecastQty"] = pd.to_numeric(forecast_df["ForecastQty"], errors="coerce")
        forecast_df = forecast_df.dropna(subset=["ForecastQty"])

        cons_path = os.path.join("data/custom/raw/consumption", custom_consumption.name)
        with open(cons_path, "wb") as f:
            f.write(custom_consumption.getbuffer())

        consumption_df = safe_read_file(custom_consumption)
        usage_cols = ["ConsumptionQty", "RealQty", "Tot_usage", "Tot. usage", "Usage", "Real Usage"]
        real_qty_col = next((col for col in consumption_df.columns if col in usage_cols), None)
        if not real_qty_col:
            st.error("❌ 'ConsumptionQty' column not found.")
            return None

        consumption_df = consumption_df.rename(columns={real_qty_col: "ConsumptionQty"})
        consumption_df = consumption_df[["Material", "Plant", "Week", "ConsumptionQty"]]
        consumption_df["Week"] = consumption_df["Week"].astype(str).apply(convert_week_format)
        consumption_df["Material"] = consumption_df["Material"].astype(str).str.strip()
        consumption_df["Plant"] = consumption_df["Plant"].astype(str).str.strip()

        merged_df = merge_forecast_and_consumption(forecast_df, consumption_df)
        merged_df = clean_dataframe(merged_df)
        merged_df.to_csv("data/custom/merged/latest.csv", index=False)
        st.success("✅ Custom data processed.")

def safe_read_file(uploaded_file):
    try:
        return pd.read_excel(uploaded_file, engine='openpyxl')
    except:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file)

def clean_dataframe(df):
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.fillna(0)

def convert_week_format(w):
    if isinstance(w, str) and "." in w:
        parts = w.split(".")
        return f"W{parts[0].zfill(2)}-{parts[1][-2:]}"
    return str(w)