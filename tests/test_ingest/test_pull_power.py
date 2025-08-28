#!/usr/bin/env python3
"""
Tests for power data ingestion module.

Tests cover synthetic data generation, API integration fallbacks,
data validation, and error handling scenarios.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import pandas as pd
import numpy as np

from src.ingest.pull_power import (
    generate_synthetic_power_data,
    fetch_nyiso_data,
    fetch_caiso_data,
    save_power_data,
    _fallback_to_synthetic
)


class TestSyntheticPowerData:
    """Test synthetic power data generation."""

    def test_generate_synthetic_power_data_basic(self):
        """Test basic synthetic data generation."""
        days = 30
        df = generate_synthetic_power_data(days)
        
        # Check DataFrame structure
        assert isinstance(df, pd.DataFrame)
        expected_cols = {"timestamp", "load", "region", "data_source"}
        assert set(df.columns) == expected_cols
        
        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
        assert pd.api.types.is_numeric_dtype(df["load"])
        assert df["region"].dtype == "object"
        assert df["data_source"].dtype == "object"
        
        # Check data ranges
        assert len(df) > 0
        assert df["load"].min() >= 1000  # Minimum load constraint
        assert df["load"].max() > df["load"].min()  # Should have variation
        
        # Check metadata
        assert all(df["region"] == "SYNTHETIC")
        assert all(df["data_source"] == "generated")

    def test_generate_synthetic_power_data_duration(self):
        """Test that generated data spans the correct time period."""
        days = 7
        df = generate_synthetic_power_data(days)
        
        time_span = df["timestamp"].max() - df["timestamp"].min()
        expected_hours = days * 24
        actual_hours = len(df)
        
        # Should have approximately the right number of hours (±1 for rounding)
        assert abs(actual_hours - expected_hours) <= 1
        assert time_span.days >= days - 1  # Account for partial days

    def test_generate_synthetic_power_data_patterns(self):
        """Test that synthetic data has realistic patterns."""
        days = 365  # Full year to test seasonal patterns
        df = generate_synthetic_power_data(days)
        
        # Test daily patterns - should have higher load during day vs night
        df["hour"] = df["timestamp"].dt.hour
        day_hours = df[df["hour"].between(10, 18)]["load"].mean()
        night_hours = df[df["hour"].between(22, 6)]["load"].mean()
        assert day_hours > night_hours, "Day load should be higher than night load"
        
        # Test weekly patterns - should have lower load on weekends
        df["weekday"] = df["timestamp"].dt.weekday
        weekday_load = df[df["weekday"] < 5]["load"].mean()
        weekend_load = df[df["weekday"] >= 5]["load"].mean()
        assert weekday_load > weekend_load, "Weekday load should be higher than weekend load"

    def test_generate_synthetic_power_data_reproducibility(self):
        """Test that synthetic data generation is reproducible."""
        days = 10
        df1 = generate_synthetic_power_data(days)
        df2 = generate_synthetic_power_data(days)
        
        # Should be identical due to fixed random seed
        pd.testing.assert_frame_equal(df1, df2)


class TestAPIIntegration:
    """Test API integration functions."""

    @patch('src.ingest.pull_power.requests.get')
    def test_fetch_nyiso_data_success(self, mock_get):
        """Test successful NYISO data fetch."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """Time Stamp,Name,PTID,Load
