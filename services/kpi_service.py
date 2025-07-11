# services/kpi_service.py
import pandas as pd


def calculate_kpis(df: pd.DataFrame):
    total_gap = (df['ForecastQty'] - df['ConsumptionQty']).sum()
    abs_total_gap = abs(total_gap)

    total_forecast = df['ForecastQty'].sum()
    if total_forecast == 0:
        average_deviation_percent = 0
    else:
        average_deviation_percent = (df['ForecastQty'] - df['ConsumptionQty']).abs().sum() / total_forecast * 100
        average_deviation_percent = round(average_deviation_percent, 2)

    return total_gap, abs_total_gap, average_deviation_percent


def get_worst_plants(df: pd.DataFrame):
    plant_deviation = df.groupby("Plant")["Deviation"].mean()
    plant_over = plant_deviation.idxmax()
    plant_under = plant_deviation.idxmin()
    return plant_over, plant_under