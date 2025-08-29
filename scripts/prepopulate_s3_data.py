#!/usr/bin/env python3
"""
Pre-populate S3 bucket with historical power and weather data.

This script downloads historical data from CAISO and NYISO APIs and uploads
it directly to S3, avoiding repeated API calls during development and testing.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from src.ingest.pull_power import fetch_caiso_data, generate_synthetic_power_data
from src.ingest.pull_weather import (
    fetch_noaa_weather_data,
    fetch_meteostat_data,
    generate_synthetic_weather_data,
    fetch_nyiso_zone_weather_data,
    fetch_caiso_zone_weather_data
)


def get_s3_client() -> boto3.client:
    """Get configured S3 client."""
    try:
        return boto3.client('s3')
    except Exception as e:
        print(f"Error creating S3 client: {e}")
        print("Make sure AWS credentials are configured (aws configure)")
        raise


def upload_to_s3(df: pd.DataFrame, bucket: str, key: str, s3_client: boto3.client) -> bool:
    """
    Upload DataFrame to S3 as parquet file.
    
    Args:
        df: DataFrame to upload
        bucket: S3 bucket name
        key: S3 object key
        s3_client: Boto3 S3 client
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Save to temporary local file
        temp_file = f"/tmp/{Path(key).name}"
        df.to_parquet(temp_file, index=False)
        
        # Upload to S3
        s3_client.upload_file(temp_file, bucket, key)
        
        # Clean up temp file
        os.remove(temp_file)
        
        print(f"✅ Uploaded {len(df)} records to s3://{bucket}/{key}")
        return True
        
    except ClientError as e:
        print(f"❌ Failed to upload to s3://{bucket}/{key}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error uploading {key}: {e}")
        return False


