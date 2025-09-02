#!/usr/bin/env python3
"""
Step 3: Regional Models

Build separate models for each California region (San Diego, LA, Bay Area, etc.)
to capture regional differences in weather sensitivity and demand patterns.
"""

import pandas as pd
import numpy as np
import boto3
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

def load_regional_data():
    """Load both power and weather data with regional breakdown."""
    print("📥 Loading regional data from S3...")
    
    s3_client = boto3.client('s3')
    bucket_name = 'ml-power-nowcast-data-1756420517'
    
    # Download data
    s3_client.download_file(bucket_name, 'raw/power/caiso/real_365d.parquet', 'temp_power.parquet')
    power_df = pd.read_parquet('temp_power.parquet')
    
    s3_client.download_file(bucket_name, 'raw/weather/caiso_zones/real_1y.parquet', 'temp_weather.parquet')
    weather_df = pd.read_parquet('temp_weather.parquet')
    
    print(f"✅ Loaded {len(power_df):,} power records and {len(weather_df):,} weather records")
    
    # Show available regions
    power_zones = power_df['zone'].value_counts()
    print(f"\n🌍 Available Power Zones:")
    for zone, count in power_zones.items():
        if zone is not None:
            avg_load = power_df[power_df['zone'] == zone]['load'].mean()
            print(f"   {zone}: {count:,} records | Avg: {avg_load:,.0f} MW")
    
    if 'zone' in weather_df.columns:
        weather_zones = weather_df['zone'].value_counts()
        print(f"\n🌤️  Available Weather Zones:")
        for zone, count in weather_zones.items():
            if zone is not None:
                avg_temp = weather_df[weather_df['zone'] == zone]['temp_c'].mean()
                print(f"   {zone}: {count:,} records | Avg: {avg_temp:.1f}°C")
    
    return power_df, weather_df

