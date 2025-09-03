#!/usr/bin/env python3
"""
Production-Ready Model Training Pipeline

Fixes the identified issues with data preprocessing, feature scaling, and model training
to achieve sub-5% MAPE for evening peak predictions.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import json
import pickle
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb

logger = logging.getLogger(__name__)

class ProductionModelTrainer:
    """Production-ready model training with proper preprocessing."""
    
    def __init__(self, 
                 data_dir: str = "data/enhanced_training",
                 models_dir: str = "production_models_v2"):
        """Initialize production model trainer."""
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensemble configuration
        self.ensemble_weights = {
            'enhanced_xgb': 0.60,    # Increased weight for best performing model
            'lightgbm': 0.40,        # Reduced but still significant
        }
        
        # Optimized hyperparameters for target <5% MAPE
        self.xgb_params = {
            'n_estimators': 500,        # More trees for better learning
            'max_depth': 6,             # Moderate depth to prevent overfitting
            'learning_rate': 0.05,      # Lower learning rate for stability
            'subsample': 0.8,           # Prevent overfitting
            'colsample_bytree': 0.8,    # Feature sampling
            'reg_alpha': 0.1,           # L1 regularization
            'reg_lambda': 1.0,          # L2 regularization
            'random_state': 42,
            'n_jobs': -1
        }
        
        self.lgb_params = {
            'n_estimators': 500,
            'max_depth': 8,
            'learning_rate': 0.05,
            'num_leaves': 64,           # Reduced to prevent overfitting
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'verbose': -1,
            'n_jobs': -1
        }
    
    def load_and_clean_data(self, zone: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load and clean enhanced training data with realistic zone load validation."""
        train_file = self.data_dir / f"{zone}_enhanced_train.parquet"
        val_file = self.data_dir / f"{zone}_enhanced_val.parquet"
        
        if not train_file.exists() or not val_file.exists():
            raise FileNotFoundError(f"Enhanced datasets not found for zone {zone}")
        
        train_df = pd.read_parquet(train_file)
        val_df = pd.read_parquet(val_file)
        
        # Define realistic load ranges for CAISO zones
        load_ranges = {
            'SCE': {'min': 6000, 'max': 25000},    # Southern California Edison
            'SP15': {'min': 1500, 'max': 7000},    # North of Path 15
            'PGE': {'min': 3000, 'max': 12000},    # Pacific Gas & Electric (if used)
            'SDGE': {'min': 1000, 'max': 4000},    # San Diego Gas & Electric (if used)
        }
        
        if zone in load_ranges:
            min_load = load_ranges[zone]['min']
            max_load = load_ranges[zone]['max']
            
            # Apply realistic load range filtering
            for df_name, df in [('train', train_df), ('val', val_df)]:
                initial_count = len(df)
                
                # Remove physically impossible load values
                realistic_mask = (df['load'] >= min_load) & (df['load'] <= max_load)
                unrealistic_count = (~realistic_mask).sum()
                
                if unrealistic_count > 0:
                    logger.warning(f"Removing {unrealistic_count} unrealistic load values from {zone} {df_name} data")
                    logger.info(f"  Removed values outside {min_load:,}-{max_load:,} MW range")
                    df.drop(df[~realistic_mask].index, inplace=True)
                
                # Additional statistical outlier removal within realistic range
                if len(df) > 10:
                    load_median = df['load'].median()
                    load_mad = np.median(np.abs(df['load'] - load_median))
                    
                    # Use modified z-score with MAD (more robust than std)
                    mad_threshold = 3.5  # Conservative threshold
                    modified_z = 0.6745 * (df['load'] - load_median) / load_mad if load_mad > 0 else 0
                    outlier_mask = np.abs(modified_z) > mad_threshold
                    
                    outlier_count = outlier_mask.sum()
                    if outlier_count > 0:
                        logger.info(f"Removing {outlier_count} statistical outliers from {zone} {df_name} data")
                        df.drop(df[outlier_mask].index, inplace=True)
                
                final_count = len(df)
                removed_pct = (initial_count - final_count) / initial_count * 100
                logger.info(f"{zone} {df_name}: {initial_count} → {final_count} samples ({removed_pct:.1f}% removed)")
        
        # Ensure we have enough data for training
        if len(train_df) < 50 or len(val_df) < 10:
            raise ValueError(f"Insufficient clean data for {zone}: {len(train_df)} train, {len(val_df)} val samples")
        
        logger.info(f"Final {zone} data: {len(train_df)} train, {len(val_df)} val samples")
        logger.info(f"Clean load range: {train_df['load'].min():.1f} - {train_df['load'].max():.1f} MW")
        
        return train_df, val_df
    
    def prepare_features_with_scaling(self, train_df: pd.DataFrame, val_df: pd.DataFrame, zone: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
        """Prepare features with proper scaling for production models."""
        
        # Define feature columns (excluding metadata and target)
        exclude_cols = [
            'timestamp', 'load', 'zone', 'resource_name', 'region', 
            'data_source', 'date', 'month_day', 'sample_weight'
        ]
        
        # Get feature columns
        feature_cols = [col for col in train_df.columns if col not in exclude_cols]
        
        # Fix problematic lag features by capping extreme values
        for df in [train_df, val_df]:
            for col in feature_cols:
                if 'lag' in col or 'ma_' in col:
                    # Cap lag features to reasonable ranges
                    q99 = df[col].quantile(0.99)
                    q01 = df[col].quantile(0.01)
                    df[col] = df[col].clip(lower=q01, upper=q99)
        
        # Prepare feature matrices
        X_train = train_df[feature_cols].values
        X_val = val_df[feature_cols].values
        y_train = train_df['load'].values
        y_val = val_df['load'].values
        sample_weights = train_df['sample_weight'].values
        
        # Apply robust scaling (less sensitive to outliers than StandardScaler)
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        
        logger.info(f"Prepared {zone} features:")
        logger.info(f"  Features: {len(feature_cols)} ({', '.join(feature_cols[:5])}...)")
        logger.info(f"  Training: {X_train_scaled.shape}, Validation: {X_val_scaled.shape}")
        logger.info(f"  Target range: {y_train.min():.1f} - {y_train.max():.1f} MW")
        
        return X_train_scaled, X_val_scaled, y_train, y_val, sample_weights, scaler
    
    def train_enhanced_xgboost(self, X_train: np.ndarray, y_train: np.ndarray,
                              X_val: np.ndarray, y_val: np.ndarray,
                              sample_weight: np.ndarray) -> xgb.XGBRegressor:
        """Train enhanced XGBoost with optimized parameters."""
        logger.info("Training enhanced XGBoost with optimized parameters...")
        
        model = xgb.XGBRegressor(**self.xgb_params)
        
        # Train with validation monitoring
        model.fit(
            X_train, y_train,
            sample_weight=sample_weight,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        return model
    
    def train_lightgbm(self, X_train: np.ndarray, y_train: np.ndarray,
                      X_val: np.ndarray, y_val: np.ndarray,
                      sample_weight: np.ndarray) -> lgb.LGBMRegressor:
        """Train optimized LightGBM model."""
        logger.info("Training optimized LightGBM model...")
        
        model = lgb.LGBMRegressor(**self.lgb_params)
        
        model.fit(
            X_train, y_train,
            sample_weight=sample_weight,
            eval_set=[(X_val, y_val)]
        )
        
        return model
    
    def create_ensemble_predictions(self, models: Dict[str, Any], X: np.ndarray) -> np.ndarray:
        """Create optimized ensemble predictions."""
        xgb_pred = models['enhanced_xgb'].predict(X)
        lgb_pred = models['lightgbm'].predict(X)
        
        # Apply ensemble weights
        ensemble_pred = (
            self.ensemble_weights['enhanced_xgb'] * xgb_pred +
            self.ensemble_weights['lightgbm'] * lgb_pred
        )
        
        # Apply bounds checking to prevent unrealistic predictions
        ensemble_pred = np.clip(ensemble_pred, 0, 50000)  # Cap at reasonable MW range
        
        return ensemble_pred
    
    def calculate_detailed_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                 val_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive performance metrics."""
        # Overall metrics
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # Evening peak specific metrics
        evening_mask = val_df.get('is_evening_peak', pd.Series([0]*len(val_df))) == 1
        if evening_mask.any():
            evening_true = y_true[evening_mask]
            evening_pred = y_pred[evening_mask]
            evening_mape = np.mean(np.abs((evening_true - evening_pred) / evening_true)) * 100
            evening_r2 = r2_score(evening_true, evening_pred)
        else:
            evening_mape = mape
            evening_r2 = r2
        
        # Peak hour metrics (7-8 PM focus)
        peak_mask = val_df.get('hour', pd.Series([0]*len(val_df))).between(19, 20)
        if peak_mask.any():
            peak_true = y_true[peak_mask]
            peak_pred = y_pred[peak_mask]
            peak_mape = np.mean(np.abs((peak_true - peak_pred) / peak_true)) * 100
        else:
            peak_mape = mape
        
        return {
            'overall_mape': mape,
            'evening_peak_mape': evening_mape,
            'peak_hour_mape': peak_mape,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'evening_r2': evening_r2,
            'validation_samples': len(y_true)
        }
    
    def train_production_models(self, zone: str) -> Dict[str, Any]:
        """Complete production model training pipeline for a zone."""
        logger.info(f"Training production models for {zone} zone")
        
        # Load and clean data
        train_df, val_df = self.load_and_clean_data(zone)
        
        # Prepare features with scaling
        X_train, X_val, y_train, y_val, sample_weights, scaler = self.prepare_features_with_scaling(
            train_df, val_df, zone
        )
        
        # Train models
        models = {}
        models['enhanced_xgb'] = self.train_enhanced_xgboost(
            X_train, y_train, X_val, y_val, sample_weights
        )
        models['lightgbm'] = self.train_lightgbm(
            X_train, y_train, X_val, y_val, sample_weights
        )
        models['scaler'] = scaler  # Include scaler for production use
        
        # Generate ensemble predictions
        ensemble_pred = self.create_ensemble_predictions(models, X_val)
        
        # Calculate comprehensive metrics
        metrics = self.calculate_detailed_metrics(y_val, ensemble_pred, val_df)
        
        logger.info(f"{zone} Production Model Performance:")
        logger.info(f"  Overall MAPE: {metrics['overall_mape']:.2f}%")
        logger.info(f"  Evening Peak MAPE: {metrics['evening_peak_mape']:.2f}%")
        logger.info(f"  Peak Hour MAPE: {metrics['peak_hour_mape']:.2f}%")
        logger.info(f"  R²: {metrics['r2']:.4f}")
        logger.info(f"  RMSE: {metrics['rmse']:.2f} MW")
        
        return models, metrics
    
    def save_production_models(self, zone: str, models: Dict[str, Any], 
                             metrics: Dict[str, float]) -> Dict[str, str]:
        """Save production models with metadata."""
        zone_dir = self.models_dir / zone
        zone_dir.mkdir(parents=True, exist_ok=True)
        
        # Save models
        model_files = {}
        for model_name, model in models.items():
            if model_name != 'scaler':
                model_file = zone_dir / f"{model_name}_production.pkl"
                with open(model_file, 'wb') as f:
                    pickle.dump(model, f)
                model_files[model_name] = str(model_file)
        
        # Save scaler separately
        scaler_file = zone_dir / "feature_scaler.pkl"
        with open(scaler_file, 'wb') as f:
            pickle.dump(models['scaler'], f)
        model_files['scaler'] = str(scaler_file)
        
        # Save metadata
        metadata = {
            'zone': zone,
            'training_date': datetime.now().isoformat(),
            'model_version': 'production_v2',
            'ensemble_weights': self.ensemble_weights,
            'hyperparameters': {
                'xgb': self.xgb_params,
                'lgb': self.lgb_params
            },
            'performance_metrics': metrics,
            'target_achieved': bool(metrics['evening_peak_mape'] < 5.0)
        }
        
        metadata_file = zone_dir / "production_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        model_files['metadata'] = str(metadata_file)
        
        logger.info(f"Saved production models for {zone} to: {zone_dir}")
        return model_files
    
    def execute_production_training(self, zones: List[str] = None) -> Dict[str, Dict]:
        """Execute production model training for all zones."""
        if zones is None:
            zones = ['SCE', 'SP15']
        
        logger.info(f"Starting production model training for zones: {zones}")
        
        results = {}
        
        for zone in zones:
            try:
                logger.info(f"Training production models for {zone}...")
                models, metrics = self.train_production_models(zone)
                model_files = self.save_production_models(zone, models, metrics)
                
                results[zone] = {
                    'metrics': metrics,
                    'files': model_files,
                    'target_met': metrics['evening_peak_mape'] < 5.0
                }
                
                logger.info(f"✅ Completed {zone} - Evening MAPE: {metrics['evening_peak_mape']:.2f}%")
                
            except Exception as e:
                logger.error(f"❌ Failed to train {zone} models: {e}")
                results[zone] = {'error': str(e)}
        
        return results

def execute_production_training():
    """Execute production model training with fixes."""
    print("=== Production Model Training with Preprocessing Fixes ===")
    print("Targeting <5% evening peak MAPE with:")
    print("1. Robust data cleaning and outlier removal")
    print("2. Proper feature scaling with RobustScaler")
    print("3. Optimized hyperparameters for accuracy")
    print("4. Enhanced ensemble with 60/40 XGB/LightGBM weights")
    print("5. Comprehensive bounds checking")
    
    trainer = ProductionModelTrainer()
    
    try:
        results = trainer.execute_production_training(['SCE', 'SP15'])
        
        print(f"\n=== Production Training Results ===")
        
        total_zones = len(results)
        successful_zones = sum(1 for r in results.values() if 'error' not in r)
        target_met_zones = sum(1 for r in results.values() 
                             if 'error' not in r and r.get('target_met', False))
        
        print(f"Zones processed: {successful_zones}/{total_zones}")
        print(f"Target met (<5% evening MAPE): {target_met_zones}/{successful_zones}")
        
        for zone, result in results.items():
            if 'error' in result:
                print(f"\n❌ {zone}: {result['error']}")
            else:
                metrics = result['metrics']
                status = "✅ TARGET MET" if result['target_met'] else "⚠️  NEEDS TUNING"
                print(f"\n{status} {zone}:")
                print(f"  Overall MAPE: {metrics['overall_mape']:.2f}%")
                print(f"  Evening Peak MAPE: {metrics['evening_peak_mape']:.2f}%")
                print(f"  Peak Hour MAPE: {metrics['peak_hour_mape']:.2f}%")
                print(f"  R²: {metrics['r2']:.4f}")
        
        if target_met_zones == successful_zones:
            print(f"\n🎯 SUCCESS: All zones achieve <5% evening peak MAPE target!")
        elif target_met_zones > 0:
            print(f"\n👍 PROGRESS: {target_met_zones} zone(s) meet target, continue refinement")
        else:
            print(f"\n🔧 CONTINUE: Additional hyperparameter tuning needed")
        
        return results
        
    except Exception as e:
        print(f"❌ Production training failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    execute_production_training()