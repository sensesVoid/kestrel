"""Realized-path labels (M4.6): c in {-1,0,+1} from the future return at
horizon h, with a zero-band of theta_bps (default 30 bps).

c = +1 if ret >  +theta
    -1 if ret <  -theta
     0 otherwise (zero-band -> REFUSE, the A-2 zero-band class)
"""
from __future__ import annotations

from typing import List

import numpy as np


ZERO_BAND_BPS = 30.0


def realized_labels(closes: np.ndarray, horizon: int,
                    theta_bps: float = ZERO_BAND_BPS) -> np.ndarray:
    """Per decision cell (index t): sign of (c[t+h]/c[t]-1), 0 in zero-band.

    Cells where t+h exceeds the array are NaN-labelled (caller drops them).
    Returns int8 array; -2 marks "no future" (drop)."""
    n = closes.shape[0]
    out = np.full(n, -2, dtype=np.int8)
    theta = theta_bps / 10000.0
    for t in range(n - horizon):
        ret = closes[t + horizon] / closes[t] - 1.0
        if ret > theta:
            out[t] = 1
        elif ret < -theta:
            out[t] = -1
        else:
            out[t] = 0
    return out


def label_counts(labels: np.ndarray) -> dict:
    vals, cnts = np.unique(labels, return_counts=True)
    return {int(v): int(c) for v, c in zip(vals, cnts)}
