#!/usr/bin/env python3
"""
Seamless Dataset Merger for Continuous ML Training

This script merges historical and incremental CAISO datasets into a unified,
continuously growing dataset for ML training. It handles:
- Deduplication across datasets
- Gap detection and filling
- Data validation and quality checks
- Incremental updates to the master dataset
- Preparation for ML feature engineering

Usage:
    python scripts/merge_datasets.py [options]
"""

import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Tuple, Optional

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for dataset merging."""
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"dataset_merge_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def load_datasets(logger: logging.Logger) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Load historical, incremental, and existing master datasets."""
    
    # Load historical data
    hist_file = Path("data/historical/caiso_5year_full.parquet")
    if hist_file.exists():
        logger.info("Loading historical dataset...")
        hist_df = pd.read_parquet(hist_file)
        hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'])
        logger.info(f"Historical: {len(hist_df):,} records ({hist_df.timestamp.min()} to {hist_df.timestamp.max()})")
    else:
        logger.warning("Historical dataset not found")
        hist_df = None
    
    # Load incremental data
    inc_file = Path("data/incremental/caiso_recent.parquet")
    if inc_file.exists():
        logger.info("Loading incremental dataset...")
        inc_df = pd.read_parquet(inc_file)
        inc_df['timestamp'] = pd.to_datetime(inc_df['timestamp'])
        logger.info(f"Incremental: {len(inc_df):,} records ({inc_df.timestamp.min()} to {inc_df.timestamp.max()})")
    else:
        logger.warning("Incremental dataset not found")
        inc_df = None
    
    # Load existing master dataset (if it exists)
    master_file = Path("data/master/caiso_master.parquet")
    if master_file.exists():
        logger.info("Loading existing master dataset...")
        master_df = pd.read_parquet(master_file)
        master_df['timestamp'] = pd.to_datetime(master_df['timestamp'])
        logger.info(f"Existing master: {len(master_df):,} records ({master_df.timestamp.min()} to {master_df.timestamp.max()})")
    else:
        logger.info("No existing master dataset found - will create new one")
        master_df = None
    
    return hist_df, inc_df, master_df


def merge_and_deduplicate(hist_df: pd.DataFrame, inc_df: pd.DataFrame, 
                         master_df: Optional[pd.DataFrame], logger: logging.Logger) -> pd.DataFrame:
    """Merge datasets with intelligent deduplication."""
    
    logger.info("Merging datasets...")
    
    # Start with historical data as base
    datasets_to_merge = []
    
    if master_df is not None:
        # Use existing master as base
        datasets_to_merge.append(master_df)
        logger.info("Using existing master dataset as base")
    elif hist_df is not None:
        # Use historical as base
        datasets_to_merge.append(hist_df)
        logger.info("Using historical dataset as base")
    
    # Add incremental data
    if inc_df is not None:
        datasets_to_merge.append(inc_df)
        logger.info("Adding incremental data")
    
    if not datasets_to_merge:
        logger.error("No datasets to merge!")
        return pd.DataFrame()
    
    # Combine all datasets
    combined_df = pd.concat(datasets_to_merge, ignore_index=True)
    logger.info(f"Combined dataset: {len(combined_df):,} records")
    
    # Remove duplicates (keep latest based on timestamp+zone+resource_name)
    before_dedup = len(combined_df)
    combined_df = combined_df.drop_duplicates(
        subset=['timestamp', 'zone', 'resource_name'], 
        keep='last'
    )
    after_dedup = len(combined_df)
    
    logger.info(f"Removed {before_dedup - after_dedup:,} duplicate records")
    
    # Sort by timestamp
    combined_df = combined_df.sort_values(['timestamp', 'zone']).reset_index(drop=True)
    
    return combined_df


