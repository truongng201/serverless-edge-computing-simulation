import torch
import torch.nn as nn


class GRUDisplacement(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 1, dropout: float = 0.1):
        super().__init__()
        self.gru = nn.GRU(input_size=input_size, hidden_size=hidden_size, num_layers=num_layers,
                          batch_first=True, dropout=(dropout if num_layers > 1 else 0.0))
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 8),  # 4 horizons * 2 (dx, dy)
        )

    def forward(self, x):
        # x: [B, L, F]
        out, h_n = self.gru(x)
        # take last hidden state (already batch_first)
        last = out[:, -1, :]
        y = self.head(last)
        return y

