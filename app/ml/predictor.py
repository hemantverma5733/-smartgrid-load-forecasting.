import os
import sys
import numpy as np
import pandas as pd
import torch
import joblib
import json
from datetime import datetime, timedelta

# Add project root directory to path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.ml.data_processor import DataProcessor
from app.ml.models import LSTMModel, TransformerModel

class Predictor:
    def __init__(self, artifacts_dir=None):
        if artifacts_dir is None:
            # Default artifacts folder
            artifacts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
            
        self.artifacts_dir = artifacts_dir
        self.metadata = None
        self.processor = None
        self.model = None
        self.best_model_name = None
        
        self._load_artifacts()

    def _load_artifacts(self):
        meta_path = os.path.join(self.artifacts_dir, "metadata.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Model metadata not found at {meta_path}. Please train the models first.")
            
        with open(meta_path, "r") as f:
            self.metadata = json.load(f)
            
        self.best_model_name = self.metadata["best_model_name"]
        self.look_back = self.metadata.get("look_back", 24)
        self.input_dim = self.metadata.get("input_dim", 12)
        
        # Load scaler
        self.processor = DataProcessor(look_back=self.look_back)
        self.processor.load(self.artifacts_dir)
        
        # Load Model
        if self.best_model_name in ["LSTM", "Transformer"]:
            if self.best_model_name == "LSTM":
                self.model = LSTMModel(input_dim=self.input_dim)
            else:
                self.model = TransformerModel(input_dim=self.input_dim)
                
            model_path = os.path.join(self.artifacts_dir, "model.pth")
            self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            self.model.eval()
        else:
            # Traditional Scikit-Learn or XGBoost models
            model_path = os.path.join(self.artifacts_dir, "model.pkl")
            self.model = joblib.load(model_path)

    def predict_horizon(self, last_readings_df: pd.DataFrame, horizon_hours: int = 24) -> list:
        """
        Takes the last N historical readings (must contain at least 25-30 readings to compute lag and rolling windows)
        for a single meter and predicts the load for the next `horizon_hours` hours autoregressively.
        Returns: list of dicts with {"target_timestamp": datetime, "predicted_load_kw": float}
        """
        # Ensure correct column formats and sort
        df = last_readings_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp").reset_index(drop=True)
        
        predictions = []
        last_time = df["timestamp"].iloc[-1]
        
        # We need to simulate future steps. We will loop step-by-step
        for step in range(1, horizon_hours + 1):
            # Create feature engineering rows on current dataframe
            df_feat = self.processor.create_features(df)
            if len(df_feat) == 0:
                raise ValueError("Insufficient historical data to generate features. Need at least 25 hourly steps.")
                
            # Take the very last row for prediction
            last_row = df_feat.iloc[[-1]]
            
            # Extract features & target scale
            X_scaled, _ = self.processor.transform(last_row)
            
            # Predict
            if self.best_model_name in ["LSTM", "Transformer"]:
                # Deep learning requires sequences.
                # Get the last `look_back` rows of scaled features
                # We need all inputs to be scaled first
                df_all_feat = self.processor.create_features(df)
                all_X_scaled, _ = self.processor.transform(all_all_feat := df_all_feat)
                
                # Check if we have enough sequences
                if len(all_X_scaled) < self.look_back:
                    # fallback to tabular model or simple prediction
                    pred_scaled_val = X_scaled[0, 7] # fallback: use lag_1
                else:
                    seq_x = all_X_scaled[-self.look_back:]
                    seq_x_tensor = torch.tensor(seq_x, dtype=torch.float32).unsqueeze(0) # add batch dim
                    with torch.no_grad():
                        pred_scaled_val = self.model(seq_x_tensor).numpy()[0, 0]
            else:
                # Tabular prediction
                pred_scaled_val = self.model.predict(X_scaled)[0]
            
            # Inverse scale predicted load
            pred_load_kw = self.processor.inverse_transform_y(np.array([[pred_scaled_val]]))[0, 0]
            pred_load_kw = max(0.1, float(pred_load_kw))  # force positive load
            
            # Record prediction
            target_time = last_time + timedelta(hours=step)
            predictions.append({
                "target_timestamp": target_time,
                "predicted_load_kw": round(pred_load_kw, 2)
            })
            
            # Append predicted row back to df to simulate next step
            # For the new row, we estimate temperature based on hour
            hour = target_time.hour
            temp_base = 25.0
            temp_cycle = 8.0 * np.sin((hour - 9) * 2 * np.pi / 24)
            estimated_temp = temp_base + temp_cycle
            
            # Voltage/current estimation
            estimated_voltage = 220.0
            estimated_current = (pred_load_kw * 1000.0) / (estimated_voltage * 0.9)
            
            new_row = pd.DataFrame([{
                "timestamp": target_time,
                "meter_id": df["meter_id"].iloc[0],
                "serial_number": df["serial_number"].iloc[0] if "serial_number" in df.columns else "MTR",
                "zone_id": df["zone_id"].iloc[0],
                "zone_name": df["zone_name"].iloc[0] if "zone_name" in df.columns else "Zone",
                "voltage": round(estimated_voltage, 2),
                "current": round(estimated_current, 2),
                "power_consumption": round(pred_load_kw, 2),
                "frequency": 50.00,
                "temperature": round(estimated_temp, 2)
            }])
            
            df = pd.concat([df, new_row], ignore_index=True)
            
        return predictions
