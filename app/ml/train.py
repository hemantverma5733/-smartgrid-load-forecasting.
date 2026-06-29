import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except Exception as e:
    XGBOOST_AVAILABLE = False
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import json

# Add project root directory to path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.ml.data_processor import DataProcessor
from app.ml.models import BaselineModel, LSTMModel, TransformerModel

# Set random seed
np.random.seed(42)
torch.manual_seed(42)

def calculate_mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    # Avoid division by zero
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def train_pytorch_model(model, X_train, y_train, epochs=8, batch_size=64, lr=0.001):
    model.train()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    # Convert to PyTorch tensors
    tensor_x = torch.tensor(X_train, dtype=torch.float32)
    tensor_y = torch.tensor(y_train, dtype=torch.float32)
    dataset = TensorDataset(tensor_x, tensor_y)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            pred = model(batch_x)
            loss = criterion(pred, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        
        # print(f"Epoch {epoch+1}/{epochs} Loss: {epoch_loss/len(loader):.5f}")
    return model

def evaluate_pytorch_model(model, X_test):
    model.eval()
    tensor_x = torch.tensor(X_test, dtype=torch.float32)
    with torch.no_grad():
        preds = model(tensor_x).numpy()
    return preds

def run_pipeline():
    global XGBOOST_AVAILABLE
    print("Loading data...")
    csv_path = "data/sample_meter_data.csv"
    if not os.path.exists(csv_path):
        print(f"Data file not found at {csv_path}. Please run generate_sample_data.py first.")
        sys.exit(1)
        
    df = pd.read_csv(csv_path)
    
    # We will build forecasting model for the total load (sum of all meters)
    # or per-meter. To make it a robust single general forecaster, we can train on all meters
    # together or select a representative meter. Let's train on all meters to learn a single generalized model.
    print("Engineering features...")
    processor = DataProcessor(look_back=24)
    df_feat = processor.create_features(df)
    
    # Split chronologically: 80% train, 20% test
    split_idx = int(len(df_feat) * 0.8)
    df_train = df_feat.iloc[:split_idx].copy()
    df_test = df_feat.iloc[split_idx:].copy()
    
    print(f"Train samples: {len(df_train)}, Test samples: {len(df_test)}")
    
    # Normalize features
    X_train_scaled, y_train_scaled = processor.fit_transform(df_train)
    X_test_scaled, y_test_scaled = processor.transform(df_test)
    
    # For Scikit-Learn / XGBoost models (tabular)
    # y target actual values
    y_test_actual = df_test["power_consumption"].values
    
    # 1. Baseline Model
    print("Training Baseline Model...")
    baseline = BaselineModel()
    baseline_preds_scaled = baseline.predict(X_test_scaled)
    baseline_preds = processor.inverse_transform_y(baseline_preds_scaled.reshape(-1, 1)).flatten()
    
    # 2. Linear Regression
    print("Training Linear Regression...")
    lr = LinearRegression()
    lr.fit(X_train_scaled, y_train_scaled.flatten())
    lr_preds_scaled = lr.predict(X_test_scaled)
    lr_preds = processor.inverse_transform_y(lr_preds_scaled.reshape(-1, 1)).flatten()
    
    # 3. Random Forest
    print("Training Random Forest...")
    rf = RandomForestRegressor(n_estimators=30, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train_scaled, y_train_scaled.flatten())
    rf_preds_scaled = rf.predict(X_test_scaled)
    rf_preds = processor.inverse_transform_y(rf_preds_scaled.reshape(-1, 1)).flatten()
    
    # 4. XGBoost
    xgb = None
    xgb_preds = None
    if XGBOOST_AVAILABLE:
        try:
            print("Training XGBoost...")
            xgb = XGBRegressor(n_estimators=30, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=-1)
            xgb.fit(X_train_scaled, y_train_scaled.flatten())
            xgb_preds_scaled = xgb.predict(X_test_scaled)
            xgb_preds = processor.inverse_transform_y(xgb_preds_scaled.reshape(-1, 1)).flatten()
        except Exception as e:
            print(f"Warning: Failed to train XGBoost ({e}).")
            XGBOOST_AVAILABLE = False
    
    # Prepare sequence data for Deep Learning models
    X_train_seq, y_train_seq = processor.create_dl_sequences(X_train_scaled, y_train_scaled)
    X_test_seq, y_test_seq = processor.create_dl_sequences(X_test_scaled, y_test_scaled)
    
    # The deep learning target corresponds to y_test_actual shifted by look_back
    y_test_dl_actual = df_test["power_consumption"].values[processor.look_back:]
    
    # 5. LSTM Model
    print("Training PyTorch LSTM...")
    input_dim = X_train_scaled.shape[1]
    lstm_net = LSTMModel(input_dim=input_dim)
    lstm_net = train_pytorch_model(lstm_net, X_train_seq, y_train_seq, epochs=10)
    lstm_preds_scaled = evaluate_pytorch_model(lstm_net, X_test_seq)
    lstm_preds = processor.inverse_transform_y(lstm_preds_scaled).flatten()
    
    # 6. Transformer Model
    print("Training PyTorch Transformer...")
    transformer_net = TransformerModel(input_dim=input_dim)
    transformer_net = train_pytorch_model(transformer_net, X_train_seq, y_train_seq, epochs=10)
    transformer_preds_scaled = evaluate_pytorch_model(transformer_net, X_test_seq)
    transformer_preds = processor.inverse_transform_y(transformer_preds_scaled).flatten()
    
    # Calculate performance metrics
    models_metrics = {}
    
    # Tabular Predictions
    preds_dict = {
        "Baseline": (y_test_actual, baseline_preds),
        "LinearRegression": (y_test_actual, lr_preds),
        "RandomForest": (y_test_actual, rf_preds),
        "LSTM": (y_test_dl_actual, lstm_preds),
        "Transformer": (y_test_dl_actual, transformer_preds)
    }
    if XGBOOST_AVAILABLE and xgb_preds is not None:
        preds_dict["XGBoost"] = (y_test_actual, xgb_preds)
    
    for name, (y_true, y_pred) in preds_dict.items():
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = calculate_mape(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        models_metrics[name] = {
            "MAE": float(mae),
            "RMSE": float(rmse),
            "MAPE": float(mape),
            "R2": float(r2)
        }

    # Print results comparison
    print("\n" + "="*50)
    print(f"{'Model Name':<20} | {'MAE':<8} | {'RMSE':<8} | {'MAPE (%)':<10} | {'R2 Score':<8}")
    print("="*50)
    for name, metrics in models_metrics.items():
        print(f"{name:<20} | {metrics['MAE']:<8.4f} | {metrics['RMSE']:<8.4f} | {metrics['MAPE']:<10.2f} | {metrics['R2']:<8.4f}")
    print("="*50)
    
    # Select best model based on minimum MAE (excluding Baseline)
    candidate_metrics = {k: v for k, v in models_metrics.items() if k != "Baseline"}
    best_model_name = min(candidate_metrics, key=lambda k: candidate_metrics[k]["MAE"])
    print(f"\nBest Performing Model selected: {best_model_name}")
    
    # Save the artifacts
    artifacts_dir = "app/ml/artifacts"
    processor.save(artifacts_dir)
    
    # Save best model
    if best_model_name == "LinearRegression":
        joblib.dump(lr, os.path.join(artifacts_dir, "model.pkl"))
    elif best_model_name == "RandomForest":
        joblib.dump(rf, os.path.join(artifacts_dir, "model.pkl"))
    elif best_model_name == "XGBoost":
        joblib.dump(xgb, os.path.join(artifacts_dir, "model.pkl"))
    elif best_model_name == "LSTM":
        torch.save(lstm_net.state_dict(), os.path.join(artifacts_dir, "model.pth"))
    elif best_model_name == "Transformer":
        torch.save(transformer_net.state_dict(), os.path.join(artifacts_dir, "model.pth"))
        
    # Save metadata
    metadata = {
        "best_model_name": best_model_name,
        "input_dim": input_dim,
        "look_back": processor.look_back,
        "metrics": models_metrics,
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(os.path.join(artifacts_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"Successfully saved all artifacts and model configuration metadata to {artifacts_dir}/")

if __name__ == "__main__":
    run_pipeline()
