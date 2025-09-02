#!/usr/bin/env python3
"""
Tests for feature engineering module.

Tests cover lag features, rolling statistics, temporal features,
weather interactions, and the complete feature building pipeline.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
import pytest
import pandas as pd
import numpy as np

from src.features.build_features import (
    create_lag_features,
    create_rolling_features,
    create_temporal_features,
    create_weather_features,
    create_target_features,
    remove_incomplete_rows,
    build_features
)


class TestLagFeatures:
    """Test lag feature creation."""

    def test_create_lag_features_basic(self) -> None:
        """Test basic lag feature creation."""
        # Create test data
        dates = pd.date_range('2024-01-01', periods=48, freq='h')
        df = pd.DataFrame({
            'timestamp': dates,
            'load': np.arange(48) + 1000  # Simple increasing pattern
        })
        
        lags = [1, 2, 6]
        result_df = create_lag_features(df, target_col='load', lags=lags)
        
        # Check new columns were created
        expected_cols = ['load_lag_1h', 'load_lag_2h', 'load_lag_6h']
        for col in expected_cols:
            assert col in result_df.columns
        
        # Check lag values are correct
        assert result_df.loc[1, 'load_lag_1h'] == 1000  # First value shifted by 1
        assert result_df.loc[2, 'load_lag_2h'] == 1000  # First value shifted by 2
        assert result_df.loc[6, 'load_lag_6h'] == 1000  # First value shifted by 6
        
        # Check NaN values at beginning
        assert pd.isna(result_df.loc[0, 'load_lag_1h'])
        assert pd.isna(result_df.loc[1, 'load_lag_2h'])

    def test_create_lag_features_custom_column(self) -> None:
        """Test lag features with custom target column."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=24, freq='h'),
            'temperature': np.random.normal(20, 5, 24)
        })
        
        result_df = create_lag_features(df, target_col='temperature', lags=[1, 3])
        
        assert 'temperature_lag_1h' in result_df.columns
        assert 'temperature_lag_3h' in result_df.columns
        assert result_df.loc[1, 'temperature_lag_1h'] == df.loc[0, 'temperature']


class TestRollingFeatures:
    """Test rolling window feature creation."""

    def test_create_rolling_features_basic(self) -> None:
        """Test basic rolling feature creation."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=24, freq='h'),
            'load': np.ones(24) * 1000  # Constant values for easy testing
        })
        
        windows = [3, 6]
        stats = ['mean', 'std']
        result_df = create_rolling_features(df, target_col='load', windows=windows, stats=stats)
        
        # Check new columns
        expected_cols = ['load_rolling_3h_mean', 'load_rolling_3h_std', 
                        'load_rolling_6h_mean', 'load_rolling_6h_std']
        for col in expected_cols:
            assert col in result_df.columns
        
        # Check rolling mean values (should be 1000 for constant input)
        assert result_df.loc[5, 'load_rolling_3h_mean'] == 1000
        assert result_df.loc[10, 'load_rolling_6h_mean'] == 1000
        
        # Check rolling std values (should be 0 for constant input)
        assert result_df.loc[5, 'load_rolling_3h_std'] == 0

    def test_create_rolling_features_varying_data(self) -> None:
        """Test rolling features with varying data."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='h'),
            'load': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        })
        
        result_df = create_rolling_features(df, target_col='load', windows=[3], stats=['mean', 'min', 'max'])
        
        # Check rolling mean at index 4 (should be mean of 1200, 1300, 1400)
        expected_mean = (1200 + 1300 + 1400) / 3
        assert result_df.loc[4, 'load_rolling_3h_mean'] == expected_mean
        
        # Check rolling min and max
        assert result_df.loc[4, 'load_rolling_3h_min'] == 1200
        assert result_df.loc[4, 'load_rolling_3h_max'] == 1400


