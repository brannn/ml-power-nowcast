# ML Power Nowcast

ML Power Nowcast implements a GPU-capable power demand forecasting system using MLflow for experiment tracking and model management. The project demonstrates reproducible machine learning workflows that can be deployed across local development environments and AWS EC2 instances.

## Project Goals

This proof of concept generates 15-60 minute power demand forecasts using publicly available datasets. The system compares classical machine learning approaches (XGBoost) against neural network models (LSTM) while maintaining full experiment reproducibility through MLflow integration. The architecture supports model serving through both MLflow's built-in server and FastAPI endpoints.

The implementation emphasizes portability across computing environments. The same codebase operates on local development machines and AWS EC2 GPU instances without modification, requiring only environment variable changes for different deployment targets.

## Implementation Status

The project implements a complete machine learning pipeline following the systematic approach outlined in the implementation plan. Current functionality includes comprehensive data ingestion with zone-based weather aggregation, feature engineering with lag variables and rolling statistics, model training for both XGBoost and LSTM architectures, evaluation with diagnostic plots and performance metrics, model registry management with promotion workflows, and production-ready serving infrastructure.

The system has been validated through comprehensive testing with 53 passing tests covering feature engineering, model evaluation, and serving functionality. End-to-end integration testing confirms that the complete pipeline operates correctly from data ingestion through model serving.

## Architecture

The system follows a linear pipeline architecture where each stage logs comprehensive metadata to MLflow:

```
[Data Ingest] → [Feature Build] → [Model Train (GPU/CPU)] → [Eval + Plots]
       ↓              ↓              ↓                      ↓
MLflow artifacts & params ← MLflow metrics & model → Model Registry → Serve
```

Data ingestion pulls power demand and weather data from public APIs, creating timestamped datasets stored as Parquet files. Feature engineering generates lagged variables and rolling statistics, with all transformations logged as MLflow artifacts. Model training supports both CPU-based XGBoost and GPU-accelerated PyTorch LSTM models, with hyperparameters and metrics tracked automatically. The evaluation stage produces diagnostic plots and performance metrics, while the model registry manages version promotion from staging to production.

## Project Structure

```
ml-power-nowcast/
├── terraform/           # Infrastructure as Code
│   ├── modules/         # Reusable Terraform modules
│   │   ├── vpc/         # ml-dev VPC with SSM endpoints
│   │   ├── security/    # IAM roles, security groups
│   │   ├── compute/     # EC2 instances (g6f.xlarge/g6.xlarge)
│   │   └── storage/     # S3 buckets for MLflow artifacts
│   └── environments/    # Environment-specific configs
│       └── dev/         # Shared infrastructure (supports both dev and prod instances)
├── packer/              # AMI building
│   └── ubuntu-ml-base/  # Ubuntu 22.04 + ML dependencies
├── planning/            # Project planning documents
├── scripts/             # Data management and utility scripts
├── src/                 # ML pipeline code
│   ├── config/          # Zone configurations (NYISO, CAISO)
│   ├── ingest/          # Data ingestion (power, weather)
│   ├── features/        # Feature engineering with lag and rolling features
│   ├── models/          # Model training (XGBoost, LSTM) and evaluation
│   └── serve/           # Model serving (FastAPI and MLflow)
├── data/                # Data storage (gitignored)
├── notebooks/           # Jupyter notebooks
└── artifacts/           # Model artifacts (gitignored)
```

## Getting Started

### Prerequisites

The project requires Python 3.10 or later, AWS CLI with configured credentials, Terraform 1.6 or later, and Packer 1.9 or later. These tools enable local development, infrastructure provisioning, and custom AMI creation respectively.

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

Copy the example environment file and configure it for your specific setup:

```bash
cp .env.example .env
# Edit .env with your AWS region and MLflow configuration
```

### Infrastructure Deployment

For cloud deployment, first build a custom AMI containing ML dependencies and NVIDIA drivers:

```bash
cd packer/ubuntu-ml-base
packer build ubuntu-ml-base.pkr.hcl
```

Deploy the AWS infrastructure using Terraform:

```bash
cd ../../terraform/environments/dev
terraform init
terraform plan -var="instance_mode=dev"
terraform apply -var="instance_mode=dev"
```

This creates a VPC named 'ml-dev' with private subnets, SSM endpoints for secure access, and EC2 instances configured for ML workloads. Use `instance_mode=prod` to deploy production instances or `instance_mode=both` for concurrent access to both instance types.

### ML Pipeline Execution

For local development, start an MLflow tracking server:

```bash
export MLFLOW_TRACKING_URI=http://0.0.0.0:5001
mlflow server --backend-store-uri sqlite:///mlruns.db \
  --default-artifact-root ./mlruns_artifacts --host 0.0.0.0 --port 5001
```

For cloud deployments with S3 storage, pre-populate historical data to avoid repeated API calls during development:

```bash
# Configure your S3 bucket name
export BUCKET_NAME="your-mlflow-bucket-name"

# Pre-populate with real data (requires API access)
make prepopulate-s3-run BUCKET=$BUCKET_NAME YEARS=3

# Or use synthetic data for development
python3 scripts/prepopulate_s3_data.py --bucket $BUCKET_NAME --years 3 --synthetic-power --synthetic-weather

# Check existing data
make list-s3-data BUCKET=$BUCKET_NAME
```

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

The system integrates multiple public data sources to create comprehensive training datasets. NYISO and CAISO provide real-time load data through their public APIs, with the ingestion system aggregating zone-level demand data into regional totals with hourly granularity. The implementation includes comprehensive zone mapping and data validation to ensure consistency across different grid operators.

