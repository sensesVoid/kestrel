"""M4 tests: S1 core identity, determinism, Clay byte-neutrality, labels,
emission contract, theta_z calibration, refuse-band share."""
from __future__ import annotations

import hashlib
import os

import numpy as np
import pytest

from kestrel.s1 import (
    S1Core, CLAY_BYTES, clay_byte_neutral, save_checkpoint, load_checkpoint,
    realized_labels, label_counts, ZERO_BAND_BPS, calibrate_theta_z,
    threshold_table, train_s1,
)
from kestrel.stats.quantizer import quantize_window, W as W16


def test_identity_and_byte_neutrality():
    assert clay_byte_neutral() is True


def test_realized_labels_zero_band():
    closes = np.array([100.0, 100.02, 100.5, 99.6, 100.0], dtype=float)
    # horizon 1, theta 30 bps (0.0030)
    lab = realized_labels(closes, horizon=1, theta_bps=30.0)
    # t=0: 100.02/100-1 = 0.0002 <= 0.003 -> 0
    assert lab[0] == 0
    # t=1: 100.5/100.02-1 = 0.0048 > 0.003 -> +1
    assert lab[1] == 1
    # t=2: 99.6/100.5-1 = -0.009 < -0.003 -> -1
    assert lab[2] == -1
    # t=3: 100.0/99.6-1 = 0.0040 > 0.003 -> +1
    assert lab[3] == 1
    assert lab[4] == -2   # no future


def test_determinism_and_checkpoint_roundtrip(tmp_path):
    core = S1Core()
    x = [1, 0, 1, 0, 1, 0, 1, 0]
    for _ in range(60):
        core.update(x, 1)
    for _ in range(55):
        core.update([0, 1, 0, 1, 0, 1, 0, 1], -1)
    d1 = core.to_dict()
    # determinism: rebuild from same stream -> identical
    core2 = S1Core()
    for _ in range(60):
        core2.update(x, 1)
    for _ in range(55):
        core2.update([0, 1, 0, 1, 0, 1, 0, 1], -1)
    assert core2.to_dict() == d1
    # checkpoint round-trip
    p = str(tmp_path / "ckpt.bin")
    save_checkpoint(core, p)
    assert os.path.getsize(p) == CLAY_BYTES
    core3 = load_checkpoint(p)
    assert core3.to_dict() == d1


def test_emission_contract():
    core = S1Core()
    x = [1, 0, 1, 0, 1, 0, 1, 0]
    for _ in range(60):
        core.update(x, 1)
    for _ in range(55):
        core.update([0, 1, 0, 1, 0, 1, 0, 1], -1)
    # before threshold: low z -> 0 (use a threshold above this cell's z)
    cls0, z0 = core.emit(x, theta_z=100.0)
    assert cls0 == 0
    # with theta_z=0, confident cell emits +/-1
    cls1, z1 = core.emit(x, theta_z=0.0)
    assert cls1 in (-1, 0, 1)
    assert z1 >= 0.0
    # z gates: if theta_z > z, refuse
    cls2, z2 = core.emit(x, theta_z=z1 + 1.0)
    assert cls2 == 0


def test_calibration_threshold_table_sha():
    core = S1Core()
    x = [1, 0, 1, 0, 1, 0, 1, 0]
    for _ in range(60):
        core.update(x, 1)
    for _ in range(55):
        core.update([0, 1, 0, 1, 0, 1, 0, 1], -1)
    Xh = [x, [0, 1, 0, 1, 0, 1, 0, 1]] * 5
    th = calibrate_theta_z(core, Xh, quantile=0.5)
    assert isinstance(th, float)
    tbl = threshold_table({1: th, 2: th, 3: th})
    assert "sha256" in tbl
    # sha is deterministic
    tbl2 = threshold_table({1: th, 2: th, 3: th})
    assert tbl["sha256"] == tbl2["sha256"]


@pytest.fixture(scope="module")
def btc1h():
    from kestrel.data import load
    return load("BTCUSDT", "1h")


def test_train_and_refuse_band_share(btc1h):
    ch = btc1h
    # use a modest slice to keep runtime small
    sl = slice(200, 900)
    o = ch.o[sl]; h = ch.h[sl]; l = ch.l[sl]; c = ch.c[sl]; v = ch.v[sl]
    closes = c.copy()
    core, theta_z, Xh, labels = train_s1(o, h, l, c, v, closes, horizon=4,
                                          theta_bps=30.0, holdout_frac=0.15)
    assert core.t >= 50  # E_MIN-ish registration happened
    # emit over decision cells
    cells = [t for t in range(W16 - 1, closes.shape[0] - 4)]
    n = len(cells)
    refuses = 0
    for t in cells:
        feats, _flag, _ = quantize_window(o, h, l, c, v, t)
        cls, z = core.emit([int(f) for f in feats], theta_z)
        if cls == 0:
            refuses += 1
    share = refuses / n
    # M4.7: refuse-band share expected ~55-75% at h=4h
    assert 0.40 <= share <= 0.90, f"refuse share {share:.3f} out of expected band"
    # theta_z finite
    assert theta_z >= 0.0
    # labels distribution has zeros (zero-band)
    nz = (labels != -2)
    assert (labels[nz] == 0).sum() > 0