class TestTemporalFeatures:
    """Test temporal feature creation."""

    def test_create_temporal_features_basic(self) -> None:
        """Test basic temporal feature creation."""
        # Create test data spanning different times
        dates = pd.date_range('2024-01-01 00:00:00', periods=48, freq='h')
        df = pd.DataFrame({'timestamp': dates})
        
        result_df = create_temporal_features(df)
        
        # Check all expected columns exist
        expected_cols = ['hour', 'day_of_week', 'month', 'day_of_year', 
                        'is_weekend', 'is_business_hours',
                        'hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos',
                        'day_of_year_sin', 'day_of_year_cos']
        for col in expected_cols:
            assert col in result_df.columns
        
        # Check specific values
        assert result_df.loc[0, 'hour'] == 0  # First timestamp is midnight
        assert result_df.loc[12, 'hour'] == 12  # 12 hours later is noon
        assert result_df.loc[0, 'month'] == 1  # January
        assert result_df.loc[0, 'day_of_week'] == 0  # Monday (2024-01-01 was Monday)

    def test_create_temporal_features_weekend_detection(self) -> None:
        """Test weekend detection in temporal features."""
        # Create data for a full week starting Monday
        dates = pd.date_range('2024-01-01', periods=7, freq='D')  # Monday to Sunday
        df = pd.DataFrame({'timestamp': dates})
        
        result_df = create_temporal_features(df)
        
        # Monday-Friday should not be weekend
        for i in range(5):
            assert result_df.loc[i, 'is_weekend'] == 0
        
        # Saturday-Sunday should be weekend
        assert result_df.loc[5, 'is_weekend'] == 1  # Saturday
        assert result_df.loc[6, 'is_weekend'] == 1  # Sunday

    def test_create_temporal_features_business_hours(self) -> None:
        """Test business hours detection."""
        # Create hourly data for one day
        dates = pd.date_range('2024-01-01 00:00:00', periods=24, freq='h')  # Monday
        df = pd.DataFrame({'timestamp': dates})
        
        result_df = create_temporal_features(df)
        
        # Check business hours (6 AM - 6 PM on weekdays)
        assert result_df.loc[5, 'is_business_hours'] == 0  # 5 AM - not business hours
        assert result_df.loc[6, 'is_business_hours'] == 1  # 6 AM - business hours
        assert result_df.loc[18, 'is_business_hours'] == 1  # 6 PM - business hours
        assert result_df.loc[19, 'is_business_hours'] == 0  # 7 PM - not business hours

    def test_create_temporal_features_cyclic_encoding(self) -> None:
        """Test cyclic encoding of temporal features."""
        dates = pd.date_range('2024-01-01 00:00:00', periods=24, freq='h')
        df = pd.DataFrame({'timestamp': dates})
        
        result_df = create_temporal_features(df)
        
        # Check that sin/cos values are in valid range
        assert (result_df['hour_sin'] >= -1).all() and (result_df['hour_sin'] <= 1).all()
        assert (result_df['hour_cos'] >= -1).all() and (result_df['hour_cos'] <= 1).all()
        
        # Check that midnight (hour 0) and 6am (hour 6) have different values
        midnight_sin = result_df.loc[0, 'hour_sin']
        morning_sin = result_df.loc[6, 'hour_sin']
        assert abs(midnight_sin - morning_sin) > 0.5  # Should be significantly different


class TestWeatherFeatures:
    """Test weather feature creation."""

    def test_create_weather_features_basic(self) -> None:
        """Test basic weather feature creation."""
        df = pd.DataFrame({
            'temp_c': [10, 15, 20, 25, 30],
            'humidity': [60, 65, 70, 75, 80],
            'wind_speed': [5, 10, 15, 20, 25]
        })
        
        result_df = create_weather_features(df)
        
        # Check temperature-based features
        assert 'temp_c_squared' in result_df.columns
        assert 'cooling_degree_days' in result_df.columns
        assert 'heating_degree_days' in result_df.columns
        
        # Check interaction features
        assert 'temp_humidity_interaction' in result_df.columns
        assert 'wind_chill_effect' in result_df.columns
        
        # Check specific calculations
        assert result_df.loc[0, 'temp_c_squared'] == 100  # 10^2
        assert result_df.loc[4, 'cooling_degree_days'] == 12  # max(30-18, 0)
        assert result_df.loc[0, 'heating_degree_days'] == 8  # max(18-10, 0)

    def test_create_weather_features_missing_columns(self) -> None:
        """Test weather features with missing columns."""
        df = pd.DataFrame({'other_col': [1, 2, 3]})
        
        result_df = create_weather_features(df)
        
        # Should not crash and should return original DataFrame
        assert len(result_df.columns) == len(df.columns)
        assert 'other_col' in result_df.columns


