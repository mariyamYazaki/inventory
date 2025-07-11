# modules/explore_dashboard.py
import re
import streamlit as st
import pandas as pd
import numpy as np
import os
import glob

from services.OEM_project import OEMMapper
from services.forecast_cleaner import clean_yppmpl_file, clean_yppmpl_file_cached
from services.plot_service import plot_gap_by_plant, plot_consumption_vs_forecast
from services.kpi_service import calculate_kpis, get_worst_plants
from services.data_service import merge_forecast_and_consumption_cached, summarize_gap_by_plant, summarize_gap_by_plant_cached

def show_explore_page(forecast_files, consumption_file):
    # === FILE PROCESSING ===
    # If new files uploaded, delete existing parquet to force regeneration
    if forecast_files or consumption_file:
        if os.path.exists("data/merged/forecast_cleaned.parquet"):
            os.remove("data/merged/forecast_cleaned.parquet")
        if os.path.exists("data/merged/consumption_cleaned.parquet"):
            os.remove("data/merged/consumption_cleaned.parquet")

    if forecast_files:
        for file in forecast_files:
            with open(os.path.join("data/raw/forecast", file.name), "wb") as f:
                f.write(file.getbuffer())

    if consumption_file:
        with open(os.path.join("data/raw/consumption", consumption_file.name), "wb") as f:
            f.write(file.getbuffer())

    with st.spinner("Loading and cleaning forecast and consumption files..."):
        forecast_long, mcsk_df = load_all_raw_data()

    if forecast_long is not None and mcsk_df is not None:
        with st.spinner("Merging forecast and consumption data..."):
            merged_df = merge_forecast_and_consumption_cached(forecast_long, mcsk_df)
            merged_df = clean_dataframe(merged_df)

            # Fix mixed types: force all object columns to str
            for col in merged_df.select_dtypes(include=['object']).columns:
                merged_df[col] = merged_df[col].astype(str)

            merged_df.to_csv("data/merged/latest.csv", index=False)
            merged_df.to_parquet("data/merged/latest.parquet", index=False)


    # === DISPLAY ===
    try:
        merged_df = pd.read_parquet("data/merged/latest.parquet")
    except FileNotFoundError:
        try:
            merged_df = pd.read_csv("data/merged/latest.csv")
        except FileNotFoundError:
            st.warning("No merged data available. Please upload forecast and consumption files.")
            return

    # Add week filter at the top of the main page
    from collections import defaultdict

    st.markdown("## 🗓️ Week Filter")

    # Group available weeks by year for better UX
    week_groups = defaultdict(list)
    for week in sorted(merged_df["Week"].unique(), key=lambda x: (int(x.split('W')[1].split('-')[0]), int(x.split('-')[1]))):
        week_num, year = week.split('-')
        week_groups[year].append(f"{week_num}-{year}")

    # Choose year
    with st.expander("🔽 Filter by Week", expanded=True):
        selected_year = st.selectbox("📅 Select Year", sorted(week_groups.keys()), index=len(week_groups)-1)
        available_weeks = week_groups[selected_year]
        
        selected_weeks = st.multiselect(
            "🗓️ Select One or More Weeks",
            options=["All Weeks"] + available_weeks,
            default="All Weeks",
            key="week_filter_multi"
        )

    # Filter DataFrame based on week(s)
    if "All Weeks" in selected_weeks or not selected_weeks:
        filtered_df = merged_df.copy()
    else:
        formatted_weeks = [f"W{w}" for w in selected_weeks]
        filtered_df = merged_df[merged_df["Week"].isin(formatted_weeks)]

    st.markdown("## 🧮 Key Performance Indicators")
    st.markdown("---")

    # Use filtered_df instead of merged_df for all calculations
    total_gap, abs_total_gap, average_deviation_percent = calculate_kpis(filtered_df)
    plant_over, plant_under = get_worst_plants(filtered_df)

    # 💶 Total Value if available
    try:
        filtered_df["Tot.us.val"] = pd.to_numeric(filtered_df["Tot.us.val"], errors="coerce")
        total_value_eur = filtered_df["Tot.us.val"].sum()
    except Exception:
        total_value_eur = None

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        label="📉 Total Gap (Qty)",
        value=f"{abs_total_gap/1e6:,.2f} M",
        delta=f"{'-' if total_gap < 0 else '+'}{abs(total_gap)/1e6:,.2f} M",
        help="Sum of differences between forecast and actual consumption in quantity."
    )

    col2.metric(
        label="📊 Avg Deviation %",
        value=f"{average_deviation_percent:.2f}%",
        delta="High" if average_deviation_percent > 50 else "Low",
        help="Average % deviation across all forecasted entries."
    )

    col3.markdown(f"""
        <div class='kpi-box'>
            <div style='font-weight:bold; font-size:16px;'>🏭 Over/Under Forecast</div>
            <div style='font-size:22px; padding-top:5px;'>⬆️ <b>{plant_over}</b> / ⬇️ <b>{plant_under}</b></div>
        </div>
    """, unsafe_allow_html=True)

    if total_value_eur is not None:
        col4.metric(
            label="💶 Total Consumption Value",
            value=f"{total_value_eur/1e6:,.2f} M EUR",
            help="Total monetary value of consumption."
        )

    st.subheader("📉 Deviation % by Plant")
    gap_df = summarize_gap_by_plant_cached(filtered_df)
    gap_df = gap_df.rename(columns={"RealQty": "ConsumptionQty"})
    gap_df["GapPercent"] = ((gap_df["ForecastQty"] - gap_df["ConsumptionQty"]) / gap_df["ForecastQty"])
    gap_df["GapPercent"] = gap_df["GapPercent"].round(2)

    # Format to Millions and add EUR column
    gap_df["ForecastQty (M)"] = (gap_df["ForecastQty"] / 1e6).round(2)
    gap_df["ConsumptionQty (M)"] = (gap_df["ConsumptionQty"] / 1e6).round(2)

    if "Tot.us.val" in filtered_df.columns:
        money_by_plant = filtered_df.groupby("Plant")["Tot.us.val"].sum().reset_index()
        money_by_plant.rename(columns={"Tot.us.val": "Consumption Value (M EUR)"}, inplace=True)
        money_by_plant["Consumption Value (M EUR)"] = (money_by_plant["Consumption Value (M EUR)"] / 1e6).round(2)
        gap_df = gap_df.merge(money_by_plant, on="Plant", how="left")

    # Reorder for clarity
    display_cols = ["Plant", "ForecastQty (M)", "ConsumptionQty (M)", "GapPercent"]
    if "Consumption Value (M EUR)" in gap_df.columns:
        display_cols.append("Consumption Value (M EUR)")

    st.dataframe(gap_df[display_cols], use_container_width=True)
    st.plotly_chart(plot_gap_by_plant(gap_df), use_container_width=True)

    st.subheader("🔍 Forecast vs Consumption")
    with st.expander("Filter Options"):
        plant_options = np.append(["All"], sorted(filtered_df["Plant"].unique()))
        material_options = np.append(["All"], sorted(filtered_df["Material"].unique()))
        selected_plant = st.selectbox("Select Plant", plant_options)
        selected_material = st.selectbox("Select Material", material_options)

    plant_filter = None if selected_plant == "All" else selected_plant
    material_filter = None if selected_material == "All" else selected_material
    st.plotly_chart(plot_consumption_vs_forecast(filtered_df, plant_filter, material_filter), use_container_width=True)

        # Add vertical spacer to push button to bottom visually
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)

    # Centered, styled button using st.button inside a centered container
   
    col1, col2, col3 = st.columns([3, 1, 3])
    with col2:
        if st.button("Open Power BI Report"):
            os.startfile(r"power_bi\streamlit.pbix")
            st.success("✅ Power BI Desktop is opening...")

    # Optional: add a subtle footer text below the button
    st.markdown(
        "<p style='text-align:center; font-size:0.9em; color:gray;'>"
        "© 2025 YAZAKI - Inventory Forecast App</p>",
        unsafe_allow_html=True
    )

