# Model Training and Operations Guide

This document provides a comprehensive overview of the machine learning model training system for California power demand forecasting. The system implements zone-specific models that achieve sub-1% mean absolute percentage error (MAPE) across all California Independent System Operator (CAISO) utility zones.

## System Overview

The ML Power Nowcast system trains separate predictive models for each California utility zone, including system-wide aggregates. The architecture addresses the unique load patterns, volatility characteristics, and operational requirements of different utility territories within the CAISO grid.

### Supported Zones

The system trains models for seven distinct zones:

- **SYSTEM**: California ISO system-wide total load
- **NP15**: Northern California (PG&E territory north of Path 15)
- **SP15**: Southern California (primary load centers)
- **SCE**: Southern California Edison territory
- **SDGE**: San Diego Gas & Electric territory
- **SMUD**: Sacramento Municipal Utility District
- **PGE_VALLEY**: Central Valley region served by PG&E

Each zone represents distinct load characteristics, weather patterns, and operational constraints that require specialized modeling approaches.

## Data Architecture

### Data Sources and Quality

The training system uses cleaned CAISO OASIS data that has been processed to remove mixed-source contamination. Historical data collection identified significant data quality issues where utility zones contained readings from multiple disparate sources, including water district pumping loads and small municipal utilities that created modeling artifacts.

The data cleaning process filters to primary utility sources only:

- **SCE-TAC**: Southern California Edison primary measurements
- **PGE-TAC**: Pacific Gas & Electric primary measurements  
- **SDGE-TAC**: San Diego Gas & Electric measurements
- **SMUD-TAC** and **BANCSMUD**: Sacramento Municipal Utility District measurements
- **CA ISO-TAC**: System-wide California ISO measurements
- **LADWP**: Los Angeles Department of Water and Power measurements

This filtering removes approximately 52.7% of the original dataset but eliminates data corruption that previously caused model performance degradation.

### Feature Engineering

The system implements zone-specific feature engineering that captures regional patterns and operational characteristics:

#### Temporal Features

Base temporal features include hour of day, day of week, month, and seasonal indicators. Advanced temporal features use multiple harmonic representations to capture complex daily and seasonal cycles.

#### Regional Pattern Features

Zone-specific features capture unique operational patterns:

**Northern California (NP15)**: Technology industry load patterns with distinct business hour peaks, residential evening loads, and seasonal heating/cooling patterns influenced by coastal and inland climate variations.

**Southern California Edison (SCE)**: Diverse load patterns reflecting metropolitan Los Angeles, desert regions, and coastal areas. Features capture extreme summer cooling demands, industrial shift patterns, and transition hour volatility.

**Sacramento Municipal Utility District (SMUD)**: Municipal utility patterns with agricultural influences, valley heat effects, and predictable weekend patterns characteristic of smaller utility territories.

**San Diego Gas & Electric (SDGE)**: Coastal climate moderation features, tourism seasonal effects, and moderate temperature-driven load variations.

#### Weather Integration

Weather features incorporate temperature, humidity, wind speed, and derived metrics such as cooling degree days and heating degree days. The system includes weather forecast integration for predictive modeling.

## Model Architecture

### Algorithm Selection

The system uses Enhanced XGBoost models as the primary algorithm. XGBoost provides robust performance for time series forecasting with complex feature interactions while maintaining computational efficiency for operational deployment.

Two model variants are trained for each zone:

**Baseline Models**: Use core temporal and lag features with conservative hyperparameters optimized for stability and interpretability.

**Enhanced Models**: Incorporate advanced temporal features, weather interactions, and zone-specific pattern recognition with optimized hyperparameters for maximum predictive accuracy.

### Zone-Specific Hyperparameter Optimization

Hyperparameters are tuned based on each zone's volatility characteristics and data quality:

**High-Volatility Zones** (NP15, SCE, SMUD): Use deeper regularization, slower learning rates, and aggressive subsampling to handle noise and prevent overfitting to volatile patterns.

**Stable Zones** (SYSTEM, SDGE, SP15, PGE_VALLEY): Use optimized parameters that balance model complexity with training efficiency while maintaining high accuracy.

### Data Preprocessing

