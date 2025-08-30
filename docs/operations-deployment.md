# Operations and Deployment Guide

This document covers operational procedures, deployment strategies, and maintenance workflows for the ML Power Nowcast system in production environments.

## System Requirements

### Hardware Requirements

**Development Environment**:
- Minimum 16GB RAM for full dataset processing
- 8+ CPU cores for efficient training
- 50GB available storage for data and models
- SSD storage recommended for I/O performance

**Production Environment**:
- 32GB RAM for optimal performance
- 16+ CPU cores for concurrent zone training
- 100GB storage for data retention and backups
- Network connectivity for CAISO API access

### Software Dependencies

**Python Environment**:
- Python 3.9 or higher
- Virtual environment management (venv, conda, or similar)
- Package dependencies managed through requirements.txt

**External Services**:
- CAISO OASIS API access (no authentication required)
- Weather API services for forecast data
- Optional: Cloud storage for backup and archival

### Environment Setup

Create and activate a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Verify installation by running the test suite:

```bash
python -m pytest tests/ -v
```

## Current Operational Status

### Production Deployment Configuration

The system currently operates in a production configuration with the following components:

**Automated Data Collection**: macOS launchd jobs handle continuous data collection from CAISO APIs with 15-second rate limiting to ensure reliable data acquisition without API throttling.

**Model Training Pipeline**: Automated ML pipeline runs zone-specific model training with the following schedule:
- Incremental data collection every 30 minutes
- Model retraining every 6 hours
- Full pipeline validation and deployment automation

**API Services**: Regional API server operates on localhost:8001 providing:
- Zone-specific prediction endpoints
- Weather data integration for all zones including consolidated zones
- Real-time model serving with ensemble predictions

**Dashboard Interface**: Interactive dashboard runs on localhost:3000 with:
- Real-time zone selection and data display
- Current conditions cards with zone-specific weather
- Prediction charts and historical performance metrics

### Recent Operational Improvements

**Ensemble Model Reliability**: Resolved critical prediction accuracy issues through zone-specific LightGBM model implementation, eliminating unrealistic predictions that previously affected system reliability.

**Weather Data Integration**: Enhanced weather data pipeline to provide accurate, zone-specific weather information that updates dynamically based on user selection in the dashboard interface.

**Error Handling and Monitoring**: Improved error handling throughout the prediction pipeline with better logging and graceful degradation when components are unavailable.

**Data Quality Assurance**: Enhanced data validation and quality checks to ensure prediction reliability and system stability during operational use.

## Deployment Architecture

### Local Development Deployment

For development and testing, the system runs entirely on local infrastructure:

**Data Storage**: Local filesystem with organized directory structure for raw data, processed features, trained models, and backups.

**Model Training**: Local execution of training scripts with configurable resource allocation.

**API Services**: Local API server for testing predictions and dashboard integration.

**Monitoring**: File-based logging with configurable log levels and rotation.

### Production Deployment Options

#### Single-Server Deployment

Suitable for small to medium-scale operations:

**Application Server**: Single server running all components including data collection, model training, and API services.

**Data Management**: Local storage with automated backup to external systems.

**Scheduling**: Cron jobs or systemd timers for automated training pipeline execution.

**Monitoring**: Log aggregation and basic alerting for system health.

#### Distributed Deployment

For larger scale or high-availability requirements:

**Training Cluster**: Dedicated compute resources for model training with job scheduling and resource management.

**API Cluster**: Load-balanced API servers for prediction serving with auto-scaling capabilities.

**Data Infrastructure**: Centralized data storage with replication and backup systems.

**Orchestration**: Container orchestration (Docker/Kubernetes) for service management and scaling.

## Automated Operations

### Scheduled Training Pipeline

The automated training pipeline executes on a configurable schedule to maintain model currency:

**Daily Training**: Standard schedule for production environments to incorporate latest data and maintain prediction accuracy.

