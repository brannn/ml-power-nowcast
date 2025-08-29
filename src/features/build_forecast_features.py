#!/usr/bin/env python3
"""
Weather Forecast Feature Engineering Module

This module creates weather forecast features for ML power demand prediction models.
It implements the feature engineering plan outlined in planning/weather_forecast_integration.md,
focusing on creating predictive features from weather forecast data.

The module provides functions to create:
- Core forecast features (temperature, humidity, wind at different horizons)
- Advanced features (weather change rates, volatility, extreme events)
- Weather event detection (heat waves, cold snaps, rapid changes)

Author: ML Power Nowcast System
Created: 2025-08-29
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ForecastFeatureConfig:
    """
    Configuration for forecast feature engineering.
    
    Attributes:
        forecast_horizons: List of forecast horizons in hours (e.g., [1, 6, 12, 24])
        base_temperature: Base temperature for degree day calculations (Celsius)
        extreme_temp_thresholds: Dict with 'hot' and 'cold' temperature thresholds
        rapid_change_threshold: Temperature change threshold for rapid change detection
        volatility_window: Rolling window size for volatility calculations
    """
    forecast_horizons: List[int]
    base_temperature: float = 18.0  # Base temperature for degree days (65°F = 18.3°C)
    extreme_temp_thresholds: Dict[str, float] = None
    rapid_change_threshold: float = 10.0  # °C change in 6 hours
    volatility_window: int = 6  # Hours for rolling volatility
    
    def __post_init__(self):
        """Set default extreme temperature thresholds if not provided."""
        if self.extreme_temp_thresholds is None:
            self.extreme_temp_thresholds = {
                'hot': 35.0,   # Heat wave threshold (95°F)
                'cold': 5.0    # Cold snap threshold (41°F)
            }


class ForecastFeatureError(Exception):
    """Base exception for forecast feature engineering operations."""
    pass


class DataValidationError(ForecastFeatureError):
    """Raised when input data fails validation."""
    pass


def validate_forecast_data(forecast_df: pd.DataFrame) -> None:
    """
    Validate forecast DataFrame for feature engineering.
    
    Args:
        forecast_df: DataFrame with forecast data
        
    Raises:
        DataValidationError: If validation fails
    """
    required_columns = ['timestamp', 'zone', 'temp_c', 'forecast_horizon_hours']
    missing_columns = [col for col in required_columns if col not in forecast_df.columns]
    
    if missing_columns:
        raise DataValidationError(f"Missing required columns: {missing_columns}")
    
    if len(forecast_df) == 0:
        raise DataValidationError("Forecast DataFrame is empty")
    
    # Check for null values in critical columns
    critical_nulls = forecast_df[['timestamp', 'zone', 'temp_c']].isnull().sum()
    if critical_nulls.sum() > 0:
        raise DataValidationError(f"Null values in critical columns: {critical_nulls.to_dict()}")
    
    # Validate temperature range (reasonable for California)
    temp_out_of_range = forecast_df[
        (forecast_df['temp_c'] < -20) | (forecast_df['temp_c'] > 60)
    ]
    if len(temp_out_of_range) > 0:
        logger.warning(f"Found {len(temp_out_of_range)} temperature values out of range")


def create_core_forecast_features(
    forecast_df: pd.DataFrame,
    config: ForecastFeatureConfig
) -> pd.DataFrame:
    """
    Create core forecast features at different time horizons.
    
    Args:
        forecast_df: DataFrame with forecast data
        config: Feature engineering configuration
        
    Returns:
        DataFrame with core forecast features added
        
    Raises:
        DataValidationError: If input data is invalid
    """
    logger.info("Creating core forecast features")
    validate_forecast_data(forecast_df)
    
    # Work with a copy to avoid modifying original data
    df = forecast_df.copy()
    
    # Ensure timestamp is datetime and sorted
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
    
    # Group by zone for feature creation
    feature_dfs = []
    
    for zone in df['zone'].unique():
        zone_df = df[df['zone'] == zone].copy()
        
        logger.debug(f"Processing zone {zone}: {len(zone_df)} records")
        
        # Create forecast features for each horizon
        for horizon in config.forecast_horizons:
            # Temperature forecasts
            zone_df[f'temp_forecast_{horizon}h'] = zone_df['temp_c'].shift(-horizon)
            
            # Humidity forecasts (if available)
            if 'humidity' in zone_df.columns and zone_df['humidity'].notna().any():
                zone_df[f'humidity_forecast_{horizon}h'] = zone_df['humidity'].shift(-horizon)
            
            # Wind speed forecasts (if available)
            if 'wind_speed_kmh' in zone_df.columns and zone_df['wind_speed_kmh'].notna().any():
                zone_df[f'wind_forecast_{horizon}h'] = zone_df['wind_speed_kmh'].shift(-horizon)
            
            # Cooling degree day forecasts
            zone_df[f'cooling_forecast_{horizon}h'] = np.maximum(
                zone_df[f'temp_forecast_{horizon}h'] - config.base_temperature, 0
            )
            
            # Heating degree day forecasts
            zone_df[f'heating_forecast_{horizon}h'] = np.maximum(
                config.base_temperature - zone_df[f'temp_forecast_{horizon}h'], 0
            )
        
        feature_dfs.append(zone_df)
    
    # Combine all zones
    result_df = pd.concat(feature_dfs, ignore_index=True)
    result_df = result_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
    
    logger.info(f"Created core forecast features for {len(config.forecast_horizons)} horizons")
    return result_df


def create_weather_change_features(
    df: pd.DataFrame,
    config: ForecastFeatureConfig
) -> pd.DataFrame:
    """
    Create weather change rate and volatility features.
    
    Args:
        df: DataFrame with core forecast features
        config: Feature engineering configuration
        
    Returns:
        DataFrame with weather change features added
    """
    logger.info("Creating weather change features")
    
    # Work with a copy
    result_df = df.copy()
    
    # Group by zone for feature creation
    feature_dfs = []
    
    for zone in result_df['zone'].unique():
        zone_df = result_df[result_df['zone'] == zone].copy()
        
        # Temperature change rates
        for horizon in [6, 12, 24]:  # Focus on key horizons for change rates
            if f'temp_forecast_{horizon}h' in zone_df.columns:
                zone_df[f'temp_change_rate_{horizon}h'] = (
                    zone_df[f'temp_forecast_{horizon}h'] - zone_df['temp_c']
                ) / horizon
        
        # Humidity change rates (if available)
        if 'humidity' in zone_df.columns:
            for horizon in [6, 12]:
                if f'humidity_forecast_{horizon}h' in zone_df.columns:
                    zone_df[f'humidity_change_rate_{horizon}h'] = (
                        zone_df[f'humidity_forecast_{horizon}h'] - zone_df['humidity']
                    ) / horizon
        
        # Weather volatility (rolling standard deviation of temperature forecasts)
        if f'temp_forecast_{config.volatility_window}h' in zone_df.columns:
            zone_df['weather_volatility_6h'] = (
                zone_df[f'temp_forecast_{config.volatility_window}h']
                .rolling(window=config.volatility_window, min_periods=3)
                .std()
            )
        
        # Temperature trend stability (how much forecast changes over time)
        if 'temp_forecast_24h' in zone_df.columns:
            zone_df['temp_forecast_stability'] = (
                zone_df['temp_forecast_24h']
                .rolling(window=6, min_periods=3)
                .std()
            )
        
        feature_dfs.append(zone_df)
    
    # Combine all zones
    result_df = pd.concat(feature_dfs, ignore_index=True)
    result_df = result_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
    
    logger.info("Created weather change features")
    return result_df


def create_extreme_weather_features(
    df: pd.DataFrame,
    config: ForecastFeatureConfig
) -> pd.DataFrame:
    """
    Create extreme weather event detection features.
    
    Args:
        df: DataFrame with forecast features
        config: Feature engineering configuration
        
    Returns:
        DataFrame with extreme weather features added
    """
    logger.info("Creating extreme weather features")
    
    # Work with a copy
    result_df = df.copy()
    
    # Group by zone for feature creation
    feature_dfs = []
    
    for zone in result_df['zone'].unique():
        zone_df = result_df[result_df['zone'] == zone].copy()
        
        # Heat wave detection (3+ consecutive days above threshold)
        if all(f'temp_forecast_{h}h' in zone_df.columns for h in [24, 48, 72]):
            zone_df['heat_wave_incoming'] = (
                (zone_df['temp_forecast_24h'] > config.extreme_temp_thresholds['hot']) &
                (zone_df['temp_forecast_48h'] > config.extreme_temp_thresholds['hot']) &
                (zone_df['temp_forecast_72h'] > config.extreme_temp_thresholds['hot'])
            ).astype(int)
        
        # Cold snap detection (3+ consecutive days below threshold)
        if all(f'temp_forecast_{h}h' in zone_df.columns for h in [24, 48, 72]):
            zone_df['cold_snap_incoming'] = (
                (zone_df['temp_forecast_24h'] < config.extreme_temp_thresholds['cold']) &
                (zone_df['temp_forecast_48h'] < config.extreme_temp_thresholds['cold']) &
                (zone_df['temp_forecast_72h'] < config.extreme_temp_thresholds['cold'])
            ).astype(int)
        
        # Rapid temperature change detection
        if 'temp_change_rate_6h' in zone_df.columns:
            zone_df['rapid_temp_change'] = (
                np.abs(zone_df['temp_change_rate_6h'] * 6) > config.rapid_change_threshold
            ).astype(int)
        
        # Extreme temperature probability (based on forecast vs historical patterns)
        if 'temp_forecast_24h' in zone_df.columns:
            # Simple approach: flag temperatures in extreme percentiles
            temp_p95 = zone_df['temp_c'].quantile(0.95)
            temp_p05 = zone_df['temp_c'].quantile(0.05)
            
            zone_df['extreme_temp_probability'] = (
                (zone_df['temp_forecast_24h'] > temp_p95) |
                (zone_df['temp_forecast_24h'] < temp_p05)
            ).astype(int)
        
        feature_dfs.append(zone_df)
    
    # Combine all zones
    result_df = pd.concat(feature_dfs, ignore_index=True)
    result_df = result_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
    
    logger.info("Created extreme weather features")
    return result_df


def create_forecast_uncertainty_features(
    df: pd.DataFrame,
    config: ForecastFeatureConfig
) -> pd.DataFrame:
    """
    Create forecast uncertainty and confidence features.
    
    Args:
        df: DataFrame with forecast features
        config: Feature engineering configuration
        
    Returns:
        DataFrame with uncertainty features added
    """
    logger.info("Creating forecast uncertainty features")
    
    # Work with a copy
    result_df = df.copy()
    
    # Group by zone for feature creation
    feature_dfs = []
    
    for zone in result_df['zone'].unique():
        zone_df = result_df[result_df['zone'] == zone].copy()
        
        # Forecast horizon uncertainty (longer horizons are less certain)
        if 'forecast_horizon_hours' in zone_df.columns:
            zone_df['forecast_uncertainty_score'] = np.minimum(
                zone_df['forecast_horizon_hours'] / 48.0,  # Normalize to 48-hour max
                1.0
            )
        
        # Weather pattern stability (how consistent forecasts are)
        if 'weather_volatility_6h' in zone_df.columns:
            zone_df['weather_pattern_stability'] = 1.0 / (1.0 + zone_df['weather_volatility_6h'])
        
        # Forecast confidence based on temperature gradient
        if 'temp_forecast_stability' in zone_df.columns:
            zone_df['forecast_confidence'] = 1.0 / (1.0 + zone_df['temp_forecast_stability'])
        
        feature_dfs.append(zone_df)
    
    # Combine all zones
    result_df = pd.concat(feature_dfs, ignore_index=True)
    result_df = result_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
    
    logger.info("Created forecast uncertainty features")
    return result_df


def build_all_forecast_features(
    forecast_df: pd.DataFrame,
    config: Optional[ForecastFeatureConfig] = None
) -> pd.DataFrame:
    """
    Build comprehensive forecast features from weather forecast data.
    
    Args:
        forecast_df: DataFrame with raw forecast data
        config: Feature engineering configuration (uses defaults if None)
        
    Returns:
        DataFrame with all forecast features
        
    Raises:
        DataValidationError: If input data is invalid
        ForecastFeatureError: If feature creation fails
    """
    if config is None:
        config = ForecastFeatureConfig(
            forecast_horizons=[1, 6, 12, 24, 48]
        )
    
    logger.info("Building comprehensive forecast features")
    logger.info(f"Input data: {len(forecast_df)} records, {len(forecast_df['zone'].unique())} zones")
    
    try:
        # Step 1: Create core forecast features
        df_with_core = create_core_forecast_features(forecast_df, config)
        
        # Step 2: Create weather change features
        df_with_changes = create_weather_change_features(df_with_core, config)
        
        # Step 3: Create extreme weather features
        df_with_extremes = create_extreme_weather_features(df_with_changes, config)
        
        # Step 4: Create uncertainty features
        df_final = create_forecast_uncertainty_features(df_with_extremes, config)
        
        # Log feature summary
        new_columns = [col for col in df_final.columns if col not in forecast_df.columns]
        logger.info(f"Created {len(new_columns)} forecast features")
        logger.debug(f"New features: {new_columns}")
        
        return df_final
        
    except Exception as e:
        raise ForecastFeatureError(f"Failed to build forecast features: {e}")


def get_forecast_feature_names(config: Optional[ForecastFeatureConfig] = None) -> List[str]:
    """
    Get list of forecast feature names that will be created.
    
    Args:
        config: Feature engineering configuration
        
    Returns:
        List of forecast feature column names
    """
    if config is None:
        config = ForecastFeatureConfig(forecast_horizons=[1, 6, 12, 24, 48])
    
    features = []
    
    # Core forecast features
    for horizon in config.forecast_horizons:
        features.extend([
            f'temp_forecast_{horizon}h',
            f'cooling_forecast_{horizon}h',
            f'heating_forecast_{horizon}h'
        ])
        
        # Optional features (may not always be available)
        features.extend([
            f'humidity_forecast_{horizon}h',
            f'wind_forecast_{horizon}h'
        ])
    
    # Weather change features
    for horizon in [6, 12, 24]:
        features.extend([
            f'temp_change_rate_{horizon}h',
            f'humidity_change_rate_{horizon}h'
        ])
    
    # Advanced features
    features.extend([
        'weather_volatility_6h',
        'temp_forecast_stability',
        'heat_wave_incoming',
        'cold_snap_incoming',
        'rapid_temp_change',
        'extreme_temp_probability',
        'forecast_uncertainty_score',
        'weather_pattern_stability',
        'forecast_confidence'
    ])
    
    return features
