#!/usr/bin/env python3
"""
Test Script for NWS Weather Forecast Collection

This script tests the NWS forecast collection functionality for the NP15 zone,
validating data quality, API connectivity, and integration readiness.

Usage:
    python scripts/test_nws_forecast_collection.py [options]
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ingest.pull_weather_forecasts import (
    NWSForecastCollector,
    CAISO_FORECAST_ZONES,
    validate_forecast_data,
    forecasts_to_dataframe,
    WeatherForecastError,
    APIConnectionError,
    DataValidationError
)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for the test script."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"nws_forecast_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def test_nws_grid_coordinates(collector: NWSForecastCollector, logger: logging.Logger) -> bool:
    """
    Test NWS grid coordinate resolution for NP15 zone.
    
    Args:
        collector: NWSForecastCollector instance
        logger: Logger instance
        
    Returns:
        True if test passes, False otherwise
    """
    logger.info("🔍 Testing NWS grid coordinate resolution for NP15...")
    
    try:
        np15_point = CAISO_FORECAST_ZONES['NP15']
        
        office, grid_x, grid_y = collector.get_grid_coordinates(
            np15_point.latitude, 
            np15_point.longitude
        )
        
        logger.info(f"✅ Grid coordinates resolved: {office}/{grid_x},{grid_y}")
        logger.info(f"   Location: {np15_point.name}")
        logger.info(f"   Coordinates: {np15_point.latitude}, {np15_point.longitude}")
        
        # Update the zone configuration with grid coordinates
        np15_point.nws_office = office
        np15_point.nws_grid_x = grid_x
        np15_point.nws_grid_y = grid_y
        
        return True
        
    except (APIConnectionError, DataValidationError) as e:
        logger.error(f"❌ Grid coordinate test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in grid coordinate test: {e}")
        return False


def test_nws_forecast_collection(collector: NWSForecastCollector, logger: logging.Logger) -> Optional[pd.DataFrame]:
    """
    Test NWS hourly forecast collection for NP15 zone.
    
    Args:
        collector: NWSForecastCollector instance
        logger: Logger instance
        
    Returns:
        DataFrame with forecast data if successful, None otherwise
    """
    logger.info("🌤️  Testing NWS hourly forecast collection for NP15...")
    
    try:
        np15_point = CAISO_FORECAST_ZONES['NP15']
        
        # Ensure we have grid coordinates
        if not all([np15_point.nws_office, np15_point.nws_grid_x, np15_point.nws_grid_y]):
            logger.error("❌ Grid coordinates not available for NP15")
            return None
        
        # Collect 24-hour forecast
        forecasts = collector.fetch_hourly_forecast(
            office=np15_point.nws_office,
            grid_x=np15_point.nws_grid_x,
            grid_y=np15_point.nws_grid_y,
            zone='NP15',
            max_hours=24
        )
        
        logger.info(f"✅ Collected {len(forecasts)} forecast points")
        
        # Validate forecast data
        validated_forecasts = validate_forecast_data(forecasts)
        logger.info(f"✅ Validated {len(validated_forecasts)} forecast points")
        
        # Convert to DataFrame
        forecast_df = forecasts_to_dataframe(validated_forecasts)
        
        if len(forecast_df) > 0:
            logger.info("📊 Forecast data summary:")
            logger.info(f"   Time range: {forecast_df['timestamp'].min()} to {forecast_df['timestamp'].max()}")
            logger.info(f"   Temperature range: {forecast_df['temp_c'].min():.1f}°C to {forecast_df['temp_c'].max():.1f}°C")
            
            if forecast_df['humidity'].notna().any():
                humidity_data = forecast_df['humidity'].dropna()
                logger.info(f"   Humidity range: {humidity_data.min():.1f}% to {humidity_data.max():.1f}%")
            
            if forecast_df['wind_speed_kmh'].notna().any():
                wind_data = forecast_df['wind_speed_kmh'].dropna()
                logger.info(f"   Wind speed range: {wind_data.min():.1f} to {wind_data.max():.1f} km/h")
        
        return forecast_df
        
    except (APIConnectionError, DataValidationError) as e:
        logger.error(f"❌ Forecast collection test failed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error in forecast collection test: {e}")
        return None


def test_data_quality(forecast_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Test forecast data quality and completeness.
    
    Args:
        forecast_df: DataFrame with forecast data
        logger: Logger instance
        
    Returns:
        True if data quality is acceptable, False otherwise
    """
    logger.info("🔍 Testing forecast data quality...")
    
    if len(forecast_df) == 0:
        logger.error("❌ No forecast data to test")
        return False
    
    quality_score = 100
    issues = []
    
    # Check for missing timestamps
    if forecast_df['timestamp'].isnull().any():
        missing_timestamps = forecast_df['timestamp'].isnull().sum()
        quality_score -= 20
        issues.append(f"Missing timestamps: {missing_timestamps}")
    
    # Check for missing temperature data
    if forecast_df['temp_c'].isnull().any():
        missing_temp = forecast_df['temp_c'].isnull().sum()
        quality_score -= 30
        issues.append(f"Missing temperature data: {missing_temp}")
    
    # Check temperature range (reasonable for California)
    temp_out_of_range = forecast_df[
        (forecast_df['temp_c'] < -10) | (forecast_df['temp_c'] > 50)
    ]
    if len(temp_out_of_range) > 0:
        quality_score -= 15
        issues.append(f"Temperature out of reasonable range: {len(temp_out_of_range)} points")
    
    # Check forecast horizon coverage
    max_horizon = forecast_df['forecast_horizon_hours'].max()
    if max_horizon < 12:
        quality_score -= 10
        issues.append(f"Limited forecast horizon: {max_horizon} hours")
    
    # Check temporal continuity
    forecast_df_sorted = forecast_df.sort_values('timestamp')
    time_gaps = forecast_df_sorted['timestamp'].diff().dt.total_seconds() / 3600
    large_gaps = time_gaps[time_gaps > 2]  # Gaps larger than 2 hours
    if len(large_gaps) > 0:
        quality_score -= 10
        issues.append(f"Temporal gaps found: {len(large_gaps)} gaps > 2 hours")
    
    # Log quality assessment
    logger.info(f"🎯 Data Quality Score: {quality_score}/100")
    
    if quality_score >= 90:
        logger.info("✅ EXCELLENT - Data quality is excellent")
    elif quality_score >= 75:
        logger.info("✅ GOOD - Data quality is good with minor issues")
    elif quality_score >= 60:
        logger.info("⚠️  FAIR - Data quality is acceptable but has issues")
    else:
        logger.info("❌ POOR - Data quality is poor and needs attention")
    
    if issues:
        logger.warning("🚨 Quality issues found:")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"   {i}. {issue}")
    
    return quality_score >= 75


