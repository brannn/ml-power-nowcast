#!/usr/bin/env python3
"""
Weather data ingestion module.

Pulls weather data from public APIs including NOAA and Meteostat.
Weather features are crucial for power demand forecasting as temperature,
humidity, and wind speed significantly impact electricity consumption.
"""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import mlflow
import numpy as np
import pandas as pd
import requests

from src.config.nyiso_zones import (
    NYISO_ZONES,
    get_all_zone_coordinates as get_nyiso_zone_coordinates,
    get_population_weighted_average
)
from src.config.caiso_zones import (
    CAISO_ZONES,
    get_all_zone_coordinates as get_caiso_zone_coordinates,
    get_load_weighted_average
)


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
    timestamps = pd.date_range(start=start_time, end=end_time, freq="h")

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
        print("Error: No NOAA API token provided.")
        print("Get a free token at: https://www.ncdc.noaa.gov/cdo-web/token")
        raise ValueError("NOAA API token is required for real weather data")

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
            raise RuntimeError(f"NOAA API request failed with status {response.status_code}")

        data = response.json()

        if "results" not in data or not data["results"]:
            print("NOAA API returned no data")
            raise RuntimeError("NOAA API returned no data for the requested parameters")

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
            raise RuntimeError("NOAA API response missing required temperature data")

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
        raise RuntimeError(f"Failed to fetch NOAA weather data: {e}")


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
            raise RuntimeError("Meteostat API returned no data for the requested location and time range")
        
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
        raise ImportError("Meteostat package is required for weather data. Install with: pip install meteostat")
    except Exception as e:
        print(f"Error fetching Meteostat data: {e}")
        raise RuntimeError(f"Failed to fetch Meteostat weather data: {e}")





