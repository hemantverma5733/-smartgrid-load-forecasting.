import torch
import torch.nn as nn
import numpy as np

# --- 1. Baseline Model ---
class BaselineModel:
    """
    Baseline model that predicts the load using the persistence method (last known value - lag_1).
    """
    def fit(self, X, y):
        pass

    def predict(self, X):
        # We assume lag_1 is at index 7 of the feature list:
        # feature_cols order:
        # 0: temperature, 1: voltage, 2: current, 3: frequency,
        # 4: hour, 5: dayofweek, 6: month,
        # 7: lag_1, 8: lag_2, 9: lag_24,
        # 10: rolling_mean_6, 11: rolling_std_6
        # So we predict index 7 (lag_1)
        return X[:, 7]


# --- 2. PyTorch LSTM Model ---
class LSTMModel(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=2, output_dim=1):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.1 if num_layers > 1 else 0.0
        )
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_dim)
        out, _ = self.lstm(x)
        # We only take the output of the last sequence step: out[:, -1, :]
        out = self.fc(out[:, -1, :])
        return out


# --- 3. PyTorch Transformer Model ---
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        if d_model % 2 == 1:
            pe[:, 1::2] = torch.cos(position * div_term[:-1])
        else:
            pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        # x shape: (batch, seq_len, d_model)
        x = x + self.pe[:, :x.size(1)]
        return x

class TransformerModel(nn.Module):
    def __init__(self, input_dim, d_model=32, nhead=4, num_layers=2, dim_feedforward=64, output_dim=1):
        super().__init__()
        self.input_projection = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=0.1,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, output_dim)

    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_dim)
        x = self.input_projection(x)
        x = self.pos_encoder(x)
        out = self.transformer_encoder(x)
        # Take the output of the last sequence step
        out = self.fc(out[:, -1, :])
        return out
