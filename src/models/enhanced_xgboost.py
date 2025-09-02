#!/usr/bin/env python3
"""
Enhanced XGBoost Model with Weather Forecast Features

This module implements the enhanced XGBoost model outlined in 
planning/weather_forecast_integration.md, combining historical features
with weather forecast features for improved power demand prediction.

The model follows the feature set specification from Week 5 of the integration plan:
- Existing features: temp_c, humidity, wind_speed, hour, day_of_week, etc.
- New forecast features: temp_forecast_6h, temp_forecast_24h, etc.
- Weather change features: temp_change_rate_6h, weather_volatility_6h
- Extreme weather features: heat_wave_incoming, cold_snap_incoming

Author: ML Power Nowcast System
Created: 2025-08-29
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler, RobustScaler
from dataclasses import dataclass
import joblib

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """
    Configuration for enhanced XGBoost model.

    Attributes:
        target_column: Name of target variable column
        feature_columns: List of feature column names to use
        test_size: Fraction of data to use for testing
        random_state: Random seed for reproducibility
        xgb_params: XGBoost hyperparameters
        use_time_series_split: Whether to use time series cross-validation
        n_splits: Number of splits for time series CV
        use_feature_scaling: Whether to apply feature scaling
        scaling_method: Type of scaling ('standard', 'robust', 'none')
        lag_feature_weight: Weight adjustment for lag features (0.1-1.0)
    """
    target_column: str = 'load'
    feature_columns: Optional[List[str]] = None
    test_size: float = 0.2
    random_state: int = 42
    xgb_params: Optional[Dict] = None
    use_time_series_split: bool = True
    n_splits: int = 5
    use_feature_scaling: bool = True
    scaling_method: str = 'robust'  # 'standard', 'robust', or 'none'
    lag_feature_weight: float = 0.3  # Reduce lag feature dominance

    def __post_init__(self):
        """Set default XGBoost parameters if not provided."""
        if self.xgb_params is None:
            self.xgb_params = {
                'objective': 'reg:squarederror',
                'max_depth': 6,  # Reduced from 8 to prevent overfitting
                'learning_rate': 0.05,  # Reduced for better generalization
                'n_estimators': 1000,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,  # L1 regularization
                'reg_lambda': 1.0,  # L2 regularization
                'random_state': self.random_state,
                'n_jobs': -1,
                'early_stopping_rounds': 50,
                'eval_metric': 'mae'
            }


class EnhancedXGBoostError(Exception):
    """Base exception for enhanced XGBoost operations."""
    pass


class ModelTrainingError(EnhancedXGBoostError):
    """Raised when model training fails."""
    pass


class FeatureSelectionError(EnhancedXGBoostError):
    """Raised when feature selection fails."""
    pass


def get_enhanced_feature_set() -> List[str]:
    """
    Get the enhanced feature set as specified in the integration plan.

    Returns:
        List of feature column names for the enhanced model
    """
    # Base features from existing models
    base_features = [
        'hour', 'day_of_week', 'month', 'quarter', 'is_weekend',
        'hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos',
        'day_of_year_sin', 'day_of_year_cos'
    ]

    # Enhanced temporal features for better pattern learning
    enhanced_temporal_features = [
        'hour_squared', 'hour_cubed', 'hour_quartic',
        'morning_peak', 'afternoon_peak', 'evening_peak', 'night_low',
        'weekend_hour', 'weekday_hour',
        'summer_indicator', 'winter_indicator', 'summer_hour', 'winter_hour',
        'business_day', 'business_hour',
        'hour_sin_2', 'hour_cos_2', 'hour_sin_cos',
        # Extreme temporal features
        'hour_sin_3', 'hour_cos_3', 'hour_sin_4', 'hour_cos_4',
        'hour_sin_6', 'hour_cos_6', 'hour_sin_8', 'hour_cos_8',
        'hour_sin_12', 'hour_cos_12',
        'early_morning', 'morning_ramp', 'midday_peak', 'afternoon_peak',
        'evening_decline', 'overnight_low', 'summer_afternoon', 'summer_evening',
        'winter_morning', 'workday_morning', 'workday_afternoon', 'weekend_midday',
        'ac_hour_14', 'ac_hour_15', 'ac_hour_16', 'ac_hour_17'
    ]

    # Historical weather features (if available)
    weather_features = [
        'temp_c', 'humidity', 'wind_speed_kmh',
        'temp_c_squared', 'cooling_degree_days', 'heating_degree_days',
        'temp_humidity_interaction', 'heat_index_approx'
    ]

    # Power lag features
    lag_features = [
        'load_lag_1h', 'load_lag_24h'
    ]

    # New forecast features (as specified in integration plan)
    forecast_features = [
        'temp_forecast_6h', 'temp_forecast_12h', 'temp_forecast_24h',
        'cooling_forecast_6h', 'heating_forecast_6h',
        'temp_change_rate_6h', 'weather_volatility_6h',
        'heat_wave_incoming', 'cold_snap_incoming'
    ]

    # Combine all features
    enhanced_features = (
        base_features +
        enhanced_temporal_features +
        weather_features +
        lag_features +
        forecast_features
    )

    return enhanced_features


def prepare_training_data(
    df: pd.DataFrame, 
    config: ModelConfig
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Prepare data for model training with proper feature selection.
    
    Args:
        df: DataFrame with unified features
        config: Model configuration
        
    Returns:
        Tuple of (features_df, target_series, selected_features)
        
    Raises:
        FeatureSelectionError: If feature preparation fails
    """
    logger.info("Preparing training data")
    
    try:
        # Get target variable
        if config.target_column not in df.columns:
            raise FeatureSelectionError(f"Target column '{config.target_column}' not found")
        
        target = df[config.target_column].copy()
        
        # Select features
        if config.feature_columns is None:
            # Use enhanced feature set
            candidate_features = get_enhanced_feature_set()
        else:
            candidate_features = config.feature_columns.copy()
        
        # Filter to available features
        available_features = [f for f in candidate_features if f in df.columns]
        missing_features = [f for f in candidate_features if f not in df.columns]
        
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
        
        if not available_features:
            raise FeatureSelectionError("No valid features found")
        
        logger.info(f"Selected {len(available_features)} features from {len(candidate_features)} candidates")
        
        # Create feature matrix
        features = df[available_features].copy()
        
        # Remove rows with missing target values
        valid_mask = target.notna()
        features = features[valid_mask]
        target = target[valid_mask]
        
        logger.info(f"Training data prepared: {len(features)} samples, {len(available_features)} features")
        
        return features, target, available_features
        
    except Exception as e:
        raise FeatureSelectionError(f"Failed to prepare training data: {e}")


