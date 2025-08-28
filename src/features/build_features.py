#!/usr/bin/env python3
"""
Feature Engineering for Power Demand Forecasting.

Builds time series features including lagged variables, rolling statistics,
temporal features, and weather correlations for power demand prediction.
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import mlflow
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def create_lag_features(
    df: pd.DataFrame, 
    target_col: str = "load", 
    lags: List[int] = [1, 2, 3, 6, 12, 24]
) -> pd.DataFrame:
    """
    Create lagged features for time series forecasting.
    
    Args:
        df: DataFrame with time series data
        target_col: Name of target column to create lags for
        lags: List of lag periods (in hours)
        
    Returns:
        DataFrame with added lag features
    """
    print(f"Creating lag features for {target_col} with lags: {lags}")
    
    df_features = df.copy()
    
    for lag in lags:
        lag_col = f"{target_col}_lag_{lag}h"
        df_features[lag_col] = df_features[target_col].shift(lag)
        
    print(f"Added {len(lags)} lag features")
    return df_features


def create_rolling_features(
    df: pd.DataFrame,
    target_col: str = "load",
    windows: List[int] = [3, 6, 12, 24],
    stats: List[str] = ["mean", "std", "min", "max"]
) -> pd.DataFrame:
    """
    Create rolling window statistical features.
    
    Args:
        df: DataFrame with time series data
        target_col: Name of target column to create rolling features for
        windows: List of rolling window sizes (in hours)
        stats: List of statistics to compute
        
    Returns:
        DataFrame with added rolling features
    """
    print(f"Creating rolling features for {target_col} with windows: {windows}")
    
    df_features = df.copy()
    
    for window in windows:
        for stat in stats:
            col_name = f"{target_col}_rolling_{window}h_{stat}"
            
            if stat == "mean":
                df_features[col_name] = df_features[target_col].rolling(window=window).mean()
            elif stat == "std":
                df_features[col_name] = df_features[target_col].rolling(window=window).std()
            elif stat == "min":
                df_features[col_name] = df_features[target_col].rolling(window=window).min()
            elif stat == "max":
                df_features[col_name] = df_features[target_col].rolling(window=window).max()
    
    feature_count = len(windows) * len(stats)
    print(f"Added {feature_count} rolling window features")
    return df_features


def create_temporal_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """
    Create temporal features from timestamp column.
    
    Args:
        df: DataFrame with timestamp column
        timestamp_col: Name of timestamp column
        
    Returns:
        DataFrame with added temporal features
    """
    print("Creating temporal features...")
    
    df_features = df.copy()
    
    # Ensure timestamp is datetime
    df_features[timestamp_col] = pd.to_datetime(df_features[timestamp_col])
    
    # Hour of day (0-23)
    df_features["hour"] = df_features[timestamp_col].dt.hour
    
    # Day of week (0=Monday, 6=Sunday)
    df_features["day_of_week"] = df_features[timestamp_col].dt.dayofweek
    
    # Month (1-12)
    df_features["month"] = df_features[timestamp_col].dt.month
    
    # Day of year (1-365/366)
    df_features["day_of_year"] = df_features[timestamp_col].dt.dayofyear
    
    # Weekend indicator
    df_features["is_weekend"] = (df_features["day_of_week"] >= 5).astype(int)
    
    # Business hours indicator (6 AM - 6 PM on weekdays)
    df_features["is_business_hours"] = (
        (df_features["hour"] >= 6) & 
        (df_features["hour"] <= 18) & 
        (df_features["day_of_week"] < 5)
    ).astype(int)
    
    # Seasonal features using sine/cosine encoding
    df_features["hour_sin"] = np.sin(2 * np.pi * df_features["hour"] / 24)
    df_features["hour_cos"] = np.cos(2 * np.pi * df_features["hour"] / 24)
    
    df_features["day_of_week_sin"] = np.sin(2 * np.pi * df_features["day_of_week"] / 7)
    df_features["day_of_week_cos"] = np.cos(2 * np.pi * df_features["day_of_week"] / 7)
    
    df_features["day_of_year_sin"] = np.sin(2 * np.pi * df_features["day_of_year"] / 365.25)
    df_features["day_of_year_cos"] = np.cos(2 * np.pi * df_features["day_of_year"] / 365.25)
    
    print("Added 13 temporal features")
    return df_features


def create_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create weather-based features and interactions.
    
    Args:
        df: DataFrame with weather columns
        
    Returns:
        DataFrame with added weather features
    """
    print("Creating weather features...")
    
    df_features = df.copy()
    feature_count = 0
    
    # Temperature-based features
    if "temp_c" in df_features.columns:
        # Temperature squared (for non-linear heating/cooling effects)
        df_features["temp_c_squared"] = df_features["temp_c"] ** 2
        
        # Cooling degree days (base 18°C)
        df_features["cooling_degree_days"] = np.maximum(df_features["temp_c"] - 18, 0)
        
        # Heating degree days (base 18°C)
        df_features["heating_degree_days"] = np.maximum(18 - df_features["temp_c"], 0)
        
        feature_count += 3
    
    # Humidity-temperature interaction
    if "temp_c" in df_features.columns and "humidity" in df_features.columns:
        # Heat index approximation
        df_features["temp_humidity_interaction"] = df_features["temp_c"] * df_features["humidity"] / 100
        feature_count += 1
    
    # Wind chill effect (simplified)
    if "temp_c" in df_features.columns and "wind_speed" in df_features.columns:
        df_features["wind_chill_effect"] = df_features["temp_c"] - (df_features["wind_speed"] * 0.5)
        feature_count += 1
    
    print(f"Added {feature_count} weather features")
    return df_features


