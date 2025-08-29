#!/usr/bin/env python3
"""
Local API Server for Power Demand Predictions

This FastAPI server runs locally on your M4 Mac Mini and provides:
1. Real-time power demand predictions
2. Historical data and model performance
3. Regional forecasts
4. Model insights and metrics

The Fly.io dashboard will fetch data from this API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import boto3
from datetime import datetime, timedelta
import pickle
import json
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import uvicorn
import warnings
warnings.filterwarnings('ignore')

# Initialize FastAPI app
app = FastAPI(
    title="Power Demand Prediction API",
    description="Real-time California power demand forecasting API",
    version="1.0.0"
)

# Add CORS middleware to allow requests from Fly.io dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Fly.io domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and data
predictor_model = None
recent_data = None
model_metrics = {}
regional_models = {}

# Pydantic models for API responses
class PredictionPoint(BaseModel):
    timestamp: str
    predicted_load: float
    confidence_lower: float
    confidence_upper: float
    hour_ahead: int

class WeatherInput(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float

class ModelMetrics(BaseModel):
    mae: float
    rmse: float
    r2: float
    mape: float
    last_updated: str

class RegionalData(BaseModel):
    zone: str
    current_load: float
    predicted_load: float
    avg_load: float
    peak_load: float

class SystemStatus(BaseModel):
    status: str
    last_prediction: str
    model_accuracy: float
    data_freshness: str
    alerts: List[str]

def load_model_and_data():
    """Load the trained model and recent data."""
    global predictor_model, recent_data, model_metrics
    
    print("🤖 Loading model and data...")
    
    try:
        # Load data from S3
        s3_client = boto3.client('s3')
        bucket_name = 'ml-power-nowcast-data-1756420517'
        
        s3_client.download_file(bucket_name, 'raw/power/caiso/real_365d.parquet', 'temp_power.parquet')
        power_df = pd.read_parquet('temp_power.parquet')
        
        s3_client.download_file(bucket_name, 'raw/weather/caiso_zones/real_1y.parquet', 'temp_weather.parquet')
        weather_df = pd.read_parquet('temp_weather.parquet')
        
        # Prepare system-wide data
        system_power = power_df[power_df['zone'] == 'SYSTEM'].copy()
        
        # Handle timezones
        system_power['timestamp'] = pd.to_datetime(system_power['timestamp'])
        weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
        
        if system_power['timestamp'].dt.tz is not None:
            system_power['timestamp'] = system_power['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
        if weather_df['timestamp'].dt.tz is not None:
            weather_df['timestamp'] = weather_df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
        
        # Resample and merge
        system_power_hourly = system_power.set_index('timestamp').resample('H')['load'].mean().reset_index()
        merged_df = pd.merge(system_power_hourly, weather_df, on='timestamp', how='inner')
        
        # Feature engineering
        merged_df = engineer_features(merged_df)
        merged_df = merged_df.dropna()
        
        # Store recent data
        recent_data = merged_df.tail(48).copy()
        
        # Train model
        feature_columns = [
            'temp_c', 'temp_squared', 'humidity', 'wind_speed',
            'hour', 'day_of_week', 'month', 'is_weekend', 'is_business_hour',
            'cooling_degree_hours', 'heating_degree_hours',
            'temp_humidity_interaction',
            'load_lag_1h', 'load_lag_24h', 'temp_lag_1h',
            'sin_hour', 'cos_hour', 'sin_day_of_year', 'cos_day_of_year'
        ]
        
        X = merged_df[feature_columns]
        y = merged_df['load']
        
        predictor_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        predictor_model.fit(X, y)
        
        # Calculate metrics on recent data
        recent_X = X.tail(1000)
        recent_y = y.tail(1000)
        recent_pred = predictor_model.predict(recent_X)
        
        model_metrics = {
            'mae': float(mean_absolute_error(recent_y, recent_pred)),
            'rmse': float(np.sqrt(np.mean((recent_y - recent_pred) ** 2))),
            'r2': float(r2_score(recent_y, recent_pred)),
            'mape': float(np.mean(np.abs((recent_y - recent_pred) / recent_y)) * 100),
            'last_updated': datetime.now().isoformat()
        }
        
        print(f"✅ Model loaded! MAE: {model_metrics['mae']:.0f} MW")
        
        # Clean up
        import os
        if os.path.exists('temp_power.parquet'):
            os.remove('temp_power.parquet')
        if os.path.exists('temp_weather.parquet'):
            os.remove('temp_weather.parquet')
            
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise

def engineer_features(df):
    """Engineer features for prediction."""
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['month'] = df['timestamp'].dt.month
    df['day_of_year'] = df['timestamp'].dt.dayofyear
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['is_business_hour'] = ((df['hour'] >= 8) & (df['hour'] <= 18) & (df['is_weekend'] == 0)).astype(int)
    
    # Weather features
    df['temp_squared'] = df['temp_c'] ** 2
    df['temp_humidity_interaction'] = df['temp_c'] * df['humidity']
    
    # Degree hours
    base_temp = 18.0
    df['cooling_degree_hours'] = np.maximum(df['temp_c'] - base_temp, 0)
    df['heating_degree_hours'] = np.maximum(base_temp - df['temp_c'], 0)
    
    # Lag features
    df = df.sort_values('timestamp')
    df['load_lag_1h'] = df['load'].shift(1)
    df['load_lag_24h'] = df['load'].shift(24)
    df['temp_lag_1h'] = df['temp_c'].shift(1)
    
    # Seasonal features
    df['sin_hour'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['cos_hour'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['sin_day_of_year'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
    df['cos_day_of_year'] = np.cos(2 * np.pi * df['day_of_year'] / 365)
    
    return df

@app.on_event("startup")
async def startup_event():
    """Load model when server starts."""
    load_model_and_data()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Power Demand Prediction API", "status": "running"}

@app.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status."""
    if predictor_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    alerts = []
    if model_metrics['mae'] > 1000:
        alerts.append("High prediction error detected")
    
    # Check data freshness (assuming recent_data is available)
    if recent_data is not None:
        latest_data = recent_data['timestamp'].max()
        hours_old = (datetime.now() - latest_data).total_seconds() / 3600
        if hours_old > 24:
            alerts.append(f"Data is {hours_old:.1f} hours old")
    
    return SystemStatus(
        status="operational" if len(alerts) == 0 else "warning",
        last_prediction=datetime.now().isoformat(),
        model_accuracy=model_metrics['mape'],
        data_freshness=f"{hours_old:.1f} hours" if recent_data is not None else "unknown",
        alerts=alerts
    )

