# services/file_utils.py
import pandas as pd
import numpy as np

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