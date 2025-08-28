#!/usr/bin/env python3
"""
Weather data ingestion module.

Pulls weather data from public APIs including NOAA and Meteostat.
Weather features are crucial for power demand forecasting as temperature,
humidity, and wind speed significantly impact electricity consumption.
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import mlflow
import numpy as np
import pandas as pd
import requests


def generate_synthetic_weather_data(days: int = 730) -> pd.DataFrame:
    """
    Generate synthetic weather data for development/testing.

    Creates realistic weather patterns with:
    - Seasonal temperature cycles
    - Daily temperature variations
    - Humidity patterns correlated with temperature
    - Wind speed variations
    - Random weather noise

    Args:
        days: Number of days of historical data to generate

    Returns:
        DataFrame with columns: timestamp, temp_c, humidity, wind_speed, region, data_source

    Raises:
        ValueError: If days is less than or equal to 0
    """
    if days <= 0:
        raise ValueError(f"Days must be positive, got {days}")

    print(f"Generating synthetic weather data for {days} days...")

    # Create hourly timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    timestamps = pd.date_range(start=start_time, end=end_time, freq="H")

    # Base temperature (Celsius) - around 15°C average
    base_temp = 15.0

    # Seasonal cycle (warmer in summer, colder in winter)
    day_of_year = timestamps.dayofyear
    seasonal_temp = 15.0 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

    # Daily cycle (warmer during day, cooler at night)
    daily_temp = 8.0 * np.sin(2 * np.pi * (timestamps.hour - 6) / 24)

    # Random temperature noise
    np.random.seed(42)  # For reproducibility
    temp_noise = np.random.normal(0, 3, len(timestamps))

    # Combine temperature components
    temp_c = base_temp + seasonal_temp + daily_temp + temp_noise

    # Humidity (inversely correlated with temperature, with noise)
    base_humidity = 60.0
    humidity_temp_effect = -1.5 * (temp_c - base_temp)
    humidity_noise = np.random.normal(0, 10, len(timestamps))
    humidity = np.clip(base_humidity + humidity_temp_effect + humidity_noise, 10, 95)

    # Wind speed (random with some seasonal variation)
    base_wind = 5.0
    seasonal_wind = 2.0 * np.sin(2 * np.pi * (day_of_year - 30) / 365)
    wind_noise = np.random.exponential(3, len(timestamps))
    wind_speed = np.maximum(base_wind + seasonal_wind + wind_noise, 0)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "temp_c": temp_c,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "region": "SYNTHETIC",
        "data_source": "generated"
    })

    return df


def fetch_noaa_weather_data(
    days: int = 365,
    station_id: str = "KNYC",  # NYC Central Park
    api_token: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch weather data from NOAA Climate Data Online API.

    NOAA provides comprehensive weather data, but requires API token
    for higher rate limits and historical data access.

    Args:
        days: Number of days of historical data to fetch
        station_id: NOAA station identifier
        api_token: NOAA API token (optional, but recommended)

    Returns:
        DataFrame with weather data from NOAA

    Raises:
        requests.RequestException: If API request fails
        ValueError: If API response is invalid
    """
    print(f"Fetching NOAA weather data for {days} days from station {station_id}...")

    if not api_token:
        print("Warning: No NOAA API token provided. Using synthetic data.")
        print("Get a free token at: https://www.ncdc.noaa.gov/cdo-web/token")
        return _fallback_to_synthetic_weather("NOAA", days)

    # NOAA Climate Data Online API endpoint
    base_url = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        headers = {"token": api_token}
        params = {
            "datasetid": "GHCND",  # Global Historical Climatology Network Daily
            "stationid": f"GHCND:{station_id}",
            "startdate": start_date.strftime("%Y-%m-%d"),
            "enddate": end_date.strftime("%Y-%m-%d"),
            "datatypeid": "TMAX,TMIN,PRCP",  # Max temp, min temp, precipitation
            "limit": 1000,
            "units": "metric"
        }

        response = requests.get(base_url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            print(f"NOAA API returned HTTP {response.status_code}")
            return _fallback_to_synthetic_weather("NOAA", days)

        data = response.json()

        if "results" not in data or not data["results"]:
            print("NOAA API returned no data")
            return _fallback_to_synthetic_weather("NOAA", days)

        # Process NOAA data format
        records = []
        for record in data["results"]:
            records.append({
                "date": record["date"],
                "datatype": record["datatype"],
                "value": record["value"]
            })

        df = pd.DataFrame(records)

        # Pivot to get temperature columns
        df_pivot = df.pivot(index="date", columns="datatype", values="value").reset_index()
        df_pivot["timestamp"] = pd.to_datetime(df_pivot["date"])

        # Calculate average temperature from min/max
        if "TMAX" in df_pivot.columns and "TMIN" in df_pivot.columns:
            df_pivot["temp_c"] = (df_pivot["TMAX"] + df_pivot["TMIN"]) / 2 / 10  # Convert from tenths
        else:
            print("Missing temperature data in NOAA response")
            return _fallback_to_synthetic_weather("NOAA", days)

        # Add synthetic humidity and wind (NOAA daily data doesn't include these)
        np.random.seed(42)
        df_pivot["humidity"] = np.random.normal(60, 15, len(df_pivot))
        df_pivot["wind_speed"] = np.random.exponential(5, len(df_pivot))

        # Standardize format
        result_df = df_pivot[["timestamp", "temp_c", "humidity", "wind_speed"]].copy()
        result_df["region"] = "NOAA"
        result_df["data_source"] = "noaa_cdo_api"

        print(f"Successfully fetched {len(result_df)} NOAA weather records")
        return result_df

    except Exception as e:
        print(f"Error fetching NOAA data: {e}")
        print("Falling back to synthetic weather data...")
        return _fallback_to_synthetic_weather("NOAA", days)


def fetch_meteostat_data(
    days: int = 365,
    latitude: float = 40.7128,  # NYC coordinates
    longitude: float = -74.0060
) -> pd.DataFrame:
    """
    Fetch weather data using Meteostat Python library.

    Meteostat provides free access to historical weather data
    from weather stations worldwide.

    Args:
        days: Number of days of historical data to fetch
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        DataFrame with weather data from Meteostat

    Note:
        This function requires the meteostat package to be installed.
        Falls back to synthetic data if package is not available.
    """
    print(f"Fetching Meteostat weather data for {days} days at ({latitude}, {longitude})...")

    try:
        from meteostat import Point, Hourly
        
        # Define location
        location = Point(latitude, longitude)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Fetch hourly data
        data = Hourly(location, start_date, end_date)
        df = data.fetch()
        
        if df.empty:
            print("Meteostat returned no data")
            return _fallback_to_synthetic_weather("METEOSTAT", days)
        
        # Meteostat columns: temp, rhum, wspd, etc.
        df = df.reset_index()
        df = df.rename(columns={
            'time': 'timestamp',
            'temp': 'temp_c',
            'rhum': 'humidity',
            'wspd': 'wind_speed'
        })
        
        # Select and clean data
        result_df = df[['timestamp', 'temp_c', 'humidity', 'wind_speed']].copy()
        result_df = result_df.dropna()
        
        result_df['region'] = 'METEOSTAT'
        result_df['data_source'] = 'meteostat_api'
        
        print(f"Successfully fetched {len(result_df)} Meteostat weather records")
        return result_df
        
    except ImportError:
        print("Meteostat package not installed. Install with: pip install meteostat")
        return _fallback_to_synthetic_weather("METEOSTAT", days)
    except Exception as e:
        print(f"Error fetching Meteostat data: {e}")
        print("Falling back to synthetic weather data...")
        return _fallback_to_synthetic_weather("METEOSTAT", days)


def _fallback_to_synthetic_weather(region: str, days: int) -> pd.DataFrame:
    """
    Fallback function to generate synthetic weather data when API fails.

    Args:
        region: Region name for labeling
        days: Number of days to generate

    Returns:
        DataFrame with synthetic weather data labeled with the specified region
    """
    df = generate_synthetic_weather_data(days)
    df["region"] = region
    df["data_source"] = f"{region.lower()}_synthetic_fallback"
    return df


def save_weather_data(df: pd.DataFrame, output_path: str = "data/raw/weather.parquet") -> str:
    """
    Save weather data to parquet file with MLflow logging.

    Args:
        df: DataFrame containing weather data
        output_path: Path where to save the parquet file

    Returns:
        Path to the saved file
    """
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Save to parquet
    df.to_parquet(output_path, index=False)

    print(f"Saved {len(df)} weather records to {output_path}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Temperature range: {df['temp_c'].min():.1f}°C - {df['temp_c'].max():.1f}°C")

    return output_path


def main() -> None:
    """Main function to handle command line arguments and orchestrate weather data ingestion."""
    parser = argparse.ArgumentParser(description="Pull weather data")
    parser.add_argument(
        "--days",
        type=int,
        default=730,
        help="Number of days of historical data to pull (default: 2 years for deep learning)"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="synthetic",
        choices=["synthetic", "noaa", "meteostat"],
        help="Weather data source"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/weather.parquet",
        help="Output file path"
    )
    parser.add_argument(
        "--noaa-token",
        type=str,
        help="NOAA API token (required for NOAA data)"
    )
    parser.add_argument(
        "--latitude",
        type=float,
        default=40.7128,
        help="Latitude for weather data (default: NYC)"
    )
    parser.add_argument(
        "--longitude",
        type=float,
        default=-74.0060,
        help="Longitude for weather data (default: NYC)"
    )

    args = parser.parse_args()

    # Start MLflow run for tracking
    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"ingest_weather_{args.source}"):

        # Log parameters
        mlflow.log_params({
            "days": args.days,
            "source": args.source,
            "output_path": args.output,
            "latitude": args.latitude,
            "longitude": args.longitude
        })

        # Fetch data based on source
        try:
            if args.source == "synthetic":
                df = generate_synthetic_weather_data(args.days)
            elif args.source == "noaa":
                df = fetch_noaa_weather_data(args.days, api_token=args.noaa_token)
            elif args.source == "meteostat":
                df = fetch_meteostat_data(args.days, args.latitude, args.longitude)
            else:
                raise ValueError(f"Unknown weather source: {args.source}")
        except Exception as e:
            print(f"Error during weather data ingestion: {e}")
            mlflow.log_param("error", str(e))
            raise

        # Save data
        output_path = save_weather_data(df, args.output)

        # Log metrics and artifacts
        mlflow.log_metrics({
            "records_count": len(df),
            "days_span": (df["timestamp"].max() - df["timestamp"].min()).days,
            "avg_temp_c": float(df["temp_c"].mean()),
            "max_temp_c": float(df["temp_c"].max()),
            "min_temp_c": float(df["temp_c"].min()),
            "avg_humidity": float(df["humidity"].mean()),
            "avg_wind_speed": float(df["wind_speed"].mean())
        })

        # Log the data file as artifact
        mlflow.log_artifact(output_path)

        print(f"\nWeather data ingestion completed successfully!")
        print(f"MLflow run logged with {len(df)} records")


if __name__ == "__main__":
    main()
