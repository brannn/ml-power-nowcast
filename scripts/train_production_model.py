#!/usr/bin/env python3
"""
Production Model Training Script

This script trains production-ready models with proper validation,
quality checks, and deployment safeguards.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import json

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


def load_hybrid_training_data(config: ProductionModelConfig) -> pd.DataFrame:
    """
    Load training data using hybrid strategy with seasonal coverage and recent emphasis.

    Args:
        config: Production configuration with hybrid parameters

    Returns:
        DataFrame with hybrid training data and sample weights
    """
    from src.models.production_config import prepare_hybrid_training_data

    logger.info("Loading hybrid training data with seasonal coverage...")

    # Load master dataset
    data_path = Path('data/master/caiso_california_only.parquet')
    df = pd.read_parquet(data_path)

    # Prepare hybrid training data with proper weighting
    hybrid_data = prepare_hybrid_training_data(df, config, zone="SYSTEM")

    return hybrid_data


def create_training_features(data_df, include_enhanced: bool = True):
    """Create features for training."""
    logger.info("Creating training features...")
    
    # Save to temp file for pipeline
    temp_path = Path('data/temp_production_training.parquet')
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
        
        # Add enhanced temporal features if requested
        if include_enhanced:
            features_df = create_enhanced_temporal_features(features_df)
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        
        return features_df
        
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise e


def train_and_validate_model(
    hybrid_data: pd.DataFrame,
    profile: str = "balanced",
    validation_config: ProductionModelConfig = None
) -> tuple:
    """
    Train model using hybrid strategy and validate for production deployment.

    Returns:
        Tuple of (model, validation_results, metrics)
    """
    logger.info(f"Training {profile} production model with hybrid strategy...")

    if validation_config is None:
        validation_config = ProductionModelConfig()

    # Create model configuration
    model_config = create_production_model_config(profile)

    # Create enhanced features (extreme for extreme_temporal profile)
    if profile == "extreme_temporal":
        features_df = create_training_features(hybrid_data, include_enhanced=True)
        # Apply extreme temporal features
        from src.models.production_config import create_extreme_temporal_features
        features_df = create_extreme_temporal_features(features_df)
    else:
        features_df = create_training_features(hybrid_data, include_enhanced=True)

    # Prepare training data
    features, target, selected_features = prepare_training_data(features_df, model_config)

    # Extract sample weights for hybrid training
    sample_weights = hybrid_data['sample_weight'] if 'sample_weight' in hybrid_data.columns else None

    logger.info(f"Hybrid training configuration:")
    logger.info(f"  Total samples: {len(features):,}")
    logger.info(f"  Selected features: {len(selected_features)}")
    logger.info(f"  Sample weights: {'Yes' if sample_weights is not None else 'No'}")
    if sample_weights is not None:
        logger.info(f"  Weight distribution: {sample_weights.value_counts().to_dict()}")

    # Train model with sample weights
    model = EnhancedXGBoostModel(model_config)
    metrics = model.train(features, target, validation_split=True, sample_weights=sample_weights)
    
    # Log training results
    logger.info("Training completed!")
    logger.info(f"Validation MAPE: {metrics.get('mape', 0):.2f}%")
    logger.info(f"Validation R²: {metrics.get('r2', 0):.4f}")
    
    # Validate model quality
    validation_results = validate_model_quality(model, features, validation_config)
    
    # Log feature importance
    importance = model.get_feature_importance()
    logger.info("Top 10 feature importance:")
    for i, row in importance.head(10).iterrows():
        logger.info(f"  {i+1:2d}. {row['feature']:<25} {row['importance']:>10.1f}")
    
    return model, validation_results, metrics


def backup_current_model() -> Path:
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


def deploy_model(model, validation_results: dict, metrics: dict, force: bool = False) -> bool:
    """
    Deploy model to production if it passes quality checks.
    
    Args:
        model: Trained model
        validation_results: Quality validation results
        metrics: Training metrics
        force: Force deployment even if checks fail
        
    Returns:
        True if deployment successful
    """
    logger.info("Evaluating model for production deployment...")
    
    # Check if model should be deployed
    should_deploy = validation_results.get('overall_pass', False) or force
    
    if not should_deploy:
        logger.warning("⚠️  Model failed quality checks - not deploying")
        logger.info("Failed checks:")
        for check, passed in validation_results.items():
            if not passed and check != 'overall_pass':
                logger.info(f"  - {check}: {'PASS' if passed else 'FAIL'}")
        return False
    
    try:
        # Backup current model
        backup_path = backup_current_model()
        
        # Save new model
        production_path = Path('data/production_models/enhanced_model_current.joblib')
        production_path.parent.mkdir(parents=True, exist_ok=True)
        
        model.save_model(production_path)
        
        # Create deployment metadata (convert numpy types to native Python)
        def convert_numpy_types(obj):
            """Convert numpy types to native Python types for JSON serialization."""
            if hasattr(obj, 'item'):
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(v) for v in obj]
            else:
                return obj

        metadata = {
            'deployed_at': datetime.now().isoformat(),
            'validation_results': convert_numpy_types(validation_results),
            'training_metrics': convert_numpy_types(metrics),
            'backup_location': str(backup_path) if backup_path else None,
            'model_config': {
                'use_feature_scaling': bool(model.config.use_feature_scaling),
                'scaling_method': str(model.config.scaling_method),
                'lag_feature_weight': float(model.config.lag_feature_weight),
                'xgb_params': convert_numpy_types(model.config.xgb_params)
            }
        }
        
        metadata_path = Path('data/production_models/deployment_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create refresh flag for dashboard
        refresh_flag = Path("data/model_refresh_completed.flag")
        refresh_flag.touch()
        
        logger.info("✅ Model deployed to production successfully!")
        logger.info(f"Production model: {production_path}")
        logger.info(f"Deployment metadata: {metadata_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Model deployment failed: {e}")
        
        # Restore backup if deployment failed
        if backup_path and backup_path.exists():
            import shutil
            shutil.copy2(backup_path, production_path)
            logger.info(f"Restored backup model from {backup_path}")
        
        return False


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description="Train production model")
    parser.add_argument("--profile", choices=["conservative", "balanced", "aggressive", "ultra_temporal", "extreme_temporal"],
                       default="balanced", help="Model training profile")
    parser.add_argument("--months", type=int, default=6, 
                       help="Months of training data to use")
    parser.add_argument("--force-deploy", action="store_true", 
                       help="Force deployment even if quality checks fail")
    parser.add_argument("--no-enhanced-features", action="store_true",
                       help="Skip enhanced temporal features")
    parser.add_argument("--dry-run", action="store_true",
                       help="Train model but don't deploy")
    
    args = parser.parse_args()
    
    logger.info(f"Starting production model training with {args.profile} profile")
    
    try:
        # Create validation config for hybrid training
        validation_config = ProductionModelConfig()

        # Load hybrid training data
        hybrid_data = load_hybrid_training_data(validation_config)

        # Train and validate model
        model, validation_results, metrics = train_and_validate_model(
            hybrid_data,
            args.profile,
            validation_config
        )
        
        # Deploy model if not dry run
        if not args.dry_run:
            deployment_success = deploy_model(
                model, 
                validation_results, 
                metrics, 
                force=args.force_deploy
            )
            
            if deployment_success:
                logger.info("🎉 Production model training and deployment completed!")
            else:
                logger.error("❌ Model deployment failed")
                return 1
        else:
            logger.info("🔍 Dry run completed - model not deployed")
        
        return 0
        
    except Exception as e:
        logger.error(f"Production model training failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