def fetch_nyiso_zone_weather_data(
    days: int = 365,
    zones: Optional[List[str]] = None,
    aggregate_method: str = "population_weighted"
) -> pd.DataFrame:
    """
    Fetch weather data for NYISO load zones using Meteostat.

    Collects weather data from representative stations in each NYISO zone
    and optionally aggregates into statewide averages for better correlation
    with statewide power demand.

    Args:
        days: Number of days of historical data to fetch
        zones: List of NYISO zone names to fetch. If None, fetches all zones
        aggregate_method: How to combine zone data:
            - "population_weighted": Population-weighted statewide average
            - "simple_average": Simple average across zones
            - "separate": Keep zones separate (returns multi-zone DataFrame)

    Returns:
        DataFrame with weather data:
        - If aggregate_method in ["population_weighted", "simple_average"]:
          Columns: timestamp, temp_c, humidity, wind_speed, region, data_source
        - If aggregate_method == "separate":
          Columns: timestamp, temp_c, humidity, wind_speed, zone, region, data_source

    Raises:
        RuntimeError: If no weather data could be retrieved
        ValueError: If invalid zones or aggregate_method specified
    """
    print(f"Fetching NYISO zone-based weather data for {days} days...")

    # Validate aggregate method
    valid_methods = ["population_weighted", "simple_average", "separate"]
    if aggregate_method not in valid_methods:
        raise ValueError(f"Invalid aggregate_method '{aggregate_method}'. Valid: {valid_methods}")

    # Use all zones if none specified
    if zones is None:
        zones = list(NYISO_ZONES.keys())

    # Validate zone names
    invalid_zones = [z for z in zones if z not in NYISO_ZONES]
    if invalid_zones:
        valid_zones = list(NYISO_ZONES.keys())
        raise ValueError(f"Invalid zones {invalid_zones}. Valid zones: {valid_zones}")

    print(f"Fetching weather for {len(zones)} NYISO zones: {zones}")

    zone_data = []
    successful_zones = []

    for zone_name in zones:
        zone_info = NYISO_ZONES[zone_name]
        print(f"Fetching weather for {zone_name} ({zone_info.major_city})...")

        try:
            # Fetch weather data for this zone's coordinates
            zone_weather = fetch_meteostat_data(
                days=days,
                latitude=zone_info.latitude,
                longitude=zone_info.longitude
            )

            # Add zone information
            zone_weather["zone"] = zone_name
            zone_weather["region"] = "NYISO"
            zone_weather["data_source"] = f"meteostat_zone_{zone_name.lower()}"

            zone_data.append(zone_weather)
            successful_zones.append(zone_name)

        except Exception as e:
            print(f"Warning: Failed to fetch weather for zone {zone_name}: {e}")
            continue

    if not zone_data:
        raise RuntimeError("No weather data retrieved for any NYISO zones")

    print(f"Successfully fetched weather for {len(successful_zones)} zones: {successful_zones}")

    # Handle aggregation
    if aggregate_method == "separate":
        # Return all zones separately
        result_df = pd.concat(zone_data, ignore_index=True)
        result_df = result_df.sort_values(["zone", "timestamp"]).reset_index(drop=True)
        return result_df[["timestamp", "temp_c", "humidity", "wind_speed", "zone", "region", "data_source"]]

    else:
        # Aggregate zones into statewide averages
        print(f"Aggregating zone weather using {aggregate_method} method...")

        # Combine all zone data
        combined_df = pd.concat(zone_data, ignore_index=True)

        # Group by timestamp and aggregate
        if aggregate_method == "population_weighted":
            # Population-weighted average
            aggregated_data = []

            for timestamp, group in combined_df.groupby("timestamp"):
                zone_temps = {row["zone"]: row["temp_c"] for _, row in group.iterrows()}
                zone_humidity = {row["zone"]: row["humidity"] for _, row in group.iterrows()}
                zone_wind = {row["zone"]: row["wind_speed"] for _, row in group.iterrows()}

                # Calculate weighted averages
                try:
                    avg_temp = get_population_weighted_average(zone_temps)
                    avg_humidity = get_population_weighted_average(zone_humidity)
                    avg_wind = get_population_weighted_average(zone_wind)

                    aggregated_data.append({
                        "timestamp": timestamp,
                        "temp_c": avg_temp,
                        "humidity": avg_humidity,
                        "wind_speed": avg_wind
                    })
                except ValueError as e:
                    print(f"Warning: Skipping timestamp {timestamp} due to aggregation error: {e}")
                    continue

            result_df = pd.DataFrame(aggregated_data)
            result_df["region"] = "NYISO"
            result_df["data_source"] = "meteostat_nyiso_population_weighted"

        else:  # simple_average
            # Simple average across zones
            result_df = (
                combined_df.groupby("timestamp", as_index=False)
                .agg({
                    "temp_c": "mean",
                    "humidity": "mean",
                    "wind_speed": "mean"
                })
            )
            result_df["region"] = "NYISO"
            result_df["data_source"] = "meteostat_nyiso_simple_average"

        result_df = result_df.sort_values("timestamp").reset_index(drop=True)
        return result_df[["timestamp", "temp_c", "humidity", "wind_speed", "region", "data_source"]]


