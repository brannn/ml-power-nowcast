#!/usr/bin/env python3
"""
Advanced SCE Model Optimization
Addresses SCE zone's 13.61% evening peak MAPE through advanced techniques.

Based on PRODUCTION_RESULTS_SUMMARY.md findings:
- SCE had insufficient clean data (195 samples vs 83,387 for training)
- Needs specialized approach to achieve <5% evening peak MAPE target
- SP15 successfully achieved 2.82% MAPE as proof-of-concept
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pickle
import json
import logging
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from sklearn.preprocessing import RobustScaler
import xgboost as xgb
import lightgbm as lgb
from scipy import stats

logger = logging.getLogger(__name__)

class AdvancedSCEOptimizer:
    """Advanced optimization targeting SCE zone's specific challenges."""
    
    def __init__(self, data_dir: str = "backup_s3_data/processed"):
        """Initialize advanced SCE optimizer."""
        self.data_dir = Path(data_dir)
        self.zone = "SCE"
        
        # SCE-specific constraints based on physical reality
        self.sce_load_range = (6000, 25000)  # MW - realistic for 15M people served
        
        # Advanced optimization parameters
        self.optimization_strategies = [
            'enhanced_feature_selection',
            'advanced_hyperparameter_tuning', 
            'ensemble_refinement',
            'temporal_pattern_enhancement',
            'transfer_learning_from_sp15'
        ]
        
        # Target metrics
        self.target_evening_mape = 5.0
        self.minimum_r2 = 0.5
        
    def load_enhanced_sce_data(self) -> pd.DataFrame:
        """Load SCE data with enhanced preprocessing for maximum data retention."""
        
        # Load the 5-year system data
        system_file = self.data_dir / "power" / "caiso" / "system_5year_20250829.parquet"
        if not system_file.exists():
            raise FileNotFoundError(f"System data not found: {system_file}")
        
        df = pd.read_parquet(system_file)
        logger.info(f"Loaded system data: {len(df)} total samples")
        
        # Filter for SCE zone
        sce_data = df[df['zone'] == 'SCE'].copy()
        logger.info(f"SCE samples before cleaning: {len(sce_data)}")
        
        # Apply more lenient data validation to retain more samples
        # Based on analysis, 66.7% was removed - try less aggressive filtering
        
        # Remove only extremely unrealistic values (not just conservative range)
        min_reasonable = 4000  # MW - lower threshold than previous 6000
        max_reasonable = 30000  # MW - higher threshold than previous 25000
        
        valid_load_mask = (
            (sce_data['load'] >= min_reasonable) & 
            (sce_data['load'] <= max_reasonable) &
            (sce_data['load'].notna())
        )
        
        sce_data = sce_data[valid_load_mask].copy()
        logger.info(f"SCE samples after lenient validation: {len(sce_data)}")
        
        # Sort by timestamp and reset index
        sce_data = sce_data.sort_values('timestamp').reset_index(drop=True)
        
        return sce_data
    
    def advanced_feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create advanced features specifically targeting SCE patterns."""
        
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        # Basic temporal features
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['month'] = df.index.month
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Advanced evening peak features (expanded from successful approach)
        df['is_evening_peak'] = ((df['hour'] >= 17) & (df['hour'] <= 21)).astype(int)
        df['evening_hour_intensity'] = np.where(
            df['is_evening_peak'] == 1,
            1.0 - abs(df['hour'] - 19) / 3.0,  # Peak at 19:00
            0.0
        )
        df['hours_from_peak'] = abs(df['hour'] - 19)
        
        # SCE-specific multipliers (higher evening demand than SP15)
        df['sce_evening_multiplier'] = np.where(df['is_evening_peak'] == 1, 1.20, 1.0)
        df['work_evening_overlap'] = df['is_evening_peak'] * (1 - df['is_weekend'])
        
        # Advanced lag features with careful selection
        for lag in [1, 2, 3, 6, 12, 24]:
            df[f'load_lag_{lag}h'] = df['load'].shift(lag)
        
        # Rolling statistics for trend capture
        for window in [6, 12, 24]:
            df[f'load_rolling_mean_{window}h'] = df['load'].rolling(window=window, min_periods=1).mean()
            df[f'load_rolling_std_{window}h'] = df['load'].rolling(window=window, min_periods=1).std()
        
        # Cyclical time encoding for better pattern capture
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Interaction features for evening patterns
        df['evening_weekend_interaction'] = df['is_evening_peak'] * df['is_weekend']
        df['evening_month_interaction'] = df['is_evening_peak'] * df['month']
        
        # Advanced demand pattern features
        df['peak_demand_indicator'] = (df['load'] > df['load'].quantile(0.9)).astype(int)
        df['off_peak_indicator'] = (df['load'] < df['load'].quantile(0.3)).astype(int)
        
        # Remove rows with NaN values from lag features
        df = df.dropna().reset_index()
        
        logger.info(f"Advanced feature engineering complete: {len(df)} samples, {len(df.columns)} features")
        
        return df
    
    def create_temporal_weighted_dataset(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """Create dataset with advanced temporal weighting strategy."""
        
        # Calculate recency weights (stronger than previous approach)
        df['days_from_latest'] = (df['timestamp'].max() - df['timestamp']).dt.days
        
        # More aggressive temporal weighting
        recent_weight = 5.0  # Increased from 3x
        evening_weight = 3.0  # Increased from 2.5x
        
        # Base recency weighting
        df['recency_weight'] = np.exp(-df['days_from_latest'] / 365.0) * recent_weight
        
        # Evening peak enhancement
        df['evening_weight'] = np.where(df['is_evening_peak'] == 1, evening_weight, 1.0)
        
        # Combined weighting
        df['sample_weight'] = df['recency_weight'] * df['evening_weight']
        
        # Normalize weights
        df['sample_weight'] = df['sample_weight'] / df['sample_weight'].mean()
        
        logger.info(f"Temporal weighting applied - mean weight: {df['sample_weight'].mean():.2f}, "
                   f"evening samples: {df[df['is_evening_peak']==1]['sample_weight'].mean():.2f}")
        
        return df, df['sample_weight'].values
    
    def advanced_hyperparameter_optimization(self, X_train: pd.DataFrame, y_train: pd.Series, 
                                           sample_weights: np.ndarray) -> Dict[str, Any]:
        """Perform advanced hyperparameter optimization for SCE zone."""
        
        logger.info("Starting advanced hyperparameter optimization for SCE...")
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        
        # Enhanced XGBoost parameter space
        xgb_param_space = {
            'n_estimators': [300, 500, 800, 1000],
            'learning_rate': [0.01, 0.05, 0.1, 0.15],
            'max_depth': [3, 4, 5, 6, 7],
            'subsample': [0.7, 0.8, 0.9, 1.0],
            'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
            'reg_alpha': [0, 0.1, 0.5, 1.0],
            'reg_lambda': [0.1, 0.5, 1.0, 2.0]
        }
        
        # Enhanced LightGBM parameter space  
        lgb_param_space = {
            'n_estimators': [300, 500, 800, 1000],
            'learning_rate': [0.01, 0.05, 0.1, 0.15],
            'max_depth': [3, 4, 5, 6, 7],
            'subsample': [0.7, 0.8, 0.9, 1.0],
            'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
            'reg_alpha': [0, 0.1, 0.5, 1.0],
            'reg_lambda': [0.1, 0.5, 1.0, 2.0],
            'num_leaves': [31, 50, 100, 150],
            'min_child_samples': [10, 20, 30, 50]
        }
        
        best_models = {}
        
        # XGBoost optimization
        logger.info("Optimizing XGBoost...")
        xgb_model = xgb.XGBRegressor(random_state=42, n_jobs=-1)
        
        xgb_search = RandomizedSearchCV(
            xgb_model,
            xgb_param_space,
            n_iter=50,
            cv=tscv,
            scoring='neg_mean_absolute_percentage_error',
            random_state=42,
            n_jobs=-1,
            verbose=1
        )
        
        xgb_search.fit(X_train, y_train, sample_weight=sample_weights)
        best_models['xgboost'] = xgb_search.best_estimator_
        
        logger.info(f"XGBoost best score: {-xgb_search.best_score_:.4f} MAPE")
        logger.info(f"XGBoost best params: {xgb_search.best_params_}")
        
        # LightGBM optimization
        logger.info("Optimizing LightGBM...")
        lgb_model = lgb.LGBMRegressor(random_state=42, n_jobs=-1, verbose=-1)
        
        lgb_search = RandomizedSearchCV(
            lgb_model,
            lgb_param_space,
            n_iter=50,
            cv=tscv,
            scoring='neg_mean_absolute_percentage_error',
            random_state=42,
            n_jobs=-1,
            verbose=1
        )
        
        lgb_search.fit(X_train, y_train, sample_weight=sample_weights)
        best_models['lightgbm'] = lgb_search.best_estimator_
        
        logger.info(f"LightGBM best score: {-lgb_search.best_score_:.4f} MAPE")
        logger.info(f"LightGBM best params: {lgb_search.best_params_}")
        
        return best_models
    
    def evaluate_evening_peak_performance(self, model: Any, X_test: pd.DataFrame, 
                                        y_test: pd.Series) -> Dict[str, float]:
        """Evaluate model specifically on evening peak hours."""
        
        # Generate predictions
        y_pred = model.predict(X_test)
        y_pred = np.clip(y_pred, self.sce_load_range[0], self.sce_load_range[1])
        
        # Overall metrics
        overall_mape = mean_absolute_percentage_error(y_test, y_pred) * 100
        overall_r2 = r2_score(y_test, y_pred)
        overall_rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
        
        # Evening peak specific metrics
        evening_mask = X_test['is_evening_peak'] == 1
        if evening_mask.sum() > 0:
            evening_y_test = y_test[evening_mask]
            evening_y_pred = y_pred[evening_mask]
            
            evening_mape = mean_absolute_percentage_error(evening_y_test, evening_y_pred) * 100
            evening_r2 = r2_score(evening_y_test, evening_y_pred)
            evening_rmse = np.sqrt(np.mean((evening_y_test - evening_y_pred) ** 2))
        else:
            evening_mape = float('inf')
            evening_r2 = -float('inf')
            evening_rmse = float('inf')
        
        return {
            'overall_mape': overall_mape,
            'overall_r2': overall_r2,
            'overall_rmse': overall_rmse,
            'evening_peak_mape': evening_mape,
            'evening_peak_r2': evening_r2,
            'evening_peak_rmse': evening_rmse,
            'evening_samples': evening_mask.sum(),
            'total_samples': len(y_test)
        }
    
    def run_advanced_optimization(self) -> Dict[str, Any]:
        """Execute complete advanced optimization workflow for SCE."""
        
        logger.info("=== Advanced SCE Model Optimization ===")
        
        # Load enhanced data
        df = self.load_enhanced_sce_data()
        
        if len(df) < 1000:
            logger.warning(f"Limited SCE data available: {len(df)} samples. Results may be suboptimal.")
        
        # Advanced feature engineering
        df = self.advanced_feature_engineering(df)
        
        # Create temporal weighted dataset
        df, sample_weights = self.create_temporal_weighted_dataset(df)
        
        # Prepare features and target
        feature_cols = [col for col in df.columns if col not in 
                       ['timestamp', 'load', 'zone', 'resource_name', 'region', 'data_source',
                        'days_from_latest', 'recency_weight', 'evening_weight', 'sample_weight']]
        
        X = df[feature_cols]
        y = df['load']
        
        logger.info(f"Feature matrix: {X.shape}, target: {y.shape}")
        logger.info(f"Features: {feature_cols}")
        
        # Time-based train/test split (80/20)
        split_idx = int(len(df) * 0.8)
        
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        train_weights = sample_weights[:split_idx]
        
        # Scale features
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns, index=X_train.index)
        X_test_scaled = pd.DataFrame(X_test_scaled, columns=X_test.columns, index=X_test.index)
        
        # Advanced hyperparameter optimization
        best_models = self.advanced_hyperparameter_optimization(X_train_scaled, y_train, train_weights)
        
        # Evaluate models
        results = {}
        for model_name, model in best_models.items():
            logger.info(f"Evaluating {model_name}...")
            metrics = self.evaluate_evening_peak_performance(model, X_test_scaled, y_test)
            metrics['model_name'] = model_name
            results[model_name] = metrics
            
            logger.info(f"{model_name} Results:")
            logger.info(f"  Evening Peak MAPE: {metrics['evening_peak_mape']:.2f}%")
            logger.info(f"  Overall MAPE: {metrics['overall_mape']:.2f}%")
            logger.info(f"  R²: {metrics['overall_r2']:.4f}")
        
        # Create ensemble based on ML-004 architecture
        logger.info("Creating optimized ensemble...")
        
        # Weights based on evening peak performance 
        xgb_evening_mape = results['xgboost']['evening_peak_mape']
        lgb_evening_mape = results['lightgbm']['evening_peak_mape']
        
        if xgb_evening_mape < lgb_evening_mape:
            # XGBoost performing better - increase its weight
            xgb_weight = 0.65
            lgb_weight = 0.35
        else:
            # LightGBM performing better - increase its weight
            xgb_weight = 0.45
            lgb_weight = 0.55
        
        # Generate ensemble predictions
        xgb_pred = best_models['xgboost'].predict(X_test_scaled)
        lgb_pred = best_models['lightgbm'].predict(X_test_scaled)
        
        ensemble_pred = xgb_weight * xgb_pred + lgb_weight * lgb_pred
        ensemble_pred = np.clip(ensemble_pred, self.sce_load_range[0], self.sce_load_range[1])
        
        # Evaluate ensemble
        ensemble_metrics = self.evaluate_evening_peak_performance_direct(ensemble_pred, X_test_scaled, y_test)
        ensemble_metrics['model_name'] = 'ensemble'
        ensemble_metrics['xgb_weight'] = xgb_weight
        ensemble_metrics['lgb_weight'] = lgb_weight
        results['ensemble'] = ensemble_metrics
        
        logger.info(f"Ensemble Results:")
        logger.info(f"  Evening Peak MAPE: {ensemble_metrics['evening_peak_mape']:.2f}%")
        logger.info(f"  Overall MAPE: {ensemble_metrics['overall_mape']:.2f}%")
        logger.info(f"  R²: {ensemble_metrics['overall_r2']:.4f}")
        logger.info(f"  Target achieved: {ensemble_metrics['evening_peak_mape'] < self.target_evening_mape}")
        
        # Save optimized models if they meet criteria
        best_evening_mape = min([r['evening_peak_mape'] for r in results.values()])
        
        if best_evening_mape < 10.0:  # Significant improvement threshold
            self.save_optimized_models(best_models, scaler, results, df.columns.tolist())
            logger.info("✅ Optimized models saved - significant improvement achieved")
        else:
            logger.warning("⚠️ Models did not achieve sufficient improvement - not saved")
        
        return {
            'optimization_results': results,
            'best_evening_mape': best_evening_mape,
            'target_achieved': best_evening_mape < self.target_evening_mape,
            'data_samples': len(df),
            'feature_count': len(feature_cols),
            'recommendations': self.generate_recommendations(results, len(df))
        }
    
    def evaluate_evening_peak_performance_direct(self, y_pred: np.ndarray, X_test: pd.DataFrame, 
                                               y_test: pd.Series) -> Dict[str, float]:
        """Direct evaluation of predictions for evening peak performance."""
        
        # Overall metrics
        overall_mape = mean_absolute_percentage_error(y_test, y_pred) * 100
        overall_r2 = r2_score(y_test, y_pred)
        overall_rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
        
        # Evening peak specific metrics
        evening_mask = X_test['is_evening_peak'] == 1
        if evening_mask.sum() > 0:
            evening_y_test = y_test[evening_mask]
            evening_y_pred = y_pred[evening_mask]
            
            evening_mape = mean_absolute_percentage_error(evening_y_test, evening_y_pred) * 100
            evening_r2 = r2_score(evening_y_test, evening_y_pred)
            evening_rmse = np.sqrt(np.mean((evening_y_test - evening_y_pred) ** 2))
        else:
            evening_mape = float('inf')
            evening_r2 = -float('inf')
            evening_rmse = float('inf')
        
        return {
            'overall_mape': overall_mape,
            'overall_r2': overall_r2,
            'overall_rmse': overall_rmse,
            'evening_peak_mape': evening_mape,
            'evening_peak_r2': evening_r2,
            'evening_peak_rmse': evening_rmse,
            'evening_samples': evening_mask.sum(),
            'total_samples': len(y_test)
        }
    
    def save_optimized_models(self, models: Dict[str, Any], scaler: RobustScaler, 
                            results: Dict[str, Any], feature_names: List[str]) -> None:
        """Save optimized models with metadata."""
        
        models_dir = Path("optimized_sce_models")
        models_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save models
        for model_name, model in models.items():
            model_file = models_dir / f"{model_name}_{timestamp}.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
        
        # Save scaler
        scaler_file = models_dir / f"scaler_{timestamp}.pkl"
        with open(scaler_file, 'wb') as f:
            pickle.dump(scaler, f)
        
        # Save metadata
        metadata = {
            'timestamp': timestamp,
            'zone': self.zone,
            'optimization_type': 'advanced_sce_optimization',
            'models': results,
            'feature_names': feature_names,
            'model_files': {name: f"{name}_{timestamp}.pkl" for name in models.keys()},
            'scaler_file': f"scaler_{timestamp}.pkl",
            'target_metrics': {
                'target_evening_mape': self.target_evening_mape,
                'minimum_r2': self.minimum_r2
            }
        }
        
        metadata_file = models_dir / f"optimization_metadata_{timestamp}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Optimized models saved to {models_dir}")
    
    def generate_recommendations(self, results: Dict[str, Any], data_samples: int) -> List[str]:
        """Generate specific recommendations based on optimization results."""
        
        recommendations = []
        
        best_evening_mape = min([r['evening_peak_mape'] for r in results.values()])
        
        if best_evening_mape < self.target_evening_mape:
            recommendations.append("🎯 Target achieved! Deploy optimized SCE models to production.")
        elif best_evening_mape < 8.0:
            recommendations.append("📈 Significant improvement achieved. Consider deploying with monitoring.")
        else:
            recommendations.append("🔧 Further optimization needed to achieve target accuracy.")
        
        if data_samples < 5000:
            recommendations.append("📊 Limited training data detected. Consider data augmentation or transfer learning.")
        
        # Model-specific recommendations
        xgb_mape = results['xgboost']['evening_peak_mape']
        lgb_mape = results['lightgbm']['evening_peak_mape']
        
        if abs(xgb_mape - lgb_mape) > 5.0:
            recommendations.append("⚖️ Large performance difference between models suggests ensemble reweighting needed.")
        
        return recommendations

def optimize_sce_models():
    """Execute SCE model optimization workflow."""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    optimizer = AdvancedSCEOptimizer()
    results = optimizer.run_advanced_optimization()
    
    print("\n" + "="*60)
    print("ADVANCED SCE OPTIMIZATION RESULTS")
    print("="*60)
    
    print(f"Target Evening Peak MAPE: <{optimizer.target_evening_mape}%")
    print(f"Best Evening Peak MAPE Achieved: {results['best_evening_mape']:.2f}%")
    print(f"Target Achieved: {'✅ YES' if results['target_achieved'] else '❌ NO'}")
    print(f"Training Data Samples: {results['data_samples']:,}")
    print(f"Advanced Features: {results['feature_count']}")
    
    print(f"\nModel Performance Summary:")
    for model_name, metrics in results['optimization_results'].items():
        print(f"  {model_name.upper()}:")
        print(f"    Evening Peak MAPE: {metrics['evening_peak_mape']:.2f}%")
        print(f"    Overall MAPE: {metrics['overall_mape']:.2f}%")
        print(f"    R²: {metrics['overall_r2']:.4f}")
    
    print(f"\nRecommendations:")
    for rec in results['recommendations']:
        print(f"  {rec}")
    
    return results

if __name__ == "__main__":
    optimize_sce_models()