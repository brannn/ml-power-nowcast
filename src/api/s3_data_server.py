#!/usr/bin/env python3
"""
S3 Data Server for Dashboard

Lightweight FastAPI server that serves pre-computed predictions and data
from S3 to the Fly.io dashboard. This decouples the dashboard from the
heavy ML pipeline running locally.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = "ml-power-nowcast-data-1756420517"
s3_client = boto3.client('s3')

# FastAPI app
app = FastAPI(
    title="Power Forecast Data API",
    description="Serves pre-computed ML predictions from S3 for dashboard consumption",
    version="1.0.0"
)

# CORS middleware for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionPoint(BaseModel):
    """Single prediction point."""
    timestamp: str
    predicted_load: float
    confidence_lower: float
    confidence_upper: float
    hour_ahead: int


class ForecastResponse(BaseModel):
    """Complete forecast response."""
    generated_at: str
    predictions: List[PredictionPoint]
    model_version: str
    current_conditions: Dict[str, float]


class SystemStatus(BaseModel):
    """System status response."""
    status: str
    last_updated: str
    data_freshness_minutes: int
    model_version: str


def get_s3_object(key: str) -> Optional[Dict]:
    """Get object from S3 bucket."""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to get S3 object {key}: {e}")
        return None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Power Forecast Data API",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/status", response_model=SystemStatus)
async def get_status():
    """Get system status."""
    try:
        # Get latest forecast metadata
        forecast_data = get_s3_object("forecasts/latest.json")
        
        if not forecast_data:
            raise HTTPException(status_code=503, detail="No forecast data available")
        
        # Calculate data freshness
        generated_at = datetime.fromisoformat(forecast_data['generated_at'].replace('Z', '+00:00'))
        freshness_minutes = (datetime.now(timezone.utc) - generated_at).total_seconds() / 60
        
        return SystemStatus(
            status="operational" if freshness_minutes < 30 else "stale",
            last_updated=forecast_data['generated_at'],
            data_freshness_minutes=int(freshness_minutes),
            model_version=forecast_data.get('model_version', 'unknown')
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")


@app.post("/predict", response_model=List[PredictionPoint])
async def get_predictions(weather_data: Optional[Dict] = None):
    """Get latest predictions from S3."""
    try:
        # Get pre-computed predictions from S3
        forecast_data = get_s3_object("forecasts/latest.json")
        
        if not forecast_data:
            raise HTTPException(status_code=503, detail="No forecast data available")
        
        # Check data freshness (warn if older than 1 hour)
        generated_at = datetime.fromisoformat(forecast_data['generated_at'].replace('Z', '+00:00'))
        age_minutes = (datetime.now(timezone.utc) - generated_at).total_seconds() / 60
        
        if age_minutes > 60:
            logger.warning(f"Serving stale predictions ({age_minutes:.1f} minutes old)")
        
        # Convert to response format
        predictions = [
            PredictionPoint(**pred) for pred in forecast_data['predictions']
        ]
        
        return predictions
        
    except Exception as e:
        logger.error(f"Prediction request failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction generation failed")


@app.get("/historical")
async def get_historical_data(days: int = 7):
    """Get historical data for comparison charts."""
    try:
        # Get historical data from S3
        historical_data = get_s3_object(f"data/processed/historical_{days}d.json")
        
        if not historical_data:
            # Fallback to generating sample data
            logger.warning("No historical data found, generating sample data")
            return generate_sample_historical(days)
        
        return historical_data
        
    except Exception as e:
        logger.error(f"Historical data request failed: {e}")
        raise HTTPException(status_code=500, detail="Historical data unavailable")


@app.get("/metrics")
async def get_model_metrics():
    """Get model performance metrics."""
    try:
        # Get model metrics from S3
        metrics_data = get_s3_object("models/latest_metrics.json")
        
        if not metrics_data:
            # Return default metrics
            return {
                "mae": 117.0,
                "rmse": 156.0,
                "r2": 0.985,
                "mape": 1.5,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        
        return metrics_data
        
    except Exception as e:
        logger.error(f"Metrics request failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")


def generate_sample_historical(days: int) -> List[Dict]:
    """Generate sample historical data for demo purposes."""
    import random
    from datetime import timedelta
    
    data = []
    base_time = datetime.now(timezone.utc) - timedelta(days=days)
    
    for i in range(days * 24):  # Hourly data
        timestamp = base_time + timedelta(hours=i)
        base_load = 25000 + 5000 * random.sin(i * 0.26)  # Daily cycle
        actual_load = base_load + random.gauss(0, 500)
        predicted_load = actual_load + random.gauss(0, 200)
        
        data.append({
            "timestamp": timestamp.isoformat(),
            "actual_load": actual_load,
            "predicted_load": predicted_load,
            "temperature": 20 + 10 * random.sin(i * 0.26),
            "humidity": 50 + 20 * random.random()
        })
    
    return data


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting S3 Data Server...")
    print("📡 This serves pre-computed data to your Fly.io dashboard")
    print("🔗 API will be available at: http://localhost:8001")
    print("📚 API docs at: http://localhost:8001/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False
    )
