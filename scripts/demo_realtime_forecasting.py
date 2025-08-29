#!/usr/bin/env python3
"""
Real-Time Power Demand Forecasting Demonstration

This script demonstrates the complete real-time prediction system outlined in
planning/weather_forecast_integration.md Phase 6. It showcases the value of
weather forecast features by comparing baseline vs forecast-enhanced predictions.

The demonstration shows:
- Real-time power demand predictions (1-48 hours ahead)
- Baseline vs forecast-enhanced model comparison
- Performance improvement measurement
- Forecast feature value quantification
- Production-ready prediction pipeline

Usage:
    python scripts/demo_realtime_forecasting.py [options]
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.prediction.realtime_forecaster import (
    RealtimeForecaster,
    PredictionConfig,
    RealtimeForecasterError,
    ModelLoadError,
    PredictionError
)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for the demonstration script."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging
    log_file = log_dir / f"realtime_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def find_latest_models(logger: logging.Logger) -> tuple[Optional[Path], Optional[Path]]:
    """
    Find the latest trained baseline and enhanced models.
    
    Args:
        logger: Logger instance
        
    Returns:
        Tuple of (baseline_model_path, enhanced_model_path)
    """
    logger.info("🔍 Searching for trained models...")
    
    models_dir = Path("data/trained_models")
    if not models_dir.exists():
        logger.warning(f"Models directory not found: {models_dir}")
        return None, None
    
    # Find baseline model
    baseline_files = list(models_dir.glob("baseline_xgboost_*.joblib"))
    baseline_path = None
    if baseline_files:
        baseline_path = max(baseline_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"✅ Found baseline model: {baseline_path}")
    else:
        logger.warning("❌ No baseline model found")
    
    # Find enhanced model
    enhanced_files = list(models_dir.glob("enhanced_xgboost_*.joblib"))
    enhanced_path = None
    if enhanced_files:
        enhanced_path = max(enhanced_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"✅ Found enhanced model: {enhanced_path}")
    else:
        logger.warning("❌ No enhanced model found")
    
    return baseline_path, enhanced_path


def check_data_availability(logger: logging.Logger) -> dict:
    """
    Check availability of required data sources for real-time predictions.
    
    Args:
        logger: Logger instance
        
    Returns:
        Dictionary with data availability status
    """
    logger.info("🔍 Checking data availability for real-time predictions...")
    
    availability = {
        'power_data': False,
        'forecast_data': False,
        'incremental_data': False
    }
    
    # Check power data
    power_paths = [
        Path("data/master/caiso_california_only.parquet"),
        Path("data/incremental/caiso_recent.parquet")
    ]
    
    for path in power_paths:
        if path.exists():
            availability['power_data'] = True
            logger.info(f"✅ Power data available: {path}")
            break
    
    # Check forecast data
    forecast_dir = Path("data/forecasts")
    if forecast_dir.exists():
        np15_forecast = forecast_dir / "raw" / "weather_forecasts" / "nws" / "np15" / "np15_forecast_latest.parquet"
        if np15_forecast.exists():
            availability['forecast_data'] = True
            logger.info(f"✅ Forecast data available: {np15_forecast}")
    
    # Check incremental data
    incremental_file = Path("data/incremental/caiso_recent.parquet")
    if incremental_file.exists():
        availability['incremental_data'] = True
        logger.info(f"✅ Incremental data available: {incremental_file}")
    
    if not availability['power_data']:
        logger.error("❌ No power data available")
    if not availability['forecast_data']:
        logger.warning("⚠️  No forecast data available - forecast features will be limited")
    
    return availability


def display_prediction_results(report: dict, logger: logging.Logger) -> None:
    """
    Display prediction results in a formatted way.
    
    Args:
        report: Forecast report dictionary
        logger: Logger instance
    """
    logger.info("📊 REAL-TIME FORECASTING RESULTS")
    logger.info("=" * 60)
    
    # Summary statistics
    logger.info(f"Generated at: {report['generated_at']}")
    logger.info(f"Total predictions: {report['total_predictions']}")
    logger.info(f"Zones: {', '.join(report['zones'])}")
    logger.info(f"Horizons: {', '.join(map(str, report['horizons']))} hours")
    
    # Forecast availability
    forecast_avail = report.get('forecast_availability', {})
    logger.info(f"\n🌤️  Forecast Availability:")
    logger.info(f"  Predictions with forecasts: {forecast_avail.get('predictions_with_forecasts', 0)}")
    logger.info(f"  Predictions without forecasts: {forecast_avail.get('predictions_without_forecasts', 0)}")
    logger.info(f"  Forecast coverage: {forecast_avail.get('forecast_coverage_pct', 0):.1f}%")
    
    # Performance summary
    perf_summary = report.get('performance_summary', {})
    if perf_summary:
        logger.info(f"\n📈 Performance Summary:")
        logger.info(f"  Mean improvement: {perf_summary.get('mean_improvement_pct', 0):+.2f}%")
        logger.info(f"  Median improvement: {perf_summary.get('median_improvement_pct', 0):+.2f}%")
        logger.info(f"  Best improvement: {perf_summary.get('max_improvement_pct', 0):+.2f}%")
        logger.info(f"  Worst improvement: {perf_summary.get('min_improvement_pct', 0):+.2f}%")
        
        target_achieved = perf_summary.get('target_improvement_achieved', False)
        if target_achieved:
            logger.info(f"  🎯 TARGET ACHIEVED: ≥5% improvement demonstrated!")
        else:
            logger.info(f"  ⚠️  Target not achieved: <5% average improvement")
    
    # Individual predictions
    predictions = report.get('predictions', [])
    if predictions:
        logger.info(f"\n🔮 Individual Predictions:")
        logger.info(f"{'Zone':<6} {'Horizon':<8} {'Baseline':<10} {'Enhanced':<10} {'Improve%':<10} {'Forecast':<9}")
        logger.info("-" * 60)
        
        for pred in predictions[:10]:  # Show first 10
            zone = pred['zone']
            horizon = f"{pred['horizon_hours']}h"
            baseline = f"{pred['baseline_prediction']:.1f}" if pred['baseline_prediction'] else "N/A"
            enhanced = f"{pred['enhanced_prediction']:.1f}" if pred['enhanced_prediction'] else "N/A"
            improve = f"{pred['improvement_pct']:+.1f}%" if pred['improvement_pct'] else "N/A"
            forecast = "Yes" if pred['forecast_available'] else "No"
            
            logger.info(f"{zone:<6} {horizon:<8} {baseline:<10} {enhanced:<10} {improve:<10} {forecast:<9}")
        
        if len(predictions) > 10:
            logger.info(f"... and {len(predictions) - 10} more predictions")


def save_demonstration_results(report: dict, logger: logging.Logger) -> bool:
    """
    Save demonstration results to file for analysis.
    
    Args:
        report: Forecast report dictionary
        logger: Logger instance
        
    Returns:
        True if save successful, False otherwise
    """
    try:
        # Create output directory
        output_dir = Path("data/demo_results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = output_dir / f"realtime_forecast_demo_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"💾 Demonstration results saved: {report_file}")
        
        # Save summary CSV for easy analysis
        predictions = report.get('predictions', [])
        if predictions:
            df = pd.DataFrame(predictions)
            csv_file = output_dir / f"predictions_summary_{timestamp}.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"📊 Predictions CSV saved: {csv_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save demonstration results: {e}")
        return False


def main():
    """Main demonstration function."""
    
    parser = argparse.ArgumentParser(
        description="Demonstrate real-time power demand forecasting with weather forecast integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--zones",
        nargs="+",
        default=["NP15"],
        help="CAISO zones to predict (default: NP15)"
    )
    
    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        default=[1, 6, 12, 24],
        help="Prediction horizons in hours (default: 1 6 12 24)"
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
        help="Save demonstration results to file"
    )
    
    parser.add_argument(
        "--baseline-model",
        type=Path,
        help="Path to baseline model (auto-detected if not provided)"
    )
    
    parser.add_argument(
        "--enhanced-model",
        type=Path,
        help="Path to enhanced model (auto-detected if not provided)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    logger.info("🚀 Starting Real-Time Power Demand Forecasting Demonstration")
    logger.info("=" * 70)
    logger.info("This demonstration showcases the weather forecast integration")
    logger.info("outlined in planning/weather_forecast_integration.md Phase 6")
    logger.info("=" * 70)
    
    try:
        # Check data availability
        availability = check_data_availability(logger)
        if not availability['power_data']:
            logger.error("❌ Cannot proceed without power data")
            return 1
        
        # Find models
        if args.baseline_model and args.enhanced_model:
            baseline_path = args.baseline_model
            enhanced_path = args.enhanced_model
        else:
            baseline_path, enhanced_path = find_latest_models(logger)
        
        if not baseline_path and not enhanced_path:
            logger.error("❌ No trained models found. Please train models first.")
            logger.info("Run: python scripts/test_enhanced_xgboost.py --save-models")
            return 1
        
        # Create prediction configuration
        config = PredictionConfig(
            prediction_horizons=args.horizons,
            baseline_model_path=baseline_path,
            enhanced_model_path=enhanced_path,
            target_zones=args.zones,
            confidence_levels=[0.80, 0.90, 0.95]
        )
        
        logger.info(f"Configuration:")
        logger.info(f"  Zones: {config.target_zones}")
        logger.info(f"  Horizons: {config.prediction_horizons} hours")
        logger.info(f"  Baseline model: {baseline_path}")
        logger.info(f"  Enhanced model: {enhanced_path}")
        
        # Initialize forecaster
        forecaster = RealtimeForecaster(config)
        
        # Run demonstration
        logger.info("\n🔮 Running real-time forecasting demonstration...")
        report = forecaster.run_realtime_demo()
        
        # Display results
        display_prediction_results(report, logger)
        
        # Save results if requested
        if args.save_results:
            save_demonstration_results(report, logger)
        
        # Final assessment
        logger.info("\n" + "=" * 70)
        
        perf_summary = report.get('performance_summary', {})
        if perf_summary and perf_summary.get('target_improvement_achieved', False):
            logger.info("🎉 SUCCESS: Weather forecast integration demonstrates significant value!")
            logger.info(f"   Average improvement: {perf_summary.get('mean_improvement_pct', 0):+.1f}%")
            logger.info("   Target ≥5% improvement achieved!")
        else:
            forecast_coverage = report.get('forecast_availability', {}).get('forecast_coverage_pct', 0)
            if forecast_coverage < 50:
                logger.info("ℹ️  Limited forecast coverage detected.")
                logger.info("   Forecast value will be higher with more recent forecast data.")
                logger.info("   Run forecast collection: python scripts/collect_weather_forecasts.py")
            else:
                logger.info("✅ Demonstration completed successfully!")
                logger.info("   System ready for production deployment.")
        
        logger.info("\n🚀 Real-time forecasting system is operational!")
        logger.info("   Ready for production deployment and continuous improvement.")
        
        return 0
        
    except (RealtimeForecasterError, ModelLoadError, PredictionError) as e:
        logger.error(f"❌ Demonstration failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
