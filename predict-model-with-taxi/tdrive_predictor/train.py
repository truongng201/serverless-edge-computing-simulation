import os
from typing import List

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .dataset import SequenceHorizonDataset
from .model import GRUDisplacement
from .metrics import compute_errors_m, hit_at_r


def train_gru(
    data_dir: str,
    lookback: int = 20,
    batch_size: int = 64,
    hidden_size: int = 128,
    num_layers: int = 1,
    dropout: float = 0.1,
    lr: float = 1e-3,
    epochs: int = 10,
    device: str = None,
) -> str:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    # load
    train_df = pd.read_pickle(os.path.join(data_dir, 'train.pkl'))
    val_df = pd.read_pickle(os.path.join(data_dir, 'val.pkl'))
    # features list saved in meta
    meta = pd.read_json(os.path.join(data_dir, 'meta.json'), typ='series').to_dict()
    feature_cols: List[str] = meta['feature_cols']
    # build datasets
    ds_train = SequenceHorizonDataset(train_df, feature_cols, lookback=lookback)
    ds_val = SequenceHorizonDataset(val_df, feature_cols, lookback=lookback)
    dl_train = DataLoader(ds_train, batch_size=batch_size, shuffle=True, num_workers=0)
    dl_val = DataLoader(ds_val, batch_size=batch_size, shuffle=False, num_workers=0)
    # model
    model = GRUDisplacement(input_size=len(feature_cols), hidden_size=hidden_size, num_layers=num_layers, dropout=dropout).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    # weighted SmoothL1 per horizon
    horizon_weights = torch.tensor([1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0, 1.0], dtype=torch.float32, device=device)
    loss_fn = nn.SmoothL1Loss(reduction='none')
    best_val = float('inf')
    ckpt_path = os.path.join(data_dir, 'gru_phase_a.pt')
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        n_batches = 0
        for x_seq, y_target, base_pos in dl_train:
            # skip batches with NaNs in inputs/targets
            if not torch.isfinite(x_seq).all() or not torch.isfinite(y_target).all():
                continue
            x_seq = x_seq.to(device)
            y_target = y_target.to(device)
            opt.zero_grad()
            y_pred = model(x_seq)
            loss_elem = loss_fn(y_pred, y_target) * horizon_weights  # [B, 8]
            loss = loss_elem.mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            opt.step()
            total_loss += loss.item()
            n_batches += 1
        avg_loss = total_loss / max(1, n_batches)
        # validation
        model.eval()
        with torch.no_grad():
            val_losses = []
            for x_seq, y_target, base_pos in dl_val:
                if not torch.isfinite(x_seq).all() or not torch.isfinite(y_target).all():
                    continue
                x_seq = x_seq.to(device)
                y_target = y_target.to(device)
                y_pred = model(x_seq)
                loss_elem = loss_fn(y_pred, y_target) * horizon_weights
                val_losses.append(loss_elem.mean().item())
            val_loss = float(np.mean(val_losses)) if val_losses else float('inf')
        if val_loss < best_val:
            best_val = val_loss
            torch.save({'model_state': model.state_dict(), 'meta': meta, 'feature_cols': feature_cols, 'lookback': lookback}, ckpt_path)
        print(f"[Epoch {epoch}/{epochs}] train_loss={avg_loss:.4f} val_loss={val_loss:.4f} best_val={best_val:.4f}")
    # Always save final weights to ensure ckpt exists
    if not os.path.exists(ckpt_path):
        torch.save({'model_state': model.state_dict(), 'meta': meta, 'feature_cols': feature_cols, 'lookback': lookback}, ckpt_path)
    return ckpt_path
