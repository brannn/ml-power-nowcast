#!/usr/bin/env python3
"""
Power demand data ingestion module.

Pulls power demand data from public APIs including NYISO and CAISO.
Supports both real data from APIs and synthetic data generation for development.
"""

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import mlflow
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup


def generate_synthetic_power_data(days: int = 730) -> pd.DataFrame:
    """
    Generate synthetic power demand data for development/testing.

    Creates realistic power demand patterns with:
    - Daily cycles (higher during day, lower at night)
    - Weekly cycles (lower on weekends)
    - Seasonal trends
    - Random noise

    Args:
        days: Number of days of historical data to generate

    Returns:
        DataFrame with columns: timestamp, load, region, data_source

    Raises:
        ValueError: If days is less than or equal to 0
    """
    if days <= 0:
        raise ValueError(f"Days must be positive, got {days}")

    print(f"Generating synthetic power demand data for {days} days...")
    
    # Create hourly timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    timestamps = pd.date_range(start=start_time, end=end_time, freq="h")

    # Base load pattern (MW)
    base_load = 15000  # Base load around 15 GW

    # Daily cycle (peak around 2 PM, low around 4 AM)
    daily_cycle = 3000 * np.sin(2 * np.pi * (timestamps.hour - 6) / 24)

    # Weekly cycle (lower on weekends)
    weekly_cycle = -1000 * ((timestamps.dayofweek >= 5).astype(int))

    # Seasonal trend (higher in summer/winter for AC/heating)
    day_of_year = timestamps.dayofyear
    seasonal_cycle = 2000 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

    # Random noise
    np.random.seed(42)  # For reproducibility
    noise = np.random.normal(0, 500, len(timestamps))

    # Combine all components
    load = base_load + daily_cycle + weekly_cycle + seasonal_cycle + noise

    # Ensure no negative values
    load = np.maximum(load, 1000)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "load": load,
        "region": "SYNTHETIC",
        "data_source": "generated"
    })
    
    return df


def fetch_nyiso_data(days: int = 365) -> pd.DataFrame:
    """
    Fetch real power demand data from NYISO P-58B 'pal' CSV files.

    NYISO publishes daily CSV files with 5-minute real-time actual load data
    by zone. This function aggregates all zones to produce statewide (NYCA) totals.

    Args:
        days: Number of days of historical data to fetch

    Returns:
        DataFrame with columns: timestamp, load, region, data_source
        - timestamp: UTC datetime
        - load: Statewide load in MW (sum of all zones)
        - region: 'NYISO'
        - data_source: 'nyiso_p58b_pal'

    Raises:
        RuntimeError: If no data could be retrieved from NYISO
        requests.RequestException: If API requests fail consistently
    """
    print(f"Fetching NYISO statewide load data for {days} days...")

    # NYISO P-58B Real-Time Actual Load CSV endpoint
    base_url = "https://mis.nyiso.com/public/csv/pal/"

    # Calculate date range using UTC
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)

    # Generate date range for daily CSV files
    day_list = pd.date_range(start=start_dt.date(), end=end_dt.date(), freq="D", tz="UTC")

    frames = []
    successful_days = 0

    print(f"Requesting data from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")

    for day in day_list:
        date_str = day.strftime('%Y%m%d')
        url = f"{base_url}{date_str}pal.csv"

        try:
            print(f"Fetching NYISO data for {day.strftime('%Y-%m-%d')}...")
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                print(f"Warning: HTTP {response.status_code} for {date_str}")
                continue

            # Parse CSV data
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))

            # Validate required columns
            timestamp_col = 'Time Stamp' if 'Time Stamp' in df.columns else None
            if timestamp_col is None or 'Load' not in df.columns:
                print(f"Warning: Missing required columns in {date_str}")
                continue

            # Convert timestamp and aggregate all zones per timestamp
            # This gives us true statewide (NYCA) load, not just one zone
            aggregated = (
                df[[timestamp_col, 'Load']]
                .assign(**{timestamp_col: pd.to_datetime(df[timestamp_col])})
                .groupby(timestamp_col, as_index=False)['Load'].sum()
                .rename(columns={timestamp_col: 'timestamp', 'Load': 'load'})
            )

            if not aggregated.empty:
                frames.append(aggregated)
                successful_days += 1

        except requests.RequestException as e:
            print(f"Warning: Request failed for {date_str}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Error processing {date_str}: {e}")
            continue

    print(f"Successfully processed {successful_days} days of NYISO data")

    # Check if we got any data
    if not frames:
        raise RuntimeError("NYISO: no data retrieved; check P-58B availability or date range.")

    # Combine all daily data frames
    result_df = pd.concat(frames, ignore_index=True).dropna()
    result_df = result_df.sort_values('timestamp').reset_index(drop=True)

    # Add metadata
    result_df['region'] = 'NYISO'
    result_df['data_source'] = 'nyiso_p58b_pal'

    # Ensure proper column order and types
    result_df = result_df[['timestamp', 'load', 'region', 'data_source']].copy()

    print(f"Successfully fetched {len(result_df)} NYISO records spanning {successful_days} days")
    return result_df





