# ML Power Nowcast

ML Power Nowcast implements a power demand forecasting system for the California Independent System Operator (CAISO) using machine learning. The project demonstrates reproducible ML workflows with real-time data collection, zone-specific weather integration, and comprehensive model training capabilities.

## Project Goals

This system generates real-time power demand forecasts for California using CAISO data and zone-specific weather information. The implementation collects actual load data from 7 granular CAISO zones (including Sacramento, Central Valley, Los Angeles, San Diego, and others) and correlates it with representative weather data for accurate demand prediction.

The system emphasizes real data collection over synthetic generation, using the CAISO OASIS API for actual system load data and Meteostat for zone-specific weather information. All data collection respects API rate limits and maintains data integrity without fallback to synthetic data.

## Implementation Status

The project implements a complete CAISO power demand forecasting pipeline with real data collection capabilities. Current functionality includes:

- **Real CAISO Data Collection**: 7 granular zones (SYSTEM, NP15, SCE, SMUD, PGE_VALLEY, SP15, SDGE) with 5-minute resolution
- **Zone-Specific Weather**: Representative weather stations for each CAISO zone with proper geographic coverage
- **Historical Data Collection**: 5+ years of historical data collection with 15-second rate limiting
- **Feature Engineering**: Weather-power correlations, lag variables, and rolling statistics
- **Model Training**: XGBoost and LSTM models with zone-specific features
- **Real-Time Dashboard**: Live power demand visualization with model performance metrics

The system operates locally with comprehensive data collection scripts and a React-based dashboard for real-time monitoring.

## Architecture

The system follows a data-driven architecture focused on real CAISO data collection and zone-specific modeling:

```
[CAISO API] → [Zone Mapping] → [Weather Collection] → [Feature Engineering]
     ↓              ↓               ↓                      ↓
[Historical Data] → [Real-time Data] → [ML Models] → [Dashboard Serving]
```

**Data Collection**: CAISO OASIS API provides real system load data with 15-second rate limiting. Zone mapping converts CAISO resources to geographic zones (Sacramento, Central Valley, LA, etc.). Weather collection uses Meteostat for zone-specific weather data.

**Processing**: Feature engineering creates weather-power correlations, lag variables, and rolling statistics. Models train on zone-specific features with proper geographic representation.

**Serving**: React dashboard displays real-time power demand, weather conditions, and model performance metrics with automatic updates.

## Project Structure

```
ml-power-nowcast/
├── scripts/             # Data collection and management scripts
│   ├── collect_caiso_historical.py  # 5-year CAISO data collection
│   └── README_caiso_collection.md   # Collection guide
├── src/                 # Core ML pipeline code
│   ├── config/          # CAISO zone configurations
│   ├── ingest/          # Data collection (CAISO power, weather)
│   ├── features/        # Feature engineering with weather correlations
│   ├── models/          # Model training and evaluation
│   ├── api/             # Regional API server for dashboard
│   └── serve/           # Model serving infrastructure
├── dashboard/           # React-based real-time dashboard
│   ├── src/             # Dashboard components and pages
│   └── public/          # Static assets
├── data/                # Local data storage (gitignored)
├── planning/            # Project planning and documentation
├── notebooks/           # Analysis and development notebooks
└── models/              # Trained model artifacts (gitignored)
```

## Getting Started

### Prerequisites

The project requires Python 3.10 or later and Node.js 18+ for the dashboard. All data collection and model training runs locally without cloud dependencies. Optional: AWS CLI for S3 data storage.

### Environment Setup

The project uses a two-tier dependency structure for optimal deployment flexibility:

- **`requirements.txt`**: Runtime dependencies for production deployment
- **`requirements-dev.txt`**: Development tools (testing, linting, notebooks, profiling)

**For Production/Runtime:**
```bash
make setup  # Creates .venv with runtime dependencies only
source .venv/bin/activate
```

**For Development:**
```bash
make setup-dev  # Creates .venv with all dependencies including dev tools
source .venv/bin/activate
```

