from typing import Dict, List, Tuple

import numpy as np
import torch


def compute_errors_m(
    pred: torch.Tensor,  # [B, 8] dx,dy x4
    target: torch.Tensor,  # [B, 8]
) -> Dict[str, float]:
    with torch.no_grad():
        p = pred.detach().cpu().numpy().reshape(-1, 4, 2)
        t = target.detach().cpu().numpy().reshape(-1, 4, 2)
        diff = p - t
        dist = np.linalg.norm(diff, axis=2)  # [B, 4]
        ade = float(np.mean(dist))
        fde = float(np.mean(dist[:, -1]))
        return {"ADE": ade, "FDE": fde}


def hit_at_r(
    pred: torch.Tensor,
    target: torch.Tensor,
    radius_m: float = 200.0,
    final_only: bool = True,
) -> float:
    with torch.no_grad():
        p = pred.detach().cpu().numpy().reshape(-1, 4, 2)
        t = target.detach().cpu().numpy().reshape(-1, 4, 2)
        diff = p - t
        dist = np.linalg.norm(diff, axis=2)
        if final_only:
            hits = (dist[:, -1] <= radius_m).astype(np.float32)
        else:
            hits = (dist <= radius_m).astype(np.float32).mean(axis=1)
        return float(hits.mean())

