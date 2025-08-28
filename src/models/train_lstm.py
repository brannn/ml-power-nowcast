#!/usr/bin/env python3
"""
LSTM Model Training for Power Demand Forecasting.

Trains neural network models using PyTorch for time series power demand prediction
with GPU acceleration support and comprehensive experiment tracking.
"""

import argparse
from pathlib import Path
from typing import Dict, Tuple

import mlflow
import mlflow.pytorch
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset


class LSTMModel(nn.Module):
    """LSTM model for time series forecasting."""
    
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2, dropout: float = 0.2):
        """
        Initialize LSTM model.
        
        Args:
            input_size: Number of input features
            hidden_size: Hidden layer size
            num_layers: Number of LSTM layers
            dropout: Dropout rate
        """
        super(LSTMModel, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # Output layer
        self.fc = nn.Linear(hidden_size, 1)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        """Forward pass."""
        # LSTM forward pass
        lstm_out, _ = self.lstm(x)
        
        # Take the last output
        last_output = lstm_out[:, -1, :]
        
        # Apply dropout and final linear layer
        output = self.dropout(last_output)
        output = self.fc(output)
        
        return output


def load_features(features_path: str) -> Tuple[pd.DataFrame, str]:
    """
    Load feature dataset and identify target column.
    
    Args:
        features_path: Path to features parquet file
        
    Returns:
        Tuple of (features DataFrame, target column name)
    """
    print(f"Loading features from {features_path}")
    df = pd.read_parquet(features_path)
    
    # Find target column
    target_cols = [col for col in df.columns if 'target' in col]
    if not target_cols:
        raise ValueError("No target column found in features dataset")
    
    target_col = target_cols[0]
    print(f"Target column: {target_col}")
    print(f"Dataset shape: {df.shape}")
    
    return df, target_col


def create_sequences(
    X: np.ndarray, 
    y: np.ndarray, 
    sequence_length: int = 24
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create sequences for LSTM training.
    
    Args:
        X: Feature array
        y: Target array
        sequence_length: Length of input sequences
        
    Returns:
        Tuple of (X_sequences, y_sequences)
    """
    X_sequences = []
    y_sequences = []
    
    for i in range(len(X) - sequence_length):
        X_sequences.append(X[i:(i + sequence_length)])
        y_sequences.append(y[i + sequence_length])
    
    return np.array(X_sequences), np.array(y_sequences)


def prepare_data(
    df: pd.DataFrame,
    target_col: str,
    sequence_length: int = 24,
    test_size: float = 0.2,
    val_size: float = 0.1
) -> Tuple[DataLoader, DataLoader, DataLoader, StandardScaler]:
    """
    Prepare data for LSTM training.
    
    Args:
        df: Features DataFrame
        target_col: Name of target column
        sequence_length: Length of input sequences
        test_size: Fraction of data for test set
        val_size: Fraction of remaining data for validation set
        
    Returns:
        Tuple of (train_loader, val_loader, test_loader, scaler)
    """
    print("Preparing data for LSTM training...")
    
    # Separate features and target
    feature_cols = [col for col in df.columns if col not in ['timestamp', target_col]]
    X = df[feature_cols].values
    y = df[target_col].values
    
    # Remove NaN values
    mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
    X = X[mask]
    y = y[mask]
    
    print(f"Features: {len(feature_cols)}")
    print(f"Samples after removing NaN: {len(X)}")
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Create sequences
    X_seq, y_seq = create_sequences(X_scaled, y, sequence_length)
    print(f"Sequences created: {len(X_seq)} with length {sequence_length}")
    
    # Split data (time series: no shuffle)
    test_idx = int(len(X_seq) * (1 - test_size))
    val_idx = int(test_idx * (1 - val_size / (1 - test_size)))
    
    X_train, y_train = X_seq[:val_idx], y_seq[:val_idx]
    X_val, y_val = X_seq[val_idx:test_idx], y_seq[val_idx:test_idx]
    X_test, y_test = X_seq[test_idx:], y_seq[test_idx:]
    
    print(f"Train sequences: {len(X_train)}")
    print(f"Validation sequences: {len(X_val)}")
    print(f"Test sequences: {len(X_test)}")
    
    # Convert to PyTorch tensors and create data loaders
    def create_dataloader(X, y, batch_size=256, shuffle=False):
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y).unsqueeze(1)
        dataset = TensorDataset(X_tensor, y_tensor)
        return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
    
    train_loader = create_dataloader(X_train, y_train, shuffle=True)
    val_loader = create_dataloader(X_val, y_val)
    test_loader = create_dataloader(X_test, y_test)
    
    return train_loader, val_loader, test_loader, scaler


def train_lstm_model(
    train_loader: DataLoader,
    val_loader: DataLoader,
    input_size: int,
    hidden_size: int = 64,
    num_layers: int = 2,
    epochs: int = 100,
    learning_rate: float = 0.001,
    patience: int = 10
) -> LSTMModel:
    """
    Train LSTM model with early stopping.
    
    Args:
        train_loader: Training data loader
        val_loader: Validation data loader
        input_size: Number of input features
        hidden_size: Hidden layer size
        num_layers: Number of LSTM layers
        epochs: Maximum number of epochs
        learning_rate: Learning rate
        patience: Early stopping patience
        
    Returns:
        Trained LSTM model
    """
    print("Training LSTM model...")
    
    # Check for GPU availability
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Initialize model
    model = LSTMModel(input_size, hidden_size, num_layers).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # Training loop with early stopping
    best_val_loss = float('inf')
    patience_counter = 0
    train_losses = []
    val_losses = []
    
    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
        
        train_loss /= len(train_loader)
        val_loss /= len(val_loader)
        
        train_losses.append(train_loss)
        val_losses.append(val_loss)
        
        # Early stopping check
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save best model state
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
        
        if epoch % 10 == 0:
            print(f"Epoch {epoch}: Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")
        
        if patience_counter >= patience:
            print(f"Early stopping at epoch {epoch}")
            break
    
    # Load best model state
    model.load_state_dict(best_model_state)
    print(f"Training completed. Best validation loss: {best_val_loss:.6f}")
    
    return model


def evaluate_model(
    model: LSTMModel,
    test_loader: DataLoader
) -> Dict[str, float]:
    """
    Evaluate LSTM model performance.
    
    Args:
        model: Trained LSTM model
        test_loader: Test data loader
        
    Returns:
        Dictionary of evaluation metrics
    """
    print("Evaluating LSTM model...")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()
    
    predictions = []
    actuals = []
    
    with torch.no_grad():
        for batch_X, batch_y in test_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            outputs = model(batch_X)
            
            predictions.extend(outputs.cpu().numpy().flatten())
            actuals.extend(batch_y.cpu().numpy().flatten())
    
    predictions = np.array(predictions)
    actuals = np.array(actuals)
    
    # Calculate metrics
    mae = mean_absolute_error(actuals, predictions)
    rmse = np.sqrt(mean_squared_error(actuals, predictions))
    mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100
    
    # R² calculation
    ss_res = np.sum((actuals - predictions) ** 2)
    ss_tot = np.sum((actuals - np.mean(actuals)) ** 2)
    r2 = 1 - (ss_res / ss_tot)
    
    metrics = {
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "r2": r2,
        "mean_actual": float(np.mean(actuals)),
        "std_actual": float(np.std(actuals)),
        "mean_predicted": float(np.mean(predictions)),
        "std_predicted": float(np.std(predictions))
    }
    
    print(f"Test MAE: {mae:.2f}")
    print(f"Test RMSE: {rmse:.2f}")
    print(f"Test MAPE: {mape:.2f}%")
    print(f"Test R²: {r2:.4f}")
    
    return metrics


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(description="Train LSTM model for power demand forecasting")
    parser.add_argument("--features", default="data/features/features.parquet", help="Path to features")
    parser.add_argument("--horizon", type=int, default=1, help="Forecast horizon in hours")
    parser.add_argument("--sequence-length", type=int, default=24, help="Input sequence length")
    parser.add_argument("--hidden-size", type=int, default=64, help="LSTM hidden size")
    parser.add_argument("--num-layers", type=int, default=2, help="Number of LSTM layers")
    parser.add_argument("--epochs", type=int, default=100, help="Maximum number of epochs")
    parser.add_argument("--learning-rate", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test set size")
    parser.add_argument("--val-size", type=float, default=0.1, help="Validation set size")

    args = parser.parse_args()

    # Start MLflow run for tracking
    mlflow.set_experiment("power-nowcast")
    with mlflow.start_run(run_name=f"lstm_h{args.horizon}"):

        # Log parameters
        mlflow.log_params({
            "model_type": "lstm",
            "horizon": args.horizon,
            "sequence_length": args.sequence_length,
            "hidden_size": args.hidden_size,
            "num_layers": args.num_layers,
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "test_size": args.test_size,
            "val_size": args.val_size,
            "features_path": args.features
        })

        try:
            # Load and prepare data
            df, target_col = load_features(args.features)
            train_loader, val_loader, test_loader, scaler = prepare_data(
                df, target_col,
                sequence_length=args.sequence_length,
                test_size=args.test_size,
                val_size=args.val_size
            )

            # Get input size from first batch
            sample_batch = next(iter(train_loader))
            input_size = sample_batch[0].shape[2]  # [batch, sequence, features]

            # Train model
            model = train_lstm_model(
                train_loader, val_loader, input_size,
                hidden_size=args.hidden_size,
                num_layers=args.num_layers,
                epochs=args.epochs,
                learning_rate=args.learning_rate
            )

            # Evaluate model
            metrics = evaluate_model(model, test_loader)
            mlflow.log_metrics(metrics)

            # Log model
            mlflow.pytorch.log_model(
                model,
                "model",
                registered_model_name="power-nowcast-lstm"
            )

            print(f"Successfully trained LSTM model for {args.horizon}-hour horizon")

        except Exception as e:
            print(f"Error during model training: {e}")
            mlflow.log_param("error", str(e))
            raise


if __name__ == "__main__":
    main()
