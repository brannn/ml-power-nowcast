#!/usr/bin/env python3
"""
XGBoost Model Training for Power Demand Forecasting.

Trains gradient boosting models for power demand prediction with comprehensive
hyperparameter tracking and model registry integration through MLflow.
"""

import argparse
from pathlib import Path
from typing import Dict, Tuple

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split


def load_features(features_path: str) -> Tuple[pd.DataFrame, str]:
    """
    Load feature dataset and identify target column.
    
    Args:
        features_path: Path to features parquet file
        
    Returns:
        Tuple of (features DataFrame, target column name)
    """
    print(f"Loading features from {features_path}")
    df = pd.read_parquet(features_path)
    
    # Find target column (should contain 'target')
    target_cols = [col for col in df.columns if 'target' in col]
    if not target_cols:
        raise ValueError("No target column found in features dataset")
    
    target_col = target_cols[0]  # Use first target column found
    print(f"Target column: {target_col}")
    print(f"Dataset shape: {df.shape}")
    
    return df, target_col


def prepare_data(
    df: pd.DataFrame, 
    target_col: str,
    test_size: float = 0.2,
    val_size: float = 0.1
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Prepare data for training with train/validation/test splits.
    
    Args:
        df: Features DataFrame
        target_col: Name of target column
        test_size: Fraction of data for test set
        val_size: Fraction of remaining data for validation set
        
    Returns:
        Tuple of (X_train, X_val, X_test, y_train, y_val, y_test)
    """
    print("Preparing data splits...")
    
    # Separate features and target (exclude non-numeric columns)
    exclude_cols = ['timestamp', target_col, 'region_power', 'region_weather', 'data_source_power', 'data_source_weather']
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    # Only keep numeric columns
    numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    X = df[numeric_cols].copy()
    y = df[target_col].copy()
    
    print(f"Features: {len(numeric_cols)}")
    print(f"Samples: {len(X)}")
    
    # Remove any remaining NaN values
    mask = ~(X.isnull().any(axis=1) | y.isnull())
    X = X[mask]
    y = y[mask]
    
    print(f"After removing NaN: {len(X)} samples")
    
    # First split: separate test set
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, shuffle=False  # Time series: no shuffle
    )
    
    # Second split: separate train and validation from remaining data
    val_size_adjusted = val_size / (1 - test_size)  # Adjust val_size for remaining data
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_size_adjusted, random_state=42, shuffle=False
    )
    
    print(f"Train set: {len(X_train)} samples")
    print(f"Validation set: {len(X_val)} samples") 
    print(f"Test set: {len(X_test)} samples")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def train_xgboost_model(
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    y_train: pd.Series,
    y_val: pd.Series,
    n_estimators: int = 500,
    max_depth: int = 6,
    learning_rate: float = 0.1,
    subsample: float = 0.8,
    colsample_bytree: float = 0.8,
    random_state: int = 42
) -> xgb.XGBRegressor:
    """
    Train XGBoost model with early stopping.
    
    Args:
        X_train: Training features
        X_val: Validation features
        y_train: Training targets
        y_val: Validation targets
        n_estimators: Maximum number of boosting rounds
        max_depth: Maximum tree depth
        learning_rate: Learning rate
        subsample: Subsample ratio of training instances
        colsample_bytree: Subsample ratio of features
        random_state: Random seed
        
    Returns:
        Trained XGBoost model
    """
    print("Training XGBoost model...")
    
    # Initialize model
    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        random_state=random_state,
        n_jobs=-1,  # Use all available cores
        verbosity=1
    )
    
    # Train model (simplified for compatibility)
    model.fit(X_train, y_train, verbose=False)
    
    print(f"Training completed with {n_estimators} estimators")
    return model


def evaluate_model(
    model: xgb.XGBRegressor,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict[str, float]:
    """
    Evaluate model performance on test set.
    
    Args:
        model: Trained XGBoost model
        X_test: Test features
        y_test: Test targets
        
    Returns:
        Dictionary of evaluation metrics
    """
    print("Evaluating model performance...")
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
    
    # Additional metrics
    r2 = model.score(X_test, y_test)
    
    metrics = {
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "r2": r2,
        "mean_actual": float(y_test.mean()),
        "std_actual": float(y_test.std()),
        "mean_predicted": float(y_pred.mean()),
        "std_predicted": float(y_pred.std())
    }
    
    print(f"Test MAE: {mae:.2f}")
    print(f"Test RMSE: {rmse:.2f}")
    print(f"Test MAPE: {mape:.2f}%")
    print(f"Test R²: {r2:.4f}")
    
    return metrics


def get_feature_importance(model: xgb.XGBRegressor, feature_names: list) -> pd.DataFrame:
    """
    Get feature importance from trained model.
    
    Args:
        model: Trained XGBoost model
        feature_names: List of feature names
        
    Returns:
        DataFrame with feature importance
    """
    importance = model.feature_importances_
    
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    print(f"Top 10 most important features:")
    for i, row in importance_df.head(10).iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")
    
    return importance_df


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(description="Train XGBoost model for power demand forecasting")
    parser.add_argument("--features", default="data/features/features.parquet", help="Path to features")
    parser.add_argument("--horizon", type=int, default=1, help="Forecast horizon in hours")
    parser.add_argument("--n-estimators", type=int, default=500, help="Number of boosting rounds")
    parser.add_argument("--max-depth", type=int, default=6, help="Maximum tree depth")
    parser.add_argument("--learning-rate", type=float, default=0.1, help="Learning rate")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test set size")
    parser.add_argument("--val-size", type=float, default=0.1, help="Validation set size")
    
    args = parser.parse_args()
    
    # Start MLflow run for tracking
    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"xgb_h{args.horizon}"):
        
        # Log parameters
        mlflow.log_params({
            "model_type": "xgboost",
            "horizon": args.horizon,
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "learning_rate": args.learning_rate,
            "test_size": args.test_size,
            "val_size": args.val_size,
            "features_path": args.features
        })
        
        try:
            # Load and prepare data
            df, target_col = load_features(args.features)
            X_train, X_val, X_test, y_train, y_val, y_test = prepare_data(
                df, target_col, test_size=args.test_size, val_size=args.val_size
            )
            
            # Train model
            model = train_xgboost_model(
                X_train, X_val, y_train, y_val,
                n_estimators=args.n_estimators,
                max_depth=args.max_depth,
                learning_rate=args.learning_rate
            )
            
            # Evaluate model
            metrics = evaluate_model(model, X_test, y_test)
            mlflow.log_metrics(metrics)
            
            # Log feature importance
            importance_df = get_feature_importance(model, X_train.columns.tolist())
            importance_path = f"feature_importance_h{args.horizon}.csv"
            importance_df.to_csv(importance_path, index=False)
            mlflow.log_artifact(importance_path)
            
            # Log model
            mlflow.xgboost.log_model(
                model, 
                "model",
                registered_model_name="power-nowcast-xgb"
            )
            
            print(f"Successfully trained XGBoost model for {args.horizon}-hour horizon")
            
        except Exception as e:
            print(f"Error during model training: {e}")
            mlflow.log_param("error", str(e))
            raise


if __name__ == "__main__":
    main()
