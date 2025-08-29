#!/usr/bin/env python3
"""
Incremental CAISO Data Collection for Real-Time Updates (macOS)

This script performs incremental data collection to keep ML models current:
- Fetches latest CAISO power data (last 2-6 hours)
- Appends to existing datasets
- Uploads to S3 for backup
- Designed to run every 30 minutes via macOS launchd

Usage:
    python scripts/incremental_collection_macos.py [options]
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import logging
from typing import Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for incremental collection."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"incremental_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def collect_recent_caiso_data(hours_back: int = 6) -> Optional[pd.DataFrame]:
    """Collect recent CAISO data using existing pull_power functionality."""
    try:
        # Import here to avoid circular imports
        from src.ingest.pull_power import fetch_caiso_data
        
        # Fetch recent data (fetch_caiso_data expects days)
        days = max(1, hours_back // 24 + 1)
        df = fetch_caiso_data(days)
        
        if df is None or len(df) == 0:
            return None
        
        # Filter to recent hours
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours_back)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        recent_df = df[df['timestamp'] >= cutoff].copy()
        
        return recent_df
        
    except Exception as e:
        logging.error(f"Error collecting CAISO data: {e}")
        return None


def append_new_data(new_df: pd.DataFrame, target_file: Path) -> bool:
    """Append new data to existing file, handling duplicates."""
    try:
        if target_file.exists():
            existing_df = pd.read_parquet(target_file)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            # Remove duplicates based on timestamp and zone
            if 'zone' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['timestamp', 'zone'], keep='last')
            else:
                combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
            
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        else:
            combined_df = new_df.copy()
        
        # Ensure directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save updated data
        combined_df.to_parquet(target_file, index=False)
        
        logging.info(f"Updated {target_file}: {len(combined_df):,} total records")
        return True
        
    except Exception as e:
        logging.error(f"Error updating {target_file}: {e}")
        return False


def upload_to_s3(file_path: Path) -> bool:
    """Upload to S3 if configured."""
    try:
        import boto3
        
        s3_client = boto3.client('s3')
        bucket = "ml-power-nowcast-data-1756420517"
        s3_key = f"incremental/{file_path.name}"
        
        s3_client.upload_file(str(file_path), bucket, s3_key)
        logging.info(f"Uploaded to S3: {s3_key}")
        return True
        
    except Exception as e:
        logging.warning(f"S3 upload failed: {e}")
        return False


def main():
    """Main incremental collection function."""
    parser = argparse.ArgumentParser(description="Incremental CAISO data collection")
    parser.add_argument("--hours", type=int, default=6, help="Hours of recent data to collect")
    parser.add_argument("--no-s3", action="store_true", help="Skip S3 upload")
    parser.add_argument("--quiet", action="store_true", help="Minimal output for scheduled runs")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = "WARNING" if args.quiet else "INFO"
    logger = setup_logging(log_level)
    
    if not args.quiet:
        logger.info("🔄 Starting incremental CAISO data collection")
    
    try:
        # Define target file
        incremental_file = Path("data/incremental/caiso_recent.parquet")
        
        # Collect recent data
        logger.info(f"Collecting last {args.hours} hours of CAISO data")
        new_data = collect_recent_caiso_data(args.hours)
        
        if new_data is None or len(new_data) == 0:
            logger.warning("No new data collected")
            return 1
        
        logger.info(f"Collected {len(new_data):,} new records")
        
        # Append to incremental dataset
        if not append_new_data(new_data, incremental_file):
            return 1
        
        # Upload to S3
        if not args.no_s3:
            upload_to_s3(incremental_file)
        
        # Trigger dataset merge for continuous training
        try:
            import subprocess
            merge_cmd = [
                str(Path(__file__).parent.parent / ".venv" / "bin" / "python"),
                str(Path(__file__).parent / "merge_datasets.py"),
                "--log-level", "WARNING"
            ]
            result = subprocess.run(merge_cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            if result.returncode == 0:
                logger.info("Master dataset updated with new incremental data")
            else:
                logger.warning(f"Dataset merge failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"Could not trigger dataset merge: {e}")

        # Create refresh flag for models
        flag_file = Path("data/model_refresh_needed.flag")
        flag_file.touch()

        if not args.quiet:
            logger.info("✅ Incremental collection completed successfully")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Collection failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
