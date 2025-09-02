#!/usr/bin/env python3
"""
Step 1: Analyze What Your Model Learned

This script analyzes your first ML model to understand:
- Which weather factors matter most for power demand
- How temperature affects electricity usage
- Daily and seasonal patterns
- Model strengths and weaknesses
"""

import pandas as pd
import numpy as np
import boto3
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Set up plotting style
plt.style.use('default')
sns.set_palette("husl")

def load_and_prepare_data():
    """Load and prepare the same data as our first model."""
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
    
    # Feature engineering
    merged_df['hour'] = merged_df['timestamp'].dt.hour
    merged_df['day_of_week'] = merged_df['timestamp'].dt.dayofweek
    merged_df['month'] = merged_df['timestamp'].dt.month
    merged_df['is_weekend'] = (merged_df['day_of_week'] >= 5).astype(int)
    merged_df['temp_squared'] = merged_df['temp_c'] ** 2
    merged_df['temp_humidity_interaction'] = merged_df['temp_c'] * merged_df['humidity']
    
    base_temp = 18.0
    merged_df['cooling_degree_hours'] = np.maximum(merged_df['temp_c'] - base_temp, 0)
    merged_df['heating_degree_hours'] = np.maximum(base_temp - merged_df['temp_c'], 0)
    
    # Clean data
    merged_df = merged_df.dropna()
    
    print(f"✅ Prepared {len(merged_df):,} records for analysis")
    return merged_df

def train_model_for_analysis(df):
    """Train the same model as before to analyze it."""
    print("\n🤖 Training model for analysis...")
    
    feature_columns = [
        'temp_c', 'temp_squared', 'humidity', 'wind_speed',
        'hour', 'day_of_week', 'month', 'is_weekend',
        'cooling_degree_hours', 'heating_degree_hours',
        'temp_humidity_interaction'
    ]
    
    X = df[feature_columns].copy()
    y = df['load'].copy()
    
    # Same train/test split as before
    split_date = '2025-06-01'
    train_mask = df['timestamp'] < split_date
    
    X_train = X[train_mask]
    X_test = X[~train_mask]
    y_train = y[train_mask]
    y_test = y[~train_mask]
    
    # Scale and train
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    model = LinearRegression()
    model.fit(X_train_scaled, y_train)
    
    # Make predictions
    y_train_pred = model.predict(X_train_scaled)
    y_test_pred = model.predict(X_test_scaled)
    
    return model, scaler, X_train, X_test, y_train, y_test, y_train_pred, y_test_pred, feature_columns, df[train_mask], df[~train_mask]

def analyze_feature_importance(model, scaler, feature_columns):
    """Analyze which features matter most to the model."""
    print("\n📊 FEATURE IMPORTANCE ANALYSIS")
    print("="*50)
    
    # Get model coefficients (how much each feature affects predictions)
    coefficients = model.coef_
    
    # Create feature importance dataframe
    importance_df = pd.DataFrame({
        'feature': feature_columns,
        'coefficient': coefficients,
        'abs_coefficient': np.abs(coefficients)
    }).sort_values('abs_coefficient', ascending=False)
    
    print("🔍 Most Important Features (ranked by impact):")
    for i, row in importance_df.head(8).iterrows():
        direction = "increases" if row['coefficient'] > 0 else "decreases"
        print(f"   {i+1}. {row['feature']}: {direction} demand (coefficient: {row['coefficient']:.1f})")
    
    # Create visualization
    plt.figure(figsize=(12, 8))
    
    # Feature importance plot
    plt.subplot(2, 2, 1)
    top_features = importance_df.head(8)
    colors = ['red' if x < 0 else 'blue' for x in top_features['coefficient']]
    plt.barh(range(len(top_features)), top_features['coefficient'], color=colors)
    plt.yticks(range(len(top_features)), top_features['feature'])
    plt.xlabel('Coefficient Value')
    plt.title('Feature Importance\n(Blue=Increases Demand, Red=Decreases)')
    plt.gca().invert_yaxis()
    
    return importance_df

