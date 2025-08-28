#!/usr/bin/env bash
# Scaffold a pandas-first Power Nowcasting repo with MLflow wiring
# Usage: ./scaffold_power_nowcast.sh [project_name]
set -euo pipefail

PROJECT="${1:-power-nowcast}"

echo ">> Creating project: ${PROJECT}"
mkdir -p "$PROJECT"/{data/raw,data/interim,data/features,notebooks,artifacts,src/{ingest,features,models,serve}}
touch "$PROJECT/.gitignore"

# .gitignore
cat > "$PROJECT/.gitignore" <<'EOF'
# Python
__pycache__/
*.pyc
.venv/
.env

# MLflow local artifacts
mlruns/
mlruns_artifacts/

# OS / tooling
.DS_Store
EOF

# README
cat > "$PROJECT/README.md" <<'EOF'
# Power Nowcasting — Lightweight GPU POC (with MLflow, pandas-first)

Minimal, portable scaffold that pairs with the Option C implementation plan.
Includes:
- Synthetic-friendly ingest placeholders
- Feature builder (pandas)
- XGBoost baseline with MLflow autologging
- FastAPI serving stub
- Makefile targets for quick iteration

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# (Optional) Run MLflow tracking server locally
export MLFLOW_TRACKING_URI=http://0.0.0.0:5001
mlflow server --backend-store-uri sqlite:///mlruns.db \
  --default-artifact-root ./mlruns_artifacts --host 0.0.0.0 --port 5001

# Run pipeline
make ingest
make features
make train-xgb
make evaluate

