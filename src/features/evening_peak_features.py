#!/usr/bin/env python3
"""
Evening Peak Feature Engineering Pipeline

Implements enhanced temporal and weather features specifically designed to capture
evening peak demand patterns that address the current 9.7% underestimation.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class EveningPeakFeatureEngine:
    """Enhanced feature engineering pipeline focused on evening peak prediction."""
    
    def __init__(self, base_temperature: float = 75.0):
        """
        Initialize the evening peak feature engine.
        
        Args:
            base_temperature: Base temperature for cooling degree calculations (°F)
        """
        self.base_temperature = base_temperature
    
    def create_cyclical_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create cyclical encodings for temporal patterns."""
        df = df.copy()
        
        # Ensure hour column exists
        if 'hour' not in df.columns:
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # Cyclical hour encoding (captures 24-hour periodicity)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Cyclical day of week encoding (captures weekly patterns)
        if 'weekday' not in df.columns:
            df['weekday'] = pd.to_datetime(df['timestamp']).dt.weekday
        df['day_of_week_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
        df['day_of_week_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)
        
        # Cyclical month encoding (captures seasonal patterns)
        if 'month' not in df.columns:
            df['month'] = pd.to_datetime(df['timestamp']).dt.month
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        return df
    
    def create_evening_specific_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features specifically targeting evening peak periods."""
        df = df.copy()
        
        # Ensure hour column exists
        if 'hour' not in df.columns:
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # Binary evening peak flag (5-9 PM)
        df['is_evening_peak'] = ((df['hour'] >= 17) & (df['hour'] <= 21)).astype(int)
        
        # Evening hour intensity (0-1 scale within evening hours)
        df['evening_hour_intensity'] = np.where(
            df['is_evening_peak'] == 1,
            (df['hour'] - 17) / 4,  # Maps 17-21 to 0-1
            0.0
        )
        
        # Distance from peak hour (18:00 is typically highest)
        df['hours_from_peak'] = np.abs(df['hour'] - 18) / 24
        
        # Evening ramp-up pattern (captures build-up to peak)
        df['evening_ramp'] = np.where(
            (df['hour'] >= 15) & (df['hour'] <= 19),
            np.maximum(0, (df['hour'] - 15) / 4),  # Linear ramp 15-19
            0.0
        )
        
        # Post-peak decline (captures demand reduction after evening)
        df['post_peak_decline'] = np.where(
            (df['hour'] >= 21) & (df['hour'] <= 23),
            (23 - df['hour']) / 2,  # Linear decline 21-23
            0.0
        )
        
        return df
    
    def create_weather_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create weather features enhanced for evening peak demand."""
        df = df.copy()
        
        # Skip if temperature data not available
        if 'temperature' not in df.columns:
            logger.warning("No temperature column found, skipping weather features")
            return df
        
        # Evening temperature interaction (cooling demand during peak hours)
        df['temp_evening_interaction'] = df.get('temperature', 0) * df.get('is_evening_peak', 0)
        
        # Cooling degree hours (hourly version of cooling degree days)
        df['cooling_degree_hour'] = np.maximum(df.get('temperature', 0) - self.base_temperature, 0)
        
        # Enhanced evening cooling demand (exponential above 85°F during evening)
        df['evening_cooling_demand'] = np.where(
            (df.get('is_evening_peak', 0) == 1) & (df.get('temperature', 0) > 85),
            df.get('temperature', 0) * np.exp((df.get('temperature', 0) - 85) / 20),
            df.get('temperature', 0)
        )
        
        # Humidity-based cooling adjustment (if available)
        if 'humidity' in df.columns:
            df['humidity_cooling_factor'] = 1 + (df['humidity'] - 50) / 100  # Adjustment factor
            df['humidity_cooling_demand'] = df['cooling_degree_hour'] * df['humidity_cooling_factor']
        
        return df
    
    def create_lag_features(self, df: pd.DataFrame, target_col: str = 'load') -> pd.DataFrame:
        """Create enhanced lag features for demand forecasting."""
        df = df.copy().sort_values('timestamp')
        
        # Recent load history (1-2 hours)
        df[f'{target_col}_lag_1h'] = df.groupby('zone')[target_col].shift(1)
        df[f'{target_col}_lag_2h'] = df.groupby('zone')[target_col].shift(2)
        
        # Moving averages for trend detection
        df[f'{target_col}_ma_4h'] = df.groupby('zone')[target_col].rolling(window=4, min_periods=1).mean().reset_index(0, drop=True)
        df[f'{target_col}_ma_8h'] = df.groupby('zone')[target_col].rolling(window=8, min_periods=1).mean().reset_index(0, drop=True)
        
        # Daily trend component (change from 24h ago)
        df[f'{target_col}_daily_change'] = df.groupby('zone')[target_col].pct_change(periods=24)
        
        # Evening-to-evening comparison (same hour yesterday)
        df[f'{target_col}_day_over_day'] = df.groupby('zone')[target_col].pct_change(periods=24)
        
        # Recent temperature lags (if available)
        if 'temperature' in df.columns:
            df['temp_lag_1h'] = df.groupby('zone')['temperature'].shift(1)
            df['temp_lag_2h'] = df.groupby('zone')['temperature'].shift(2)
        
        return df
    
    def create_demand_pattern_features(self, df: pd.DataFrame, target_col: str = 'load') -> pd.DataFrame:
        """Create features that capture demand patterns and growth trends."""
        df = df.copy()
        
        # Days since dataset start (linear growth proxy)
        min_date = df['timestamp'].min()
        df['days_since_start'] = (df['timestamp'] - min_date).dt.total_seconds() / (24 * 3600)
        
        # Weekend vs weekday behavior
        if 'weekday' not in df.columns:
            df['weekday'] = pd.to_datetime(df['timestamp']).dt.weekday
        df['weekend_flag'] = (df['weekday'] >= 5).astype(int)
        
        # Holiday proximity effect (simplified - major holidays)
        df['month_day'] = pd.to_datetime(df['timestamp']).dt.strftime('%m-%d')
        holiday_dates = ['01-01', '07-04', '12-25', '11-24', '05-30']  # Major holidays
        df['near_holiday'] = df['month_day'].isin(holiday_dates).astype(int)
        
        # Summer vs winter patterns
        df['is_summer_month'] = df.get('month', pd.to_datetime(df['timestamp']).dt.month).isin([6, 7, 8, 9]).astype(int)
        
        # Work hour overlap (evening peak coincides with end of work day)
        df['work_evening_overlap'] = (
            (df.get('hour', pd.to_datetime(df['timestamp']).dt.hour) >= 17) &
            (df.get('hour', pd.to_datetime(df['timestamp']).dt.hour) <= 19) &
            (df.get('weekday', pd.to_datetime(df['timestamp']).dt.weekday) < 5)
        ).astype(int)
        
        return df
    
    def create_zone_specific_features(self, df: pd.DataFrame, zone: str) -> pd.DataFrame:
        """Create zone-specific features based on regional characteristics."""
        df = df.copy()
        
        # Zone-specific evening multipliers based on historical patterns
        zone_evening_multipliers = {
            'SCE': 1.15,    # Higher evening peaks due to residential concentration
            'SP15': 1.08,   # Moderate evening peaks with mixed commercial/residential
            'LADWP': 1.12,  # Similar to SCE but slightly lower
        }
        
        df['zone_evening_multiplier'] = zone_evening_multipliers.get(zone, 1.0)
        df['zone_adjusted_evening'] = (
            df.get('is_evening_peak', 0) * df['zone_evening_multiplier']
        )
        
        # Zone-specific growth factors (can be updated with actual data)
        zone_growth_factors = {
            'SCE': 0.02,    # 2% annual growth
            'SP15': 0.015,  # 1.5% annual growth
            'LADWP': 0.018, # 1.8% annual growth
        }
        
        df['zone_growth_factor'] = zone_growth_factors.get(zone, 0.0)
        df['zone_growth_effect'] = df.get('days_since_start', 0) * df['zone_growth_factor'] / 365
        
        return df
    
    def apply_all_features(self, df: pd.DataFrame, zone: str, target_col: str = 'load') -> pd.DataFrame:
        """Apply all feature engineering transformations."""
        logger.info(f"Applying evening peak features for zone: {zone}")
        
        # Apply each feature group
        df = self.create_cyclical_temporal_features(df)
        logger.info("Created cyclical temporal features")
        
        df = self.create_evening_specific_features(df)
        logger.info("Created evening-specific features")
        
        df = self.create_weather_interaction_features(df)
        logger.info("Created weather interaction features")
        
        df = self.create_lag_features(df, target_col)
        logger.info("Created lag features")
        
        df = self.create_demand_pattern_features(df, target_col)
        logger.info("Created demand pattern features")
        
        df = self.create_zone_specific_features(df, zone)
        logger.info(f"Created zone-specific features for {zone}")
        
        # Remove rows with NaN values created by lag features
        initial_rows = len(df)
        df = df.dropna()
        final_rows = len(df)
        
        if final_rows < initial_rows:
            logger.info(f"Removed {initial_rows - final_rows} rows with NaN values from lag features")
        
        logger.info(f"Feature engineering complete: {len(df)} samples, {len(df.columns)} features")
        return df

def enhance_training_datasets_with_features():
    """Enhance the weighted training datasets with evening peak features."""
    print("=== Evening Peak Feature Engineering Enhancement ===")
    
    feature_engine = EveningPeakFeatureEngine()
    training_dir = Path("data/training")
    enhanced_dir = Path("data/enhanced_training")
    enhanced_dir.mkdir(parents=True, exist_ok=True)
    
    zones = ['SCE', 'SP15']
    
    for zone in zones:
        print(f"\nEnhancing features for {zone} zone...")
        
        # Load weighted training and validation datasets
        train_file = training_dir / f"{zone}_weighted_train.parquet"
        val_file = training_dir / f"{zone}_weighted_val.parquet"
        
        if not train_file.exists():
            print(f"❌ Training file not found: {train_file}")
            continue
        
        # Load datasets
        train_df = pd.read_parquet(train_file)
        val_df = pd.read_parquet(val_file)
        
        print(f"  Original train samples: {len(train_df)}")
        print(f"  Original validation samples: {len(val_df)}")
        
        # Apply feature engineering
        enhanced_train = feature_engine.apply_all_features(train_df, zone)
        enhanced_val = feature_engine.apply_all_features(val_df, zone)
        
        # Save enhanced datasets
        enhanced_train_file = enhanced_dir / f"{zone}_enhanced_train.parquet"
        enhanced_val_file = enhanced_dir / f"{zone}_enhanced_val.parquet"
        
        enhanced_train.to_parquet(enhanced_train_file, index=False)
        enhanced_val.to_parquet(enhanced_val_file, index=False)
        
        print(f"  Enhanced train samples: {len(enhanced_train)}")
        print(f"  Enhanced validation samples: {len(enhanced_val)}")
        print(f"  Total features: {len(enhanced_train.columns)}")
        print(f"  Saved to: {enhanced_train_file}")
        
        # Show key evening features
        evening_features = [col for col in enhanced_train.columns 
                          if 'evening' in col.lower() or 'peak' in col.lower()]
        print(f"  Evening-specific features: {len(evening_features)}")
        print(f"    {', '.join(evening_features[:5])}{'...' if len(evening_features) > 5 else ''}")
    
    print("\n✅ Evening peak feature engineering complete!")
    print("\nNext steps:")
    print("1. Train zone-specific models using enhanced datasets")
    print("2. Apply sample_weight column during model fitting")
    print("3. Test evening peak prediction improvements")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    enhance_training_datasets_with_features()