# services/api_client.py
import requests
import pandas as pd
import numpy as np
import streamlit as st


API_URL = "http://127.0.0.1:5000/predict"

def prepare_records(df: pd.DataFrame) -> list:
    api_data = df.fillna(0)
    records = api_data.to_dict(orient="records")
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, (np.integer, np.int32, np.int64)):
                rec[k] = int(v)
            elif isinstance(v, (np.floating, np.float32, np.float64)):
                rec[k] = float(v)
    return records

def call_prediction_api(df: pd.DataFrame) -> pd.DataFrame:
    records = prepare_records(df)
    response = requests.post(API_URL, json=records, timeout=30)

    if response.status_code == 200:
        return pd.DataFrame(response.json())
    else:
        raise Exception(f"API {response.status_code}: {response.text}")