def analyze_data_quality(df: pd.DataFrame, logger: logging.Logger) -> dict:
    """Analyze merged dataset quality and identify issues."""
    
    logger.info("Analyzing data quality...")
    
    analysis = {
        'total_records': len(df),
        'date_range': (df['timestamp'].min(), df['timestamp'].max()),
        'zones': df['zone'].value_counts().to_dict(),
        'missing_zones': df['zone'].isnull().sum(),
        'load_stats': df['load'].describe().to_dict(),
        'gaps': []
    }
    
    # Check for temporal gaps in each zone
    california_zones = ['SYSTEM', 'NP15', 'SCE', 'SMUD', 'PGE_VALLEY', 'SP15', 'SDGE']
    
    for zone in california_zones:
        if zone in analysis['zones']:
            zone_data = df[df['zone'] == zone].sort_values('timestamp')
            if len(zone_data) > 1:
                time_diffs = zone_data['timestamp'].diff().dropna()
                expected_interval = pd.Timedelta(minutes=5)  # CAISO 5-minute data
                
                # Find gaps larger than 15 minutes (3x expected)
                large_gaps = time_diffs[time_diffs > expected_interval * 3]
                if len(large_gaps) > 0:
                    analysis['gaps'].append({
                        'zone': zone,
                        'gap_count': len(large_gaps),
                        'largest_gap': str(large_gaps.max())
                    })
    
    # Log analysis results
    logger.info(f"Quality Analysis Results:")
    logger.info(f"  Total records: {analysis['total_records']:,}")
    logger.info(f"  Date range: {analysis['date_range'][0]} to {analysis['date_range'][1]}")
    logger.info(f"  California zones: {len([z for z in california_zones if z in analysis['zones']])}/7")
    logger.info(f"  Missing zone values: {analysis['missing_zones']:,}")
    logger.info(f"  Load range: {analysis['load_stats']['min']:.1f} - {analysis['load_stats']['max']:.1f} MW")
    
    if analysis['gaps']:
        logger.warning(f"Found temporal gaps in {len(analysis['gaps'])} zones")
        for gap in analysis['gaps']:
            logger.warning(f"  {gap['zone']}: {gap['gap_count']} gaps, largest: {gap['largest_gap']}")
    else:
        logger.info("No significant temporal gaps found")
    
    return analysis


def save_master_dataset(df: pd.DataFrame, logger: logging.Logger) -> bool:
    """Save the merged dataset as the new master dataset."""
    
    try:
        # Ensure output directory exists
        output_dir = Path("data/master")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save master dataset
        master_file = output_dir / "caiso_master.parquet"
        df.to_parquet(master_file, index=False)
        
        # Save California-only subset for ML training
        ca_only_df = df[df['zone'].notnull()].copy()  # Only mapped California zones
        ca_file = output_dir / "caiso_california_only.parquet"
        ca_only_df.to_parquet(ca_file, index=False)
        
        logger.info(f"Saved master dataset: {master_file} ({len(df):,} records)")
        logger.info(f"Saved CA-only dataset: {ca_file} ({len(ca_only_df):,} records)")
        
        # Create metadata file
        metadata = {
            'created': datetime.now().isoformat(),
            'total_records': len(df),
            'california_records': len(ca_only_df),
            'date_range_start': df['timestamp'].min().isoformat(),
            'date_range_end': df['timestamp'].max().isoformat(),
            'zones': df['zone'].value_counts().to_dict(),
            'file_size_mb': master_file.stat().st_size / (1024**2)
        }
        
        metadata_file = output_dir / "dataset_metadata.json"
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Saved metadata: {metadata_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving master dataset: {e}")
        return False


def main():
    """Main dataset merging function."""
    
    parser = argparse.ArgumentParser(
        description="Merge historical and incremental datasets for continuous ML training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreation of master dataset even if it exists"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    logger.info("🔗 Starting dataset merge for continuous ML training")
    logger.info("=" * 60)
    
    try:
        # Load all datasets
        hist_df, inc_df, master_df = load_datasets(logger)
        
        if hist_df is None and inc_df is None:
            logger.error("No datasets found to merge!")
            return 1
        
        # Check if we need to merge
        if not args.force and master_df is not None and inc_df is not None:
            # Check if incremental data is newer than master
            master_end = master_df['timestamp'].max()
            inc_end = inc_df['timestamp'].max()
            
            if inc_end <= master_end:
                logger.info("Master dataset is already up to date")
                return 0
        
        # Merge datasets
        merged_df = merge_and_deduplicate(hist_df, inc_df, master_df, logger)
        
        if len(merged_df) == 0:
            logger.error("Merged dataset is empty!")
            return 1
        
        # Analyze quality
        analysis = analyze_data_quality(merged_df, logger)
        
        # Save master dataset
        if save_master_dataset(merged_df, logger):
            logger.info("✅ Dataset merge completed successfully!")
            logger.info(f"Master dataset ready for ML training: {analysis['total_records']:,} records")
            
            # Create flag for ML pipeline
            flag_file = Path("data/master_dataset_updated.flag")
            flag_file.touch()
            
            return 0
        else:
            logger.error("❌ Failed to save master dataset")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Dataset merge failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
