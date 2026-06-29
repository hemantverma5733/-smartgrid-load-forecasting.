import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

class DataProcessor:
    def __init__(self, look_back=24):
        self.look_back = look_back
        self.scaler_x = MinMaxScaler()
        self.scaler_y = MinMaxScaler()
        self.feature_cols = [
            "temperature", "voltage", "current", "frequency",
            "hour", "dayofweek", "month",
            "lag_1", "lag_2", "lag_24",
            "rolling_mean_6", "rolling_std_6"
        ]

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates lag, rolling, and time-based features from raw smart meter reading dataframe.
        Expected columns: timestamp, power_consumption, temperature, voltage, current, frequency
        """
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp").reset_index(drop=True)

        # Time features
        df["hour"] = df["timestamp"].dt.hour
        df["dayofweek"] = df["timestamp"].dt.dayofweek
        df["month"] = df["timestamp"].dt.month

        # Lag features (grouped by meter to avoid leakage across meters)
        # Note: If single meter or pre-filtered, group by is safe
        df["lag_1"] = df.groupby("meter_id")["power_consumption"].shift(1)
        df["lag_2"] = df.groupby("meter_id")["power_consumption"].shift(2)
        df["lag_24"] = df.groupby("meter_id")["power_consumption"].shift(24)

        # Rolling features
        df["rolling_mean_6"] = df.groupby("meter_id")["power_consumption"].transform(
            lambda x: x.rolling(6, min_periods=1).mean()
        )
        df["rolling_std_6"] = df.groupby("meter_id")["power_consumption"].transform(
            lambda x: x.rolling(6, min_periods=1).std()
        )
        # Fill standard deviation NaN values for initial rows
        df["rolling_std_6"] = df["rolling_std_6"].fillna(0)

        # Drop any remaining NaN rows caused by shifting
        df = df.dropna().reset_index(drop=True)
        return df

    def fit_transform(self, df: pd.DataFrame):
        """
        Fits scalers on train features and returns scaled features & target.
        """
        X = df[self.feature_cols].values
        y = df["power_consumption"].values.reshape(-1, 1)

        X_scaled = self.scaler_x.fit_transform(X)
        y_scaled = self.scaler_y.fit_transform(y)
        return X_scaled, y_scaled

    def transform(self, df: pd.DataFrame):
        """
        Transforms features using pre-fitted scalers.
        """
        X = df[self.feature_cols].values
        X_scaled = self.scaler_x.transform(X)
        
        if "power_consumption" in df.columns:
            y = df["power_consumption"].values.reshape(-1, 1)
            y_scaled = self.scaler_y.transform(y)
            return X_scaled, y_scaled
        return X_scaled, None

    def inverse_transform_y(self, y_scaled: np.ndarray) -> np.ndarray:
        return self.scaler_y.inverse_transform(y_scaled)

    def create_dl_sequences(self, X_scaled: np.ndarray, y_scaled: np.ndarray):
        """
        Creates sequences for deep learning (LSTM/Transformer).
        Shape: (samples, look_back, num_features)
        """
        X_seq, y_seq = [], []
        for i in range(len(X_scaled) - self.look_back):
            X_seq.append(X_scaled[i : i + self.look_back])
            y_seq.append(y_scaled[i + self.look_back])
        return np.array(X_seq), np.array(y_seq)

    def save(self, filepath_dir: str):
        os.makedirs(filepath_dir, exist_ok=True)
        joblib.dump(self.scaler_x, os.path.join(filepath_dir, "scaler_x.pkl"))
        joblib.dump(self.scaler_y, os.path.join(filepath_dir, "scaler_y.pkl"))
        joblib.dump(self.feature_cols, os.path.join(filepath_dir, "feature_cols.pkl"))

    def load(self, filepath_dir: str):
        self.scaler_x = joblib.load(os.path.join(filepath_dir, "scaler_x.pkl"))
        self.scaler_y = joblib.load(os.path.join(filepath_dir, "scaler_y.pkl"))
        self.feature_cols = joblib.load(os.path.join(filepath_dir, "feature_cols.pkl"))
