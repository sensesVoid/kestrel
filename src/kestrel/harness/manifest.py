"""Run manifest (M5.4): reproducibility record — package versions, seeds,
population sha, quantizer sha, threshold table sha; no network I/O."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from typing import Any, Dict, List

import numpy as np


def _versions() -> Dict[str, str]:
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("numpy", "pandas", "torch", "torchhd", "scipy"):
        try:
            m = __import__(mod)
            out[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            out[mod] = "not-installed"
    return out


def build_manifest(seeds: List[int], windows: List, pop_sha: str,
                   quantizer_sha: str, threshold_table_sha: str,
                   extra: Dict[str, Any] = None) -> Dict[str, Any]:
    wlist = [{"idx": w.idx, "train": [w.train_start_idx, w.train_end_idx],
              "test": [w.test_start_idx, w.test_end_idx],
              "embargo_bars": w.embargo_bars} for w in windows]
    m = {
        "schema": "kestrel-run-manifest-v1",
        "no_network_io": True,
        "seeds": list(seeds),
        "n_windows": len(windows),
        "windows": wlist,
        "population_sha256": pop_sha,
        "quantizer_sha256": quantizer_sha,
        "threshold_table_sha256": threshold_table_sha,
        "versions": _versions(),
    }
    if extra:
        m["extra"] = extra
    # canonical sha
    canon = json.dumps(m, sort_keys=True, separators=(",", ":"))
    m["manifest_sha256"] = hashlib.sha256(canon.encode()).hexdigest()
    return m


def manifest_sha(manifest: Dict[str, Any]) -> str:
    m = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    canon = json.dumps(m, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()
