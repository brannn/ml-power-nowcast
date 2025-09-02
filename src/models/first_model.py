#!/usr/bin/env python3
"""
Your First ML Model for Power Demand Prediction

This script creates a simple but effective model to predict California power demand
using weather data. Perfect for learning ML fundamentals!

We'll start with Linear Regression - it's simple, fast, and interpretable.
"""

import pandas as pd
import numpy as np
import boto3
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

def load_data_from_s3(bucket_name: str):
    """Load our collected power and weather data from S3."""
    print("📥 Loading data from S3...")
    
    s3_client = boto3.client('s3')
    
    # Download power data
    print("   Loading CAISO power data...")
    s3_client.download_file(bucket_name, 'raw/power/caiso/real_365d.parquet', 'temp_power.parquet')
    power_df = pd.read_parquet('temp_power.parquet')
    
    # Download weather data  
    print("   Loading CAISO weather data...")
    s3_client.download_file(bucket_name, 'raw/weather/caiso_zones/real_1y.parquet', 'temp_weather.parquet')
    weather_df = pd.read_parquet('temp_weather.parquet')
    
    print(f"✅ Loaded {len(power_df):,} power records and {len(weather_df):,} weather records")
    return power_df, weather_df

def explore_data(power_df, weather_df):
    """Quick data exploration to understand what we're working with."""
    print("\n🔍 DATA EXPLORATION")
    print("="*50)
    
    # Power data overview
    print("📊 Power Data:")
    print(f"   Date range: {power_df['timestamp'].min()} to {power_df['timestamp'].max()}")
    print(f"   Zones available: {power_df['zone'].unique()}")
    
    # Focus on system-wide data for first model
    system_power = power_df[power_df['zone'] == 'SYSTEM'].copy()
    print(f"   System-wide records: {len(system_power):,}")
    print(f"   Load range: {system_power['load'].min():.0f} - {system_power['load'].max():.0f} MW")
    print(f"   Average load: {system_power['load'].mean():.0f} MW")
    
    # Weather data overview
    print(f"\n🌤️  Weather Data:")
    print(f"   Date range: {weather_df['timestamp'].min()} to {weather_df['timestamp'].max()}")
    print(f"   Temperature range: {weather_df['temp_c'].min():.1f} - {weather_df['temp_c'].max():.1f}°C")
    print(f"   Average temperature: {weather_df['temp_c'].mean():.1f}°C")
    
    return system_power

def prepare_features(power_df, weather_df):
    """Prepare features for our ML model."""
    print("\n🔧 FEATURE ENGINEERING")
    print("="*50)
    
    # Focus on system-wide power demand for simplicity
    system_power = power_df[power_df['zone'] == 'SYSTEM'].copy()
    
    # Convert timestamps to datetime and handle timezone issues
    system_power['timestamp'] = pd.to_datetime(system_power['timestamp'])
    weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])

    # Make sure both timestamps are timezone-naive for merging
    if system_power['timestamp'].dt.tz is not None:
        system_power['timestamp'] = system_power['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
    if weather_df['timestamp'].dt.tz is not None:
        weather_df['timestamp'] = weather_df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)

    # Merge power and weather data on timestamp
    # Weather is hourly, power is 5-minute, so we'll resample power to hourly
    print("   Resampling power data to hourly (to match weather)...")
    system_power_hourly = system_power.set_index('timestamp').resample('H')['load'].mean().reset_index()

    print("   Merging power and weather data...")
    merged_df = pd.merge(system_power_hourly, weather_df, on='timestamp', how='inner')
    
    print(f"   Merged dataset: {len(merged_df):,} records")
    
    # Create time-based features
    print("   Creating time-based features...")
    merged_df['hour'] = merged_df['timestamp'].dt.hour
    merged_df['day_of_week'] = merged_df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
    merged_df['month'] = merged_df['timestamp'].dt.month
    merged_df['is_weekend'] = (merged_df['day_of_week'] >= 5).astype(int)
    
    # Create weather-based features
    print("   Creating weather-based features...")
    merged_df['temp_squared'] = merged_df['temp_c'] ** 2  # Capture non-linear temperature effects
    merged_df['temp_humidity_interaction'] = merged_df['temp_c'] * merged_df['humidity']
    
    # Create cooling/heating degree days (base temperature 18°C)
    base_temp = 18.0
    merged_df['cooling_degree_hours'] = np.maximum(merged_df['temp_c'] - base_temp, 0)
    merged_df['heating_degree_hours'] = np.maximum(base_temp - merged_df['temp_c'], 0)
    
    # Clean the data - remove any rows with missing values
    print("   Cleaning data (removing missing values)...")
    initial_rows = len(merged_df)
    merged_df = merged_df.dropna()
    final_rows = len(merged_df)

    if initial_rows != final_rows:
        print(f"   Removed {initial_rows - final_rows} rows with missing values")

    print(f"✅ Feature engineering complete! Dataset shape: {merged_df.shape}")
    return merged_df

