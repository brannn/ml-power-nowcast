#!/usr/bin/env python3
"""
FastAPI microservice for power demand nowcasting.

Implements Section 13 of the implementation plan with MLflow model registry
integration, comprehensive error handling, and production-ready features.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any
import traceback

import mlflow
import mlflow.pyfunc
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionRequest(BaseModel):
    """Request model for nowcast predictions."""
    
    features: Dict[str, Union[float, int]] = Field(
        ..., 
        description="Feature values for prediction",
        example={
            "load_lag_1h": 1200.0,
            "load_lag_2h": 1150.0,
            "temp_c": 22.5,
            "humidity": 65.0,
            "hour": 14,
            "day_of_week": 2
        }
    )
    
    @validator('features')
    def validate_features(cls, v: Dict[str, Union[float, int]]) -> Dict[str, Union[float, int]]:
        """Validate feature dictionary."""
        if not v:
            raise ValueError("Features dictionary cannot be empty")
        
        # Check for required feature types
        numeric_types = (int, float, np.integer, np.floating)
        for key, value in v.items():
            if not isinstance(value, numeric_types):
                raise ValueError(f"Feature '{key}' must be numeric, got {type(value)}")
        
        return v


class BatchPredictionRequest(BaseModel):
    """Request model for batch predictions."""
    
    rows: List[Dict[str, Union[float, int]]] = Field(
        ...,
        description="List of feature dictionaries for batch prediction",
        min_items=1,
        max_items=1000  # Reasonable batch size limit
    )
    
    @validator('rows')
    def validate_rows(cls, v: List[Dict[str, Union[float, int]]]) -> List[Dict[str, Union[float, int]]]:
        """Validate batch rows."""
        if not v:
            raise ValueError("Rows list cannot be empty")
        
        # Validate each row
        for i, row in enumerate(v):
            if not row:
                raise ValueError(f"Row {i} cannot be empty")
            
            numeric_types = (int, float, np.integer, np.floating)
            for key, value in row.items():
                if not isinstance(value, numeric_types):
                    raise ValueError(f"Row {i}, feature '{key}' must be numeric, got {type(value)}")
        
        return v


class PredictionResponse(BaseModel):
    """Response model for predictions."""
    
    prediction: float = Field(..., description="Predicted power demand in MW")
    model_name: str = Field(..., description="Name of the model used")
    model_version: str = Field(..., description="Version of the model used")
    timestamp: str = Field(..., description="Prediction timestamp (ISO format)")
    horizon_hours: int = Field(..., description="Forecast horizon in hours")


class BatchPredictionResponse(BaseModel):
    """Response model for batch predictions."""
    
    predictions: List[float] = Field(..., description="List of predicted power demands in MW")
    model_name: str = Field(..., description="Name of the model used")
    model_version: str = Field(..., description="Version of the model used")
    timestamp: str = Field(..., description="Prediction timestamp (ISO format)")
    horizon_hours: int = Field(..., description="Forecast horizon in hours")
    count: int = Field(..., description="Number of predictions made")


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    model_name: Optional[str] = Field(None, description="Loaded model name")
    model_version: Optional[str] = Field(None, description="Loaded model version")
    timestamp: str = Field(..., description="Health check timestamp")


class ModelManager:
    """Manages MLflow model loading and caching."""
    
    def __init__(self, model_name: str = "power-nowcast", model_stage: str = "Production"):
        self.model_name = model_name
        self.model_stage = model_stage
        self.model = None
        self.model_version = None
        self.model_metadata = {}
        self.last_loaded = None
        
    def load_model(self) -> None:
        """Load model from MLflow registry."""
        try:
            model_uri = f"models:/{self.model_name}/{self.model_stage}"
            logger.info(f"Loading model from {model_uri}")
            
            # Load model
            self.model = mlflow.pyfunc.load_model(model_uri)
            
            # Get model metadata
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            
            try:
                model_versions = client.get_latest_versions(self.model_name, stages=[self.model_stage])
                if model_versions:
                    model_version = model_versions[0]
                    self.model_version = model_version.version
                    self.model_metadata = {
                        "name": self.model_name,
                        "version": model_version.version,
                        "stage": model_version.current_stage,
                        "run_id": model_version.run_id,
                        "creation_timestamp": str(model_version.creation_timestamp)
                    }
                else:
                    self.model_version = "unknown"
                    self.model_metadata = {"name": self.model_name, "version": "unknown"}
            except Exception as e:
                logger.warning(f"Could not get model metadata: {e}")
                self.model_version = "unknown"
                self.model_metadata = {"name": self.model_name, "version": "unknown"}
            
            self.last_loaded = datetime.now(timezone.utc)
            logger.info(f"Successfully loaded model {self.model_name} v{self.model_version}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Could not load model {self.model_name} from {self.model_stage}: {e}")
    
    def predict(self, features_df: pd.DataFrame) -> np.ndarray:
        """Make predictions using loaded model."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            predictions = self.model.predict(features_df)
            return predictions
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise RuntimeError(f"Prediction failed: {e}")
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None


