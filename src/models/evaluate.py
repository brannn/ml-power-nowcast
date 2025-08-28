#!/usr/bin/env python3
"""
Model Evaluation for Power Demand Forecasting.

Comprehensive evaluation of trained models with visualization and performance
analysis across different forecast horizons and time periods.
"""

import argparse
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error


def load_model_predictions(model_name: str, version: str = "latest") -> Dict:
    """
    Load model and make predictions.
    
    Args:
        model_name: Name of registered model
        version: Model version to load
        
    Returns:
        Dictionary with model info and predictions
    """
    print(f"Loading model {model_name} version {version}")
    
    # Load model from MLflow registry
    model_uri = f"models:/{model_name}/{version}"
    
    try:
        if "xgb" in model_name.lower():
            import mlflow.xgboost
            model = mlflow.xgboost.load_model(model_uri)
        elif "lstm" in model_name.lower():
            import mlflow.pytorch
            model = mlflow.pytorch.load_model(model_uri)
        else:
            model = mlflow.pyfunc.load_model(model_uri)
        
        return {"model": model, "name": model_name, "version": version}
        
    except Exception as e:
        print(f"Error loading model {model_name}: {e}")
        return None


def evaluate_model_performance(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str
) -> Dict[str, float]:
    """
    Calculate comprehensive evaluation metrics.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        model_name: Name of model for logging
        
    Returns:
        Dictionary of evaluation metrics
    """
    # Basic regression metrics
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    
    # R² score
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot)
    
    # Additional metrics
    max_error = np.max(np.abs(y_true - y_pred))
    median_ae = np.median(np.abs(y_true - y_pred))
    
    # Bias metrics
    bias = np.mean(y_pred - y_true)
    bias_pct = (bias / np.mean(y_true)) * 100
    
    metrics = {
        f"{model_name}_mae": mae,
        f"{model_name}_rmse": rmse,
        f"{model_name}_mape": mape,
        f"{model_name}_r2": r2,
        f"{model_name}_max_error": max_error,
        f"{model_name}_median_ae": median_ae,
        f"{model_name}_bias": bias,
        f"{model_name}_bias_pct": bias_pct
    }
    
    return metrics


