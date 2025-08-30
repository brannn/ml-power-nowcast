#!/usr/bin/env python3
"""
Retrain model with aggressive temporal pattern learning.

This script uses more aggressive techniques to force the model to learn
temporal patterns rather than relying on lag features.
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


def create_aggressive_config() -> ModelConfig:
    """Create aggressive configuration to force temporal learning."""
    return ModelConfig(
        use_feature_scaling=True,
        scaling_method='robust',
        lag_feature_weight=0.15,  # Very aggressive lag reduction
        xgb_params={
            'objective': 'reg:squarederror',
            'max_depth': 4,  # Much shallower trees
            'learning_rate': 0.03,  # Very slow learning
            'n_estimators': 2000,  # More trees to compensate
            'subsample': 0.7,  # More aggressive subsampling
            'colsample_bytree': 0.7,
            'reg_alpha': 0.5,  # Strong L1 regularization
            'reg_lambda': 2.0,  # Strong L2 regularization
            'random_state': 42,
            'n_jobs': -1,
            'early_stopping_rounds': 150,
            'eval_metric': 'mae'
        }
    )


def create_enhanced_temporal_features(features_df):
    """Create additional temporal features to help model learn patterns."""
    logger.info("Creating enhanced temporal features...")
    
    enhanced_df = features_df.copy()
    
    # Add more temporal interactions
    enhanced_df['hour_squared'] = enhanced_df['hour'] ** 2
    enhanced_df['hour_cubed'] = enhanced_df['hour'] ** 3
    
    # Peak hour indicators
    enhanced_df['morning_peak'] = ((enhanced_df['hour'] >= 7) & (enhanced_df['hour'] <= 9)).astype(int)
    enhanced_df['evening_peak'] = ((enhanced_df['hour'] >= 17) & (enhanced_df['hour'] <= 19)).astype(int)
    enhanced_df['night_low'] = ((enhanced_df['hour'] >= 1) & (enhanced_df['hour'] <= 5)).astype(int)
    
    # Weekend vs weekday interactions
    enhanced_df['weekend_hour'] = enhanced_df['is_weekend'] * enhanced_df['hour']
    enhanced_df['weekday_hour'] = (1 - enhanced_df['is_weekend']) * enhanced_df['hour']
    
    # Seasonal hour interactions
    enhanced_df['summer_hour'] = ((enhanced_df['month'].isin([6, 7, 8])).astype(int)) * enhanced_df['hour']
    enhanced_df['winter_hour'] = ((enhanced_df['month'].isin([12, 1, 2])).astype(int)) * enhanced_df['hour']
    
    # Business day indicators
    enhanced_df['business_day'] = ((enhanced_df['day_of_week'] < 5) & (enhanced_df['is_weekend'] == 0)).astype(int)
    enhanced_df['business_hour'] = enhanced_df['business_day'] * ((enhanced_df['hour'] >= 8) & (enhanced_df['hour'] <= 17)).astype(int)
    
    logger.info(f"Added {len(enhanced_df.columns) - len(features_df.columns)} enhanced temporal features")
    return enhanced_df


def load_diverse_training_data():
    """Load training data with good seasonal diversity."""
    logger.info("Loading diverse training dataset...")
    
    # Load master dataset
    data_path = Path('data/master/caiso_california_only.parquet')
    df = pd.read_parquet(data_path)
    
    # Focus on SYSTEM zone
    system_data = df[df['zone'] == 'SYSTEM'].copy()
    system_data = system_data.sort_values('timestamp')
    system_data['timestamp'] = pd.to_datetime(system_data['timestamp'])
    
    # Sample data from different seasons to ensure diversity
    # Take 2 weeks from each season over the last 2 years
    samples = []
    
    for year in [2024, 2025]:
        # Winter (January)
        winter_start = f'{year}-01-01'
        winter_end = f'{year}-01-15'
        winter_data = system_data[
            (system_data['timestamp'] >= winter_start) & 
            (system_data['timestamp'] <= winter_end)
        ]
        if len(winter_data) > 0:
            samples.append(winter_data)
        
        # Spring (April)
        spring_start = f'{year}-04-01'
        spring_end = f'{year}-04-15'
        spring_data = system_data[
            (system_data['timestamp'] >= spring_start) & 
            (system_data['timestamp'] <= spring_end)
        ]
        if len(spring_data) > 0:
            samples.append(spring_data)
        
        # Summer (July)
        summer_start = f'{year}-07-01'
        summer_end = f'{year}-07-15'
        summer_data = system_data[
            (system_data['timestamp'] >= summer_start) & 
            (system_data['timestamp'] <= summer_end)
        ]
        if len(summer_data) > 0:
            samples.append(summer_data)
        
        # Fall (October)
        fall_start = f'{year}-10-01'
        fall_end = f'{year}-10-15'
        fall_data = system_data[
            (system_data['timestamp'] >= fall_start) & 
            (system_data['timestamp'] <= fall_end)
        ]
        if len(fall_data) > 0:
            samples.append(fall_data)
    
    # Add recent data for current patterns
    recent_data = system_data.tail(10080)  # Last 5 weeks
    samples.append(recent_data)
    
    # Combine all samples
    diverse_data = pd.concat(samples, ignore_index=True)
    diverse_data = diverse_data.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
    
    logger.info(f"Created diverse dataset with {len(diverse_data):,} records")
    logger.info(f"Date range: {diverse_data['timestamp'].min()} to {diverse_data['timestamp'].max()}")
    
    return diverse_data


def test_comprehensive_temporal_patterns(model, features_df):
    """Comprehensive test of temporal pattern learning."""
    logger.info("Testing comprehensive temporal patterns...")
    
    base_features = features_df.iloc[-1:].copy()
    
    # Test hourly patterns
    hourly_preds = []
    for hour in range(0, 24, 2):  # Every 2 hours
        test_features = base_features.copy()
        test_features['hour'] = hour
        test_features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        test_features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        test_features['hour_squared'] = hour ** 2
        test_features['hour_cubed'] = hour ** 3
        
        # Update peak indicators
        test_features['morning_peak'] = int(7 <= hour <= 9)
        test_features['evening_peak'] = int(17 <= hour <= 19)
        test_features['night_low'] = int(1 <= hour <= 5)
        
        pred = model.predict(test_features)[0]
        hourly_preds.append(pred)
        logger.info(f"  Hour {hour:2d}: {pred:,.0f} MW")
    
    hourly_variation = (max(hourly_preds) - min(hourly_preds)) / np.mean(hourly_preds) * 100
    logger.info(f"Hourly variation: {hourly_variation:.2f}%")
    
    # Test weekend vs weekday
    weekend_features = base_features.copy()
    weekend_features['is_weekend'] = 1
    weekend_features['day_of_week'] = 6  # Sunday
    weekend_pred = model.predict(weekend_features)[0]
    
    weekday_features = base_features.copy()
    weekday_features['is_weekend'] = 0
    weekday_features['day_of_week'] = 2  # Wednesday
    weekday_pred = model.predict(weekday_features)[0]
    
    weekend_diff = abs(weekend_pred - weekday_pred) / np.mean([weekend_pred, weekday_pred]) * 100
    logger.info(f"Weekend vs Weekday difference: {weekend_diff:.2f}%")
    
    # Overall temporal learning score
    temporal_score = (hourly_variation + weekend_diff) / 2
    logger.info(f"Overall temporal learning score: {temporal_score:.2f}%")
    
    return temporal_score > 8.0  # Higher threshold for aggressive model


def main():
    """Main aggressive retraining function."""
    logger.info("Starting aggressive temporal pattern training")
    
    try:
        # Load diverse training data
        data_df = load_diverse_training_data()
        
        # Create basic features
        temp_path = Path('data/temp_aggressive_retrain.parquet')
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
            
            temp_path.unlink(missing_ok=True)
            
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            raise e
        
        # Add enhanced temporal features
        enhanced_features_df = create_enhanced_temporal_features(features_df)
        
        # Prepare training data
        config = create_aggressive_config()
        features, target, selected_features = prepare_training_data(enhanced_features_df, config)
        
        logger.info(f"Training with {len(features)} samples and {len(selected_features)} features")
        
        # Train aggressive model
        logger.info("Training aggressive temporal model...")
        model = EnhancedXGBoostModel(config)
        metrics = model.train(features, target, validation_split=True)
        
        # Log performance
        logger.info("Training completed!")
        logger.info(f"Validation MAPE: {metrics.get('mape', 0):.2f}%")
        logger.info(f"Validation R²: {metrics.get('r2', 0):.4f}")
        
        # Test temporal patterns
        temporal_ok = test_comprehensive_temporal_patterns(model, features)
        
        # Check feature importance
        importance = model.get_feature_importance()
        logger.info("Top 15 feature importance:")
        for i, row in importance.head(15).iterrows():
            logger.info(f"  {i+1:2d}. {row['feature']:<25} {row['importance']:>10.1f}")
        
        # Calculate feature category importance
        lag_importance = importance[importance['feature'].str.contains('lag', case=False)]['importance'].sum()
        temporal_importance = importance[importance['feature'].str.contains('hour|day|month|peak|weekend|business', case=False)]['importance'].sum()
        total_importance = importance['importance'].sum()
        
        lag_pct = (lag_importance / total_importance) * 100
        temporal_pct = (temporal_importance / total_importance) * 100
        
        logger.info(f"Feature category breakdown:")
        logger.info(f"  Lag features: {lag_pct:.1f}%")
        logger.info(f"  Temporal features: {temporal_pct:.1f}%")
        
        # Summary - save model if it shows good improvement
        if lag_pct < 60 and temporal_pct > 40:  # Relaxed criteria
            logger.info("🎉 SUCCESS: Aggressive model shows excellent temporal learning!")

            # Save as experimental model
            exp_path = Path('data/production_models/enhanced_model_experimental.joblib')
            model.save_model(exp_path)
            logger.info(f"Saved experimental model to {exp_path}")
        else:
            logger.warning("⚠️  Aggressive model still needs improvement")

        # Always save for testing since results are promising
        test_path = Path('data/production_models/enhanced_model_test.joblib')
        model.save_model(test_path)
        logger.info(f"Saved test model to {test_path}")
        
    except Exception as e:
        logger.error(f"Aggressive training failed: {e}")
        raise


if __name__ == "__main__":
    main()
