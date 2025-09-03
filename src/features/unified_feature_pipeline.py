#!/usr/bin/env python3
"""
Unified Feature Engineering Pipeline

This module creates a comprehensive feature engineering pipeline that combines:
- Historical weather data features
- Weather forecast features  
- Power data features
- Temporal features

The pipeline produces a unified dataset ready for ML model training and prediction,
implementing the enhanced feature set outlined in planning/weather_forecast_integration.md.

Author: ML Power Nowcast System
Created: 2025-08-29
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from dataclasses import dataclass

from .build_forecast_features import (
    ForecastFeatureConfig,
    build_all_forecast_features,
    get_forecast_feature_names
)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class UnifiedFeatureConfig:
    """
    Configuration for unified feature engineering pipeline.
    
    Attributes:
        forecast_config: Configuration for forecast features
        include_lag_features: Whether to include power load lag features
        lag_hours: List of lag hours for power features (e.g., [1, 24, 168])
        include_temporal_features: Whether to include time-based features
        include_weather_interactions: Whether to include weather interaction features
        target_zones: List of CAISO zones to process (None for all)
    """
    forecast_config: ForecastFeatureConfig
    include_lag_features: bool = True
    lag_hours: List[int] = None
    include_temporal_features: bool = True
    include_weather_interactions: bool = True
    target_zones: Optional[List[str]] = None
    
    def __post_init__(self):
        """Set default lag hours if not provided."""
        if self.lag_hours is None:
            self.lag_hours = [1, 24, 168]  # 1 hour, 1 day, 1 week


class UnifiedFeatureError(Exception):
    """Base exception for unified feature engineering operations."""
    pass


class DataMergeError(UnifiedFeatureError):
    """Raised when data merging fails."""
    pass


def load_power_data(data_path: Path, zones: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Load power demand data for feature engineering.
    
    Args:
        data_path: Path to power data file
        zones: List of zones to load (None for all California zones)
        
    Returns:
        DataFrame with power data
        
    Raises:
        UnifiedFeatureError: If data loading fails
    """
    try:
        logger.info(f"Loading power data from {data_path}")
        
        if not data_path.exists():
            raise UnifiedFeatureError(f"Power data file not found: {data_path}")
        
        # Load power data
        power_df = pd.read_parquet(data_path)
        
        # Filter to California zones only (exclude None zones)
        power_df = power_df[power_df['zone'].notna()].copy()
        
        # Filter to specific zones if requested
        if zones:
            power_df = power_df[power_df['zone'].isin(zones)].copy()
        
        # Ensure timestamp is datetime
        power_df['timestamp'] = pd.to_datetime(power_df['timestamp'])
        
        # Sort by zone and timestamp
        power_df = power_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
        
        logger.info(f"Loaded power data: {len(power_df):,} records, {len(power_df['zone'].unique())} zones")
        logger.info(f"Date range: {power_df['timestamp'].min()} to {power_df['timestamp'].max()}")
        
        return power_df
        
    except Exception as e:
        raise UnifiedFeatureError(f"Failed to load power data: {e}")