def check_s3_object_exists(bucket: str, key: str, s3_client: boto3.client) -> bool:
    """Check if S3 object already exists."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def prepopulate_power_data(
    bucket: str,
    years: int = 3,
    force: bool = False,
    use_synthetic: bool = False,
    s3_client: Optional[boto3.client] = None
) -> None:
    """
    Pre-populate S3 with historical power data from CAISO and NYISO.

    Args:
        bucket: S3 bucket name
        years: Number of years of historical data to fetch (limited by API availability)
        force: Overwrite existing data
        use_synthetic: Use synthetic data instead of real APIs
        s3_client: Boto3 S3 client
    """
    if s3_client is None:
        s3_client = get_s3_client()

    # For real data, limit to available data ranges
    if not use_synthetic:
        # CAISO OASIS retention is ~39 months
        max_caiso_days = min(years * 365, 39 * 30)  # CAISO retention ~39 months

        print(f"📊 Fetching real CAISO power data (limited by API availability):")
        print(f"   CAISO: {max_caiso_days} days (OASIS retention ~39 months)")
    else:
        days = years * 365
        print(f"📊 Generating {years} years ({days} days) of synthetic power data...")
    
    # CAISO data (California focus only)
    data_type = "synthetic" if use_synthetic else "real"
    if use_synthetic:
        caiso_key = f"raw/power/caiso/{data_type}_{years}y.parquet"
        days_caiso = years * 365
    else:
        caiso_key = f"raw/power/caiso/{data_type}_{max_caiso_days}d.parquet"
        days_caiso = max_caiso_days

    if not force and check_s3_object_exists(bucket, caiso_key, s3_client):
        print(f"⏭️  CAISO data already exists: s3://{bucket}/{caiso_key}")
    else:
        if use_synthetic:
            print("🔄 Generating synthetic CAISO data...")
            caiso_df = generate_synthetic_power_data(days=days_caiso)
            caiso_df["region"] = "CAISO"
            caiso_df["data_source"] = "synthetic"
            upload_to_s3(caiso_df, bucket, caiso_key, s3_client)
        else:
            print(f"🔄 Fetching real CAISO data ({days_caiso} days available)...")
            try:
                caiso_df = fetch_caiso_data(days=days_caiso)
                upload_to_s3(caiso_df, bucket, caiso_key, s3_client)
            except Exception as e:
                print(f"❌ Failed to fetch CAISO data: {e}")
                print("💡 Consider using synthetic data mode: --synthetic-power")
                print("   Or try a shorter time period with --years 1")
                raise


def prepopulate_weather_data(
    bucket: str,
    years: int = 3,
    force: bool = False,
    use_synthetic: bool = False,
    noaa_token: Optional[str] = None,
    s3_client: Optional[boto3.client] = None
) -> None:
    """
    Pre-populate S3 with historical weather data.

    Args:
        bucket: S3 bucket name
        years: Number of years of historical data to fetch
        force: Overwrite existing data
        use_synthetic: Use synthetic weather data instead of real APIs
        noaa_token: NOAA API token
        s3_client: Boto3 S3 client
    """
    if s3_client is None:
        s3_client = get_s3_client()
    
    days = years * 365
    print(f"🌤️  Fetching {years} years ({days} days) of weather data...")
    
    # NYISO zone-based weather (for accurate power correlation)
    data_type = "synthetic" if use_synthetic else "real"
    nyiso_weather_key = f"raw/weather/nyiso_zones/{data_type}_{years}y.parquet"

    if not force and check_s3_object_exists(bucket, nyiso_weather_key, s3_client):
        print(f"⏭️  NYISO zone weather data already exists: s3://{bucket}/{nyiso_weather_key}")
    else:
        if use_synthetic:
            print("🔄 Generating synthetic NYISO weather data...")
            nyiso_weather_df = generate_synthetic_weather_data(days=days)
            nyiso_weather_df["region"] = "NYISO"
            nyiso_weather_df["data_source"] = "synthetic"
            upload_to_s3(nyiso_weather_df, bucket, nyiso_weather_key, s3_client)
        else:
            print("🔄 Fetching NYISO zone-based weather data...")
            try:
                # Fetch weather for all 11 NYISO zones and create population-weighted average
                nyiso_weather_df = fetch_nyiso_zone_weather_data(
                    days=days,
                    zones=None,  # All zones
                    aggregate_method="population_weighted"
                )
                upload_to_s3(nyiso_weather_df, bucket, nyiso_weather_key, s3_client)
            except Exception as e:
                print(f"❌ Failed to fetch NYISO zone weather data: {e}")
                print("💡 Consider using synthetic weather mode: --synthetic-weather")
                print("   Or check Meteostat package installation")
                raise
    
    # CAISO zone-based weather (for accurate power correlation)
    caiso_weather_key = f"raw/weather/caiso_zones/{data_type}_{years}y.parquet"

    if not force and check_s3_object_exists(bucket, caiso_weather_key, s3_client):
        print(f"⏭️  CAISO zone weather data already exists: s3://{bucket}/{caiso_weather_key}")
    else:
        if use_synthetic:
            print("🔄 Generating synthetic CAISO weather data...")
            caiso_weather_df = generate_synthetic_weather_data(days=days)
            caiso_weather_df["region"] = "CAISO"
            caiso_weather_df["data_source"] = "synthetic"
            upload_to_s3(caiso_weather_df, bucket, caiso_weather_key, s3_client)
        else:
            print("🔄 Fetching CAISO zone-based weather data...")
            try:
                # Fetch weather for all 8 CAISO zones and create load-weighted average
                caiso_weather_df = fetch_caiso_zone_weather_data(
                    days=days,
                    zones=None,  # All zones
                    aggregate_method="load_weighted"
                )
                upload_to_s3(caiso_weather_df, bucket, caiso_weather_key, s3_client)
            except Exception as e:
                print(f"❌ Failed to fetch CAISO zone weather data: {e}")
                print("💡 Consider using synthetic weather mode: --synthetic-weather")
                print("   Or check Meteostat package installation")
                raise


def list_s3_data(bucket: str, s3_client: Optional[boto3.client] = None) -> None:
    """List existing data in S3 bucket."""
    if s3_client is None:
        s3_client = get_s3_client()
    
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix="raw/")
        
        if 'Contents' not in response:
            print(f"📭 No data found in s3://{bucket}/raw/")
            return
        
        print(f"📋 Existing data in s3://{bucket}:")
        total_size = 0
        
        for obj in response['Contents']:
            size_mb = obj['Size'] / (1024 * 1024)
            total_size += size_mb
            modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M')
            print(f"   {obj['Key']} ({size_mb:.1f} MB, {modified})")
        
        print(f"📊 Total: {len(response['Contents'])} files, {total_size:.1f} MB")
        
    except ClientError as e:
        print(f"❌ Error listing S3 objects: {e}")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Pre-populate S3 with historical power and weather data")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--years", type=int, default=3, help="Years of historical data (default: 3)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing data")
    parser.add_argument("--power-only", action="store_true", help="Only fetch power data")
    parser.add_argument("--weather-only", action="store_true", help="Only fetch weather data")
    parser.add_argument("--list-only", action="store_true", help="Only list existing data")
    parser.add_argument("--synthetic-power", action="store_true", help="Use synthetic power data instead of real APIs")
    parser.add_argument("--synthetic-weather", action="store_true", help="Use synthetic weather data instead of real APIs")
    parser.add_argument("--noaa-token", help="NOAA API token for weather data")
    
    args = parser.parse_args()
    
    print(f"🚀 ML Power Nowcast - S3 Data Pre-population")
    print(f"📦 Target bucket: s3://{args.bucket}")
    
    s3_client = get_s3_client()
    
    if args.list_only:
        list_s3_data(args.bucket, s3_client)
        return
    
    if not args.weather_only:
        prepopulate_power_data(
            bucket=args.bucket,
            years=args.years,
            force=args.force,
            use_synthetic=args.synthetic_power,
            s3_client=s3_client
        )
    
    if not args.power_only:
        prepopulate_weather_data(
            bucket=args.bucket,
            years=args.years,
            force=args.force,
            use_synthetic=args.synthetic_weather,
            noaa_token=args.noaa_token,
            s3_client=s3_client
        )
    
    print("\n📋 Final S3 contents:")
    list_s3_data(args.bucket, s3_client)
    print("\n✅ Data pre-population complete!")


if __name__ == "__main__":
    main()