**Weekly Deep Training**: Extended training sessions that include comprehensive data validation, feature engineering optimization, and performance analysis.

**On-Demand Training**: Manual trigger capability for immediate model updates following data corrections or system changes.

### Scheduling Configuration

#### Cron-based Scheduling

Example crontab configuration for daily training at 2 AM:

```bash
0 2 * * * cd /path/to/ml-power-nowcast && /path/to/venv/bin/python scripts/automated_ml_pipeline.py --target-zones ALL >> logs/training.log 2>&1
```

#### Systemd Timer Configuration

Create systemd service and timer files for more robust scheduling:

```ini
# /etc/systemd/system/ml-training.service
[Unit]
Description=ML Power Nowcast Training Pipeline
After=network.target

[Service]
Type=oneshot
User=mluser
WorkingDirectory=/opt/ml-power-nowcast
ExecStart=/opt/ml-power-nowcast/venv/bin/python scripts/automated_ml_pipeline.py --target-zones ALL
StandardOutput=journal
StandardError=journal

# /etc/systemd/system/ml-training.timer
[Unit]
Description=Run ML training daily
Requires=ml-training.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

### Data Collection Automation

Automated data collection ensures continuous data availability:

**Historical Data Backfill**: Periodic collection of historical data to fill gaps and maintain complete datasets.

**Real-time Data Collection**: Continuous collection of current power demand and weather data for prediction generation.

**Data Quality Monitoring**: Automated validation of collected data with alerting for quality issues or collection failures.

## Monitoring and Alerting

### Performance Monitoring

**Model Performance Tracking**: Continuous monitoring of prediction accuracy with trend analysis and threshold alerting.

**Training Pipeline Monitoring**: Tracking of training job success rates, execution times, and resource utilization.

**API Performance Monitoring**: Response time tracking, error rate monitoring, and availability metrics for prediction services.

### System Health Monitoring

**Resource Utilization**: CPU, memory, and storage monitoring with capacity planning alerts.

**Data Pipeline Health**: Monitoring of data collection processes, feature engineering pipelines, and data quality metrics.

**Service Availability**: Health checks for API services, database connections, and external service dependencies.

### Alerting Configuration

Configure alerts for critical system events:

**Model Performance Degradation**: Alert when model MAPE exceeds acceptable thresholds (typically 2% for any zone).

**Training Pipeline Failures**: Immediate notification of training job failures or extended execution times.

**Data Quality Issues**: Alerts for missing data, data corruption, or significant distribution changes.

**System Resource Exhaustion**: Proactive alerts for high resource utilization or storage capacity issues.

## Backup and Recovery

### Data Backup Strategy

**Model Backups**: Automated backup of trained models with timestamped versions for rollback capability.

**Data Backups**: Regular backup of collected data, processed features, and configuration files.

**Configuration Backups**: Version control and backup of system configuration, deployment scripts, and documentation.

### Backup Implementation

```bash
#!/bin/bash
# Daily backup script
BACKUP_DIR="/backup/ml-power-nowcast/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup models
cp -r data/production_models "$BACKUP_DIR/"
cp -r data/model_backups "$BACKUP_DIR/"

# Backup data
cp -r data/master "$BACKUP_DIR/"
cp -r data/forecasts "$BACKUP_DIR/"

# Backup configuration
cp -r src/config "$BACKUP_DIR/"

# Compress and archive
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

