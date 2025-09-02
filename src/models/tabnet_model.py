"""
TabNet neural network model for power demand forecasting.

This module implements Google's TabNet architecture specifically designed for
tabular data. TabNet uses sequential attention to learn which features to use
at each decision step, providing both high performance and interpretability.

Key Features:
- Attention-based feature selection
- Interpretable decision process
- Handles mixed categorical/numerical features
- Optimized for Apple Silicon MPS acceleration

Author: ML Power Nowcast Team
Created: 2024-08-30
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import torch
from pytorch_tabnet.tab_model import TabNetRegressor
from sklearn.model_selection import train_test_split

from .base_neural_model import (
    BaseNeuralModel,
    ModelLoadError,
    ModelPredictionError,
    ModelTrainingError
)

# Configure logging
logger = logging.getLogger(__name__)


class TabNetModel(BaseNeuralModel):
    """
    TabNet neural network model for tabular power demand forecasting.
    
    This class implements Google's TabNet architecture with optimizations for
    power demand forecasting. It provides interpretable attention mechanisms
    and handles the mixed feature types common in power grid data.
    
    Attributes:
        model: The underlying TabNet regressor
        device: PyTorch device (MPS for Apple Silicon, CPU fallback)
        attention_weights: Feature attention weights from last prediction
    """
    
    def __init__(
        self,
        n_d: int = 64,
        n_a: int = 64,
        n_steps: int = 5,
        gamma: float = 1.5,
        lambda_sparse: float = 1e-4,
        learning_rate: float = 0.02,
        **kwargs: Any
    ) -> None:
        """
        Initialize TabNet model with specified hyperparameters.
        
        Args:
            n_d: Width of the decision prediction layer
            n_a: Width of the attention embedding for each mask
            n_steps: Number of steps in the architecture
            gamma: Coefficient for feature reusage in the masks
            lambda_sparse: Sparsity regularization parameter
            learning_rate: Learning rate for optimization
            **kwargs: Additional TabNet parameters
        """
        super().__init__(model_type="tabnet", model_version="1.0.0")
        
        # Store hyperparameters
        self.hyperparameters = {
            "n_d": n_d,
            "n_a": n_a,
            "n_steps": n_steps,
            "gamma": gamma,
            "lambda_sparse": lambda_sparse,
            "learning_rate": learning_rate,
            **kwargs
        }
        
        # Initialize device (prefer MPS on Apple Silicon)
        self.device = self._get_optimal_device()
        logger.info(f"TabNet using device: {self.device}")
        
        # Model-specific attributes
        self.model: Optional[TabNetRegressor] = None
        self.attention_weights: Optional[np.ndarray] = None
        
    def _get_optimal_device(self) -> str:
        """
        Determine the optimal device for training/inference.
        
        Returns:
            Device string ('mps', 'cuda', or 'cpu')
        """
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        max_epochs: int = 100,
        patience: int = 10,
        batch_size: int = 256,
        virtual_batch_size: int = 128,
        **kwargs: Any
    ) -> Dict[str, float]:
        """
        Train the TabNet model on the provided data.
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features (optional)
            y_val: Validation targets (optional)
            max_epochs: Maximum number of training epochs
            patience: Early stopping patience
            batch_size: Training batch size
            virtual_batch_size: Virtual batch size for gradient accumulation
            **kwargs: Additional training parameters
            
        Returns:
            Dictionary containing training metrics
            
        Raises:
            ModelTrainingError: If training fails
        """
        try:
            logger.info("Starting TabNet training...")
            
            # Validate inputs
            if X_train.empty or y_train.empty:
                raise ModelTrainingError("Training data cannot be empty")
            
            # Preprocess features
            X_train_clean = self._validate_features(X_train)
            self.feature_columns = list(X_train_clean.columns)
            self.input_size = len(self.feature_columns)
            
            # Fit scalers and scale data
            X_scaled, y_scaled = self._fit_scalers(X_train_clean, y_train, scale_target=False)

            # Convert to float32 for MPS compatibility
            X_scaled = X_scaled.astype(np.float32)
            y_scaled = y_scaled.astype(np.float32)

            # TabNet requires 2D targets - reshape if necessary
            if y_scaled.ndim == 1:
                y_scaled = y_scaled.reshape(-1, 1)
            
            # Prepare validation data if provided
            eval_set = None
            if X_val is not None and y_val is not None:
                X_val_clean = self._validate_features(X_val)
                X_val_scaled = self.feature_scaler.transform(X_val_clean).astype(np.float32)
                y_val_reshaped = y_val.values.astype(np.float32)
                if y_val_reshaped.ndim == 1:
                    y_val_reshaped = y_val_reshaped.reshape(-1, 1)
                eval_set = [(X_val_scaled, y_val_reshaped)]
            
            # Initialize TabNet model
            self.model = TabNetRegressor(
                device_name=self.device,
                n_d=self.hyperparameters["n_d"],
                n_a=self.hyperparameters["n_a"],
                n_steps=self.hyperparameters["n_steps"],
                gamma=self.hyperparameters["gamma"],
                lambda_sparse=self.hyperparameters["lambda_sparse"],
                optimizer_fn=torch.optim.Adam,
                optimizer_params={"lr": self.hyperparameters["learning_rate"]},
                mask_type="entmax",
                scheduler_params={
                    "mode": "min",
                    "patience": patience // 2,
                    "min_lr": 1e-5,
                    "factor": 0.9
                },
                scheduler_fn=torch.optim.lr_scheduler.ReduceLROnPlateau,
                verbose=1
            )
            
            # Train the model
            self.model.fit(
                X_train=X_scaled,
                y_train=y_scaled,
                eval_set=eval_set,
                max_epochs=max_epochs,
                patience=patience,
                batch_size=batch_size,
                virtual_batch_size=virtual_batch_size,
                num_workers=0,  # Avoid multiprocessing issues on macOS
                drop_last=False,
                **kwargs
            )
            
            # Calculate training metrics
            train_predictions = self.model.predict(X_scaled)
            # Flatten predictions and targets for metric calculation
            y_scaled_flat = y_scaled.flatten() if y_scaled.ndim > 1 else y_scaled
            train_predictions_flat = train_predictions.flatten() if train_predictions.ndim > 1 else train_predictions

            train_mae = np.mean(np.abs(train_predictions_flat - y_scaled_flat))
            train_rmse = np.sqrt(np.mean((train_predictions_flat - y_scaled_flat) ** 2))
            train_mape = np.mean(np.abs((y_scaled_flat - train_predictions_flat) / y_scaled_flat)) * 100
            
            # Calculate validation metrics if available
            val_mae = val_rmse = val_mape = None
            if eval_set is not None:
                val_predictions = self.model.predict(X_val_scaled)
                val_predictions_flat = val_predictions.flatten() if val_predictions.ndim > 1 else val_predictions
                y_val_flat = y_val.values

                val_mae = np.mean(np.abs(val_predictions_flat - y_val_flat))
                val_rmse = np.sqrt(np.mean((val_predictions_flat - y_val_flat) ** 2))
                val_mape = np.mean(np.abs((y_val_flat - val_predictions_flat) / y_val_flat)) * 100
            
            # Store training metadata
            self.model_metadata = {
                "training_samples": len(X_train),
                "validation_samples": len(X_val) if X_val is not None else 0,
                "feature_count": self.input_size,
                "hyperparameters": self.hyperparameters.copy(),
                "device": self.device
            }
            
            self.is_loaded = True
            logger.info("TabNet training completed successfully")
            
            # Return metrics
            metrics = {
                "train_mae": train_mae,
                "train_rmse": train_rmse,
                "train_mape": train_mape
            }
            
            if val_mae is not None:
                metrics.update({
                    "val_mae": val_mae,
                    "val_rmse": val_rmse,
                    "val_mape": val_mape
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"TabNet training failed: {e}")
            raise ModelTrainingError(f"TabNet training failed: {e}") from e
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """
        Make predictions using the trained TabNet model.
        
        Args:
            features: Input features for prediction
            
        Returns:
            Array of predictions
            
        Raises:
            ModelPredictionError: If prediction fails
            ModelLoadError: If model is not loaded
        """
        if not self.is_loaded or self.model is None:
            raise ModelLoadError("Model not loaded. Train or load a model first.")
        
        try:
            # Validate and preprocess features
            features_clean = self._validate_features(features)
            features_scaled = self._scale_features(features_clean).astype(np.float32)
            
            # Make predictions
            predictions = self.model.predict(features_scaled)

            # Flatten predictions if they're 2D
            if predictions.ndim > 1:
                predictions = predictions.flatten()

            # Store attention weights for interpretability
            if hasattr(self.model, 'explain'):
                self.attention_weights = self.model.explain(features_scaled)[1]

            return predictions
            
        except Exception as e:
            logger.error(f"TabNet prediction failed: {e}")
            raise ModelPredictionError(f"TabNet prediction failed: {e}") from e

    def save_model(self, model_path: Union[str, Path]) -> None:
        """
        Save the trained TabNet model to disk.

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

            # Save TabNet model
            tabnet_path = model_path.with_suffix('.zip')
            self.model.save_model(str(tabnet_path))

            # Save additional metadata and scalers
            metadata = {
                "model_type": self.model_type,
                "model_version": self.model_version,
                "feature_columns": self.feature_columns,
                "input_size": self.input_size,
                "hyperparameters": self.hyperparameters,
                "model_metadata": self.model_metadata,
                "feature_scaler": self.feature_scaler,
                "target_scaler": self.target_scaler,
                "device": self.device
            }

            metadata_path = model_path.with_suffix('.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)

            logger.info(f"TabNet model saved to {model_path}")

        except Exception as e:
            logger.error(f"Failed to save TabNet model: {e}")
            raise ModelLoadError(f"Failed to save TabNet model: {e}") from e

    @classmethod
    def load_model(cls, model_path: Union[str, Path]) -> TabNetModel:
        """
        Load a trained TabNet model from disk.

        Args:
            model_path: Path to the saved model

        Returns:
            Loaded TabNet model instance

        Raises:
            ModelLoadError: If model loading fails
        """
        try:
            model_path = Path(model_path)

            # Load metadata
            metadata_path = model_path.with_suffix('.pkl')
            if not metadata_path.exists():
                raise ModelLoadError(f"Metadata file not found: {metadata_path}")

            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)

            # Create model instance with saved hyperparameters
            instance = cls(**metadata["hyperparameters"])

            # Restore attributes
            instance.feature_columns = metadata["feature_columns"]
            instance.input_size = metadata["input_size"]
            instance.model_metadata = metadata["model_metadata"]
            instance.feature_scaler = metadata["feature_scaler"]
            instance.target_scaler = metadata["target_scaler"]
            instance.device = metadata.get("device", instance._get_optimal_device())

            # Load TabNet model
            tabnet_path = model_path.with_suffix('.zip')
            if not tabnet_path.exists():
                raise ModelLoadError(f"TabNet model file not found: {tabnet_path}")

            instance.model = TabNetRegressor(device_name=instance.device)
            instance.model.load_model(str(tabnet_path))
            instance.is_loaded = True

            logger.info(f"TabNet model loaded from {model_path}")
            return instance

        except Exception as e:
            logger.error(f"Failed to load TabNet model: {e}")
            raise ModelLoadError(f"Failed to load TabNet model: {e}") from e

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance scores from the trained model.

        Returns:
            Dictionary mapping feature names to importance scores, or None if not available
        """
        if not self.is_loaded or self.model is None:
            return None

        try:
            # Get global feature importance
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                return dict(zip(self.feature_columns, importances))
            return None
        except Exception as e:
            logger.warning(f"Could not retrieve feature importance: {e}")
            return None

    def get_attention_weights(self) -> Optional[np.ndarray]:
        """
        Get the attention weights from the last prediction.

        Returns:
            Attention weights array, or None if not available
        """
        return self.attention_weights
