"""L1 statistical layer: continuous per-bar features (M2.1).

Determinism contract (M2.3): pure numpy float64, single-threaded, ddof=0,
no RNG, no network. Warmup: long-horizon fields need 64 prior bars, twin-
window regime fields need 2*16 — the published union warmup is 64 leading
NaN per field (fields with shorter needs also carry NaN there, documented).

Feature horizons:
- S1 boundary (frozen, vendored adapter): returns {1,4,8,16}, pos16 at 0.85
  decile, range expansion, volume delta, gap — see stats/quantizer.py.
- Continuous stat dictionary (this module): ret1/ret4/ret16/ret64,
  pos_in_range(16), range_expansion(16 vs prev-16), volume_delta(16),
  vol16 (std of ret1 over 16, ddof=0), regime ratios rv (volume) /
  sigma (return std), cur-window / prev-window (16 each),
  gap_abs (|open vs prev close|, absolute price units).
"""
from __future__ import annotations

from typing import Dict

import numpy as np

FIELDS_WARMUP = 64
W16 = 16


def ret(c: np.ndarray, k: int) -> np.ndarray:
    """Simple return over k prior closes: c[t]/c[t-k] - 1 (NaN warmup < k)."""
    out = np.full(c.shape[0], np.nan, dtype=np.float64)
    out[k:] = c[k:] / c[:-k] - 1.0
    return out


def pos_in_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Close position in the trailing 16-bar [low, high] range; 0.5 on a
    zero range (degenerate window guard, mirrors vendor adapter)."""
    n = c.shape[0]
    out = np.full(n, np.nan, dtype=np.float64)
    for t in range(W16 - 1, n):
        s = slice(t - W16 + 1, t + 1)
        hh = h[s].max()
        ll = l[s].min()
        rng = hh - ll
        out[t] = (c[t] - ll) / rng if rng > 1e-12 else 0.5
    return out


def rolling_mean(x: np.ndarray, w: int = W16) -> np.ndarray:
    """Trailing-window mean (first w-1 = NaN)."""
    cs = np.cumsum(np.concatenate(([0.0], x)))
    out = np.full(x.shape[0], np.nan, dtype=np.float64)
    out[w - 1:] = (cs[w:] - cs[:-w]) / w
    return out


def rolling_std(r1: np.ndarray, w: int = W16) -> np.ndarray:
    """Trailing-window population std (ddof=0) of a series with NaN warmup
    ignored via zero-fill at leading NaNs (first w-1 outputs NaN)."""
    r1z = np.where(np.isnan(r1), 0.0, r1)
    cs = np.cumsum(r1z)
    cs2 = np.cumsum(r1z * r1z)
    out = np.full(r1.shape[0], np.nan, dtype=np.float64)
    if r1.shape[0] >= w:
        s = cs[w:] - cs[:-w]
        s2 = cs2[w:] - cs2[:-w]
        out[w:] = np.sqrt(np.maximum(s2 / w - (s / w) ** 2, 0.0))
    return out


def _shift(x: np.ndarray, k: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    out[k:] = x[:-k]
    return out


def volume_delta(v: np.ndarray) -> np.ndarray:
    """mean(volume, cur 16 bars) MINUS mean(volume, prev 16 bars);
    NaN before 2*16-1 (needs two full windows)."""
    cur = rolling_mean(v)
    prev = _shift(rolling_mean(v), W16)
    out = cur - prev
    out[: 2 * W16 - 2] = np.nan
    return out


def range_expansion(h: np.ndarray, l: np.ndarray) -> np.ndarray:
    """cur-16 range over prev-16 range (NaN before 2*16-1; 1.0 on
    degenerate prev range)."""
    n = h.shape[0]
    out = np.full(n, np.nan, dtype=np.float64)
    for t in range(2 * W16 - 1, n):
        cur_rng = h[t - W16 + 1: t + 1].max() - l[t - W16 + 1: t + 1].min()
        prv_rng = h[t - 2 * W16 + 1: t - W16 + 1].max() - l[t - 2 * W16 + 1: t - W16 + 1].min()
        out[t] = cur_rng / prv_rng if prv_rng > 1e-12 else 1.0
    return out


def gap_abs(o: np.ndarray, c: np.ndarray) -> np.ndarray:
    """|open(t) - close(t-1)| in price units; NaN at t=0."""
    out = np.abs(_shift(o, 1) - c)
    out[0] = np.nan
    return out


def features(o, h, l, c, v) -> Dict[str, np.ndarray]:
    """The continuous per-bar dictionary (M2.1). All float64, length n;
    leading warmup NaN as documented. Deterministic, no hidden state."""
    r1 = ret(c, 1)
    mean16v = rolling_mean(v)
    std16 = rolling_std(r1)
    out = {
        "ret1": r1,
        "ret4": ret(c, 4),
        "ret16": ret(c, 16),
        "ret64": ret(c, 64),
        "pos_in_range": pos_in_range(h, l, c),
        "range_expansion": range_expansion(h, l),
        "volume_delta": volume_delta(v),
        "vol16": std16,
        "regime_rv": mean16v / _shift(mean16v, W16),
        "regime_sigma": std16 / _shift(std16, W16),
        "gap_abs": gap_abs(o, c),
    }
    # regime ratios are NaN until two full windows align (t >= 2W-1)
    for k in ("regime_rv", "regime_sigma"):
        out[k][: 2 * W16 - 2] = np.nan
    out["volume_delta"][: 2 * W16 - 2] = np.nan
    out["range_expansion"][: 2 * W16 - 2] = np.nan
    return out
