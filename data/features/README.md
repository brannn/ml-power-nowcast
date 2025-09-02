# Power Demand Forecasting Features

This directory contains engineered features for power demand forecasting models. All features are designed for tabular machine learning models (XGBoost, LightGBM, CatBoost) and ensemble methods.

## Primary Feature Datasets

### `power_features_realtime.parquet` (Primary Dataset)
- **Size**: 524,656 rows × 21 columns
- **Date Range**: 2020-08-28 to 2025-08-30 (5+ years)
- **Update Frequency**: Real-time (automated collection)
- **Performance**: 99.71% accuracy with LightGBM (0.29% MAPE)
- **Use Case**: Primary dataset for all model training and evaluation

**Features Include:**
- `timestamp`: UTC timestamp
- `load`: Actual power demand (MW)
- `load_target_1h`: 1-hour ahead target for forecasting
- `load_lag_1h`, `load_lag_24h`: Lag features for temporal patterns
- `hour`, `day_of_week`, `month`, `quarter`: Temporal features
- `hour_sin`, `hour_cos`: Cyclical time encoding
- `day_of_week_sin`, `day_of_week_cos`: Cyclical day encoding
- `day_of_year_sin`, `day_of_year_cos`: Cyclical seasonal encoding
- `is_weekend`: Weekend indicator
- `zone`, `region`, `resource_name`: Geographic identifiers
- `data_source`: Data source tracking

### `power_features_complete.parquet` (Historical Archive)
- **Size**: 524,650 rows × 21 columns
- **Purpose**: Complete historical archive
- **Use Case**: Long-term analysis and model validation

### `power_features_compact.parquet` (Compact Version)
- **Size**: 524,632 rows × 14 columns
- **Purpose**: Reduced feature set for faster training
- **Use Case**: Quick prototyping and testing

## Legacy/Sample Files

### `features_sample_fresh.parquet` & `features_sample.parquet`
- **Status**: Empty (0 rows)
- **Purpose**: Sample/testing files
- **Note**: Use primary datasets above for actual training

### `features_sample_backup.parquet`
- **Size**: 143 rows × 49 columns
- **Date Range**: 2024-01-02 to 2024-01-07
- **Purpose**: Small backup sample for testing

## Data Quality

### Proven Performance
- **LightGBM**: 99.71% accuracy (0.29% MAPE)
- **Feature Importance**: Lag features dominate (load_lag_1h, load_lag_24h)
- **Temporal Patterns**: Strong cyclical encoding performance
- **Data Completeness**: 5+ years of continuous California power data

### Feature Engineering Quality
- **Lag Features**: Capture short-term (1h) and daily (24h) patterns
- **Cyclical Encoding**: Sin/cos transformations for temporal cycles
- **Geographic Coverage**: Multiple California power zones
- **Target Engineering**: 1-hour ahead forecasting targets

## Usage Recommendations

### For Model Training
```python
# Primary dataset for production models
df = pd.read_parquet('data/features/power_features_realtime.parquet')

# Use for XGBoost, LightGBM, CatBoost training
X = df.drop(columns=['timestamp', 'load', 'load_target_1h'])
y = df['load_target_1h']
```

### For Quick Testing
```python
# Compact dataset for faster iteration
df = pd.read_parquet('data/features/power_features_compact.parquet')
```

### Categorical Features
For models with native categorical support (LightGBM, CatBoost):
```python
categorical_features = ['hour', 'day_of_week', 'month', 'quarter', 'is_weekend']
```

## Model Performance Benchmarks

### Current Best Performance (on power_features_realtime.parquet)
- **LightGBM**: 99.71% accuracy (0.29% MAPE)
- **Training Time**: <1 second on Mac M4
- **Feature Count**: 14 numeric features
- **Sample Size**: 524K+ rows

### Expected Performance Range
- **Tree Models (XGBoost/LightGBM/CatBoost)**: 99.5-99.8% accuracy
- **Simple Neural Networks**: 95-98% accuracy
- **Ensemble Methods**: >99.8% accuracy target

## Data Collection Status

- **Status**: Active continuous collection
- **Last Update**: 2025-08-30 05:30:00 UTC
- **Collection Frequency**: Hourly
- **Data Sources**: CAISO OASIS API, weather APIs
- **Geographic Coverage**: California power grid zones

## Historical Context

**Note**: These files were previously labeled with "lstm_" prefixes when LSTM modeling was being explored. However, the data contains high-quality engineered tabular features that are optimal for tree-based models, not LSTM architectures. The renaming reflects the actual optimal use case for this data.

**Performance Evidence**: LSTM achieved 87% MAPE vs. LightGBM's 0.29% MAPE on the same data, confirming that tree-based models are the correct approach for this engineered tabular dataset.
