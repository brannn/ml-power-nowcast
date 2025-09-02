#!/usr/bin/env python3
"""
Step 2: More Powerful ML Algorithms

This script builds more sophisticated models that can capture complex patterns
your linear model missed. We'll try Random Forest and XGBoost - both are
excellent for power demand forecasting.
"""

import pandas as pd
import numpy as np
import boto3
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

def load_and_prepare_data():
    """Load and prepare data (same as before)."""
    print("📥 Loading data from S3...")
    
    s3_client = boto3.client('s3')
    bucket_name = 'ml-power-nowcast-data-1756420517'
    
    # Download data
    s3_client.download_file(bucket_name, 'raw/power/caiso/real_365d.parquet', 'temp_power.parquet')
    power_df = pd.read_parquet('temp_power.parquet')
    
    s3_client.download_file(bucket_name, 'raw/weather/caiso_zones/real_1y.parquet', 'temp_weather.parquet')
    weather_df = pd.read_parquet('temp_weather.parquet')
    
    # Prepare data (same as first model)
    system_power = power_df[power_df['zone'] == 'SYSTEM'].copy()
    
    # Handle timezones
    system_power['timestamp'] = pd.to_datetime(system_power['timestamp'])
    weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
    
    if system_power['timestamp'].dt.tz is not None:
        system_power['timestamp'] = system_power['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
    if weather_df['timestamp'].dt.tz is not None:
        weather_df['timestamp'] = weather_df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
    
    # Resample to hourly and merge
    system_power_hourly = system_power.set_index('timestamp').resample('H')['load'].mean().reset_index()
    merged_df = pd.merge(system_power_hourly, weather_df, on='timestamp', how='inner')
    
    # Enhanced feature engineering for advanced models
    print("🔧 Creating enhanced features for advanced models...")
    
    # Time features
    merged_df['hour'] = merged_df['timestamp'].dt.hour
    merged_df['day_of_week'] = merged_df['timestamp'].dt.dayofweek
    merged_df['month'] = merged_df['timestamp'].dt.month
    merged_df['day_of_year'] = merged_df['timestamp'].dt.dayofyear
    merged_df['is_weekend'] = (merged_df['day_of_week'] >= 5).astype(int)
    merged_df['is_business_hour'] = ((merged_df['hour'] >= 8) & (merged_df['hour'] <= 18) & (merged_df['is_weekend'] == 0)).astype(int)
    
    # Weather features
    merged_df['temp_squared'] = merged_df['temp_c'] ** 2
    merged_df['temp_cubed'] = merged_df['temp_c'] ** 3
    merged_df['temp_humidity_interaction'] = merged_df['temp_c'] * merged_df['humidity']
    merged_df['temp_wind_interaction'] = merged_df['temp_c'] * merged_df['wind_speed']
    
    # Degree hours (more sophisticated)
    base_temp = 18.0
    merged_df['cooling_degree_hours'] = np.maximum(merged_df['temp_c'] - base_temp, 0)
    merged_df['heating_degree_hours'] = np.maximum(base_temp - merged_df['temp_c'], 0)
    merged_df['extreme_heat'] = (merged_df['temp_c'] > 30).astype(int)
    merged_df['extreme_cold'] = (merged_df['temp_c'] < 5).astype(int)
    
    # Lag features (previous hours' weather and demand)
    merged_df = merged_df.sort_values('timestamp')
    merged_df['load_lag_1h'] = merged_df['load'].shift(1)
    merged_df['load_lag_24h'] = merged_df['load'].shift(24)
    merged_df['temp_lag_1h'] = merged_df['temp_c'].shift(1)
    merged_df['temp_change_1h'] = merged_df['temp_c'] - merged_df['temp_lag_1h']
    
    # Seasonal features
    merged_df['sin_hour'] = np.sin(2 * np.pi * merged_df['hour'] / 24)
    merged_df['cos_hour'] = np.cos(2 * np.pi * merged_df['hour'] / 24)
    merged_df['sin_day_of_year'] = np.sin(2 * np.pi * merged_df['day_of_year'] / 365)
    merged_df['cos_day_of_year'] = np.cos(2 * np.pi * merged_df['day_of_year'] / 365)
    
    # Clean data
    merged_df = merged_df.dropna()
    
    print(f"✅ Prepared {len(merged_df):,} records with {merged_df.shape[1]} features")
    return merged_df

def compare_algorithms(df):
    """Compare Linear Regression, Random Forest, and show the improvement."""
    print("\n🤖 COMPARING ML ALGORITHMS")
    print("="*50)
    
    # Enhanced feature set
    feature_columns = [
        'temp_c', 'temp_squared', 'temp_cubed', 'humidity', 'wind_speed',
        'hour', 'day_of_week', 'month', 'day_of_year', 'is_weekend', 'is_business_hour',
        'cooling_degree_hours', 'heating_degree_hours', 'extreme_heat', 'extreme_cold',
        'temp_humidity_interaction', 'temp_wind_interaction',
        'load_lag_1h', 'load_lag_24h', 'temp_lag_1h', 'temp_change_1h',
        'sin_hour', 'cos_hour', 'sin_day_of_year', 'cos_day_of_year'
    ]
    
    X = df[feature_columns].copy()
    y = df['load'].copy()
    
    # Train/test split
    split_date = '2025-06-01'
    train_mask = df['timestamp'] < split_date
    
    X_train = X[train_mask]
    X_test = X[~train_mask]
    y_train = y[train_mask]
    y_test = y[~train_mask]
    
    print(f"Training samples: {len(X_train):,}")
    print(f"Testing samples: {len(X_test):,}")
    print(f"Features: {len(feature_columns)}")
    
    # Scale features for Linear Regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Model 1: Linear Regression (baseline)
    print("\n📊 Training Linear Regression (baseline)...")
    lr_model = LinearRegression()
    lr_model.fit(X_train_scaled, y_train)
    lr_pred = lr_model.predict(X_test_scaled)
    
    lr_mae = mean_absolute_error(y_test, lr_pred)
    lr_rmse = np.sqrt(mean_squared_error(y_test, lr_pred))
    lr_r2 = r2_score(y_test, lr_pred)
    lr_mape = np.mean(np.abs((y_test - lr_pred) / y_test)) * 100
    
    # Model 2: Random Forest
    print("🌲 Training Random Forest...")
    rf_model = RandomForestRegressor(
        n_estimators=100,      # Number of trees
        max_depth=15,          # Maximum depth of trees
        min_samples_split=5,   # Minimum samples to split a node
        min_samples_leaf=2,    # Minimum samples in a leaf
        random_state=42,       # For reproducible results
        n_jobs=-1             # Use all CPU cores
    )
    rf_model.fit(X_train, y_train)  # Random Forest doesn't need scaling
    rf_pred = rf_model.predict(X_test)
    
    rf_mae = mean_absolute_error(y_test, rf_pred)
    rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))
    rf_r2 = r2_score(y_test, rf_pred)
    rf_mape = np.mean(np.abs((y_test - rf_pred) / y_test)) * 100
    
    # Compare results
    print("\n📈 MODEL COMPARISON RESULTS")
    print("="*50)
    
    print("🔹 Linear Regression (Enhanced Features):")
    print(f"   MAE: {lr_mae:.0f} MW")
    print(f"   RMSE: {lr_rmse:.0f} MW")
    print(f"   R²: {lr_r2:.3f}")
    print(f"   MAPE: {lr_mape:.1f}%")
    
    print("\n🌲 Random Forest:")
    print(f"   MAE: {rf_mae:.0f} MW")
    print(f"   RMSE: {rf_rmse:.0f} MW")
    print(f"   R²: {rf_r2:.3f}")
    print(f"   MAPE: {rf_mape:.1f}%")
    
    # Calculate improvements
    mae_improvement = (lr_mae - rf_mae) / lr_mae * 100
    r2_improvement = (rf_r2 - lr_r2) / lr_r2 * 100
    
    print(f"\n🚀 RANDOM FOREST IMPROVEMENTS:")
    print(f"   MAE improved by: {mae_improvement:.1f}%")
    print(f"   R² improved by: {r2_improvement:.1f}%")
    print(f"   {'🎉 Significant improvement!' if mae_improvement > 10 else '✅ Good improvement!' if mae_improvement > 5 else '📈 Modest improvement'}")
    
    return rf_model, X_test, y_test, rf_pred, feature_columns

