#!/usr/bin/env python3
"""
Retrain production model with improved feature scaling and regularization.

This script retrains the production model using the full dataset with
the improved configuration to fix the flat prediction issue.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging
from datetime import datetime

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


def create_improved_production_config() -> ModelConfig:
    """Create improved configuration for production model."""
    return ModelConfig(
        use_feature_scaling=True,
        scaling_method='robust',
        lag_feature_weight=0.4,  # Slightly higher than test for stability
        xgb_params={
            'objective': 'reg:squarederror',
            'max_depth': 6,  # Reduced from 8
            'learning_rate': 0.05,  # Reduced from 0.1
            'n_estimators': 1500,  # Increased for better learning
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,  # L1 regularization
            'reg_lambda': 1.0,  # L2 regularization
            'random_state': 42,
            'n_jobs': -1,
            'early_stopping_rounds': 100,  # More patience
            'eval_metric': 'mae'
        }
    )


def load_full_training_data():
    """Load full training dataset."""
    logger.info("Loading full training dataset...")
    
    # Load master dataset
    data_path = Path('data/master/caiso_california_only.parquet')
    df = pd.read_parquet(data_path)
    
    # Focus on SYSTEM zone for statewide predictions
    system_data = df[df['zone'] == 'SYSTEM'].copy()
    system_data = system_data.sort_values('timestamp')
    
    logger.info(f"Loaded {len(system_data):,} records")
    logger.info(f"Date range: {system_data['timestamp'].min()} to {system_data['timestamp'].max()}")
    
    # Use last 6 months for training (balance between data size and training time)
    recent_data = system_data.tail(52560)  # ~6 months * 24 hours * 12 (5-min intervals) * 30 days
    logger.info(f"Using {len(recent_data):,} records for training (last 6 months)")
    
    return recent_data


def create_features(data_df):
    """Create features using unified pipeline."""
    logger.info("Creating features...")
    
    # Save to temp file for pipeline
    temp_path = Path('data/temp_production_retrain.parquet')
    data_df.to_parquet(temp_path, index=False)
    
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


def test_model_temporal_patterns(model, features_df):
    """Test if model learned proper temporal patterns."""
    logger.info("Testing temporal pattern learning...")
    
    # Create test scenarios for different hours
    test_hours = [6, 10, 14, 18, 22]  # Morning, mid-morning, afternoon, evening, night
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
    
    logger.info(f"Temporal variation: {variation:.2f}%")
    
    # Check if variation is reasonable (should be > 5% for good temporal learning)
    if variation > 5.0:
        logger.info("✅ Model shows good temporal variation")
        return True
    else:
        logger.warning("⚠️  Model shows limited temporal variation")
        return False


def backup_current_model():
    """Backup current production model."""
    current_path = Path('data/production_models/enhanced_model_current.joblib')
    if current_path.exists():
        backup_path = Path(f'data/production_models/enhanced_model_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.joblib')
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        import shutil
        shutil.copy2(current_path, backup_path)
        logger.info(f"Backed up current model to {backup_path}")
        return backup_path
    return None


def save_production_model(model, backup_path=None):
    """Save new model as production model."""
    production_path = Path('data/production_models/enhanced_model_current.joblib')
    production_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        model.save_model(production_path)
        logger.info(f"✅ New production model saved to {production_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save production model: {e}")
        
        # Restore backup if save failed
        if backup_path and backup_path.exists():
            import shutil
            shutil.copy2(backup_path, production_path)
            logger.info(f"Restored backup model from {backup_path}")
        
        return False


def main():
    """Main retraining function."""
    logger.info("Starting production model retraining")
    
    try:
        # Backup current model
        backup_path = backup_current_model()
        
        # Load training data
        data_df = load_full_training_data()
        
        # Create features
        features_df = create_features(data_df)
        
        # Prepare training data
        config = create_improved_production_config()
        features, target, selected_features = prepare_training_data(features_df, config)
        
        logger.info(f"Training with {len(features)} samples and {len(selected_features)} features")
        logger.info(f"Selected features: {selected_features}")
        
        # Train improved model
        logger.info("Training improved production model...")
        model = EnhancedXGBoostModel(config)
        metrics = model.train(features, target, validation_split=True)
        
        # Log performance
        logger.info("Training completed!")
        logger.info(f"Validation MAPE: {metrics.get('mape', 0):.2f}%")
        logger.info(f"Validation R²: {metrics.get('r2', 0):.4f}")
        
        # Test temporal patterns
        temporal_ok = test_model_temporal_patterns(model, features)
        
        # Check feature importance
        importance = model.get_feature_importance()
        logger.info("Top 10 feature importance:")
        for i, row in importance.head(10).iterrows():
            logger.info(f"  {i+1:2d}. {row['feature']:<20} {row['importance']:>10.1f}")
        
        # Calculate feature category importance
        lag_importance = importance[importance['feature'].str.contains('lag', case=False)]['importance'].sum()
        temporal_importance = importance[importance['feature'].str.contains('hour|day|month', case=False)]['importance'].sum()
        total_importance = importance['importance'].sum()
        
        lag_pct = (lag_importance / total_importance) * 100
        temporal_pct = (temporal_importance / total_importance) * 100
        
        logger.info(f"Feature category breakdown:")
        logger.info(f"  Lag features: {lag_pct:.1f}%")
        logger.info(f"  Temporal features: {temporal_pct:.1f}%")
        
        # Decide whether to deploy
        deploy_model = True
        
        if not temporal_ok:
            logger.warning("Model shows poor temporal variation")
            deploy_model = False
        
        if lag_pct > 90:
            logger.warning(f"Lag features still dominate ({lag_pct:.1f}%)")
            deploy_model = False
        
        if metrics.get('mape', 100) > 2.0:
            logger.warning(f"Model accuracy is poor (MAPE: {metrics.get('mape', 0):.2f}%)")
            deploy_model = False
        
        # Save model if it passes checks
        if deploy_model:
            if save_production_model(model, backup_path):
                logger.info("🎉 Successfully deployed improved production model!")
            else:
                logger.error("❌ Failed to deploy model")
        else:
            logger.warning("⚠️  Model did not pass quality checks - not deploying")
            logger.info("Current production model remains unchanged")
        
    except Exception as e:
        logger.error(f"Retraining failed: {e}")
        raise


if __name__ == "__main__":
    main()