def build_and_train_model(df):
    """Build and train our first ML model."""
    print("\n🤖 BUILDING YOUR FIRST ML MODEL")
    print("="*50)
    
    # Define features (inputs) and target (what we want to predict)
    feature_columns = [
        'temp_c', 'temp_squared', 'humidity', 'wind_speed',
        'hour', 'day_of_week', 'month', 'is_weekend',
        'cooling_degree_hours', 'heating_degree_hours',
        'temp_humidity_interaction'
    ]
    
    X = df[feature_columns].copy()
    y = df['load'].copy()  # Target: power demand in MW
    
    print(f"   Features: {feature_columns}")
    print(f"   Target: power demand (load)")
    print(f"   Training data shape: {X.shape}")
    
    # Split data into training and testing sets (80% train, 20% test)
    # Use temporal split - train on earlier data, test on recent data
    split_date = '2025-06-01'
    train_mask = df['timestamp'] < split_date
    
    X_train = X[train_mask]
    X_test = X[~train_mask]
    y_train = y[train_mask]
    y_test = y[~train_mask]
    
    print(f"   Training period: {df[train_mask]['timestamp'].min()} to {df[train_mask]['timestamp'].max()}")
    print(f"   Testing period: {df[~train_mask]['timestamp'].min()} to {df[~train_mask]['timestamp'].max()}")
    print(f"   Training samples: {len(X_train):,}")
    print(f"   Testing samples: {len(X_test):,}")
    
    # Scale features for better model performance
    print("   Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Create and train the model
    print("   Training Linear Regression model...")
    model = LinearRegression()
    model.fit(X_train_scaled, y_train)
    
    # Make predictions
    print("   Making predictions...")
    y_train_pred = model.predict(X_train_scaled)
    y_test_pred = model.predict(X_test_scaled)
    
    return model, scaler, X_train, X_test, y_train, y_test, y_train_pred, y_test_pred, feature_columns

def evaluate_model(y_train, y_test, y_train_pred, y_test_pred):
    """Evaluate how well our model performed."""
    print("\n📊 MODEL EVALUATION")
    print("="*50)
    
    # Calculate metrics for training data
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    train_r2 = r2_score(y_train, y_train_pred)
    train_mape = np.mean(np.abs((y_train - y_train_pred) / y_train)) * 100
    
    # Calculate metrics for test data
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    test_r2 = r2_score(y_test, y_test_pred)
    test_mape = np.mean(np.abs((y_test - y_test_pred) / y_test)) * 100
    
    print("📈 Training Performance:")
    print(f"   MAE (Mean Absolute Error): {train_mae:.0f} MW")
    print(f"   RMSE (Root Mean Square Error): {train_rmse:.0f} MW")
    print(f"   R² Score: {train_r2:.3f} (1.0 = perfect)")
    print(f"   MAPE (Mean Absolute Percentage Error): {train_mape:.1f}%")
    
    print("\n🎯 Test Performance (How well it predicts new data):")
    print(f"   MAE: {test_mae:.0f} MW")
    print(f"   RMSE: {test_rmse:.0f} MW")
    print(f"   R² Score: {test_r2:.3f}")
    print(f"   MAPE: {test_mape:.1f}%")
    
    # Interpretation
    print(f"\n💡 What this means:")
    print(f"   • Your model predicts power demand within ±{test_mae:.0f} MW on average")
    print(f"   • That's about {test_mape:.1f}% error - {'Excellent!' if test_mape < 5 else 'Good!' if test_mape < 10 else 'Needs improvement'}")
    print(f"   • R² of {test_r2:.3f} means the model explains {test_r2*100:.1f}% of demand variation")
    
    return {
        'test_mae': test_mae,
        'test_rmse': test_rmse,
        'test_r2': test_r2,
        'test_mape': test_mape
    }

def main():
    """Run your first ML model!"""
    print("🚀 WELCOME TO YOUR FIRST ML MODEL!")
    print("="*50)
    print("We're going to predict California power demand using weather data.")
    print("This is a great introduction to machine learning!")
    
    # Load data
    bucket_name = 'ml-power-nowcast-data-1756420517'  # Your S3 bucket
    power_df, weather_df = load_data_from_s3(bucket_name)
    
    # Explore the data
    system_power = explore_data(power_df, weather_df)
    
    # Prepare features
    df = prepare_features(power_df, weather_df)
    
    # Build and train model
    results = build_and_train_model(df)
    model, scaler, X_train, X_test, y_train, y_test, y_train_pred, y_test_pred, feature_columns = results
    
    # Evaluate performance
    metrics = evaluate_model(y_train, y_test, y_train_pred, y_test_pred)
    
    print(f"\n🎉 CONGRATULATIONS!")
    print(f"You've built your first ML model that predicts power demand!")
    print(f"Your model achieves {metrics['test_mape']:.1f}% average error.")
    
    # Clean up temporary files
    import os
    if os.path.exists('temp_power.parquet'):
        os.remove('temp_power.parquet')
    if os.path.exists('temp_weather.parquet'):
        os.remove('temp_weather.parquet')

if __name__ == "__main__":
    main()
