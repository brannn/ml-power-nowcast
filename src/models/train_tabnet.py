"""
TabNet model training script for power demand forecasting.

This script provides a command-line interface for training TabNet models on
power demand data. It includes comprehensive hyperparameter tuning, validation,
and model persistence with MLflow experiment tracking.

Usage:
    python -m src.models.train_tabnet --features data/features/tabnet_features.parquet --horizon 1

Author: ML Power Nowcast Team
Created: 2024-08-30
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import mlflow
import mlflow.pytorch
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from .tabnet_model import TabNetModel
from .base_neural_model import ModelTrainingError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def prepare_training_data(
    features_path: Path,
    target_column: str,
    test_size: float = 0.2,
    val_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Load and prepare training data for TabNet.
    
    Args:
        features_path: Path to the features parquet file
        target_column: Name of the target column
        test_size: Proportion of data for testing
        val_size: Proportion of training data for validation
        random_state: Random seed for reproducibility
        
    Returns:
        Tuple of (X_train, X_val, X_test, y_train, y_val, y_test)
        
    Raises:
        FileNotFoundError: If features file doesn't exist
        ValueError: If target column is missing
    """
    logger.info(f"Loading features from {features_path}")
    
    if not features_path.exists():
        raise FileNotFoundError(f"Features file not found: {features_path}")
    
    # Load data
    df = pd.read_parquet(features_path)
    logger.info(f"Loaded dataset with shape: {df.shape}")
    
    # Validate target column
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset")
    
    # Separate features and target
    X = df.drop(columns=[target_column])
    y = df[target_column]
    
    # Remove non-numeric columns for TabNet
    numeric_columns = X.select_dtypes(include=[np.number]).columns
    X_numeric = X[numeric_columns]
    
    logger.info(f"Using {len(numeric_columns)} numeric features")
    logger.info(f"Target statistics: mean={y.mean():.2f}, std={y.std():.2f}")
    
    # Split data
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_numeric, y, test_size=test_size, random_state=random_state
    )
    
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_size, random_state=random_state
    )
    
    logger.info(f"Data splits - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def evaluate_model(
    model: TabNetModel,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict[str, float]:
    """
    Evaluate the trained model on test data.
    
    Args:
        model: Trained TabNet model
        X_test: Test features
        y_test: Test targets
        
    Returns:
        Dictionary containing evaluation metrics
    """
    logger.info("Evaluating model on test data...")
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
    
    metrics = {
        "test_mae": mae,
        "test_rmse": rmse,
        "test_r2": r2,
        "test_mape": mape
    }
    
    logger.info(f"Test MAE: {mae:.2f}")
    logger.info(f"Test RMSE: {rmse:.2f}")
    logger.info(f"Test MAPE: {mape:.2f}%")
    logger.info(f"Test R²: {r2:.4f}")
    
    return metrics


def train_tabnet_model(
    features_path: Path,
    horizon: int,
    output_dir: Path,
    n_d: int = 64,
    n_a: int = 64,
    n_steps: int = 5,
    gamma: float = 1.5,
    lambda_sparse: float = 1e-4,
    learning_rate: float = 0.02,
    max_epochs: int = 100,
    patience: int = 15,
    batch_size: int = 256,
    experiment_name: str = "tabnet-power-forecasting"
) -> Optional[TabNetModel]:
    """
    Train a TabNet model with the specified parameters.
    
    Args:
        features_path: Path to training features
        horizon: Forecast horizon in hours
        output_dir: Directory to save the trained model
        n_d: Width of decision prediction layer
        n_a: Width of attention embedding
        n_steps: Number of steps in architecture
        gamma: Feature reusage coefficient
        lambda_sparse: Sparsity regularization
        learning_rate: Learning rate
        max_epochs: Maximum training epochs
        patience: Early stopping patience
        batch_size: Training batch size
        experiment_name: MLflow experiment name
        
    Returns:
        Trained TabNet model or None if training fails
    """
    try:
        # Set up MLflow
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run():
            # Log parameters
            mlflow.log_params({
                "model_type": "tabnet",
                "horizon": horizon,
                "n_d": n_d,
                "n_a": n_a,
                "n_steps": n_steps,
                "gamma": gamma,
                "lambda_sparse": lambda_sparse,
                "learning_rate": learning_rate,
                "max_epochs": max_epochs,
                "patience": patience,
                "batch_size": batch_size
            })
            
            # Prepare data
            target_column = f"load_target_{horizon}h"
            X_train, X_val, X_test, y_train, y_val, y_test = prepare_training_data(
                features_path, target_column
            )
            
            # Initialize model
            model = TabNetModel(
                n_d=n_d,
                n_a=n_a,
                n_steps=n_steps,
                gamma=gamma,
                lambda_sparse=lambda_sparse,
                learning_rate=learning_rate
            )
            
            # Train model
            logger.info("Starting TabNet training...")
            training_metrics = model.train(
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                max_epochs=max_epochs,
                patience=patience,
                batch_size=batch_size
            )
            
            # Log training metrics
            mlflow.log_metrics(training_metrics)
            
            # Evaluate on test set
            test_metrics = evaluate_model(model, X_test, y_test)
            mlflow.log_metrics(test_metrics)
            
            # Save model
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"tabnet_model_{timestamp}"
            model_path = output_dir / model_filename
            
            output_dir.mkdir(parents=True, exist_ok=True)
            model.save_model(model_path)
            
            # Log model to MLflow
            mlflow.pytorch.log_model(
                pytorch_model=model.model,
                artifact_path="tabnet_model",
                registered_model_name="power-nowcast-tabnet"
            )
            
            logger.info(f"TabNet model saved to {model_path}")
            logger.info(f"Training completed successfully for {horizon}-hour horizon")
            
            return model
            
    except Exception as e:
        logger.error(f"TabNet training failed: {e}")
        mlflow.log_param("error", str(e))
        raise ModelTrainingError(f"TabNet training failed: {e}") from e


def main() -> int:
    """Main entry point for TabNet training script."""
    parser = argparse.ArgumentParser(
        description="Train TabNet model for power demand forecasting",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "--features",
        type=Path,
        required=True,
        help="Path to features parquet file"
    )
    parser.add_argument(
        "--horizon",
        type=int,
        required=True,
        help="Forecast horizon in hours"
    )
    
    # Model hyperparameters
    parser.add_argument("--n-d", type=int, default=64, help="Decision layer width")
    parser.add_argument("--n-a", type=int, default=64, help="Attention embedding width")
    parser.add_argument("--n-steps", type=int, default=5, help="Number of steps")
    parser.add_argument("--gamma", type=float, default=1.5, help="Feature reusage coefficient")
    parser.add_argument("--lambda-sparse", type=float, default=1e-4, help="Sparsity regularization")
    parser.add_argument("--learning-rate", type=float, default=0.02, help="Learning rate")
    
    # Training parameters
    parser.add_argument("--max-epochs", type=int, default=100, help="Maximum epochs")
    parser.add_argument("--patience", type=int, default=15, help="Early stopping patience")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size")
    
    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/trained_models"),
        help="Output directory for trained models"
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default="tabnet-power-forecasting",
        help="MLflow experiment name"
    )
    
    args = parser.parse_args()
    
    try:
        model = train_tabnet_model(
            features_path=args.features,
            horizon=args.horizon,
            output_dir=args.output_dir,
            n_d=args.n_d,
            n_a=args.n_a,
            n_steps=args.n_steps,
            gamma=args.gamma,
            lambda_sparse=args.lambda_sparse,
            learning_rate=args.learning_rate,
            max_epochs=args.max_epochs,
            patience=args.patience,
            batch_size=args.batch_size,
            experiment_name=args.experiment_name
        )
        
        if model is not None:
            logger.info("✅ TabNet training completed successfully")
            return 0
        else:
            logger.error("❌ TabNet training failed")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Training script failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