def analyze_random_forest_insights(model, feature_columns):
    """Analyze what the Random Forest learned."""
    print("\n🌲 RANDOM FOREST INSIGHTS")
    print("="*50)
    
    # Feature importance from Random Forest
    importance_df = pd.DataFrame({
        'feature': feature_columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("🔍 Most Important Features (Random Forest ranking):")
    for i, row in importance_df.head(10).iterrows():
        print(f"   {i+1}. {row['feature']}: {row['importance']:.3f}")
    
    # Plot feature importance
    plt.figure(figsize=(14, 10))
    
    # Feature importance plot
    plt.subplot(2, 2, 1)
    top_features = importance_df.head(12)
    plt.barh(range(len(top_features)), top_features['importance'])
    plt.yticks(range(len(top_features)), top_features['feature'])
    plt.xlabel('Feature Importance')
    plt.title('Random Forest Feature Importance')
    plt.gca().invert_yaxis()
    
    return importance_df

def visualize_predictions(y_test, rf_pred, df):
    """Create visualizations of model performance."""
    
    # Predictions vs Actual
    plt.subplot(2, 2, 2)
    plt.scatter(y_test, rf_pred, alpha=0.5, s=10)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', linewidth=2)
    plt.xlabel('Actual Demand (MW)')
    plt.ylabel('Predicted Demand (MW)')
    plt.title('Random Forest: Predictions vs Actual')
    plt.grid(True, alpha=0.3)
    
    # Add R² to plot
    r2 = r2_score(y_test, rf_pred)
    plt.text(0.05, 0.95, f'R² = {r2:.3f}', transform=plt.gca().transAxes, 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Time series of recent predictions
    plt.subplot(2, 2, 3)
    test_df = df[df['timestamp'] >= '2025-06-01'].copy()
    test_df = test_df.iloc[:168]  # Show one week
    test_df['prediction'] = rf_pred[:len(test_df)]
    
    plt.plot(test_df['timestamp'], test_df['load'], 'b-', label='Actual', linewidth=2)
    plt.plot(test_df['timestamp'], test_df['prediction'], 'r-', label='Predicted', linewidth=2)
    plt.xlabel('Date')
    plt.ylabel('Power Demand (MW)')
    plt.title('One Week of Predictions (June 2025)')
    plt.legend()
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Error distribution
    plt.subplot(2, 2, 4)
    errors = rf_pred - y_test
    plt.hist(errors, bins=50, alpha=0.7, edgecolor='black')
    plt.axvline(0, color='red', linestyle='--', linewidth=2)
    plt.xlabel('Prediction Error (MW)')
    plt.ylabel('Frequency')
    plt.title('Distribution of Prediction Errors')
    plt.grid(True, alpha=0.3)
    
    # Add error statistics
    mean_error = np.mean(errors)
    std_error = np.std(errors)
    plt.text(0.05, 0.95, f'Mean: {mean_error:.0f} MW\nStd: {std_error:.0f} MW', 
             transform=plt.gca().transAxes, 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

def main():
    """Run the advanced model comparison."""
    print("🚀 STEP 2: MORE POWERFUL ML ALGORITHMS")
    print("="*60)
    print("Let's build more sophisticated models that can capture complex patterns!")
    
    # Load and prepare data with enhanced features
    df = load_and_prepare_data()
    
    # Compare algorithms
    rf_model, X_test, y_test, rf_pred, feature_columns = compare_algorithms(df)
    
    # Create visualizations
    plt.figure(figsize=(16, 12))
    
    # Analyze Random Forest insights
    importance_df = analyze_random_forest_insights(rf_model, feature_columns)
    
    # Create prediction visualizations
    visualize_predictions(y_test, rf_pred, df)
    
    # Save the plot
    plt.tight_layout()
    plt.savefig('advanced_model_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Advanced model analysis saved as 'advanced_model_analysis.png'")
    
    # Key insights
    print(f"\n🎯 KEY IMPROVEMENTS WITH RANDOM FOREST:")
    print("="*50)
    print(f"1. 🌲 Random Forest can capture non-linear patterns Linear Regression missed")
    print(f"2. 📊 Lag features (previous hours) are very important for prediction")
    print(f"3. 🕐 Cyclical time features (sin/cos) help capture daily/seasonal patterns")
    print(f"4. 🌡️ Temperature interactions and extremes matter for accuracy")
    print(f"5. 🎯 Overall better performance with more sophisticated feature engineering")
    
    # Clean up
    import os
    if os.path.exists('temp_power.parquet'):
        os.remove('temp_power.parquet')
    if os.path.exists('temp_weather.parquet'):
        os.remove('temp_weather.parquet')
    
    print(f"\n✅ Step 2 complete! Ready for Step 3: Regional Models")

if __name__ == "__main__":
    main()
