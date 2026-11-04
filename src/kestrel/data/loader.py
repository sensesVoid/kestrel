"""Manifest-locked loader for the frozen Binance kline snapshot (M1.2/M1.5).

Guarantees:
- assert_manifest(): refuses unless sha256(manifest bytes) equals the pinned
  constant; returns the parsed manifest rows.
- load(): per (pair, interval) channel — verifies each zip row's sha (double
  pin), normalizes mixed ms/µs epochs, decodes CSV in-memory, and returns an
  immutable-ish Channel of numpy arrays with published internal stats:
  duplicates/non-monotonic are FATAL (loader refuses), missing-cadence slots
  are PUBLISHED (authentic archive holes; loader never interpolates).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import os
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from pathlib import Path

from .snapshot_const import DATA_ROOT, MANIFEST_REL, MANIFEST_SHA

ROOT = str(Path(__file__).resolve().parents[3])   # repo root
DATA_DIR = os.path.join(ROOT, DATA_ROOT)


class DataLockError(RuntimeError):
    """Raised when any pin (manifest sha, per-file sha, structural gate)
    fails. Runners must refuse, never adapt."""


@dataclass(frozen=True)
class MANIFEST_ROW_FORMAT_MODE:
    pass  # placeholder for docs; rows are (sha256, size, relpath)


@dataclass
class Channel:
    pair: str
    interval: str
    ivms: int
    open_time: np.ndarray        # int64 ms epoch, strictly increasing
    o: np.ndarray                # float64
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    v: np.ndarray
    missing_slots: int
    gap_sample: List[Tuple[int, int]]     # (missing_from_open_ms, delta_ms)
    files: int
    manifest_sha: str
    source_relpaths: List[str] = field(default_factory=list)

    def __len__(self) -> int:
        return int(self.open_time.shape[0])


def _norm_ms(ts: int) -> int:
    """Binance Vision mixes ms epochs (legacy files) and µs epochs (newer
    files). Normalize to ms: while the value is too large to be ms, /1000."""
    ts = int(ts)
    while ts > 10_000_000_000_000:
        ts //= 1000
    return ts


def assert_manifest(manifest_path: Optional[str] = None) -> List[Tuple[str, int, str]]:
    """Compute sha256 over the manifest bytes, compare to the pinned const,
    and parse rows. Raises DataLockError on mismatch/malformation."""
    mp = manifest_path or os.path.join(ROOT, MANIFEST_REL)
    with open(mp, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != MANIFEST_SHA:
        raise DataLockError(
            f"manifest sha mismatch: file={sha[:16]}… pinned={MANIFEST_SHA[:16]}… "
            f"({mp}) — stale code or frozen snapshot drifted (M1.5)"
        )
    rows: List[Tuple[str, int, str]] = []
    for line in raw.decode("utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("  ")
        if len(parts) != 3:
            raise DataLockError(f"manifest row malformed: {line!r}")
        sha_r, size_r, rel = parts
        rows.append((sha_r, int(size_r), rel))
    return rows


def _decode_csv(raw_csv: bytes, interval: str) -> Tuple[np.ndarray, np.ndarray,
                np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, List[Tuple[int, int]]]:
    cad = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}[interval]
    ots, ohlc, vs = [], [], []
    n_missing, gaps = 0, []
    rd = csv.reader(io.StringIO(raw_csv.decode("utf-8")))
    for row in rd:
        if not row or len(row) < 7:
            continue
        ots.append(_norm_ms(row[0]))
        ohlc.append((float(row[1]), float(row[2]), float(row[3]), float(row[4])))
        vs.append(float(row[5]) if row[5] else 0.0)
    ot = np.asarray(ots, dtype=np.int64)
    O = np.empty((len(ohlc), 4), dtype=np.float64)
    for i, q in enumerate(ohlc):
        O[i] = q
    V = np.asarray(vs, dtype=np.float64)
    # structural gates inside the loader (cheap; publishes, never interpolates)
    if ot.shape[0] > 1:
        d = np.diff(ot)
        n_missing = int((d != cad).sum())
        if n_missing:
            idx = np.nonzero(d != cad)[0]
            gaps = [(int(ot[i]), int(d[i])) for i in idx[:100]]
    if not (np.diff(ot) > 0).all():
        raise DataLockError("non-monotonic open_time (loader refuses)")
    _ = ot, O, V
    return ot, O[:, 0].copy(), O[:, 1].copy(), O[:, 2].copy(), O[:, 3].copy(), V, n_missing, gaps


def _load_channel(pair: str, interval: str, rows,) -> Channel:
    ivms = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}[interval]
    otL, oL, hL, lL, cL, vL = [], [], [], [], [], []
    missing_total, files = 0, 0
    gaps: List[Tuple[int, int]] = []
    srcs: List[str] = []
    for sha, size, rel in rows:
        if not rel.startswith(f"{pair}/{interval}/"):
            continue
        ap = os.path.join(DATA_DIR, rel)
        raw = open(ap, "rb").read()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise DataLockError(f"rpm sha mismatch for {rel} (double pin failed)")
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            csvn = sorted(n for n in z.namelist() if n.endswith(".csv"))[0]
            ot, o, h, l, c, v, nm, g = _decode_csv(z.read(csvn), interval)
            missing_total += nm
            if g:
                gaps.extend(g)
            otL.append(ot); oL.append(o); hL.append(h); lL.append(l); cL.append(c); vL.append(v)
            files += 1
            srcs.append(rel)
    ot = np.concatenate(otL)
    if ot.shape[0] > 1 and not (np.diff(ot) > 0).all():
        raise DataLockError(f"cross-file non-monotonic open_time for {pair} {interval}")
    ch = Channel(
        pair=pair, interval=interval, ivms=ivms,
        open_time=ot,
        o=np.concatenate(oL), h=np.concatenate(hL), l=np.concatenate(lL), c=np.concatenate(cL),
        v=np.concatenate(vL),
        missing_slots=missing_total, gap_sample=gaps[:64], files=files,
        manifest_sha=MANIFEST_SHA, source_relpaths=srcs)
    if ch.c.min() <= 0:
        raise DataLockError(f"non-positive close in {pair} {interval} (division guard)")
    return ch


def load(pair: Optional[str] = None, interval: Optional[str] = None,
         manifest_path: Optional[str] = None) -> "Channel | dict[str, Channel]":
    """Load one channel or the full 6-channel matrix. Every access asserts
    the manifest sha first, then re-verifies file bytes (double pin)."""
    rows = assert_manifest(manifest_path)
    rows = sorted(rows, key=lambda r: r[2])
    if pair and interval:
        return _load_channel(pair, interval, rows)
    out = {}
    for p in ("BTCUSDT", "ETHUSDT"):
        for i in ("1h", "4h", "1d"):
            out[f"{p}/{i}"] = _load_channel(p, i, rows)
    return out
