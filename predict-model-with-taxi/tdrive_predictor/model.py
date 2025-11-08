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


class GRUDisplacementRoad(nn.Module):
    """Predict curvilinear Δs for horizons [1,3,5,10]."""

    def __init__(self, input_size: int, hidden_size: int = 256, num_layers: int = 1, dropout: float = 0.1):
        super().__init__()
        self.gru = nn.GRU(input_size=input_size, hidden_size=hidden_size, num_layers=num_layers,
                          batch_first=True, dropout=(dropout if num_layers > 1 else 0.0))
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 4),  # 4 horizons (Δs)
        )

    def forward(self, x):
        out, _ = self.gru(x)
        last = out[:, -1, :]
        y = self.head(last)
        return y


class GRUStepDecoderRoad(nn.Module):
    """Encoder-decoder for stepwise Δs (10 steps of 1')."""

    def __init__(self, input_size: int, hidden_size: int = 256, num_layers: int = 1, dropout: float = 0.1, max_steps: int = 10):
        super().__init__()
        self.max_steps = int(max_steps)
        self.encoder = nn.GRU(input_size=input_size, hidden_size=hidden_size, num_layers=num_layers,
                               batch_first=True, dropout=(dropout if num_layers > 1 else 0.0))
        self.dec_cell = nn.GRUCell(input_size=1, hidden_size=hidden_size)
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x, teacher: torch.Tensor = None, ss_prob: float = 0.0):
        # x: [B,L,F]; teacher: [B,S] with S=max_steps
        B = x.size(0)
        device = x.device
        enc_out, _ = self.encoder(x)
        h = enc_out[:, -1, :]  # [B,H]
        prev = torch.zeros(B, 1, device=device, dtype=x.dtype)
        preds = []
        # scheduled sampling mask per step
        use_pred = None
        for s in range(self.max_steps):
            if (self.training and teacher is not None and ss_prob > 0.0):
                if use_pred is None or use_pred.size(0) != B:
                    use_pred = (torch.rand(B, 1, device=device) < ss_prob).float()
                inp = use_pred * prev + (1.0 - use_pred) * teacher[:, s:s+1]
            elif (self.training and teacher is not None and ss_prob <= 0.0):
                inp = teacher[:, s:s+1]
            else:
                inp = prev
            h = self.dec_cell(inp, h)
            out = self.head(h)
            preds.append(out)
            prev = out.detach()  # feed model output on next step by default
        y = torch.cat(preds, dim=1)  # [B,S]
        return y