# Serve (either MLflow model server or FastAPI)
make serve-mlflow
# or
make api
```
EOF

# requirements.txt
cat > "$PROJECT/requirements.txt" <<'EOF'
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
EOF

# Makefile
cat > "$PROJECT/Makefile" <<'EOF'
.PHONY: ingest features train-xgb evaluate serve-mlflow api fmt

ingest:
\tpython -m src.ingest.pull_power --days 120
\tpython -m src.ingest.pull_weather --days 120

features:
\tpython -m src.features.build_features --horizon 30 --lags "1,2,3,6,12,24" --rolling "3,6,12"

train-xgb:
\tpython -m src.models.train_xgb --horizon 30 --n_estimators 500 --max_depth 6

evaluate:
\tpython -m src.models.evaluate --horizon 30

serve-mlflow:
\tmlflow models serve -m "models:/power-nowcast/Production" -p 5000

api:
\tuvicorn src.serve.fastapi_app:app --host 0.0.0.0 --port 8000

fmt:
\tpython - <<'PY'\nfrom pathlib import Path\nimport subprocess\nfor p in Path('src').rglob('*.py'):\n    try:\n        subprocess.run(['python','-m','black',str(p)], check=False)\n    except Exception:\n        pass\nPY
EOF

# Placeholder ingest scripts
cat > "$PROJECT/src/ingest/pull_power.py" <<'EOF'
import argparse, pathlib, pandas as pd, numpy as np
from datetime import datetime, timedelta, timezone

def main(days: int):
    # Synthetic placeholder: generates hourly "load" for the last N days
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    idx = pd.date_range(start, end, freq="H", tz="UTC")
    # daily and weekly seasonality + noise
    hours = idx.hour.to_numpy()
    dow = idx.dayofweek.to_numpy()
    base = 100 + 20*np.sin(2*np.pi*hours/24) + 10*np.cos(2*np.pi*dow/7)
    noise = np.random.normal(0, 3, size=len(idx))
    load = base + noise
    df = pd.DataFrame({"timestamp": idx, "load": load})
    out = pathlib.Path("data/raw/power.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"Wrote {out} ({len(df)} rows)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    args = ap.parse_args()
    main(args.days)
EOF

cat > "$PROJECT/src/ingest/pull_weather.py" <<'EOF'
import argparse, pathlib, pandas as pd, numpy as np
from datetime import datetime, timedelta, timezone

def main(days: int):
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    idx = pd.date_range(start, end, freq="H", tz="UTC")
    hours = idx.hour.to_numpy()
    temp = 15 + 10*np.sin(2*np.pi*(hours-6)/24) + np.random.normal(0, 1.5, size=len(idx))
    wind = 5 + 2*np.abs(np.sin(2*np.pi*hours/24)) + np.random.normal(0, 0.5, size=len(idx))
    df = pd.DataFrame({"timestamp": idx, "temp_c": temp, "wind_mps": wind})
    out = pathlib.Path("data/raw/weather.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"Wrote {out} ({len(df)} rows)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    args = ap.parse_args()
    main(args.days)
EOF

# Feature builder
cat > "$PROJECT/src/features/build_features.py" <<'EOF'
import argparse, json
from pathlib import Path
import pandas as pd

def build(horizon: int, lags: list[int], rolling: list[int]):
    power = pd.read_parquet("data/raw/power.parquet")
    weather = pd.read_parquet("data/raw/weather.parquet")
    for df in (power, weather):
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    power = power.set_index("timestamp").sort_index()
    weather = weather.set_index("timestamp").sort_index()
    df = power.join(weather, how="inner").reset_index()
    df["hour"] = df["timestamp"].dt.hour
    df["dow"] = df["timestamp"].dt.dayofweek
    # lags
    for L in lags:
        df[f"load_lag{L}"] = df["load"].shift(L)
    # rolling means on load and temp
    for W in rolling:
        df[f"load_roll{W}"] = df["load"].rolling(window=W, min_periods=1).mean()
        df[f"temp_roll{W}"] = df["temp_c"].rolling(window=W, min_periods=1).mean()
    # target: horizon-step ahead load
    df["target"] = df["load"].shift(-horizon)
    df = df.dropna().reset_index(drop=True)
    out = Path("data/features/train.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)

    manifest = {
        "rows": int(len(df)),
        "columns": df.columns.tolist(),
        "horizon": horizon,
        "lags": lags,
        "rolling": rolling,
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/feature_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {out} with {len(df)} rows")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=30, help="steps ahead (hours if hourly)")
    ap.add_argument("--lags", type=str, default="1,2,3,6,12,24")
    ap.add_argument("--rolling", type=str, default="3,6,12")
    args = ap.parse_args()
    lags = [int(x) for x in args.lags.split(",") if x]
    rolling = [int(x) for x in args.rolling.split(",") if x]
    build(args.horizon, lags, rolling)
EOF

# XGBoost trainer
cat > "$PROJECT/src/models/train_xgb.py" <<'EOF'
import argparse, numpy as np, pandas as pd
import mlflow, mlflow.xgboost
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

def train(horizon:int, n_estimators:int, max_depth:int):
    df = pd.read_parquet("data/features/train.parquet")
    y = df["target"].to_numpy()
    X = df.drop(columns=["target","timestamp"]).to_numpy()

    X_train, X_valid, y_train, y_valid = train_test_split(X, y, test_size=0.2, random_state=42)

    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"xgb@h{horizon}"):
        mlflow.xgboost.autolog(log_input_examples=True)
        model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            tree_method="hist",
        )
        model.fit(X_train, y_train)

        preds = model.predict(X_valid)
        mae = mean_absolute_error(y_valid, preds)
        rmse = mean_squared_error(y_valid, preds, squared=False)
        mape = float(np.mean(np.abs((y_valid - preds) / np.clip(np.abs(y_valid), 1e-6, None))) * 100)

        mlflow.log_metrics({"MAE": mae, "RMSE": rmse, "MAPE": mape})
        print({"MAE": mae, "RMSE": rmse, "MAPE": mape})

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=30)
    ap.add_argument("--n_estimators", type=int, default=500)
    ap.add_argument("--max_depth", type=int, default=6)
    args = ap.parse_args()
    train(args.horizon, args.n_estimators, args.max_depth)
EOF

# Evaluator
cat > "$PROJECT/src/models/evaluate.py" <<'EOF'
import argparse, numpy as np, pandas as pd, matplotlib.pyplot as plt
import mlflow
from sklearn.metrics import mean_absolute_error, mean_squared_error

def evaluate(horizon:int):
    df = pd.read_parquet("data/features/train.parquet")
    # naive baseline: target vs previous value (lag1)
    y = df["target"].to_numpy()
    yhat = df["load_lag1"].to_numpy()
    mae = mean_absolute_error(y, yhat)
    rmse = mean_squared_error(y, yhat, squared=False)

    # Plot: target vs naive
    fig = plt.figure()
    plt.plot(df["timestamp"].iloc[:500], y[:500], label="target")
    plt.plot(df["timestamp"].iloc[:500], yhat[:500], label="naive_lag1")
    plt.legend()
    fig_path = "artifacts/pred_vs_actual_naive.png"
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)

    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"evaluate@h{horizon}"):
        mlflow.log_metrics({"MAE_naive": mae, "RMSE_naive": rmse})
        mlflow.log_artifact(fig_path)
    print({"MAE_naive": mae, "RMSE_naive": rmse, "plot": fig_path})

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=30)
    args = ap.parse_args()
    evaluate(args.horizon)
EOF

# FastAPI app
cat > "$PROJECT/src/serve/fastapi_app.py" <<'EOF'
from fastapi import FastAPI
import os, pandas as pd, mlflow.pyfunc

app = FastAPI(title="Power Nowcast API")

# Lazy-load model from registry if configured; otherwise just a health endpoint.
MODEL_URI = os.getenv("MODEL_URI") or "models:/power-nowcast/Production"
_model = None

@app.get("/health")
def health():
    return {"ok": True}

@app.on_event("startup")
def load_model():
    global _model
    try:
        _model = mlflow.pyfunc.load_model(MODEL_URI)
    except Exception:
        _model = None

@app.post("/nowcast")
def nowcast(payload: dict):
    if _model is None:
        return {"error": "Model not loaded. Set MODEL_URI or promote a model to Production."}
    # Expect payload like {"rows": [{"load":..., "temp_c":..., ...}, ...]}
    df = pd.DataFrame(payload.get("rows", []))
    preds = _model.predict(df)
    try:
        preds = preds.tolist()
    except Exception:
        pass
    return {"yhat": preds}
EOF

# env example
cat > "$PROJECT/.env.example" <<'EOF'
# MLflow tracking
MLFLOW_TRACKING_URI=http://127.0.0.1:5001
# For S3/MinIO artifact store (optional)
# MLFLOW_S3_ENDPOINT_URL=https://minio.example.com
# AWS_ACCESS_KEY_ID=changeme
# AWS_SECRET_ACCESS_KEY=changeme

# Serving (optional override of model location)
# MODEL_URI=models:/power-nowcast/Production
EOF

# Optional git init
if command -v git >/dev/null 2>&1; then
  (cd "$PROJECT" && git init -q && git add . && git commit -m "chore: scaffold MLflow pandas POC" -q) || true
fi

echo ">> Done. Project created at ./${PROJECT}"
