#!/usr/bin/env python3
"""
Weekly Deep Training Script

This script performs comprehensive model training using the full historical dataset
to capture long-term patterns, seasonal variations, and extreme events.

Runs weekly to complement the daily hybrid training strategy.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.models.enhanced_xgboost import (
    EnhancedXGBoostModel,
    prepare_training_data
)
from src.models.production_config import (
    create_production_model_config,
    create_enhanced_temporal_features,
    validate_model_quality,
    ProductionModelConfig
)
from src.features.unified_feature_pipeline import (
    build_unified_features,
    UnifiedFeatureConfig,
    ForecastFeatureConfig
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_full_historical_data(years_back: int = 5) -> pd.DataFrame:
    """
    Load full historical dataset for deep training.
    
    Args:
        years_back: Number of years of historical data to include
        
    Returns:
        DataFrame with full historical data
    """
    logger.info(f"Loading {years_back} years of historical data for deep training...")
    
    # Load master dataset
    data_path = Path('data/master/caiso_california_only.parquet')
    df = pd.read_parquet(data_path)
    
    # Focus on SYSTEM zone for statewide predictions
    system_data = df[df['zone'] == 'SYSTEM'].copy()
    system_data = system_data.sort_values('timestamp')
    system_data['timestamp'] = pd.to_datetime(system_data['timestamp'])
    
    # Get data from last N years
    cutoff_date = system_data['timestamp'].max() - timedelta(days=years_back * 365)
    historical_data = system_data[system_data['timestamp'] >= cutoff_date]
    
    logger.info(f"Loaded {len(historical_data):,} records")
    logger.info(f"Date range: {historical_data['timestamp'].min().date()} to {historical_data['timestamp'].max().date()}")
    
    # Analyze seasonal coverage
    months_covered = historical_data['timestamp'].dt.month.nunique()
    years_covered = historical_data['timestamp'].dt.year.nunique()
    
    logger.info(f"Temporal coverage:")
    logger.info(f"  Years: {years_covered} ({sorted(historical_data['timestamp'].dt.year.unique())})")
    logger.info(f"  Months: {months_covered}/12")
    
    # Analyze data distribution
    monthly_avg = historical_data.groupby(historical_data['timestamp'].dt.month)['load'].mean()
    seasonal_variation = (monthly_avg.max() - monthly_avg.min()) / monthly_avg.mean() * 100
    
    logger.info(f"  Seasonal variation: {seasonal_variation:.1f}%")
    logger.info(f"  Load range: {historical_data['load'].min():,.0f} - {historical_data['load'].max():,.0f} MW")
    
    return historical_data


def create_deep_training_features(data_df):
    """Create comprehensive features for deep training."""
    logger.info("Creating comprehensive features for deep training...")
    
    # Save to temp file for pipeline
    temp_path = Path('data/temp_deep_training.parquet')
    data_df.to_parquet(temp_path, index=False)
    
    try:
        config = UnifiedFeatureConfig(
            forecast_config=ForecastFeatureConfig(
                forecast_horizons=[6, 24],
                base_temperature=18.0
            ),
            include_lag_features=True,
            lag_hours=[1, 24, 168],  # Add weekly lag for long-term patterns
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
        
        # Add enhanced temporal features
        features_df = create_enhanced_temporal_features(features_df)
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        
        return features_df
        
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise e


def train_deep_model(
    features_df: pd.DataFrame,
    profile: str = "conservative"
) -> tuple:
    """
    Train deep model with full historical data.
    
    Args:
        features_df: Feature dataset
        profile: Training profile (conservative for stability)
        
    Returns:
        Tuple of (model, validation_results, metrics)
    """
    logger.info(f"Training deep model with {profile} profile...")
    
    # Use conservative profile for stability with large dataset
    model_config = create_production_model_config(profile)
    
    # Prepare training data
    features, target, selected_features = prepare_training_data(features_df, model_config)
    
    logger.info(f"Deep training configuration:")
    logger.info(f"  Total samples: {len(features):,}")
    logger.info(f"  Selected features: {len(selected_features)}")
    logger.info(f"  Training profile: {profile}")
    
    # Train model
    model = EnhancedXGBoostModel(model_config)
    metrics = model.train(features, target, validation_split=True)
    
    # Log training results
    logger.info("Deep training completed!")
    logger.info(f"Validation MAPE: {metrics.get('mape', 0):.2f}%")
    logger.info(f"Validation R²: {metrics.get('r2', 0):.4f}")
    
    # Validate model quality
    validation_config = ProductionModelConfig()
    validation_results = validate_model_quality(model, features_df, validation_config)
    
    # Log feature importance
    importance = model.get_feature_importance()
    logger.info("Top 10 feature importance:")
    for i, row in importance.head(10).iterrows():
        logger.info(f"  {i+1:2d}. {row['feature']:<25} {row['importance']:>10.1f}")
    
    return model, validation_results, metrics


def deploy_deep_model(model, validation_results: dict, metrics: dict) -> bool:
    """
    Deploy deep model as weekly baseline.
    
    Args:
        model: Trained deep model
        validation_results: Quality validation results
        metrics: Training metrics
        
    Returns:
        True if deployment successful
    """
    logger.info("Deploying deep model as weekly baseline...")
    
    try:
        # Save as weekly deep model
        weekly_path = Path('data/production_models/enhanced_model_weekly_deep.joblib')
        weekly_path.parent.mkdir(parents=True, exist_ok=True)
        
        model.save_model(weekly_path)
        
        # Create deployment metadata
        metadata = {
            'deployed_at': datetime.now().isoformat(),
            'model_type': 'weekly_deep_training',
            'validation_results': validation_results,
            'training_metrics': metrics,
            'training_strategy': 'full_historical_data'
        }
        
        metadata_path = Path('data/production_models/weekly_deep_metadata.json')
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"✅ Deep model deployed to {weekly_path}")
        logger.info(f"Metadata saved to {metadata_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Deep model deployment failed: {e}")
        return False


def main():
    """Main deep training function."""
    parser = argparse.ArgumentParser(description="Weekly deep training with full historical data")
    parser.add_argument("--years", type=int, default=5, 
                       help="Years of historical data to use")
    parser.add_argument("--profile", choices=["conservative", "balanced", "aggressive"], 
                       default="conservative", help="Model training profile")
    parser.add_argument("--dry-run", action="store_true",
                       help="Train model but don't deploy")
    
    args = parser.parse_args()
    
    logger.info(f"Starting weekly deep training with {args.years} years of data")
    
    try:
        # Load full historical data
        data_df = load_full_historical_data(args.years)
        
        # Create comprehensive features
        features_df = create_deep_training_features(data_df)
        
        # Train deep model
        model, validation_results, metrics = train_deep_model(
            features_df, 
            args.profile
        )
        
        # Deploy model if not dry run
        if not args.dry_run:
            deployment_success = deploy_deep_model(
                model, 
                validation_results, 
                metrics
            )
            
            if deployment_success:
                logger.info("🎉 Weekly deep training completed successfully!")
            else:
                logger.error("❌ Deep model deployment failed")
                return 1
        else:
            logger.info("🔍 Dry run completed - deep model not deployed")
        
        return 0
        
    except Exception as e:
        logger.error(f"Weekly deep training failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
