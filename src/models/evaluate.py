#!/usr/bin/env python3
"""
Model Evaluation for Power Demand Forecasting.

Comprehensive evaluation of trained models with visualization and performance
analysis across different forecast horizons and time periods. Implements
Section 11 of the implementation plan with diagnostic plots and artifacts.
"""

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import mlflow
import mlflow.pyfunc
import mlflow.pytorch
import mlflow.xgboost
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error


def load_model_from_registry(
    model_name: str,
    version: Union[str, int] = "latest"
) -> Tuple[mlflow.pyfunc.PyFuncModel, Dict[str, str]]:
    """
    Load model from MLflow Model Registry per Section 12.

    Args:
        model_name: Name of registered model
        version: Model version to load ("latest", "Production", "Staging", or version number)

    Returns:
        Tuple of (loaded model, model metadata)

    Raises:
        RuntimeError: If model cannot be loaded
    """
    print(f"Loading model {model_name} version {version}")

    # Construct model URI
    model_uri = f"models:/{model_name}/{version}"

    try:
        # Load model using pyfunc interface for consistency
        model = mlflow.pyfunc.load_model(model_uri)

        # Get model metadata
        from mlflow.tracking import MlflowClient
        client = MlflowClient()

        if isinstance(version, str) and version in ["latest", "Production", "Staging"]:
            # Get latest version or by stage
            if version == "latest":
                model_versions = client.get_latest_versions(model_name, stages=None)
                if not model_versions:
                    raise RuntimeError(f"No versions found for model {model_name}")
                model_version = model_versions[0]
            else:
                model_versions = client.get_latest_versions(model_name, stages=[version])
                if not model_versions:
                    raise RuntimeError(f"No {version} version found for model {model_name}")
                model_version = model_versions[0]
        else:
            # Get specific version
            model_version = client.get_model_version(model_name, str(version))

        metadata = {
            "name": model_name,
            "version": model_version.version,
            "stage": model_version.current_stage,
            "run_id": model_version.run_id,
            "creation_timestamp": str(model_version.creation_timestamp),
            "description": model_version.description or ""
        }

        print(f"Successfully loaded {model_name} v{model_version.version} ({model_version.current_stage})")
        return model, metadata

    except Exception as e:
        raise RuntimeError(f"Failed to load model {model_name} version {version}: {e}")


def promote_model_to_stage(
    model_name: str,
    version: Union[str, int],
    stage: str,
    description: Optional[str] = None
) -> None:
    """
    Promote model to specified stage per Section 12.

    Args:
        model_name: Name of registered model
        version: Model version to promote
        stage: Target stage ("Staging", "Production", "Archived")
        description: Optional description for the transition

    Raises:
        RuntimeError: If promotion fails
    """
    try:
        from mlflow.tracking import MlflowClient
        client = MlflowClient()

        # Transition model version to new stage
        client.transition_model_version_stage(
            name=model_name,
            version=str(version),
            stage=stage,
            archive_existing_versions=True  # Archive previous versions in same stage
        )

        # Add description if provided
        if description:
            client.update_model_version(
                name=model_name,
                version=str(version),
                description=description
            )

        print(f"Successfully promoted {model_name} v{version} to {stage}")

    except Exception as e:
        raise RuntimeError(f"Failed to promote model {model_name} v{version} to {stage}: {e}")


def add_model_tags(
    model_name: str,
    version: Union[str, int],
    tags: Dict[str, str]
) -> None:
    """
    Add tags to model version for audit trail per Section 12.

    Args:
        model_name: Name of registered model
        version: Model version
        tags: Dictionary of tags to add (e.g., dataset, horizon, git_sha)

    Raises:
        RuntimeError: If tagging fails
    """
    try:
        from mlflow.tracking import MlflowClient
        client = MlflowClient()

        for key, value in tags.items():
            client.set_model_version_tag(
                name=model_name,
                version=str(version),
                key=key,
                value=value
            )

        print(f"Added {len(tags)} tags to {model_name} v{version}")

    except Exception as e:
        raise RuntimeError(f"Failed to add tags to model {model_name} v{version}: {e}")


def calculate_pinball_loss(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    quantile: float
) -> float:
    """
    Calculate Pinball loss for quantile predictions.

    Args:
        y_true: True values
        y_pred: Predicted quantile values
        quantile: Quantile level (e.g., 0.1, 0.5, 0.9)

    Returns:
        Pinball loss value
    """
    errors = y_true - y_pred
    return np.mean(np.maximum(quantile * errors, (quantile - 1) * errors))


