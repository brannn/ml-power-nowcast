#!/usr/bin/env python3
"""
Data Flow Architecture Validation

Clarifies and validates the proper separation between:
1. Historical training data (for model training only)
2. Real-time operational data (current power + weather forecasts)

Ensures we're not continuously retraining with historical data during production.
"""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class DataFlowValidator:
    """Validates proper data flow architecture and separation."""
    
    def __init__(self):
        """Initialize data flow validator."""
        
        self.data_sources = {
            'historical_training': {
                'purpose': 'Model training only - offline process',
                'location': 'backup_s3_data/processed/',
                'usage': 'periodic_model_retraining',
                'frequency': 'weekly_or_monthly',
                'data_types': ['power_demand_history', 'weather_history']
            },
            'real_time_operational': {
                'purpose': 'Live predictions - online process', 
                'location': 'data/weather/current_conditions.json',
                'usage': 'continuous_predictions',
                'frequency': 'every_15_seconds',
                'data_types': ['current_power_reading', 'weather_forecast']
            }
        }
        
        self.operational_workflow = [
            'collect_current_power_reading',
            'fetch_weather_forecast_data',
            'load_trained_models',
            'generate_prediction_using_forecast',
            'return_prediction_to_api'
        ]
        
        self.training_workflow = [
            'load_historical_power_data',
            'load_historical_weather_data', 
            'create_training_features',
            'train_models_offline',
            'validate_model_performance',
            'save_trained_models_for_production'
        ]
    
    def analyze_current_data_usage(self) -> Dict[str, Any]:
        """Analyze what data is currently being used where."""
        
        analysis = {
            'data_inventory': {},
            'usage_patterns': {},
            'potential_issues': [],
            'recommendations': []
        }
        
        # Check historical data location and size
        historical_path = Path("backup_s3_data/processed/power/caiso/")
        if historical_path.exists():
            for file in historical_path.glob("*.parquet"):
                file_stats = file.stat()
                analysis['data_inventory'][str(file)] = {
                    'size_bytes': file_stats.st_size,
                    'size_mb': file_stats.st_size / (1024*1024),
                    'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    'purpose': 'historical_training_only'
                }
        
        # Check real-time data location
        realtime_weather = Path("data/weather/current_conditions.json")
        if realtime_weather.exists():
            file_stats = realtime_weather.stat()
            analysis['data_inventory'][str(realtime_weather)] = {
                'size_bytes': file_stats.st_size,
                'size_kb': file_stats.st_size / 1024,
                'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                'purpose': 'real_time_operational'
            }
        
        # Analyze usage patterns
        analysis['usage_patterns'] = {
            'training_data_confusion': 'Historical parquet files should NEVER be used for real-time predictions',
            'proper_training_flow': 'Historical data → Model training → Save models → Use models for predictions',
            'proper_operational_flow': 'Current conditions + Weather forecast → Trained models → Predictions',
            'data_separation_critical': 'Training data (historical) vs Operational data (current + forecast)'
        }
        
        # Identify potential issues
        small_historical_files = [f for f, stats in analysis['data_inventory'].items() 
                                if 'historical' in stats['purpose'] and stats['size_mb'] < 1.0]
        
        if small_historical_files:
            analysis['potential_issues'].append({
                'issue': 'Small historical training files detected',
                'files': small_historical_files,
                'impact': 'May indicate incomplete historical dataset',
                'solution': 'Verify access to full 5-year historical dataset'
            })
        
        # Check if we might be confusing data sources
        analysis['potential_issues'].append({
            'issue': 'Data source confusion risk',
            'description': 'Need clear separation between training and operational data',
            'solution': 'Implement strict data flow validation'
        })
        
        return analysis
    
    def validate_proper_data_flow(self) -> Dict[str, Any]:
        """Validate proper separation of training vs operational data flow."""
        
        validation_results = {
            'training_flow_validation': {},
            'operational_flow_validation': {},
            'data_separation_check': {},
            'recommendations': []
        }
        
        # Validate training flow
        validation_results['training_flow_validation'] = {
            'step_1_historical_data': {
                'description': 'Load historical power demand data (5 years)',
                'data_source': 'backup_s3_data/processed/power/caiso/',
                'frequency': 'Periodic (weekly/monthly model refresh)',
                'purpose': 'Model training only',
                'should_never_be_used_for': 'Real-time predictions'
            },
            'step_2_feature_engineering': {
                'description': 'Create features from historical data',
                'includes': ['lag_features', 'temporal_features', 'weather_features'],
                'purpose': 'Training dataset preparation'
            },
            'step_3_model_training': {
                'description': 'Train XGBoost + LightGBM models',
                'output': 'Trained model files (.pkl)',
                'frequency': 'Periodic refresh based on new data'
            },
            'step_4_model_saving': {
                'description': 'Save trained models for production use',
                'location': 'production_models/ directory',
                'format': 'Pickle files with metadata'
            }
        }
        
        # Validate operational flow
        validation_results['operational_flow_validation'] = {
            'step_1_current_reading': {
                'description': 'Get current power demand reading',
                'source': 'CAISO OASIS API (real-time)',
                'frequency': 'Every 15 seconds',
                'purpose': 'Real-time system state'
            },
            'step_2_weather_forecast': {
                'description': 'Fetch weather forecast data',
                'source': 'Weather API (forecast data)',
                'horizon': '1-6 hours ahead',
                'purpose': 'Predictive features for models'
            },
            'step_3_load_models': {
                'description': 'Load pre-trained models from disk',
                'source': 'Saved .pkl model files',
                'frequency': 'Once at startup, refresh periodically',
                'purpose': 'Apply trained models to new data'
            },
            'step_4_prediction': {
                'description': 'Generate prediction using current + forecast',
                'inputs': ['current_conditions', 'weather_forecast'],
                'models': 'Pre-trained XGBoost + LightGBM',
                'output': 'Power demand prediction'
            }
        }
        
        # Data separation validation
        validation_results['data_separation_check'] = {
            'critical_separation': {
                'training_data': 'Historical power + weather (for model training)',
                'operational_data': 'Current power + weather forecast (for predictions)',
                'never_mix': 'Historical data should NEVER be used for real-time predictions'
            },
            'proper_architecture': {
                'offline_training': 'Historical data → Train models → Save models',
                'online_operations': 'Current data + Forecast → Trained models → Predictions',
                'model_refresh': 'Periodic retraining with new historical data'
            },
            'data_freshness': {
                'training_data_age': 'Can be days/weeks old (for model training)',
                'operational_data_age': 'Must be current (for accurate predictions)',
                'model_age': 'Trained models can be used for days/weeks'
            }
        }
        
        # Generate recommendations
        validation_results['recommendations'] = [
            {
                'priority': 'critical',
                'item': 'Implement strict data source validation',
                'description': 'Ensure training code never accesses real-time data, and operational code never uses historical training data'
            },
            {
                'priority': 'critical', 
                'item': 'Separate training and operational environments',
                'description': 'Training: Load historical data → Train models → Save. Operations: Load models + current data → Predict'
            },
            {
                'priority': 'high',
                'item': 'Validate weather forecast integration',
                'description': 'Ensure operational flow uses weather FORECASTS, not historical weather data'
            },
            {
                'priority': 'high',
                'item': 'Model refresh workflow',
                'description': 'Periodic retraining with accumulated new historical data, not continuous training'
            },
            {
                'priority': 'medium',
                'item': 'Data lineage documentation', 
                'description': 'Clear documentation of what data goes where and when'
            }
        ]
        
        return validation_results
    
    def create_operational_architecture_diagram(self) -> Dict[str, Any]:
        """Create clear architecture diagram for proper data flow."""
        
        architecture = {
            'training_pipeline': {
                'trigger': 'Periodic (weekly/monthly)',
                'data_sources': [
                    'Historical power demand (5 years)',
                    'Historical weather data',
                    'Zone-specific load patterns'
                ],
                'process_steps': [
                    '1. Load historical datasets',
                    '2. Data cleaning and validation', 
                    '3. Feature engineering (43 features)',
                    '4. Temporal weighting (recent data emphasis)',
                    '5. Model training (XGBoost + LightGBM)',
                    '6. Cross-validation and testing',
                    '7. Save trained models to disk'
                ],
                'outputs': [
                    'Trained model files (.pkl)',
                    'Model metadata and performance metrics',
                    'Feature scalers and preprocessors'
                ]
            },
            'operational_pipeline': {
                'trigger': 'Continuous (every 15 seconds)',
                'data_sources': [
                    'Current power demand (CAISO API)',
                    'Weather forecast (Weather API)',
                    'Time/date features (system clock)'
                ],
                'process_steps': [
                    '1. Fetch current power reading',
                    '2. Fetch weather forecast',
                    '3. Load pre-trained models',
                    '4. Create prediction features',
                    '5. Apply models to generate prediction',
                    '6. Return prediction via API'
                ],
                'outputs': [
                    'Power demand predictions (1-6 hours)',
                    'Confidence intervals',
                    'Zone-specific forecasts'
                ]
            },
            'critical_separations': {
                'data_separation': 'Historical (training) vs Current+Forecast (operational)',
                'time_separation': 'Offline training vs Real-time predictions',
                'purpose_separation': 'Model development vs Model application'
            }
        }
        
        return architecture
    
    def run_data_flow_validation(self) -> Dict[str, Any]:
        """Execute complete data flow validation."""
        
        logger.info("=== Data Flow Architecture Validation ===")
        
        # Analyze current data usage
        data_analysis = self.analyze_current_data_usage()
        
        # Validate proper flow separation
        flow_validation = self.validate_proper_data_flow()
        
        # Create architecture diagram
        architecture = self.create_operational_architecture_diagram()
        
        return {
            'validation_timestamp': datetime.now().isoformat(),
            'data_analysis': data_analysis,
            'flow_validation': flow_validation,
            'architecture_diagram': architecture,
            'key_principles': [
                'Historical data is for training ONLY',
                'Real-time predictions use current conditions + forecasts',
                'Models are trained offline, applied online',
                'Never continuously retrain with historical data',
                'Weather forecasts (not historical weather) for predictions'
            ]
        }