@app.get("/metrics", response_model=ModelMetrics)
async def get_model_metrics():
    """Get model performance metrics."""
    if not model_metrics:
        raise HTTPException(status_code=503, detail="Model metrics not available")
    
    return ModelMetrics(**model_metrics)

@app.post("/predict", response_model=List[PredictionPoint])
async def predict_demand(weather: WeatherInput, hours_ahead: int = 6):
    """Predict power demand for the next few hours."""
    if predictor_model is None or recent_data is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if hours_ahead < 1 or hours_ahead > 24:
        raise HTTPException(status_code=400, detail="hours_ahead must be between 1 and 24")
    
    predictions = []
    current_time = datetime.now()
    
    # Get recent load values for lag features
    recent_load_1h = recent_data['load'].iloc[-1]
    recent_load_24h = recent_data['load'].iloc[-24] if len(recent_data) >= 24 else recent_load_1h
    recent_temp_1h = recent_data['temp_c'].iloc[-1]
    
    feature_columns = [
        'temp_c', 'temp_squared', 'humidity', 'wind_speed',
        'hour', 'day_of_week', 'month', 'is_weekend', 'is_business_hour',
        'cooling_degree_hours', 'heating_degree_hours',
        'temp_humidity_interaction',
        'load_lag_1h', 'load_lag_24h', 'temp_lag_1h',
        'sin_hour', 'cos_hour', 'sin_day_of_year', 'cos_day_of_year'
    ]
    
    for hour in range(hours_ahead):
        future_time = current_time + timedelta(hours=hour + 1)
        
        # Create feature vector
        features = {
            'temp_c': weather.temperature,
            'temp_squared': weather.temperature ** 2,
            'humidity': weather.humidity,
            'wind_speed': weather.wind_speed,
            'hour': future_time.hour,
            'day_of_week': future_time.weekday(),
            'month': future_time.month,
            'day_of_year': future_time.timetuple().tm_yday,
            'is_weekend': 1 if future_time.weekday() >= 5 else 0,
            'is_business_hour': 1 if (8 <= future_time.hour <= 18 and future_time.weekday() < 5) else 0,
            'cooling_degree_hours': max(weather.temperature - 18.0, 0),
            'heating_degree_hours': max(18.0 - weather.temperature, 0),
            'temp_humidity_interaction': weather.temperature * weather.humidity,
            'load_lag_1h': recent_load_1h,
            'load_lag_24h': recent_load_24h,
            'temp_lag_1h': recent_temp_1h,
            'sin_hour': np.sin(2 * np.pi * future_time.hour / 24),
            'cos_hour': np.cos(2 * np.pi * future_time.hour / 24),
            'sin_day_of_year': np.sin(2 * np.pi * future_time.timetuple().tm_yday / 365),
            'cos_day_of_year': np.cos(2 * np.pi * future_time.timetuple().tm_yday / 365)
        }
        
        # Make prediction
        X = pd.DataFrame([features])[feature_columns]
        prediction = predictor_model.predict(X)[0]
        
        # Simple confidence interval based on model error
        confidence_margin = model_metrics['mae']
        
        predictions.append(PredictionPoint(
            timestamp=future_time.isoformat(),
            predicted_load=float(prediction),
            confidence_lower=float(prediction - confidence_margin),
            confidence_upper=float(prediction + confidence_margin),
            hour_ahead=hour + 1
        ))
        
        # Update lag for next iteration
        recent_load_1h = prediction
    
    return predictions

