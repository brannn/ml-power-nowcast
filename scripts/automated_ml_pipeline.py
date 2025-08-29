#!/usr/bin/env python3
"""
Automated ML Pipeline for Continuous Model Updates

This script implements the automated ML pipeline for continuous model updates
as outlined in planning/weather_forecast_integration.md. It provides:

- Automated dataset merging and refresh
- Model retraining with latest data
- Performance validation and monitoring
- Model deployment for dashboard serving
- Fallback and error handling

The pipeline runs every 6 hours to keep models fresh with the latest
power demand patterns and weather forecast data.

Usage:
    python scripts/automated_ml_pipeline.py [options]
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.features.unified_feature_pipeline import (
    build_unified_features,
    UnifiedFeatureConfig,
    ForecastFeatureConfig
)
from src.models.enhanced_xgboost import (
    EnhancedXGBoostModel,
    ModelConfig,
    prepare_training_data,
    ModelTrainingError
)
from scripts.merge_datasets import main as merge_datasets


def setup_logging(log_level: str = "INFO", quiet: bool = False) -> logging.Logger:
    """Set up logging for the automated ML pipeline."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"automated_ml_{datetime.now().strftime('%Y%m%d')}.log"
    
    handlers = [logging.FileHandler(log_file)]
    if not quiet:
        handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