**Manual Setup (if preferred):**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt  # For development
# OR
pip install -r requirements.txt  # For production only
```

### CAISO Data Collection

Collect 5 years of real CAISO historical data using the provided script:

```bash
# Test the collection plan
python scripts/collect_caiso_historical.py --dry-run

# Collect power data only (recommended first run)
python scripts/collect_caiso_historical.py

# Collect power + weather data for all zones
python scripts/collect_caiso_historical.py --collect-weather

# Upload to S3 (optional)
python scripts/collect_caiso_historical.py --collect-weather --upload-s3
```

The collection script uses 15-second rate limiting and takes ~30-45 minutes for 5 years of data. It collects data from 7 CAISO zones with proper geographic representation.

### Dashboard and Real-Time Monitoring

Start the real-time dashboard to monitor CAISO power demand and model performance:

```bash
# Start the regional API server (serves CAISO data)
cd src/api && python regional_api_server.py

# In another terminal, start the dashboard
cd dashboard && npm install && npm start
```

The dashboard displays:
- Real-time CAISO power demand by zone
- Weather conditions for each zone
- Model performance metrics (MAPE, R², accuracy)
- Zone-specific load patterns and forecasts

Access the dashboard at `http://localhost:3000`

Execute the ML pipeline using the provided Makefile targets:

```bash
make ingest       # Download and process power/weather data
make features     # Generate lagged and rolling features with temporal encoding
make train-xgb    # Train XGBoost baseline model with MLflow tracking
make train-lstm   # Train LSTM neural network model with GPU support
make evaluate     # Generate comprehensive evaluation metrics and diagnostic plots
```

The feature engineering stage creates 47 engineered features from power and weather data, including lag features for 1-24 hour historical values, rolling statistics over multiple time windows, temporal features with cyclic encoding, and weather interaction variables such as heating and cooling degree days.

Model training supports both classical and neural approaches. XGBoost provides a robust baseline with automatic hyperparameter logging, while LSTM networks leverage GPU acceleration for sequence modeling. Both models integrate with MLflow for experiment tracking and model registry management.

Deploy trained models for serving using either approach:

```bash
make serve-fastapi  # Serve via FastAPI microservice (recommended)
make serve-mlflow   # Serve via MLflow built-in server
make serve-info     # Display model registry information
make serve-test     # Test serving endpoints
```

The FastAPI serving option provides production-ready endpoints with comprehensive error handling, request validation, health checks, and batch prediction support. The MLflow serving option offers direct model deployment from the model registry with minimal configuration.

Validate the implementation using the comprehensive test suite:

```bash
make test     # Run all tests with coverage reporting
make lint     # Check code quality and formatting
make fmt      # Apply automatic code formatting
```

The test suite includes 53 tests covering feature engineering, model training, evaluation, and serving functionality with end-to-end integration validation.

## Data Sources and Processing

The system focuses exclusively on California Independent System Operator (CAISO) data for comprehensive power demand forecasting. CAISO provides real-time load data through their OASIS API, with the ingestion system collecting data from 7 granular zones including Sacramento (SMUD), Central Valley (PGE_VALLEY), Los Angeles (SP15), San Diego (SDGE), and others.

Weather data comes from Meteostat, which provides free historical and current weather observations. The system collects zone-specific weather data for each CAISO zone using representative coordinates, ensuring proper geographic correlation between weather patterns and power demand across California's diverse climate regions.

### CAISO Zone Coverage

The system collects data from 7 granular CAISO zones with proper geographic representation:

- **SYSTEM**: California statewide total (23-35 GW)
- **SMUD**: Sacramento Municipal Utility District (Sacramento area)
- **PGE_VALLEY**: Central Valley region (Modesto, agricultural areas)
- **SP15**: South of Path 15 (Los Angeles area via LADWP)
- **SCE**: Southern California Edison (Inland Empire, San Bernardino)
- **NP15**: North of Path 15 (San Francisco Bay Area, Northern CA)
- **SDGE**: San Diego Gas & Electric (San Diego County)

Each zone has representative weather coordinates capturing California's climate diversity from coastal Mediterranean to hot semi-arid inland regions.

## Real-Time Dashboard

The system includes a comprehensive React-based dashboard for real-time CAISO power demand monitoring and model performance tracking.

