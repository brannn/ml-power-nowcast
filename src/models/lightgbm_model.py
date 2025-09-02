"""
LightGBM model for power demand forecasting.

This module implements Microsoft's LightGBM gradient boosting framework,
optimized for speed and memory efficiency. LightGBM is designed to be
faster than XGBoost while maintaining competitive accuracy on tabular data.

Key Features:
- Faster training than XGBoost
- Lower memory usage
- Native categorical feature support
- Excellent performance on large datasets
- Built-in early stopping and cross-validation

Author: ML Power Nowcast Team
Created: 2024-08-30
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# Configure logging
logger = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """Raised when a model fails to load."""
    pass


class ModelPredictionError(Exception):
    """Raised when a model fails to make predictions."""
    pass


class ModelTrainingError(Exception):
    """Raised when a model fails to train."""
    pass


class LightGBMModel:
    """
    LightGBM model wrapper for power demand forecasting.
    
    This class provides a consistent interface for LightGBM models that matches
    our existing XGBoost model interface, enabling easy integration into the
    existing prediction pipeline.
    
    Attributes:
        model: The underlying LightGBM regressor
        model_type: String identifier for the model type
        model_version: Version string for the model
        is_loaded: Boolean indicating if the model is loaded and ready
        feature_columns: List of feature column names
        model_metadata: Dictionary containing model configuration and metrics
    """
    
    def __init__(
        self,
        objective: str = 'regression',
        metric: str = 'mae',
        boosting_type: str = 'gbdt',
        num_leaves: int = 31,
        learning_rate: float = 0.05,
        feature_fraction: float = 0.9,
        bagging_fraction: float = 0.8,
        bagging_freq: int = 5,
        n_estimators: int = 1000,
        early_stopping_rounds: int = 100,
        random_state: int = 42,
        **kwargs: Any
    ) -> None:
        """
        Initialize LightGBM model with specified hyperparameters.
        
        Args:
            objective: Learning objective
            metric: Evaluation metric
            boosting_type: Boosting algorithm type
            num_leaves: Maximum number of leaves in one tree
            learning_rate: Learning rate for boosting
            feature_fraction: Fraction of features to use in each iteration
            bagging_fraction: Fraction of data to use in each iteration
            bagging_freq: Frequency of bagging
            n_estimators: Number of boosting iterations
            early_stopping_rounds: Early stopping rounds
            random_state: Random seed for reproducibility
            **kwargs: Additional LightGBM parameters
        """
        self.model_type = "lightgbm"
        self.model_version = "1.0.0"
        self.is_loaded = False
        
        # Store hyperparameters
        self.hyperparameters = {
            "objective": objective,
            "metric": metric,
            "boosting_type": boosting_type,
            "num_leaves": num_leaves,
            "learning_rate": learning_rate,
            "feature_fraction": feature_fraction,
            "bagging_fraction": bagging_fraction,
            "bagging_freq": bagging_freq,
            "n_estimators": n_estimators,
            "early_stopping_rounds": early_stopping_rounds,
            "random_state": random_state,
            **kwargs
        }
        
        # Model attributes
        self.model: Optional[LGBMRegressor] = None
        self.feature_columns: List[str] = []
        self.model_metadata: Dict[str, Any] = {}
        
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        categorical_features: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Dict[str, float]:
        """
        Train the LightGBM model on the provided data.
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features (optional)
            y_val: Validation targets (optional)
            categorical_features: List of categorical feature names
            **kwargs: Additional training parameters
            
        Returns:
            Dictionary containing training metrics
            
        Raises:
            ModelTrainingError: If training fails
        """
        try:
            logger.info("Starting LightGBM training...")
            
            # Validate inputs
            if X_train.empty or y_train.empty:
                raise ModelTrainingError("Training data cannot be empty")
            
            # Store feature information
            self.feature_columns = list(X_train.columns)
            
            # Initialize LightGBM model
            self.model = LGBMRegressor(**self.hyperparameters)
            
            # Prepare evaluation set for early stopping
            eval_set = None
            if X_val is not None and y_val is not None:
                eval_set = [(X_val, y_val)]
            
            # Train the model
            self.model.fit(
                X_train,
                y_train,
                eval_set=eval_set,
                categorical_feature=categorical_features,
                callbacks=[],  # Disable verbose output
                **kwargs
            )
            
            # Calculate training metrics
            train_predictions = self.model.predict(X_train)
            train_mae = mean_absolute_error(y_train, train_predictions)
            train_rmse = np.sqrt(mean_squared_error(y_train, train_predictions))
            train_r2 = r2_score(y_train, train_predictions)
            train_mape = np.mean(np.abs((y_train - train_predictions) / y_train)) * 100
            
            # Calculate validation metrics if available
            val_mae = val_rmse = val_r2 = val_mape = None
            if eval_set is not None:
                val_predictions = self.model.predict(X_val)
                val_mae = mean_absolute_error(y_val, val_predictions)
                val_rmse = np.sqrt(mean_squared_error(y_val, val_predictions))
                val_r2 = r2_score(y_val, val_predictions)
                val_mape = np.mean(np.abs((y_val - val_predictions) / y_val)) * 100
            
            # Store training metadata
            self.model_metadata = {
                "training_samples": len(X_train),
                "validation_samples": len(X_val) if X_val is not None else 0,
                "feature_count": len(self.feature_columns),
                "hyperparameters": self.hyperparameters.copy(),
                "categorical_features": categorical_features or [],
                "best_iteration": getattr(self.model, 'best_iteration', self.hyperparameters["n_estimators"])
            }
            
            self.is_loaded = True
            logger.info("LightGBM training completed successfully")
            
            # Return metrics
            metrics = {
                "train_mae": train_mae,
                "train_rmse": train_rmse,
                "train_r2": train_r2,
                "train_mape": train_mape
            }
            
            if val_mae is not None:
                metrics.update({
                    "val_mae": val_mae,
                    "val_rmse": val_rmse,
                    "val_r2": val_r2,
                    "val_mape": val_mape
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"LightGBM training failed: {e}")
            raise ModelTrainingError(f"LightGBM training failed: {e}") from e
    
    def predict(self, features) -> np.ndarray:
        """
        Make predictions using the trained LightGBM model.

        Args:
            features: Input features for prediction (DataFrame or numpy array)

        Returns:
            Array of predictions

        Raises:
            ModelPredictionError: If prediction fails
            ModelLoadError: If model is not loaded
        """
        if not self.is_loaded or self.model is None:
            raise ModelLoadError("Model not loaded. Train or load a model first.")

        try:
            # Handle both DataFrame and numpy array inputs
            if hasattr(features, 'columns'):
                # DataFrame input - apply feature processing
                if features.empty:
                    raise ModelPredictionError("Input features cannot be empty")

                # Check for required columns
                missing_cols = set(self.feature_columns) - set(features.columns)
                if missing_cols:
                    raise ModelPredictionError(f"Missing required feature columns: {missing_cols}")

                # Select and order features to match training
                features_ordered = features[self.feature_columns]
                features_array = features_ordered.values
            else:
                # Numpy array input - use directly
                features_array = features
            
            # Make predictions using the correct features variable
            if hasattr(features, 'columns'):
                predictions = self.model.predict(features_ordered)
            else:
                predictions = self.model.predict(features_array)

            return predictions
            
        except Exception as e:
            logger.error(f"LightGBM prediction failed: {e}")
            raise ModelPredictionError(f"LightGBM prediction failed: {e}") from e

    def save_model(self, model_path: Union[str, Path]) -> None:
        """
        Save the trained LightGBM model to disk.

        Args:
            model_path: Path where the model should be saved

        Raises:
            ModelLoadError: If model is not trained or save fails
        """
        if not self.is_loaded or self.model is None:
            raise ModelLoadError("No trained model to save")

        try:
            model_path = Path(model_path)
            model_path.parent.mkdir(parents=True, exist_ok=True)

            # Save LightGBM model using joblib for consistency with XGBoost
            model_data = {
                "model": self.model,
                "model_type": self.model_type,
                "model_version": self.model_version,
                "feature_columns": self.feature_columns,
                "hyperparameters": self.hyperparameters,
                "model_metadata": self.model_metadata
            }

            joblib.dump(model_data, model_path)
            logger.info(f"LightGBM model saved to {model_path}")

        except Exception as e:
            logger.error(f"Failed to save LightGBM model: {e}")
            raise ModelLoadError(f"Failed to save LightGBM model: {e}") from e

    @classmethod
    def load_model(cls, model_path: Union[str, Path]) -> LightGBMModel:
        """
        Load a trained LightGBM model from disk.

        Args:
            model_path: Path to the saved model

        Returns:
            Loaded LightGBM model instance

        Raises:
            ModelLoadError: If model loading fails
        """
        try:
            model_path = Path(model_path)

            if not model_path.exists():
                raise ModelLoadError(f"Model file not found: {model_path}")

            # Load model data
            model_data = joblib.load(model_path)

            # Create model instance with saved hyperparameters
            instance = cls(**model_data["hyperparameters"])

            # Restore attributes
            instance.model = model_data["model"]
            instance.feature_columns = model_data["feature_columns"]
            instance.model_metadata = model_data["model_metadata"]
            instance.is_loaded = True

            logger.info(f"LightGBM model loaded from {model_path}")
            return instance

        except Exception as e:
            logger.error(f"Failed to load LightGBM model: {e}")
            raise ModelLoadError(f"Failed to load LightGBM model: {e}") from e

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance scores from the trained model.

        Returns:
            Dictionary mapping feature names to importance scores, or None if not available
        """
        if not self.is_loaded or self.model is None:
            return None

        try:
            importances = self.model.feature_importances_
            return dict(zip(self.feature_columns, importances))
        except Exception as e:
            logger.warning(f"Could not retrieve feature importance: {e}")
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get comprehensive model information.

        Returns:
            Dictionary containing model metadata and configuration
        """
        return {
            "model_type": self.model_type,
            "model_version": self.model_version,
            "is_loaded": self.is_loaded,
            "feature_columns": self.feature_columns,
            "feature_count": len(self.feature_columns),
            "hyperparameters": self.hyperparameters.copy(),
            "metadata": self.model_metadata.copy()
        }

    def __repr__(self) -> str:
        """String representation of the model."""
        status = "loaded" if self.is_loaded else "not loaded"
        return f"LightGBMModel(version={self.model_version}, status={status}, features={len(self.feature_columns)})"