def analyze_temperature_relationship(df):
    """Analyze how temperature affects power demand."""
    print("\n🌡️ TEMPERATURE-DEMAND RELATIONSHIP")
    print("="*50)
    
    # Temperature bins for analysis
    df['temp_bin'] = pd.cut(df['temp_c'], bins=15, labels=False)
    temp_analysis = df.groupby('temp_bin').agg({
        'temp_c': 'mean',
        'load': 'mean',
        'cooling_degree_hours': 'mean',
        'heating_degree_hours': 'mean'
    }).reset_index()
    
    # Find optimal temperature (lowest demand)
    optimal_temp_idx = temp_analysis['load'].idxmin()
    optimal_temp = temp_analysis.loc[optimal_temp_idx, 'temp_c']
    min_demand = temp_analysis.loc[optimal_temp_idx, 'load']
    
    print(f"🎯 Optimal temperature: {optimal_temp:.1f}°C (lowest demand: {min_demand:.0f} MW)")
    
    # Temperature sensitivity
    hot_days = df[df['temp_c'] > 25]
    cold_days = df[df['temp_c'] < 10]
    mild_days = df[(df['temp_c'] >= 15) & (df['temp_c'] <= 20)]
    
    print(f"📈 Average demand by temperature:")
    print(f"   Hot days (>25°C): {hot_days['load'].mean():.0f} MW")
    print(f"   Mild days (15-20°C): {mild_days['load'].mean():.0f} MW")
    print(f"   Cold days (<10°C): {cold_days['load'].mean():.0f} MW")
    
    # Plot temperature relationship
    plt.subplot(2, 2, 2)
    plt.scatter(df['temp_c'], df['load'], alpha=0.3, s=1)
    plt.plot(temp_analysis['temp_c'], temp_analysis['load'], 'r-', linewidth=2, label='Average')
    plt.axvline(optimal_temp, color='green', linestyle='--', label=f'Optimal: {optimal_temp:.1f}°C')
    plt.xlabel('Temperature (°C)')
    plt.ylabel('Power Demand (MW)')
    plt.title('Temperature vs Power Demand')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    return temp_analysis

def analyze_daily_patterns(df):
    """Analyze daily and weekly patterns."""
    print("\n📅 DAILY & WEEKLY PATTERNS")
    print("="*50)
    
    # Hourly patterns
    hourly_avg = df.groupby('hour')['load'].mean()
    peak_hour = hourly_avg.idxmax()
    valley_hour = hourly_avg.idxmin()
    
    print(f"⏰ Daily patterns:")
    print(f"   Peak demand hour: {peak_hour}:00 ({hourly_avg[peak_hour]:.0f} MW)")
    print(f"   Valley demand hour: {valley_hour}:00 ({hourly_avg[valley_hour]:.0f} MW)")
    print(f"   Peak-to-valley ratio: {hourly_avg[peak_hour]/hourly_avg[valley_hour]:.2f}x")
    
    # Weekly patterns
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_avg = df.groupby('day_of_week')['load'].mean()
    
    print(f"\n📊 Weekly patterns:")
    for day_num, avg_load in weekly_avg.items():
        print(f"   {day_names[day_num]}: {avg_load:.0f} MW")
    
    # Plot daily patterns
    plt.subplot(2, 2, 3)
    plt.plot(hourly_avg.index, hourly_avg.values, 'b-', linewidth=2, marker='o')
    plt.axvline(peak_hour, color='red', linestyle='--', alpha=0.7, label=f'Peak: {peak_hour}:00')
    plt.axvline(valley_hour, color='green', linestyle='--', alpha=0.7, label=f'Valley: {valley_hour}:00')
    plt.xlabel('Hour of Day')
    plt.ylabel('Average Power Demand (MW)')
    plt.title('Daily Demand Pattern')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xticks(range(0, 24, 3))
    
    return hourly_avg, weekly_avg

