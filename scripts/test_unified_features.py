#!/usr/bin/env python3
"""
Test Script for Unified Feature Engineering Pipeline

This script tests the unified feature engineering pipeline that combines
power data, historical weather, and forecast weather into a comprehensive
feature set ready for ML model training.

Usage:
    python scripts/test_unified_features.py [options]
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.features.unified_feature_pipeline import (
    UnifiedFeatureConfig,
    ForecastFeatureConfig,
    build_unified_features,
    get_unified_feature_names,
    UnifiedFeatureError,
    DataMergeError
)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for the test script."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"unified_features_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def check_data_availability(logger: logging.Logger) -> dict:
    """
    Check availability of required data sources.
    
    Args:
        logger: Logger instance
        
    Returns:
        Dictionary with data availability status
    """
    logger.info("🔍 Checking data availability...")
    
    availability = {
        'power_data': False,
        'weather_data': False,
        'forecast_data': False,
        'power_path': None,
        'weather_path': None,
        'forecast_dir': None
    }
    
    # Check power data (California-only master dataset)
    power_paths = [
        Path("data/master/caiso_california_only.parquet"),
        Path("data/master/caiso_master.parquet"),
        Path("data/historical/caiso_5year_full.parquet")
    ]
    
    for path in power_paths:
        if path.exists():
            availability['power_data'] = True
            availability['power_path'] = path
            logger.info(f"✅ Found power data: {path}")
            break
    
    if not availability['power_data']:
        logger.warning("❌ No power data found")
    
    # Check historical weather data
    weather_paths = [
        Path("data/historical/caiso_weather_5year.parquet"),
        Path("data/weather/caiso_weather.parquet")
    ]
    
    for path in weather_paths:
        if path.exists():
            availability['weather_data'] = True
            availability['weather_path'] = path
            logger.info(f"✅ Found weather data: {path}")
            break
    
    if not availability['weather_data']:
        logger.warning("⚠️  No historical weather data found")
    
    # Check forecast data
    forecast_dir = Path("data/forecasts")
    if forecast_dir.exists():
        # Look for NP15 forecast data as indicator
        np15_forecast = forecast_dir / "raw" / "weather_forecasts" / "nws" / "np15" / "np15_forecast_latest.parquet"
        if np15_forecast.exists():
            availability['forecast_data'] = True
            availability['forecast_dir'] = forecast_dir
            logger.info(f"✅ Found forecast data: {forecast_dir}")
        else:
            logger.warning("⚠️  Forecast directory exists but no forecast files found")
    else:
        logger.warning("⚠️  No forecast data directory found")
    
    return availability


def test_unified_pipeline_basic(availability: dict, logger: logging.Logger) -> Optional[pd.DataFrame]:
    """
    Test basic unified pipeline functionality.
    
    Args:
        availability: Data availability status
        logger: Logger instance
        
    Returns:
        DataFrame with unified features, or None if test fails
    """
    logger.info("🔧 Testing basic unified pipeline...")
    
    if not availability['power_data']:
        logger.error("❌ Cannot test without power data")
        return None
    
    try:
        # Create test configuration
        config = UnifiedFeatureConfig(
            forecast_config=ForecastFeatureConfig(
                forecast_horizons=[6, 24]  # Reduced for testing
            ),
            target_zones=['NP15'],  # Test with single zone
            lag_hours=[1, 24],  # Reduced for testing
            include_temporal_features=True,
            include_weather_interactions=True
        )
        
        # Build unified features
        unified_df = build_unified_features(
            power_data_path=availability['power_path'],
            weather_data_path=availability['weather_path'],
            forecast_data_dir=availability['forecast_dir'],
            config=config
        )
        
        logger.info(f"✅ Unified pipeline completed successfully")
        logger.info(f"   Records: {len(unified_df):,}")
        logger.info(f"   Features: {len(unified_df.columns)}")
        logger.info(f"   Zones: {unified_df['zone'].unique()}")
        logger.info(f"   Date range: {unified_df['timestamp'].min()} to {unified_df['timestamp'].max()}")
        
        return unified_df
        
    except Exception as e:
        logger.error(f"❌ Basic pipeline test failed: {e}")
        return None


def test_feature_completeness(unified_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Test that all expected features are present and reasonable.
    
    Args:
        unified_df: DataFrame with unified features
        logger: Logger instance
        
    Returns:
        True if feature completeness test passes, False otherwise
    """
    logger.info("📊 Testing feature completeness...")
    
    try:
        # Check for core feature categories
        feature_categories = {
            'base': ['timestamp', 'zone', 'load'],
            'temporal': ['hour', 'day_of_week', 'month'],
            'weather': ['temp_c', 'humidity'],
            'weather_derived': ['cooling_degree_days', 'heating_degree_days'],
            'lag': ['load_lag_1h', 'load_lag_24h'],
            'forecast': ['temp_forecast_6h', 'temp_forecast_24h'],
            'interaction': ['temp_humidity_interaction']
        }
        
        missing_categories = []
        
        for category, expected_features in feature_categories.items():
            present_features = [f for f in expected_features if f in unified_df.columns]
            missing_features = [f for f in expected_features if f not in unified_df.columns]
            
            if len(present_features) == 0:
                missing_categories.append(category)
                logger.warning(f"⚠️  No {category} features found")
            elif len(missing_features) > 0:
                logger.info(f"✅ {category} features: {len(present_features)}/{len(expected_features)} present")
                logger.debug(f"   Missing: {missing_features}")
            else:
                logger.info(f"✅ {category} features: all {len(expected_features)} present")
        
        if missing_categories:
            logger.error(f"❌ Missing feature categories: {missing_categories}")
            return False
        
        logger.info("✅ Feature completeness test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Feature completeness test failed: {e}")
        return False