# Global model manager
model_manager = ModelManager(
    model_name=os.getenv("MODEL_NAME", "power-nowcast"),
    model_stage=os.getenv("MODEL_STAGE", "Production")
)

# FastAPI app
app = FastAPI(
    title="Power Nowcast API",
    description="Real-time power demand forecasting API using MLflow models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_model_manager() -> ModelManager:
    """Dependency to get model manager."""
    return model_manager


@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    try:
        logger.info("Starting Power Nowcast API...")
        model_manager.load_model()
        logger.info("API startup completed successfully")
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        # Don't raise here - let the app start and handle errors in endpoints


@app.get("/health", response_model=HealthResponse)
async def health_check(manager: ModelManager = Depends(get_model_manager)) -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if manager.is_loaded() else "unhealthy",
        model_loaded=manager.is_loaded(),
        model_name=manager.model_name if manager.is_loaded() else None,
        model_version=manager.model_version if manager.is_loaded() else None,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/nowcast", response_model=PredictionResponse)
async def nowcast(
    request: PredictionRequest,
    manager: ModelManager = Depends(get_model_manager)
) -> PredictionResponse:
    """
    Generate power demand nowcast for a single set of features.
    
    Args:
        request: Prediction request with feature values
        
    Returns:
        Prediction response with forecasted demand
    """
    if not manager.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Check service health."
        )
    
    try:
        # Convert features to DataFrame
        features_df = pd.DataFrame([request.features])
        
        # Make prediction
        prediction = manager.predict(features_df)[0]
        
        # Ensure prediction is a Python float
        if isinstance(prediction, np.ndarray):
            prediction = float(prediction.item())
        else:
            prediction = float(prediction)
        
        return PredictionResponse(
            prediction=prediction,
            model_name=manager.model_name,
            model_version=manager.model_version or "unknown",
            timestamp=datetime.now(timezone.utc).isoformat(),
            horizon_hours=1  # Default horizon - could be made configurable
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/nowcast/batch", response_model=BatchPredictionResponse)
async def nowcast_batch(
    request: BatchPredictionRequest,
    manager: ModelManager = Depends(get_model_manager)
) -> BatchPredictionResponse:
    """
    Generate power demand nowcasts for multiple feature sets.
    
    Args:
        request: Batch prediction request with list of feature dictionaries
        
    Returns:
        Batch prediction response with list of forecasted demands
    """
    if not manager.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Check service health."
        )
    
    try:
        # Convert features to DataFrame
        features_df = pd.DataFrame(request.rows)
        
        # Make predictions
        predictions = manager.predict(features_df)
        
        # Convert to Python floats
        predictions_list = [float(pred.item() if isinstance(pred, np.ndarray) else pred) 
                           for pred in predictions]
        
        return BatchPredictionResponse(
            predictions=predictions_list,
            model_name=manager.model_name,
            model_version=manager.model_version or "unknown",
            timestamp=datetime.now(timezone.utc).isoformat(),
            horizon_hours=1,  # Default horizon
            count=len(predictions_list)
        )
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


@app.get("/model/info")
async def model_info(manager: ModelManager = Depends(get_model_manager)) -> Dict[str, Any]:
    """Get information about the loaded model."""
    if not manager.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded"
        )
    
    return {
        "model_metadata": manager.model_metadata,
        "last_loaded": manager.last_loaded.isoformat() if manager.last_loaded else None,
        "model_stage": manager.model_stage
    }


@app.post("/model/reload")
async def reload_model(manager: ModelManager = Depends(get_model_manager)) -> Dict[str, str]:
    """Reload the model from MLflow registry."""
    try:
        manager.load_model()
        return {
            "status": "success",
            "message": f"Model {manager.model_name} v{manager.model_version} reloaded successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Model reload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model reload failed: {str(e)}"
        )


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