def evaluate_model_performance(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str,
    y_pred_quantiles: Optional[Dict[float, np.ndarray]] = None
) -> Dict[str, float]:
    """
    Calculate comprehensive evaluation metrics per Section 11 of implementation plan.

    Args:
        y_true: True values
        y_pred: Point predictions
        model_name: Name of model for logging
        y_pred_quantiles: Optional quantile predictions for Pinball loss

    Returns:
        Dictionary of evaluation metrics including MAE, RMSE, MAPE, Pinball loss
    """
    # Core metrics from implementation plan
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))

    # MAPE with protection against division by zero
    mape = np.mean(np.abs((y_true - y_pred) / np.clip(np.abs(y_true), 1e-6, None))) * 100

    # R² score
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Additional diagnostic metrics
    max_error = np.max(np.abs(y_true - y_pred))
    median_ae = np.median(np.abs(y_true - y_pred))

    # Bias metrics
    bias = np.mean(y_pred - y_true)
    bias_pct = (bias / np.mean(y_true)) * 100 if np.mean(y_true) != 0 else 0.0

    metrics = {
        f"{model_name}_mae": float(mae),
        f"{model_name}_rmse": float(rmse),
        f"{model_name}_mape": float(mape),
        f"{model_name}_r2": float(r2),
        f"{model_name}_max_error": float(max_error),
        f"{model_name}_median_ae": float(median_ae),
        f"{model_name}_bias": float(bias),
        f"{model_name}_bias_pct": float(bias_pct)
    }

    # Pinball loss for quantiles (τ ∈ {0.1, 0.5, 0.9} per implementation plan)
    if y_pred_quantiles is not None:
        for quantile, y_pred_q in y_pred_quantiles.items():
            pinball = calculate_pinball_loss(y_true, y_pred_q, quantile)
            metrics[f"{model_name}_pinball_{quantile:.1f}"] = float(pinball)

    return metrics