# === HELPER FUNCTIONS ===

def convert_week_format(w):
    if isinstance(w, str) and "." in w:
        parts = w.split(".")
        return f"W{parts[0].zfill(2)}-{parts[1][-2:]}"
    return str(w)

def safe_read_file(uploaded_file):
    try:
        return pd.read_excel(uploaded_file, engine='openpyxl')
    except:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file)

def clean_dataframe(df):
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.fillna(0)

def load_all_raw_data():
    forecast_parquet = "data/merged/forecast_cleaned.parquet"
    consumption_parquet = "data/merged/consumption_cleaned.parquet"

    # === Forecast Data ===
    if os.path.exists(forecast_parquet):
        forecast_long = pd.read_parquet(forecast_parquet)
    else:
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
            cleaned_df = clean_yppmpl_file_cached(raw_df, week_str, current_week, current_year)
            all_forecast_dfs.append(cleaned_df)

        if not all_forecast_dfs:
            return None, None

        forecast_long = pd.concat(all_forecast_dfs, ignore_index=True)
        forecast_long["ForecastQty"] = pd.to_numeric(forecast_long["ForecastQty"], errors="coerce")
        forecast_long = forecast_long.dropna(subset=["ForecastQty"])

        forecast_long.to_parquet(forecast_parquet, index=False)

    # === Consumption Data ===
    if os.path.exists(consumption_parquet):
        mcsk_df = pd.read_parquet(consumption_parquet)
    else:
        consumption_paths = glob.glob("data/raw/consumption/*.xlsx")
        if not consumption_paths:
            return forecast_long, None
        cons_file = consumption_paths[0]
        with open(cons_file, 'rb') as f:
            mcsk_df = safe_read_file(f)
        usage_cols = ["ConsumptionQty", "RealQty", "Tot_usage", "Tot. usage", "Usage", "Real Usage"]
        real_qty_col = next((col for col in mcsk_df.columns if col in usage_cols), None)
        if not real_qty_col:
            return forecast_long, None

        mcsk_df = mcsk_df.rename(columns={real_qty_col: "ConsumptionQty"})
        columns_to_keep = ["Material", "Plant", "Week", "ConsumptionQty", "Tot.us.val"]
        mcsk_df = mcsk_df[[col for col in columns_to_keep if col in mcsk_df.columns]]
        mcsk_df["Week"] = mcsk_df["Week"].astype(str).apply(convert_week_format)
        mcsk_df["Material"] = mcsk_df["Material"].astype(str).str.strip()
        mcsk_df["Plant"] = mcsk_df["Plant"].astype(str).str.strip()

        # Ensure numeric columns are numeric
        mcsk_df["ConsumptionQty"] = pd.to_numeric(mcsk_df["ConsumptionQty"], errors="coerce")
        if "Tot.us.val" in mcsk_df.columns:
            mcsk_df["Tot.us.val"] = pd.to_numeric(mcsk_df["Tot.us.val"], errors="coerce")

        mcsk_df.to_parquet(consumption_parquet, index=False)

    return forecast_long, mcsk_df