def create_evaluation_plots(
    y_true: np.ndarray,
    predictions: Dict[str, np.ndarray],
    timestamps: Optional[pd.Series] = None,
    output_dir: str = "plots"
) -> List[str]:
    """
    Create evaluation plots for model comparison.
    
    Args:
        y_true: True values
        predictions: Dictionary of model predictions
        timestamps: Timestamps for time series plots
        output_dir: Directory to save plots
        
    Returns:
        List of plot file paths
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    plot_files = []
    
    # Set style
    plt.style.use('seaborn-v0_8')
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # 1. Actual vs Predicted scatter plots
    fig, axes = plt.subplots(1, len(predictions), figsize=(5*len(predictions), 5))
    if len(predictions) == 1:
        axes = [axes]
    
    for i, (model_name, y_pred) in enumerate(predictions.items()):
        ax = axes[i]
        ax.scatter(y_true, y_pred, alpha=0.6, color=colors[i % len(colors)])
        
        # Perfect prediction line
        min_val, max_val = min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8)
        
        ax.set_xlabel('Actual Load (MW)')
        ax.set_ylabel('Predicted Load (MW)')
        ax.set_title(f'{model_name} - Actual vs Predicted')
        ax.grid(True, alpha=0.3)
        
        # Add R² to plot
        r2 = 1 - np.sum((y_true - y_pred)**2) / np.sum((y_true - np.mean(y_true))**2)
        ax.text(0.05, 0.95, f'R² = {r2:.3f}', transform=ax.transAxes, 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    scatter_path = f"{output_dir}/actual_vs_predicted.png"
    plt.savefig(scatter_path, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(scatter_path)
    
    # 2. Time series plot (if timestamps provided)
    if timestamps is not None:
        fig, ax = plt.subplots(figsize=(15, 6))
        
        # Plot actual values
        ax.plot(timestamps, y_true, label='Actual', color='black', linewidth=1)
        
        # Plot predictions
        for i, (model_name, y_pred) in enumerate(predictions.items()):
            ax.plot(timestamps, y_pred, label=model_name, 
                   color=colors[i % len(colors)], linewidth=1, alpha=0.8)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Load (MW)')
        ax.set_title('Power Demand Forecasting - Time Series Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        timeseries_path = f"{output_dir}/timeseries_comparison.png"
        plt.savefig(timeseries_path, dpi=300, bbox_inches='tight')
        plt.close()
        plot_files.append(timeseries_path)
    
    # 3. Residuals plot
    fig, axes = plt.subplots(1, len(predictions), figsize=(5*len(predictions), 5))
    if len(predictions) == 1:
        axes = [axes]
    
    for i, (model_name, y_pred) in enumerate(predictions.items()):
        ax = axes[i]
        residuals = y_true - y_pred
        
        ax.scatter(y_pred, residuals, alpha=0.6, color=colors[i % len(colors)])
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.8)
        
        ax.set_xlabel('Predicted Load (MW)')
        ax.set_ylabel('Residuals (MW)')
        ax.set_title(f'{model_name} - Residuals')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    residuals_path = f"{output_dir}/residuals.png"
    plt.savefig(residuals_path, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(residuals_path)
    
    # 4. Error distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for i, (model_name, y_pred) in enumerate(predictions.items()):
        errors = np.abs(y_true - y_pred)
        ax.hist(errors, bins=50, alpha=0.7, label=model_name, 
               color=colors[i % len(colors)], density=True)
    
    ax.set_xlabel('Absolute Error (MW)')
    ax.set_ylabel('Density')
    ax.set_title('Error Distribution Comparison')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    error_dist_path = f"{output_dir}/error_distribution.png"
    plt.savefig(error_dist_path, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(error_dist_path)
    
    return plot_files


def create_metrics_comparison(metrics_dict: Dict[str, Dict[str, float]]) -> pd.DataFrame:
    """
    Create comparison table of model metrics.
    
    Args:
        metrics_dict: Dictionary of model metrics
        
    Returns:
        DataFrame with metrics comparison
    """
    # Extract model names and metric types
    all_metrics = {}
    
    for model_name, metrics in metrics_dict.items():
        for metric_name, value in metrics.items():
            # Remove model prefix from metric name
            clean_metric = metric_name.replace(f"{model_name}_", "")
            
            if clean_metric not in all_metrics:
                all_metrics[clean_metric] = {}
            all_metrics[clean_metric][model_name] = value
    
    # Create DataFrame
    comparison_df = pd.DataFrame(all_metrics).T
    
    # Round values for better display
    comparison_df = comparison_df.round(3)
    
    return comparison_df


def main():
    """Main function for model evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate power demand forecasting models")
    parser.add_argument("--features", default="data/features/features.parquet", help="Path to features")
    parser.add_argument("--horizon", type=int, default=1, help="Forecast horizon in hours")
    parser.add_argument("--models", default="power-nowcast-xgb,power-nowcast-lstm", 
                       help="Comma-separated list of model names")
    parser.add_argument("--output-dir", default="plots", help="Output directory for plots")
    
    args = parser.parse_args()
    
    # Parse model names
    model_names = [name.strip() for name in args.models.split(",")]
    
    # Start MLflow run for evaluation tracking
    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"evaluation_h{args.horizon}"):
        
        # Log parameters
        mlflow.log_params({
            "evaluation_type": "model_comparison",
            "horizon": args.horizon,
            "models": args.models,
            "features_path": args.features
        })
        
        try:
            print(f"Evaluating models for {args.horizon}-hour horizon: {model_names}")
            
            # Load test data (this would need to be implemented based on your data split strategy)
            # For now, we'll create a placeholder
            print("Note: This evaluation script needs test data loading implementation")
            print("Consider implementing a consistent test set across all models")
            
            # Create placeholder metrics for demonstration
            all_metrics = {}
            predictions = {}
            
            for model_name in model_names:
                # Placeholder metrics (replace with actual model evaluation)
                all_metrics[model_name] = {
                    f"{model_name}_mae": np.random.uniform(50, 150),
                    f"{model_name}_rmse": np.random.uniform(80, 200),
                    f"{model_name}_mape": np.random.uniform(3, 8),
                    f"{model_name}_r2": np.random.uniform(0.85, 0.95)
                }
                
                # Placeholder predictions (replace with actual predictions)
                predictions[model_name] = np.random.normal(1000, 200, 1000)
            
            # Create comparison table
            comparison_df = create_metrics_comparison(all_metrics)
            print("\nModel Performance Comparison:")
            print(comparison_df)
            
            # Save comparison table
            comparison_path = f"{args.output_dir}/metrics_comparison.csv"
            Path(args.output_dir).mkdir(parents=True, exist_ok=True)
            comparison_df.to_csv(comparison_path)
            
            # Log metrics to MLflow
            for model_metrics in all_metrics.values():
                mlflow.log_metrics(model_metrics)
            
            # Log comparison table as artifact
            mlflow.log_artifact(comparison_path)
            
            print(f"\nEvaluation completed. Results saved to {args.output_dir}")
            
        except Exception as e:
            print(f"Error during evaluation: {e}")
            mlflow.log_param("error", str(e))
            raise


if __name__ == "__main__":
    main()