def create_pred_vs_actual_plot(
    y_true: np.ndarray,
    predictions: Dict[str, np.ndarray],
    output_dir: str
) -> str:
    """
    Create prediction vs actual scatter plot per Section 11.

    Args:
        y_true: True values
        predictions: Dictionary of model predictions
        output_dir: Directory to save plots

    Returns:
        Path to saved plot
    """
    fig, axes = plt.subplots(1, len(predictions), figsize=(5*len(predictions), 5))
    if len(predictions) == 1:
        axes = [axes]

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    for i, (model_name, y_pred) in enumerate(predictions.items()):
        ax = axes[i]
        ax.scatter(y_true, y_pred, alpha=0.6, color=colors[i % len(colors)], s=20)

        # Perfect prediction line
        min_val = min(y_true.min(), y_pred.min())
        max_val = max(y_true.max(), y_pred.max())
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8, linewidth=2)

        ax.set_xlabel('Actual Load (MW)', fontsize=12)
        ax.set_ylabel('Predicted Load (MW)', fontsize=12)
        ax.set_title(f'{model_name} - Actual vs Predicted', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        # Add R² and MAE to plot
        r2 = 1 - np.sum((y_true - y_pred)**2) / np.sum((y_true - np.mean(y_true))**2)
        mae = mean_absolute_error(y_true, y_pred)
        ax.text(0.05, 0.95, f'R² = {r2:.3f}\nMAE = {mae:.1f}',
                transform=ax.transAxes, fontsize=11,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    plot_path = Path(output_dir) / "pred_vs_actual.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return str(plot_path)


def create_residual_histogram(
    y_true: np.ndarray,
    predictions: Dict[str, np.ndarray],
    output_dir: str
) -> str:
    """
    Create residual histogram per Section 11.

    Args:
        y_true: True values
        predictions: Dictionary of model predictions
        output_dir: Directory to save plots

    Returns:
        Path to saved plot
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    for i, (model_name, y_pred) in enumerate(predictions.items()):
        residuals = y_true - y_pred
        ax.hist(residuals, bins=50, alpha=0.7, label=model_name,
               color=colors[i % len(colors)], density=True, edgecolor='black', linewidth=0.5)

        # Add vertical line at zero
        ax.axvline(0, color='red', linestyle='--', alpha=0.8, linewidth=2)

        # Add statistics text
        mean_resid = np.mean(residuals)
        std_resid = np.std(residuals)
        ax.text(0.02 + i*0.15, 0.95 - i*0.05,
                f'{model_name}:\nMean: {mean_resid:.1f}\nStd: {std_resid:.1f}',
                transform=ax.transAxes, fontsize=10,
                bbox=dict(boxstyle='round', facecolor=colors[i % len(colors)], alpha=0.3))

    ax.set_xlabel('Residuals (Actual - Predicted) [MW]', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title('Residual Distribution Comparison', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = Path(output_dir) / "residual_hist.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return str(plot_path)


def create_backtest_chart(
    y_true: np.ndarray,
    predictions: Dict[str, np.ndarray],
    timestamps: pd.Series,
    horizon: int,
    output_dir: str
) -> str:
    """
    Create backtest chart by horizon per Section 11.

    Args:
        y_true: True values
        predictions: Dictionary of model predictions
        timestamps: Timestamps for time series
        horizon: Forecast horizon in hours
        output_dir: Directory to save plots

    Returns:
        Path to saved plot
    """
    fig, ax = plt.subplots(figsize=(15, 8))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    # Plot actual values
    ax.plot(timestamps, y_true, label='Actual', color='black', linewidth=2, alpha=0.8)

    # Plot predictions
    for i, (model_name, y_pred) in enumerate(predictions.items()):
        ax.plot(timestamps, y_pred, label=f'{model_name} (h={horizon})',
               color=colors[i % len(colors)], linewidth=1.5, alpha=0.8)

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Load (MW)', fontsize=12)
    ax.set_title(f'Backtest Chart - {horizon}h Horizon', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)

    plt.tight_layout()
    plot_path = Path(output_dir) / f"backtest_horizon_{horizon}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return str(plot_path)


def create_evaluation_plots(
    y_true: np.ndarray,
    predictions: Dict[str, np.ndarray],
    timestamps: Optional[pd.Series] = None,
    horizon: int = 1,
    output_dir: str = "plots"
) -> List[str]:
    """
    Create comprehensive evaluation plots per Section 11 of implementation plan.

    Args:
        y_true: True values
        predictions: Dictionary of model predictions
        timestamps: Timestamps for time series plots
        horizon: Forecast horizon for backtest chart
        output_dir: Directory to save plots

    Returns:
        List of plot file paths
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    plot_files = []

    # Set consistent style
    plt.style.use('seaborn-v0_8')

    # 1. Prediction vs Actual scatter plot (Section 11 requirement)
    pred_vs_actual_path = create_pred_vs_actual_plot(y_true, predictions, output_dir)
    plot_files.append(pred_vs_actual_path)

    # 2. Residual histogram (Section 11 requirement)
    residual_hist_path = create_residual_histogram(y_true, predictions, output_dir)
    plot_files.append(residual_hist_path)

    # 3. Backtest chart by horizon (Section 11 requirement)
    if timestamps is not None:
        backtest_path = create_backtest_chart(y_true, predictions, timestamps, horizon, output_dir)
        plot_files.append(backtest_path)

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


def run_comprehensive_evaluation(
    test_features: pd.DataFrame,
    test_targets: pd.Series,
    timestamps: pd.Series,
    model_names: List[str],
    horizon: int,
    output_dir: str = "plots"
) -> Dict[str, Dict[str, float]]:
    """
    Run comprehensive model evaluation per Sections 11-12.

    Args:
        test_features: Test feature matrix
        test_targets: Test target values
        timestamps: Test timestamps
        model_names: List of registered model names to evaluate
        horizon: Forecast horizon in hours
        output_dir: Directory for plots and artifacts

    Returns:
        Dictionary of model metrics

    Raises:
        RuntimeError: If evaluation fails
    """
    print(f"Running comprehensive evaluation for {len(model_names)} models")

    all_metrics = {}
    predictions = {}
    model_metadata = {}

    # Load models and generate predictions
    for model_name in model_names:
        try:
            print(f"\nEvaluating {model_name}...")

            # Load model from registry
            model, metadata = load_model_from_registry(model_name, "latest")
            model_metadata[model_name] = metadata

            # Generate predictions
            y_pred = model.predict(test_features)
            if hasattr(y_pred, 'flatten'):
                y_pred = y_pred.flatten()

            predictions[model_name] = y_pred

            # Calculate metrics
            metrics = evaluate_model_performance(
                test_targets.values, y_pred, model_name
            )
            all_metrics[model_name] = metrics

            print(f"  MAE: {metrics[f'{model_name}_mae']:.2f}")
            print(f"  RMSE: {metrics[f'{model_name}_rmse']:.2f}")
            print(f"  MAPE: {metrics[f'{model_name}_mape']:.2f}%")
            print(f"  R²: {metrics[f'{model_name}_r2']:.4f}")

        except Exception as e:
            print(f"Failed to evaluate {model_name}: {e}")
            continue

    if not predictions:
        raise RuntimeError("No models could be evaluated successfully")

    # Generate diagnostic plots
    print(f"\nGenerating diagnostic plots...")
    plot_files = create_evaluation_plots(
        test_targets.values, predictions, timestamps, horizon, output_dir
    )

    # Log all artifacts to MLflow
    for plot_file in plot_files:
        mlflow.log_artifact(plot_file)
        print(f"  Logged: {plot_file}")

    # Create and log metrics comparison
    comparison_df = create_metrics_comparison(all_metrics)
    comparison_path = Path(output_dir) / "metrics_comparison.csv"
    comparison_df.to_csv(comparison_path)
    mlflow.log_artifact(str(comparison_path))

    # Log model metadata
    metadata_path = Path(output_dir) / "model_metadata.json"
    import json
    with open(metadata_path, 'w') as f:
        json.dump(model_metadata, f, indent=2)
    mlflow.log_artifact(str(metadata_path))

    return all_metrics


def main() -> None:
    """Main function for comprehensive model evaluation per Sections 11-12."""
    parser = argparse.ArgumentParser(description="Comprehensive model evaluation with MLflow Registry")
    parser.add_argument("--features", default="data/features/features.parquet", help="Path to test features")
    parser.add_argument("--horizon", type=int, default=1, help="Forecast horizon in hours")
    parser.add_argument("--models", default="power-nowcast-xgb,power-nowcast-lstm",
                       help="Comma-separated list of registered model names")
    parser.add_argument("--output-dir", default="plots", help="Output directory for plots and artifacts")
    parser.add_argument("--promote-best", action="store_true", help="Promote best model to Production")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test set size for evaluation")

    args = parser.parse_args()

    # Parse model names
    model_names = [name.strip() for name in args.models.split(",")]

    # Start MLflow run for evaluation tracking
    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"comprehensive_eval_h{args.horizon}"):

        # Log parameters
        mlflow.log_params({
            "evaluation_type": "comprehensive_registry_evaluation",
            "horizon": args.horizon,
            "models": args.models,
            "features_path": args.features,
            "test_size": args.test_size,
            "promote_best": args.promote_best
        })

        try:
            print(f"Loading test data from {args.features}")

            # Load features and prepare test set
            df = pd.read_parquet(args.features)
            target_col = [col for col in df.columns if 'target' in col][0]

            # Use last portion as test set (time series: no shuffle)
            test_start_idx = int(len(df) * (1 - args.test_size))
            test_df = df.iloc[test_start_idx:].copy()

            # Prepare test data
            exclude_cols = ['timestamp', target_col, 'region_power', 'region_weather',
                          'data_source_power', 'data_source_weather']
            feature_cols = [col for col in test_df.columns if col not in exclude_cols]
            numeric_cols = test_df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()

            test_features = test_df[numeric_cols].dropna()
            test_targets = test_df.loc[test_features.index, target_col]
            timestamps = test_df.loc[test_features.index, 'timestamp']

            print(f"Test set: {len(test_features)} samples, {len(numeric_cols)} features")

            # Run comprehensive evaluation
            all_metrics = run_comprehensive_evaluation(
                test_features, test_targets, timestamps, model_names, args.horizon, args.output_dir
            )

            # Log all metrics to MLflow
            for model_metrics in all_metrics.values():
                mlflow.log_metrics(model_metrics)

            # Find best model by MAE
            if args.promote_best and all_metrics:
                best_model = min(all_metrics.keys(),
                               key=lambda m: all_metrics[m][f"{m}_mae"])

                print(f"\nBest model by MAE: {best_model}")

                # Get model version for promotion
                model, metadata = load_model_from_registry(best_model, "latest")

                # Promote to Production
                promote_model_to_stage(
                    best_model,
                    metadata["version"],
                    "Production",
                    f"Promoted after comprehensive evaluation (h={args.horizon}, MAE={all_metrics[best_model][f'{best_model}_mae']:.2f})"
                )

                # Add audit tags
                import subprocess
                try:
                    git_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
                except:
                    git_sha = "unknown"

                add_model_tags(best_model, metadata["version"], {
                    "evaluation_date": str(pd.Timestamp.now()),
                    "horizon": str(args.horizon),
                    "git_sha": git_sha,
                    "test_mae": f"{all_metrics[best_model][f'{best_model}_mae']:.2f}",
                    "promoted_by": "comprehensive_evaluation"
                })

                mlflow.log_param("promoted_model", best_model)
                mlflow.log_param("promoted_version", metadata["version"])

            print(f"\nComprehensive evaluation completed. Results in {args.output_dir}")

        except Exception as e:
            print(f"Error during evaluation: {e}")
            mlflow.log_param("error", str(e))
            raise


if __name__ == "__main__":
    main()
