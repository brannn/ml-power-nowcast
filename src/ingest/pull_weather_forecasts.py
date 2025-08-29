#!/usr/bin/env python3
"""
Weather Forecast Data Collection Module

This module provides functionality to collect weather forecast data from multiple
sources (NWS, Open-Meteo) for CAISO power demand prediction. It focuses on
California zones with proper error handling, data validation, and type safety.

The module implements the weather forecast integration plan outlined in
planning/weather_forecast_integration.md, starting with NWS API integration
for the NP15 (Northern California) zone.

Author: ML Power Nowcast System
Created: 2025-08-29
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class WeatherForecastPoint:
    """
    Represents a geographic point for weather forecast collection.
    
    Attributes:
        zone: CAISO zone identifier (e.g., 'NP15', 'SCE')
        latitude: Latitude coordinate in decimal degrees
        longitude: Longitude coordinate in decimal degrees
        name: Human-readable location name
        nws_office: NWS office code (e.g., 'MTR', 'LOX')
        nws_grid_x: NWS grid X coordinate
        nws_grid_y: NWS grid Y coordinate
    """
    zone: str
    latitude: float
    longitude: float
    name: str
    nws_office: Optional[str] = None
    nws_grid_x: Optional[int] = None
    nws_grid_y: Optional[int] = None


@dataclass
class WeatherForecast:
    """
    Represents a single weather forecast data point.
    
    Attributes:
        timestamp: Forecast valid time (timezone-aware)
        zone: CAISO zone identifier
        temp_c: Temperature in Celsius
        humidity: Relative humidity percentage (0-100)
        wind_speed_kmh: Wind speed in kilometers per hour
        forecast_source: Data source identifier ('nws', 'open_meteo', etc.)
        forecast_issued: When the forecast was issued
        forecast_horizon_hours: Hours ahead this forecast represents
    """
    timestamp: datetime
    zone: str
    temp_c: float
    humidity: Optional[float]
    wind_speed_kmh: Optional[float]
    forecast_source: str
    forecast_issued: datetime
    forecast_horizon_hours: int


class WeatherForecastError(Exception):
    """Base exception for weather forecast operations."""
    pass


class APIConnectionError(WeatherForecastError):
    """Raised when API connection fails."""
    pass


class DataValidationError(WeatherForecastError):
    """Raised when forecast data fails validation."""
    pass


class NWSForecastCollector:
    """
    National Weather Service forecast data collector.
    
    This class handles interaction with the NWS API to collect hourly weather
    forecasts for CAISO zones. It includes proper error handling, rate limiting,
    and data validation.
    
    Attributes:
        base_url: NWS API base URL
        session: HTTP session with retry configuration
        rate_limit_delay: Delay between API calls in seconds
    """
    
    def __init__(
        self, 
        rate_limit_delay: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3
    ) -> None:
        """
        Initialize NWS forecast collector.
        
        Args:
            rate_limit_delay: Seconds to wait between API calls
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = "https://api.weather.gov"
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        
        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set user agent as required by NWS API
        self.session.headers.update({
            'User-Agent': 'ML-Power-Nowcast/1.0 (contact@example.com)'
        })
    
    def get_grid_coordinates(
        self, 
        latitude: float, 
        longitude: float
    ) -> Tuple[str, int, int]:
        """
        Get NWS grid coordinates for a geographic location.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            
        Returns:
            Tuple of (office_code, grid_x, grid_y)
            
        Raises:
            APIConnectionError: If API request fails
            DataValidationError: If response data is invalid
        """
        url = f"{self.base_url}/points/{latitude:.4f},{longitude:.4f}"
        
        try:
            logger.debug(f"Fetching grid coordinates for {latitude}, {longitude}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract grid information
            properties = data.get('properties', {})
            grid_id = properties.get('gridId')
            grid_x = properties.get('gridX')
            grid_y = properties.get('gridY')
            
            if not all([grid_id, grid_x, grid_y]):
                raise DataValidationError(
                    f"Invalid grid data received: {properties}"
                )
            
            logger.info(
                f"Grid coordinates: {grid_id}/{grid_x},{grid_y} "
                f"for {latitude}, {longitude}"
            )
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return grid_id, int(grid_x), int(grid_y)
            
        except requests.RequestException as e:
            raise APIConnectionError(f"Failed to get grid coordinates: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise DataValidationError(f"Invalid response format: {e}")
    
    def fetch_hourly_forecast(
        self, 
        office: str, 
        grid_x: int, 
        grid_y: int,
        zone: str,
        max_hours: int = 48
    ) -> List[WeatherForecast]:
        """
        Fetch hourly weather forecast from NWS.
        
        Args:
            office: NWS office code (e.g., 'MTR')
            grid_x: NWS grid X coordinate
            grid_y: NWS grid Y coordinate
            zone: CAISO zone identifier
            max_hours: Maximum forecast hours to retrieve
            
        Returns:
            List of WeatherForecast objects
            
        Raises:
            APIConnectionError: If API request fails
            DataValidationError: If response data is invalid
        """
        url = f"{self.base_url}/gridpoints/{office}/{grid_x},{grid_y}/forecast/hourly"
        
        try:
            logger.debug(f"Fetching hourly forecast for {office}/{grid_x},{grid_y}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            periods = data.get('properties', {}).get('periods', [])
            
            if not periods:
                raise DataValidationError("No forecast periods found in response")
            
            forecasts: List[WeatherForecast] = []
            forecast_issued = datetime.now(timezone.utc)
            
            for i, period in enumerate(periods[:max_hours]):
                try:
                    # Parse timestamp
                    timestamp = pd.to_datetime(period['startTime']).to_pydatetime()
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    
                    # Convert temperature from Fahrenheit to Celsius
                    temp_f = period.get('temperature')
                    if temp_f is None:
                        logger.warning(f"Missing temperature in period {i}")
                        continue
                    
                    temp_c = (temp_f - 32) * 5 / 9
                    
                    # Extract humidity (may be None)
                    humidity_data = period.get('relativeHumidity')
                    humidity = None
                    if humidity_data and isinstance(humidity_data, dict):
                        humidity = humidity_data.get('value')
                    
                    # Extract wind speed (parse from string like "10 mph")
                    wind_speed_kmh = None
                    wind_speed_str = period.get('windSpeed', '')
                    if wind_speed_str and 'mph' in wind_speed_str:
                        try:
                            mph = float(wind_speed_str.split()[0])
                            wind_speed_kmh = mph * 1.60934  # Convert to km/h
                        except (ValueError, IndexError):
                            logger.warning(f"Could not parse wind speed: {wind_speed_str}")
                    
                    # Calculate forecast horizon
                    horizon_hours = int((timestamp - forecast_issued).total_seconds() / 3600)
                    
                    forecast = WeatherForecast(
                        timestamp=timestamp,
                        zone=zone,
                        temp_c=temp_c,
                        humidity=humidity,
                        wind_speed_kmh=wind_speed_kmh,
                        forecast_source='nws',
                        forecast_issued=forecast_issued,
                        forecast_horizon_hours=horizon_hours
                    )
                    
                    forecasts.append(forecast)
                    
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid forecast period {i}: {e}")
                    continue
            
            logger.info(f"Collected {len(forecasts)} forecast points for zone {zone}")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return forecasts
            
        except requests.RequestException as e:
            raise APIConnectionError(f"Failed to fetch hourly forecast: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise DataValidationError(f"Invalid forecast response format: {e}")


# CAISO zone coordinates for forecast collection
CAISO_FORECAST_ZONES: Dict[str, WeatherForecastPoint] = {
    'NP15': WeatherForecastPoint(
        zone='NP15',
        latitude=37.7749,  # San Francisco (representative of Northern California)
        longitude=-122.4194,
        name='Northern California (San Francisco)'
    ),
    # Additional zones will be added in subsequent phases
}


def validate_forecast_data(forecasts: List[WeatherForecast]) -> List[WeatherForecast]:
    """
    Validate and filter forecast data for quality assurance.
    
    Args:
        forecasts: List of WeatherForecast objects to validate
        
    Returns:
        List of validated WeatherForecast objects
        
    Raises:
        DataValidationError: If validation fails critically
    """
    if not forecasts:
        raise DataValidationError("No forecast data to validate")
    
    validated_forecasts: List[WeatherForecast] = []
    
    for forecast in forecasts:
        # Temperature range validation (reasonable for California)
        if not (-20 <= forecast.temp_c <= 60):
            logger.warning(
                f"Temperature out of range: {forecast.temp_c}°C at {forecast.timestamp}"
            )
            continue
        
        # Humidity range validation
        if forecast.humidity is not None and not (0 <= forecast.humidity <= 100):
            logger.warning(
                f"Humidity out of range: {forecast.humidity}% at {forecast.timestamp}"
            )
            forecast.humidity = None  # Set to None but keep the forecast
        
        # Wind speed validation
        if (forecast.wind_speed_kmh is not None and 
            not (0 <= forecast.wind_speed_kmh <= 200)):
            logger.warning(
                f"Wind speed out of range: {forecast.wind_speed_kmh} km/h at {forecast.timestamp}"
            )
            forecast.wind_speed_kmh = None
        
        validated_forecasts.append(forecast)
    
    logger.info(f"Validated {len(validated_forecasts)}/{len(forecasts)} forecasts")
    
    return validated_forecasts


def forecasts_to_dataframe(forecasts: List[WeatherForecast]) -> pd.DataFrame:
    """
    Convert list of WeatherForecast objects to pandas DataFrame.
    
    Args:
        forecasts: List of WeatherForecast objects
        
    Returns:
        DataFrame with forecast data
    """
    if not forecasts:
        return pd.DataFrame()
    
    data = []
    for forecast in forecasts:
        data.append({
            'timestamp': forecast.timestamp,
            'zone': forecast.zone,
            'temp_c': forecast.temp_c,
            'humidity': forecast.humidity,
            'wind_speed_kmh': forecast.wind_speed_kmh,
            'forecast_source': forecast.forecast_source,
            'forecast_issued': forecast.forecast_issued,
            'forecast_horizon_hours': forecast.forecast_horizon_hours
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df