### Dashboard Features

- **Real-Time Power Demand**: Live CAISO system load with automatic updates
- **Zone-Specific Data**: Individual zone loads (Sacramento, Central Valley, LA, San Diego, etc.)
- **Weather Integration**: Current weather conditions for each CAISO zone
- **Model Performance**: Live MAPE, R², and accuracy metrics
- **Historical Trends**: Power demand patterns and forecasting accuracy
- **Model Comparison**: Performance across different models and zones

### Technology Stack

- **Frontend**: React 18 with TypeScript, Tailwind CSS, Recharts for visualization
- **Backend**: Python FastAPI regional API server serving CAISO data
- **Data Collection**: CAISO OASIS API with Meteostat weather integration
- **Storage**: Local Parquet files with optional S3 backup
- **Models**: XGBoost and LSTM with scikit-learn and PyTorch

## Security Considerations

This repository is publicly accessible on GitHub. Never commit credentials, API keys, or other sensitive information to version control. The .gitignore file excludes common secret file patterns, but developers must remain vigilant about accidental credential exposure.

Local development uses .env files for configuration management. These files are excluded from version control and should contain only non-sensitive configuration values. For cloud deployments, store sensitive values in AWS Parameter Store or similar secure configuration services.

Infrastructure secrets such as Terraform variable files containing credentials should never be committed. Use Terraform Cloud, AWS Secrets Manager, or similar services for secure infrastructure credential management.

## Testing and Quality Assurance

The project maintains comprehensive test coverage across all major components. The test suite includes 53 passing tests covering feature engineering, model training, evaluation, and serving functionality. Tests validate feature creation logic, model performance calculations, API endpoint behavior, and end-to-end pipeline integration.

Feature engineering tests verify lag feature creation, rolling window statistics, temporal feature encoding, and weather interaction calculations. Model evaluation tests cover metric calculations including Pinball loss, diagnostic plot generation, and model registry integration. Serving tests validate FastAPI endpoints, request validation, error handling, and model loading functionality.

Integration testing confirms that the complete pipeline operates correctly from data ingestion through model serving. The test framework uses pytest with comprehensive fixtures and mocking to ensure reliable, fast test execution. All tests follow PEP-8 compliance and include comprehensive type hinting for maintainability.

Quality assurance includes automated code formatting with black, linting with flake8, and type checking capabilities. The project structure supports continuous integration workflows and maintains high code quality standards throughout development.

## Model Training and Evaluation

The system implements two complementary modeling approaches for power demand forecasting. XGBoost provides a robust baseline using gradient boosting with automatic feature importance analysis and hyperparameter logging through MLflow. LSTM neural networks leverage PyTorch for sequence modeling with GPU acceleration, capturing temporal dependencies in power demand patterns.

Model training follows time series best practices with temporal splits to prevent data leakage. The training pipeline automatically logs experiments to MLflow, tracking hyperparameters, metrics, and model artifacts for reproducibility. Both models integrate with the MLflow Model Registry for version management and deployment workflows.

Evaluation uses comprehensive forecasting metrics including Mean Absolute Error (MAE), Root Mean Square Error (RMSE), Mean Absolute Percentage Error (MAPE), and R-squared for model comparison. The system also calculates Pinball loss for quantile predictions when available. Diagnostic plots include prediction versus actual scatter plots, residual histograms, and backtest charts by forecast horizon.

The evaluation framework generates detailed performance reports with model comparison tables and diagnostic visualizations. All evaluation artifacts are logged to MLflow for experiment tracking and model registry integration. The system supports automated model promotion based on performance thresholds, enabling controlled deployment from staging to production environments.

## Operational Model

The system operates entirely locally with real CAISO data collection, eliminating cloud dependencies for core functionality. This approach provides:

### Local Development Benefits
- **No cloud costs**: All processing runs on local hardware
- **Real data access**: Direct CAISO OASIS API integration
- **Rapid iteration**: Immediate feedback without deployment delays
- **Data control**: Complete ownership of collected datasets