2024-01-01 00:00:00,NYISO,61757,15000
2024-01-01 01:00:00,NYISO,61757,14500
2024-01-01 02:00:00,NYISO,61757,14000"""
        mock_get.return_value = mock_response
        
        df = fetch_nyiso_data(days=1)
        
        # Check result
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "timestamp" in df.columns
        assert "load" in df.columns
        assert all(df["region"] == "NYISO")
        assert all(df["data_source"] == "nyiso_oasis_api")

    @patch('src.ingest.pull_power.requests.get')
    def test_fetch_nyiso_data_api_failure(self, mock_get):
        """Test NYISO data fetch with API failure."""
        # Mock API failure
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        df = fetch_nyiso_data(days=1)
        
        # Should fallback to synthetic data
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(df["region"] == "NYISO")
        assert all(df["data_source"] == "nyiso_synthetic_fallback")

    @patch('src.ingest.pull_power.requests.get')
    def test_fetch_caiso_data_api_failure(self, mock_get):
        """Test CAISO data fetch with API failure."""
        # Mock API failure
        mock_get.side_effect = Exception("Network error")
        
        df = fetch_caiso_data(days=1)
        
        # Should fallback to synthetic data
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(df["region"] == "CAISO")
        assert all(df["data_source"] == "caiso_synthetic_fallback")


class TestFallbackFunction:
    """Test fallback to synthetic data."""

    def test_fallback_to_synthetic(self):
        """Test fallback function creates properly labeled synthetic data."""
        region = "TEST_REGION"
        days = 5
        
        df = _fallback_to_synthetic(region, days)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(df["region"] == region)
        assert all(df["data_source"] == "test_region_synthetic_fallback")
        
        # Should have all required columns
        expected_cols = {"timestamp", "load", "region", "data_source"}
        assert set(df.columns) == expected_cols


class TestDataSaving:
    """Test data saving functionality."""

    def test_save_power_data(self):
        """Test saving power data to parquet file."""
        # Create test data
        df = generate_synthetic_power_data(days=1)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_power.parquet"
            
            # Save data
            result_path = save_power_data(df, str(output_path))
            
            # Check file was created
            assert Path(result_path).exists()
            assert result_path == str(output_path)
            
            # Check file can be read back
            loaded_df = pd.read_parquet(output_path)
            pd.testing.assert_frame_equal(df, loaded_df)

    def test_save_power_data_creates_directory(self):
        """Test that save_power_data creates output directory if it doesn't exist."""
        df = generate_synthetic_power_data(days=1)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "dir" / "test_power.parquet"
            
            # Directory doesn't exist yet
            assert not output_path.parent.exists()
            
            # Save data
            save_power_data(df, str(output_path))
            
            # Directory should be created
            assert output_path.parent.exists()
            assert output_path.exists()


class TestDataValidation:
    """Test data validation and quality checks."""

    def test_power_data_quality(self):
        """Test that generated power data meets quality requirements."""
        df = generate_synthetic_power_data(days=30)
        
        # No missing values
        assert not df.isnull().any().any()
        
        # Timestamps are monotonic
        assert df["timestamp"].is_monotonic_increasing
        
        # Load values are positive
        assert (df["load"] > 0).all()
        
        # Load values are reasonable (between 1 GW and 50 GW)
        assert (df["load"] >= 1000).all()
        assert (df["load"] <= 50000).all()
        
        # Timestamps are hourly
        time_diffs = df["timestamp"].diff().dropna()
        expected_diff = pd.Timedelta(hours=1)
        assert (time_diffs == expected_diff).all()

    def test_power_data_columns(self):
        """Test that power data has required columns with correct types."""
        df = generate_synthetic_power_data(days=1)
        
        # Required columns exist
        required_cols = ["timestamp", "load", "region", "data_source"]
        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"
        
        # Correct data types
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
        assert pd.api.types.is_numeric_dtype(df["load"])
        assert df["region"].dtype == "object"
        assert df["data_source"].dtype == "object"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_days(self):
        """Test handling of zero days request."""
        with pytest.raises(ValueError):
            generate_synthetic_power_data(days=0)

    def test_negative_days(self):
        """Test handling of negative days request."""
        with pytest.raises(ValueError):
            generate_synthetic_power_data(days=-1)

    def test_very_large_days(self):
        """Test handling of very large days request."""
        # Should work but might be slow
        df = generate_synthetic_power_data(days=1000)
        assert len(df) > 20000  # Should have many hours of data


if __name__ == "__main__":
    pytest.main([__file__])