def fetch_caiso_data(days: int = 365) -> pd.DataFrame:
    """
    Fetch real actual power demand data from CAISO OASIS API using chunked requests.

    CAISO provides actual system load data through their OASIS SingleZip API.
    Uses SLD (System Load Demand) endpoint for actual historical load data,
    not forecasts. Data retention is approximately 39 months.

    Args:
        days: Number of days of historical data to fetch

    Returns:
        DataFrame with columns: timestamp, load, resource_name, zone, region, data_source
        - timestamp: UTC datetime
        - load: Actual system/zone demand in MW
        - resource_name: CAISO resource identifier
        - zone: Mapped CAISO zone (SYSTEM, NP15, SP15, etc.)
        - region: 'CAISO'
        - data_source: 'caiso_oasis_sld'

    Raises:
        RuntimeError: If no data could be retrieved from CAISO OASIS
        requests.RequestException: If API requests fail consistently
    """
    print(f"Fetching CAISO actual system demand data for {days} days...")

    # CAISO OASIS API endpoint
    base_url = "https://oasis.caiso.com/oasisapi/SingleZip"

    # Calculate date range using UTC
    end_utc = datetime.now(timezone.utc)
    start_utc = end_utc - timedelta(days=days)

    # Chunk requests to avoid API limits (14-day chunks to reduce request count)
    chunk_days = 14
    frames = []

    print(f"Requesting data from {start_utc.strftime('%Y-%m-%d')} to {end_utc.strftime('%Y-%m-%d')}")
    print(f"Using {chunk_days}-day chunks with 15-second rate limiting for API reliability")

    current_start = start_utc
    chunk_count = 0
    while current_start < end_utc:
        chunk_end = min(current_start + timedelta(days=chunk_days), end_utc)
        chunk_count += 1

        # CAISO API parameters for actual system load demand
        # Use SLD_FCST but filter for actual load data items, not forecasts
        params = {
            "queryname": "SLD_FCST",  # System Load Demand family (includes actual data)
            "startdatetime": current_start.strftime("%Y%m%dT%H:%M-0000"),
            "enddatetime": chunk_end.strftime("%Y%m%dT%H:%M-0000"),
            "version": "1",
            "market_run_id": "RTM",  # Real-Time Market for actual data
        }

        try:
            print(f"Fetching CAISO chunk {chunk_count}: {current_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")

            # Rate limiting: wait between requests to respect API limits
            if chunk_count > 1:
                print("⏳ Waiting 15 seconds to respect API rate limits...")
                time.sleep(15)

            # Retry logic for rate limiting
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                response = requests.get(base_url, params=params, timeout=90)

                if response.status_code == 429:
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 5, 10, 20 seconds
                    print(f"⚠️  Rate limited (429). Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    break  # Success or other error

            if response.status_code == 200 and response.content:
                # CAISO returns ZIP file with XML data
                import zipfile
                from io import BytesIO

                with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                    for xml_filename in zip_file.namelist():
                        if xml_filename.lower().endswith(".xml"):
                            with zip_file.open(xml_filename) as xml_file:
                                # Parse XML content
                                soup = BeautifulSoup(xml_file.read(), 'xml')

                                # Check for errors first
                                error = soup.find(['error', 'ERROR'])
                                if error:
                                    code = error.find(['err_code', 'ERR_CODE'])
                                    desc = error.find(['err_desc', 'ERR_DESC'])
                                    print(f"⚠️  CAISO API error: {code.text if code else 'Unknown'} - {desc.text if desc else 'Unknown'}")
                                    continue

                                # Parse data elements
                                data_elements = soup.find_all(['REPORT_DATA', 'report_data'])
                                chunk_records = []

                                for element in data_elements:
                                    # Look for actual system load data (5-min RTM)
                                    data_item = element.find(['DATA_ITEM', 'data_item'])
                                    resource_name = element.find(['RESOURCE_NAME', 'resource_name'])

                                    # Accept actual load data - try both forecast and actual data items
                                    # SYS_FCST_5MIN_MW might include actual data in RTM market
                                    if (data_item and data_item.text in ['SYS_FCST_5MIN_MW', 'SYS_LOAD_5MIN_MW', 'LOAD_5MIN_MW'] and
                                        resource_name and resource_name.text):

                                        # Extract timestamp and value
                                        timestamp_elem = element.find(['INTERVAL_START_GMT', 'interval_start_gmt'])
                                        value_elem = element.find(['VALUE', 'value'])

                                        if timestamp_elem and value_elem:
                                            try:
                                                timestamp = pd.to_datetime(timestamp_elem.text)
                                                load_mw = float(value_elem.text)
                                                resource = resource_name.text

                                                chunk_records.append({
                                                    'timestamp': timestamp,
                                                    'load': load_mw,
                                                    'resource_name': resource
                                                })
                                            except (ValueError, TypeError) as e:
                                                print(f"⚠️  Error parsing CAISO data element: {e}")
                                                continue

                                if chunk_records:
                                    chunk_data = pd.DataFrame(chunk_records)
                                    frames.append(chunk_data)
            else:
                print(f"Warning: CAISO API returned HTTP {response.status_code} for chunk")

        except requests.RequestException as e:
            print(f"Warning: Request failed for chunk: {e}")
            continue
        except Exception as e:
            print(f"Warning: Error processing chunk: {e}")
            continue

        # Move to next chunk
        current_start = chunk_end

    # Check if we got any data
    if not frames:
        raise RuntimeError("CAISO OASIS fetch returned no data. Consider Today's Outlook CSV.")

    # Combine all chunk data
    if not frames:
        raise RuntimeError("No data retrieved from CAISO OASIS API")

    result_df = pd.concat(frames, ignore_index=True).dropna()
    result_df = result_df.sort_values(["timestamp", "resource_name"]).reset_index(drop=True)

    # Map CAISO resource names to our zone configuration
    from src.config.caiso_zones import CAISO_ZONES

    # Create mapping from CAISO resource names to our zone names
    # Based on CAISO OASIS resource identifiers and geographic territories
    # FIXED MAPPING: Use only primary utility data sources for clean zone modeling
    resource_to_zone = {
        # System-wide and major utility TAC areas (PRIMARY SOURCES ONLY)
        'CA ISO-TAC': 'SYSTEM',     # California ISO system total
        'SDGE-TAC': 'SDGE',         # San Diego Gas & Electric
        'SCE-TAC': 'SCE',           # Southern California Edison (PRIMARY ONLY)
        'PGE-TAC': 'NP15',          # PG&E North of Path 15 (PRIMARY ONLY)
        'SMUD-TAC': 'SMUD',         # Sacramento Municipal Utility District

        # REMOVED PROBLEMATIC MIXED SOURCES:
        # 'MWD-TAC': 'SCE',         # Metropolitan Water District - REMOVED (water pumping, not utility load)
        # 'VEA-TAC': 'SCE',         # Ventura County - REMOVED (small utility, creates noise)
        # 'BANC': 'NP15',           # BANC general - REMOVED (overlaps with PGE-TAC)
        # 'PGE': 'NP15',            # PG&E general - REMOVED (overlaps with PGE-TAC)
        # 'SCL': 'NP15',            # Seattle City Light - REMOVED (wrong state!)
        # 'BANCRDNG': 'NP15',       # BANC Redding - REMOVED (small utility)
        # 'BANCWASN': 'NP15',       # BANC Western Area - REMOVED (small utility)
        # 'BANCRSVL': 'SMUD',       # BANC Roseville - REMOVED (small utility)

        # Keep only clean, primary utility sources
        'BANCSMUD': 'SMUD',         # BANC - Sacramento Municipal Utility District (primary SMUD source)
        'BANCMID': 'PGE_VALLEY',    # BANC - Modesto Irrigation District (Central Valley)
        'LADWP': 'SP15',            # Los Angeles Department of Water and Power

        # Note: Many other resources (AZPS, NEVP, BPAT, etc.) are outside California
        # and will remain unmapped (zone = None) as they're not CAISO load zones
    }

    # Map resource names to zones
    result_df['zone'] = result_df['resource_name'].map(resource_to_zone)

    # Add metadata
    result_df["region"] = "CAISO"
    result_df["data_source"] = "caiso_oasis_sld"

    # Show what resource names we found
    unique_resources = result_df['resource_name'].unique()
    mapped_resources = result_df[result_df['zone'].notna()]['resource_name'].unique()
    unmapped_resources = result_df[result_df['zone'].isna()]['resource_name'].unique()

    print(f"📊 Found {len(unique_resources)} unique CAISO resource names:")
    print(f"   ✅ Mapped: {list(mapped_resources)}")
    if len(unmapped_resources) > 0:
        print(f"   ❓ Unmapped: {list(unmapped_resources)}")

    # Ensure proper column order
    result_df = result_df[["timestamp", "load", "resource_name", "zone", "region", "data_source"]].copy()

    print(f"Successfully fetched {len(result_df)} CAISO records from {len(frames)} chunks")
    return result_df


def save_power_data(df: pd.DataFrame, output_path: str = "data/raw/power.parquet") -> str:
    """
    Save power data to parquet file with MLflow logging.

    Args:
        df: DataFrame containing power demand data
        output_path: Path where to save the parquet file

    Returns:
        Path to the saved file
    """
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Save to parquet
    df.to_parquet(output_path, index=False)

    print(f"Saved {len(df)} power demand records to {output_path}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Load range: {df['load'].min():.0f} - {df['load'].max():.0f} MW")

    return output_path


def main() -> None:
    """Main function to handle command line arguments and orchestrate data ingestion."""
    parser = argparse.ArgumentParser(description="Pull power demand data")
    parser.add_argument(
        "--days",
        type=int,
        default=730,
        help="Number of days of historical data to pull (default: 2 years for deep learning)"
    )
    parser.add_argument(
        "--region",
        type=str,
        default="synthetic",
        choices=["synthetic", "nyiso", "caiso"],
        help="Data source region"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/power.parquet",
        help="Output file path"
    )

    args = parser.parse_args()

    # Start MLflow run for tracking
    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"ingest_power_{args.region}"):

        # Log parameters
        mlflow.log_params({
            "days": args.days,
            "region": args.region,
            "output_path": args.output
        })

        # Fetch data based on region
        try:
            if args.region == "synthetic":
                df = generate_synthetic_power_data(args.days)
            elif args.region == "nyiso":
                df = fetch_nyiso_data(args.days)
            elif args.region == "caiso":
                df = fetch_caiso_data(args.days)
            else:
                raise ValueError(f"Unknown region: {args.region}")
        except Exception as e:
            print(f"Error during data ingestion: {e}")
            mlflow.log_param("error", str(e))
            raise

        # Save data
        output_path = save_power_data(df, args.output)

        # Log metrics and artifacts
        mlflow.log_metrics({
            "records_count": len(df),
            "days_span": (df["timestamp"].max() - df["timestamp"].min()).days,
            "avg_load_mw": float(df["load"].mean()),
            "max_load_mw": float(df["load"].max()),
            "min_load_mw": float(df["load"].min())
        })

        # Log the data file as artifact
        mlflow.log_artifact(output_path)

        print(f"\nPower data ingestion completed successfully!")
        print(f"MLflow run logged with {len(df)} records")


if __name__ == "__main__":
    main()
