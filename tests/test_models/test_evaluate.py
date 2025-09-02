#!/usr/bin/env python3
"""
Tests for model evaluation and registry functionality.

Tests cover Sections 11-12 of implementation plan: comprehensive evaluation,
diagnostic plots, model registry integration, and promotion workflows.
"""

import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch, MagicMock
import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for testing

from src.models.evaluate import (
    calculate_pinball_loss,
    evaluate_model_performance,
    create_pred_vs_actual_plot,
    create_residual_histogram,
    create_backtest_chart,
    create_evaluation_plots,
    create_metrics_comparison,
    load_model_from_registry,
    promote_model_to_stage,
    add_model_tags
)


class TestPinballLoss:
    """Test Pinball loss calculation per Section 11."""

    def test_calculate_pinball_loss_basic(self) -> None:
        """Test basic Pinball loss calculation."""
        y_true = np.array([100, 200, 150, 180])
        y_pred = np.array([90, 190, 140, 170])
        
        # Test different quantiles
        pinball_10 = calculate_pinball_loss(y_true, y_pred, 0.1)
        pinball_50 = calculate_pinball_loss(y_true, y_pred, 0.5)
        pinball_90 = calculate_pinball_loss(y_true, y_pred, 0.9)
        
        # All should be positive
        assert pinball_10 >= 0
        assert pinball_50 >= 0
        assert pinball_90 >= 0
        
        # Different quantiles should give different results
        assert pinball_10 != pinball_90

    def test_calculate_pinball_loss_perfect_prediction(self) -> None:
        """Test Pinball loss with perfect predictions."""
        y_true = np.array([100, 200, 150, 180])
        y_pred = y_true.copy()  # Perfect predictions
        
        for quantile in [0.1, 0.5, 0.9]:
            pinball = calculate_pinball_loss(y_true, y_pred, quantile)
            assert pinball == 0.0, f"Perfect prediction should have zero Pinball loss for quantile {quantile}"

    def test_calculate_pinball_loss_edge_cases(self) -> None:
        """Test Pinball loss edge cases."""
        y_true = np.array([100])
        y_pred = np.array([110])  # Over-prediction
        
        # For high quantiles, over-prediction should be penalized less
        pinball_10 = calculate_pinball_loss(y_true, y_pred, 0.1)
        pinball_90 = calculate_pinball_loss(y_true, y_pred, 0.9)
        
        assert pinball_10 > pinball_90


class TestModelPerformanceEvaluation:
    """Test comprehensive model performance evaluation per Section 11."""

    def test_evaluate_model_performance_basic(self) -> None:
        """Test basic model performance evaluation."""
        y_true = np.array([100, 200, 150, 180, 120])
        y_pred = np.array([95, 195, 145, 175, 125])
        
        metrics = evaluate_model_performance(y_true, y_pred, "test_model")
        
        # Check all required metrics are present
        expected_metrics = [
            "test_model_mae", "test_model_rmse", "test_model_mape", "test_model_r2",
            "test_model_max_error", "test_model_median_ae", "test_model_bias", "test_model_bias_pct"
        ]
        
        for metric in expected_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
            assert isinstance(metrics[metric], float), f"Metric {metric} should be float"

    def test_evaluate_model_performance_with_quantiles(self) -> None:
        """Test model performance evaluation with quantile predictions."""
        y_true = np.array([100, 200, 150, 180])
        y_pred = np.array([95, 195, 145, 175])
        
        # Mock quantile predictions
        y_pred_quantiles = {
            0.1: np.array([85, 185, 135, 165]),
            0.5: y_pred,  # Median should be same as point prediction
            0.9: np.array([105, 205, 155, 185])
        }
        
        metrics = evaluate_model_performance(y_true, y_pred, "test_model", y_pred_quantiles)
        
        # Check Pinball loss metrics are included
        assert "test_model_pinball_0.1" in metrics
        assert "test_model_pinball_0.5" in metrics
        assert "test_model_pinball_0.9" in metrics

    def test_evaluate_model_performance_edge_cases(self) -> None:
        """Test model performance evaluation edge cases."""
        # Test with zero values (MAPE protection)
        y_true = np.array([0, 100, 200])
        y_pred = np.array([5, 95, 195])
        
        metrics = evaluate_model_performance(y_true, y_pred, "test_model")
        
        # Should not crash and should return finite values
        assert np.isfinite(metrics["test_model_mape"])
        assert np.isfinite(metrics["test_model_bias_pct"])

    def test_evaluate_model_performance_perfect_prediction(self) -> None:
        """Test evaluation with perfect predictions."""
        y_true = np.array([100, 200, 150, 180])
        y_pred = y_true.copy()
        
        metrics = evaluate_model_performance(y_true, y_pred, "perfect_model")
        
        # Perfect prediction should have specific metric values
        assert metrics["perfect_model_mae"] == 0.0
        assert metrics["perfect_model_rmse"] == 0.0
        assert metrics["perfect_model_mape"] == 0.0
        assert metrics["perfect_model_r2"] == 1.0
        assert metrics["perfect_model_bias"] == 0.0


