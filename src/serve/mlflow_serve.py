#!/usr/bin/env python3
"""
MLflow built-in serving utilities.

Implements Section 13 MLflow pyfunc serving option with model management
and serving configuration per the implementation plan.
"""

import argparse
import os
import subprocess
import sys
import time
from typing import Optional, Dict, Any
import logging

import mlflow
from mlflow.tracking import MlflowClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_model_uri(model_name: str, stage: str = "Production") -> str:
    """
    Get model URI for serving.
    
    Args:
        model_name: Name of the registered model
        stage: Model stage (Production, Staging, etc.)
        
    Returns:
        Model URI for MLflow serving
    """
    return f"models:/{model_name}/{stage}"


def check_model_exists(model_name: str, stage: str = "Production") -> bool:
    """
    Check if model exists in the specified stage.
    
    Args:
        model_name: Name of the registered model
        stage: Model stage to check
        
    Returns:
        True if model exists, False otherwise
    """
    try:
        client = MlflowClient()
        model_versions = client.get_latest_versions(model_name, stages=[stage])
        return len(model_versions) > 0
    except Exception as e:
        logger.error(f"Error checking model existence: {e}")
        return False


def get_model_info(model_name: str, stage: str = "Production") -> Optional[Dict[str, Any]]:
    """
    Get detailed model information.
    
    Args:
        model_name: Name of the registered model
        stage: Model stage
        
    Returns:
        Dictionary with model information or None if not found
    """
    try:
        client = MlflowClient()
        model_versions = client.get_latest_versions(model_name, stages=[stage])
        
        if not model_versions:
            return None
        
        model_version = model_versions[0]
        return {
            "name": model_name,
            "version": model_version.version,
            "stage": model_version.current_stage,
            "run_id": model_version.run_id,
            "creation_timestamp": model_version.creation_timestamp,
            "description": model_version.description,
            "tags": model_version.tags
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return None


def serve_model(
    model_name: str,
    stage: str = "Production",
    port: int = 5000,
    host: str = "0.0.0.0",
    workers: int = 1,
    timeout: int = 60,
    env_vars: Optional[Dict[str, str]] = None
) -> subprocess.Popen:
    """
    Start MLflow model serving.
    
    Args:
        model_name: Name of the registered model
        stage: Model stage to serve
        port: Port to serve on
        host: Host to bind to
        workers: Number of worker processes
        timeout: Request timeout in seconds
        env_vars: Additional environment variables
        
    Returns:
        Subprocess handle for the serving process
    """
    # Check if model exists
    if not check_model_exists(model_name, stage):
        raise ValueError(f"Model {model_name} not found in {stage} stage")
    
    # Get model info
    model_info = get_model_info(model_name, stage)
    if model_info:
        logger.info(f"Serving model: {model_info['name']} v{model_info['version']} ({model_info['stage']})")
    
    # Build MLflow serve command
    model_uri = get_model_uri(model_name, stage)
    cmd = [
        "mlflow", "models", "serve",
        "-m", model_uri,
        "-p", str(port),
        "-h", host,
        "--timeout", str(timeout)
    ]
    
    # Add workers if > 1
    if workers > 1:
        cmd.extend(["--workers", str(workers)])
    
    # Set up environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    logger.info(f"Starting MLflow serving with command: {' '.join(cmd)}")
    
    try:
        # Start the serving process
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Wait a moment to check if process started successfully
        time.sleep(2)
        if process.poll() is not None:
            output, _ = process.communicate()
            raise RuntimeError(f"MLflow serving failed to start: {output}")
        
        logger.info(f"MLflow serving started on {host}:{port} (PID: {process.pid})")
        return process
        
    except Exception as e:
        logger.error(f"Failed to start MLflow serving: {e}")
        raise


def test_serving_endpoint(host: str = "localhost", port: int = 5000, timeout: int = 30) -> bool:
    """
    Test if the serving endpoint is responding.
    
    Args:
        host: Host to test
        port: Port to test
        timeout: Timeout for the test
        
    Returns:
        True if endpoint is responding, False otherwise
    """
    import requests
    
    url = f"http://{host}:{port}/ping"
    
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Endpoint test failed: {e}")
        return False


def make_prediction_request(
    features: Dict[str, float],
    host: str = "localhost",
    port: int = 5000,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Make a prediction request to the serving endpoint.
    
    Args:
        features: Feature dictionary for prediction
        host: Host of the serving endpoint
        port: Port of the serving endpoint
        timeout: Request timeout
        
    Returns:
        Prediction response
    """
    import requests
    import pandas as pd
    
    url = f"http://{host}:{port}/invocations"
    
    # Convert features to DataFrame format expected by MLflow
    df = pd.DataFrame([features])
    
    # Prepare request payload
    payload = {
        "dataframe_split": {
            "columns": df.columns.tolist(),
            "data": df.values.tolist()
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Prediction request failed: {e}")
        raise


def main() -> None:
    """Main function for MLflow serving CLI."""
    parser = argparse.ArgumentParser(description="MLflow model serving utilities")
    parser.add_argument("--model-name", default="power-nowcast", help="Model name to serve")
    parser.add_argument("--stage", default="Production", help="Model stage to serve")
    parser.add_argument("--port", type=int, default=5000, help="Port to serve on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds")
    parser.add_argument("--test", action="store_true", help="Test the serving endpoint")
    parser.add_argument("--info", action="store_true", help="Show model information")
    
    args = parser.parse_args()
    
    try:
        if args.info:
            # Show model information
            model_info = get_model_info(args.model_name, args.stage)
            if model_info:
                print(f"Model Information:")
                print(f"  Name: {model_info['name']}")
                print(f"  Version: {model_info['version']}")
                print(f"  Stage: {model_info['stage']}")
                print(f"  Run ID: {model_info['run_id']}")
                print(f"  Created: {model_info['creation_timestamp']}")
                if model_info['description']:
                    print(f"  Description: {model_info['description']}")
            else:
                print(f"Model {args.model_name} not found in {args.stage} stage")
                sys.exit(1)
        
        elif args.test:
            # Test serving endpoint
            print(f"Testing serving endpoint at {args.host}:{args.port}...")
            if test_serving_endpoint(args.host, args.port):
                print("✅ Serving endpoint is responding")
                
                # Test prediction
                sample_features = {
                    "load_lag_1h": 1200.0,
                    "load_lag_2h": 1150.0,
                    "temp_c": 22.5,
                    "humidity": 65.0,
                    "hour": 14,
                    "day_of_week": 2
                }
                
                try:
                    result = make_prediction_request(sample_features, args.host, args.port)
                    print(f"✅ Sample prediction: {result}")
                except Exception as e:
                    print(f"❌ Prediction test failed: {e}")
            else:
                print("❌ Serving endpoint is not responding")
                sys.exit(1)
        
        else:
            # Start serving
            process = serve_model(
                args.model_name,
                args.stage,
                args.port,
                args.host,
                args.workers,
                args.timeout
            )
            
            try:
                # Stream output
                for line in process.stdout:
                    print(line.strip())
            except KeyboardInterrupt:
                logger.info("Stopping MLflow serving...")
                process.terminate()
                process.wait()
                logger.info("MLflow serving stopped")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
