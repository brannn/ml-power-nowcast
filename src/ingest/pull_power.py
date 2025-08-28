#!/usr/bin/env python3
"""
Power demand data ingestion module.

Pulls power demand data from public APIs including NYISO and CAISO.
Supports both real data from APIs and synthetic data generation for development.
"""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import mlflow
import numpy as np
import pandas as pd
import requests


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
    Fetch real power demand data from CAISO OASIS API using chunked requests.

    CAISO provides system demand data through their OASIS SingleZip API.
    Data retention is approximately 39 months. This function uses chunked
    requests to handle large date ranges reliably.

    Args:
        days: Number of days of historical data to fetch

    Returns:
        DataFrame with columns: timestamp, load, region, data_source
        - timestamp: UTC datetime
        - load: System demand in MW
        - region: 'CAISO'
        - data_source: 'caiso_oasis_sld'

    Raises:
        RuntimeError: If no data could be retrieved from CAISO OASIS
        requests.RequestException: If API requests fail consistently
    """
    print(f"Fetching CAISO system demand data for {days} days...")

    # CAISO OASIS API endpoint
    base_url = "https://oasis.caiso.com/oasisapi/SingleZip"

    # Calculate date range using UTC
    end_utc = datetime.now(timezone.utc)
    start_utc = end_utc - timedelta(days=days)

    # Chunk requests to avoid API limits (7-day chunks recommended)
    chunk_days = 7
    frames = []

    print(f"Requesting data from {start_utc.strftime('%Y-%m-%d')} to {end_utc.strftime('%Y-%m-%d')}")
    print(f"Using {chunk_days}-day chunks for API reliability")

    current_start = start_utc
    while current_start < end_utc:
        chunk_end = min(current_start + timedelta(days=chunk_days), end_utc)

        # CAISO API parameters for system load demand forecast (actual data)
        params = {
            "queryname": "SLD_FCST",  # System Load Demand Forecast family
            "startdatetime": current_start.strftime("%Y%m%dT%H:%M-0000"),
            "enddatetime": chunk_end.strftime("%Y%m%dT%H:%M-0000"),
            "version": "1",
            "granularity": "15MIN",  # 15-minute granularity
            "market_run_id": "ACTUAL",  # Actual data, not forecast
        }

        try:
            print(f"Fetching CAISO chunk: {current_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")
            response = requests.get(base_url, params=params, timeout=90)

            if response.status_code == 200 and response.content:
                # CAISO returns ZIP file with CSV data
                import zipfile
                from io import BytesIO

                with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                    for csv_filename in zip_file.namelist():
                        if csv_filename.lower().endswith(".csv"):
                            with zip_file.open(csv_filename) as csv_file:
                                df = pd.read_csv(csv_file)

                                # Look for standard CAISO columns
                                if "INTERVALSTARTTIME_GMT" in df.columns and "MW" in df.columns:
                                    chunk_data = pd.DataFrame({
                                        "timestamp": pd.to_datetime(df["INTERVALSTARTTIME_GMT"]),
                                        "load": pd.to_numeric(df["MW"], errors="coerce")
                                    }).dropna()

                                    if not chunk_data.empty:
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
    result_df = pd.concat(frames, ignore_index=True).dropna()
    result_df = result_df.sort_values("timestamp").reset_index(drop=True)

    # Add metadata
    result_df["region"] = "CAISO"
    result_df["data_source"] = "caiso_oasis_sld"

    # Ensure proper column order
    result_df = result_df[["timestamp", "load", "region", "data_source"]].copy()

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
