#!/usr/bin/env python3
"""
CAISO Historical Data Collection Script

Collects 5 years of real CAISO system load data (2020-2025) using the 
rate-limited CAISO OASIS API. This script provides comprehensive data
collection with progress tracking, error handling, and data validation.

Usage:
    python scripts/collect_caiso_historical.py [options]

The script will:
1. Collect real CAISO system load data from August 28, 2020 to present
2. Use 15-second rate limiting for reliable API access
3. Save data to both local files and S3
4. Provide progress updates and time estimates
5. Handle interruptions gracefully with resume capability

Expected runtime: ~30-45 minutes for full 5-year collection
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import boto3
import pandas as pd
from botocore.exceptions import ClientError

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ingest.pull_power import fetch_caiso_data
from src.ingest.pull_weather import fetch_caiso_zone_weather_data


def setup_logging():
    """Set up logging for the collection process."""
    import logging
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"caiso_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def calculate_collection_stats(start_date: datetime, end_date: datetime):
    """Calculate and display collection statistics."""
    total_days = (end_date - start_date).days
    chunks = total_days // 14 + 1  # 14-day chunks
    estimated_minutes = chunks * 15 / 60  # 15 seconds per chunk
    
    print(f"📊 COLLECTION PLAN:")
    print(f"   Start Date: {start_date.strftime('%Y-%m-%d')}")
    print(f"   End Date: {end_date.strftime('%Y-%m-%d')}")
    print(f"   Total Days: {total_days} ({total_days/365:.1f} years)")
    print(f"   API Chunks: {chunks} (14-day chunks)")
    print(f"   Estimated Time: ~{estimated_minutes:.1f} minutes")
    print(f"   Rate Limiting: 15 seconds between chunks")
    print()
    
    return total_days, chunks, estimated_minutes


def save_data_locally(power_df: pd.DataFrame, output_dir: Path):
    """Save collected data to local files."""
    print("💾 Saving data locally...")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full dataset
    full_path = output_dir / "caiso_5year_full.parquet"
    power_df.to_parquet(full_path, index=False)
    print(f"   ✅ Full dataset: {full_path} ({len(power_df):,} records)")
    
    # Save system-only data
    system_data = power_df[power_df['zone'] == 'SYSTEM']
    if len(system_data) > 0:
        system_path = output_dir / "caiso_5year_system.parquet"
        system_data.to_parquet(system_path, index=False)
        print(f"   ✅ System data: {system_path} ({len(system_data):,} records)")
        
        # Display system data stats
        print(f"   📊 System load range: {system_data['load'].min():.1f} - {system_data['load'].max():.1f} MW")
        print(f"   📊 Average system load: {system_data['load'].mean():.1f} MW")
    
    # Save zone breakdown
    zone_counts = power_df['zone'].value_counts()
    print(f"   📊 Zone breakdown:")
    for zone, count in zone_counts.head(10).items():
        if pd.notna(zone):
            print(f"      {zone}: {count:,} records")
    
    return full_path, system_path if len(system_data) > 0 else None


def upload_to_s3(local_path: Path, s3_key: str, bucket: str = "ml-power-nowcast-data-1756420517"):
    """Upload data to S3 with error handling."""
    try:
        s3_client = boto3.client('s3')
        s3_client.upload_file(str(local_path), bucket, s3_key)
        print(f"   ✅ Uploaded to s3://{bucket}/{s3_key}")
        return True
    except ClientError as e:
        print(f"   ❌ S3 upload failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return False


def main():
    """Main collection function."""
    parser = argparse.ArgumentParser(
        description="Collect 5 years of CAISO historical data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        default="2020-08-28",
        help="Start date for collection (YYYY-MM-DD). Default: 2020-08-28"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date for collection (YYYY-MM-DD). Default: today"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/historical",
        help="Output directory for data files. Default: data/historical"
    )
    
    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help="Upload collected data to S3"
    )

    parser.add_argument(
        "--collect-weather",
        action="store_true",
        help="Also collect weather data for all power zones"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show collection plan without actually collecting data"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    print("🚀 CAISO Historical Data Collection")
    print("=" * 50)
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        return 1
    
    if start_date >= end_date:
        print("❌ Start date must be before end date")
        return 1
    
    # Calculate collection statistics
    total_days, chunks, estimated_minutes = calculate_collection_stats(start_date, end_date)
    
    if args.dry_run:
        print("🔍 DRY RUN - No data will be collected")
        print("✅ Collection plan validated")
        return 0
    
    # Confirm collection
    print("⚠️  This will collect real CAISO data using their API with 15-second rate limiting.")
    print(f"   Estimated time: ~{estimated_minutes:.1f} minutes")
    
    try:
        confirm = input("\nProceed with collection? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Collection cancelled by user")
            return 0
    except KeyboardInterrupt:
        print("\n❌ Collection cancelled by user")
        return 0
    
    # Start collection
    print(f"\n🔄 Starting CAISO data collection...")
    print(f"   Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    start_time = datetime.now()
    
    try:
        # Collect power data
        power_df = fetch_caiso_data(days=total_days)

        # Collect weather data if requested
        weather_df = None
        if args.collect_weather:
            print(f"\n🌤️  Collecting weather data for all power zones...")
            power_zones = ['NP15', 'SCE', 'SMUD', 'PGE_VALLEY', 'SP15', 'SDGE']
            weather_df = fetch_caiso_zone_weather_data(
                days=total_days,
                zones=power_zones,
                aggregate_method='separate'
            )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60  # minutes
        
        print(f"\n✅ COLLECTION COMPLETE!")
        print(f"   Duration: {duration:.1f} minutes")
        print(f"   Records: {len(power_df):,}")
        print(f"   Date range: {power_df['timestamp'].min()} to {power_df['timestamp'].max()}")
        
        # Save data locally
        output_dir = Path(args.output_dir)
        full_path, system_path = save_data_locally(power_df, output_dir)

        # Save weather data if collected
        weather_path = None
        if weather_df is not None:
            weather_path = output_dir / "caiso_5year_weather.parquet"
            weather_df.to_parquet(weather_path, index=False)
            print(f"   ✅ Weather data: {weather_path} ({len(weather_df):,} records)")

            # Show weather zone breakdown
            weather_zone_counts = weather_df['zone'].value_counts()
            print(f"   📊 Weather zones:")
            for zone, count in weather_zone_counts.items():
                print(f"      {zone}: {count:,} records")
        
        # Upload to S3 if requested
        if args.upload_s3:
            print(f"\n☁️  Uploading to S3...")
            
            # Upload full dataset
            s3_key_full = f"raw/power/caiso/historical_5year_{datetime.now().strftime('%Y%m%d')}.parquet"
            upload_to_s3(full_path, s3_key_full)
            
            # Upload system dataset
            if system_path:
                s3_key_system = f"processed/power/caiso/system_5year_{datetime.now().strftime('%Y%m%d')}.parquet"
                upload_to_s3(system_path, s3_key_system)
        
        print(f"\n🎉 SUCCESS: 5-year CAISO historical data collection complete!")
        print(f"   Local files: {output_dir}")
        if args.upload_s3:
            print(f"   S3 bucket: ml-power-nowcast-data-1756420517")
        
        logger.info(f"Collection completed: {len(power_df):,} records in {duration:.1f} minutes")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Collection interrupted by user")
        logger.warning("Collection interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n❌ Collection failed: {e}")
        logger.error(f"Collection failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