### Data Collection Strategy
- **Historical collection**: 5+ years of CAISO data via rate-limited API calls
- **Incremental updates**: Daily collection of fresh data
- **Zone-specific weather**: Representative weather stations for each CAISO zone
- **Data integrity**: No synthetic fallbacks, real data only

### Scalability Options
- **Local processing**: Sufficient for CAISO zone-level modeling
- **Optional S3 storage**: Backup and sharing capabilities
- **Dashboard serving**: Real-time monitoring via local React app

## Data Ingestion Architecture

The system implements a comprehensive data ingestion framework designed for accuracy and geographic representativeness. Data collection operates through zone-based weather aggregation and robust power demand APIs, ensuring that weather features properly correlate with statewide power demand patterns.

### CAISO Power Demand Data Collection

Power demand data comes exclusively from the California Independent System Operator (CAISO) OASIS API. The implementation collects real actual load data (not forecasts) with proper zone mapping and geographic representation.

**CAISO OASIS API Integration** uses the SLD_FCST endpoint with RTM (Real-Time Market) parameters to collect actual system load data. The system employs 14-day chunked requests with 15-second rate limiting to handle large historical date ranges reliably. This approach respects API limits while enabling collection of 5+ years of historical data.

**Zone Resource Mapping** converts CAISO resource identifiers to geographic zones:
- `CA ISO-TAC` → SYSTEM (statewide total)
- `BANCSMUD`, `BANCRSVL` → SMUD (Sacramento area)
- `BANCMID` → PGE_VALLEY (Central Valley/Modesto)
- `LADWP` → SP15 (Los Angeles area)
- `SCE-TAC` → SCE (Southern California Edison)
- `PGE-TAC` → NP15 (Northern California)
- `SDGE-TAC` → SDGE (San Diego area)

The system implements UTC timestamp normalization and comprehensive error handling without synthetic data fallbacks, maintaining data integrity for production model training.

### Zone-Based Weather Collection

Weather data collection addresses the geographic diversity of California's climate regions by collecting zone-specific weather data that properly correlates with power demand patterns. The system uses Meteostat for reliable, free weather data collection.

**CAISO Weather Zones** cover 6 major climate regions across California with representative coordinates:

- **SMUD (Sacramento)**: 38.58°N, -121.49°W - Valley heat patterns
- **PGE_VALLEY (Modesto)**: 37.64°N, -120.99°W - Central Valley agriculture climate
- **SP15 (Los Angeles)**: 34.05°N, -118.24°W - Urban heat island effects
- **SCE (San Bernardino)**: 34.15°N, -117.83°W - Inland desert climate
- **NP15 (San Francisco)**: 37.77°N, -122.42°W - Coastal fog and marine layer
- **SDGE (San Diego)**: 32.72°N, -117.16°W - Mild coastal Mediterranean

This zone-based approach captures California's extreme climate diversity, from coastal Mediterranean conditions to hot semi-arid Central Valley and desert regions in the Inland Empire. Each zone's weather data correlates directly with its power demand patterns, enabling accurate weather-driven load forecasting.

### Data Storage and Organization

Local and S3 storage follows a structured hierarchy focused on CAISO data with clear data provenance:

```
data/
├── historical/                  # Historical data collection
│   ├── caiso_5year_full.parquet    # All zones and resources (power)
│   ├── caiso_5year_system.parquet  # SYSTEM zone only (power)
│   └── caiso_5year_weather.parquet # All zones weather data
├── fresh_power_today.parquet    # Today's incremental power data
└── fresh_weather_today.parquet  # Today's incremental weather data

# S3 structure (optional)
s3://bucket/
├── raw/power/caiso/
│   └── historical_5year_YYYYMMDD.parquet
└── processed/power/caiso/
    └── system_5year_YYYYMMDD.parquet
```

This organization maintains clear separation between historical collections and incremental updates, with optional S3 storage for backup and sharing. All data includes proper source attribution and zone mapping for reproducibility.

### Data Pre-Population Capabilities

The system includes comprehensive S3 pre-population functionality that enables bulk historical data collection from local environments. This approach avoids repeated API calls during development and provides reliable data availability for model training.

