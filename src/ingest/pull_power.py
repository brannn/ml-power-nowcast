#!/usr/bin/env python3
"""
Power demand data ingestion module.

Pulls power demand data from public APIs including NYISO and CAISO.
Supports both real data from APIs and synthetic data generation for development.
"""

import argparse
from datetime import datetime, timedelta
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
    timestamps = pd.date_range(start=start_time, end=end_time, freq="H")

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
    Fetch real power demand data from NYISO OASIS API.

    NYISO provides public access to real-time and historical load data
    through their OASIS (Open Access Same-time Information System) API.

    Args:
        days: Number of days of historical data to fetch

    Returns:
        DataFrame with power demand data from NYISO

    Raises:
        requests.RequestException: If API request fails
        ValueError: If API response is invalid
    """
    print(f"Fetching NYISO data for {days} days...")

    # NYISO OASIS API endpoint for real-time actual load
    # Note: NYISO provides data through their OASIS system, but the public CSV
    # endpoints may have limited historical availability
    base_url = "http://mis.nyiso.com/public/csv/pal/"

    # Calculate date range - limit to recent data for better success rate
    end_date = datetime.now()
    start_date = end_date - timedelta(days=min(days, 30))  # Limit to 30 days for API reliability

    all_data = []
    successful_days = 0

    try:
        # NYISO provides daily CSV files, so we need to fetch multiple files
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y%m%d")
            url = f"{base_url}{date_str}pal.csv"

            print(f"Fetching NYISO data for {current_date.strftime('%Y-%m-%d')}...")

            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    # Parse CSV data
                    from io import StringIO
                    csv_data = pd.read_csv(StringIO(response.text))

                    # NYISO CSV format: Time Stamp, Name, PTID, Load
                    if not csv_data.empty and 'Load' in csv_data.columns:
                        # Filter for statewide load (PTID 61757 is NYISO total)
                        statewide_data = csv_data[csv_data['PTID'] == 61757].copy()
                        if not statewide_data.empty:
                            all_data.append(statewide_data)
                            successful_days += 1
                else:
                    print(f"Warning: Could not fetch data for {date_str} (HTTP {response.status_code})")
            except requests.RequestException as e:
                print(f"Warning: Request failed for {date_str}: {e}")

            current_date += timedelta(days=1)

        print(f"Successfully fetched {successful_days} days of NYISO data")

    except requests.RequestException as e:
        print(f"Error fetching NYISO data: {e}")
        raise RuntimeError(f"Failed to fetch NYISO data: {e}")

    if not all_data:
        print("No NYISO data retrieved from API")
        raise RuntimeError("NYISO API returned no data for the requested date range")

    if successful_days < days * 0.1:  # Less than 10% success rate
        print(f"Warning: Low success rate ({successful_days}/{days} days)")
        print("Consider using a shorter date range or checking NYISO API status")

    # Combine all data
    df = pd.concat(all_data, ignore_index=True)

    # Standardize column names and format
    df = df.rename(columns={'Time Stamp': 'timestamp', 'Load': 'load'})
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['region'] = 'NYISO'
    df['data_source'] = 'nyiso_oasis_api'

    # Select only needed columns
    df = df[['timestamp', 'load', 'region', 'data_source']].copy()

    print(f"Successfully fetched {len(df)} NYISO records")
    return df


def _fallback_to_synthetic(region: str, days: int) -> pd.DataFrame:
    """
    Fallback function to generate synthetic data when API fails.

    Args:
        region: Region name for labeling
        days: Number of days to generate

    Returns:
        DataFrame with synthetic data labeled with the specified region
    """
    df = generate_synthetic_power_data(days)
    df["region"] = region
    df["data_source"] = f"{region.lower()}_synthetic_fallback"
    return df


def fetch_caiso_data(days: int = 365) -> pd.DataFrame:
    """
    Fetch real power demand data from CAISO OASIS API.

    CAISO provides public access to real-time and historical load data
    through their OASIS (Open Access Same-time Information System) API.

    Args:
        days: Number of days of historical data to fetch

    Returns:
        DataFrame with power demand data from CAISO

    Raises:
        requests.RequestException: If API request fails
        ValueError: If API response is invalid
    """
    print(f"Fetching CAISO data for {days} days...")

    # CAISO OASIS API endpoint for system load
    # Note: CAISO OASIS API can be unreliable for large date ranges
    base_url = "http://oasis.caiso.com/oasisapi/SingleZip"

    # Calculate date range - limit to recent data for better success rate
    end_date = datetime.now()
    start_date = end_date - timedelta(days=min(days, 7))  # Limit to 7 days for API reliability

    try:
        # CAISO API parameters for actual system load
        params = {
            'queryname': 'SLD_RTO',  # System Load Demand Real Time Operations
            'startdatetime': start_date.strftime('%Y%m%dT00:00-0000'),
            'enddatetime': end_date.strftime('%Y%m%dT23:59-0000'),
            'version': '1'
        }

        print(f"Requesting CAISO data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
        print(f"API URL: {base_url}")
        print(f"Parameters: {params}")

        response = requests.get(base_url, params=params, timeout=60)

        if response.status_code != 200:
            print(f"CAISO API returned HTTP {response.status_code}")
            return _fallback_to_synthetic("CAISO", days)

        # CAISO returns ZIP file with CSV data
        import zipfile
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
            # Extract CSV file (usually only one file in the ZIP)
            csv_filename = zip_file.namelist()[0]
            with zip_file.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file)

        if df.empty:
            print("CAISO API returned empty data")
            return _fallback_to_synthetic("CAISO", days)

        # CAISO CSV format varies, but typically includes INTERVALSTARTTIME_GMT and MW columns
        # Standardize column names
        timestamp_cols = ['INTERVALSTARTTIME_GMT', 'INTERVALSTARTTIME', 'OPR_DT']
        load_cols = ['MW', 'LOAD', 'DEMAND']

        timestamp_col = None
        load_col = None

        for col in timestamp_cols:
            if col in df.columns:
                timestamp_col = col
                break

        for col in load_cols:
            if col in df.columns:
                load_col = col
                break

        if not timestamp_col or not load_col:
            print(f"Could not find required columns in CAISO data. Available: {list(df.columns)}")
            return _fallback_to_synthetic("CAISO", days)

        # Create standardized DataFrame
        result_df = pd.DataFrame({
            'timestamp': pd.to_datetime(df[timestamp_col]),
            'load': pd.to_numeric(df[load_col], errors='coerce'),
            'region': 'CAISO',
            'data_source': 'caiso_oasis_api'
        })

        # Remove any rows with invalid data
        result_df = result_df.dropna().copy()

        print(f"Successfully fetched {len(result_df)} CAISO records")
        return result_df

    except Exception as e:
        print(f"Error fetching CAISO data: {e}")
        raise RuntimeError(f"Failed to fetch CAISO data: {e}")


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
