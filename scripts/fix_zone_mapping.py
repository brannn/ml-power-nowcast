#!/usr/bin/env python3
"""
Fix Zone Mapping in CAISO Dataset

This script properly maps resource names to CAISO zones to restore
full 7-zone coverage for model training.
"""

import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_zone_mapping():
    """Create mapping from resource names to CAISO zones."""
    return {
        # System-wide
        'CA ISO-TAC': 'SYSTEM',
        
        # Individual utility zones
        'PGE-TAC': 'NP15',           # Northern California (PG&E TAC)
        'PGE': 'PGE_VALLEY',        # PG&E Central Valley
        'SCE-TAC': 'SCE',           # Southern California Edison
        'SDGE-TAC': 'SDGE',         # San Diego Gas & Electric
        'BANCSMUD': 'SMUD',         # Sacramento Municipal Utility District
        'LADWP': 'SP15',            # Los Angeles Dept of Water & Power
    }

def fix_zones(input_file: str, output_file: str):
    """Fix zone assignments in the dataset."""
    logger.info(f"Loading dataset from {input_file}")
    df = pd.read_parquet(input_file)
    
    logger.info(f"Original shape: {df.shape}")
    logger.info(f"Zones before fix: {sorted(df[df.zone.notna()].zone.unique())}")
    
    # Create zone mapping
    zone_mapping = create_zone_mapping()
    logger.info(f"Zone mapping: {zone_mapping}")
    
    # Apply zone mapping
    df['zone'] = df['resource_name'].map(zone_mapping)
    
    # Filter to only California zones (remove NULL zones)
    california_df = df[df.zone.notna()].copy()
    
    logger.info(f"After zone mapping:")
    logger.info(f"Shape: {california_df.shape}")
    logger.info(f"Zones: {sorted(california_df.zone.unique())}")
    logger.info(f"Records per zone:")
    for zone, count in california_df.zone.value_counts().sort_index().items():
        logger.info(f"  {zone}: {count:,} records")
    
    # Date range info
    logger.info(f"Date range: {california_df.timestamp.min()} to {california_df.timestamp.max()}")
    
    # Save fixed dataset
    logger.info(f"Saving to {output_file}")
    california_df.to_parquet(output_file, index=False)
    
    return california_df

if __name__ == "__main__":
    # Fix the main dataset
    fixed_df = fix_zones(
        "data/master/caiso_california_only.parquet",
        "data/master/caiso_california_clean.parquet"
    )
    
    # Also update the backup
    logger.info("Updating backup dataset")
    fixed_df.to_parquet("data/master/caiso_california_complete_7zones.parquet", index=False)
    
    logger.info("✅ Zone mapping fix completed!")
    logger.info("Ready for 7-zone model training")