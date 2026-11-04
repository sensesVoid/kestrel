"""Training (M4.2): conditional counter registration over the TRAIN stream,
study-episode protocol (one episode per arrived label, full recency window).

Registration runs on the frozen TRAIN population only; labels are realized-path
labels (M4.6, theta=30 bps zero-band). c=0 (zero-band) cells are NOT
registered (they are the REFUSE class, not a trade signal)."""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from kestrel.stats.quantizer import quantize_window, W as W16
from .core import S1Core
from .labels import realized_labels, ZERO_BAND_BPS


def train_test_split_indices(n: int, holdout_frac: float = 0.15) -> Tuple[List[int], List[int]]:
    """Split decision-cell indices into (train, held_out_tail) by position.

    held_out is the final `holdout_frac` of available cells (pop-style disjoint
    block; labels are causal by construction)."""
    idx = list(range(n))
    cut = int(n * (1.0 - holdout_frac))
    return idx[:cut], idx[cut:]


def train_s1(o, h, l, c, v, closes, horizon: int, theta_bps: float = ZERO_BAND_BPS,
             holdout_frac: float = 0.15, seed: int = 1) -> tuple:
    """Train an S1Core on the TRAIN slice; calibrate theta_z on held-out tail.

    Returns (core, theta_z, heldout_features, labels)."""
    labels = realized_labels(closes, horizon, theta_bps)
    n = closes.shape[0]
    # decision cells: t where t+h < n and t >= W16-1 (full window)
    cells = [t for t in range(W16 - 1, n - horizon)]
    if not cells:
        raise ValueError("no decision cells available")
    train_idx, hold_idx = train_test_split_indices(len(cells), holdout_frac)
    train_cells = [cells[i] for i in train_idx]
    hold_cells = [cells[i] for i in hold_idx]

    core = S1Core()
    for t in train_cells:
        lab = int(labels[t])
        if lab == -2:
            continue
        if lab == 0:
            continue  # refuse class, not registered
        feats, _flag, _stats = quantize_window(o, h, l, c, v, t)
        core.update([int(f) for f in feats], lab)

    # held-out features for calibration
    X_hold = []
    for t in hold_cells:
        if labels[t] == -2:
            continue
        feats, _flag, _stats = quantize_window(o, h, l, c, v, t)
        X_hold.append([int(f) for f in feats])

    from .calibration import calibrate_theta_z
    theta_z = calibrate_theta_z(core, X_hold, quantile=0.7)

    return core, theta_z, X_hold, labels
