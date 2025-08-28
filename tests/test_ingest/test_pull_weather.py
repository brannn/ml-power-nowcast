#!/usr/bin/env python3
"""
Tests for weather data ingestion module.

Tests cover synthetic weather generation, API integration fallbacks,
data validation, and error handling scenarios.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import pandas as pd
import numpy as np

from src.ingest.pull_weather import (
    generate_synthetic_weather_data,
    fetch_noaa_weather_data,
    fetch_meteostat_data,
    save_weather_data,
    _fallback_to_synthetic_weather
)


class TestSyntheticWeatherData:
    """Test synthetic weather data generation."""

    def test_generate_synthetic_weather_data_basic(self):
        """Test basic synthetic weather data generation."""
        days = 30
        df = generate_synthetic_weather_data(days)
        
        # Check DataFrame structure
        assert isinstance(df, pd.DataFrame)
        expected_cols = {"timestamp", "temp_c", "humidity", "wind_speed", "region", "data_source"}
        assert set(df.columns) == expected_cols
        
        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
        assert pd.api.types.is_numeric_dtype(df["temp_c"])
        assert pd.api.types.is_numeric_dtype(df["humidity"])
        assert pd.api.types.is_numeric_dtype(df["wind_speed"])
        assert df["region"].dtype == "object"
        assert df["data_source"].dtype == "object"
        
        # Check data ranges
        assert len(df) > 0
        assert df["temp_c"].min() > -50  # Reasonable temperature range
        assert df["temp_c"].max() < 60
        assert df["humidity"].min() >= 10  # Humidity constraints
        assert df["humidity"].max() <= 95
        assert df["wind_speed"].min() >= 0  # Wind speed non-negative
        
        # Check metadata
        assert all(df["region"] == "SYNTHETIC")
        assert all(df["data_source"] == "generated")

    def test_generate_synthetic_weather_data_patterns(self):
        """Test that synthetic weather data has realistic patterns."""
        days = 365  # Full year to test seasonal patterns
        df = generate_synthetic_weather_data(days)
        
        # Test seasonal patterns - summer should be warmer than winter
        df["month"] = df["timestamp"].dt.month
        summer_temp = df[df["month"].isin([6, 7, 8])]["temp_c"].mean()
        winter_temp = df[df["month"].isin([12, 1, 2])]["temp_c"].mean()
        assert summer_temp > winter_temp, "Summer should be warmer than winter"
        
        # Test daily patterns - day should be warmer than night
        df["hour"] = df["timestamp"].dt.hour
        day_temp = df[df["hour"].between(12, 16)]["temp_c"].mean()
        night_temp = df[df["hour"].between(0, 6)]["temp_c"].mean()
        assert day_temp > night_temp, "Day should be warmer than night"

    def test_generate_synthetic_weather_data_correlations(self):
        """Test correlations between weather variables."""
        days = 100
        df = generate_synthetic_weather_data(days)
        
        # Temperature and humidity should be somewhat negatively correlated
        temp_humidity_corr = df["temp_c"].corr(df["humidity"])
        assert temp_humidity_corr < 0, "Temperature and humidity should be negatively correlated"

    def test_generate_synthetic_weather_data_reproducibility(self):
        """Test that synthetic weather data generation is reproducible."""
        days = 10
        df1 = generate_synthetic_weather_data(days)
        df2 = generate_synthetic_weather_data(days)
        
        # Should be identical due to fixed random seed
        pd.testing.assert_frame_equal(df1, df2)


class TestNOAAIntegration:
    """Test NOAA API integration."""

    def test_fetch_noaa_weather_data_no_token(self):
        """Test NOAA data fetch without API token."""
        df = fetch_noaa_weather_data(days=1, api_token=None)
        
        # Should fallback to synthetic data
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(df["region"] == "NOAA")
        assert all(df["data_source"] == "noaa_synthetic_fallback")

    @patch('src.ingest.pull_weather.requests.get')
    def test_fetch_noaa_weather_data_success(self, mock_get):
        """Test successful NOAA data fetch."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"date": "2024-01-01", "datatype": "TMAX", "value": 250},
                {"date": "2024-01-01", "datatype": "TMIN", "value": 150},
                {"date": "2024-01-02", "datatype": "TMAX", "value": 280},
                {"date": "2024-01-02", "datatype": "TMIN", "value": 180},
            ]
        }
        mock_get.return_value = mock_response
        
        df = fetch_noaa_weather_data(days=2, api_token="test_token")
        
        # Check result
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2  # Two days of data
        assert "timestamp" in df.columns
        assert "temp_c" in df.columns
        assert all(df["region"] == "NOAA")
        assert all(df["data_source"] == "noaa_cdo_api")

    @patch('src.ingest.pull_weather.requests.get')
    def test_fetch_noaa_weather_data_api_failure(self, mock_get):
        """Test NOAA data fetch with API failure."""
        # Mock API failure
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        df = fetch_noaa_weather_data(days=1, api_token="test_token")
        
        # Should fallback to synthetic data
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(df["region"] == "NOAA")
        assert all(df["data_source"] == "noaa_synthetic_fallback")