def prepare_regional_features(power_df, weather_df, zone):
    """Prepare features for a specific zone."""
    
    # Filter data for this zone
    zone_power = power_df[power_df['zone'] == zone].copy()
    
    # Handle timezones
    zone_power['timestamp'] = pd.to_datetime(zone_power['timestamp'])
    weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
    
    if zone_power['timestamp'].dt.tz is not None:
        zone_power['timestamp'] = zone_power['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
    if weather_df['timestamp'].dt.tz is not None:
        weather_df['timestamp'] = weather_df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
    
    # Resample power to hourly
    zone_power_hourly = zone_power.set_index('timestamp').resample('H')['load'].mean().reset_index()
    
    # For weather, use system-wide weather for now (could be enhanced with zone-specific weather)
    # If we have zone-specific weather, use it; otherwise use system-wide
    if 'zone' in weather_df.columns and zone in weather_df['zone'].values:
        zone_weather = weather_df[weather_df['zone'] == zone].copy()
    else:
        # Use system-wide weather as fallback
        zone_weather = weather_df.copy()
    
    # Merge power and weather
    merged_df = pd.merge(zone_power_hourly, zone_weather, on='timestamp', how='inner')
    
    if len(merged_df) == 0:
        print(f"⚠️  No data after merging for zone {zone}")
        return None
    
    # Feature engineering (same as advanced model)
    merged_df['hour'] = merged_df['timestamp'].dt.hour
    merged_df['day_of_week'] = merged_df['timestamp'].dt.dayofweek
    merged_df['month'] = merged_df['timestamp'].dt.month
    merged_df['day_of_year'] = merged_df['timestamp'].dt.dayofyear
    merged_df['is_weekend'] = (merged_df['day_of_week'] >= 5).astype(int)
    merged_df['is_business_hour'] = ((merged_df['hour'] >= 8) & (merged_df['hour'] <= 18) & (merged_df['is_weekend'] == 0)).astype(int)
    
    # Weather features
    merged_df['temp_squared'] = merged_df['temp_c'] ** 2
    merged_df['temp_humidity_interaction'] = merged_df['temp_c'] * merged_df['humidity']
    
    # Degree hours
    base_temp = 18.0
    merged_df['cooling_degree_hours'] = np.maximum(merged_df['temp_c'] - base_temp, 0)
    merged_df['heating_degree_hours'] = np.maximum(base_temp - merged_df['temp_c'], 0)
    
    # Lag features
    merged_df = merged_df.sort_values('timestamp')
    merged_df['load_lag_1h'] = merged_df['load'].shift(1)
    merged_df['load_lag_24h'] = merged_df['load'].shift(24)
    merged_df['temp_lag_1h'] = merged_df['temp_c'].shift(1)
    
    # Seasonal features
    merged_df['sin_hour'] = np.sin(2 * np.pi * merged_df['hour'] / 24)
    merged_df['cos_hour'] = np.cos(2 * np.pi * merged_df['hour'] / 24)
    merged_df['sin_day_of_year'] = np.sin(2 * np.pi * merged_df['day_of_year'] / 365)
    merged_df['cos_day_of_year'] = np.cos(2 * np.pi * merged_df['day_of_year'] / 365)
    
    # Clean data
    merged_df = merged_df.dropna()
    
    return merged_df

def build_regional_model(df, zone_name):
    """Build a Random Forest model for a specific zone."""
    
    feature_columns = [
        'temp_c', 'temp_squared', 'humidity', 'wind_speed',
        'hour', 'day_of_week', 'month', 'is_weekend', 'is_business_hour',
        'cooling_degree_hours', 'heating_degree_hours',
        'temp_humidity_interaction',
        'load_lag_1h', 'load_lag_24h', 'temp_lag_1h',
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
    
    if len(X_train) < 100 or len(X_test) < 20:
        print(f"⚠️  Insufficient data for {zone_name}: train={len(X_train)}, test={len(X_test)}")
        return None, None, None, None, None
    
    # Train Random Forest
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    
    # Calculate metrics
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)
    mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100
    
    return model, X_test, y_test, predictions, {
        'mae': mae, 'rmse': rmse, 'r2': r2, 'mape': mape,
        'train_samples': len(X_train), 'test_samples': len(X_test)
    }

def compare_regional_models():
    """Build and compare models for each region."""
    print("\n🌍 BUILDING REGIONAL MODELS")
    print("="*50)
    
    # Load data
    power_df, weather_df = load_regional_data()
    
    # Define zones to model (focus on major ones with sufficient data)
    zones_to_model = ['SYSTEM', 'NP15', 'SCE', 'SDGE']
    
    regional_results = {}
    
    for zone in zones_to_model:
        print(f"\n🔧 Building model for {zone}...")
        
        # Prepare data for this zone
        zone_df = prepare_regional_features(power_df, weather_df, zone)
        
        if zone_df is None or len(zone_df) < 1000:
            print(f"   ⚠️  Skipping {zone} - insufficient data")
            continue
        
        # Build model
        results = build_regional_model(zone_df, zone)
        model, X_test, y_test, predictions, metrics = results
        
        if model is None:
            continue
        
        regional_results[zone] = {
            'model': model,
            'metrics': metrics,
            'predictions': predictions,
            'actual': y_test,
            'zone_df': zone_df
        }
        
        # Print results
        print(f"   ✅ {zone} Model Results:")
        print(f"      MAE: {metrics['mae']:.0f} MW")
        print(f"      MAPE: {metrics['mape']:.1f}%")
        print(f"      R²: {metrics['r2']:.3f}")
        print(f"      Training samples: {metrics['train_samples']:,}")
    
    return regional_results

def analyze_regional_differences(regional_results):
    """Analyze differences between regional models."""
    print(f"\n📊 REGIONAL MODEL COMPARISON")
    print("="*50)
    
    # Create comparison table
    comparison_data = []
    for zone, results in regional_results.items():
        metrics = results['metrics']
        avg_load = results['actual'].mean()
        
        comparison_data.append({
            'Zone': zone,
            'Avg Load (MW)': f"{avg_load:.0f}",
            'MAE (MW)': f"{metrics['mae']:.0f}",
            'MAPE (%)': f"{metrics['mape']:.1f}",
            'R²': f"{metrics['r2']:.3f}",
            'Samples': f"{metrics['test_samples']:,}"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df.to_string(index=False))
    
    # Visualize regional performance
    plt.figure(figsize=(16, 12))
    
    # MAPE comparison
    plt.subplot(2, 3, 1)
    zones = list(regional_results.keys())
    mapes = [regional_results[zone]['metrics']['mape'] for zone in zones]
    colors = ['red' if zone == 'SYSTEM' else 'blue' for zone in zones]
    
    plt.bar(zones, mapes, color=colors, alpha=0.7)
    plt.ylabel('MAPE (%)')
    plt.title('Model Accuracy by Region')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Average load comparison
    plt.subplot(2, 3, 2)
    avg_loads = [regional_results[zone]['actual'].mean() for zone in zones]
    plt.bar(zones, avg_loads, color='green', alpha=0.7)
    plt.ylabel('Average Load (MW)')
    plt.title('Average Demand by Region')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Feature importance for each region
    for i, zone in enumerate(zones[:4]):  # Show up to 4 regions
        plt.subplot(2, 3, i+3)
        
        model = regional_results[zone]['model']
        feature_names = [
            'temp_c', 'temp_squared', 'humidity', 'wind_speed',
            'hour', 'day_of_week', 'month', 'is_weekend', 'is_business_hour',
            'cooling_degree_hours', 'heating_degree_hours',
            'temp_humidity_interaction',
            'load_lag_1h', 'load_lag_24h', 'temp_lag_1h',
            'sin_hour', 'cos_hour', 'sin_day_of_year', 'cos_day_of_year'
        ]
        
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False).head(8)
        
        plt.barh(range(len(importance_df)), importance_df['importance'])
        plt.yticks(range(len(importance_df)), importance_df['feature'])
        plt.xlabel('Importance')
        plt.title(f'{zone} Feature Importance')
        plt.gca().invert_yaxis()
    
    plt.tight_layout()
    plt.savefig('regional_models_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Regional analysis saved as 'regional_models_analysis.png'")
    
    return comparison_df

def regional_insights(regional_results):
    """Generate insights about regional differences."""
    print(f"\n🎯 REGIONAL INSIGHTS")
    print("="*50)
    
    # Find best and worst performing regions
    mapes = {zone: results['metrics']['mape'] for zone, results in regional_results.items()}
    best_zone = min(mapes, key=mapes.get)
    worst_zone = max(mapes, key=mapes.get)
    
    print(f"🏆 Best performing region: {best_zone} ({mapes[best_zone]:.1f}% MAPE)")
    print(f"📈 Most challenging region: {worst_zone} ({mapes[worst_zone]:.1f}% MAPE)")
    
    # Analyze load characteristics
    print(f"\n📊 Regional Load Characteristics:")
    for zone, results in regional_results.items():
        actual = results['actual']
        peak_load = actual.max()
        min_load = actual.min()
        volatility = actual.std()
        
        print(f"   {zone}:")
        print(f"      Peak: {peak_load:.0f} MW")
        print(f"      Valley: {min_load:.0f} MW")
        print(f"      Volatility (std): {volatility:.0f} MW")
        print(f"      Peak/Valley ratio: {peak_load/min_load:.2f}x")
    
    print(f"\n💡 Key Takeaways:")
    print(f"   1. Regional models can capture local weather-demand patterns")
    print(f"   2. Different regions have different temperature sensitivities")
    print(f"   3. Urban vs rural areas show different demand profiles")
    print(f"   4. Regional models enable more targeted forecasting")

def main():
    """Run the regional modeling analysis."""
    print("🌍 STEP 3: REGIONAL MODELS")
    print("="*60)
    print("Building separate models for each California region!")
    
    # Build regional models
    regional_results = compare_regional_models()
    
    if not regional_results:
        print("❌ No regional models could be built")
        return
    
    # Analyze regional differences
    comparison_df = analyze_regional_differences(regional_results)
    
    # Generate insights
    regional_insights(regional_results)
    
    # Clean up
    import os
    if os.path.exists('temp_power.parquet'):
        os.remove('temp_power.parquet')
    if os.path.exists('temp_weather.parquet'):
        os.remove('temp_weather.parquet')
    
    print(f"\n✅ Step 3 complete! Ready for Step 4: Visualizations")

if __name__ == "__main__":
    main()
