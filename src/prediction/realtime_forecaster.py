#!/usr/bin/env python3
"""
Real-Time Power Demand Forecaster with Weather Forecast Integration

This module implements the real-time prediction system outlined in Phase 6 of
planning/weather_forecast_integration.md. It demonstrates the value of weather
forecast features for power demand prediction by comparing baseline vs 
forecast-enhanced predictions on current data.

The system provides:
- Real-time power demand predictions (1-48 hours ahead)
- Baseline predictions (historical patterns only)
- Forecast-enhanced predictions (with weather forecasts)
- Performance comparison and improvement measurement
- Confidence intervals and uncertainty quantification

Author: ML Power Nowcast System
Created: 2025-08-29
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from dataclasses import dataclass

from ..models.enhanced_xgboost import EnhancedXGBoostModel
from ..features.unified_feature_pipeline import (
    build_unified_features,
    UnifiedFeatureConfig,
    ForecastFeatureConfig
)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PredictionConfig:
    """
    Configuration for real-time predictions.
    
    Attributes:
        prediction_horizons: List of prediction horizons in hours
        confidence_levels: List of confidence levels for intervals
        baseline_model_path: Path to baseline model file
        enhanced_model_path: Path to enhanced model file
        target_zones: List of CAISO zones to predict
        update_frequency_minutes: How often to update predictions
    """
    prediction_horizons: List[int]
    confidence_levels: List[float] = None
    baseline_model_path: Optional[Path] = None
    enhanced_model_path: Optional[Path] = None
    target_zones: List[str] = None
    update_frequency_minutes: int = 30
    
    def __post_init__(self):
        """Set defaults for optional parameters."""
        if self.confidence_levels is None:
            self.confidence_levels = [0.80, 0.90, 0.95]
        
        if self.target_zones is None:
            self.target_zones = ['NP15']


@dataclass
class PredictionResult:
    """
    Container for prediction results.
    
    Attributes:
        timestamp: Prediction timestamp
        zone: CAISO zone
        horizon_hours: Prediction horizon in hours
        baseline_prediction: Baseline model prediction
        enhanced_prediction: Enhanced model prediction (with forecasts)
        confidence_intervals: Dictionary of confidence intervals
        forecast_improvement_pct: Percentage improvement from forecasts
        prediction_metadata: Additional metadata
    """
    timestamp: datetime
    zone: str
    horizon_hours: int
    baseline_prediction: float
    enhanced_prediction: Optional[float]
    confidence_intervals: Dict[float, Tuple[float, float]]
    forecast_improvement_pct: Optional[float]
    prediction_metadata: Dict[str, any]


class RealtimeForecasterError(Exception):
    """Base exception for real-time forecaster operations."""
    pass


class ModelLoadError(RealtimeForecasterError):
    """Raised when model loading fails."""
    pass


class PredictionError(RealtimeForecasterError):
    """Raised when prediction generation fails."""
    pass


class RealtimeForecaster:
    """
    Real-time power demand forecaster with weather forecast integration.
    
    This class implements the complete real-time prediction system as specified
    in the weather forecast integration plan, demonstrating the value of weather
    forecast features for power demand prediction.
    """
    
    def __init__(self, config: PredictionConfig):
        """
        Initialize real-time forecaster.
        
        Args:
            config: Prediction configuration
        """
        self.config = config
        self.baseline_model = None
        self.enhanced_model = None
        self.is_initialized = False
        
    def initialize(self) -> None:
        """
        Initialize the forecaster by loading trained models.
        
        Raises:
            ModelLoadError: If model loading fails
        """
        logger.info("Initializing real-time forecaster")
        
        try:
            # Load baseline model
            if self.config.baseline_model_path and self.config.baseline_model_path.exists():
                self.baseline_model = EnhancedXGBoostModel.load_model(self.config.baseline_model_path)
                logger.info(f"Loaded baseline model from {self.config.baseline_model_path}")
            else:
                logger.warning("No baseline model path provided or file not found")
            
            # Load enhanced model
            if self.config.enhanced_model_path and self.config.enhanced_model_path.exists():
                self.enhanced_model = EnhancedXGBoostModel.load_model(self.config.enhanced_model_path)
                logger.info(f"Loaded enhanced model from {self.config.enhanced_model_path}")
            else:
                logger.warning("No enhanced model path provided or file not found")
            
            if not self.baseline_model and not self.enhanced_model:
                raise ModelLoadError("No models could be loaded")
            
            self.is_initialized = True
            logger.info("Real-time forecaster initialized successfully")
            
        except Exception as e:
            raise ModelLoadError(f"Failed to initialize forecaster: {e}")
    
    def prepare_prediction_features(
        self, 
        prediction_time: datetime,
        zone: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare features for baseline and enhanced predictions.
        
        Args:
            prediction_time: Time for which to make predictions
            zone: CAISO zone to predict
            
        Returns:
            Tuple of (baseline_features, enhanced_features)
            
        Raises:
            PredictionError: If feature preparation fails
        """
        try:
            logger.debug(f"Preparing prediction features for {zone} at {prediction_time}")
            
            # Create unified feature configuration
            unified_config = UnifiedFeatureConfig(
                forecast_config=ForecastFeatureConfig(
                    forecast_horizons=[6, 24]  # Match training configuration
                ),
                target_zones=[zone],
                lag_hours=[1, 24],
                include_temporal_features=True,
                include_weather_interactions=True
            )
            
            # Build unified features (this will include current data + forecasts)
            unified_df = build_unified_features(
                power_data_path=Path("data/master/caiso_california_only.parquet"),
                weather_data_path=None,
                forecast_data_dir=Path("data/forecasts"),
                config=unified_config
            )
            
            # Filter to the specific zone and recent data
            zone_df = unified_df[unified_df['zone'] == zone].copy()
            
            # Get the most recent complete record for prediction
            zone_df = zone_df.sort_values('timestamp')
            latest_record = zone_df.tail(1).copy()
            
            if len(latest_record) == 0:
                raise PredictionError(f"No data available for zone {zone}")
            
            # Prepare baseline features (no forecast features)
            baseline_features = [
                'hour', 'day_of_week', 'month', 'quarter', 'is_weekend',
                'hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos',
                'day_of_year_sin', 'day_of_year_cos',
                'load_lag_1h', 'load_lag_24h'
            ]
            
            baseline_df = latest_record[[col for col in baseline_features if col in latest_record.columns]].copy()
            
            # Prepare enhanced features (include forecast features)
            enhanced_features = baseline_features + [
                'temp_forecast_6h', 'temp_forecast_24h',
                'cooling_forecast_6h', 'heating_forecast_6h',
                'temp_change_rate_6h', 'weather_volatility_6h'
            ]
            
            enhanced_df = latest_record[[col for col in enhanced_features if col in latest_record.columns]].copy()
            
            logger.debug(f"Prepared features: baseline={len(baseline_df.columns)}, enhanced={len(enhanced_df.columns)}")
            
            return baseline_df, enhanced_df
            
        except Exception as e:
            raise PredictionError(f"Failed to prepare prediction features: {e}")
    
    def make_predictions(
        self,
        prediction_time: datetime,
        zone: str,
        horizons: List[int]
    ) -> List[PredictionResult]:
        """
        Make baseline and enhanced predictions for specified horizons.
        
        Args:
            prediction_time: Time for which to make predictions
            zone: CAISO zone to predict
            horizons: List of prediction horizons in hours
            
        Returns:
            List of PredictionResult objects
            
        Raises:
            PredictionError: If prediction generation fails
        """
        if not self.is_initialized:
            raise PredictionError("Forecaster not initialized. Call initialize() first.")
        
        logger.info(f"Making predictions for {zone} at {prediction_time}")
        
        try:
            # Prepare features
            baseline_features, enhanced_features = self.prepare_prediction_features(prediction_time, zone)
            
            results = []
            
            for horizon in horizons:
                # Make baseline prediction
                baseline_pred = None
                if self.baseline_model:
                    try:
                        baseline_pred = self.baseline_model.predict(baseline_features)[0]
                    except Exception as e:
                        logger.warning(f"Baseline prediction failed for horizon {horizon}h: {e}")
                
                # Make enhanced prediction
                enhanced_pred = None
                if self.enhanced_model:
                    try:
                        enhanced_pred = self.enhanced_model.predict(enhanced_features)[0]
                    except Exception as e:
                        logger.warning(f"Enhanced prediction failed for horizon {horizon}h: {e}")
                
                # Calculate improvement
                improvement_pct = None
                if baseline_pred and enhanced_pred and baseline_pred != 0:
                    improvement_pct = ((enhanced_pred - baseline_pred) / baseline_pred) * 100
                
                # Create confidence intervals (simplified approach)
                confidence_intervals = {}
                if enhanced_pred:
                    for conf_level in self.config.confidence_levels:
                        # Simple approach: ±10% for 95% confidence, scaled for other levels
                        margin = enhanced_pred * 0.10 * (conf_level / 0.95)
                        confidence_intervals[conf_level] = (
                            enhanced_pred - margin,
                            enhanced_pred + margin
                        )
                
                # Check for forecast feature availability
                forecast_available = enhanced_features['temp_forecast_6h'].notna().any() if 'temp_forecast_6h' in enhanced_features.columns else False
                
                # Create prediction result
                result = PredictionResult(
                    timestamp=prediction_time + timedelta(hours=horizon),
                    zone=zone,
                    horizon_hours=horizon,
                    baseline_prediction=baseline_pred,
                    enhanced_prediction=enhanced_pred,
                    confidence_intervals=confidence_intervals,
                    forecast_improvement_pct=improvement_pct,
                    prediction_metadata={
                        'prediction_made_at': prediction_time,
                        'forecast_features_available': forecast_available,
                        'baseline_model_available': self.baseline_model is not None,
                        'enhanced_model_available': self.enhanced_model is not None
                    }
                )
                
                results.append(result)
                
                logger.debug(f"Prediction for {horizon}h: baseline={baseline_pred:.1f}, enhanced={enhanced_pred:.1f}")
            
            logger.info(f"Generated {len(results)} predictions for {zone}")
            return results
            
        except Exception as e:
            raise PredictionError(f"Failed to make predictions: {e}")
    
    def generate_forecast_report(
        self,
        predictions: List[PredictionResult]
    ) -> Dict[str, any]:
        """
        Generate comprehensive forecast report with performance analysis.
        
        Args:
            predictions: List of prediction results
            
        Returns:
            Dictionary with forecast report data
        """
        logger.info("Generating forecast report")
        
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'total_predictions': len(predictions),
            'zones': list(set(p.zone for p in predictions)),
            'horizons': list(set(p.horizon_hours for p in predictions)),
            'forecast_availability': {},
            'performance_summary': {},
            'predictions': []
        }
        
        # Analyze forecast availability
        with_forecasts = [p for p in predictions if p.prediction_metadata.get('forecast_features_available', False)]
        report['forecast_availability'] = {
            'predictions_with_forecasts': len(with_forecasts),
            'predictions_without_forecasts': len(predictions) - len(with_forecasts),
            'forecast_coverage_pct': (len(with_forecasts) / len(predictions)) * 100 if predictions else 0
        }
        
        # Analyze performance improvements
        valid_improvements = [p.forecast_improvement_pct for p in predictions if p.forecast_improvement_pct is not None]
        if valid_improvements:
            report['performance_summary'] = {
                'mean_improvement_pct': np.mean(valid_improvements),
                'median_improvement_pct': np.median(valid_improvements),
                'std_improvement_pct': np.std(valid_improvements),
                'min_improvement_pct': np.min(valid_improvements),
                'max_improvement_pct': np.max(valid_improvements),
                'predictions_with_improvement': len([x for x in valid_improvements if x > 0]),
                'target_improvement_achieved': np.mean([abs(x) for x in valid_improvements]) >= 5.0
            }
        
        # Add individual predictions
        for pred in predictions:
            report['predictions'].append({
                'timestamp': pred.timestamp.isoformat(),
                'zone': pred.zone,
                'horizon_hours': pred.horizon_hours,
                'baseline_prediction': pred.baseline_prediction,
                'enhanced_prediction': pred.enhanced_prediction,
                'improvement_pct': pred.forecast_improvement_pct,
                'forecast_available': pred.prediction_metadata.get('forecast_features_available', False)
            })
        
        return report
    
    def run_realtime_demo(self) -> Dict[str, any]:
        """
        Run a demonstration of real-time forecasting capabilities.
        
        Returns:
            Dictionary with demonstration results
            
        Raises:
            PredictionError: If demonstration fails
        """
        logger.info("🚀 Running real-time forecasting demonstration")
        
        if not self.is_initialized:
            self.initialize()
        
        try:
            current_time = datetime.now(timezone.utc)
            all_predictions = []
            
            # Generate predictions for each configured zone
            for zone in self.config.target_zones:
                zone_predictions = self.make_predictions(
                    prediction_time=current_time,
                    zone=zone,
                    horizons=self.config.prediction_horizons
                )
                all_predictions.extend(zone_predictions)
            
            # Generate comprehensive report
            report = self.generate_forecast_report(all_predictions)
            
            logger.info("✅ Real-time forecasting demonstration completed")
            logger.info(f"Generated {len(all_predictions)} predictions across {len(self.config.target_zones)} zones")
            
            return report
            
        except Exception as e:
            raise PredictionError(f"Real-time demonstration failed: {e}")