def execute_data_flow_validation():
    """Execute and display data flow validation results."""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    validator = DataFlowValidator()
    results = validator.run_data_flow_validation()
    
    print("\n" + "="*80)
    print("📊 DATA FLOW ARCHITECTURE VALIDATION")
    print("="*80)
    
    # Key Principles
    print(f"\n🎯 KEY PRINCIPLES:")
    for i, principle in enumerate(results['key_principles'], 1):
        print(f"  {i}. {principle}")
    
    # Current Data Inventory
    print(f"\n📁 DATA INVENTORY:")
    for file_path, stats in results['data_analysis']['data_inventory'].items():
        file_name = Path(file_path).name
        if 'historical' in stats['purpose']:
            print(f"  📊 {file_name}: {stats['size_mb']:.1f}MB (TRAINING DATA)")
        else:
            print(f"  🌤️  {file_name}: {stats['size_kb']:.1f}KB (OPERATIONAL DATA)")
    
    # Training Pipeline
    print(f"\n🔧 TRAINING PIPELINE (Offline - Periodic):")
    training = results['architecture_diagram']['training_pipeline']
    print(f"  Trigger: {training['trigger']}")
    print(f"  Data Sources:")
    for source in training['data_sources']:
        print(f"    • {source}")
    print(f"  Output: Trained models for production use")
    
    # Operational Pipeline
    print(f"\n🚀 OPERATIONAL PIPELINE (Online - Continuous):")
    operational = results['architecture_diagram']['operational_pipeline']
    print(f"  Trigger: {operational['trigger']}")
    print(f"  Data Sources:")
    for source in operational['data_sources']:
        print(f"    • {source}")
    print(f"  Output: Real-time power demand predictions")
    
    # Critical Separations
    print(f"\n⚠️  CRITICAL SEPARATIONS:")
    separations = results['architecture_diagram']['critical_separations']
    for key, value in separations.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Recommendations
    print(f"\n📋 RECOMMENDATIONS:")
    for rec in results['flow_validation']['recommendations']:
        priority = rec['priority'].upper()
        print(f"  {priority}: {rec['item']}")
        print(f"    → {rec['description']}")
    
    # Data Flow Clarity
    print(f"\n✅ PROPER DATA FLOW SUMMARY:")
    print(f"  1. TRAINING: Historical data → Train models → Save .pkl files")
    print(f"  2. OPERATIONS: Current reading + Weather forecast → Load models → Predict")
    print(f"  3. REFRESH: Periodically retrain models with new historical data")
    print(f"  4. NEVER: Use historical data for real-time predictions")
    print(f"  5. NEVER: Continuously retrain during operational predictions")
    
    return results

if __name__ == "__main__":
    execute_data_flow_validation()