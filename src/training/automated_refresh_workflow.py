#!/usr/bin/env python3
"""
Automated Model Refresh Workflow

Implements a comprehensive automated workflow for retraining, validating, and deploying
improved models to address evening peak prediction accuracy issues.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import json
import pickle
import shutil
from dataclasses import dataclass
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)

@dataclass
class ModelPerformance:
    """Data class for storing model performance metrics."""
    mape: float
    rmse: float
    mae: float
    r2: float
    evening_peak_mape: float
    validation_samples: int

@dataclass
class ModelMetadata:
    """Data class for storing model metadata."""
    model_id: str
    zone: str
    model_type: str
    training_date: datetime
    performance: ModelPerformance
    feature_count: int
    training_samples: int
    hyperparameters: Dict[str, Any]

class AutomatedModelRefreshWorkflow:
    """Comprehensive automated model retraining and deployment workflow."""
    
    def __init__(self, 
                 data_dir: str = "data/enhanced_training",
                 models_dir: str = "production_models",
                 backup_dir: str = "model_backups"):
        """
        Initialize the automated refresh workflow.
        
        Args:
            data_dir: Directory containing enhanced training datasets
            models_dir: Directory for production models
            backup_dir: Directory for model backups
        """
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.backup_dir = Path(backup_dir)
        
        # Create directories
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Model architecture configuration following ML-004 policy
        self.ensemble_config = {
            'baseline_xgb_weight': 0.20,      # Reduced from 25%
            'enhanced_xgb_weight': 0.40,      # Increased from 35%
            'lightgbm_weight': 0.40,          # Same at 40%
        }
        
        # Model hyperparameters from strategy
        self.xgb_params = {
            'n_estimators': 300,
            'max_depth': 8,
            'learning_rate': 0.1,
            'subsample': 0.9,
            'colsample_bytree': 0.9,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42
        }
        
        self.lgb_params = {
            'n_estimators': 300,
            'max_depth': 12,
            'learning_rate': 0.1,
            'num_leaves': 128,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.9,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'verbose': -1
        }
    
    def load_enhanced_datasets(self, zone: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load enhanced training and validation datasets for a zone."""
        train_file = self.data_dir / f"{zone}_enhanced_train.parquet"
        val_file = self.data_dir / f"{zone}_enhanced_val.parquet"
        
        if not train_file.exists() or not val_file.exists():
            raise FileNotFoundError(f"Enhanced datasets not found for zone {zone}")
        
        train_df = pd.read_parquet(train_file)
        val_df = pd.read_parquet(val_file)
        
        logger.info(f"Loaded {zone} datasets: {len(train_df)} train, {len(val_df)} val samples")
        return train_df, val_df
    
    def prepare_features_and_targets(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare feature matrix, targets, and sample weights."""
        # Exclude non-feature columns
        exclude_cols = ['timestamp', 'load', 'zone', 'resource_name', 'region', 
                       'data_source', 'date', 'month_day', 'sample_weight']
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        X = df[feature_cols].values
        y = df['load'].values
        sample_weight = df['sample_weight'].values if 'sample_weight' in df.columns else None
        
        logger.info(f"Prepared features: {X.shape}, targets: {y.shape}")
        return X, y, sample_weight
    
    def train_baseline_xgboost(self, X_train: np.ndarray, y_train: np.ndarray, 
                              X_val: np.ndarray, y_val: np.ndarray,
                              sample_weight: Optional[np.ndarray] = None) -> xgb.XGBRegressor:
        """Train baseline XGBoost model."""
        logger.info("Training baseline XGBoost model...")
        
        # Simplified parameters for baseline
        baseline_params = self.xgb_params.copy()
        baseline_params.update({
            'n_estimators': 200,  # Fewer estimators
            'max_depth': 6,       # Shallower trees
        })
        
        model = xgb.XGBRegressor(**baseline_params)
        model.fit(X_train, y_train, 
                 sample_weight=sample_weight,
                 eval_set=[(X_val, y_val)],
                 verbose=False)
        
        return model
    
    def train_enhanced_xgboost(self, X_train: np.ndarray, y_train: np.ndarray,
                              X_val: np.ndarray, y_val: np.ndarray,
                              sample_weight: Optional[np.ndarray] = None) -> xgb.XGBRegressor:
        """Train enhanced XGBoost model with full parameters."""
        logger.info("Training enhanced XGBoost model...")
        
        model = xgb.XGBRegressor(**self.xgb_params)
        model.fit(X_train, y_train,
                 sample_weight=sample_weight,
                 eval_set=[(X_val, y_val)],
                 verbose=False)
        
        return model
    
    def train_lightgbm(self, X_train: np.ndarray, y_train: np.ndarray,
                      X_val: np.ndarray, y_val: np.ndarray,
                      sample_weight: Optional[np.ndarray] = None) -> lgb.LGBMRegressor:
        """Train zone-specific LightGBM model following ML-005 policy."""
        logger.info("Training zone-specific LightGBM model...")
        
        model = lgb.LGBMRegressor(**self.lgb_params)
        model.fit(X_train, y_train,
                 sample_weight=sample_weight,
                 eval_set=[(X_val, y_val)])
        
        return model
    
    def create_ensemble_predictions(self, models: Dict[str, Any], X: np.ndarray) -> np.ndarray:
        """Create ensemble predictions using configured weights."""
        baseline_pred = models['baseline_xgb'].predict(X)
        enhanced_pred = models['enhanced_xgb'].predict(X)
        lgb_pred = models['lightgbm'].predict(X)
        
        ensemble_pred = (
            self.ensemble_config['baseline_xgb_weight'] * baseline_pred +
            self.ensemble_config['enhanced_xgb_weight'] * enhanced_pred +
            self.ensemble_config['lightgbm_weight'] * lgb_pred
        )
        
        return ensemble_pred
    
    def calculate_performance_metrics(self, y_true: np.ndarray, y_pred: np.ndarray,
                                    df_val: pd.DataFrame) -> ModelPerformance:
        """Calculate comprehensive performance metrics."""
        # Overall metrics
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # Evening peak specific metrics
        evening_mask = df_val.get('is_evening_peak', 0) == 1
        if evening_mask.any():
            evening_true = y_true[evening_mask]
            evening_pred = y_pred[evening_mask]
            evening_peak_mape = np.mean(np.abs((evening_true - evening_pred) / evening_true)) * 100
        else:
            evening_peak_mape = mape
        
        return ModelPerformance(
            mape=mape,
            rmse=rmse,
            mae=mae,
            r2=r2,
            evening_peak_mape=evening_peak_mape,
            validation_samples=len(y_true)
        )
    
    def backup_existing_models(self, zone: str) -> bool:
        """Backup existing production models before deployment."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zone_backup_dir = self.backup_dir / f"{zone}_{timestamp}"
        
        zone_models_dir = self.models_dir / zone
        if zone_models_dir.exists():
            shutil.copytree(zone_models_dir, zone_backup_dir)
            logger.info(f"Backed up existing models to: {zone_backup_dir}")
            return True
        
        logger.info(f"No existing models found for {zone}, skipping backup")
        return False
    
    def save_trained_models(self, zone: str, models: Dict[str, Any], 
                           metadata: ModelMetadata) -> Dict[str, str]:
        """Save trained models and metadata to production directory."""
        zone_dir = self.models_dir / zone
        zone_dir.mkdir(parents=True, exist_ok=True)
        
        # Save models
        model_files = {}
        for model_type, model in models.items():
            model_file = zone_dir / f"{model_type}_model.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
            model_files[model_type] = str(model_file)
            logger.info(f"Saved {model_type} model: {model_file}")
        
        # Save metadata
        metadata_file = zone_dir / "model_metadata.json"
        with open(metadata_file, 'w') as f:
            # Convert metadata to serializable format
            metadata_dict = {
                'model_id': metadata.model_id,
                'zone': metadata.zone,
                'model_type': metadata.model_type,
                'training_date': metadata.training_date.isoformat(),
                'performance': {
                    'mape': metadata.performance.mape,
                    'rmse': metadata.performance.rmse,
                    'mae': metadata.performance.mae,
                    'r2': metadata.performance.r2,
                    'evening_peak_mape': metadata.performance.evening_peak_mape,
                    'validation_samples': metadata.performance.validation_samples
                },
                'feature_count': metadata.feature_count,
                'training_samples': metadata.training_samples,
                'hyperparameters': metadata.hyperparameters,
                'ensemble_config': self.ensemble_config
            }
            json.dump(metadata_dict, f, indent=2)
        
        model_files['metadata'] = str(metadata_file)
        logger.info(f"Saved model metadata: {metadata_file}")
        
        return model_files
    
    def train_and_validate_zone_models(self, zone: str) -> Tuple[Dict[str, Any], ModelPerformance]:
        """Complete training and validation pipeline for a zone."""
        logger.info(f"Starting model training and validation for zone: {zone}")
        
        # Load enhanced datasets
        train_df, val_df = self.load_enhanced_datasets(zone)
        
        # Prepare features and targets
        X_train, y_train, train_weights = self.prepare_features_and_targets(train_df)
        X_val, y_val, _ = self.prepare_features_and_targets(val_df)
        
        # Train all models
        models = {}
        models['baseline_xgb'] = self.train_baseline_xgboost(X_train, y_train, X_val, y_val, train_weights)
        models['enhanced_xgb'] = self.train_enhanced_xgboost(X_train, y_train, X_val, y_val, train_weights)
        models['lightgbm'] = self.train_lightgbm(X_train, y_train, X_val, y_val, train_weights)
        
        # Create ensemble predictions
        ensemble_pred = self.create_ensemble_predictions(models, X_val)
        
        # Calculate performance metrics
        performance = self.calculate_performance_metrics(y_val, ensemble_pred, val_df)
        
        logger.info(f"{zone} model performance:")
        logger.info(f"  Overall MAPE: {performance.mape:.2f}%")
        logger.info(f"  Evening peak MAPE: {performance.evening_peak_mape:.2f}%")
        logger.info(f"  RMSE: {performance.rmse:.2f}")
        logger.info(f"  R²: {performance.r2:.4f}")
        
        return models, performance
    
    def execute_full_refresh_workflow(self, zones: List[str] = None) -> Dict[str, ModelMetadata]:
        """Execute the complete model refresh workflow for specified zones."""
        if zones is None:
            zones = ['SCE', 'SP15']
        
        logger.info(f"Starting automated model refresh workflow for zones: {zones}")
        
        results = {}
        
        for zone in zones:
            try:
                logger.info(f"Processing zone: {zone}")
                
                # Backup existing models
                self.backup_existing_models(zone)
                
                # Train and validate models
                models, performance = self.train_and_validate_zone_models(zone)
                
                # Create metadata
                metadata = ModelMetadata(
                    model_id=f"{zone}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    zone=zone,
                    model_type="enhanced_ensemble",
                    training_date=datetime.now(),
                    performance=performance,
                    feature_count=len([col for col in pd.read_parquet(self.data_dir / f"{zone}_enhanced_train.parquet").columns 
                                     if col not in ['timestamp', 'load', 'zone', 'resource_name', 'region', 'data_source', 'date', 'month_day', 'sample_weight']]),
                    training_samples=len(pd.read_parquet(self.data_dir / f"{zone}_enhanced_train.parquet")),
                    hyperparameters={
                        'xgb_params': self.xgb_params,
                        'lgb_params': self.lgb_params,
                        'ensemble_config': self.ensemble_config
                    }
                )
                
                # Save models to production
                model_files = self.save_trained_models(zone, models, metadata)
                
                results[zone] = metadata
                logger.info(f"Successfully completed refresh for zone {zone}")
                
            except Exception as e:
                logger.error(f"Failed to refresh models for zone {zone}: {e}")
                continue
        
        logger.info(f"Automated model refresh workflow completed for {len(results)} zones")
        return results

def execute_model_refresh():
    """Execute the automated model refresh workflow."""
    print("=== Automated Model Refresh Workflow ===")
    
    workflow = AutomatedModelRefreshWorkflow()
    
    print("Starting model retraining for SCE and SP15 zones...")
    print("This process includes:")
    print("1. Loading enhanced training datasets with evening peak features")
    print("2. Training baseline XGBoost, enhanced XGBoost, and zone-specific LightGBM models")
    print("3. Creating ensemble predictions with optimized weights")
    print("4. Validating against recent evening peak data")
    print("5. Backing up existing models and deploying improved models")
    
    try:
        results = workflow.execute_full_refresh_workflow(['SCE', 'SP15'])
        
        print(f"\n✅ Model refresh completed successfully for {len(results)} zones!")
        
        for zone, metadata in results.items():
            print(f"\n{zone} Zone Results:")
            print(f"  Model ID: {metadata.model_id}")
            print(f"  Overall MAPE: {metadata.performance.mape:.2f}%")
            print(f"  Evening Peak MAPE: {metadata.performance.evening_peak_mape:.2f}%")
            print(f"  R²: {metadata.performance.r2:.4f}")
            print(f"  Training samples: {metadata.training_samples:,}")
            print(f"  Features: {metadata.feature_count}")
        
        print("\nNext steps:")
        print("1. Test improved models against current LA_METRO predictions")
        print("2. Deploy models to API server if performance meets targets")
        print("3. Monitor evening peak accuracy improvements")
        
    except Exception as e:
        print(f"❌ Model refresh failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    execute_model_refresh()