def refresh_master_dataset(logger: logging.Logger) -> bool:
    """
    Refresh the master dataset by merging incremental data.
    
    Args:
        logger: Logger instance
        
    Returns:
        True if refresh successful, False otherwise
    """
    logger.info("🔄 Refreshing master dataset with incremental data")
    
    try:
        # Run the dataset merge script
        import subprocess
        
        merge_cmd = [
            str(Path(__file__).parent.parent / ".venv" / "bin" / "python"),
            str(Path(__file__).parent / "merge_datasets.py"),
            "--log-level", "WARNING"
        ]
        
        result = subprocess.run(
            merge_cmd, 
            capture_output=True, 
            text=True, 
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            logger.info("✅ Master dataset refreshed successfully")
            return True
        else:
            logger.error(f"❌ Dataset refresh failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Dataset refresh failed: {e}")
        return False


def validate_training_data(df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Validate training data quality before model training.
    
    Args:
        df: Training dataset
        logger: Logger instance
        
    Returns:
        True if data is valid for training, False otherwise
    """
    logger.info("🔍 Validating training data quality")
    
    try:
        # Check minimum data requirements
        min_records = 10000  # Minimum records for reliable training
        if len(df) < min_records:
            logger.error(f"❌ Insufficient data: {len(df)} records (minimum: {min_records})")
            return False
        
        # Check target variable
        if 'load' not in df.columns:
            logger.error("❌ Target variable 'load' not found")
            return False
        
        # Check for excessive nulls in target
        null_pct = df['load'].isnull().mean() * 100
        if null_pct > 10:
            logger.error(f"❌ Excessive nulls in target: {null_pct:.1f}%")
            return False
        
        # Check for recent data (within last 7 days)
        if 'timestamp' in df.columns:
            latest_data = pd.to_datetime(df['timestamp']).max()
            days_old = (datetime.now() - latest_data.to_pydatetime().replace(tzinfo=None)).days
            
            if days_old > 7:
                logger.warning(f"⚠️  Latest data is {days_old} days old")
            else:
                logger.info(f"✅ Data freshness: {days_old} days old")
        
        # Check data distribution
        load_data = df['load'].dropna()
        if len(load_data) > 0:
            q1, q3 = load_data.quantile([0.25, 0.75])
            iqr = q3 - q1
            
            if iqr == 0:
                logger.error("❌ No variance in load data")
                return False
            
            logger.info(f"✅ Load data range: {load_data.min():.1f} - {load_data.max():.1f} MW")
        
        logger.info("✅ Training data validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Data validation failed: {e}")
        return False


def train_production_models(
    df: pd.DataFrame, 
    logger: logging.Logger
) -> Tuple[Optional[EnhancedXGBoostModel], Optional[EnhancedXGBoostModel]]:
    """
    Train baseline and enhanced models for production.
    
    Args:
        df: Training dataset
        logger: Logger instance
        
    Returns:
        Tuple of (baseline_model, enhanced_model)
    """
    logger.info("🤖 Training production models")
    
    baseline_model = None
    enhanced_model = None
    
    try:
        # Filter to recent data for faster training (last 6 months)
        if 'timestamp' in df.columns:
            cutoff_date = datetime.now()
            cutoff_date = cutoff_date.replace(tzinfo=None) - timedelta(days=180)

            # Ensure timestamp column is timezone-naive for comparison
            df_timestamps = pd.to_datetime(df['timestamp'])
            if df_timestamps.dt.tz is not None:
                df_timestamps = df_timestamps.dt.tz_localize(None)

            recent_df = df[df_timestamps >= cutoff_date].copy()

            if len(recent_df) > 50000:  # Use recent data if sufficient
                df = recent_df
                logger.info(f"Using recent data for training: {len(df):,} records")
        
        # Train baseline model (no forecast features)
        logger.info("Training baseline model...")
        baseline_features = [
            'hour', 'day_of_week', 'month', 'quarter', 'is_weekend',
            'hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos',
            'day_of_year_sin', 'day_of_year_cos',
            'load_lag_1h', 'load_lag_24h'
        ]
        
        baseline_config = ModelConfig(
            feature_columns=baseline_features,
            test_size=0.1,  # Smaller test set for production
            xgb_params={
                'objective': 'reg:squarederror',
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 300,  # Faster training
                'random_state': 42,
                'n_jobs': -1
            }
        )
        
        baseline_features_df, target, _ = prepare_training_data(df, baseline_config)
        baseline_model = EnhancedXGBoostModel(baseline_config)
        baseline_metrics = baseline_model.train(baseline_features_df, target, validation_split=True)
        
        logger.info(f"✅ Baseline model trained - MAPE: {baseline_metrics.get('mape', 0):.2f}%")
        
        # Train enhanced model (with forecast features)
        logger.info("Training enhanced model...")
        enhanced_config = ModelConfig(
            feature_columns=None,  # Use all available features
            test_size=0.1,
            xgb_params={
                'objective': 'reg:squarederror',
                'max_depth': 8,
                'learning_rate': 0.1,
                'n_estimators': 500,
                'random_state': 42,
                'n_jobs': -1
            }
        )
        
        enhanced_features_df, target, _ = prepare_training_data(df, enhanced_config)
        enhanced_model = EnhancedXGBoostModel(enhanced_config)
        enhanced_metrics = enhanced_model.train(enhanced_features_df, target, validation_split=True)
        
        logger.info(f"✅ Enhanced model trained - MAPE: {enhanced_metrics.get('mape', 0):.2f}%")
        
        # Compare performance
        baseline_mape = baseline_metrics.get('mape', float('inf'))
        enhanced_mape = enhanced_metrics.get('mape', float('inf'))
        
        if enhanced_mape < baseline_mape:
            improvement = ((baseline_mape - enhanced_mape) / baseline_mape) * 100
            logger.info(f"🎯 Enhanced model improvement: {improvement:.2f}%")
        
        return baseline_model, enhanced_model
        
    except Exception as e:
        logger.error(f"❌ Model training failed: {e}")
        return None, None


def deploy_models(
    baseline_model: Optional[EnhancedXGBoostModel],
    enhanced_model: Optional[EnhancedXGBoostModel],
    logger: logging.Logger
) -> bool:
    """
    Deploy trained models for production use.
    
    Args:
        baseline_model: Trained baseline model
        enhanced_model: Trained enhanced model
        logger: Logger instance
        
    Returns:
        True if deployment successful, False otherwise
    """
    logger.info("🚀 Deploying models for production")
    
    try:
        # Create production models directory
        prod_models_dir = Path("data/production_models")
        prod_models_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped backup directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = Path("data/model_backups") / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        deployment_success = False
        
        # Deploy baseline model
        if baseline_model:
            # Save to production location
            baseline_prod_path = prod_models_dir / "baseline_model_current.joblib"
            baseline_model.save_model(baseline_prod_path)
            
            # Save backup
            baseline_backup_path = backup_dir / "baseline_model.joblib"
            baseline_model.save_model(baseline_backup_path)
            
            logger.info(f"✅ Baseline model deployed: {baseline_prod_path}")
            deployment_success = True
        
        # Deploy enhanced model
        if enhanced_model:
            # Save to production location
            enhanced_prod_path = prod_models_dir / "enhanced_model_current.joblib"
            enhanced_model.save_model(enhanced_prod_path)
            
            # Save backup
            enhanced_backup_path = backup_dir / "enhanced_model.joblib"
            enhanced_model.save_model(enhanced_backup_path)
            
            logger.info(f"✅ Enhanced model deployed: {enhanced_prod_path}")
            deployment_success = True
        
        if deployment_success:
            # Create deployment metadata
            metadata = {
                'deployed_at': datetime.now().isoformat(),
                'baseline_available': baseline_model is not None,
                'enhanced_available': enhanced_model is not None,
                'backup_location': str(backup_dir)
            }
            
            metadata_file = prod_models_dir / "deployment_metadata.json"
            import json
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create model refresh flag for dashboard
            refresh_flag = Path("data/model_refresh_completed.flag")
            refresh_flag.touch()
            
            logger.info("✅ Model deployment completed successfully")
            return True
        else:
            logger.error("❌ No models available for deployment")
            return False
            
    except Exception as e:
        logger.error(f"❌ Model deployment failed: {e}")
        return False


def cleanup_old_models(logger: logging.Logger, keep_days: int = 7) -> None:
    """
    Clean up old model backups to save disk space.
    
    Args:
        logger: Logger instance
        keep_days: Number of days of backups to keep
    """
    logger.info(f"🧹 Cleaning up model backups older than {keep_days} days")
    
    try:
        backup_dir = Path("data/model_backups")
        if not backup_dir.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        removed_count = 0
        
        for backup_folder in backup_dir.iterdir():
            if backup_folder.is_dir():
                try:
                    # Parse timestamp from folder name
                    folder_date = datetime.strptime(backup_folder.name, '%Y%m%d_%H%M%S')
                    
                    if folder_date < cutoff_date:
                        import shutil
                        shutil.rmtree(backup_folder)
                        removed_count += 1
                        logger.debug(f"Removed old backup: {backup_folder}")
                        
                except ValueError:
                    # Skip folders that don't match timestamp format
                    continue
        
        if removed_count > 0:
            logger.info(f"✅ Cleaned up {removed_count} old model backups")
        else:
            logger.info("✅ No old backups to clean up")
            
    except Exception as e:
        logger.warning(f"⚠️  Model cleanup failed: {e}")


def main():
    """Main automated ML pipeline function."""
    
    parser = argparse.ArgumentParser(
        description="Automated ML pipeline for continuous model updates",
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
        "--quiet",
        action="store_true",
        help="Minimal console output for scheduled runs"
    )
    
    parser.add_argument(
        "--skip-dataset-refresh",
        action="store_true",
        help="Skip dataset refresh step"
    )
    
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip model cleanup step"
    )
    
    parser.add_argument(
        "--target-zones",
        nargs="+",
        default=["NP15"],
        help="CAISO zones to include in training (default: NP15)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level, args.quiet)
    
    if not args.quiet:
        logger.info("🤖 Starting Automated ML Pipeline")
        logger.info("=" * 60)
        logger.info("Continuous model updates for production deployment")
    
    pipeline_success = True
    
    try:
        # Step 1: Refresh master dataset
        if not args.skip_dataset_refresh:
            if not refresh_master_dataset(logger):
                logger.error("❌ Dataset refresh failed - continuing with existing data")
        
        # Step 2: Build unified features
        logger.info("🔧 Building unified features for training")
        
        unified_config = UnifiedFeatureConfig(
            forecast_config=ForecastFeatureConfig(forecast_horizons=[6, 24]),
            target_zones=args.target_zones,
            lag_hours=[1, 24],
            include_temporal_features=True,
            include_weather_interactions=True
        )
        
        unified_df = build_unified_features(
            power_data_path=Path("data/master/caiso_california_only.parquet"),
            weather_data_path=None,
            forecast_data_dir=Path("data/forecasts"),
            config=unified_config
        )
        
        # Step 3: Validate training data
        if not validate_training_data(unified_df, logger):
            logger.error("❌ Training data validation failed")
            return 1
        
        # Step 4: Train models
        baseline_model, enhanced_model = train_production_models(unified_df, logger)
        
        if not baseline_model and not enhanced_model:
            logger.error("❌ No models trained successfully")
            return 1
        
        # Step 5: Deploy models
        if not deploy_models(baseline_model, enhanced_model, logger):
            logger.error("❌ Model deployment failed")
            pipeline_success = False
        
        # Step 6: Cleanup old models
        if not args.skip_cleanup:
            cleanup_old_models(logger)
        
        # Final status
        if pipeline_success:
            if not args.quiet:
                logger.info("=" * 60)
                logger.info("✅ Automated ML Pipeline completed successfully!")
                logger.info("   Fresh models deployed for production use")
                logger.info("   Dashboard can now serve updated predictions")
            return 0
        else:
            logger.error("❌ Pipeline completed with errors")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Automated ML Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