def evaluate_model_performance(
    y_true: np.ndarray, 
    y_pred: np.ndarray, 
    model_name: str = "Model"
) -> Dict[str, float]:
    """
    Evaluate model performance with comprehensive metrics.
    
    Args:
        y_true: True target values
        y_pred: Predicted target values
        model_name: Name of the model for logging
        
    Returns:
        Dictionary with performance metrics
    """
    # Calculate metrics
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    
    # Calculate MAPE (avoiding division by zero)
    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    
    metrics = {
        'mae': mae,
        'mse': mse,
        'rmse': rmse,
        'r2': r2,
        'mape': mape
    }
    
    # Log metrics
    logger.info(f"{model_name} Performance Metrics:")
    logger.info(f"  MAE: {mae:.2f}")
    logger.info(f"  RMSE: {rmse:.2f}")
    logger.info(f"  R²: {r2:.4f}")
    logger.info(f"  MAPE: {mape:.2f}%")
    
    return metrics


class EnhancedXGBoostModel:
    """
    Enhanced XGBoost model with weather forecast features.
    
    This class implements the enhanced XGBoost model as specified in the
    weather forecast integration plan, combining historical and forecast features.
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """
        Initialize enhanced XGBoost model.

        Args:
            config: Model configuration (uses defaults if None)
        """
        self.config = config if config is not None else ModelConfig()
        self.model = None
        self.feature_names = None
        self.scaler = None
        self.is_trained = False
        self.training_metrics = {}
        self.validation_metrics = {}

        # Initialize scaler if feature scaling is enabled
        if self.config.use_feature_scaling:
            if self.config.scaling_method == 'standard':
                self.scaler = StandardScaler()
            elif self.config.scaling_method == 'robust':
                self.scaler = RobustScaler()
            else:
                self.scaler = None

    def _apply_lag_feature_weighting(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Apply weighting to lag features to reduce their dominance.

        Args:
            features: Feature matrix

        Returns:
            Feature matrix with weighted lag features
        """
        if self.config.lag_feature_weight >= 1.0:
            return features

        features_weighted = features.copy()
        lag_columns = [col for col in features.columns if 'lag' in col.lower()]

        if lag_columns:
            logger.info(f"Applying weight {self.config.lag_feature_weight} to {len(lag_columns)} lag features")
            for col in lag_columns:
                # Scale down lag features to reduce their influence
                features_weighted[col] = features_weighted[col] * self.config.lag_feature_weight

        return features_weighted

    def _scale_features(self, features: pd.DataFrame, fit_scaler: bool = True) -> pd.DataFrame:
        """
        Apply feature scaling to balance feature importance.

        Args:
            features: Feature matrix
            fit_scaler: Whether to fit the scaler (True for training, False for prediction)

        Returns:
            Scaled feature matrix
        """
        if not self.config.use_feature_scaling or self.scaler is None:
            return features

        features_scaled = features.copy()

        if fit_scaler:
            # Fit and transform for training
            scaled_values = self.scaler.fit_transform(features_scaled)
            features_scaled = pd.DataFrame(scaled_values, columns=features_scaled.columns, index=features_scaled.index)
            logger.info(f"Applied {self.config.scaling_method} scaling to {len(features.columns)} features")
        else:
            # Transform only for prediction
            scaled_values = self.scaler.transform(features_scaled)
            features_scaled = pd.DataFrame(scaled_values, columns=features_scaled.columns, index=features_scaled.index)

        return features_scaled

    def train(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        validation_split: bool = True,
        sample_weights: Optional[pd.Series] = None
    ) -> Dict[str, float]:
        """
        Train the enhanced XGBoost model.

        Args:
            features: Feature matrix
            target: Target variable
            validation_split: Whether to use validation split
            sample_weights: Optional sample weights for hybrid training

        Returns:
            Dictionary with training metrics
            
        Raises:
            ModelTrainingError: If training fails
        """
        logger.info("Training enhanced XGBoost model")
        
        try:
            # Store feature names
            self.feature_names = list(features.columns)

            # Handle missing values
            features_clean = features.fillna(0)  # Simple imputation for now

            # Apply lag feature weighting to reduce dominance
            features_weighted = self._apply_lag_feature_weighting(features_clean)

            # Apply feature scaling
            features_processed = self._scale_features(features_weighted, fit_scaler=True)

            if validation_split:
                # Split data for validation
                if sample_weights is not None:
                    # Ensure sample_weights is properly aligned and converted
                    if hasattr(sample_weights, 'values'):
                        sample_weights_array = sample_weights.values
                    else:
                        sample_weights_array = sample_weights

                    X_train, X_val, y_train, y_val, w_train, w_val = train_test_split(
                        features_processed, target, sample_weights_array,
                        test_size=self.config.test_size,
                        random_state=self.config.random_state,
                        shuffle=False  # Preserve temporal order
                    )
                else:
                    X_train, X_val, y_train, y_val = train_test_split(
                        features_processed, target,
                        test_size=self.config.test_size,
                        random_state=self.config.random_state,
                        shuffle=False  # Preserve temporal order
                    )
                    w_train, w_val = None, None

                # Create XGBoost model
                self.model = xgb.XGBRegressor(**self.config.xgb_params)

                # Train with early stopping and sample weights
                # Convert DataFrames to numpy arrays for XGBoost
                X_train_array = X_train.values if hasattr(X_train, 'values') else X_train
                y_train_array = y_train.values if hasattr(y_train, 'values') else y_train
                X_val_array = X_val.values if hasattr(X_val, 'values') else X_val
                y_val_array = y_val.values if hasattr(y_val, 'values') else y_val

                self.model.fit(
                    X_train_array, y_train_array,
                    sample_weight=w_train,
                    eval_set=[(X_val_array, y_val_array)],
                    verbose=False
                )
                
                # Evaluate on validation set
                val_pred = self.model.predict(X_val_array)
                self.validation_metrics = evaluate_model_performance(
                    y_val_array, val_pred, "Validation"
                )
                
                # Evaluate on training set
                train_pred = self.model.predict(X_train_array)
                self.training_metrics = evaluate_model_performance(
                    y_train_array, train_pred, "Training"
                )
                
            else:
                # Train on full dataset
                self.model = xgb.XGBRegressor(**self.config.xgb_params)

                # Handle sample weights for full dataset training
                train_sample_weights = None
                if sample_weights is not None:
                    if hasattr(sample_weights, 'values'):
                        train_sample_weights = sample_weights.values
                    else:
                        train_sample_weights = sample_weights

                # Convert to numpy arrays for XGBoost
                features_array = features_processed.values if hasattr(features_processed, 'values') else features_processed
                target_array = target.values if hasattr(target, 'values') else target

                self.model.fit(
                    features_array, target_array,
                    sample_weight=train_sample_weights
                )

                # Evaluate on training set
                features_array = features_processed.values if hasattr(features_processed, 'values') else features_processed
                target_array = target.values if hasattr(target, 'values') else target
                train_pred = self.model.predict(features_array)
                self.training_metrics = evaluate_model_performance(
                    target_array, train_pred, "Training"
                )
            
            self.is_trained = True
            logger.info("Model training completed successfully")
            
            return self.validation_metrics if validation_split else self.training_metrics
            
        except Exception as e:
            raise ModelTrainingError(f"Failed to train model: {e}")
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """
        Make predictions with the trained model.

        Args:
            features: Feature matrix for prediction

        Returns:
            Array of predictions

        Raises:
            ModelTrainingError: If model is not trained
        """
        if not self.is_trained:
            raise ModelTrainingError("Model must be trained before making predictions")

        # Ensure feature order matches training
        if self.feature_names:
            missing_features = [f for f in self.feature_names if f not in features.columns]
            if missing_features:
                logger.warning(f"Missing features for prediction: {missing_features}")
                # Add missing features with zeros
                for feature in missing_features:
                    features[feature] = 0

            # Reorder features to match training
            features = features[self.feature_names]

        # Handle missing values
        features_clean = features.fillna(0)

        # Apply same feature processing as training
        features_weighted = self._apply_lag_feature_weighting(features_clean)
        features_processed = self._scale_features(features_weighted, fit_scaler=False)

        # Convert DataFrame to numpy array for XGBoost (same as training)
        features_array = features_processed.values if hasattr(features_processed, 'values') else features_processed

        return self.model.predict(features_array)
    
    def get_feature_importance(self, importance_type: str = 'gain') -> pd.DataFrame:
        """
        Get feature importance from the trained model.
        
        Args:
            importance_type: Type of importance ('gain', 'weight', 'cover')
            
        Returns:
            DataFrame with feature importance
            
        Raises:
            ModelTrainingError: If model is not trained
        """
        if not self.is_trained:
            raise ModelTrainingError("Model must be trained to get feature importance")
        
        importance = self.model.get_booster().get_score(importance_type=importance_type)
        
        # Convert to DataFrame and sort
        importance_df = pd.DataFrame([
            {'feature': feature, 'importance': score}
            for feature, score in importance.items()
        ]).sort_values('importance', ascending=False)
        
        return importance_df
    
    def save_model(self, file_path: Path) -> None:
        """
        Save the trained model to disk.
        
        Args:
            file_path: Path to save the model
            
        Raises:
            ModelTrainingError: If model is not trained or save fails
        """
        if not self.is_trained:
            raise ModelTrainingError("Model must be trained before saving")
        
        try:
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save model and metadata
            model_data = {
                'model': self.model,
                'feature_names': self.feature_names,
                'config': self.config,
                'scaler': self.scaler,
                'training_metrics': self.training_metrics,
                'validation_metrics': self.validation_metrics,
                'trained_at': datetime.now().isoformat()
            }
            
            joblib.dump(model_data, file_path)
            logger.info(f"Model saved to {file_path}")
            
        except Exception as e:
            raise ModelTrainingError(f"Failed to save model: {e}")
    
    @classmethod
    def load_model(cls, file_path: Path) -> 'EnhancedXGBoostModel':
        """
        Load a trained model from disk.
        
        Args:
            file_path: Path to the saved model
            
        Returns:
            Loaded EnhancedXGBoostModel instance
            
        Raises:
            ModelTrainingError: If loading fails
        """
        try:
            model_data = joblib.load(file_path)
            
            # Create instance
            instance = cls(model_data['config'])
            instance.model = model_data['model']
            instance.feature_names = model_data['feature_names']
            instance.scaler = model_data.get('scaler', None)  # Backward compatibility
            instance.training_metrics = model_data['training_metrics']
            instance.validation_metrics = model_data['validation_metrics']
            instance.is_trained = True
            
            logger.info(f"Model loaded from {file_path}")
            return instance
            
        except Exception as e:
            raise ModelTrainingError(f"Failed to load model: {e}")
