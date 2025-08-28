#!/bin/bash
# Model serving script per Section 13
# Supports both MLflow built-in and FastAPI serving options

set -e

# Default values
MODEL_NAME="power-nowcast"
MODEL_STAGE="Production"
SERVING_TYPE="fastapi"
PORT=8000
HOST="0.0.0.0"
WORKERS=1

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model-name)
            MODEL_NAME="$2"
            shift 2
            ;;
        --stage)
            MODEL_STAGE="$2"
            shift 2
            ;;
        --type)
            SERVING_TYPE="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --model-name NAME    Model name (default: power-nowcast)"
            echo "  --stage STAGE        Model stage (default: Production)"
            echo "  --type TYPE          Serving type: fastapi|mlflow (default: fastapi)"
            echo "  --port PORT          Port to serve on (default: 8000 for FastAPI, 5000 for MLflow)"
            echo "  --host HOST          Host to bind to (default: 0.0.0.0)"
            echo "  --workers NUM        Number of workers (default: 1)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set default ports based on serving type
if [[ "$SERVING_TYPE" == "mlflow" && "$PORT" == "8000" ]]; then
    PORT=5000
fi

echo "🚀 Starting Power Nowcast Model Serving"
echo "========================================"
echo "Model: $MODEL_NAME"
echo "Stage: $MODEL_STAGE"
echo "Type: $SERVING_TYPE"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Workers: $WORKERS"
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not detected. Activating .venv..."
    if [[ -f ".venv/bin/activate" ]]; then
        source .venv/bin/activate
    else
        echo "❌ Virtual environment not found. Please run 'make setup' first."
        exit 1
    fi
fi

# Check MLflow tracking URI
if [[ -z "$MLFLOW_TRACKING_URI" ]]; then
    echo "⚠️  MLFLOW_TRACKING_URI not set. Using default: http://localhost:5001"
    export MLFLOW_TRACKING_URI="http://localhost:5001"
fi

# Set environment variables for serving
export MODEL_NAME="$MODEL_NAME"
export MODEL_STAGE="$MODEL_STAGE"

case $SERVING_TYPE in
    "fastapi")
        echo "🔧 Starting FastAPI serving..."
        echo "API Documentation: http://$HOST:$PORT/docs"
        echo "Health Check: http://$HOST:$PORT/health"
        echo ""
        
        # Start FastAPI server
        uvicorn src.serve.fastapi_app:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --log-level info
        ;;
        
    "mlflow")
        echo "🔧 Starting MLflow built-in serving..."
        echo "Ping endpoint: http://$HOST:$PORT/ping"
        echo "Invocations endpoint: http://$HOST:$PORT/invocations"
        echo ""
        
        # Start MLflow serving
        python src/serve/mlflow_serve.py \
            --model-name "$MODEL_NAME" \
            --stage "$MODEL_STAGE" \
            --port "$PORT" \
            --host "$HOST" \
            --workers "$WORKERS"
        ;;
        
    *)
        echo "❌ Unknown serving type: $SERVING_TYPE"
        echo "Supported types: fastapi, mlflow"
        exit 1
        ;;
esac