def create_target_features(
    df: pd.DataFrame, 
    target_col: str = "load", 
    horizon: int = 1
) -> Tuple[pd.DataFrame, str]:
    """
    Create target variable for forecasting.
    
    Args:
        df: DataFrame with target column
        target_col: Name of target column
        horizon: Forecast horizon in hours
        
    Returns:
        Tuple of (DataFrame with target, target column name)
    """
    print(f"Creating target variable for {horizon}-hour forecast horizon")
    
    df_target = df.copy()
    target_name = f"{target_col}_target_{horizon}h"
    
    # Shift target backwards to create future values
    df_target[target_name] = df_target[target_col].shift(-horizon)
    
    print(f"Created target: {target_name}")
    return df_target, target_name


def remove_incomplete_rows(df: pd.DataFrame, required_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Remove rows with missing values in required columns.
    
    Args:
        df: DataFrame to clean
        required_cols: List of required columns. If None, uses all columns
        
    Returns:
        DataFrame with incomplete rows removed
    """
    initial_rows = len(df)
    
    if required_cols is None:
        df_clean = df.dropna()
    else:
        df_clean = df.dropna(subset=required_cols)
    
    final_rows = len(df_clean)
    removed_rows = initial_rows - final_rows
    
    print(f"Removed {removed_rows} incomplete rows ({removed_rows/initial_rows*100:.1f}%)")
    print(f"Final dataset: {final_rows} rows")
    
    return df_clean


def build_features(
    power_data_path: str,
    weather_data_path: str,
    horizon: int = 1,
    lags: List[int] = [1, 2, 3, 6, 12, 24],
    rolling_windows: List[int] = [3, 6, 12, 24],
    output_path: str = "data/features/features.parquet"
) -> Tuple[pd.DataFrame, str]:
    """
    Build complete feature set for power demand forecasting.
    
    Args:
        power_data_path: Path to power demand data
        weather_data_path: Path to weather data
        horizon: Forecast horizon in hours
        lags: List of lag periods for lagged features
        rolling_windows: List of window sizes for rolling features
        output_path: Path to save features
        
    Returns:
        Tuple of (features DataFrame, target column name)
    """
    print("Building features for power demand forecasting...")
    print(f"Forecast horizon: {horizon} hours")
    
    # Load data
    print(f"Loading power data from {power_data_path}")
    power_df = pd.read_parquet(power_data_path)
    
    print(f"Loading weather data from {weather_data_path}")
    weather_df = pd.read_parquet(weather_data_path)
    
    # Merge power and weather data on timestamp
    print("Merging power and weather data...")
    df = pd.merge(power_df, weather_df, on="timestamp", how="inner", suffixes=("_power", "_weather"))
    
    print(f"Merged dataset: {len(df)} rows")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Create features
    df = create_lag_features(df, target_col="load", lags=lags)
    df = create_rolling_features(df, target_col="load", windows=rolling_windows)
    df = create_temporal_features(df, timestamp_col="timestamp")
    df = create_weather_features(df)
    
    # Create target variable
    df, target_col = create_target_features(df, target_col="load", horizon=horizon)
    
    # Remove incomplete rows
    feature_cols = [col for col in df.columns if col not in ["timestamp", "region_power", "region_weather", "data_source_power", "data_source_weather"]]
    df = remove_incomplete_rows(df, required_cols=feature_cols)
    
    # Save features
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    
    print(f"Saved features to {output_path}")
    print(f"Feature columns: {len([col for col in df.columns if col not in ['timestamp', target_col]])}")
    print(f"Target column: {target_col}")
    
    return df, target_col


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(description="Build features for power demand forecasting")
    parser.add_argument("--power-data", default="data/raw/power.parquet", help="Path to power data")
    parser.add_argument("--weather-data", default="data/raw/weather.parquet", help="Path to weather data")
    parser.add_argument("--horizon", type=int, default=1, help="Forecast horizon in hours")
    parser.add_argument("--lags", default="1,2,3,6,12,24", help="Comma-separated lag periods")
    parser.add_argument("--rolling", default="3,6,12,24", help="Comma-separated rolling window sizes")
    parser.add_argument("--output", default="data/features/features.parquet", help="Output path for features")

    args = parser.parse_args()

    # Parse comma-separated lists
    lags = [int(x.strip()) for x in args.lags.split(",")]
    rolling_windows = [int(x.strip()) for x in args.rolling.split(",")]

    # Start MLflow run for tracking
    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"build_features_h{args.horizon}"):

        # Log parameters
        mlflow.log_params({
            "horizon": args.horizon,
            "lags": args.lags,
            "rolling_windows": args.rolling,
            "power_data_path": args.power_data,
            "weather_data_path": args.weather_data,
            "output_path": args.output
        })

        try:
            # Build features
            features_df, target_col = build_features(
                power_data_path=args.power_data,
                weather_data_path=args.weather_data,
                horizon=args.horizon,
                lags=lags,
                rolling_windows=rolling_windows,
                output_path=args.output
            )

            # Log metrics
            mlflow.log_metrics({
                "num_features": len([col for col in features_df.columns if col not in ['timestamp', target_col]]),
                "num_samples": len(features_df),
                "date_range_days": (features_df['timestamp'].max() - features_df['timestamp'].min()).days,
                "missing_values": features_df.isnull().sum().sum()
            })

            # Log feature list as artifact
            feature_cols = [col for col in features_df.columns if col not in ['timestamp', target_col]]
            feature_info = pd.DataFrame({
                'feature_name': feature_cols,
                'feature_type': [
                    'lag' if 'lag' in col else
                    'rolling' if 'rolling' in col else
                    'temporal' if col in ['hour', 'day_of_week', 'month', 'day_of_year', 'is_weekend', 'is_business_hours'] else
                    'temporal_cyclic' if any(x in col for x in ['_sin', '_cos']) else
                    'weather' if any(x in col for x in ['temp', 'humidity', 'wind', 'degree_days']) else
                    'target' if 'target' in col else
                    'other'
                    for col in feature_cols
                ]
            })

            feature_info_path = args.output.replace('.parquet', '_info.csv')
            feature_info.to_csv(feature_info_path, index=False)
            mlflow.log_artifact(feature_info_path)

            print(f"Successfully built features with {len(feature_cols)} features and {len(features_df)} samples")

        except Exception as e:
            print(f"Error during feature building: {e}")
            mlflow.log_param("error", str(e))
            raise


if __name__ == "__main__":
    main()
