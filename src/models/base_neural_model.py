"""
Base neural network model interface for power demand forecasting.

This module provides the abstract base class and common functionality for all
neural network models in the power demand forecasting system. It ensures
consistent interfaces, proper type hinting, and standardized error handling.

Author: ML Power Nowcast Team
Created: 2024-08-30
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

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


class BaseNeuralModel(ABC):
    """
    Abstract base class for neural network models.
    
    This class defines the interface that all neural network models must
    implement, ensuring consistency across different architectures while
    maintaining flexibility for model-specific implementations.
    
    Attributes:
        model_type: String identifier for the model type
        model_version: Version string for the model
        is_loaded: Boolean indicating if the model is loaded and ready
        feature_scaler: Scaler for input features
        target_scaler: Optional scaler for target values
        model_metadata: Dictionary containing model configuration and metrics
    """
    
    def __init__(
        self,
        model_type: str,
        model_version: str = "1.0.0"
    ) -> None:
        """
        Initialize the base neural model.
        
        Args:
            model_type: String identifier for the model type (e.g., 'tabnet', 'wide_deep')
            model_version: Version string for the model
        """
        self.model_type = model_type
        self.model_version = model_version
        self.is_loaded = False
        self.feature_scaler: Optional[StandardScaler] = None
        self.target_scaler: Optional[StandardScaler] = None
        self.model_metadata: Dict[str, Any] = {}
        
        # Model-specific attributes to be set by subclasses
        self.model: Optional[Any] = None
        self.feature_columns: List[str] = []
        self.input_size: Optional[int] = None
        
    @abstractmethod
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs: Any
    ) -> Dict[str, float]:
        """
        Train the neural network model.
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features (optional)
            y_val: Validation targets (optional)
            **kwargs: Additional training parameters
            
        Returns:
            Dictionary containing training metrics
            
        Raises:
            ModelTrainingError: If training fails
        """
        pass
    
    @abstractmethod
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """
        Make predictions using the trained model.
        
        Args:
            features: Input features for prediction
            
        Returns:
            Array of predictions
            
        Raises:
            ModelPredictionError: If prediction fails
            ModelLoadError: If model is not loaded
        """
        pass
    
    @abstractmethod
    def save_model(self, model_path: Union[str, Path]) -> None:
        """
        Save the trained model to disk.
        
        Args:
            model_path: Path where the model should be saved
            
        Raises:
            ModelLoadError: If model is not trained or save fails
        """
        pass
    
    @classmethod
    @abstractmethod
    def load_model(cls, model_path: Union[str, Path]) -> BaseNeuralModel:
        """
        Load a trained model from disk.
        
        Args:
            model_path: Path to the saved model
            
        Returns:
            Loaded model instance
            
        Raises:
            ModelLoadError: If model loading fails
        """
        pass
    
    def _validate_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and preprocess input features.
        
        Args:
            features: Input features to validate
            
        Returns:
            Validated and preprocessed features
            
        Raises:
            ModelPredictionError: If features are invalid
        """
        if features.empty:
            raise ModelPredictionError("Input features cannot be empty")
        
        # Check for required columns if model is trained
        if self.feature_columns and not all(col in features.columns for col in self.feature_columns):
            missing_cols = set(self.feature_columns) - set(features.columns)
            raise ModelPredictionError(f"Missing required feature columns: {missing_cols}")
        
        # Select only numeric features
        numeric_features = features.select_dtypes(include=[np.number])
        if numeric_features.empty:
            raise ModelPredictionError("No numeric features found in input data")
        
        return numeric_features
    
    def _scale_features(self, features: pd.DataFrame) -> np.ndarray:
        """
        Scale input features using the fitted scaler.
        
        Args:
            features: Features to scale
            
        Returns:
            Scaled feature array
            
        Raises:
            ModelPredictionError: If scaler is not fitted
        """
        if self.feature_scaler is None:
            raise ModelPredictionError("Feature scaler not fitted. Train model first.")
        
        try:
            return self.feature_scaler.transform(features)
        except Exception as e:
            raise ModelPredictionError(f"Feature scaling failed: {e}") from e
    
    def _fit_scalers(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        scale_target: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fit feature and target scalers on training data.
        
        Args:
            X_train: Training features
            y_train: Training targets
            scale_target: Whether to scale target values
            
        Returns:
            Tuple of (scaled_features, scaled_targets)
        """
        # Fit feature scaler
        self.feature_scaler = StandardScaler()
        X_scaled = self.feature_scaler.fit_transform(X_train)
        
        # Optionally fit target scaler
        y_scaled = y_train.values
        if scale_target:
            self.target_scaler = StandardScaler()
            y_scaled = self.target_scaler.fit_transform(y_train.values.reshape(-1, 1)).flatten()
        
        return X_scaled, y_scaled
    
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
            "input_size": self.input_size,
            "has_feature_scaler": self.feature_scaler is not None,
            "has_target_scaler": self.target_scaler is not None,
            "metadata": self.model_metadata.copy()
        }
    
    def __repr__(self) -> str:
        """String representation of the model."""
        status = "loaded" if self.is_loaded else "not loaded"
        return f"{self.__class__.__name__}(type={self.model_type}, version={self.model_version}, status={status})"