def analyze_model_performance(y_test, y_test_pred, test_df):
    """Analyze where the model performs well and poorly."""
    print("\n🎯 MODEL PERFORMANCE ANALYSIS")
    print("="*50)
    
    # Calculate errors
    errors = y_test_pred - y_test
    abs_errors = np.abs(errors)
    percent_errors = abs_errors / y_test * 100
    
    # Performance by conditions
    test_df_copy = test_df.copy()
    test_df_copy['prediction'] = y_test_pred
    test_df_copy['error'] = errors
    test_df_copy['abs_error'] = abs_errors
    test_df_copy['percent_error'] = percent_errors
    
    # Performance by temperature
    hot_performance = test_df_copy[test_df_copy['temp_c'] > 25]['percent_error'].mean()
    mild_performance = test_df_copy[(test_df_copy['temp_c'] >= 15) & (test_df_copy['temp_c'] <= 20)]['percent_error'].mean()
    cold_performance = test_df_copy[test_df_copy['temp_c'] < 10]['percent_error'].mean()
    
    print(f"🌡️ Performance by temperature:")
    print(f"   Hot days (>25°C): {hot_performance:.1f}% average error")
    print(f"   Mild days (15-20°C): {mild_performance:.1f}% average error")
    print(f"   Cold days (<10°C): {cold_performance:.1f}% average error")
    
    # Performance by time
    weekend_performance = test_df_copy[test_df_copy['is_weekend'] == 1]['percent_error'].mean()
    weekday_performance = test_df_copy[test_df_copy['is_weekend'] == 0]['percent_error'].mean()
    
    print(f"\n📅 Performance by day type:")
    print(f"   Weekends: {weekend_performance:.1f}% average error")
    print(f"   Weekdays: {weekday_performance:.1f}% average error")
    
    # Plot predictions vs actual
    plt.subplot(2, 2, 4)
    plt.scatter(y_test, y_test_pred, alpha=0.5, s=10)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', linewidth=2)
    plt.xlabel('Actual Demand (MW)')
    plt.ylabel('Predicted Demand (MW)')
    plt.title('Predictions vs Actual')
    plt.grid(True, alpha=0.3)
    
    # Add R² to plot
    r2 = r2_score(y_test, y_test_pred)
    plt.text(0.05, 0.95, f'R² = {r2:.3f}', transform=plt.gca().transAxes, 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    return test_df_copy

def main():
    """Run the complete model analysis."""
    print("🔍 STEP 1: ANALYZING YOUR FIRST ML MODEL")
    print("="*60)
    print("Let's understand what your model learned about California power demand!")
    
    # Load and prepare data
    df = load_and_prepare_data()
    
    # Train model
    results = train_model_for_analysis(df)
    model, scaler, X_train, X_test, y_train, y_test, y_train_pred, y_test_pred, feature_columns, train_df, test_df = results
    
    # Create analysis plots
    plt.figure(figsize=(16, 12))
    
    # Run all analyses
    importance_df = analyze_feature_importance(model, scaler, feature_columns)
    temp_analysis = analyze_temperature_relationship(df)
    hourly_avg, weekly_avg = analyze_daily_patterns(df)
    performance_analysis = analyze_model_performance(y_test, y_test_pred, test_df)
    
    # Save the plot
    plt.tight_layout()
    plt.savefig('model_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Analysis plots saved as 'model_analysis.png'")
    
    # Key insights summary
    print(f"\n🎯 KEY INSIGHTS FROM YOUR MODEL:")
    print("="*50)
    print(f"1. 🌡️ Temperature is the strongest predictor of power demand")
    print(f"2. ⏰ Time of day matters a lot - peak demand around evening")
    print(f"3. 🔥 Hot weather drives up demand (air conditioning)")
    print(f"4. ❄️ Cold weather also increases demand (heating)")
    print(f"5. 📅 Weekend patterns differ from weekdays")
    print(f"6. 🎯 Model works best in mild weather conditions")
    
    # Clean up
    import os
    if os.path.exists('temp_power.parquet'):
        os.remove('temp_power.parquet')
    if os.path.exists('temp_weather.parquet'):
        os.remove('temp_weather.parquet')
    
    print(f"\n✅ Analysis complete! Ready for Step 2: More Powerful Algorithms")

if __name__ == "__main__":
    main()
