#!/usr/bin/env python3
"""
Tests for FastAPI serving application.

Tests cover Section 13 FastAPI microservice implementation including
model loading, prediction endpoints, error handling, and API validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np

from src.serve.fastapi_app import app, ModelManager


class TestModelManager:
    """Test ModelManager functionality."""

    def test_model_manager_init(self) -> None:
        """Test ModelManager initialization."""
        manager = ModelManager("test-model", "Staging")
        
        assert manager.model_name == "test-model"
        assert manager.model_stage == "Staging"
        assert manager.model is None
        assert manager.model_version is None
        assert not manager.is_loaded()

    @patch('mlflow.pyfunc.load_model')
    @patch('mlflow.tracking.MlflowClient')
    def test_load_model_success(self, mock_client_class: Mock, mock_load_model: Mock) -> None:
        """Test successful model loading."""
        # Mock MLflow client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock model version
        mock_version = Mock()
        mock_version.version = "1"
        mock_version.current_stage = "Production"
        mock_version.run_id = "test_run_id"
        mock_version.creation_timestamp = 1234567890
        
        mock_client.get_latest_versions.return_value = [mock_version]
        
        # Mock loaded model
        mock_model = Mock()
        mock_load_model.return_value = mock_model
        
        # Test loading
        manager = ModelManager("test-model", "Production")
        manager.load_model()
        
        assert manager.is_loaded()
        assert manager.model == mock_model
        assert manager.model_version == "1"
        assert manager.model_metadata["name"] == "test-model"

    @patch('mlflow.pyfunc.load_model')
    def test_load_model_failure(self, mock_load_model: Mock) -> None:
        """Test model loading failure."""
        mock_load_model.side_effect = Exception("Model not found")
        
        manager = ModelManager("nonexistent-model")
        
        with pytest.raises(RuntimeError, match="Could not load model"):
            manager.load_model()

    def test_predict_without_model(self) -> None:
        """Test prediction without loaded model."""
        manager = ModelManager("test-model")
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            manager.predict(pd.DataFrame({"feature": [1.0]}))

    @patch('mlflow.pyfunc.load_model')
    @patch('mlflow.tracking.MlflowClient')
    def test_predict_success(self, mock_client_class: Mock, mock_load_model: Mock) -> None:
        """Test successful prediction."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_latest_versions.return_value = []
        
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1234.5])
        mock_load_model.return_value = mock_model
        
        # Test prediction
        manager = ModelManager("test-model")
        manager.load_model()
        
        features_df = pd.DataFrame({"feature1": [1.0], "feature2": [2.0]})
        result = manager.predict(features_df)
        
        assert len(result) == 1
        assert result[0] == 1234.5
        mock_model.predict.assert_called_once_with(features_df)


