"""theta_z calibration (M4.5): per-seed threshold on a held-out tail slice
inside the train fold (final 15%). Threshold table + sha for the manifest.
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List

import numpy as np

from .core import S1Core


def calibrate_theta_z(core: S1Core, X_holdout: List[List[int]],
                      quantile: float = 0.5) -> float:
    """Calibrate theta_z on held-out features.

    Collects z over confident predictions on the held-out slice; theta_z is
    the `quantile` quantile of those z values. Cells with z >= theta_z pass.
    If no confident predictions, fall back to 0.0 (everything refuses)."""
    zs = []
    for x in X_holdout:
        cls, z = core.predict(x)
        if cls is not None:
            zs.append(z)
    if not zs:
        return 0.0
    return float(np.quantile(np.asarray(zs, dtype=np.float64), quantile))


def threshold_table(thetas: Dict[int, float]) -> Dict:
    """Build a JSON-serializable threshold table + its sha."""
    table = {"seeds": {str(k): float(v) for k, v in thetas.items()}}
    table["sha256"] = hashlib.sha256(
        json.dumps(table["seeds"], sort_keys=True).encode()).hexdigest()
    return table
