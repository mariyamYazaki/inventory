# services/forecast_cleaner.py
import pandas as pd
import numpy as np
import re
import streamlit as st

@st.cache_data
def clean_yppmpl_file_cached(df, week_str, current_week, current_year):
    return clean_yppmpl_file(df, week_str, current_week, current_year)


def clean_yppmpl_file(df: pd.DataFrame, week_str: str, current_week: int, current_year: int) -> pd.DataFrame:
    df = df[df['Material'].notna() & df['Material'].astype(str).str.strip().ne('')]
    po_sl_cols = [col for col in df.columns if str(col).strip().upper().startswith("PO/SL")]
    df.drop(columns=po_sl_cols, inplace=True)

    mrp_cols_to_sum = []
    all_mrp_cols = []

    for col in df.columns:
        col_str = str(col).strip()
        if col_str.startswith("MRP"):
            all_mrp_cols.append(col)
            if col_str in ["MRP BACKLOG", "MRP"]:
                mrp_cols_to_sum.append(col)
            elif "." in col_str:
                match = re.search(r"(\d{2})\.(\d{4})", col_str)
                if match:
                    col_week = int(match.group(1))
                    col_year = int(match.group(2))
                    if (col_year < current_year) or (col_year == current_year and col_week <= current_week):
                        mrp_cols_to_sum.append(col)

    df["ForecastQty"] = df[mrp_cols_to_sum].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)

    # Columns to preserve explicitly
    keep_features = [
        "WIP", "Stock", "MRP BACKLOG",
        "Price from Info Record", "Price unit",
        "Currency from Info Record", "Safety Stock"
    ]
    preserved_cols = [col for col in keep_features if col in df.columns]

    drop_mrp = [col for col in all_mrp_cols if col not in preserved_cols]
    df.drop(columns=drop_mrp, inplace=True)

    df["Week"] = week_str
    df["Material"] = df["Material"].astype(str).str.strip()
    df["Plant"] = df["Plant"].astype(str).str.strip()

    # Required columns
    columns_to_keep = ["Material", "Plant", "Week", "ForecastQty"] + preserved_cols
    if "Vendor" in df.columns:
        columns_to_keep.insert(2, "Vendor")

    return df[columns_to_keep]
