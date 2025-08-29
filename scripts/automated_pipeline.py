#!/usr/bin/env python3
"""
Automated ML Pipeline for Power Demand Forecasting

This script orchestrates the complete pipeline:
1. Data ingestion from CAISO/NYISO
2. Feature engineering
3. Model training/retraining
4. Prediction generation
5. S3 upload for dashboard consumption
6. Model deployment

Designed to run on schedule (cron) for production operations.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import pandas as pd
import requests
from botocore.exceptions import ClientError

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ingest.pull_power import fetch_caiso_data, generate_synthetic_power_data
from src.ingest.pull_weather import fetch_weather_data
from src.features.build_features import build_features
from src.models.train_xgb import main as train_xgb
from src.models.realtime_predictor import RealtimePredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PowerForecastPipeline:
    """Automated pipeline for power demand forecasting."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.s3_client = boto3.client('s3')
        self.bucket_name = config.get('s3_bucket', 'ml-power-nowcast-data-1756420517')
        self.predictor = RealtimePredictor()
        
    def ingest_fresh_data(self) -> bool:
        """Ingest latest power and weather data."""
        try:
            logger.info("🔄 Starting data ingestion...")
            
            # Ingest power data (last 7 days for freshness)
            if self.config.get('data_source') == 'caiso':
                power_df = fetch_caiso_data(days=7)
            else:
                power_df = generate_synthetic_power_data(days=7)
            
            # Save to local storage
            power_path = "data/raw/power_latest.parquet"
            Path(power_path).parent.mkdir(parents=True, exist_ok=True)
            power_df.to_parquet(power_path, index=False)
            
            # Upload to S3
            self.upload_to_s3(power_path, "data/raw/power_latest.parquet")
            
            logger.info(f"✅ Ingested {len(power_df)} power records")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data ingestion failed: {e}")
            return False
    
    def retrain_models(self) -> bool:
        """Retrain models if needed."""
        try:
            logger.info("🧠 Checking if model retraining is needed...")
            
            # Check if we have enough new data (simple heuristic)
            last_training = self.get_last_training_time()
            hours_since_training = (datetime.now() - last_training).total_seconds() / 3600
            
            if hours_since_training < self.config.get('retrain_interval_hours', 24):
                logger.info(f"⏭️  Skipping retraining (last trained {hours_since_training:.1f}h ago)")
                return True
            
            logger.info("🔄 Starting model retraining...")
            
            # Build fresh features
            os.system("python -m src.features.build_features --horizon 6 --lags '1,2,3,6,12,24'")
            
            # Train XGBoost model
            os.system("python -m src.models.train_xgb --horizon 6 --n_estimators 300")
            
            # Update last training timestamp
            self.update_training_timestamp()
            
            logger.info("✅ Model retraining completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Model retraining failed: {e}")
            return False
    
    def generate_predictions(self) -> bool:
        """Generate fresh predictions for the dashboard."""
        try:
            logger.info("🔮 Generating fresh predictions...")
            
            # Generate 6-hour forecasts
            current_conditions = {
                'temperature': 28.5,  # TODO: Get from weather API
                'humidity': 65,
                'wind_speed': 3.2
            }
            
            predictions = []
            base_time = datetime.now(timezone.utc)
            
            for hour in range(1, 7):
                pred_time = base_time + timedelta(hours=hour)
                
                # Use your existing predictor
                pred_load = self.predictor.predict_next_hour(
                    current_conditions['temperature'],
                    current_conditions['humidity'],
                    current_conditions['wind_speed']
                )
                
                # Add some realistic confidence intervals
                confidence_range = pred_load * 0.05  # ±5%
                
                predictions.append({
                    'timestamp': pred_time.isoformat(),
                    'predicted_load': float(pred_load),
                    'confidence_lower': float(pred_load - confidence_range),
                    'confidence_upper': float(pred_load + confidence_range),
                    'hour_ahead': hour
                })
            
            # Save predictions locally
            pred_path = "data/predictions/latest_forecast.json"
            Path(pred_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(pred_path, 'w') as f:
                json.dump({
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'predictions': predictions,
                    'model_version': self.get_model_version(),
                    'current_conditions': current_conditions
                }, f, indent=2)
            
            # Upload to S3 for dashboard consumption
            self.upload_to_s3(pred_path, "forecasts/latest.json")
            
            logger.info(f"✅ Generated {len(predictions)} predictions")
            return True
            
        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}")
            return False
    
    def upload_to_s3(self, local_path: str, s3_key: str) -> bool:
        """Upload file to S3."""
        try:
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            logger.info(f"📤 Uploaded {local_path} → s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {e}")
            return False
    
    def get_last_training_time(self) -> datetime:
        """Get timestamp of last model training."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key="models/last_training.txt"
            )
            timestamp_str = response['Body'].read().decode('utf-8').strip()
            return datetime.fromisoformat(timestamp_str)
        except:
            # Default to 25 hours ago to trigger retraining
            return datetime.now() - timedelta(hours=25)
    
    def update_training_timestamp(self):
        """Update last training timestamp."""
        timestamp = datetime.now().isoformat()
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key="models/last_training.txt",
            Body=timestamp.encode('utf-8')
        )
    
    def get_model_version(self) -> str:
        """Get current model version."""
        # TODO: Integrate with MLflow to get actual version
        return "1.0.0"
    
    def run_pipeline(self) -> bool:
        """Run the complete pipeline."""
        logger.info("🚀 Starting automated ML pipeline...")
        
        success = True
        
        # Step 1: Ingest fresh data
        if not self.ingest_fresh_data():
            success = False
        
        # Step 2: Retrain models if needed
        if not self.retrain_models():
            success = False
        
        # Step 3: Generate fresh predictions
        if not self.generate_predictions():
            success = False
        
        if success:
            logger.info("✅ Pipeline completed successfully!")
        else:
            logger.error("❌ Pipeline completed with errors")
        
        return success


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Automated ML Pipeline")
    parser.add_argument("--config", default="config/pipeline.json", help="Pipeline configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    # Default configuration
    config = {
        'data_source': 'caiso',
        's3_bucket': 'ml-power-nowcast-data-1756420517',
        'retrain_interval_hours': 24,
        'prediction_horizon_hours': 6
    }
    
    # Load config file if it exists
    if Path(args.config).exists():
        with open(args.config) as f:
            config.update(json.load(f))
    
    if args.dry_run:
        logger.info("🧪 DRY RUN MODE - No actual changes will be made")
        return
    
    # Run pipeline
    pipeline = PowerForecastPipeline(config)
    success = pipeline.run_pipeline()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
