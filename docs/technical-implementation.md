# Technical Implementation Guide

This document details the technical implementation of the zone-specific machine learning training system, including code architecture, configuration management, and operational procedures.

## Code Architecture

### Core Components

The system is organized into several key modules that handle different aspects of the machine learning pipeline:

#### Data Ingestion (`src/ingest/`)

**pull_power.py**: Handles CAISO OASIS API integration with proper resource mapping to utility zones. The module implements rate limiting, error handling, and data validation to ensure reliable data collection.

**pull_weather.py**: Integrates weather data from multiple sources including historical weather services and forecast APIs.

**pull_weather_forecasts.py**: Manages real-time weather forecast collection for predictive modeling.

#### Feature Engineering (`src/features/`)

**unified_feature_pipeline.py**: Orchestrates the complete feature engineering process, combining power data, weather data, and forecast information into training-ready datasets.

**build_forecast_features.py**: Creates forecast-specific features including weather change indicators, extreme weather detection, and forecast uncertainty metrics.

#### Model Training (`src/models/`)

**production_config.py**: Defines model configurations, hyperparameters, and zone-specific settings. Contains the core logic for zone-specific parameter optimization and feature selection.

**enhanced_xgboost.py**: Implements the Enhanced XGBoost model class with custom preprocessing, training procedures, and evaluation metrics.

**lightgbm_model.py**: Provides alternative LightGBM implementation for comparison and ensemble methods.

#### API Services (`src/api/`)

**regional_api_server.py**: Serves trained models through REST API endpoints with zone-specific model loading and prediction generation.

#### Prediction Services (`src/prediction/`)

**realtime_forecaster.py**: Handles real-time prediction generation using trained models with proper feature preprocessing and output formatting.

### Training Scripts

#### Automated Pipeline (`scripts/automated_ml_pipeline.py`)

The primary training script that orchestrates the complete machine learning pipeline:

```python
python scripts/automated_ml_pipeline.py --target-zones ALL --skip-cleanup
```

**Command Line Options**:
- `--target-zones`: Specify zones to train (ALL, SYSTEM, NP15, etc.)
- `--skip-cleanup`: Preserve intermediate files for debugging
- `--skip-dataset-refresh`: Use existing feature datasets

The script performs data validation, feature engineering, zone-specific model training, performance evaluation, and deployment in a single automated process.

#### Manual Training Scripts

**train_production_model.py**: Provides manual control over individual model training with custom parameters.

**retrain_production_model.py**: Handles model retraining with existing configurations.

**test_improved_model.py**: Validates model improvements and performance comparisons.

## Configuration Management

### Zone-Specific Configuration

The system uses zone-specific configuration that adapts hyperparameters, preprocessing, and feature engineering based on each zone's characteristics:

```python
def get_zone_specific_params(zone: str) -> Dict:
    zone_params = {
        'NP15': {
            'max_depth': 4,
            'learning_rate': 0.02,
            'reg_alpha': 1.0,
            'reg_lambda': 5.0,
            'subsample': 0.7,
            'colsample_bytree': 0.7,
            'min_child_weight': 5,
            'n_estimators': 2000,
        },
        'SCE': {
            'max_depth': 6,
            'learning_rate': 0.03,
            'reg_alpha': 0.5,
            'reg_lambda': 2.0,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'n_estimators': 1800,
        },
        # Additional zone configurations...
    }
```

### Data Preprocessing Configuration

Zone-specific preprocessing handles different data quality issues and volatility patterns:

```python
def preprocess_zone_data(zone_data, zone: str):
    if zone in ['NP15', 'SCE', 'SMUD']:  # High volatility zones
        # More aggressive outlier removal
        Q1 = load_col.quantile(0.25)
        Q3 = load_col.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 3 * IQR  # Wider bounds for volatile zones
        upper_bound = Q3 + 3 * IQR
        
    if zone in ['NP15', 'SMUD']:
        # Apply light smoothing to reduce noise
        cleaned_data['load'] = 0.7 * original + 0.3 * smoothed
```

### Feature Engineering Configuration

Regional pattern features are configured per zone to capture specific operational characteristics:

```python
def add_regional_pattern_features(df, zone: str):
    if zone == 'NP15':
        # Northern California tech industry patterns
        df['tech_peak_hours'] = ((hour >= 9) & (hour <= 17) & (weekday)).astype(int)
        df['winter_heating'] = ((month.isin([12, 1, 2])) & (hour.isin([7, 8, 18, 19, 20]))).astype(int)
        
    elif zone == 'SCE':
        # Southern California diverse load patterns
        df['desert_cooling'] = ((month.isin([5, 6, 7, 8, 9])) & (hour.isin([13, 14, 15, 16, 17, 18]))).astype(int)
        df['industrial_shift'] = ((hour.isin([6, 7, 14, 15, 22, 23])) & (weekday)).astype(int)
```