def load_historical_weather_data(data_path: Path, zones: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Load historical weather data for feature engineering.
    
    Args:
        data_path: Path to weather data file
        zones: List of zones to load (None for all)
        
    Returns:
        DataFrame with historical weather data
        
    Raises:
        UnifiedFeatureError: If data loading fails
    """
    try:
        logger.info(f"Loading historical weather data from {data_path}")
        
        if not data_path.exists():
            logger.warning(f"Historical weather data file not found: {data_path}")
            return pd.DataFrame()
        
        # Load weather data
        weather_df = pd.read_parquet(data_path)
        
        # Filter to specific zones if requested
        if zones:
            weather_df = weather_df[weather_df['zone'].isin(zones)].copy()
        
        # Ensure timestamp is datetime
        weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
        
        # Sort by zone and timestamp
        weather_df = weather_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
        
        logger.info(f"Loaded historical weather data: {len(weather_df):,} records, {len(weather_df['zone'].unique())} zones")
        
        return weather_df
        
    except Exception as e:
        raise UnifiedFeatureError(f"Failed to load historical weather data: {e}")


def load_forecast_weather_data(forecast_dir: Path, zones: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Load weather forecast data for feature engineering.
    
    Args:
        forecast_dir: Directory containing forecast data files
        zones: List of zones to load (None for all)
        
    Returns:
        DataFrame with forecast weather data
        
    Raises:
        UnifiedFeatureError: If data loading fails
    """
    try:
        logger.info(f"Loading forecast weather data from {forecast_dir}")
        
        if not forecast_dir.exists():
            logger.warning(f"Forecast data directory not found: {forecast_dir}")
            return pd.DataFrame()
        
        # Find forecast files
        forecast_files = []
        
        # Look for zone-specific forecast files
        target_zones = zones if zones else ['np15', 'sce', 'smud', 'pge_valley', 'sp15', 'sdge']
        
        for zone in target_zones:
            zone_dir = forecast_dir / "raw" / "weather_forecasts" / "nws" / zone.lower()
            if zone_dir.exists():
                latest_file = zone_dir / f"{zone.lower()}_forecast_latest.parquet"
                if latest_file.exists():
                    forecast_files.append(latest_file)
        
        if not forecast_files:
            logger.warning("No forecast data files found")
            return pd.DataFrame()
        
        # Load and combine forecast data
        forecast_dfs = []
        for file_path in forecast_files:
            try:
                df = pd.read_parquet(file_path)
                forecast_dfs.append(df)
                logger.debug(f"Loaded forecast file: {file_path} ({len(df)} records)")
            except Exception as e:
                logger.warning(f"Failed to load forecast file {file_path}: {e}")
        
        if not forecast_dfs:
            logger.warning("No forecast data could be loaded")
            return pd.DataFrame()
        
        # Combine all forecast data
        forecast_df = pd.concat(forecast_dfs, ignore_index=True)
        
        # Ensure timestamp is datetime
        forecast_df['timestamp'] = pd.to_datetime(forecast_df['timestamp'])
        
        # Sort by zone and timestamp
        forecast_df = forecast_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
        
        logger.info(f"Loaded forecast weather data: {len(forecast_df):,} records, {len(forecast_df['zone'].unique())} zones")
        
        return forecast_df
        
    except Exception as e:
        raise UnifiedFeatureError(f"Failed to load forecast weather data: {e}")


def create_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create temporal features from timestamp.
    
    Args:
        df: DataFrame with timestamp column
        
    Returns:
        DataFrame with temporal features added
    """
    logger.info("Creating temporal features")
    
    result_df = df.copy()
    
    # Ensure timestamp is datetime
    result_df['timestamp'] = pd.to_datetime(result_df['timestamp'])
    
    # Extract temporal components
    result_df['hour'] = result_df['timestamp'].dt.hour
    result_df['day_of_week'] = result_df['timestamp'].dt.dayofweek
    result_df['day_of_year'] = result_df['timestamp'].dt.dayofyear
    result_df['month'] = result_df['timestamp'].dt.month
    result_df['quarter'] = result_df['timestamp'].dt.quarter
    result_df['is_weekend'] = (result_df['day_of_week'] >= 5).astype(int)
    
    # Create cyclical features for better ML performance
    result_df['hour_sin'] = np.sin(2 * np.pi * result_df['hour'] / 24)
    result_df['hour_cos'] = np.cos(2 * np.pi * result_df['hour'] / 24)
    result_df['day_of_week_sin'] = np.sin(2 * np.pi * result_df['day_of_week'] / 7)
    result_df['day_of_week_cos'] = np.cos(2 * np.pi * result_df['day_of_week'] / 7)
    result_df['day_of_year_sin'] = np.sin(2 * np.pi * result_df['day_of_year'] / 365.25)
    result_df['day_of_year_cos'] = np.cos(2 * np.pi * result_df['day_of_year'] / 365.25)
    
    logger.info("Created temporal features")
    return result_df


def create_historical_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create features from historical weather data.
    
    Args:
        df: DataFrame with historical weather data
        
    Returns:
        DataFrame with weather features added
    """
    logger.info("Creating historical weather features")
    
    result_df = df.copy()
    
    # Temperature-based features
    if 'temp_c' in result_df.columns:
        result_df['temp_c_squared'] = result_df['temp_c'] ** 2
        result_df['cooling_degree_days'] = np.maximum(result_df['temp_c'] - 18, 0)
        result_df['heating_degree_days'] = np.maximum(18 - result_df['temp_c'], 0)
    
    # Humidity features
    if 'humidity' in result_df.columns:
        result_df['humidity_squared'] = result_df['humidity'] ** 2
    
    # Wind features
    if 'wind_speed_kmh' in result_df.columns:
        result_df['wind_speed_squared'] = result_df['wind_speed_kmh'] ** 2
    
    logger.info("Created historical weather features")
    return result_df


def create_power_lag_features(df: pd.DataFrame, lag_hours: List[int]) -> pd.DataFrame:
    """
    Create lag features from power load data.
    
    Args:
        df: DataFrame with power load data
        lag_hours: List of lag hours to create
        
    Returns:
        DataFrame with lag features added
    """
    logger.info(f"Creating power lag features for lags: {lag_hours}")
    
    if 'load' not in df.columns:
        logger.warning("No 'load' column found for lag features")
        return df
    
    result_df = df.copy()
    
    # Group by zone to create lag features
    zone_dfs = []
    
    for zone in result_df['zone'].unique():
        zone_df = result_df[result_df['zone'] == zone].copy()
        zone_df = zone_df.sort_values('timestamp')
        
        # Create lag features
        for lag in lag_hours:
            zone_df[f'load_lag_{lag}h'] = zone_df['load'].shift(lag)
        
        zone_dfs.append(zone_df)
    
    # Combine all zones
    result_df = pd.concat(zone_dfs, ignore_index=True)
    result_df = result_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
    
    logger.info(f"Created {len(lag_hours)} lag features")
    return result_df


def create_weather_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create interaction features between weather variables and temporal components.
    
    Enhanced to include time-of-day × weather interactions for better heat wave
    and peak demand modeling during extreme weather conditions.
    
    Args:
        df: DataFrame with weather and temporal features
        
    Returns:
        DataFrame with interaction features added
    """
    logger.info("Creating weather interaction features")
    
    result_df = df.copy()
    
    # Traditional weather-weather interactions (unchanged)
    if 'temp_c' in result_df.columns and 'humidity' in result_df.columns:
        result_df['temp_humidity_interaction'] = result_df['temp_c'] * result_df['humidity']
        result_df['heat_index_approx'] = result_df['temp_c'] + 0.5 * result_df['humidity']
    
    if 'temp_c' in result_df.columns and 'wind_speed_kmh' in result_df.columns:
        result_df['temp_wind_interaction'] = result_df['temp_c'] * result_df['wind_speed_kmh']
        # Simple wind chill approximation
        result_df['wind_chill_approx'] = result_df['temp_c'] - 0.1 * result_df['wind_speed_kmh']
    
    # NEW: Time-of-day × weather interactions for better temporal pattern modeling
    if 'temp_c' in result_df.columns and 'hour' in result_df.columns:
        # Afternoon heat intensity (stronger AC demand 2-6 PM during hot weather)
        afternoon_mask = (result_df['hour'] >= 14) & (result_df['hour'] <= 18)
        result_df['afternoon_heat_load'] = result_df['temp_c'] * afternoon_mask.astype(int)
        
        # Evening cooling effect (reduced AC demand after 7 PM even on hot days)  
        evening_mask = (result_df['hour'] >= 19) & (result_df['hour'] <= 23)
        result_df['evening_temp_relief'] = result_df['temp_c'] * evening_mask.astype(int)
        
        # Morning pre-heating (low AC demand before 10 AM regardless of temperature)
        morning_mask = result_df['hour'] <= 10
        result_df['morning_temp_baseline'] = result_df['temp_c'] * morning_mask.astype(int)
        
        # Peak heat stress indicator (extreme temps during peak hours 4-8 PM)
        peak_hours_mask = (result_df['hour'] >= 16) & (result_df['hour'] <= 20)
        temp_extreme_mask = result_df['temp_c'] >= 35  # 95°F threshold
        result_df['peak_heat_stress'] = (peak_hours_mask & temp_extreme_mask).astype(int)
    
    # NEW: Cyclical time × temperature interactions (captures heat wave progression)
    if 'temp_c' in result_df.columns and 'hour_sin' in result_df.columns and 'hour_cos' in result_df.columns:
        result_df['temp_hour_sin_interaction'] = result_df['temp_c'] * result_df['hour_sin']
        result_df['temp_hour_cos_interaction'] = result_df['temp_c'] * result_df['hour_cos']
    
    # NEW: Weekend × temperature interactions (different patterns on weekends)
    if 'temp_c' in result_df.columns and 'is_weekend' in result_df.columns:
        result_df['weekend_temp_load'] = result_df['temp_c'] * result_df['is_weekend']
    
    logger.info("Created enhanced weather and temporal interaction features")
    return result_df


def merge_datasets(
    power_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    config: UnifiedFeatureConfig
) -> pd.DataFrame:
    """
    Merge power, weather, and forecast datasets with proper alignment.
    
    Args:
        power_df: Power demand data
        weather_df: Historical weather data
        forecast_df: Weather forecast data
        config: Feature engineering configuration
        
    Returns:
        Merged DataFrame ready for feature engineering
        
    Raises:
        DataMergeError: If merging fails
    """
    logger.info("Merging power, weather, and forecast datasets")
    
    try:
        # Start with power data as the base
        merged_df = power_df.copy()
        
        # Merge historical weather data
        if len(weather_df) > 0:
            logger.info("Merging historical weather data")
            merged_df = pd.merge(
                merged_df,
                weather_df,
                on=['timestamp', 'zone'],
                how='left',
                suffixes=('', '_weather')
            )
            logger.info(f"After weather merge: {len(merged_df)} records")
        
        # Merge forecast weather data
        if len(forecast_df) > 0:
            logger.info("Merging forecast weather data")
            
            # Create forecast features first
            forecast_with_features = build_all_forecast_features(
                forecast_df, 
                config.forecast_config
            )
            
            # Select only forecast features for merging (avoid duplicating base weather)
            forecast_feature_cols = get_forecast_feature_names(config.forecast_config)
            forecast_merge_cols = ['timestamp', 'zone'] + [
                col for col in forecast_feature_cols if col in forecast_with_features.columns
            ]
            
            forecast_for_merge = forecast_with_features[forecast_merge_cols].copy()
            
            merged_df = pd.merge(
                merged_df,
                forecast_for_merge,
                on=['timestamp', 'zone'],
                how='left',
                suffixes=('', '_forecast')
            )
            logger.info(f"After forecast merge: {len(merged_df)} records")
        
        # Sort final result
        merged_df = merged_df.sort_values(['zone', 'timestamp']).reset_index(drop=True)
        
        logger.info(f"Dataset merge completed: {len(merged_df)} records, {len(merged_df.columns)} columns")
        return merged_df
        
    except Exception as e:
        raise DataMergeError(f"Failed to merge datasets: {e}")


def build_unified_features(
    power_data_path: Path,
    weather_data_path: Optional[Path] = None,
    forecast_data_dir: Optional[Path] = None,
    config: Optional[UnifiedFeatureConfig] = None
) -> pd.DataFrame:
    """
    Build unified feature dataset from all data sources.
    
    Args:
        power_data_path: Path to power demand data
        weather_data_path: Path to historical weather data (optional)
        forecast_data_dir: Directory with forecast data (optional)
        config: Feature engineering configuration
        
    Returns:
        DataFrame with unified features ready for ML training
        
    Raises:
        UnifiedFeatureError: If feature building fails
    """
    if config is None:
        config = UnifiedFeatureConfig(
            forecast_config=ForecastFeatureConfig(
                forecast_horizons=[1, 6, 12, 24]
            )
        )
    
    logger.info("Building unified feature dataset")
    logger.info(f"Power data: {power_data_path}")
    logger.info(f"Weather data: {weather_data_path}")
    logger.info(f"Forecast data: {forecast_data_dir}")
    
    try:
        # Load all datasets
        power_df = load_power_data(power_data_path, config.target_zones)
        
        weather_df = pd.DataFrame()
        if weather_data_path:
            weather_df = load_historical_weather_data(weather_data_path, config.target_zones)
        
        forecast_df = pd.DataFrame()
        if forecast_data_dir:
            forecast_df = load_forecast_weather_data(forecast_data_dir, config.target_zones)
        
        # Merge datasets
        merged_df = merge_datasets(power_df, weather_df, forecast_df, config)
        
        # Create temporal features
        if config.include_temporal_features:
            merged_df = create_temporal_features(merged_df)
        
        # Create historical weather features
        if len(weather_df) > 0:
            merged_df = create_historical_weather_features(merged_df)
        
        # Create power lag features
        if config.include_lag_features:
            merged_df = create_power_lag_features(merged_df, config.lag_hours)
        
        # Create weather interaction features
        if config.include_weather_interactions:
            merged_df = create_weather_interaction_features(merged_df)
        
        logger.info(f"Unified feature dataset completed: {len(merged_df)} records, {len(merged_df.columns)} features")
        
        return merged_df

    except Exception as e:
        raise UnifiedFeatureError(f"Failed to build unified features: {e}")


def get_unified_feature_names(config: Optional[UnifiedFeatureConfig] = None) -> List[str]:
    """
    Get list of all feature names that will be created by the unified pipeline.

    Args:
        config: Feature engineering configuration

    Returns:
        List of all feature column names
    """
    if config is None:
        config = UnifiedFeatureConfig(
            forecast_config=ForecastFeatureConfig(forecast_horizons=[1, 6, 12, 24])
        )

    features = []

    # Base features
    features.extend(['timestamp', 'zone', 'load'])

    # Historical weather features
    features.extend([
        'temp_c', 'humidity', 'wind_speed_kmh',
        'temp_c_squared', 'cooling_degree_days', 'heating_degree_days',
        'humidity_squared', 'wind_speed_squared'
    ])

    # Forecast features
    features.extend(get_forecast_feature_names(config.forecast_config))

    # Temporal features
    if config.include_temporal_features:
        features.extend([
            'hour', 'day_of_week', 'day_of_year', 'month', 'quarter', 'is_weekend',
            'hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos',
            'day_of_year_sin', 'day_of_year_cos'
        ])

    # Lag features
    if config.include_lag_features:
        for lag in config.lag_hours:
            features.append(f'load_lag_{lag}h')

    # Interaction features
    if config.include_weather_interactions:
        features.extend([
            # Traditional weather-weather interactions
            'temp_humidity_interaction', 'heat_index_approx',
            'temp_wind_interaction', 'wind_chill_approx',
            # NEW: Time-of-day × weather interactions  
            'afternoon_heat_load', 'evening_temp_relief', 'morning_temp_baseline',
            'peak_heat_stress', 'temp_hour_sin_interaction', 'temp_hour_cos_interaction',
            'weekend_temp_load'
        ])

    return features
