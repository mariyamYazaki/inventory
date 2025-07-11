import pandas as pd

def create_features(df):
    """
    Create time-series features for forecasting.
    Includes week parsing, date indexing, lag and rolling mean features.
    """
    # Extract Week number and Year from Week format "W01-2023"
    week_year = df['Week'].str.extract(r'W(\d{2})-(\d{4})')  # Extract week and full year
    df['Week_num'] = week_year[0].astype(int)
    df['Year'] = week_year[1]

    # Create datetime index from week number (ISO calendar)
    df['Time_index'] = pd.to_datetime(
        df['Year'] + '-W' + df['Week_num'].astype(str).str.zfill(2) + '-1',
        format='%G-W%V-%u'
    )

    # Extract additional temporal features
    df['Month'] = df['Time_index'].dt.month
    df['Quarter'] = df['Time_index'].dt.quarter

    # Sort for lag calculation
    df = df.sort_values(by=['Material', 'Plant', 'Time_index'])

    # Lag features (1-week lag + rolling average over last 4 weeks)
    df['ConsumptionQty_lag1'] = df.groupby(['Material', 'Plant'])['ConsumptionQty'].shift(1)
    df['ConsumptionQty_rolling4'] = (
        df.groupby(['Material', 'Plant'])['ConsumptionQty']
        .rolling(4, min_periods=1)
        .mean()
        .reset_index(level=[0, 1], drop=True)
    )
    # Remove any rows with missing values (typically caused by lagging)
    return df.dropna()