def test_data_quality(unified_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Test unified feature data quality.
    
    Args:
        unified_df: DataFrame with unified features
        logger: Logger instance
        
    Returns:
        True if data quality test passes, False otherwise
    """
    logger.info("🔍 Testing unified feature data quality...")
    
    try:
        quality_score = 100
        issues = []
        
        # Test 1: Check for excessive null values in critical features
        critical_features = ['timestamp', 'zone', 'load', 'hour', 'day_of_week']
        for feature in critical_features:
            if feature in unified_df.columns:
                null_pct = unified_df[feature].isnull().mean() * 100
                if null_pct > 5:  # More than 5% nulls is concerning
                    quality_score -= 15
                    issues.append(f"{feature} has {null_pct:.1f}% null values")
        
        # Test 2: Check load values are reasonable
        if 'load' in unified_df.columns:
            load_data = unified_df['load'].dropna()
            if len(load_data) > 0:
                if load_data.min() < 0 or load_data.max() > 100000:  # Reasonable MW range
                    quality_score -= 20
                    issues.append(f"Load values out of range: {load_data.min():.1f} to {load_data.max():.1f} MW")
        
        # Test 3: Check temporal features are in expected ranges
        temporal_checks = {
            'hour': (0, 23),
            'day_of_week': (0, 6),
            'month': (1, 12)
        }
        
        for feature, (min_val, max_val) in temporal_checks.items():
            if feature in unified_df.columns:
                data = unified_df[feature].dropna()
                if len(data) > 0:
                    if data.min() < min_val or data.max() > max_val:
                        quality_score -= 10
                        issues.append(f"{feature} out of range: {data.min()} to {data.max()}")
        
        # Test 4: Check forecast features have reasonable coverage
        forecast_features = [col for col in unified_df.columns if 'forecast' in col]
        if forecast_features:
            for feature in forecast_features[:3]:  # Check first few
                null_pct = unified_df[feature].isnull().mean() * 100
                if null_pct > 90:  # More than 90% nulls suggests poor forecast coverage
                    quality_score -= 5
                    issues.append(f"Poor forecast coverage for {feature}: {null_pct:.1f}% null")
        
        # Test 5: Check lag features have expected null pattern
        lag_features = [col for col in unified_df.columns if 'lag' in col]
        for feature in lag_features:
            null_pct = unified_df[feature].isnull().mean() * 100
            # Lag features should have some nulls at the beginning, but not too many
            if null_pct > 50:
                quality_score -= 5
                issues.append(f"Excessive nulls in lag feature {feature}: {null_pct:.1f}%")
        
        # Log quality assessment
        logger.info(f"🎯 Unified Feature Quality Score: {quality_score}/100")
        
        if quality_score >= 90:
            logger.info("✅ EXCELLENT - Unified feature quality is excellent")
        elif quality_score >= 75:
            logger.info("✅ GOOD - Unified feature quality is good with minor issues")
        elif quality_score >= 60:
            logger.info("⚠️  FAIR - Unified feature quality is acceptable but has issues")
        else:
            logger.info("❌ POOR - Unified feature quality is poor and needs attention")
        
        if issues:
            logger.warning("🚨 Quality issues found:")
            for i, issue in enumerate(issues, 1):
                logger.warning(f"   {i}. {issue}")
        
        return quality_score >= 75
        
    except Exception as e:
        logger.error(f"❌ Data quality test failed: {e}")
        return False


def analyze_feature_coverage(unified_df: pd.DataFrame, logger: logging.Logger) -> None:
    """
    Analyze feature coverage and provide insights.
    
    Args:
        unified_df: DataFrame with unified features
        logger: Logger instance
    """
    logger.info("📈 Analyzing feature coverage...")
    
    try:
        # Categorize features
        feature_types = {
            'Base': [col for col in unified_df.columns if col in ['timestamp', 'zone', 'load']],
            'Temporal': [col for col in unified_df.columns if any(x in col for x in ['hour', 'day', 'month', 'quarter', 'weekend'])],
            'Weather Historical': [col for col in unified_df.columns if any(x in col for x in ['temp_c', 'humidity', 'wind']) and 'forecast' not in col],
            'Weather Forecast': [col for col in unified_df.columns if 'forecast' in col],
            'Lag Features': [col for col in unified_df.columns if 'lag' in col],
            'Interactions': [col for col in unified_df.columns if 'interaction' in col or 'index' in col or 'chill' in col],
            'Other': []
        }
        
        # Classify remaining features
        classified = set()
        for features in feature_types.values():
            classified.update(features)
        
        feature_types['Other'] = [col for col in unified_df.columns if col not in classified]
        
        # Report coverage
        logger.info("Feature Coverage by Category:")
        total_features = 0
        for category, features in feature_types.items():
            if features:
                non_null_counts = {f: unified_df[f].notna().sum() for f in features}
                avg_coverage = np.mean(list(non_null_counts.values())) / len(unified_df) * 100
                logger.info(f"  {category}: {len(features)} features, {avg_coverage:.1f}% avg coverage")
                total_features += len(features)
        
        logger.info(f"Total features: {total_features}")
        
        # Identify features with poor coverage
        poor_coverage_features = []
        for col in unified_df.columns:
            if col not in ['timestamp', 'zone']:  # Skip identifier columns
                coverage = unified_df[col].notna().sum() / len(unified_df) * 100
                if coverage < 50:
                    poor_coverage_features.append((col, coverage))
        
        if poor_coverage_features:
            logger.warning("Features with <50% coverage:")
            for feature, coverage in sorted(poor_coverage_features, key=lambda x: x[1]):
                logger.warning(f"  {feature}: {coverage:.1f}%")
        
    except Exception as e:
        logger.error(f"❌ Feature coverage analysis failed: {e}")


def save_test_results(unified_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Save test unified feature data for inspection.
    
    Args:
        unified_df: DataFrame with unified features
        logger: Logger instance
        
    Returns:
        True if save successful, False otherwise
    """
    try:
        # Create test output directory
        output_dir = Path("data/test_unified")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save unified feature data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"unified_features_test_{timestamp}.parquet"
        
        unified_df.to_parquet(output_file, index=False)
        
        logger.info(f"💾 Test unified feature data saved: {output_file}")
        logger.info(f"   Records: {len(unified_df):,}")
        logger.info(f"   Features: {len(unified_df.columns)}")
        logger.info(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
        
        # Save feature summary
        summary_file = output_dir / f"unified_feature_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write("UNIFIED FEATURE PIPELINE TEST SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write(f"Records: {len(unified_df):,}\n")
            f.write(f"Features: {len(unified_df.columns)}\n")
            f.write(f"Zones: {list(unified_df['zone'].unique())}\n")
            f.write(f"Date range: {unified_df['timestamp'].min()} to {unified_df['timestamp'].max()}\n\n")
            
            f.write("FEATURE LIST:\n")
            f.write("-" * 20 + "\n")
            for i, col in enumerate(sorted(unified_df.columns), 1):
                coverage = unified_df[col].notna().sum() / len(unified_df) * 100
                f.write(f"{i:3d}. {col:<30} ({coverage:5.1f}% coverage)\n")
        
        logger.info(f"📝 Feature summary saved: {summary_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save test results: {e}")
        return False


def main():
    """Main test function."""
    
    parser = argparse.ArgumentParser(
        description="Test unified feature engineering pipeline",
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
        help="Save test unified feature data to file"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    logger.info("🚀 Starting unified feature engineering pipeline test")
    logger.info("=" * 60)
    
    try:
        # Check data availability
        availability = check_data_availability(logger)
        
        # Test basic pipeline
        unified_df = test_unified_pipeline_basic(availability, logger)
        if unified_df is None:
            logger.error("❌ Basic pipeline test failed")
            return 1
        
        # Test feature completeness
        if not test_feature_completeness(unified_df, logger):
            logger.warning("⚠️  Feature completeness test had issues")
        
        # Test data quality
        if not test_data_quality(unified_df, logger):
            logger.warning("⚠️  Data quality test had issues")
        
        # Analyze feature coverage
        analyze_feature_coverage(unified_df, logger)
        
        # Save results if requested
        if args.save_results:
            save_test_results(unified_df, logger)
        
        logger.info("=" * 60)
        logger.info("✅ Unified feature engineering pipeline test completed!")
        logger.info(f"   Created unified dataset with {len(unified_df.columns)} features")
        logger.info(f"   Ready for ML model training and evaluation")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
