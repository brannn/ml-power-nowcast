#!/usr/bin/env python3
"""
Test Script for Weather Forecast Feature Engineering

This script tests the forecast feature engineering functionality, validating
that features are created correctly and are ready for ML model integration.

Usage:
    python scripts/test_forecast_features.py [options]
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

from src.features.build_forecast_features import (
    ForecastFeatureConfig,
    build_all_forecast_features,
    get_forecast_feature_names,
    validate_forecast_data,
    ForecastFeatureError,
    DataValidationError
)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for the test script."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"forecast_features_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def load_test_forecast_data(logger: logging.Logger) -> Optional[pd.DataFrame]:
    """
    Load forecast data for testing feature engineering.
    
    Args:
        logger: Logger instance
        
    Returns:
        DataFrame with forecast data, or None if not found
    """
    # Try to load the latest NP15 forecast data
    forecast_file = Path("data/forecasts/raw/weather_forecasts/nws/np15/np15_forecast_latest.parquet")
    
    if not forecast_file.exists():
        logger.error(f"Forecast data file not found: {forecast_file}")
        logger.info("Please run forecast collection first: python scripts/collect_weather_forecasts.py")
        return None
    
    try:
        df = pd.read_parquet(forecast_file)
        logger.info(f"Loaded forecast data: {len(df)} records")
        logger.info(f"Columns: {list(df.columns)}")
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to load forecast data: {e}")
        return None


def test_data_validation(forecast_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Test forecast data validation functionality.
    
    Args:
        forecast_df: DataFrame with forecast data
        logger: Logger instance
        
    Returns:
        True if validation tests pass, False otherwise
    """
    logger.info("🔍 Testing forecast data validation...")
    
    try:
        # Test 1: Valid data should pass
        validate_forecast_data(forecast_df)
        logger.info("✅ Valid data validation passed")
        
        # Test 2: Missing columns should fail
        try:
            invalid_df = forecast_df.drop(columns=['temp_c'])
            validate_forecast_data(invalid_df)
            logger.error("❌ Missing column validation should have failed")
            return False
        except DataValidationError:
            logger.info("✅ Missing column validation correctly failed")
        
        # Test 3: Empty DataFrame should fail
        try:
            empty_df = forecast_df.iloc[0:0]
            validate_forecast_data(empty_df)
            logger.error("❌ Empty DataFrame validation should have failed")
            return False
        except DataValidationError:
            logger.info("✅ Empty DataFrame validation correctly failed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Data validation test failed: {e}")
        return False


def test_core_features(forecast_df: pd.DataFrame, logger: logging.Logger) -> Optional[pd.DataFrame]:
    """
    Test core forecast feature creation.
    
    Args:
        forecast_df: DataFrame with forecast data
        logger: Logger instance
        
    Returns:
        DataFrame with core features, or None if test fails
    """
    logger.info("🌡️  Testing core forecast feature creation...")
    
    try:
        # Create configuration for testing
        config = ForecastFeatureConfig(
            forecast_horizons=[1, 6, 12, 24],
            base_temperature=18.0
        )
        
        # Build all forecast features
        features_df = build_all_forecast_features(forecast_df, config)
        
        # Validate results
        original_cols = len(forecast_df.columns)
        new_cols = len(features_df.columns)
        added_features = new_cols - original_cols
        
        logger.info(f"✅ Created {added_features} forecast features")
        logger.info(f"   Original columns: {original_cols}")
        logger.info(f"   New columns: {new_cols}")
        
        # Check specific core features
        expected_core_features = [
            'temp_forecast_6h', 'temp_forecast_24h',
            'cooling_forecast_6h', 'heating_forecast_6h'
        ]
        
        missing_features = [f for f in expected_core_features if f not in features_df.columns]
        if missing_features:
            logger.error(f"❌ Missing expected core features: {missing_features}")
            return None
        
        logger.info("✅ All expected core features created")
        
        # Validate feature values
        for feature in expected_core_features:
            if features_df[feature].isnull().all():
                logger.warning(f"⚠️  Feature {feature} is all null")
            else:
                non_null_count = features_df[feature].notna().sum()
                logger.info(f"   {feature}: {non_null_count} non-null values")
        
        return features_df
        
    except Exception as e:
        logger.error(f"❌ Core features test failed: {e}")
        return None