class TestMeteostatIntegration:
    """Test Meteostat integration."""

    def test_fetch_meteostat_data_success(self):
        """Test successful Meteostat data fetch."""
        with patch('builtins.__import__') as mock_import:
            # Mock the meteostat module
            mock_meteostat = Mock()
            mock_point = Mock()
            mock_hourly = Mock()

            def import_side_effect(name, *args, **kwargs):
                if name == 'meteostat':
                    mock_meteostat.Point = Mock(return_value=mock_point)
                    mock_meteostat.Hourly = Mock(return_value=mock_hourly)
                    return mock_meteostat
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            # Mock data
            test_data = pd.DataFrame({
                'time': pd.date_range('2024-01-01', periods=24, freq='H'),
                'temp': [15.0] * 24,
                'rhum': [60.0] * 24,
                'wspd': [5.0] * 24
            })
            test_data.set_index('time', inplace=True)
            mock_hourly.fetch.return_value = test_data

            df = fetch_meteostat_data(days=1)

            # Check result
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 24  # 24 hours of data
            assert "timestamp" in df.columns
            assert "temp_c" in df.columns
            assert "humidity" in df.columns
            assert "wind_speed" in df.columns
            assert all(df["region"] == "METEOSTAT")
            assert all(df["data_source"] == "meteostat_api")

    def test_fetch_meteostat_data_import_error(self):
        """Test Meteostat data fetch when package is not installed."""
        df = fetch_meteostat_data(days=1)

        # Should fallback to synthetic data (since meteostat likely not installed in test env)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(df["region"] == "METEOSTAT")
        assert all(df["data_source"] == "meteostat_synthetic_fallback")


class TestFallbackFunction:
    """Test fallback to synthetic weather data."""

    def test_fallback_to_synthetic_weather(self):
        """Test fallback function creates properly labeled synthetic weather data."""
        region = "TEST_REGION"
        days = 5
        
        df = _fallback_to_synthetic_weather(region, days)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(df["region"] == region)
        assert all(df["data_source"] == "test_region_synthetic_fallback")
        
        # Should have all required columns
        expected_cols = {"timestamp", "temp_c", "humidity", "wind_speed", "region", "data_source"}
        assert set(df.columns) == expected_cols


class TestWeatherDataSaving:
    """Test weather data saving functionality."""

    def test_save_weather_data(self):
        """Test saving weather data to parquet file."""
        # Create test data
        df = generate_synthetic_weather_data(days=1)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_weather.parquet"
            
            # Save data
            result_path = save_weather_data(df, str(output_path))
            
            # Check file was created
            assert Path(result_path).exists()
            assert result_path == str(output_path)
            
            # Check file can be read back
            loaded_df = pd.read_parquet(output_path)
            pd.testing.assert_frame_equal(df, loaded_df)


class TestWeatherDataValidation:
    """Test weather data validation and quality checks."""

    def test_weather_data_quality(self):
        """Test that generated weather data meets quality requirements."""
        df = generate_synthetic_weather_data(days=30)
        
        # No missing values
        assert not df.isnull().any().any()
        
        # Timestamps are monotonic
        assert df["timestamp"].is_monotonic_increasing
        
        # Temperature values are reasonable
        assert df["temp_c"].min() > -50
        assert df["temp_c"].max() < 60
        
        # Humidity values are in valid range
        assert (df["humidity"] >= 10).all()
        assert (df["humidity"] <= 95).all()
        
        # Wind speed is non-negative
        assert (df["wind_speed"] >= 0).all()
        
        # Timestamps are hourly
        time_diffs = df["timestamp"].diff().dropna()
        expected_diff = pd.Timedelta(hours=1)
        assert (time_diffs == expected_diff).all()

    def test_weather_data_columns(self):
        """Test that weather data has required columns with correct types."""
        df = generate_synthetic_weather_data(days=1)
        
        # Required columns exist
        required_cols = ["timestamp", "temp_c", "humidity", "wind_speed", "region", "data_source"]
        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"
        
        # Correct data types
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
        assert pd.api.types.is_numeric_dtype(df["temp_c"])
        assert pd.api.types.is_numeric_dtype(df["humidity"])
        assert pd.api.types.is_numeric_dtype(df["wind_speed"])
        assert df["region"].dtype == "object"
        assert df["data_source"].dtype == "object"


if __name__ == "__main__":
    pytest.main([__file__])