class TestTargetFeatures:
    """Test target variable creation."""

    def test_create_target_features_basic(self) -> None:
        """Test basic target feature creation."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='h'),
            'load': np.arange(10) + 1000
        })
        
        horizon = 3
        result_df, target_col = create_target_features(df, target_col='load', horizon=horizon)
        
        # Check target column name
        assert target_col == 'load_target_3h'
        assert target_col in result_df.columns
        
        # Check target values (should be shifted backwards)
        assert result_df.loc[0, target_col] == 1003  # load[3]
        assert result_df.loc[1, target_col] == 1004  # load[4]
        
        # Check NaN values at end
        assert pd.isna(result_df.loc[7, target_col])  # Should be NaN
        assert pd.isna(result_df.loc[8, target_col])  # Should be NaN
        assert pd.isna(result_df.loc[9, target_col])  # Should be NaN


class TestDataCleaning:
    """Test data cleaning functions."""

    def test_remove_incomplete_rows_basic(self) -> None:
        """Test removing incomplete rows."""
        df = pd.DataFrame({
            'a': [1, 2, np.nan, 4],
            'b': [1, np.nan, 3, 4],
            'c': [1, 2, 3, 4]
        })
        
        result_df = remove_incomplete_rows(df)
        
        # Should keep rows with all values present (rows 0 and 3)
        assert len(result_df) == 2
        assert 0 in result_df.index
        assert 3 in result_df.index

    def test_remove_incomplete_rows_specific_columns(self) -> None:
        """Test removing incomplete rows for specific columns."""
        df = pd.DataFrame({
            'a': [1, 2, np.nan, 4],
            'b': [1, np.nan, 3, 4],
            'c': [1, 2, 3, 4]
        })
        
        result_df = remove_incomplete_rows(df, required_cols=['a', 'c'])
        
        # Should keep rows 0, 1, 3 (column 'b' not required)
        assert len(result_df) == 3
        assert list(result_df.index) == [0, 1, 3]


class TestIntegration:
    """Test complete feature building pipeline."""

    def test_build_features_integration(self) -> None:
        """Test complete feature building pipeline with sample data."""
        # Create sample power data
        dates = pd.date_range('2024-01-01', periods=72, freq='h')  # 3 days
        power_df = pd.DataFrame({
            'timestamp': dates,
            'load': 1000 + 200 * np.sin(2 * np.pi * np.arange(72) / 24) + np.random.normal(0, 50, 72),
            'region': 'TEST',
            'data_source': 'synthetic'
        })
        
        # Create sample weather data
        weather_df = pd.DataFrame({
            'timestamp': dates,
            'temp_c': 15 + 10 * np.sin(2 * np.pi * np.arange(72) / 24) + np.random.normal(0, 2, 72),
            'humidity': 60 + 20 * np.sin(2 * np.pi * np.arange(72) / 48) + np.random.normal(0, 5, 72),
            'wind_speed': 5 + 3 * np.random.random(72),
            'region': 'TEST',
            'data_source': 'synthetic'
        })
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save sample data
            power_path = Path(temp_dir) / "power.parquet"
            weather_path = Path(temp_dir) / "weather.parquet"
            features_path = Path(temp_dir) / "features.parquet"
            
            power_df.to_parquet(power_path, index=False)
            weather_df.to_parquet(weather_path, index=False)
            
            # Build features
            result_df, target_col = build_features(
                power_data_path=str(power_path),
                weather_data_path=str(weather_path),
                horizon=1,
                lags=[1, 2, 6],
                rolling_windows=[3, 6],
                output_path=str(features_path)
            )
            
            # Check results
            assert isinstance(result_df, pd.DataFrame)
            assert len(result_df) > 0
            assert target_col == 'load_target_1h'
            assert target_col in result_df.columns
            
            # Check that features file was created
            assert features_path.exists()
            
            # Check feature types are present
            feature_cols = [col for col in result_df.columns if col not in ['timestamp', target_col]]
            
            # Should have lag features
            lag_features = [col for col in feature_cols if 'lag' in col]
            assert len(lag_features) > 0
            
            # Should have rolling features
            rolling_features = [col for col in feature_cols if 'rolling' in col]
            assert len(rolling_features) > 0
            
            # Should have temporal features
            temporal_features = [col for col in feature_cols if any(x in col for x in ['hour', 'day', 'month'])]
            assert len(temporal_features) > 0
            
            # Should have weather features
            weather_features = [col for col in feature_cols if any(x in col for x in ['temp', 'humidity', 'wind'])]
            assert len(weather_features) > 0
            
            print(f"✅ Integration test passed: {len(feature_cols)} features created from {len(result_df)} samples")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
