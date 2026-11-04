"""Data layer: manifest-locked loaders for the frozen Binance snapshot.

Determinism contract (M2.3):
- pure numpy float64 / int64; single-threaded; no randomness, no network
- mixed Binance Vision epoch precision (ms in legacy files, µs in newer
  files) normalized per row to ms before any window math
- manifest is the sole source of truth: every load first asserts
  sha256(manifest bytes) == snapshot_const.MANIFEST_SHA, then re-verifies
  each zip's raw bytes against its manifest row (double pin).
"""
from .loader import DataLockError, Channel, assert_manifest, load  # noqa: F401
from .snapshot_const import MANIFEST_SHA, MANIFEST_REL, DATA_ROOT  # noqa: F401
