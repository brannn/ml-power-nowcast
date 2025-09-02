.PHONY: help setup ingest features train-xgb train-lstm evaluate serve-mlflow serve-fastapi serve-info serve-test api fmt lint test clean infra-plan infra-apply infra-destroy build-ami docker-build docker-run

# Default target
help:
	@echo "ML Power Nowcast - Available targets:"
	@echo ""
	@echo "Setup:"
	@echo "  setup          - Create venv and install runtime dependencies"
	@echo "  setup-dev      - Create venv and install all dependencies (runtime + dev)"
	@echo "  build-ami      - Build custom Ubuntu ML AMI with Packer"
	@echo ""
	@echo "Infrastructure:"
	@echo "  infra-plan     - Plan Terraform infrastructure changes"
	@echo "  infra-apply    - Apply Terraform infrastructure"
	@echo "  infra-destroy  - Destroy Terraform infrastructure"
	@echo ""
	@echo "ML Pipeline:"
	@echo "  ingest         - Ingest power and weather data"
	@echo "  features       - Build features with lags and rolling windows"
	@echo "  train-xgb      - Train XGBoost baseline model"

	@echo "  evaluate       - Evaluate models and generate plots"
	@echo ""
	@echo "Serving:"
	@echo "  serve-fastapi  - Serve model via FastAPI (recommended)"
	@echo "  serve-mlflow   - Serve model via MLflow built-in server"
	@echo "  serve-info     - Show information about registered models"
	@echo "  serve-test     - Test serving endpoints"
	@echo "  api            - Alias for serve-fastapi"
	@echo ""
	@echo "Data Management:"
	@echo "  prepopulate-s3 - Show S3 pre-population usage"
	@echo "  list-s3-data   - List existing data in S3 bucket"
	@echo ""
	@echo "Development:"
	@echo "  fmt            - Format code with black and isort"
	@echo "  lint           - Lint code with flake8"
	@echo "  test           - Run pytest test suite"
	@echo "  clean          - Clean temporary files and artifacts"

setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "Virtual environment created. Activate with: source .venv/bin/activate"

setup-dev:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
	.venv/bin/pip install -e .
	@echo "Development environment created. Activate with: source .venv/bin/activate"

build-ami:
	cd packer/ubuntu-ml-base && packer build ubuntu-ml-base.pkr.hcl

infra-plan:
	cd terraform/environments/dev && terraform plan

infra-apply:
	cd terraform/environments/dev && terraform apply

infra-destroy:
	cd terraform/environments/dev && terraform destroy

ingest:
	python3 -m src.ingest.pull_power --days 120
	python3 -m src.ingest.pull_weather --days 120

features:
	python3 -m src.features.build_features --horizon 30 --lags "1,2,3,6,12,24" --rolling "3,6,12"

train-xgb:
	python3 -m src.models.train_xgb --horizon 30 --n_estimators 500 --max_depth 6



evaluate:
	python3 -m src.models.evaluate --horizon 30

# S3 data pre-population
prepopulate-s3:
	@echo "Usage: make prepopulate-s3 BUCKET=your-bucket-name [YEARS=3]"
	@echo "Example: make prepopulate-s3 BUCKET=ml-power-nowcast-dev-mlflow-abc123"

prepopulate-s3-run:
	python3 scripts/prepopulate_s3_data.py --bucket $(BUCKET) --years $(or $(YEARS),3)

list-s3-data:
	python3 scripts/prepopulate_s3_data.py --bucket $(BUCKET) --list-only

serve-mlflow:
	mlflow models serve -m "models:/power-nowcast/Production" -p 5000

api:
	uvicorn src.serve.fastapi_app:app --host 0.0.0.0 --port 8000 --reload

fmt:
	black src/ tests/ --line-length 88
	isort src/ tests/ --profile black

lint:
	flake8 src/ tests/ --max-line-length 88 --extend-ignore E203,W503

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-fast:
	pytest tests/ -v -m "not slow"

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	rm -rf data/raw/

# Serving targets per Section 13
serve-fastapi:
	@echo "🚀 Starting FastAPI serving (recommended)..."
	./scripts/serve_model.sh --type fastapi --port 8000

serve-mlflow:
	@echo "🚀 Starting MLflow built-in serving..."
	./scripts/serve_model.sh --type mlflow --port 5000

serve-info:
	@echo "📋 Model registry information..."
	python src/serve/mlflow_serve.py --info

serve-test:
	@echo "🧪 Testing serving endpoints..."
	@echo "Testing FastAPI (port 8000)..."
	@curl -f http://localhost:8000/health || echo "FastAPI not running"
	@echo ""
	@echo "Testing MLflow (port 5000)..."
	@curl -f http://localhost:5000/ping || echo "MLflow serving not running"

api: serve-fastapi

# Docker targets per Section 13
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t power-nowcast-api .

docker-run:
	@echo "🐳 Running Docker container..."
	docker run -p 8000:8000 \
		-e MLFLOW_TRACKING_URI=http://host.docker.internal:5001 \
		power-nowcast-api
	rm -rf data/interim/
	rm -rf data/features/
