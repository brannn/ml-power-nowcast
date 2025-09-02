#!/usr/bin/env python3
"""
Current Weather Collection for CAISO Zones

Lightweight script to collect current weather conditions for each CAISO zone
using Open-Meteo API (free, no API key required) with OpenWeatherMap fallback.
Updates every 15 minutes for dashboard display.

Author: ML Power Nowcast System
Created: 2025-09-02
Updated: 2025-09-02 (Added Open-Meteo support)
"""

import logging
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from src.config.caiso_zones import CAISO_ZONES

# Load environment variables
load_dotenv(project_root / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Weather API configurations
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"


def get_current_weather_openmeteo(lat: float, lon: float, zone_name: str) -> Optional[Dict]:
    """
    Get current weather conditions using Open-Meteo API (free, no API key required).
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate  
        zone_name: CAISO zone name for logging
        
    Returns:
        Dictionary with weather data or None if failed
    """
    try:
        params = {
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code',
            'temperature_unit': 'celsius',
            'wind_speed_unit': 'kmh',
            'timezone': 'America/Los_Angeles'
        }
        
        response = requests.get(OPENMETEO_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        current = data.get('current', {})
        
        weather_data = {
            'zone': zone_name,
            'timestamp': datetime.now(timezone.utc),
            'temp_c': current.get('temperature_2m'),
            'humidity': current.get('relative_humidity_2m'),
            'wind_speed': current.get('wind_speed_10m'),
            'weather_code': current.get('weather_code', 0),
            'description': weather_code_to_description(current.get('weather_code', 0)),
            'city': CAISO_ZONES[zone_name].major_city,
            'data_source': 'open-meteo'
        }
        
        logger.info(f"🌤️ {zone_name} (Open-Meteo - {weather_data['city']}): {weather_data['temp_c']:.1f}°C, "
                   f"{weather_data['humidity']}% humidity, {weather_data['wind_speed']:.1f} km/h - {weather_data['description']}")
        return weather_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Open-Meteo API request failed for {zone_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error processing Open-Meteo data for {zone_name}: {e}")
        return None


def weather_code_to_description(code: int) -> str:
    """Convert Open-Meteo weather code to human-readable description."""
    weather_codes = {
        0: 'clear sky',
        1: 'mainly clear', 2: 'partly cloudy', 3: 'overcast',
        45: 'fog', 48: 'depositing rime fog',
        51: 'light drizzle', 53: 'moderate drizzle', 55: 'dense drizzle',
        61: 'slight rain', 63: 'moderate rain', 65: 'heavy rain',
        80: 'slight rain showers', 81: 'moderate rain showers', 82: 'violent rain showers',
        95: 'thunderstorm', 96: 'thunderstorm with slight hail', 99: 'thunderstorm with heavy hail'
    }
    return weather_codes.get(code, f'weather code {code}')

def get_current_weather(lat: float, lon: float, zone_name: str, demo_mode: bool = False) -> Optional[Dict]:
    """
    Get current weather conditions for a specific location.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate  
        zone_name: CAISO zone name for logging
        demo_mode: If True, return simulated weather data
        
    Returns:
        Dictionary with weather data or None if failed
    """
    if demo_mode:
        # Return simulated weather data for testing
        import random
        zone_temps = {
            'NP15': 22.0,      # Oakland/Bay Area - mild
            'SP15': 28.0,      # Los Angeles - warmer
            'SCE': 32.0,       # Inland Empire - hot
            'SDGE': 24.0,      # San Diego - mild coastal
            'SMUD': 30.0,      # Sacramento - warm valley
            'PGE_VALLEY': 26.0, # Central Valley - moderate
            'ZP26': 29.0       # Fresno - Central Valley hot
        }
        base_temp = zone_temps.get(zone_name, 25.0)
        weather_data = {
            'zone': zone_name,
            'timestamp': datetime.now(timezone.utc),
            'temp_c': base_temp + random.uniform(-3, 3),
            'humidity': random.randint(45, 75),
            'wind_speed': random.uniform(5, 20),
            'description': random.choice(['clear sky', 'few clouds', 'partly cloudy', 'overcast']),
            'city': CAISO_ZONES[zone_name].major_city,
            'data_source': 'demo_mode'
        }
        logger.info(f"🧪 {zone_name} (Demo - {weather_data['city']}): {weather_data['temp_c']:.1f}°C, "
                   f"{weather_data['humidity']}% humidity, {weather_data['wind_speed']:.1f} km/h")
        return weather_data
    
    # Try Open-Meteo first (free, no API key required)
    weather_data = get_current_weather_openmeteo(lat, lon, zone_name)
    if weather_data:
        return weather_data
    
    # Fallback to OpenWeatherMap if API key is available
    if not API_KEY or API_KEY == "your_api_key_here":
        logger.warning(f"⚠️ No OpenWeatherMap fallback available for {zone_name} (no API key)")
        return None
    
    try:
        params = {
            'lat': lat,
            'lon': lon,
            'appid': API_KEY,
            'units': 'metric'  # Celsius for consistency
        }
        
        response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract relevant weather data
        weather_data = {
            'zone': zone_name,
            'timestamp': datetime.now(timezone.utc),
            'temp_c': data['main']['temp'],
            'humidity': data['main']['humidity'],
            'wind_speed': data['wind']['speed'] * 3.6,  # Convert m/s to km/h
            'description': data['weather'][0]['description'],
            'city': data['name'],
            'data_source': 'openweathermap'
        }
        
        logger.info(f"✅ {zone_name} ({data['name']}): {weather_data['temp_c']:.1f}°C, "
                   f"{weather_data['humidity']}% humidity, {weather_data['wind_speed']:.1f} km/h")
        
        return weather_data
        
    except requests.RequestException as e:
        logger.error(f"❌ Failed to fetch weather for {zone_name}: {e}")
        return None
    except KeyError as e:
        logger.error(f"❌ Invalid weather data format for {zone_name}: {e}")
        return None

def collect_all_zones_weather(demo_mode: bool = False) -> pd.DataFrame:
    """
    Collect current weather for all CAISO zones.
    
    Returns:
        DataFrame with current weather data for all zones
    """
    logger.info("🌤️ Collecting current weather for all CAISO zones")
    
    weather_records = []
    
    # Collect weather for primary zones (using all zones for comprehensive coverage)
    primary_zones = ['NP15', 'SP15', 'SCE', 'SDGE', 'SMUD', 'PGE_VALLEY', 'ZP26']
    
    for zone_name in primary_zones:
        if zone_name in CAISO_ZONES:
            zone_info = CAISO_ZONES[zone_name]
            weather_data = get_current_weather(
                zone_info.latitude, 
                zone_info.longitude, 
                zone_name,
                demo_mode
            )
            if weather_data:
                weather_records.append(weather_data)
        else:
            logger.warning(f"⚠️ Zone {zone_name} not found in CAISO_ZONES")
    
    if weather_records:
        df = pd.DataFrame(weather_records)
        logger.info(f"✅ Collected weather data for {len(weather_records)} zones")
        return df
    else:
        logger.error("❌ No weather data collected")
        return pd.DataFrame()

def save_current_weather(df: pd.DataFrame, output_path: Path) -> None:
    """
    Save current weather data to parquet file.
    
    Args:
        df: Weather data DataFrame
        output_path: Output file path
    """
    if df.empty:
        logger.warning("⚠️ No weather data to save")
        return
    
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to parquet
        df.to_parquet(output_path, index=False)
        logger.info(f"✅ Saved current weather data to {output_path}")
        
        # Also save as JSON for easy API access
        json_path = output_path.with_suffix('.json')
        weather_dict = df.to_dict('records')
        with open(json_path, 'w') as f:
            json.dump(weather_dict, f, indent=2, default=str)
        logger.info(f"✅ Saved current weather JSON to {json_path}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save weather data: {e}")

def main():
    """Main execution function."""
    logger.info("🚀 Starting current weather collection")
    
    # Check for demo mode
    demo_mode = len(sys.argv) > 1 and sys.argv[1] == "--demo"
    if demo_mode:
        logger.info("🧪 Running in demo mode with simulated weather data")
    
    # Collect weather data
    weather_df = collect_all_zones_weather(demo_mode)
    
    if not weather_df.empty:
        # Save to data directory
        project_root = Path(__file__).parent.parent
        output_path = project_root / "data" / "weather" / "current_conditions.parquet"
        
        save_current_weather(weather_df, output_path)
        
        # Print summary
        print("\n🌤️ Current Weather Summary:")
        for _, row in weather_df.iterrows():
            temp_f = row['temp_c'] * 9/5 + 32
            print(f"  {row['zone']} ({row['city']}): {temp_f:.1f}°F, "
                  f"{row['humidity']}% humidity, {row['wind_speed']:.1f} km/h")
        
        logger.info("✅ Current weather collection completed successfully")
    else:
        logger.error("❌ Current weather collection failed")
        sys.exit(1)

if __name__ == "__main__":
    main()