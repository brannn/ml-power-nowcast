#!/usr/bin/env python3
"""
Safe Weather Forecast Feature Engineering

This module creates weather forecast features without data leakage, using:
1. Historical forecast accuracy modeling
2. Forecast uncertainty bounds
3. Conservative feature scaling

Author: ML Power Nowcast System
Created: 2025-09-02
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SafeForecastConfig:
    """Configuration for safe forecast feature engineering."""
    forecast_horizons: List[int] = None
    uncertainty_buffer: float = 0.15  # 15% uncertainty buffer
    max_forecast_weight: float = 0.3  # Limit forecast influence
    use_ensemble_average: bool = True
    validate_forecast_bounds: bool = True
    
    def __post_init__(self):
        if self.forecast_horizons is None:
            self.forecast_horizons = [1, 6, 12, 24]


def create_safe_forecast_features(
    historical_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    config: SafeForecastConfig
) -> pd.DataFrame:
    """
    Create forecast features with safety constraints.
    
    Args:
        historical_df: Historical weather/power data
        forecast_df: Weather forecast data from API
        config: Safety configuration
        
    Returns:
        DataFrame with safe forecast features
    """
    logger.info("Creating safe forecast features")
    
    # 1. Calculate historical forecast accuracy
    forecast_errors = calculate_historical_forecast_errors(historical_df, forecast_df)
    
    # 2. Apply uncertainty bounds to forecasts
    bounded_forecasts = apply_uncertainty_bounds(forecast_df, forecast_errors, config)
    
    # 3. Create weighted features (limit forecast influence)
    weighted_features = create_weighted_forecast_features(
        historical_df, bounded_forecasts, config
    )
    
    # 4. Add forecast confidence metrics
    confidence_features = create_forecast_confidence_features(
        forecast_df, forecast_errors, config
    )
    
    # Merge all features
    result_df = historical_df.copy()
    result_df = result_df.merge(weighted_features, on=['timestamp', 'zone'], how='left')
    result_df = result_df.merge(confidence_features, on=['timestamp', 'zone'], how='left')
    
    return result_df


def calculate_historical_forecast_errors(
    historical_df: pd.DataFrame,
    forecast_df: pd.DataFrame
) -> Dict[str, Dict[int, float]]:
    """Calculate MAPE for different zones and forecast horizons."""
    errors = {}
    
    for zone in historical_df['zone'].unique():
        zone_hist = historical_df[historical_df['zone'] == zone]
        zone_forecast = forecast_df[forecast_df['zone'] == zone]
        
        errors[zone] = {}
        
        for horizon in [1, 6, 12, 24]:
            # Calculate MAPE between historical actuals and forecasts
            merged = pd.merge_asof(
                zone_hist.sort_values('timestamp'),
                zone_forecast[zone_forecast['forecast_horizon_hours'] == horizon]
                .sort_values('timestamp'),
                on='timestamp',
                direction='backward',
                tolerance=pd.Timedelta(hours=1)
            )
            
            if len(merged.dropna()) > 10:
                actual = merged['temp_c_x']  # Historical actual
                forecast = merged['temp_c_y']  # Forecast value
                mape = np.mean(np.abs((actual - forecast) / actual)) * 100
                errors[zone][horizon] = min(mape, 50.0)  # Cap at 50% error
            else:
                errors[zone][horizon] = 20.0  # Default conservative error
    
    return errors


def apply_uncertainty_bounds(
    forecast_df: pd.DataFrame,
    forecast_errors: Dict[str, Dict[int, float]],
    config: SafeForecastConfig
) -> pd.DataFrame:
    """Apply uncertainty bounds to forecast values."""
    bounded_df = forecast_df.copy()
    
    for zone in forecast_df['zone'].unique():
        zone_mask = bounded_df['zone'] == zone
        
        for horizon in config.forecast_horizons:
            horizon_mask = bounded_df['forecast_horizon_hours'] == horizon
            mask = zone_mask & horizon_mask
            
            if mask.any():
                # Get forecast error for this zone/horizon
                error_rate = forecast_errors.get(zone, {}).get(horizon, 20.0) / 100
                
                # Apply conservative bounds
                forecast_values = bounded_df.loc[mask, 'temp_c']
                uncertainty = forecast_values * error_rate * config.uncertainty_buffer
                
                # Create bounded versions
                bounded_df.loc[mask, f'temp_forecast_{horizon}h_lower'] = (
                    forecast_values - uncertainty
                )
                bounded_df.loc[mask, f'temp_forecast_{horizon}h_upper'] = (
                    forecast_values + uncertainty
                )
                bounded_df.loc[mask, f'temp_forecast_{horizon}h'] = forecast_values
    
    return bounded_df


def create_weighted_forecast_features(
    historical_df: pd.DataFrame,
    bounded_forecasts: pd.DataFrame,
    config: SafeForecastConfig
) -> pd.DataFrame:
    """Create weighted features that limit forecast influence."""
    feature_df = historical_df[['timestamp', 'zone']].copy()
    
    for zone in historical_df['zone'].unique():
        zone_hist = historical_df[historical_df['zone'] == zone]
        zone_forecast = bounded_forecasts[bounded_forecasts['zone'] == zone]
        
        # Get recent historical average for baseline
        recent_temp = zone_hist.groupby('timestamp')['temp_c'].mean().rolling(
            window=24, min_periods=12
        ).mean()
        
        for horizon in config.forecast_horizons:
            horizon_forecasts = zone_forecast[
                zone_forecast['forecast_horizon_hours'] == horizon
            ]
            
            if len(horizon_forecasts) > 0:
                # Merge forecast with historical baseline
                merged = pd.merge_asof(
                    zone_hist[['timestamp', 'temp_c']].sort_values('timestamp'),
                    horizon_forecasts[['timestamp', f'temp_forecast_{horizon}h']]
                    .sort_values('timestamp'),
                    on='timestamp',
                    direction='backward'
                )
                
                if not merged[f'temp_forecast_{horizon}h'].isna().all():
                    # Weight: historical baseline + limited forecast influence
                    baseline_weight = 1 - config.max_forecast_weight
                    forecast_weight = config.max_forecast_weight
                    
                    weighted_temp = (
                        baseline_weight * merged['temp_c'] +
                        forecast_weight * merged[f'temp_forecast_{horizon}h']
                    )
                    
                    # Add to feature dataframe
                    temp_df = merged[['timestamp']].copy()
                    temp_df['zone'] = zone
                    temp_df[f'temp_forecast_weighted_{horizon}h'] = weighted_temp
                    
                    feature_df = pd.concat([feature_df, temp_df], ignore_index=True)
    
    return feature_df


def create_forecast_confidence_features(
    forecast_df: pd.DataFrame,
    forecast_errors: Dict[str, Dict[int, float]],
    config: SafeForecastConfig
) -> pd.DataFrame:
    """Create features that encode forecast confidence."""
    confidence_df = forecast_df[['timestamp', 'zone']].copy()
    
    for zone in forecast_df['zone'].unique():
        for horizon in config.forecast_horizons:
            error_rate = forecast_errors.get(zone, {}).get(horizon, 20.0)
            
            # Confidence score (inverse of error rate)
            confidence = max(0.0, 1.0 - error_rate / 100.0)
            
            mask = (forecast_df['zone'] == zone) & (
                forecast_df['forecast_horizon_hours'] == horizon
            )
            
            confidence_df.loc[mask, f'forecast_confidence_{horizon}h'] = confidence
            confidence_df.loc[mask, f'forecast_uncertainty_{horizon}h'] = error_rate
    
    return confidence_df


def validate_forecast_features(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate forecast features for safety."""
    issues = []
    
    # Check for extreme values
    forecast_cols = [col for col in df.columns if 'forecast' in col and 'confidence' not in col]
    
    for col in forecast_cols:
        if col in df.columns:
            extreme_mask = (df[col] < -20) | (df[col] > 60)
            if extreme_mask.any():
                issues.append(f"Extreme values in {col}: {extreme_mask.sum()} records")
    
    # Check for excessive NaN values
    for col in forecast_cols:
        if col in df.columns:
            nan_rate = df[col].isna().mean()
            if nan_rate > 0.5:
                issues.append(f"High NaN rate in {col}: {nan_rate:.1%}")
    
    return len(issues) == 0, issues