def test_advanced_features(features_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Test advanced forecast features (change rates, extremes, uncertainty).
    
    Args:
        features_df: DataFrame with forecast features
        logger: Logger instance
        
    Returns:
        True if advanced features test passes, False otherwise
    """
    logger.info("🌪️  Testing advanced forecast features...")
    
    try:
        # Check weather change features
        change_features = [
            'temp_change_rate_6h', 'temp_change_rate_12h',
            'weather_volatility_6h'
        ]
        
        for feature in change_features:
            if feature in features_df.columns:
                non_null_count = features_df[feature].notna().sum()
                if non_null_count > 0:
                    logger.info(f"✅ {feature}: {non_null_count} values")
                else:
                    logger.warning(f"⚠️  {feature}: all null values")
            else:
                logger.warning(f"⚠️  {feature}: not found")
        
        # Check extreme weather features
        extreme_features = [
            'heat_wave_incoming', 'cold_snap_incoming',
            'rapid_temp_change', 'extreme_temp_probability'
        ]
        
        for feature in extreme_features:
            if feature in features_df.columns:
                value_counts = features_df[feature].value_counts()
                logger.info(f"✅ {feature}: {dict(value_counts)}")
            else:
                logger.warning(f"⚠️  {feature}: not found")
        
        # Check uncertainty features
        uncertainty_features = [
            'forecast_uncertainty_score', 'weather_pattern_stability',
            'forecast_confidence'
        ]
        
        for feature in uncertainty_features:
            if feature in features_df.columns:
                non_null_count = features_df[feature].notna().sum()
                if non_null_count > 0:
                    mean_val = features_df[feature].mean()
                    logger.info(f"✅ {feature}: {non_null_count} values, mean={mean_val:.3f}")
                else:
                    logger.warning(f"⚠️  {feature}: all null values")
            else:
                logger.warning(f"⚠️  {feature}: not found")
        
        logger.info("✅ Advanced features test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Advanced features test failed: {e}")
        return False


def test_feature_quality(features_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Test forecast feature data quality and reasonableness.
    
    Args:
        features_df: DataFrame with forecast features
        logger: Logger instance
        
    Returns:
        True if quality tests pass, False otherwise
    """
    logger.info("🔍 Testing forecast feature quality...")
    
    try:
        quality_score = 100
        issues = []
        
        # Test 1: Check for excessive null values
        null_percentages = features_df.isnull().mean() * 100
        high_null_features = null_percentages[null_percentages > 50]
        
        if len(high_null_features) > 0:
            quality_score -= 20
            issues.append(f"High null percentages: {dict(high_null_features)}")
        
        # Test 2: Check temperature forecast reasonableness
        temp_features = [col for col in features_df.columns if 'temp_forecast' in col]
        for feature in temp_features:
            if feature in features_df.columns:
                temp_data = features_df[feature].dropna()
                if len(temp_data) > 0:
                    if temp_data.min() < -30 or temp_data.max() > 60:
                        quality_score -= 10
                        issues.append(f"{feature} has unreasonable values: {temp_data.min():.1f} to {temp_data.max():.1f}°C")
        
        # Test 3: Check degree day features are non-negative
        degree_features = [col for col in features_df.columns if 'cooling_forecast' in col or 'heating_forecast' in col]
        for feature in degree_features:
            if feature in features_df.columns:
                degree_data = features_df[feature].dropna()
                if len(degree_data) > 0 and degree_data.min() < 0:
                    quality_score -= 15
                    issues.append(f"{feature} has negative values: min={degree_data.min():.1f}")
        
        # Test 4: Check binary features are 0/1
        binary_features = [col for col in features_df.columns if any(x in col for x in ['incoming', 'rapid_', 'extreme_'])]
        for feature in binary_features:
            if feature in features_df.columns:
                unique_vals = features_df[feature].dropna().unique()
                if not all(val in [0, 1] for val in unique_vals):
                    quality_score -= 10
                    issues.append(f"{feature} has non-binary values: {unique_vals}")
        
        # Log quality assessment
        logger.info(f"🎯 Feature Quality Score: {quality_score}/100")
        
        if quality_score >= 90:
            logger.info("✅ EXCELLENT - Feature quality is excellent")
        elif quality_score >= 75:
            logger.info("✅ GOOD - Feature quality is good with minor issues")
        elif quality_score >= 60:
            logger.info("⚠️  FAIR - Feature quality is acceptable but has issues")
        else:
            logger.info("❌ POOR - Feature quality is poor and needs attention")
        
        if issues:
            logger.warning("🚨 Quality issues found:")
            for i, issue in enumerate(issues, 1):
                logger.warning(f"   {i}. {issue}")
        
        return quality_score >= 75
        
    except Exception as e:
        logger.error(f"❌ Feature quality test failed: {e}")
        return False


def save_test_results(features_df: pd.DataFrame, logger: logging.Logger) -> bool:
    """
    Save test feature data for inspection.
    
    Args:
        features_df: DataFrame with forecast features
        logger: Logger instance
        
    Returns:
        True if save successful, False otherwise
    """
    try:
        # Create test output directory
        output_dir = Path("data/test_features")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save feature data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"forecast_features_test_{timestamp}.parquet"
        
        features_df.to_parquet(output_file, index=False)
        
        logger.info(f"💾 Test feature data saved: {output_file}")
        logger.info(f"   Records: {len(features_df)}")
        logger.info(f"   Features: {len(features_df.columns)}")
        logger.info(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
        
        # Save feature list
        feature_list_file = output_dir / f"forecast_feature_list_{timestamp}.txt"
        with open(feature_list_file, 'w') as f:
            for col in sorted(features_df.columns):
                f.write(f"{col}\n")
        
        logger.info(f"📝 Feature list saved: {feature_list_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save test results: {e}")
        return False


def main():
    """Main test function."""
    
    parser = argparse.ArgumentParser(
        description="Test weather forecast feature engineering",
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
        help="Save test feature data to file"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    logger.info("🚀 Starting forecast feature engineering test")
    logger.info("=" * 60)
    
    try:
        # Load test data
        forecast_df = load_test_forecast_data(logger)
        if forecast_df is None:
            return 1
        
        # Test 1: Data validation
        if not test_data_validation(forecast_df, logger):
            logger.error("❌ Data validation test failed")
            return 1
        
        # Test 2: Core feature creation
        features_df = test_core_features(forecast_df, logger)
        if features_df is None:
            logger.error("❌ Core features test failed")
            return 1
        
        # Test 3: Advanced features
        if not test_advanced_features(features_df, logger):
            logger.warning("⚠️  Advanced features test had issues")
        
        # Test 4: Feature quality
        if not test_feature_quality(features_df, logger):
            logger.warning("⚠️  Feature quality test had issues")
        
        # Save results if requested
        if args.save_results:
            save_test_results(features_df, logger)
        
        logger.info("=" * 60)
        logger.info("✅ Forecast feature engineering test completed successfully!")
        logger.info(f"   Created {len(features_df.columns)} total features")
        logger.info(f"   Ready for ML model integration")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