Pre-population operates through configurable scripts that support both real API collection and synthetic data generation. Users can specify data types, time ranges, and aggregation methods through command-line parameters. The system handles API failures gracefully without falling back to synthetic data, maintaining strict separation between data types.

Example usage demonstrates the flexibility of the pre-population system:

```bash
# Real data collection with zone-based weather
python3 scripts/prepopulate_s3_data.py --bucket mybucket --years 3

# Synthetic data for development
python3 scripts/prepopulate_s3_data.py --bucket mybucket --years 3 --synthetic-power --synthetic-weather

# Power-only collection for specific testing
python3 scripts/prepopulate_s3_data.py --bucket mybucket --years 2 --power-only
```

The pre-population system supports incremental updates and force-refresh capabilities, enabling efficient data management workflows for both development and production environments.

### API Integration and Data Quality

The implementation incorporates specific fixes for known API limitations and data quality issues identified through comprehensive analysis of public power data sources. These improvements ensure accurate data collection and proper geographic representation.

**NYISO API Corrections** address the critical issue of zone aggregation versus single-zone filtering. Previous implementations incorrectly filtered for PTID 61757, which corresponds only to the CAPITL zone rather than statewide totals. The corrected implementation aggregates all zones per timestamp to produce true NYCA (New York Control Area) statewide load figures. This change significantly improves data accuracy for statewide forecasting models.

**CAISO API Reliability** improvements implement chunked request patterns to handle the system's data retention limitations and request size constraints. CAISO OASIS API maintains approximately 39 months of historical data with varying request limits across different report types. The implementation uses 7-day request chunks with comprehensive error handling for individual chunk failures, ensuring robust data collection across large date ranges.

**UTC Timestamp Normalization** standardizes all temporal data to UTC timezone handling, eliminating timezone-related inconsistencies that can affect model training. This normalization applies across both power and weather data sources, ensuring proper temporal alignment for feature engineering.

**Data Integrity Safeguards** prevent mixing of synthetic and real data through strict separation of data collection workflows. Real API functions raise explicit errors rather than falling back to synthetic data generation, maintaining clear data provenance for model evaluation and production deployment.

### Synthetic Data Generation

The system provides comprehensive synthetic data generation capabilities for development and testing scenarios where real API access is unavailable or impractical. Synthetic data generation operates independently from real data collection, ensuring no contamination of production datasets.

Synthetic power demand data incorporates realistic patterns including daily cycles, weekly variations, seasonal trends, and weather correlations. The generation process uses configurable parameters for base load levels, peak demand ratios, and seasonal adjustment factors that reflect actual power system characteristics.

Synthetic weather data generation produces correlated meteorological variables including temperature, humidity, and wind speed with appropriate seasonal patterns and daily variations. The synthetic weather maintains statistical properties similar to real weather data while providing consistent, reproducible datasets for development workflows.

Both synthetic data types include proper metadata attribution that clearly identifies generated data sources, preventing accidental use in production model training or evaluation scenarios.

## Docker Deployment

The project includes Docker containerization support for portable deployment across different environments. The provided Dockerfile creates a production-ready container with all necessary dependencies, security configurations, and health checks.

Container deployment supports both serving modes through environment variable configuration. The FastAPI serving mode provides the recommended production deployment option with comprehensive API endpoints and monitoring capabilities. The MLflow serving mode offers direct model deployment from the registry with minimal configuration overhead.

Build and run the container using the provided Makefile targets:

```bash
make docker-build  # Build the Docker image
make docker-run    # Run the container with default configuration
```

The container configuration includes non-root user execution for security, health check endpoints for orchestration integration, and environment variable support for MLflow tracking URI and model registry configuration. Port 8000 is exposed for API access, with configurable host and worker settings through environment variables.

## Contributing

Development follows standard Git workflow practices with feature branches for all changes. Infrastructure modifications must be tested in the development environment before applying to production resources.

Documentation updates should accompany any architectural changes or new feature implementations. This ensures that setup instructions and usage examples remain current with code modifications.

Security review is required for any changes affecting credential management, network access, or data handling. Never commit credentials or sensitive configuration information to the repository.

## License

MIT License - see LICENSE file for details