@app.get("/historical")
async def get_historical_data(days: int = 7):
    """Get historical actual vs predicted data."""
    if recent_data is None:
        raise HTTPException(status_code=503, detail="Historical data not available")
    
    # Return recent data for visualization
    historical = recent_data.tail(days * 24).copy()
    
    # Generate predictions for historical data
    feature_columns = [
        'temp_c', 'temp_squared', 'humidity', 'wind_speed',
        'hour', 'day_of_week', 'month', 'is_weekend', 'is_business_hour',
        'cooling_degree_hours', 'heating_degree_hours',
        'temp_humidity_interaction',
        'load_lag_1h', 'load_lag_24h', 'temp_lag_1h',
        'sin_hour', 'cos_hour', 'sin_day_of_year', 'cos_day_of_year'
    ]
    
    if all(col in historical.columns for col in feature_columns):
        X_hist = historical[feature_columns]
        historical['predicted_load'] = predictor_model.predict(X_hist)
    
    # Convert to JSON-serializable format
    result = []
    for _, row in historical.iterrows():
        result.append({
            'timestamp': row['timestamp'].isoformat(),
            'actual_load': float(row['load']),
            'predicted_load': float(row.get('predicted_load', 0)),
            'temperature': float(row['temp_c']),
            'humidity': float(row['humidity'])
        })
    
    return result

if __name__ == "__main__":
    print("🚀 Starting Power Demand Prediction API Server...")
    print("📡 This will serve data to your Fly.io dashboard")
    print("🔗 API will be available at: http://localhost:8000")
    print("📚 API docs at: http://localhost:8000/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",  # Allow external connections
        port=8000,
        reload=False  # Disable reload to avoid import issues
    )