class TestFastAPIEndpoints:
    """Test FastAPI endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_model_manager(self) -> Mock:
        """Create mock model manager."""
        manager = Mock(spec=ModelManager)
        manager.model_name = "test-model"
        manager.model_version = "1"
        manager.model_stage = "Production"
        manager.is_loaded.return_value = True
        manager.predict.return_value = np.array([1234.5])
        return manager

    def test_health_endpoint_healthy(self, client: TestClient) -> None:
        """Test health endpoint with healthy service."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.is_loaded.return_value = True
            mock_manager.model_name = "test-model"
            mock_manager.model_version = "1"
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["model_loaded"] is True
            assert data["model_name"] == "test-model"
            assert data["model_version"] == "1"

    def test_health_endpoint_unhealthy(self, client: TestClient) -> None:
        """Test health endpoint with unhealthy service."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.is_loaded.return_value = False
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["model_loaded"] is False

    def test_nowcast_endpoint_success(self, client: TestClient) -> None:
        """Test successful nowcast prediction."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.is_loaded.return_value = True
            mock_manager.model_name = "test-model"
            mock_manager.model_version = "1"
            mock_manager.predict.return_value = np.array([1234.5])
            
            request_data = {
                "features": {
                    "load_lag_1h": 1200.0,
                    "temp_c": 22.5,
                    "hour": 14
                }
            }
            
            response = client.post("/nowcast", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["prediction"] == 1234.5
            assert data["model_name"] == "test-model"
            assert data["model_version"] == "1"
            assert data["horizon_hours"] == 1

    def test_nowcast_endpoint_model_not_loaded(self, client: TestClient) -> None:
        """Test nowcast with model not loaded."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.is_loaded.return_value = False
            
            request_data = {
                "features": {
                    "load_lag_1h": 1200.0,
                    "temp_c": 22.5
                }
            }
            
            response = client.post("/nowcast", json=request_data)
            
            assert response.status_code == 503
            assert "Model not loaded" in response.json()["detail"]

    def test_nowcast_endpoint_invalid_features(self, client: TestClient) -> None:
        """Test nowcast with invalid features."""
        request_data = {
            "features": {
                "load_lag_1h": "invalid",  # Should be numeric
                "temp_c": 22.5
            }
        }
        
        response = client.post("/nowcast", json=request_data)
        
        assert response.status_code == 422  # Validation error

    def test_nowcast_endpoint_empty_features(self, client: TestClient) -> None:
        """Test nowcast with empty features."""
        request_data = {"features": {}}
        
        response = client.post("/nowcast", json=request_data)
        
        assert response.status_code == 422  # Validation error

    def test_batch_nowcast_endpoint_success(self, client: TestClient) -> None:
        """Test successful batch nowcast prediction."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.is_loaded.return_value = True
            mock_manager.model_name = "test-model"
            mock_manager.model_version = "1"
            mock_manager.predict.return_value = np.array([1234.5, 1456.7])
            
            request_data = {
                "rows": [
                    {"load_lag_1h": 1200.0, "temp_c": 22.5},
                    {"load_lag_1h": 1300.0, "temp_c": 25.0}
                ]
            }
            
            response = client.post("/nowcast/batch", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["predictions"]) == 2
            assert data["predictions"] == [1234.5, 1456.7]
            assert data["count"] == 2

    def test_batch_nowcast_endpoint_empty_rows(self, client: TestClient) -> None:
        """Test batch nowcast with empty rows."""
        request_data = {"rows": []}
        
        response = client.post("/nowcast/batch", json=request_data)
        
        assert response.status_code == 422  # Validation error

    def test_model_info_endpoint(self, client: TestClient) -> None:
        """Test model info endpoint."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.is_loaded.return_value = True
            mock_manager.model_metadata = {"name": "test-model", "version": "1"}
            mock_manager.last_loaded = None
            mock_manager.model_stage = "Production"
            
            response = client.get("/model/info")
            
            assert response.status_code == 200
            data = response.json()
            assert data["model_metadata"]["name"] == "test-model"
            assert data["model_stage"] == "Production"

    def test_model_info_endpoint_not_loaded(self, client: TestClient) -> None:
        """Test model info endpoint with model not loaded."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.is_loaded.return_value = False
            
            response = client.get("/model/info")
            
            assert response.status_code == 503

    def test_reload_model_endpoint_success(self, client: TestClient) -> None:
        """Test successful model reload."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.load_model.return_value = None
            mock_manager.model_name = "test-model"
            mock_manager.model_version = "2"
            
            response = client.post("/model/reload")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "reloaded successfully" in data["message"]

    def test_reload_model_endpoint_failure(self, client: TestClient) -> None:
        """Test model reload failure."""
        with patch('src.serve.fastapi_app.model_manager') as mock_manager:
            mock_manager.load_model.side_effect = Exception("Reload failed")
            
            response = client.post("/model/reload")
            
            assert response.status_code == 500
            assert "Model reload failed" in response.json()["detail"]


class TestRequestValidation:
    """Test request validation models."""

    def test_prediction_request_validation(self) -> None:
        """Test PredictionRequest validation."""
        from src.serve.fastapi_app import PredictionRequest
        
        # Valid request
        valid_data = {"features": {"load_lag_1h": 1200.0, "temp_c": 22.5}}
        request = PredictionRequest(**valid_data)
        assert request.features["load_lag_1h"] == 1200.0
        
        # Invalid request - empty features
        with pytest.raises(ValueError, match="Features dictionary cannot be empty"):
            PredictionRequest(features={})
        
        # Invalid request - non-numeric feature
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PredictionRequest(features={"load_lag_1h": "invalid"})

    def test_batch_prediction_request_validation(self) -> None:
        """Test BatchPredictionRequest validation."""
        from src.serve.fastapi_app import BatchPredictionRequest
        
        # Valid request
        valid_data = {
            "rows": [
                {"load_lag_1h": 1200.0, "temp_c": 22.5},
                {"load_lag_1h": 1300.0, "temp_c": 25.0}
            ]
        }
        request = BatchPredictionRequest(**valid_data)
        assert len(request.rows) == 2
        
        # Invalid request - empty rows
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BatchPredictionRequest(rows=[])
        
        # Invalid request - empty row
        with pytest.raises(ValueError, match="Row 0 cannot be empty"):
            BatchPredictionRequest(rows=[{}])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