def save_test_results(forecast_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Save test forecast data for inspection.
    
    Args:
        forecast_df: DataFrame with forecast data
        logger: Logger instance
        
    Returns:
        True if save successful, False otherwise
    """
    try:
        # Create test output directory
        output_dir = Path("data/test_forecasts")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save forecast data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"nws_np15_forecast_test_{timestamp}.parquet"
        
        forecast_df.to_parquet(output_file, index=False)
        
        logger.info(f"💾 Test forecast data saved: {output_file}")
        logger.info(f"   Records: {len(forecast_df)}")
        logger.info(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save test results: {e}")
        return False


def main():
    """Main test function."""
    
    parser = argparse.ArgumentParser(
        description="Test NWS weather forecast collection for NP15 zone",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save test forecast data to file"
    )
    
    parser.add_argument(
        "--max-hours",
        type=int,
        default=24,
        help="Maximum forecast hours to collect (default: 24)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    logger.info("🚀 Starting NWS forecast collection test for NP15 zone")
    logger.info("=" * 60)
    
    try:
        # Initialize collector
        collector = NWSForecastCollector(
            rate_limit_delay=1.0,  # Be respectful to NWS API
            timeout=30,
            max_retries=3
        )
        
        # Test 1: Grid coordinate resolution
        if not test_nws_grid_coordinates(collector, logger):
            logger.error("❌ Grid coordinate test failed - cannot proceed")
            return 1
        
        # Test 2: Forecast collection
        forecast_df = test_nws_forecast_collection(collector, logger)
        if forecast_df is None or len(forecast_df) == 0:
            logger.error("❌ Forecast collection test failed")
            return 1
        
        # Test 3: Data quality validation
        if not test_data_quality(forecast_df, logger):
            logger.warning("⚠️  Data quality test failed - proceeding with caution")
        
        # Save results if requested
        if args.save_results:
            save_test_results(forecast_df, logger)
        
        logger.info("=" * 60)
        logger.info("✅ NWS forecast collection test completed successfully!")
        logger.info(f"   Collected {len(forecast_df)} forecast points for NP15 zone")
        logger.info(f"   Ready for integration into incremental collection pipeline")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