class TestDiagnosticPlots:
    """Test diagnostic plot generation per Section 11."""

    def test_create_pred_vs_actual_plot(self) -> None:
        """Test prediction vs actual scatter plot creation."""
        y_true = np.random.normal(1000, 200, 100)
        predictions = {
            "model_1": y_true + np.random.normal(0, 50, 100),
            "model_2": y_true + np.random.normal(0, 100, 100)
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            plot_path = create_pred_vs_actual_plot(y_true, predictions, temp_dir)
            
            # Check plot file was created
            assert Path(plot_path).exists()
            assert plot_path.endswith("pred_vs_actual.png")

    def test_create_residual_histogram(self) -> None:
        """Test residual histogram creation."""
        y_true = np.random.normal(1000, 200, 100)
        predictions = {
            "model_1": y_true + np.random.normal(0, 50, 100)
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            plot_path = create_residual_histogram(y_true, predictions, temp_dir)
            
            # Check plot file was created
            assert Path(plot_path).exists()
            assert plot_path.endswith("residual_hist.png")

    def test_create_backtest_chart(self) -> None:
        """Test backtest chart creation."""
        timestamps = pd.date_range('2024-01-01', periods=100, freq='h')
        y_true = np.random.normal(1000, 200, 100)
        predictions = {
            "model_1": y_true + np.random.normal(0, 50, 100)
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            plot_path = create_backtest_chart(y_true, predictions, timestamps, horizon=1, output_dir=temp_dir)
            
            # Check plot file was created
            assert Path(plot_path).exists()
            assert "backtest_horizon_1.png" in plot_path

    def test_create_evaluation_plots_comprehensive(self) -> None:
        """Test comprehensive evaluation plot creation."""
        timestamps = pd.date_range('2024-01-01', periods=100, freq='h')
        y_true = np.random.normal(1000, 200, 100)
        predictions = {
            "xgb_model": y_true + np.random.normal(0, 50, 100),
            "lstm_model": y_true + np.random.normal(0, 75, 100)
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            plot_files = create_evaluation_plots(y_true, predictions, timestamps, horizon=1, output_dir=temp_dir)
            
            # Check all required plots were created
            assert len(plot_files) == 3  # pred_vs_actual, residual_hist, backtest
            
            for plot_file in plot_files:
                assert Path(plot_file).exists()


class TestMetricsComparison:
    """Test metrics comparison functionality."""

    def test_create_metrics_comparison(self) -> None:
        """Test metrics comparison table creation."""
        metrics_dict = {
            "model_1": {
                "model_1_mae": 50.0,
                "model_1_rmse": 75.0,
                "model_1_mape": 5.0,
                "model_1_r2": 0.85
            },
            "model_2": {
                "model_2_mae": 60.0,
                "model_2_rmse": 85.0,
                "model_2_mape": 6.0,
                "model_2_r2": 0.80
            }
        }
        
        comparison_df = create_metrics_comparison(metrics_dict)
        
        # Check DataFrame structure
        assert isinstance(comparison_df, pd.DataFrame)
        assert "model_1" in comparison_df.columns
        assert "model_2" in comparison_df.columns
        assert "mae" in comparison_df.index
        assert "rmse" in comparison_df.index
        assert "mape" in comparison_df.index
        assert "r2" in comparison_df.index
        
        # Check values
        assert comparison_df.loc["mae", "model_1"] == 50.0
        assert comparison_df.loc["mae", "model_2"] == 60.0


class TestModelRegistry:
    """Test model registry functionality per Section 12."""

    @patch('src.models.evaluate.mlflow.pyfunc.load_model')
    @patch('mlflow.tracking.MlflowClient')
    def test_load_model_from_registry_latest(self, mock_client_class: Mock, mock_load_model: Mock) -> None:
        """Test loading latest model from registry."""
        # Mock MLflow client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock model version
        mock_version = Mock()
        mock_version.version = "1"
        mock_version.current_stage = "None"
        mock_version.run_id = "test_run_id"
        mock_version.creation_timestamp = 1234567890
        mock_version.description = "Test model"
        
        mock_client.get_latest_versions.return_value = [mock_version]
        
        # Mock loaded model
        mock_model = Mock()
        mock_load_model.return_value = mock_model
        
        # Test loading
        model, metadata = load_model_from_registry("test_model", "latest")
        
        # Check results
        assert model == mock_model
        assert metadata["name"] == "test_model"
        assert metadata["version"] == "1"
        assert metadata["stage"] == "None"

    @patch('mlflow.tracking.MlflowClient')
    def test_promote_model_to_stage(self, mock_client_class: Mock) -> None:
        """Test model promotion to stage."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Test promotion
        promote_model_to_stage("test_model", "1", "Production", "Test promotion")
        
        # Check client was called correctly
        mock_client.transition_model_version_stage.assert_called_once_with(
            name="test_model",
            version="1",
            stage="Production",
            archive_existing_versions=True
        )
        
        mock_client.update_model_version.assert_called_once_with(
            name="test_model",
            version="1",
            description="Test promotion"
        )

    @patch('mlflow.tracking.MlflowClient')
    def test_add_model_tags(self, mock_client_class: Mock) -> None:
        """Test adding tags to model version."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        tags = {
            "dataset": "test_dataset",
            "horizon": "1",
            "git_sha": "abc123"
        }
        
        # Test adding tags
        add_model_tags("test_model", "1", tags)
        
        # Check client was called for each tag
        assert mock_client.set_model_version_tag.call_count == 3


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_load_model_from_registry_not_found(self) -> None:
        """Test loading non-existent model from registry."""
        with patch('src.models.evaluate.mlflow.pyfunc.load_model') as mock_load:
            mock_load.side_effect = Exception("Model not found")
            
            with pytest.raises(RuntimeError, match="Failed to load model"):
                load_model_from_registry("nonexistent_model", "latest")

    def test_promote_model_to_stage_failure(self) -> None:
        """Test model promotion failure."""
        with patch('mlflow.tracking.MlflowClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.transition_model_version_stage.side_effect = Exception("Promotion failed")
            
            with pytest.raises(RuntimeError, match="Failed to promote model"):
                promote_model_to_stage("test_model", "1", "Production")

    def test_add_model_tags_failure(self) -> None:
        """Test adding tags failure."""
        with patch('mlflow.tracking.MlflowClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.set_model_version_tag.side_effect = Exception("Tagging failed")
            
            with pytest.raises(RuntimeError, match="Failed to add tags"):
                add_model_tags("test_model", "1", {"test": "tag"})


class TestIntegration:
    """Test integration scenarios."""

    def test_evaluation_metrics_consistency(self) -> None:
        """Test that evaluation metrics are consistent across functions."""
        y_true = np.array([100, 200, 150, 180, 120])
        y_pred = np.array([95, 195, 145, 175, 125])
        
        # Calculate metrics using our function
        metrics = evaluate_model_performance(y_true, y_pred, "test_model")
        
        # Manually calculate some metrics for verification
        manual_mae = np.mean(np.abs(y_true - y_pred))
        manual_rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        
        # Check consistency
        assert abs(metrics["test_model_mae"] - manual_mae) < 1e-10
        assert abs(metrics["test_model_rmse"] - manual_rmse) < 1e-10

    def test_plot_generation_with_real_data(self) -> None:
        """Test plot generation with realistic data patterns."""
        # Generate realistic power demand data
        timestamps = pd.date_range('2024-01-01', periods=168, freq='h')  # 1 week
        base_load = 1000
        daily_pattern = 200 * np.sin(2 * np.pi * np.arange(168) / 24)
        weekly_pattern = 100 * np.sin(2 * np.pi * np.arange(168) / (24 * 7))
        noise = np.random.normal(0, 50, 168)
        
        y_true = base_load + daily_pattern + weekly_pattern + noise
        
        # Generate predictions with different error patterns
        predictions = {
            "good_model": y_true + np.random.normal(0, 30, 168),
            "poor_model": y_true + np.random.normal(50, 80, 168)  # Biased and noisy
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            plot_files = create_evaluation_plots(y_true, predictions, timestamps, horizon=1, output_dir=temp_dir)
            
            # All plots should be generated successfully
            assert len(plot_files) == 3
            for plot_file in plot_files:
                assert Path(plot_file).exists()
                # Check file size is reasonable (not empty)
                assert Path(plot_file).stat().st_size > 1000  # At least 1KB


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
