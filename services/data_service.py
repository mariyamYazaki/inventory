import pandas as pd
import numpy as np
import streamlit as st

@st.cache_data
def summarize_gap_by_plant_cached(df):
    return summarize_gap_by_plant(df)

def load_latest_merged_data(path="data/merged/latest.csv"):
    try:
        df = pd.read_csv(path)
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
        return df
    except FileNotFoundError:
        return None

def merge_forecast_and_consumption(forecast_df: pd.DataFrame, consumption_df: pd.DataFrame) -> pd.DataFrame:
    """Merge forecast and consumption data on Material, Plant, and Week."""
    merged_df = pd.merge(
        forecast_df,
        consumption_df,
        on=["Material", "Plant", "Week"],
        how="inner"
    )
    
    # ✅ Force numeric columns before doing arithmetic
    merged_df["ForecastQty"] = pd.to_numeric(merged_df["ForecastQty"], errors="coerce").fillna(0)
    merged_df["ConsumptionQty"] = pd.to_numeric(merged_df["ConsumptionQty"], errors="coerce").fillna(0)

    merged_df["Deviation"] = merged_df["ConsumptionQty"] - merged_df["ForecastQty"]
    merged_df["DeviationPercent"] = (
        merged_df["Deviation"] / merged_df["ForecastQty"].replace(0, np.nan)
    ) * 100
    merged_df["DeviationPercent"] = merged_df["DeviationPercent"].fillna(0)

    return merged_df


@st.cache_data
def merge_forecast_and_consumption_cached(forecast_df, consumption_df):
    return merge_forecast_and_consumption(forecast_df, consumption_df)

def summarize_gap_by_plant(df: pd.DataFrame) -> pd.DataFrame:
    """Group by Plant and calculate forecast gap % correctly."""
    if df.empty:
        return pd.DataFrame(columns=["Plant", "ForecastQty", "ConsumptionQty", "GapPercent"])

    grouped = df.groupby("Plant").agg(
        ForecastQty=pd.NamedAgg(column="ForecastQty", aggfunc="sum"),
        ConsumptionQty=pd.NamedAgg(column="ConsumptionQty", aggfunc="sum")
    ).reset_index()

    grouped["GapPercent"] = ((grouped["ForecastQty"] - grouped["ConsumptionQty"]) / grouped["ForecastQty"]) 
    grouped["GapPercent"] = grouped["GapPercent"].round(2)

    return grouped[["Plant", "ForecastQty", "ConsumptionQty", "GapPercent"]]
