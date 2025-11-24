import os
from typing import List

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .dataset import SequenceHorizonDataset, SequenceHorizonCurvDataset, SequenceStepCurvDataset
from .model import GRUDisplacement, GRUDisplacementRoad, GRUStepDecoderRoad
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
    num_workers: int = 0,
    progress: bool = True,
    target_scale: float = 100.0,
    mode: str = "xy",  # 'xy' or 'curv' or 'curv_step'
    early_stop_patience: int = 0,
    early_stop_min_delta: float = 0.0,
) -> str:
    # resolve device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    elif device == "cuda" and not torch.cuda.is_available():
        print("[Train] CUDA requested but not available; falling back to CPU", flush=True)
        device = "cpu"
    if device == "cuda":
        try:
            torch.backends.cudnn.benchmark = True
        except Exception:
            pass
    # load
    train_df = pd.read_pickle(os.path.join(data_dir, 'train.pkl'))
    val_df = pd.read_pickle(os.path.join(data_dir, 'val.pkl'))
    # features list saved in meta
    meta = pd.read_json(os.path.join(data_dir, 'meta.json'), typ='series').to_dict()
    feature_cols: List[str] = meta['feature_cols']
    # Experiment toggles for curv_step mode (controlled via environment variables)
    # - TDRIVE_CURVSTEP_WEIGHTED_LOSS=1 -> use non-uniform step weights
    # - TDRIVE_CURVSTEP_HIGH_SS=1       -> increase scheduled sampling cap to 0.8
    def _env_flag(name: str) -> bool:
        v = os.environ.get(name, "").strip().lower()
        return v in ("1", "true", "yes", "y")

    use_weighted_curv_step_loss = _env_flag("TDRIVE_CURVSTEP_WEIGHTED_LOSS")
    use_high_ss_prob = _env_flag("TDRIVE_CURVSTEP_HIGH_SS")
    # build datasets
    if mode == 'curv':
        ds_train = SequenceHorizonCurvDataset(train_df, feature_cols, lookback=lookback)
        ds_val = SequenceHorizonCurvDataset(val_df, feature_cols, lookback=lookback)
    elif mode == 'curv_step':
        ds_train = SequenceStepCurvDataset(train_df, feature_cols, lookback=lookback, max_steps=10)
        ds_val = SequenceStepCurvDataset(val_df, feature_cols, lookback=lookback, max_steps=10)
    else:
        ds_train = SequenceHorizonDataset(train_df, feature_cols, lookback=lookback)
        ds_val = SequenceHorizonDataset(val_df, feature_cols, lookback=lookback)
    pin = (device == "cuda")
    dl_train = DataLoader(ds_train, batch_size=batch_size, shuffle=True, num_workers=int(num_workers), pin_memory=pin)
    dl_val = DataLoader(ds_val, batch_size=batch_size, shuffle=False, num_workers=int(num_workers), pin_memory=pin)
    try:
        ntr, nva = len(dl_train), len(dl_val)
    except Exception:
        ntr, nva = None, None
    print(f"[Train] Device={device} | train_batches={ntr} | val_batches={nva}", flush=True)
    # model
    if mode == 'curv':
        model = GRUDisplacementRoad(input_size=len(feature_cols), hidden_size=max(hidden_size, 256), num_layers=num_layers, dropout=dropout).to(device)
    elif mode == 'curv_step':
        model = GRUStepDecoderRoad(input_size=len(feature_cols), hidden_size=max(hidden_size, 256), num_layers=num_layers, dropout=dropout, max_steps=10).to(device)
    else:
        model = GRUDisplacement(input_size=len(feature_cols), hidden_size=hidden_size, num_layers=num_layers, dropout=dropout).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    # Older torch versions may not accept 'verbose' kwarg
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode='min', factor=0.5, patience=2)
    # weighted SmoothL1 per horizon / step
    if mode == 'curv':
        horizon_weights = torch.tensor([1.0, 0.5, 0.5, 1.0], dtype=torch.float32, device=device)
    elif mode == 'curv_step':
        if use_weighted_curv_step_loss:
            horizon_weights = torch.tensor(
                [1.0, 1.0, 1.0, 1.0, 0.8, 0.8, 0.8, 0.8, 0.7, 0.7],
                dtype=torch.float32,
                device=device,
            )
        else:
            horizon_weights = torch.ones(10, dtype=torch.float32, device=device)
    else:
        horizon_weights = torch.tensor([1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0, 1.0], dtype=torch.float32, device=device)
    loss_fn = nn.SmoothL1Loss(reduction='none')
    best_val = float('inf')
    ckpt_name = 'gru_phase_curv.pt' if mode == 'curv' else ('gru_phase_curv_step.pt' if mode == 'curv_step' else 'gru_phase_a.pt')
    ckpt_path = os.path.join(data_dir, ckpt_name)
    no_improve = 0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        n_batches = 0
        # training loop with optional tqdm progress
        try:
            from tqdm import tqdm  # type: ignore
            _train_iter = tqdm(dl_train, total=len(dl_train), disable=(not progress), desc=f"[Train] {epoch}/{epochs}", leave=False)
        except Exception:
            _train_iter = dl_train
        for x_seq, y_target, base_pos in _train_iter:
            # skip batches with NaNs in inputs/targets
            if not torch.isfinite(x_seq).all() or not torch.isfinite(y_target).all():
                continue
            x_seq = x_seq.to(device, non_blocking=pin)
            y_target = y_target.to(device, non_blocking=pin)
            opt.zero_grad()
            if mode == 'curv_step':
                max_ss = 0.8 if use_high_ss_prob else 0.5
                ss_p = min(max_ss, 0.1 * epoch)
                y_pred = model(x_seq, teacher=y_target, ss_prob=ss_p)
            else:
                y_pred = model(x_seq)
            # target scaling speeds convergence
            if target_scale and target_scale != 1.0:
                loss_elem = loss_fn(y_pred * target_scale, y_target * target_scale) * horizon_weights
            else:
                loss_elem = loss_fn(y_pred, y_target) * horizon_weights
            # simple scheduled sampling surrogate for 'curv':
            # mix teacher vs self outputs in target path with prob increasing 0->0.5 in 5 epochs
            if mode == 'curv':
                with torch.no_grad():
                    p = min(0.5, 0.1 * epoch)  # 0.1 per epoch up to 0.5
                    mixed = (1.0 - p) * y_target + p * y_pred.detach()
                ss_loss = loss_fn(y_pred, mixed) * horizon_weights
                # blend small weight into main loss
                loss_elem = 0.8 * loss_elem + 0.2 * ss_loss
            loss = loss_elem.mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            opt.step()
            total_loss += loss.item()
            n_batches += 1
            if hasattr(_train_iter, 'set_postfix'):
                try:
                    _train_iter.set_postfix(loss=f"{loss.item():.3f}")
                except Exception:
                    pass
        avg_loss = total_loss / max(1, n_batches)
        # validation
        model.eval()
        with torch.no_grad():
            val_losses = []
            try:
                from tqdm import tqdm  # type: ignore
                _val_iter = tqdm(dl_val, total=len(dl_val), disable=(not progress), desc=f"[Val]   {epoch}/{epochs}", leave=False)
            except Exception:
                _val_iter = dl_val
            for x_seq, y_target, base_pos in _val_iter:
                if not torch.isfinite(x_seq).all() or not torch.isfinite(y_target).all():
                    continue
                x_seq = x_seq.to(device, non_blocking=pin)
                y_target = y_target.to(device, non_blocking=pin)
                if mode == 'curv_step':
                    y_pred = model(x_seq, teacher=None, ss_prob=1.0)
                else:
                    y_pred = model(x_seq)
                if target_scale and target_scale != 1.0:
                    loss_elem = loss_fn(y_pred * target_scale, y_target * target_scale) * horizon_weights
                else:
                    loss_elem = loss_fn(y_pred, y_target) * horizon_weights
                val_losses.append(loss_elem.mean().item())
            val_loss = float(np.mean(val_losses)) if val_losses else float('inf')
        scheduler.step(val_loss)
        cur_lr = opt.param_groups[0]['lr']
        if val_loss < (best_val - float(early_stop_min_delta)):
            best_val = val_loss
            torch.save({'model_state': model.state_dict(), 'meta': meta, 'feature_cols': feature_cols, 'lookback': lookback, 'mode': mode, 'hidden_size': hidden_size}, ckpt_path)
            no_improve = 0
        else:
            no_improve += 1
        print(f"[Epoch {epoch}/{epochs}] train_loss={avg_loss:.4f} val_loss={val_loss:.4f} best_val={best_val:.4f} lr={cur_lr:.2e}")
        if early_stop_patience and no_improve >= int(early_stop_patience):
            print(f"Early stopping at epoch {epoch} (patience={early_stop_patience})")
            break
    # Always save final weights to ensure ckpt exists
    if not os.path.exists(ckpt_path):
        torch.save({'model_state': model.state_dict(), 'meta': meta, 'feature_cols': feature_cols, 'lookback': lookback, 'mode': mode, 'hidden_size': hidden_size}, ckpt_path)
    return ckpt_path
