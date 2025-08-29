#!/usr/bin/env python3
"""
Weather Forecast Collection Pipeline

This script implements a dedicated pipeline for collecting weather forecast data
from NWS and other sources for CAISO zones. It runs independently from the power
data collection pipeline, allowing for flexible scheduling and easier testing.

The script follows the implementation plan outlined in planning/weather_forecast_integration.md,
starting with NWS integration for the NP15 zone and designed for expansion to all zones.

Features:
- NWS API integration with proper error handling
- Data validation and quality assurance
- S3 storage with organized structure
- Comprehensive logging and monitoring
- Designed for scheduled execution via launchd

Usage:
    python scripts/collect_weather_forecasts.py [options]
"""

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

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


def setup_logging(log_level: str = "INFO", quiet: bool = False) -> logging.Logger:
    """
    Set up comprehensive logging for forecast collection.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        quiet: If True, reduce console output for scheduled runs
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"forecast_collection_{datetime.now().strftime('%Y%m%d')}.log"
    
    handlers = [logging.FileHandler(log_file)]
    if not quiet:
        handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


def collect_zone_forecasts(
    collector: NWSForecastCollector,
    zone: str,
    max_hours: int,
    logger: logging.Logger
) -> Optional[pd.DataFrame]:
    """
    Collect weather forecasts for a specific CAISO zone.
    
    Args:
        collector: NWSForecastCollector instance
        zone: CAISO zone identifier (e.g., 'NP15')
        max_hours: Maximum forecast hours to collect
        logger: Logger instance
        
    Returns:
        DataFrame with forecast data, or None if collection fails
    """
    if zone not in CAISO_FORECAST_ZONES:
        logger.error(f"Unknown zone: {zone}")
        return None
    
    zone_point = CAISO_FORECAST_ZONES[zone]
    logger.info(f"Collecting forecasts for zone {zone} ({zone_point.name})")
    
    try:
        # Get grid coordinates if not already cached
        if not all([zone_point.nws_office, zone_point.nws_grid_x, zone_point.nws_grid_y]):
            logger.debug(f"Resolving grid coordinates for {zone}")
            office, grid_x, grid_y = collector.get_grid_coordinates(
                zone_point.latitude,
                zone_point.longitude
            )
            zone_point.nws_office = office
            zone_point.nws_grid_x = grid_x
            zone_point.nws_grid_y = grid_y
        
        # Collect hourly forecasts
        forecasts = collector.fetch_hourly_forecast(
            office=zone_point.nws_office,
            grid_x=zone_point.nws_grid_x,
            grid_y=zone_point.nws_grid_y,
            zone=zone,
            max_hours=max_hours
        )
        
        if not forecasts:
            logger.warning(f"No forecasts collected for zone {zone}")
            return None
        
        # Validate forecast data
        validated_forecasts = validate_forecast_data(forecasts)
        
        if not validated_forecasts:
            logger.warning(f"No valid forecasts after validation for zone {zone}")
            return None
        
        # Convert to DataFrame
        forecast_df = forecasts_to_dataframe(validated_forecasts)
        
        logger.info(f"Successfully collected {len(forecast_df)} forecasts for zone {zone}")
        logger.debug(f"Forecast time range: {forecast_df['timestamp'].min()} to {forecast_df['timestamp'].max()}")
        
        return forecast_df
        
    except (APIConnectionError, DataValidationError) as e:
        logger.error(f"Failed to collect forecasts for zone {zone}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error collecting forecasts for zone {zone}: {e}")
        return None


def save_forecast_data(
    forecast_df: pd.DataFrame,
    zone: str,
    output_dir: Path,
    logger: logging.Logger
) -> bool:
    """
    Save forecast data to local storage with organized structure.
    
    Args:
        forecast_df: DataFrame with forecast data
        zone: CAISO zone identifier
        output_dir: Base output directory
        logger: Logger instance
        
    Returns:
        True if save successful, False otherwise
    """
    try:
        # Create organized directory structure
        zone_dir = output_dir / "raw" / "weather_forecasts" / "nws" / zone.lower()
        zone_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{zone.lower()}_forecast_{timestamp}.parquet"
        file_path = zone_dir / filename
        
        # Save forecast data
        forecast_df.to_parquet(file_path, index=False)
        
        file_size_kb = file_path.stat().st_size / 1024
        logger.info(f"Saved forecast data: {file_path}")
        logger.info(f"  Records: {len(forecast_df)}, Size: {file_size_kb:.1f} KB")
        
        # Also save to latest file for easy access
        latest_file = zone_dir / f"{zone.lower()}_forecast_latest.parquet"
        forecast_df.to_parquet(latest_file, index=False)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to save forecast data for zone {zone}: {e}")
        return False


def upload_to_s3(
    file_path: Path,
    zone: str,
    logger: logging.Logger
) -> bool:
    """
    Upload forecast data to S3 for backup and sharing.
    
    Args:
        file_path: Local file path to upload
        zone: CAISO zone identifier
        logger: Logger instance
        
    Returns:
        True if upload successful, False otherwise
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        s3_client = boto3.client('s3')
        bucket = "ml-power-nowcast-data-1756420517"
        
        # Create S3 key following organized structure
        s3_key = f"raw/weather_forecasts/nws/{zone.lower()}/{file_path.name}"
        
        # Upload file
        s3_client.upload_file(str(file_path), bucket, s3_key)
        
        logger.info(f"Uploaded to S3: s3://{bucket}/{s3_key}")
        return True
        
    except ClientError as e:
        logger.error(f"S3 upload failed for {file_path}: {e}")
        return False
    except Exception as e:
        logger.warning(f"S3 upload failed (boto3 not available?): {e}")
        return False