# Cleanup old backups (keep 30 days)
find /backup/ml-power-nowcast -name "*.tar.gz" -mtime +30 -delete
```

### Recovery Procedures

**Model Rollback**: Restore previous model versions from timestamped backups when performance degradation occurs.

**Data Recovery**: Restore data from backups when corruption or loss is detected.

**System Recovery**: Complete system restoration from configuration and data backups following infrastructure failures.

## Security Considerations

### Data Security

**Access Control**: Implement appropriate file system permissions and user access controls for data and model files.

**Data Encryption**: Encrypt sensitive data at rest and in transit, particularly when using cloud storage or network transfers.

**API Security**: Implement authentication and authorization for API endpoints in production environments.

### Operational Security

**Service Isolation**: Run services with minimal required privileges and appropriate user accounts.

**Network Security**: Configure firewalls and network access controls to limit exposure of internal services.

**Audit Logging**: Maintain comprehensive audit logs of system access, configuration changes, and operational activities.

## Maintenance Procedures

### Regular Maintenance Tasks

**Log Rotation**: Configure automatic log rotation to prevent disk space exhaustion while maintaining adequate log retention.

**Model Cleanup**: Periodic cleanup of old model backups and intermediate files to manage storage utilization.

**Dependency Updates**: Regular updates of Python packages and system dependencies with testing in development environments.

**Performance Optimization**: Periodic review and optimization of model parameters, feature engineering, and system configuration.

### Troubleshooting Procedures

**Performance Issues**: Systematic approach to identifying and resolving model performance degradation or system slowdowns.

**Data Quality Problems**: Procedures for investigating and correcting data collection or processing issues.

## Current System Status and Known Issues

### System Reliability Status

The system has undergone significant reliability improvements with recent fixes addressing critical prediction accuracy issues. The ensemble model architecture now provides consistent, realistic predictions across all California utility zones.

### Known Areas for Improvement

**Prediction Consistency Validation**: While major ensemble model issues have been resolved, the system would benefit from additional prediction bounds checking and validation to ensure all forecasts remain within realistic operational ranges.

**Data Quality Monitoring**: Enhanced monitoring of data quality metrics and automated alerting for data collection issues would improve system reliability and reduce manual intervention requirements.

**Performance Optimization**: Some prediction scenarios may still exhibit inconsistencies that require systematic analysis and optimization of the ensemble weighting and model selection logic.

### Recommended Next Steps

**Comprehensive System Audit**: A systematic review of the entire prediction pipeline to identify and address any remaining data quality or prediction consistency issues.

**Enhanced Validation Framework**: Implementation of robust prediction validation and bounds checking to prevent unrealistic forecasts from reaching production systems.

**Monitoring and Alerting Improvements**: Enhanced monitoring capabilities to provide early warning of system issues and automated recovery procedures where possible.

### Maintenance Priorities

**Regular Model Validation**: Ongoing validation of model performance and prediction accuracy across all zones to ensure continued system reliability.

**Data Pipeline Monitoring**: Continuous monitoring of data collection and processing pipelines to maintain data quality and system availability.

**Performance Tracking**: Regular analysis of system performance metrics to identify optimization opportunities and prevent performance degradation.

**Service Failures**: Step-by-step recovery procedures for API service failures, training pipeline issues, and system component failures.

### Capacity Planning

**Storage Growth**: Monitor data growth rates and plan for storage expansion based on retention requirements and collection volumes.

**Compute Scaling**: Track training times and resource utilization to plan for compute capacity increases as data volumes grow.

**Network Capacity**: Monitor API usage patterns and plan for network capacity to handle prediction request volumes.

## Integration Guidelines

### Dashboard Integration

The system provides REST API endpoints for dashboard integration:

**Real-time Predictions**: Current and forecast power demand predictions for all zones.

**Historical Performance**: Model accuracy metrics and prediction history for performance visualization.

**System Status**: Health and status information for monitoring dashboard components.

### External System Integration

**Data Export**: Standardized data export formats for integration with external analytics and reporting systems.

**Alert Integration**: Webhook and notification system integration for external monitoring and alerting platforms.

**API Integration**: RESTful API design for integration with external applications and services.

The operational procedures outlined in this document ensure reliable, secure, and maintainable deployment of the ML Power Nowcast system in production environments. Regular review and updates of these procedures maintain system effectiveness as requirements and infrastructure evolve.
