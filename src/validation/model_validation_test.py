#!/usr/bin/env python3
"""
Model Validation Test for Evening Peak Improvements

Tests the newly trained models against the original problem:
- Current prediction: 20,765 MW 
- Actual load: 22,782 MW
- Target improvement: Address 9.7% underestimation
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import json

logger = logging.getLogger(__name__)

class ModelValidationTest:
    """Test improved models against current evening peak conditions."""
    
    def __init__(self, models_dir: str = "production_models"):
        """
        Initialize model validation test.
        
        Args:
            models_dir: Directory containing trained models
        """
        self.models_dir = Path(models_dir)
        
        # Original problem data
        self.baseline_predictions = {'SCE': 16427, 'SP15': 4338}  # Total: 20,765 MW
        self.actual_current_load = 22782  # MW
        self.current_conditions = {
            'temperature': 82.4,  # °F (from API: 28°C converted)
            'hour': 19,           # 7 PM Pacific (current time was 20:30)
            'weekday': 0,         # Monday
            'month': 9,           # September
        }
        
    def load_zone_models(self, zone: str) -> Dict[str, Any]:
        """Load all models for a specific zone."""
        zone_dir = self.models_dir / zone
        
        if not zone_dir.exists():
            raise FileNotFoundError(f"Models directory not found for zone: {zone}")
        
        models = {}
        
        # Load each model type
        for model_type in ['baseline_xgb', 'enhanced_xgb', 'lightgbm']:
            model_file = zone_dir / f"{model_type}_model.pkl"
            
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    models[model_type] = pickle.load(f)
                logger.info(f"Loaded {zone} {model_type} model")
            else:
                logger.warning(f"Model file not found: {model_file}")
        
        # Load metadata
        metadata_file = zone_dir / "model_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                models['metadata'] = json.load(f)
        
        return models
    
    def create_current_conditions_features(self, zone: str) -> np.ndarray:
        """Create feature vector representing current conditions."""
        # This is a simplified version - in practice you'd need the exact same
        # feature engineering pipeline used in training
        
        # Basic temporal features
        hour = self.current_conditions['hour']
        weekday = self.current_conditions['weekday']  
        month = self.current_conditions['month']
        
        # Cyclical encodings
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * weekday / 7)
        day_cos = np.cos(2 * np.pi * weekday / 7)
        month_sin = np.sin(2 * np.pi * month / 12)
        month_cos = np.cos(2 * np.pi * month / 12)
        
        # Evening-specific features
        is_evening_peak = 1 if 17 <= hour <= 21 else 0
        evening_hour_intensity = (hour - 17) / 4 if is_evening_peak else 0
        hours_from_peak = abs(hour - 18) / 24
        evening_ramp = max(0, (hour - 15) / 4) if 15 <= hour <= 19 else 0
        post_peak_decline = (23 - hour) / 2 if 21 <= hour <= 23 else 0
        
        # Weather features (simplified - no actual temp data in training)
        temp_evening_interaction = 0  # Would be temperature * is_evening_peak
        cooling_degree_hour = 0       # Would be max(temp - 75, 0)
        evening_cooling_demand = 0    # Complex calculation
        
        # Lag features (would need actual recent load data)
        load_lag_1h = self.baseline_predictions[zone]  # Use baseline as proxy
        load_lag_2h = self.baseline_predictions[zone]  # Use baseline as proxy
        load_ma_4h = self.baseline_predictions[zone]   # Use baseline as proxy
        load_ma_8h = self.baseline_predictions[zone]   # Use baseline as proxy
        load_daily_change = 0.0
        load_day_over_day = 0.0
        temp_lag_1h = 0.0
        temp_lag_2h = 0.0
        
        # Demand pattern features
        days_since_start = 400  # Approximate for recent data
        weekend_flag = 1 if weekday >= 5 else 0
        near_holiday = 0
        is_summer_month = 1 if month in [6, 7, 8, 9] else 0
        work_evening_overlap = 1 if (17 <= hour <= 19) and (weekday < 5) else 0
        
        # Zone-specific features
        zone_multipliers = {'SCE': 1.15, 'SP15': 1.08}
        zone_evening_multiplier = zone_multipliers.get(zone, 1.0)
        zone_adjusted_evening = is_evening_peak * zone_evening_multiplier
        
        zone_growth_factors = {'SCE': 0.02, 'SP15': 0.015}
        zone_growth_factor = zone_growth_factors.get(zone, 0.0)
        zone_growth_effect = days_since_start * zone_growth_factor / 365
        
        # Assemble feature vector (31 features to match training)
        features = np.array([
            hour_sin, hour_cos, day_sin, day_cos, month_sin, month_cos,
            is_evening_peak, evening_hour_intensity, hours_from_peak,
            evening_ramp, post_peak_decline, temp_evening_interaction,
            cooling_degree_hour, evening_cooling_demand,
            load_lag_1h, load_lag_2h, load_ma_4h, load_ma_8h,
            load_daily_change, load_day_over_day, temp_lag_1h, temp_lag_2h,
            days_since_start, weekend_flag, near_holiday, is_summer_month,
            work_evening_overlap, zone_evening_multiplier, zone_adjusted_evening,
            zone_growth_factor, zone_growth_effect
        ])
        
        return features.reshape(1, -1)  # Shape for single prediction
    
    def create_ensemble_prediction(self, models: Dict[str, Any], features: np.ndarray) -> float:
        """Create ensemble prediction using trained models."""
        # Get ensemble weights from metadata or use defaults
        if 'metadata' in models and 'ensemble_config' in models['metadata']:
            config = models['metadata']['ensemble_config']
        else:
            config = {
                'baseline_xgb_weight': 0.20,
                'enhanced_xgb_weight': 0.40,
                'lightgbm_weight': 0.40
            }
        
        # Make individual predictions
        predictions = {}
        for model_type in ['baseline_xgb', 'enhanced_xgb', 'lightgbm']:
            if model_type in models:
                try:
                    pred = models[model_type].predict(features)[0]
                    predictions[model_type] = pred
                    logger.info(f"{model_type} prediction: {pred:.2f}")
                except Exception as e:
                    logger.warning(f"Failed to predict with {model_type}: {e}")
                    predictions[model_type] = 0.0
        
        # Create ensemble prediction
        ensemble_pred = (
            config['baseline_xgb_weight'] * predictions.get('baseline_xgb', 0) +
            config['enhanced_xgb_weight'] * predictions.get('enhanced_xgb', 0) +
            config['lightgbm_weight'] * predictions.get('lightgbm', 0)
        )
        
        return ensemble_pred
    
    def test_improved_predictions(self) -> Dict[str, float]:
        """Test improved models against current conditions."""
        logger.info("Testing improved models against current evening peak conditions")
        logger.info(f"Current conditions: {self.current_conditions}")
        logger.info(f"Baseline predictions: {self.baseline_predictions}")
        logger.info(f"Actual load: {self.actual_current_load} MW")
        
        improved_predictions = {}
        
        for zone in ['SCE', 'SP15']:
            try:
                logger.info(f"Testing {zone} zone models...")
                
                # Load trained models
                models = self.load_zone_models(zone)
                
                # Create feature vector for current conditions
                features = self.create_current_conditions_features(zone)
                
                # Make ensemble prediction
                prediction = self.create_ensemble_prediction(models, features)
                improved_predictions[zone] = prediction
                
                logger.info(f"{zone} improved prediction: {prediction:.2f} MW")
                
            except Exception as e:
                logger.error(f"Failed to test {zone} models: {e}")
                # Fallback to baseline prediction
                improved_predictions[zone] = self.baseline_predictions[zone]
        
        return improved_predictions
    
    def calculate_improvement_metrics(self, improved_predictions: Dict[str, float]) -> Dict[str, float]:
        """Calculate improvement metrics against baseline."""
        baseline_total = sum(self.baseline_predictions.values())
        improved_total = sum(improved_predictions.values())
        
        # Calculate errors
        baseline_error = ((baseline_total - self.actual_current_load) / self.actual_current_load) * 100
        improved_error = ((improved_total - self.actual_current_load) / self.actual_current_load) * 100
        
        # Calculate improvements
        error_reduction = abs(baseline_error) - abs(improved_error)
        accuracy_improvement = baseline_total / improved_total if improved_total > 0 else 1.0
        
        metrics = {
            'baseline_total_mw': baseline_total,
            'improved_total_mw': improved_total,
            'actual_load_mw': self.actual_current_load,
            'baseline_error_pct': baseline_error,
            'improved_error_pct': improved_error,
            'error_reduction_pct': error_reduction,
            'accuracy_improvement_ratio': accuracy_improvement,
            'target_met': abs(improved_error) < abs(baseline_error)
        }
        
        return metrics

def validate_improved_models():
    """Execute comprehensive model validation test."""
    print("=== Model Validation Test for Evening Peak Improvements ===")
    
    validator = ModelValidationTest()
    
    print("\nOriginal Problem:")
    print(f"  Baseline prediction: {sum(validator.baseline_predictions.values()):,} MW")
    print(f"  Actual current load: {validator.actual_current_load:,} MW") 
    print(f"  Original error: {((sum(validator.baseline_predictions.values()) - validator.actual_current_load) / validator.actual_current_load) * 100:.1f}%")
    
    print(f"\nCurrent Conditions:")
    print(f"  Temperature: {validator.current_conditions['temperature']}°F")
    print(f"  Time: {validator.current_conditions['hour']}:00 (evening peak)")
    print(f"  Day: {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][validator.current_conditions['weekday']]}")
    
    try:
        print("\nTesting Improved Models...")
        improved_predictions = validator.test_improved_predictions()
        
        print("\nImproved Predictions:")
        for zone, prediction in improved_predictions.items():
            baseline = validator.baseline_predictions[zone]
            change = ((prediction - baseline) / baseline) * 100
            print(f"  {zone}: {baseline:,} MW → {prediction:.0f} MW ({change:+.1f}%)")
        
        print("\nLA_METRO Combined Results:")
        metrics = validator.calculate_improvement_metrics(improved_predictions)
        
        print(f"  Baseline total: {metrics['baseline_total_mw']:,.0f} MW")
        print(f"  Improved total: {metrics['improved_total_mw']:,.0f} MW")
        print(f"  Actual load: {metrics['actual_load_mw']:,} MW")
        print(f"  Baseline error: {metrics['baseline_error_pct']:.1f}%")
        print(f"  Improved error: {metrics['improved_error_pct']:.1f}%")
        print(f"  Error reduction: {metrics['error_reduction_pct']:.1f} percentage points")
        
        if metrics['target_met']:
            print("✅ SUCCESS: Improved models reduce evening peak prediction error!")
        else:
            print("⚠️  PARTIAL: Models show changes but may need further tuning")
            
        print("\nRecommendations:")
        if abs(metrics['improved_error_pct']) < 5.0:
            print("🎯 Excellent: Prediction error now under 5%")
        elif metrics['error_reduction_pct'] > 2.0:
            print("👍 Good: Significant error reduction achieved")
        else:
            print("🔧 Consider: Additional model tuning or feature engineering")
            
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    validate_improved_models()