def create_collection_summary(
    results: Dict[str, Optional[pd.DataFrame]],
    logger: logging.Logger
) -> Dict[str, any]:
    """
    Create summary of forecast collection results.
    
    Args:
        results: Dictionary mapping zone names to forecast DataFrames
        logger: Logger instance
        
    Returns:
        Summary dictionary with collection statistics
    """
    summary = {
        'collection_time': datetime.now(timezone.utc).isoformat(),
        'zones_attempted': list(results.keys()),
        'zones_successful': [],
        'zones_failed': [],
        'total_forecasts': 0,
        'forecast_horizon_hours': 0
    }
    
    for zone, forecast_df in results.items():
        if forecast_df is not None and len(forecast_df) > 0:
            summary['zones_successful'].append(zone)
            summary['total_forecasts'] += len(forecast_df)
            
            # Track maximum forecast horizon
            max_horizon = forecast_df['forecast_horizon_hours'].max()
            summary['forecast_horizon_hours'] = max(
                summary['forecast_horizon_hours'], 
                max_horizon
            )
        else:
            summary['zones_failed'].append(zone)
    
    # Log summary
    logger.info("📊 Forecast Collection Summary:")
    logger.info(f"  Zones attempted: {len(summary['zones_attempted'])}")
    logger.info(f"  Zones successful: {len(summary['zones_successful'])}")
    logger.info(f"  Zones failed: {len(summary['zones_failed'])}")
    logger.info(f"  Total forecasts: {summary['total_forecasts']}")
    logger.info(f"  Max forecast horizon: {summary['forecast_horizon_hours']} hours")
    
    if summary['zones_failed']:
        logger.warning(f"Failed zones: {summary['zones_failed']}")
    
    return summary


def main():
    """Main forecast collection function."""
    
    parser = argparse.ArgumentParser(
        description="Collect weather forecasts for CAISO zones",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--zones",
        nargs="+",
        default=["NP15"],
        choices=list(CAISO_FORECAST_ZONES.keys()),
        help="CAISO zones to collect forecasts for (default: NP15)"
    )
    
    parser.add_argument(
        "--max-hours",
        type=int,
        default=48,
        help="Maximum forecast hours to collect (default: 48)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/forecasts"),
        help="Output directory for forecast data (default: data/forecasts)"
    )
    
    parser.add_argument(
        "--no-s3",
        action="store_true",
        help="Skip S3 upload"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal console output for scheduled runs"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level, args.quiet)
    
    if not args.quiet:
        logger.info("🌤️  Starting weather forecast collection")
        logger.info("=" * 60)
        logger.info(f"Zones: {args.zones}")
        logger.info(f"Max hours: {args.max_hours}")
        logger.info(f"Output directory: {args.output_dir}")
    
    try:
        # Initialize NWS collector
        collector = NWSForecastCollector(
            rate_limit_delay=1.0,  # Respectful to NWS API
            timeout=30,
            max_retries=3
        )
        
        # Collect forecasts for each zone
        results: Dict[str, Optional[pd.DataFrame]] = {}
        
        for zone in args.zones:
            logger.info(f"Processing zone: {zone}")
            
            forecast_df = collect_zone_forecasts(
                collector=collector,
                zone=zone,
                max_hours=args.max_hours,
                logger=logger
            )
            
            results[zone] = forecast_df
            
            # Save data if collection successful
            if forecast_df is not None and len(forecast_df) > 0:
                if save_forecast_data(forecast_df, zone, args.output_dir, logger):
                    # Upload to S3 if requested
                    if not args.no_s3:
                        zone_dir = args.output_dir / "raw" / "weather_forecasts" / "nws" / zone.lower()
                        latest_file = zone_dir / f"{zone.lower()}_forecast_latest.parquet"
                        upload_to_s3(latest_file, zone, logger)
        
        # Create collection summary
        summary = create_collection_summary(results, logger)
        
        # Determine exit code based on results
        if summary['zones_successful']:
            if not args.quiet:
                logger.info("✅ Forecast collection completed successfully!")
            return 0
        else:
            logger.error("❌ No forecasts collected successfully")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Forecast collection failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
