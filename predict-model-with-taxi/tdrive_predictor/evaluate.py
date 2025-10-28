import os
from typing import List

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from .dataset import SequenceHorizonDataset
from .model import GRUDisplacement
from .metrics import compute_errors_m, hit_at_r


def evaluate_gru(
    data_dir: str,
    ckpt_path: str = None,
    lookback: int = None,
    batch_size: int = 128,
    device: str = None,
) -> dict:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    meta = pd.read_json(os.path.join(data_dir, 'meta.json'), typ='series').to_dict()
    test_df = pd.read_pickle(os.path.join(data_dir, 'test.pkl'))
    feature_cols: List[str] = meta['feature_cols']
    if ckpt_path is None:
        ckpt_path = os.path.join(data_dir, 'gru_phase_a.pt')
    ckpt = torch.load(ckpt_path, map_location=device)
    if lookback is None:
        lookback = int(ckpt.get('lookback', 20))
    ds_test = SequenceHorizonDataset(test_df, feature_cols, lookback=lookback)
    dl_test = DataLoader(ds_test, batch_size=batch_size, shuffle=False, num_workers=0)
    model = GRUDisplacement(input_size=len(feature_cols))
    model.load_state_dict(ckpt['model_state'])
    model.to(device)
    model.eval()
    preds = []
    targets = []
    with torch.no_grad():
        for x_seq, y_target, base_pos in dl_test:
            y_pred = model(x_seq.to(device))
            preds.append(y_pred.cpu())
            targets.append(y_target)
    if not preds:
        return {"ADE": float('nan'), "FDE": float('nan'), "Hit@100": float('nan'), "Hit@200": float('nan'), "Hit@400": float('nan')}
    preds = torch.cat(preds, dim=0)
    targets = torch.cat(targets, dim=0)
    res = compute_errors_m(preds, targets)
    res['Hit@100'] = hit_at_r(preds, targets, radius_m=100.0, final_only=True)
    res['Hit@200'] = hit_at_r(preds, targets, radius_m=200.0, final_only=True)
    res['Hit@400'] = hit_at_r(preds, targets, radius_m=400.0, final_only=True)
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items()})
    return res

