# ML Power Nowcast

ML Power Nowcast implements a GPU-capable power demand forecasting system using MLflow for experiment tracking and model management. The project demonstrates reproducible machine learning workflows that can be deployed across local development environments, AWS EC2 instances, and SageMaker.

## Project Goals

This proof of concept generates 15-60 minute power demand forecasts using publicly available datasets. The system compares classical machine learning approaches (XGBoost) against neural network models (LSTM) while maintaining full experiment reproducibility through MLflow integration. The architecture supports model serving through both MLflow's built-in server and FastAPI endpoints.

The implementation emphasizes portability across computing environments. The same codebase operates on local development machines and AWS EC2 GPU instances without modification, requiring only environment variable changes for different deployment targets.

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
├── src/                 # ML pipeline code
│   ├── ingest/          # Data ingestion (power, weather)
│   ├── features/        # Feature engineering
│   ├── models/          # Model training (XGBoost, LSTM)
│   └── serve/           # FastAPI serving
├── data/                # Data storage (gitignored)
├── notebooks/           # Jupyter notebooks
└── artifacts/           # Model artifacts (gitignored)
```

## Getting Started

### Prerequisites

The project requires Python 3.12 or later, AWS CLI with configured credentials, Terraform 1.6 or later, and Packer 1.9 or later. These tools enable local development, infrastructure provisioning, and custom AMI creation respectively.

### Environment Setup

Create a Python virtual environment and install the required dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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

Execute the ML pipeline using the provided Makefile targets:

```bash
make ingest     # Download and process power/weather data
make features   # Generate lagged and rolling features
make train-xgb  # Train XGBoost baseline model
make evaluate   # Generate evaluation metrics and plots
```

Deploy the trained model for serving:

```bash
make serve-mlflow  # Serve via MLflow model server
# or
make api          # Serve via FastAPI application
```

## Technology Stack

The system uses MLflow as the central framework for experiment tracking and model registry management. Model implementations include XGBoost for baseline comparisons and PyTorch LSTM networks for neural forecasting approaches. Data processing follows a pandas-first methodology with Parquet file storage for efficient columnar data access.

Model serving operates through both MLflow's built-in model server and custom FastAPI applications. Infrastructure provisioning uses Terraform for reproducible AWS resource management, while Packer creates custom AMIs containing ML dependencies and NVIDIA drivers.

Compute resources include EC2 g6f.xlarge instances for development and testing, with g6.xlarge instances for production workloads. Both instance types provide L4 GPU acceleration for neural network training. Remote access uses AWS Systems Manager Session Manager, eliminating SSH key management and improving security posture.

## Security Considerations

This repository is publicly accessible on GitHub. Never commit credentials, API keys, or other sensitive information to version control. The .gitignore file excludes common secret file patterns, but developers must remain vigilant about accidental credential exposure.

Local development uses .env files for configuration management. These files are excluded from version control and should contain only non-sensitive configuration values. For cloud deployments, store sensitive values in AWS Parameter Store or similar secure configuration services.

Infrastructure secrets such as Terraform variable files containing credentials should never be committed. Use Terraform Cloud, AWS Secrets Manager, or similar services for secure infrastructure credential management.

## Evaluation Metrics

Model performance evaluation uses standard forecasting metrics including Mean Absolute Error (MAE), Root Mean Square Error (RMSE), and Mean Absolute Percentage Error (MAPE). These metrics are compared against naive baseline forecasts to establish performance improvements.

Reproducibility validation ensures identical results across different computing environments. The same model training code should produce consistent outputs whether executed locally, on EC2 instances, or within SageMaker environments.

Operational metrics include model registry promotion workflows and serving endpoint performance. The system demonstrates automated model deployment through MLflow's model registry, enabling controlled promotion from staging to production environments.

## Deployment Environments

Local development uses synthetic data generation for rapid iteration without external API dependencies. This environment supports full pipeline testing and model development using CPU-only resources.

AWS EC2 g6f.xlarge instances provide GPU acceleration for development and testing workflows. These instances offer cost-effective GPU access for model training experiments and hyperparameter optimization.

Production deployments use EC2 g6.xlarge instances for optimized training and serving performance. The same infrastructure supports both development and production workloads through instance type selection.

## Data Sources

Power demand data comes from public APIs including NYISO (New York Independent System Operator) and CAISO (California Independent System Operator). These sources provide real-time and historical electricity demand data at hourly intervals.

Weather data integration uses NOAA (National Oceanic and Atmospheric Administration) APIs and the Meteostat Python library. Weather features include temperature, wind speed, and other meteorological variables that correlate with power demand patterns.

Calendar and temporal features incorporate holiday calendars, hour-of-day indicators, day-of-week patterns, and seasonal variables. These features capture regular demand cycles and special event impacts on power consumption.

## Contributing

Development follows standard Git workflow practices with feature branches for all changes. Infrastructure modifications must be tested in the development environment before applying to production resources.

Documentation updates should accompany any architectural changes or new feature implementations. This ensures that setup instructions and usage examples remain current with code modifications.

Security review is required for any changes affecting credential management, network access, or data handling. Never commit credentials or sensitive configuration information to the repository.

## License

MIT License - see LICENSE file for details
