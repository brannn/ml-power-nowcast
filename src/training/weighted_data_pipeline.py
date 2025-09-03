#!/usr/bin/env python3
"""
Enhanced Training Data Pipeline with Recent Data Weighting

Implements Phase 1 of the model retraining strategy to address 9.7% underestimation
in evening peak predictions by applying temporal weighting to training samples.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class WeightedDataPipeline:
    """Enhanced training data pipeline with temporal and time-of-day weighting."""
    
    def __init__(self, data_file_path: str = "backup_s3_data/raw/power/caiso/historical_5year_20250829.parquet"):
        """
        Initialize the weighted data pipeline.
        
        Args:
            data_file_path: Path to the historical CAISO dataset with zone data
        """
        self.data_file = Path(data_file_path)
        
        # Weighting strategy parameters
        self.temporal_weights = {
            'last_30_days': 3.0,      # 3x weight for most recent data
            'last_90_days': 2.0,      # 2x weight for recent data  
            'last_180_days': 1.5,     # 1.5x weight for moderately recent
            'older_data': 1.0         # Standard weight for historical
        }
        
        self.time_of_day_weights = {
            'evening_peak_hours': 2.5,  # 2.5x weight for 17-21 hours
            'afternoon_hours': 1.5,     # 1.5x weight for 14-16 hours
            'other_hours': 1.0          # Standard weight
        }
        
        self.sample_strategy = {
            'min_recent_samples': 1000,  # Minimum recent evening samples per zone
            'max_total_samples': 50000,  # Cap total training samples per zone
            'validation_split': 0.2,    # 20% for validation
            'time_based_split': True     # Split by time, not random
        }
    
    def load_and_prepare_data(self) -> pd.DataFrame:
        """Load and prepare the base dataset with temporal features."""
        if not self.data_file.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_file}")
        
        logger.info(f"Loading dataset from {self.data_file}")
        df = pd.read_parquet(self.data_file)
        
        # Filter for SCE and SP15 zones only
        df = df[df['zone'].isin(['SCE', 'SP15'])].copy()
        
        # Remove rows with null zones or load
        df = df.dropna(subset=['zone', 'load'])
        
        # Convert timestamp and add temporal features
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['weekday'] = df['timestamp'].dt.weekday
        df['month'] = df['timestamp'].dt.month
        df['date'] = df['timestamp'].dt.date
        
        logger.info(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns")
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        logger.info(f"Zones: {df['zone'].unique()}")
        
        return df
    
    def calculate_temporal_weights(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate temporal weights based on data recency."""
        df = df.copy()
        latest_date = df['timestamp'].max()
        
        # Define temporal periods
        cutoffs = {
            'last_30_days': latest_date - timedelta(days=30),
            'last_90_days': latest_date - timedelta(days=90),
            'last_180_days': latest_date - timedelta(days=180),
        }
        
        # Assign temporal weights
        conditions = [
            df['timestamp'] >= cutoffs['last_30_days'],
            df['timestamp'] >= cutoffs['last_90_days'],
            df['timestamp'] >= cutoffs['last_180_days'],
        ]
        
        choices = [
            self.temporal_weights['last_30_days'],
            self.temporal_weights['last_90_days'],
            self.temporal_weights['last_180_days'],
        ]
        
        df['temporal_weight'] = np.select(conditions, choices, 
                                        default=self.temporal_weights['older_data'])
        
        return df
    
    def calculate_time_of_day_weights(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate time-of-day weights to emphasize evening peaks."""
        df = df.copy()
        
        # Define hour-based weights
        conditions = [
            df['hour'].between(17, 21),  # Evening peak hours
            df['hour'].between(14, 16),  # Afternoon hours
        ]
        
        choices = [
            self.time_of_day_weights['evening_peak_hours'],
            self.time_of_day_weights['afternoon_hours'],
        ]
        
        df['time_of_day_weight'] = np.select(conditions, choices,
                                           default=self.time_of_day_weights['other_hours'])
        
        return df
    
    def calculate_combined_weights(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate combined sample weights for training."""
        df = df.copy()
        
        # Apply temporal weighting
        df = self.calculate_temporal_weights(df)
        
        # Apply time-of-day weighting  
        df = self.calculate_time_of_day_weights(df)
        
        # Combine weights multiplicatively
        df['sample_weight'] = df['temporal_weight'] * df['time_of_day_weight']
        
        logger.info(f"Weight distribution:")
        logger.info(f"  Min weight: {df['sample_weight'].min():.2f}")
        logger.info(f"  Max weight: {df['sample_weight'].max():.2f}")
        logger.info(f"  Mean weight: {df['sample_weight'].mean():.2f}")
        
        return df
    
    def create_zone_weighted_dataset(self, df: pd.DataFrame, zone: str) -> pd.DataFrame:
        """Create weighted dataset for specific zone."""
        zone_data = df[df['zone'] == zone].copy()
        
        if len(zone_data) == 0:
            raise ValueError(f"No data found for zone: {zone}")
        
        # Calculate combined weights
        zone_data = self.calculate_combined_weights(zone_data)
        
        # Sort by timestamp for time-based splitting
        zone_data = zone_data.sort_values('timestamp')
        
        # Check minimum recent samples requirement
        recent_cutoff = zone_data['timestamp'].max() - timedelta(days=60)
        recent_evening_samples = len(zone_data[
            (zone_data['timestamp'] >= recent_cutoff) & 
            (zone_data['hour'].between(17, 21))
        ])
        
        logger.info(f"{zone} zone dataset:")
        logger.info(f"  Total samples: {len(zone_data)}")
        logger.info(f"  Recent evening samples: {recent_evening_samples}")
        
        if recent_evening_samples < self.sample_strategy['min_recent_samples']:
            logger.warning(f"Zone {zone} has only {recent_evening_samples} recent evening samples, "
                         f"minimum required: {self.sample_strategy['min_recent_samples']}")
        
        return zone_data
    
    def apply_sample_strategy(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Apply sampling strategy to create train/validation split."""
        max_samples = self.sample_strategy['max_total_samples']
        
        # Cap total samples if needed
        if len(df) > max_samples:
            logger.info(f"Capping dataset from {len(df)} to {max_samples} samples")
            # Use weighted sampling to preserve important samples
            sample_probs = df['sample_weight'] / df['sample_weight'].sum()
            sampled_indices = np.random.choice(
                df.index, size=max_samples, replace=False, p=sample_probs
            )
            df = df.loc[sampled_indices].sort_values('timestamp')
        
        # Time-based train/validation split
        split_point = int(len(df) * (1 - self.sample_strategy['validation_split']))
        
        train_df = df.iloc[:split_point].copy()
        val_df = df.iloc[split_point:].copy()
        
        logger.info(f"Dataset split:")
        logger.info(f"  Training samples: {len(train_df)}")
        logger.info(f"  Validation samples: {len(val_df)}")
        logger.info(f"  Training date range: {train_df['timestamp'].min()} to {train_df['timestamp'].max()}")
        logger.info(f"  Validation date range: {val_df['timestamp'].min()} to {val_df['timestamp'].max()}")
        
        return train_df, val_df
    
    def analyze_weighting_impact(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze the impact of weighting on sample distribution."""
        analysis = {}
        
        # Evening sample analysis
        evening_data = df[df['hour'].between(17, 21)]
        all_evening_weight = evening_data['sample_weight'].sum()
        total_weight = df['sample_weight'].sum()
        evening_weight_pct = (all_evening_weight / total_weight) * 100
        
        # Recent data analysis
        recent_cutoff = df['timestamp'].max() - timedelta(days=30)
        recent_data = df[df['timestamp'] >= recent_cutoff]
        recent_weight = recent_data['sample_weight'].sum()
        recent_weight_pct = (recent_weight / total_weight) * 100
        
        analysis = {
            'evening_samples_pct': len(evening_data) / len(df) * 100,
            'evening_weight_pct': evening_weight_pct,
            'recent_samples_pct': len(recent_data) / len(df) * 100,
            'recent_weight_pct': recent_weight_pct,
            'weight_amplification': df['sample_weight'].max() / df['sample_weight'].min()
        }
        
        return analysis
    
    def create_weighted_datasets(self, target_zones: List[str] = None) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
        """Create weighted training datasets for specified zones."""
        if target_zones is None:
            target_zones = ['SCE', 'SP15']  # Focus on LA_METRO component zones
        
        # Load base data
        df = self.load_and_prepare_data()
        
        zone_datasets = {}
        
        for zone in target_zones:
            logger.info(f"Creating weighted dataset for zone: {zone}")
            
            try:
                # Create zone-specific weighted dataset
                zone_data = self.create_zone_weighted_dataset(df, zone)
                
                # Apply sampling strategy
                train_df, val_df = self.apply_sample_strategy(zone_data)
                
                # Analyze weighting impact
                impact = self.analyze_weighting_impact(zone_data)
                
                logger.info(f"{zone} weighting impact:")
                logger.info(f"  Evening samples: {impact['evening_samples_pct']:.1f}% → weighted: {impact['evening_weight_pct']:.1f}%")
                logger.info(f"  Recent samples: {impact['recent_samples_pct']:.1f}% → weighted: {impact['recent_weight_pct']:.1f}%")
                logger.info(f"  Weight amplification: {impact['weight_amplification']:.1f}x")
                
                zone_datasets[zone] = (train_df, val_df)
                
            except Exception as e:
                logger.error(f"Failed to create dataset for zone {zone}: {e}")
                continue
        
        return zone_datasets
    
    def save_weighted_datasets(self, zone_datasets: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]], 
                             output_dir: str = "data/training") -> Dict[str, Dict[str, str]]:
        """Save weighted datasets to disk."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        for zone, (train_df, val_df) in zone_datasets.items():
            zone_files = {}
            
            # Save training dataset
            train_file = output_path / f"{zone}_weighted_train.parquet"
            train_df.to_parquet(train_file, index=False)
            zone_files['train'] = str(train_file)
            
            # Save validation dataset
            val_file = output_path / f"{zone}_weighted_val.parquet"
            val_df.to_parquet(val_file, index=False)
            zone_files['val'] = str(val_file)
            
            logger.info(f"Saved {zone} datasets:")
            logger.info(f"  Training: {train_file}")
            logger.info(f"  Validation: {val_file}")
            
            saved_files[zone] = zone_files
        
        return saved_files

def demonstrate_weighted_pipeline():
    """Demonstrate the enhanced weighted data pipeline."""
    print("=== Enhanced Training Data Pipeline with Recent Data Weighting ===")
    
    pipeline = WeightedDataPipeline()
    
    try:
        print("\n1. Creating weighted datasets for SCE and SP15 zones...")
        zone_datasets = pipeline.create_weighted_datasets(['SCE', 'SP15'])
        
        print("\n2. Saving datasets to disk...")
        saved_files = pipeline.save_weighted_datasets(zone_datasets)
        
        print("\n3. Dataset Summary:")
        for zone, files in saved_files.items():
            train_df, val_df = zone_datasets[zone]
            print(f"\n{zone} Zone:")
            print(f"  Training samples: {len(train_df):,}")
            print(f"  Validation samples: {len(val_df):,}")
            print(f"  Files: {files['train']}, {files['val']}")
            
            # Evening peak statistics
            train_evening = train_df[train_df['hour'].between(17, 21)]
            evening_weight_total = train_evening['sample_weight'].sum()
            total_weight = train_df['sample_weight'].sum()
            evening_influence = (evening_weight_total / total_weight) * 100
            
            print(f"  Evening peak influence: {evening_influence:.1f}% of total training weight")
        
        print("\n✅ Weighted data pipeline complete!")
        print("\nNext steps:")
        print("1. Use these weighted datasets for model retraining")
        print("2. Apply sample_weight column during model fitting")
        print("3. Validate improvements on recent evening peak predictions")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    demonstrate_weighted_pipeline()