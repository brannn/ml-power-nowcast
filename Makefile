.PHONY: help setup ingest features train-xgb train-lstm evaluate serve-mlflow api fmt lint test clean infra-plan infra-apply infra-destroy build-ami

# Default target
help:
	@echo "ML Power Nowcast - Available targets:"
	@echo ""
	@echo "Setup:"
	@echo "  setup          - Create venv and install dependencies"
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
	@echo "  train-lstm     - Train LSTM neural model"
	@echo "  evaluate       - Evaluate models and generate plots"
	@echo ""
	@echo "Serving:"
	@echo "  serve-mlflow   - Serve model via MLflow"
	@echo "  api            - Start FastAPI server"
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

train-lstm:
	python3 -m src.models.train_lstm --horizon 30 --hidden_size 64 --layers 2 --epochs 10 --batch_size 256

evaluate:
	python3 -m src.models.evaluate --horizon 30

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
	rm -rf data/interim/
	rm -rf data/features/