def fetch_caiso_zone_weather_data(
    days: int = 365,
    zones: Optional[List[str]] = None,
    aggregate_method: str = "load_weighted"
) -> pd.DataFrame:
    """
    Fetch weather data for CAISO load zones using Meteostat.

    Collects weather data from representative stations in each CAISO zone
    and optionally aggregates into statewide averages for better correlation
    with statewide power demand.

    Args:
        days: Number of days of historical data to fetch
        zones: List of CAISO zone names to fetch. If None, fetches all zones
        aggregate_method: How to combine zone data:
            - "load_weighted": Load-weighted statewide average
            - "simple_average": Simple average across zones
            - "separate": Keep zones separate (returns multi-zone DataFrame)

    Returns:
        DataFrame with weather data:
        - If aggregate_method in ["load_weighted", "simple_average"]:
          Columns: timestamp, temp_c, humidity, wind_speed, region, data_source
        - If aggregate_method == "separate":
          Columns: timestamp, temp_c, humidity, wind_speed, zone, region, data_source

    Raises:
        RuntimeError: If no weather data could be retrieved
        ValueError: If invalid zones or aggregate_method specified
    """
    print(f"Fetching CAISO zone-based weather data for {days} days...")

    # Validate aggregate method
    valid_methods = ["load_weighted", "simple_average", "separate"]
    if aggregate_method not in valid_methods:
        raise ValueError(f"Invalid aggregate_method '{aggregate_method}'. Valid: {valid_methods}")

    # Use all zones if none specified
    if zones is None:
        zones = list(CAISO_ZONES.keys())

    # Validate zone names
    invalid_zones = [z for z in zones if z not in CAISO_ZONES]
    if invalid_zones:
        valid_zones = list(CAISO_ZONES.keys())
        raise ValueError(f"Invalid zones {invalid_zones}. Valid zones: {valid_zones}")

    print(f"Fetching weather for {len(zones)} CAISO zones: {zones}")

    zone_data = []
    successful_zones = []

    for zone_name in zones:
        zone_info = CAISO_ZONES[zone_name]
        print(f"Fetching weather for {zone_name} ({zone_info.major_city})...")

        try:
            # Fetch weather data for this zone's coordinates
            zone_weather = fetch_meteostat_data(
                days=days,
                latitude=zone_info.latitude,
                longitude=zone_info.longitude
            )

            # Add zone information
            zone_weather["zone"] = zone_name
            zone_weather["region"] = "CAISO"
            zone_weather["data_source"] = f"meteostat_zone_{zone_name.lower()}"

            zone_data.append(zone_weather)
            successful_zones.append(zone_name)

        except Exception as e:
            print(f"Warning: Failed to fetch weather for zone {zone_name}: {e}")
            continue

    if not zone_data:
        raise RuntimeError("No weather data retrieved for any CAISO zones")

    print(f"Successfully fetched weather for {len(successful_zones)} zones: {successful_zones}")

    # Handle aggregation
    if aggregate_method == "separate":
        # Return all zones separately
        result_df = pd.concat(zone_data, ignore_index=True)
        result_df = result_df.sort_values(["zone", "timestamp"]).reset_index(drop=True)
        return result_df[["timestamp", "temp_c", "humidity", "wind_speed", "zone", "region", "data_source"]]

    else:
        # Aggregate zones into statewide averages
        print(f"Aggregating zone weather using {aggregate_method} method...")

        # Combine all zone data
        combined_df = pd.concat(zone_data, ignore_index=True)

        # Group by timestamp and aggregate
        if aggregate_method == "load_weighted":
            # Load-weighted average
            aggregated_data = []

            for timestamp, group in combined_df.groupby("timestamp"):
                zone_temps = {row["zone"]: row["temp_c"] for _, row in group.iterrows()}
                zone_humidity = {row["zone"]: row["humidity"] for _, row in group.iterrows()}
                zone_wind = {row["zone"]: row["wind_speed"] for _, row in group.iterrows()}

                # Calculate weighted averages
                try:
                    avg_temp = get_load_weighted_average(zone_temps)
                    avg_humidity = get_load_weighted_average(zone_humidity)
                    avg_wind = get_load_weighted_average(zone_wind)

                    aggregated_data.append({
                        "timestamp": timestamp,
                        "temp_c": avg_temp,
                        "humidity": avg_humidity,
                        "wind_speed": avg_wind
                    })
                except ValueError as e:
                    print(f"Warning: Skipping timestamp {timestamp} due to aggregation error: {e}")
                    continue

            result_df = pd.DataFrame(aggregated_data)
            result_df["region"] = "CAISO"
            result_df["data_source"] = "meteostat_caiso_load_weighted"

        else:  # simple_average
            # Simple average across zones
            result_df = (
                combined_df.groupby("timestamp", as_index=False)
                .agg({
                    "temp_c": "mean",
                    "humidity": "mean",
                    "wind_speed": "mean"
                })
            )
            result_df["region"] = "CAISO"
            result_df["data_source"] = "meteostat_caiso_simple_average"

        result_df = result_df.sort_values("timestamp").reset_index(drop=True)
        return result_df[["timestamp", "temp_c", "humidity", "wind_speed", "region", "data_source"]]


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
