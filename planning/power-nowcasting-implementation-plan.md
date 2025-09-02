
# Option C — Power Nowcasting (Lightweight GPU POC)  
**With MLflow integrated from day 0 for portability and reproducibility**

> Goal: Build a concise, GPU-capable forecasting POC that ingests public power/weather/temporal signals, trains & evaluates classical and neural models, and exposes a tiny prediction API — all **tracked and packaged with MLflow** so it can be moved across environments (local, EC2 g5.xlarge, or SageMaker).

---

## 1) Scope & Success Criteria

**Business outcome (POC):**
- Generate 15–60 minute **nowcasts** of load or generation for a chosen region/site.
- Demonstrate **reproducible experiments** and **one-command model serving**.

**Technical exit criteria:**
- ✅ MLflow tracking server running; all runs logged with params, metrics, and artifacts.
- ✅ At least 2 model families compared (e.g., **XGBoost baseline** vs **LSTM**/**TFT-lite**).
- ✅ Metrics reported: **MAE, RMSE, MAPE**, plus **Pinball loss τ∈{0.1,0.5,0.9}** if doing probabilistic forecasts.
- ✅ Best model **registered** to MLflow **Model Registry**, **served** via MLflow or FastAPI.
- ✅ Re-run end‑to‑end on a fresh environment (portability proof).

---

## 2) Data sources (public & free)

Pick a small, friendly set. Examples:
- **Power / load / generation**: New York ISO (NYISO) or CAISO OASIS day‑ahead/real-time demand; ENTSO‑E (EU) (subject to terms). Use a small window (e.g., last 90 days) for the POC.
- **Weather**: NOAA/NWS API or Meteostat (Python). Cache to local Parquet for repeatability.
- **Calendar/time features**: Holiday calendars (e.g., `holidays` Python lib), hour-of-day, day-of-week, weekend, season.

> For the POC, **snapshot** a modest time range (e.g., 3–6 months) into `data/raw/` and treat it as read‑only for runs. We will log the **manifest** (hashes + date ranges) to MLflow artifacts to ensure reproducibility.

---

## 3) Architecture (POC)

```
[Data Ingest] -> [Feature Build] -> [Model Train (GPU/CPU)] -> [Eval + Plots]
       |                    |                 |                      |
       +---- MLflow artifacts & params ------ + --------- MLflow metrics & model -----> [Model Registry]
                                                                                                  |
                                                                                          [Serve (MLflow/FASTAPI)]
```

**MLflow is the “glue”:** every step logs inputs, code SHA, params, metrics, artifacts, and models, enabling apples‑to‑apples comparisons and portable deployment.

---

## 4) Repo layout

```
ml-power-nowcast/
  data/
    raw/                   # (optional) small cached CSV/Parquet slices for reproducibility
    interim/               # cleaned & aligned tables
    features/              # final feature matrices (train/valid/test)
  notebooks/
  src/
    ingest/
      pull_power.py
      pull_weather.py
    features/
      build_features.py
      windowing.py
    models/
      train_xgb.py
      train_lightgbm.py
      evaluate.py
    serve/
      fastapi_app.py
  mlflow_client.py
  requirements.txt
  Makefile
  README.md
```

---

## 5) Environment & tooling

- **Compute**: EC2 **g6f.xlarge** (L4, 1 GPU) for development/testing, **g6.xlarge** (L4, 1 GPU) for production training/serving. Both compatible with MLflow.
- **Python**: 3.12+ (minimum); always work in a venv.
- **Key libs**: `mlflow`, `pandas`, `pyarrow`, `xgboost`, `lightgbm`, `torch`, `scikit-learn`, `fastapi`, `uvicorn`, `holidays`, `meteostat` (or NOAA client), `matplotlib`.  
- **Artifacts**: S3 or MinIO bucket recommended (local FS is fine for day‑1).

`requirements.txt` (minimal starting point):
```
mlflow>=2.12
pandas>=2.2
pyarrow>=16
numpy>=1.26
scikit-learn>=1.5
xgboost>=2.0
lightgbm>=4.3
torch>=2.3
fastapi>=0.112
uvicorn[standard]>=0.30
holidays>=0.56
meteostat>=1.6
matplotlib>=3.9
```

---

## 6) MLflow setup (Day‑1, 10 minutes)

**Option A — local lightweight (single node):**
```bash
# ENV (adjust for S3/MinIO if used)
export MLFLOW_TRACKING_URI=http://0.0.0.0:5001
export AWS_DEFAULT_REGION=us-west-2
# If using MinIO:
# export MLFLOW_S3_ENDPOINT_URL=https://minio.yourdomain
# export AWS_ACCESS_KEY_ID=...
# export AWS_SECRET_ACCESS_KEY=...

mlflow server \
  --backend-store-uri sqlite:///mlruns.db \
  --default-artifact-root ./mlruns_artifacts \
  --host 0.0.0.0 --port 5001
```

**Option B — remote artifacts (recommended):**
```bash
mlflow server \
  --backend-store-uri sqlite:///mlruns.db \
  --default-artifact-root s3://mlflow-artifacts-power/ \
  --host 0.0.0.0 --port 5001
```

> You can later swap `sqlite` → `postgresql://` and local artifacts → S3/MinIO with no code changes.

---

## 7) Makefile targets (quality‑of‑life)

```makefile
.PHONY: ingest features train-xgb train-lightgbm evaluate serve-mlflow api

ingest:
\tpython -m src.ingest.pull_power --days 120
\tpython -m src.ingest.pull_weather --days 120

features:
\tpython -m src.features.build_features --horizon 30 --lags "1,2,3,6,12,24" --rolling "3,6,12"

train-xgb:
\tpython -m src.models.train_xgb --horizon 30 --n_estimators 500 --max_depth 6

train-lightgbm:
\tpython -m src.models.train_lightgbm --horizon 30 --num_leaves 31 --learning_rate 0.1

evaluate:
\tpython -m src.models.evaluate --horizon 30

serve-mlflow:
\tmlflow models serve -m "models:/power-nowcast/Production" -p 5000

api:
\tuvicorn src.serve.fastapi_app:app --host 0.0.0.0 --port 8000
```

---

## 8) Ingest & feature build (with logging)

Key actions:
- Normalize timezones.
- Join power + weather on aligned intervals.
- Create calendar features.
- Create **lagged** features and **rolling stats** windows.
- **Log** the **feature manifest** as MLflow artifact (columns + dtypes + SHA256 of input files).

Example (inside `build_features.py`):
```python
import mlflow, json, hashlib, pandas as pd

def file_sha256(path):
    with open(path, "rb") as f: 
        import hashlib; return hashlib.sha256(f.read()).hexdigest()

mlflow.set_experiment("power-nowcast")
with mlflow.start_run(run_name="build_features@h30"):
    # ... load data, engineer features ...
    manifest = {
        "raw_files": {
            "power": file_sha256("data/raw/power.parquet"),
            "weather": file_sha256("data/raw/weather.parquet")
        },
        "feature_columns": list(df.columns),
        "rows": len(df),
    }
    with open("feature_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    mlflow.log_artifact("feature_manifest.json")
```

---

## 9) Baseline model (XGBoost) with autologging

`src/models/train_xgb.py` (sketch):
```python
import mlflow, mlflow.xgboost, xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

mlflow.set_experiment("power-nowcast")
with mlflow.start_run(run_name="xgb@h30"):
    mlflow.xgboost.autolog(log_input_examples=True)
    model = xgb.XGBRegressor(
        n_estimators=500, max_depth=6, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_valid)
    mae = mean_absolute_error(y_valid, preds)
    rmse = mean_squared_error(y_valid, preds, squared=False)
    mape = float(np.mean(np.abs((y_valid - preds)/np.clip(np.abs(y_valid),1e-6,None))) * 100)
    mlflow.log_metrics({"MAE": mae, "RMSE": rmse, "MAPE": mape})
    # Optionally save custom plots and log via mlflow.log_artifact(...)
```

---

## 10) Advanced tree-based models (LightGBM/CatBoost)

`src/models/train_lightgbm.py` (implemented):
```python
import lightgbm as lgb, mlflow, mlflow.lightgbm
mlflow.set_experiment("power-nowcast")
with mlflow.start_run(run_name="lightgbm@h30"):
    mlflow.lightgbm.autolog(log_models=True)
    # model = lgb.LGBMRegressor(...)
    # ... training with early stopping ...
    # mlflow.log_metrics({"MAE": mae, "RMSE": rmse})
    # mlflow.lightgbm.log_model(model, "model")
```

---

## 11) Evaluation, diagnostics & artifacts

- Metrics: `MAE`, `RMSE`, `MAPE`, optional **Pinball loss** for quantiles.
- Plots: `pred_vs_actual.png`, `residual_hist.png`, **backtest** chart by horizon, feature importance/SHAP.

```
mlflow.log_metrics({...})
mlflow.log_artifact("pred_vs_actual.png")
mlflow.log_artifact("backtest_horizon_30.png")
```

---

## 12) Model Registry & Promotion

Register best run’s model:
```python
from mlflow import register_model
mv = register_model("runs:/<RUN_ID>/model", "power-nowcast")
```

Promote to **Staging** / **Production**:
```python
from mlflow.tracking import MlflowClient
client = MlflowClient()
client.transition_model_version_stage("power-nowcast", mv.version, "Staging")
```

Add model‑level tags (dataset window, horizon, git SHA) so you can audit deployments.

---

## 13) Serving options

**A) MLflow built‑in server (pyfunc):**
```bash
mlflow models serve -m "models:/power-nowcast/Production" -p 5000
```

**B) FastAPI microservice (more control):**
```python
from fastapi import FastAPI
import mlflow.pyfunc, pandas as pd
app = FastAPI(title="Power Nowcast API")
model = mlflow.pyfunc.load_model("models:/power-nowcast/Production")

@app.post("/nowcast")
def nowcast(payload: dict):
    df = pd.DataFrame(payload["rows"])
    yhat = model.predict(df)
    return {"yhat": yhat.tolist()}
```

Dockerfile (optional):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src ./src
ENV MLFLOW_TRACKING_URI=...
CMD ["uvicorn", "src.serve.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 14) Portability playbook (local → EC2)

1) **Local dev**: run MLflow server (SQLite + local artifacts). Prove the pipeline end‑to‑end.
2) **EC2 g6f.xlarge** (development): reuse repo; point `MLFLOW_TRACKING_URI` to the same server; switch artifacts to S3. Confirm GPU training works and iterate on models.
3) **EC2 g6.xlarge** (production): deploy final model training and serving with optimized performance.

> All code remains the same — only **env vars / URIs** change, validating portability.

---

## 15) Security & governance (lightweight)

- Use **IAM roles** (or MinIO credentials) restricted to the artifacts bucket.
- Store secret config in `.env`/Parameter Store; never commit keys.
- Tag MLflow runs with `owner`, `dataset`, `horizon`, `git_sha` for traceability.

---

## 16) Timeline (1–3 working days)

- **Day 1**: Data snapshot, feature build, MLflow server up, baseline XGBoost run + artifacts.
- **Day 2**: LSTM GPU run, evaluation plots, backtesting, registry setup.
- **Day 3**: Serve best model, portability demo (fresh machine), POC readout.

---

## 17) Readout checklist

- Scorecard: MAE/RMSE/MAPE vs. naive/seasonal baselines.
- Charts: pred vs. actual; backtest across horizons; residuals.
- Ops demo: swap Production model version in MLflow; API gives new forecasts without code change.
- Portability demo: same repo on EC2 g6f.xlarge (dev) → g6.xlarge (prod) with identical MLflow runs.

---

## 18) Operational Notes

**Infrastructure Management:**
- **IaC Tools**: Use **Packer** for AMI building and **Terraform** for infrastructure provisioning
- **VPC**: Dedicated VPC named **'ml-dev'** for all ML workloads
- **Region**: Always deploy in **us-west-2** region
- **Base AMI**: Always use **Ubuntu 22.04 LTS** base AMI for better ML ecosystem compatibility
- **Remote Access**: Use **AWS Systems Manager (SSM)** for remote access, **not SSH**
- **Security**: No SSH keys or direct internet access required; all access via SSM Session Manager
- **SSM Ubuntu Setup**: Ubuntu requires manual SSM agent installation and configuration (see Packer requirements below)
- **Public Repository**: https://github.com/brannn/ml-power-nowcast - **NO SECRETS** in version control
- **Secret Management**: Use AWS Parameter Store, .env files (gitignored), or Terraform Cloud for sensitive values

**Compute Instance Strategy:**
- **Development/Testing**: EC2 **g6f.xlarge** (L4 GPU) for cost-effective iteration
- **Production**: EC2 **g6.xlarge** (L4 GPU) for optimized training and serving
- **MLflow Server**: Can run on smaller general-purpose instance (t3.medium/large) in same VPC

**Terraform Structure Recommendations:**
```
terraform/
  modules/
    vpc/           # ml-dev VPC with private subnets + SSM VPC endpoints
    security/      # Security groups, IAM roles for SSM (AmazonSSMManagedInstanceCore)
    compute/       # EC2 instances with GPU support + SSM instance profiles
    storage/       # S3 buckets for MLflow artifacts
  environments/
    dev/           # Development environment config
    prod/          # Production environment config
```

**Required VPC Endpoints for SSM (in private subnets):**
- `com.amazonaws.us-west-2.ssm`
- `com.amazonaws.us-west-2.ssmmessages`
- `com.amazonaws.us-west-2.ec2messages`

**Packer AMI Requirements:**
- Base: **Ubuntu 22.04 LTS** (better ML ecosystem support than Amazon Linux)
- **SSM Agent Setup** (critical for Ubuntu):
  ```bash
  # Install SSM agent
  sudo snap install amazon-ssm-agent --classic
  sudo systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
  sudo systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service
  ```
- **IAM Instance Profile**: Attach role with `AmazonSSMManagedInstanceCore` policy
- **VPC Endpoints**: Create SSM VPC endpoints for private subnet access (ssm, ssmmessages, ec2messages)
- Pre-installed: Docker, NVIDIA drivers (535+), AWS CLI v2
- Python 3.12+, CUDA toolkit 12.x for L4 GPU support
- MLflow dependencies and common ML libraries (PyTorch, XGBoost, etc.)
- **Rationale**: Ubuntu provides broader ML package compatibility and community support

---

## 19) Next steps (post‑POC)

- Switch backend store to **Postgres**, artifacts to **S3/MinIO** (if not already).
- Add **data validation** (Great Expectations or pydantic validators at serve time).
- Expand to **probabilistic nowcasts** (quantile regression or distributional outputs).
- Integrate with **Kubernetes** for scheduled retraining and canary rollouts.
- Fold into broader **MLOps** (CI/CD for models, feature store, monitoring).
