#!/usr/bin/env python3
"""
Test script to compare old vs improved XGBoost model.

This script tests the improved model with feature scaling and regularization
to verify that temporal patterns are properly learned.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.models.enhanced_xgboost import (
    EnhancedXGBoostModel,
    ModelConfig,
    prepare_training_data
)
from src.features.unified_feature_pipeline import (
    build_unified_features,
    UnifiedFeatureConfig,
    ForecastFeatureConfig
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_old_model_config() -> ModelConfig:
    """Create configuration for old model (no scaling, weak regularization)."""
    return ModelConfig(
        use_feature_scaling=False,
        lag_feature_weight=1.0,  # No weighting
        xgb_params={
            'objective': 'reg:squarederror',
            'max_depth': 8,  # Deep trees
            'learning_rate': 0.1,
            'n_estimators': 500,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
            'early_stopping_rounds': 50,
            'eval_metric': 'mae'
            # No regularization
        }
    )


def create_improved_model_config() -> ModelConfig:
    """Create configuration for improved model (with scaling and regularization)."""
    return ModelConfig(
        use_feature_scaling=True,
        scaling_method='robust',
        lag_feature_weight=0.3,  # Reduce lag dominance
        xgb_params={
            'objective': 'reg:squarederror',
            'max_depth': 6,  # Shallower trees
            'learning_rate': 0.05,  # Slower learning
            'n_estimators': 1000,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,  # L1 regularization
            'reg_lambda': 1.0,  # L2 regularization
            'random_state': 42,
            'n_jobs': -1,
            'early_stopping_rounds': 50,
            'eval_metric': 'mae'
        }
    )


def load_and_prepare_data():
    """Load and prepare training data."""
    logger.info("Loading training data...")
    
    # Load master dataset
    data_path = Path('data/master/caiso_california_only.parquet')
    df = pd.read_parquet(data_path)
    
    # Focus on SYSTEM zone for testing
    system_data = df[df['zone'] == 'SYSTEM'].copy()
    system_data = system_data.sort_values('timestamp')
    
    # Take recent data for faster testing (last 30 days)
    recent_data = system_data.tail(8640)  # 30 days * 24 hours * 12 (5-min intervals)
    
    logger.info(f"Using {len(recent_data):,} records for testing")
    
    # Create features using unified pipeline
    temp_path = Path('data/temp_model_test.parquet')
    recent_data.to_parquet(temp_path, index=False)
    
    try:
        config = UnifiedFeatureConfig(
            forecast_config=ForecastFeatureConfig(
                forecast_horizons=[6, 24],
                base_temperature=18.0
            ),
            include_lag_features=True,
            lag_hours=[1, 24],
            include_temporal_features=True,
            include_weather_interactions=False,
            target_zones=['SYSTEM']
        )
        
        features_df = build_unified_features(
            power_data_path=temp_path,
            weather_data_path=None,
            forecast_data_dir=None,
            config=config
        )
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        
        return features_df
        
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise e


def test_model_predictions(model, features_df, model_name):
    """Test model predictions for temporal patterns."""
    logger.info(f"Testing {model_name} predictions...")
    
    # Create test scenarios for different hours
    test_hours = [6, 12, 18, 22]  # Morning, noon, evening, night
    base_features = features_df.iloc[-1:].copy()  # Use latest features as base
    
    predictions = []
    for hour in test_hours:
        test_features = base_features.copy()
        test_features['hour'] = hour
        test_features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        test_features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        
        pred = model.predict(test_features)[0]
        predictions.append(pred)
        logger.info(f"  Hour {hour:2d}: {pred:,.0f} MW")
    
    # Calculate variation
    min_pred = min(predictions)
    max_pred = max(predictions)
    variation = (max_pred - min_pred) / np.mean(predictions) * 100
    
    logger.info(f"  Prediction variation: {variation:.2f}%")
    return variation


def compare_feature_importance(old_model, improved_model):
    """Compare feature importance between models."""
    logger.info("Comparing feature importance...")
    
    old_importance = old_model.get_feature_importance()
    improved_importance = improved_model.get_feature_importance()
    
    # Focus on key feature categories
    categories = {
        'lag': ['lag'],
        'temporal': ['hour', 'day', 'month'],
        'weather': ['temp', 'humidity', 'wind']
    }
    
    for category, keywords in categories.items():
        old_cat_importance = old_importance[
            old_importance['feature'].str.contains('|'.join(keywords), case=False)
        ]['importance'].sum()
        
        improved_cat_importance = improved_importance[
            improved_importance['feature'].str.contains('|'.join(keywords), case=False)
        ]['importance'].sum()
        
        logger.info(f"{category.capitalize()} features:")
        logger.info(f"  Old model: {old_cat_importance:.4f}")
        logger.info(f"  Improved model: {improved_cat_importance:.4f}")


def main():
    """Main test function."""
    logger.info("Starting improved model comparison test")
    
    try:
        # Load and prepare data
        features_df = load_and_prepare_data()
        
        # Prepare training data
        old_config = create_old_model_config()
        improved_config = create_improved_model_config()
        
        old_features, target, _ = prepare_training_data(features_df, old_config)
        improved_features, _, _ = prepare_training_data(features_df, improved_config)
        
        # Train old model
        logger.info("Training old model...")
        old_model = EnhancedXGBoostModel(old_config)
        old_metrics = old_model.train(old_features, target, validation_split=True)
        
        # Train improved model
        logger.info("Training improved model...")
        improved_model = EnhancedXGBoostModel(improved_config)
        improved_metrics = improved_model.train(improved_features, target, validation_split=True)
        
        # Compare performance
        logger.info("\n" + "="*50)
        logger.info("PERFORMANCE COMPARISON")
        logger.info("="*50)
        
        logger.info(f"Old Model MAPE: {old_metrics.get('mape', 0):.2f}%")
        logger.info(f"Improved Model MAPE: {improved_metrics.get('mape', 0):.2f}%")
        
        # Test temporal pattern learning
        logger.info("\n" + "="*50)
        logger.info("TEMPORAL PATTERN TESTING")
        logger.info("="*50)
        
        old_variation = test_model_predictions(old_model, old_features, "Old Model")
        improved_variation = test_model_predictions(improved_model, improved_features, "Improved Model")
        
        # Compare feature importance
        logger.info("\n" + "="*50)
        logger.info("FEATURE IMPORTANCE COMPARISON")
        logger.info("="*50)
        
        compare_feature_importance(old_model, improved_model)
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("SUMMARY")
        logger.info("="*50)
        
        if improved_variation > old_variation * 2:
            logger.info("✅ SUCCESS: Improved model shows better temporal variation")
        else:
            logger.info("❌ ISSUE: Improved model still shows flat predictions")
            
        logger.info(f"Old model temporal variation: {old_variation:.2f}%")
        logger.info(f"Improved model temporal variation: {improved_variation:.2f}%")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
