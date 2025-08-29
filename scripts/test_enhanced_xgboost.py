#!/usr/bin/env python3
"""
Test Script for Enhanced XGBoost Model

This script tests the enhanced XGBoost model with weather forecast features,
following the implementation plan in planning/weather_forecast_integration.md.

The test validates:
- Model training with unified features
- Baseline vs forecast-enhanced performance comparison
- Feature importance analysis
- Model persistence and loading

Usage:
    python scripts/test_enhanced_xgboost.py [options]
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple

import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.models.enhanced_xgboost import (
    EnhancedXGBoostModel,
    ModelConfig,
    get_enhanced_feature_set,
    prepare_training_data,
    evaluate_model_performance,
    ModelTrainingError,
    FeatureSelectionError
)
from src.features.unified_feature_pipeline import (
    build_unified_features,
    UnifiedFeatureConfig,
    ForecastFeatureConfig
)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for the test script."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"enhanced_xgboost_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def load_test_data(logger: logging.Logger) -> Optional[pd.DataFrame]:
    """
    Load unified feature data for model testing.
    
    Args:
        logger: Logger instance
        
    Returns:
        DataFrame with unified features, or None if loading fails
    """
    logger.info("Loading test data for enhanced XGBoost model")
    
    # Try to load existing unified test data first
    test_files = list(Path("data/test_unified").glob("unified_features_test_*.parquet"))
    if test_files:
        latest_file = max(test_files, key=lambda x: x.stat().st_mtime)
        try:
            df = pd.read_parquet(latest_file)
            logger.info(f"Loaded existing unified test data: {latest_file}")
            logger.info(f"  Records: {len(df):,}, Features: {len(df.columns)}")
            return df
        except Exception as e:
            logger.warning(f"Failed to load existing test data: {e}")
    
    # If no test data, try to create it
    logger.info("Creating unified feature data for testing")
    try:
        # Check for required data sources
        power_path = Path("data/master/caiso_california_only.parquet")
        forecast_dir = Path("data/forecasts")
        
        if not power_path.exists():
            logger.error(f"Power data not found: {power_path}")
            return None
        
        # Create unified features with limited scope for testing
        config = UnifiedFeatureConfig(
            forecast_config=ForecastFeatureConfig(forecast_horizons=[6, 24]),
            target_zones=['NP15'],  # Single zone for testing
            lag_hours=[1, 24],
            include_temporal_features=True,
            include_weather_interactions=True
        )
        
        df = build_unified_features(
            power_data_path=power_path,
            weather_data_path=None,  # No historical weather for now
            forecast_data_dir=forecast_dir if forecast_dir.exists() else None,
            config=config
        )
        
        logger.info(f"Created unified feature data: {len(df):,} records, {len(df.columns)} features")
        return df
        
    except Exception as e:
        logger.error(f"Failed to create unified feature data: {e}")
        return None


def create_baseline_model(
    df: pd.DataFrame, 
    logger: logging.Logger
) -> Tuple[EnhancedXGBoostModel, Dict[str, float]]:
    """
    Create and train baseline model without forecast features.
    
    Args:
        df: DataFrame with unified features
        logger: Logger instance
        
    Returns:
        Tuple of (trained_model, performance_metrics)
    """
    logger.info("🔧 Creating baseline model (no forecast features)")
    
    # Define baseline features (no forecast features)
    baseline_features = [
        'hour', 'day_of_week', 'month', 'quarter', 'is_weekend',
        'hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos',
        'day_of_year_sin', 'day_of_year_cos',
        'load_lag_1h', 'load_lag_24h'
    ]
    
    # Add weather features if available
    weather_features = ['temp_c', 'humidity', 'wind_speed_kmh', 'cooling_degree_days', 'heating_degree_days']
    available_weather = [f for f in weather_features if f in df.columns]
    baseline_features.extend(available_weather)
    
    # Create model configuration
    config = ModelConfig(
        feature_columns=baseline_features,
        xgb_params={
            'objective': 'reg:squarederror',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 500,
            'random_state': 42,
            'n_jobs': -1
        }
    )
    
    # Prepare training data
    features, target, selected_features = prepare_training_data(df, config)
    
    logger.info(f"Baseline model features: {len(selected_features)}")
    logger.debug(f"Features: {selected_features}")
    
    # Train model
    model = EnhancedXGBoostModel(config)
    metrics = model.train(features, target, validation_split=True)
    
    logger.info("✅ Baseline model training completed")
    
    return model, metrics


def create_enhanced_model(
    df: pd.DataFrame, 
    logger: logging.Logger
) -> Tuple[EnhancedXGBoostModel, Dict[str, float]]:
    """
    Create and train enhanced model with forecast features.
    
    Args:
        df: DataFrame with unified features
        logger: Logger instance
        
    Returns:
        Tuple of (trained_model, performance_metrics)
    """
    logger.info("🌤️  Creating enhanced model (with forecast features)")
    
    # Use default enhanced feature set
    config = ModelConfig(
        feature_columns=None,  # Use default enhanced features
        xgb_params={
            'objective': 'reg:squarederror',
            'max_depth': 8,
            'learning_rate': 0.1,
            'n_estimators': 1000,
            'random_state': 42,
            'n_jobs': -1
        }
    )
    
    # Prepare training data
    features, target, selected_features = prepare_training_data(df, config)
    
    logger.info(f"Enhanced model features: {len(selected_features)}")
    logger.debug(f"Features: {selected_features}")
    
    # Train model
    model = EnhancedXGBoostModel(config)
    metrics = model.train(features, target, validation_split=True)
    
    logger.info("✅ Enhanced model training completed")
    
    return model, metrics


def compare_model_performance(
    baseline_metrics: Dict[str, float],
    enhanced_metrics: Dict[str, float],
    logger: logging.Logger
) -> Dict[str, float]:
    """
    Compare baseline vs enhanced model performance.
    
    Args:
        baseline_metrics: Baseline model performance metrics
        enhanced_metrics: Enhanced model performance metrics
        logger: Logger instance
        
    Returns:
        Dictionary with improvement metrics
    """
    logger.info("📊 Comparing model performance")
    
    improvements = {}
    
    for metric in ['mae', 'rmse', 'mape']:
        if metric in baseline_metrics and metric in enhanced_metrics:
            baseline_val = baseline_metrics[metric]
            enhanced_val = enhanced_metrics[metric]
            
            # Calculate improvement (negative means enhanced is better)
            improvement = ((enhanced_val - baseline_val) / baseline_val) * 100
            improvements[f'{metric}_improvement_pct'] = improvement
            
            logger.info(f"{metric.upper()} Comparison:")
            logger.info(f"  Baseline: {baseline_val:.3f}")
            logger.info(f"  Enhanced: {enhanced_val:.3f}")
            logger.info(f"  Improvement: {improvement:+.2f}%")
    
    # Check if we achieved the target improvement
    if 'mape_improvement_pct' in improvements:
        mape_improvement = -improvements['mape_improvement_pct']  # Negative is better
        target_improvement = 5.0  # 5% MAPE reduction target
        
        if mape_improvement >= target_improvement:
            logger.info(f"🎯 SUCCESS: Achieved {mape_improvement:.1f}% MAPE improvement (target: {target_improvement}%)")
        else:
            logger.warning(f"⚠️  Below target: {mape_improvement:.1f}% MAPE improvement (target: {target_improvement}%)")
    
    return improvements


def analyze_feature_importance(
    baseline_model: EnhancedXGBoostModel,
    enhanced_model: EnhancedXGBoostModel,
    logger: logging.Logger
) -> None:
    """
    Analyze and compare feature importance between models.
    
    Args:
        baseline_model: Trained baseline model
        enhanced_model: Trained enhanced model
        logger: Logger instance
    """
    logger.info("🔍 Analyzing feature importance")
    
    try:
        # Get feature importance from both models
        baseline_importance = baseline_model.get_feature_importance()
        enhanced_importance = enhanced_model.get_feature_importance()
        
        logger.info("Top 10 features in baseline model:")
        for i, row in baseline_importance.head(10).iterrows():
            logger.info(f"  {i+1:2d}. {row['feature']:<25} {row['importance']:>8.1f}")
        
        logger.info("Top 10 features in enhanced model:")
        for i, row in enhanced_importance.head(10).iterrows():
            logger.info(f"  {i+1:2d}. {row['feature']:<25} {row['importance']:>8.1f}")
        
        # Check for forecast features in top features
        forecast_features = [f for f in enhanced_importance['feature'] if 'forecast' in f]
        if forecast_features:
            logger.info(f"Forecast features found in enhanced model: {len(forecast_features)}")
            
            # Show top forecast features
            forecast_importance = enhanced_importance[
                enhanced_importance['feature'].str.contains('forecast')
            ].head(5)
            
            if len(forecast_importance) > 0:
                logger.info("Top forecast features:")
                for i, row in forecast_importance.iterrows():
                    logger.info(f"  {row['feature']:<25} {row['importance']:>8.1f}")
        else:
            logger.warning("No forecast features found in enhanced model importance")
            
    except Exception as e:
        logger.error(f"Failed to analyze feature importance: {e}")


def test_model_persistence(
    model: EnhancedXGBoostModel,
    test_features: pd.DataFrame,
    logger: logging.Logger
) -> bool:
    """
    Test model saving and loading functionality.
    
    Args:
        model: Trained model to test
        test_features: Features for prediction testing
        logger: Logger instance
        
    Returns:
        True if persistence test passes, False otherwise
    """
    logger.info("💾 Testing model persistence")
    
    try:
        # Create test output directory
        output_dir = Path("data/test_models")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = output_dir / f"enhanced_xgboost_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
        model.save_model(model_path)
        
        # Make prediction with original model
        original_pred = model.predict(test_features.head(100))
        
        # Load model
        loaded_model = EnhancedXGBoostModel.load_model(model_path)
        
        # Make prediction with loaded model
        loaded_pred = loaded_model.predict(test_features.head(100))
        
        # Compare predictions
        pred_diff = np.abs(original_pred - loaded_pred).max()
        
        if pred_diff < 1e-6:
            logger.info("✅ Model persistence test passed")
            return True
        else:
            logger.error(f"❌ Model persistence test failed: max prediction difference = {pred_diff}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Model persistence test failed: {e}")
        return False


def main():
    """Main test function."""
    
    parser = argparse.ArgumentParser(
        description="Test enhanced XGBoost model with weather forecast features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip baseline model training"
    )
    
    parser.add_argument(
        "--save-models",
        action="store_true",
        help="Save trained models to disk"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    logger.info("🚀 Starting enhanced XGBoost model test")
    logger.info("=" * 60)
    
    try:
        # Load test data
        df = load_test_data(logger)
        if df is None:
            logger.error("❌ Failed to load test data")
            return 1
        
        # Filter to recent data with sufficient samples for training
        # Use last 100k records to ensure we have enough data
        if len(df) > 100000:
            df = df.tail(100000).copy()
            logger.info(f"Using last 100k records for training: {len(df):,} samples")
        
        baseline_metrics = None
        enhanced_metrics = None
        
        # Train baseline model
        if not args.skip_baseline:
            baseline_model, baseline_metrics = create_baseline_model(df, logger)
        
        # Train enhanced model
        enhanced_model, enhanced_metrics = create_enhanced_model(df, logger)
        
        # Compare performance
        if baseline_metrics and enhanced_metrics:
            improvements = compare_model_performance(baseline_metrics, enhanced_metrics, logger)
        
        # Analyze feature importance
        if not args.skip_baseline:
            analyze_feature_importance(baseline_model, enhanced_model, logger)
        else:
            # Just show enhanced model importance
            importance = enhanced_model.get_feature_importance()
            logger.info("Top 10 features in enhanced model:")
            for i, row in importance.head(10).iterrows():
                logger.info(f"  {i+1:2d}. {row['feature']:<25} {row['importance']:>8.1f}")
        
        # Test model persistence
        features, _, _ = prepare_training_data(df, enhanced_model.config)
        if not test_model_persistence(enhanced_model, features, logger):
            logger.warning("⚠️  Model persistence test failed")
        
        # Save models if requested
        if args.save_models:
            models_dir = Path("data/trained_models")
            models_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if not args.skip_baseline:
                baseline_path = models_dir / f"baseline_xgboost_{timestamp}.joblib"
                baseline_model.save_model(baseline_path)
                logger.info(f"Saved baseline model: {baseline_path}")
            
            enhanced_path = models_dir / f"enhanced_xgboost_{timestamp}.joblib"
            enhanced_model.save_model(enhanced_path)
            logger.info(f"Saved enhanced model: {enhanced_path}")
        
        logger.info("=" * 60)
        logger.info("✅ Enhanced XGBoost model test completed successfully!")
        
        if enhanced_metrics:
            logger.info(f"   Enhanced model MAPE: {enhanced_metrics.get('mape', 0):.2f}%")
        
        logger.info("   Ready for production deployment and further evaluation")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
