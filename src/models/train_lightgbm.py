"""
LightGBM model training script for power demand forecasting.

This script provides a command-line interface for training LightGBM models on
power demand data. It includes hyperparameter optimization, validation, and
model persistence with MLflow experiment tracking.

Usage:
    python -m src.models.train_lightgbm --features data/features/enhanced_features.parquet --horizon 1

Author: ML Power Nowcast Team
Created: 2024-08-30
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from .lightgbm_model import LightGBMModel, ModelTrainingError

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
    Load and prepare training data for LightGBM.
    
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
    
    # Remove non-numeric columns except those we want to treat as categorical
    categorical_columns = ['hour', 'day_of_week', 'month', 'quarter', 'is_weekend']
    numeric_columns = X.select_dtypes(include=[np.number]).columns
    categorical_in_data = [col for col in categorical_columns if col in X.columns]
    
    # Keep numeric columns and categorical columns
    columns_to_keep = list(numeric_columns) + categorical_in_data
    X_processed = X[columns_to_keep]
    
    logger.info(f"Using {len(numeric_columns)} numeric features and {len(categorical_in_data)} categorical features")
    logger.info(f"Categorical features: {categorical_in_data}")
    logger.info(f"Target statistics: mean={y.mean():.2f}, std={y.std():.2f}")
    
    # Split data
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_processed, y, test_size=test_size, random_state=random_state
    )
    
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_size, random_state=random_state
    )
    
    logger.info(f"Data splits - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def evaluate_model(
    model: LightGBMModel,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict[str, float]:
    """
    Evaluate the trained model on test data.
    
    Args:
        model: Trained LightGBM model
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
    logger.info(f"Test MAPE: {mape:.4f}%")
    logger.info(f"Test R²: {r2:.6f}")
    
    return metrics


def get_categorical_features(X: pd.DataFrame) -> List[str]:
    """
    Identify categorical features in the dataset.
    
    Args:
        X: Feature dataframe
        
    Returns:
        List of categorical feature names
    """
    categorical_candidates = ['hour', 'day_of_week', 'month', 'quarter', 'is_weekend']
    return [col for col in categorical_candidates if col in X.columns]


def train_lightgbm_model(
    features_path: Path,
    horizon: int,
    output_dir: Path,
    num_leaves: int = 31,
    learning_rate: float = 0.05,
    feature_fraction: float = 0.9,
    bagging_fraction: float = 0.8,
    bagging_freq: int = 5,
    n_estimators: int = 1000,
    early_stopping_rounds: int = 100,
    experiment_name: str = "lightgbm-power-forecasting"
) -> Optional[LightGBMModel]:
    """
    Train a LightGBM model with the specified parameters.
    
    Args:
        features_path: Path to training features
        horizon: Forecast horizon in hours
        output_dir: Directory to save the trained model
        num_leaves: Maximum number of leaves in one tree
        learning_rate: Learning rate
        feature_fraction: Fraction of features to use
        bagging_fraction: Fraction of data to use
        bagging_freq: Frequency of bagging
        n_estimators: Number of boosting iterations
        early_stopping_rounds: Early stopping rounds
        experiment_name: MLflow experiment name
        
    Returns:
        Trained LightGBM model or None if training fails
    """
    try:
        # Set up MLflow
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run():
            # Log parameters
            mlflow.log_params({
                "model_type": "lightgbm",
                "horizon": horizon,
                "num_leaves": num_leaves,
                "learning_rate": learning_rate,
                "feature_fraction": feature_fraction,
                "bagging_fraction": bagging_fraction,
                "bagging_freq": bagging_freq,
                "n_estimators": n_estimators,
                "early_stopping_rounds": early_stopping_rounds
            })
            
            # Prepare data
            target_column = f"load_target_{horizon}h"
            X_train, X_val, X_test, y_train, y_val, y_test = prepare_training_data(
                features_path, target_column
            )
            
            # Identify categorical features
            categorical_features = get_categorical_features(X_train)
            mlflow.log_param("categorical_features", categorical_features)
            
            # Initialize model
            model = LightGBMModel(
                num_leaves=num_leaves,
                learning_rate=learning_rate,
                feature_fraction=feature_fraction,
                bagging_fraction=bagging_fraction,
                bagging_freq=bagging_freq,
                n_estimators=n_estimators,
                early_stopping_rounds=early_stopping_rounds,
                verbose=-1  # Suppress LightGBM output
            )
            
            # Train model
            logger.info("Starting LightGBM training...")
            training_metrics = model.train(
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                categorical_features=categorical_features
            )
            
            # Log training metrics
            mlflow.log_metrics(training_metrics)
            
            # Evaluate on test set
            test_metrics = evaluate_model(model, X_test, y_test)
            mlflow.log_metrics(test_metrics)
            
            # Log feature importance
            feature_importance = model.get_feature_importance()
            if feature_importance:
                # Log top 10 most important features
                sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
                for i, (feature, importance) in enumerate(sorted_features[:10]):
                    mlflow.log_metric(f"feature_importance_{i+1}_{feature}", importance)
            
            # Save model
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"lightgbm_model_{timestamp}.joblib"
            model_path = output_dir / model_filename
            
            output_dir.mkdir(parents=True, exist_ok=True)
            model.save_model(model_path)
            
            # Log model to MLflow
            mlflow.lightgbm.log_model(
                lgb_model=model.model,
                artifact_path="lightgbm_model",
                registered_model_name="power-nowcast-lightgbm"
            )
            
            logger.info(f"LightGBM model saved to {model_path}")
            logger.info(f"Training completed successfully for {horizon}-hour horizon")
            
            return model
            
    except Exception as e:
        logger.error(f"LightGBM training failed: {e}")
        if 'mlflow' in locals():
            mlflow.log_param("error", str(e))
        raise ModelTrainingError(f"LightGBM training failed: {e}") from e


def main() -> int:
    """Main entry point for LightGBM training script."""
    parser = argparse.ArgumentParser(
        description="Train LightGBM model for power demand forecasting",
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
    parser.add_argument("--num-leaves", type=int, default=31, help="Maximum number of leaves")
    parser.add_argument("--learning-rate", type=float, default=0.05, help="Learning rate")
    parser.add_argument("--feature-fraction", type=float, default=0.9, help="Feature fraction")
    parser.add_argument("--bagging-fraction", type=float, default=0.8, help="Bagging fraction")
    parser.add_argument("--bagging-freq", type=int, default=5, help="Bagging frequency")
    parser.add_argument("--n-estimators", type=int, default=1000, help="Number of estimators")
    parser.add_argument("--early-stopping-rounds", type=int, default=100, help="Early stopping rounds")

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
        default="lightgbm-power-forecasting",
        help="MLflow experiment name"
    )

    args = parser.parse_args()

    try:
        model = train_lightgbm_model(
            features_path=args.features,
            horizon=args.horizon,
            output_dir=args.output_dir,
            num_leaves=args.num_leaves,
            learning_rate=args.learning_rate,
            feature_fraction=args.feature_fraction,
            bagging_fraction=args.bagging_fraction,
            bagging_freq=args.bagging_freq,
            n_estimators=args.n_estimators,
            early_stopping_rounds=args.early_stopping_rounds,
            experiment_name=args.experiment_name
        )

        if model is not None:
            logger.info("✅ LightGBM training completed successfully")
            return 0
        else:
            logger.error("❌ LightGBM training failed")
            return 1

    except Exception as e:
        logger.error(f"❌ Training script failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