Zone-specific preprocessing addresses data quality issues and volatility:

**Outlier Detection**: Uses interquartile range methods with zone-appropriate thresholds. High-volatility zones use wider bounds (3x IQR) while stable zones use standard bounds (1.5x IQR).

**Smoothing**: Applies light smoothing to extremely volatile zones using rolling averages that preserve patterns while reducing noise.

**Missing Data Handling**: Implements linear interpolation for sparse missing values and removes periods with extensive data gaps.

## Training Pipeline

### Automated Training Process

The automated training pipeline executes daily to maintain model currency and performance. The process includes:

**Data Validation**: Verifies data freshness, completeness, and quality metrics before training initiation.

**Zone-Specific Processing**: Applies appropriate preprocessing, feature engineering, and hyperparameter selection for each zone.

**Model Training**: Trains both baseline and enhanced models using hybrid training strategies that weight recent data more heavily while maintaining historical pattern recognition.

**Performance Validation**: Validates model performance against established thresholds before deployment.

**Deployment**: Updates production models with automatic backup and rollback capabilities.

### Hybrid Training Strategy

The training process uses a hybrid approach that combines historical data for pattern learning with recent data weighting for current condition adaptation. Recent data (last 25% of training period) receives 2x weighting to ensure models adapt to evolving load patterns while maintaining long-term seasonal understanding.

### Model Validation

Validation uses time-based splits that respect temporal dependencies. Models are evaluated on out-of-sample data using multiple metrics:

- **Mean Absolute Percentage Error (MAPE)**: Primary performance metric
- **R-squared**: Model fit quality assessment  
- **Root Mean Square Error (RMSE)**: Absolute error magnitude
- **Mean Absolute Error (MAE)**: Robust error measurement

Performance thresholds require MAPE below 2% for deployment approval, with most zones achieving sub-1% performance.

## Operational Deployment

### Production Model Management

Production models are deployed in zone-specific directories with versioning and backup systems. Each deployment includes:

- Current production models (baseline and enhanced variants)
- Timestamped backups for rollback capability
- Deployment metadata with performance metrics
- Model configuration and feature specifications

### Continuous Monitoring

The system monitors model performance through:

**Real-time Prediction Accuracy**: Tracks prediction errors against actual load measurements.

**Data Quality Metrics**: Monitors input data for anomalies, missing values, and distribution shifts.

**Model Drift Detection**: Identifies when model performance degrades due to changing load patterns.

### API Integration

Production models serve predictions through a regional API server that:

- Loads zone-specific models automatically
- Provides real-time predictions with confidence intervals
- Handles zone-specific feature preprocessing
- Returns predictions in standardized formats for dashboard integration

## Performance Results

The current system achieves the following performance across all zones:

- **SMUD**: 0.31% MAPE, 0.9995 R²
- **SYSTEM**: 0.42% MAPE, 0.9991 R²  
- **PGE_VALLEY**: 0.46% MAPE, 0.9994 R²
- **NP15**: 0.49% MAPE, 0.9991 R²
- **SP15**: 0.49% MAPE, 0.9982 R²
- **SCE**: 0.58% MAPE, 0.9984 R²
- **SDGE**: 0.80% MAPE, 0.9976 R²

These results represent significant improvements from previous iterations that suffered from data quality issues and inadequate zone-specific modeling approaches.

## Troubleshooting and Maintenance

### Common Issues

**High MAPE Values**: Usually indicate data quality problems or insufficient preprocessing. Check for mixed data sources, outliers, or missing zone-specific features.

**Model Training Failures**: Often caused by insufficient data, memory constraints, or hyperparameter conflicts. Review data availability and system resources.

**Deployment Issues**: Typically result from model file corruption, directory permission problems, or API server configuration errors.

### Maintenance Procedures

**Data Quality Monitoring**: Regularly audit data sources for new contamination or mapping changes in CAISO systems.

**Performance Tracking**: Monitor model performance trends to identify gradual degradation or sudden performance drops.

**System Updates**: Coordinate model retraining with system updates to ensure compatibility and performance maintenance.

The automated training pipeline handles routine maintenance, but manual intervention may be required for significant data source changes or system modifications.