## Data Pipeline

### Data Collection Process

The data collection process implements several quality assurance measures:

**Rate Limiting**: CAISO OASIS API calls are limited to 15-second intervals to comply with service terms and ensure reliable data access.

**Resource Mapping**: Clean mapping from CAISO resource identifiers to utility zones, filtering out mixed sources that previously caused data contamination.

**Data Validation**: Automatic validation of data ranges, completeness, and consistency before storage.

### Feature Pipeline

The unified feature pipeline combines multiple data sources:

1. **Power Data Loading**: Loads cleaned CAISO data with proper zone filtering
2. **Weather Data Integration**: Merges historical and forecast weather data
3. **Temporal Feature Creation**: Generates comprehensive time-based features
4. **Lag Feature Generation**: Creates power demand lag features for time series modeling
5. **Weather Interaction Features**: Computes weather-power interaction terms

### Training Data Preparation

Training data preparation uses hybrid strategies:

**Temporal Splitting**: Uses time-based validation splits that respect temporal dependencies in the data.

**Data Weighting**: Recent data receives higher weights (2x) to ensure models adapt to current conditions while maintaining historical pattern recognition.

**Feature Selection**: Automatic feature selection based on availability and zone-specific requirements.

## Model Deployment

### Production Model Structure

Production models are organized in zone-specific directories:

```
data/production_models/
├── SYSTEM/
│   ├── baseline_model_current.joblib
│   ├── enhanced_model_current.joblib
│   └── deployment_metadata.json
├── NP15/
│   ├── baseline_model_current.joblib
│   ├── enhanced_model_current.joblib
│   └── deployment_metadata.json
└── [other zones...]
```

### Backup and Versioning

The system maintains timestamped backups for rollback capability:

```
data/model_backups/
├── 20250830_125555/
│   ├── SYSTEM/
│   │   ├── baseline_model.joblib
│   │   └── enhanced_model.joblib
│   └── [other zones...]
└── [other timestamps...]
```

### API Server Integration

The regional API server automatically loads zone-specific models:

```python
# Zone-specific model loading
for zone in ["SYSTEM", "NP15", "SP15", "SDGE", "SCE", "SMUD", "PGE_VALLEY"]:
    zone_dir = production_models_dir / zone
    baseline_path = zone_dir / "baseline_model_current.joblib"
    enhanced_path = zone_dir / "enhanced_model_current.joblib"
    
    if baseline_path.exists() or enhanced_path.exists():
        available_zones.append(zone)
        zone_model_paths[zone] = {
            'baseline': baseline_path if baseline_path.exists() else None,
            'enhanced': enhanced_path if enhanced_path.exists() else None
        }
```

## Performance Monitoring

### Validation Metrics

The system tracks multiple performance metrics:

**Mean Absolute Percentage Error (MAPE)**: Primary metric for model accuracy assessment.

**R-squared**: Measures model fit quality and explained variance.

**Root Mean Square Error (RMSE)**: Provides absolute error magnitude in MW units.

**Mean Absolute Error (MAE)**: Robust error measurement less sensitive to outliers.

### Automated Quality Checks

Training pipeline includes automatic quality validation:

```python
def validate_model_performance(metrics, zone):
    mape_threshold = 2.0  # 2% MAPE threshold
    r2_threshold = 0.95   # R² threshold
    
    if metrics['mape'] > mape_threshold:
        logger.warning(f"Zone {zone}: MAPE {metrics['mape']:.2f}% exceeds threshold")
        return False
        
    if metrics['r2'] < r2_threshold:
        logger.warning(f"Zone {zone}: R² {metrics['r2']:.4f} below threshold")
        return False
        
    return True
```

### Continuous Integration

The automated pipeline integrates with monitoring systems to track:

- Training success rates
- Model performance trends
- Data quality metrics
- Deployment status
- API server health

## Troubleshooting

### Common Error Patterns

**Memory Issues**: Large datasets may cause memory problems during training. Monitor system resources and consider data sampling for development.

**API Timeouts**: CAISO OASIS API may timeout during data collection. The system implements retry logic with exponential backoff.

**Model Loading Errors**: Check file permissions and model file integrity if models fail to load in production.

### Debugging Procedures

**Enable Debug Logging**: Set logging level to DEBUG for detailed execution information.

**Preserve Intermediate Files**: Use `--skip-cleanup` flag to retain intermediate datasets for analysis.

**Manual Model Testing**: Use individual training scripts to isolate issues in specific zones or components.

### Performance Optimization

**Feature Selection**: Remove unnecessary features to reduce training time and memory usage.

**Hyperparameter Tuning**: Adjust zone-specific parameters based on performance requirements and computational constraints.

**Data Sampling**: Use representative data samples for development and testing to reduce iteration time.