Weather data comes from OpenWeatherMap API, which supplies current and historical weather observations including temperature, humidity, wind speed, and other meteorological variables. The system aggregates weather data by region using zone-based mapping to align with power demand geography, ensuring spatial consistency between weather and load data.

The data processing pipeline handles API rate limiting, data validation, and format standardization. Missing data points are identified and logged, but the system does not generate synthetic replacements to maintain data integrity. Processing includes automatic retry mechanisms and comprehensive error logging for production reliability.

Feature engineering transforms raw time series data into machine learning features through multiple approaches. The pipeline creates lag features for 1-24 hour historical values, computes rolling statistics over multiple time windows, generates temporal features with cyclic encoding for hour and seasonal patterns, and calculates weather interaction variables such as heating and cooling degree days. This process typically generates 47 engineered features from the raw power and weather data.

## Technology Stack

The system uses MLflow as the central framework for experiment tracking and model registry management. Model implementations include XGBoost for baseline comparisons and PyTorch LSTM networks for neural forecasting approaches. Data processing follows a pandas-first methodology with Parquet file storage for efficient columnar data access.

Model serving operates through both MLflow's built-in model server and custom FastAPI applications. Infrastructure provisioning uses Terraform for reproducible AWS resource management, while Packer creates custom AMIs containing ML dependencies and NVIDIA drivers.

Compute resources include EC2 g6f.xlarge instances for development and testing, with g6.xlarge instances for production workloads. Both instance types provide L4 GPU acceleration for neural network training. Remote access uses AWS Systems Manager Session Manager, eliminating SSH key management and improving security posture.

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

## Deployment Environments

Local development uses synthetic data generation for rapid iteration without external API dependencies. This environment supports full pipeline testing and model development using CPU-only resources.

AWS EC2 g6f.xlarge instances provide GPU acceleration for development and testing workflows. These instances offer cost-effective GPU access for model training experiments and hyperparameter optimization.

Production deployments use EC2 g6.xlarge instances for optimized training and serving performance. The same infrastructure supports both development and production workloads through instance type selection.

## Data Ingestion Architecture

The system implements a comprehensive data ingestion framework designed for accuracy and geographic representativeness. Data collection operates through zone-based weather aggregation and robust power demand APIs, ensuring that weather features properly correlate with statewide power demand patterns.

### Power Demand Data Collection

Power demand data originates from public APIs provided by Independent System Operators (ISOs). The implementation addresses specific API limitations and data quality requirements through targeted fixes based on comprehensive analysis of each system's data structure.

**NYISO (New York Independent System Operator)** data collection uses the P-58B Real-Time Actual Load CSV files published daily. The system fetches 5-minute interval data across all load zones and aggregates zone totals to produce accurate statewide (NYCA) demand figures. This approach corrects previous implementations that incorrectly filtered for single zones rather than computing true statewide totals.

**CAISO (California Independent System Operator)** data collection employs the OASIS SingleZip API with chunked requests to handle large date ranges reliably. The implementation uses 7-day request windows with proper error handling for individual chunk failures. API parameters specify 15-minute granularity with actual load data rather than forecasts.

Both systems implement UTC timestamp normalization and comprehensive error handling without synthetic data fallbacks. This approach maintains data integrity by preventing contamination of real datasets with generated values.

### Zone-Based Weather Collection

Weather data collection addresses the geographic mismatch between statewide power demand and single-point weather measurements. The system implements zone-based weather aggregation that properly represents climate diversity across entire states.

**NYISO Weather Zones** encompass 11 representative locations across New York State, from Buffalo (Western NY) through Syracuse (Central NY) to New York City and Long Island. Each zone corresponds to a major load center with coordinates selected for representative weather station coverage. Population-weighted aggregation produces statewide weather averages that reflect actual load distribution, with NYC accounting for 42% of the weighting and Long Island contributing 18%.

**CAISO Weather Zones** cover 8 major load aggregation points across California's diverse climate regions. These include NP15 (North of Path 15, San Francisco Bay Area), SP15 (South of Path 15, Los Angeles Basin), SDGE (San Diego), and additional zones representing the Central Valley, Inland Empire, and Sacramento areas. Load-weighted aggregation accounts for California's concentrated demand patterns, with the LA Basin (SP15) weighted at 35% and the Bay Area (NP15) at 25%.

The zone-based approach captures climate diversity that single-point measurements cannot represent. New York State weather varies significantly from Buffalo's lake-effect snow patterns to NYC's coastal moderation. California spans Mediterranean coastal climates, hot semi-arid Central Valley conditions, and desert regions in the Inland Empire.

### Data Storage and Organization

S3 storage follows a structured hierarchy that maintains clear data provenance and supports both synthetic and real data workflows. The storage structure separates power and weather data by region and data type:

```
raw/
├── power/
│   ├── nyiso/
│   │   ├── real_3y.parquet      # Real NYISO statewide data
│   │   └── synthetic_3y.parquet # Synthetic NYISO data
│   └── caiso/
│       ├── real_3y.parquet      # Real CAISO statewide data
│       └── synthetic_3y.parquet # Synthetic CAISO data
└── weather/
    ├── nyiso_zones/
    │   ├── real_3y.parquet      # 11-zone population-weighted NY weather
    │   └── synthetic_3y.parquet # Synthetic NY weather
    └── caiso_zones/
        ├── real_3y.parquet      # 8-zone load-weighted CA weather
        └── synthetic_3y.parquet # Synthetic CA weather
```

This organization enables clear separation between synthetic and real data sources while maintaining consistent naming conventions. Data source attribution tracks aggregation methods and API sources for full reproducibility.

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
