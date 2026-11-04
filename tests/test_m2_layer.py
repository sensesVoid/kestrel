"""M2 unit tests: quantizer lock, manifest lock, A-1 no-lookahead (+ its
mandatory mutation flip), feature semantics + determinism.

Determinism: real-data fixtures from the frozen snapshot; synthetic windows
use sha-driven deterministic draws (no RNG state).
"""
import hashlib
import io
import shutil
import zipfile
import os

import numpy as np
import pytest

from kestrel.data import (
    Channel, DataLockError, assert_manifest, load,
    MANIFEST_SHA, MANIFEST_REL,
)
from kestrel.stats import (
    QUANTIZER, RULES, QUANTIZER_SHA, RULE_TABLE_SHA,
    FLAG, N_BITS, W, THRESHOLDS, AdapterAudit, quantize_window, quantize_many,
    features, ret, FIELDS_WARMUP,
)


@pytest.fixture(scope="module")
def btc1h():
    return load("BTCUSDT", "1h")


@pytest.fixture()
def manifest_tamper(tmp_path):
    src = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), MANIFEST_REL)   # repo root / manifest
    dst = tmp_path / "snapshot.sha256"
    b = open(src, "rb").read()
    # flip one hex char inside the first row
    txt = b.decode()
    i = txt.find("\n")
    head = txt[:i]
    first = head.replace(head[0], "0" if head[0] != "0" else "1")
    dst.write_text(first + txt[i:], encoding="utf-8", newline="")
    return str(dst)


# ---------------------------------------------------------------- M2.2 lock
def test_quantizer_constants_frozen():
    assert len(QUANTIZER) == 8
    assert QUANTIZER == ("ret1:0", "ret4:0", "ret8:0", "ret16:0", "pos16:0.85",
                         "rexp:1.0", "vdel:0", "gap:0")
    assert len(RULES) == 4
    # self-asserted at import: parsed == recomputed == vendored-frozen
    assert QUANTIZER_SHA == hashlib.sha256(
        __import__("json").dumps(QUANTIZER).encode()).hexdigest()
    assert RULE_TABLE_SHA == hashlib.sha256(
        __import__("json").dumps(RULES).encode()).hexdigest()
    assert W == 16 and N_BITS == 16
    assert FLAG["rv"] == (0.85, 1.09) and FLAG["rg"] == 5.0
    assert THRESHOLDS["pos16"] == 0.85 and THRESHOLDS["rexp"] == 1.0


def test_vendor_pin_file_promises_match():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pins = __import__("json").load(open(
        os.path.join(root, "specs", "vendor_pins.json"), encoding="utf-8"))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tr1 = next(p for p in pins["pins"] if p["vendored"] == "src/vendor/tr1_replay.py")
    raw = open(os.path.join(root, "src", "vendor", "tr1_replay.py"), "rb").read()
    assert hashlib.sha256(raw).hexdigest() == tr1["sha256"]


# ---------------------------------------------------------------- M1.5 lock
def test_manifest_assert(btc1h):
    rows = assert_manifest()
    assert len(rows) == 666
    assert btc1h.manifest_sha == MANIFEST_SHA == MANIFEST_SHA
    assert len(btc1h) == 80581
    assert (np.diff(btc1h.open_time) > 0).all()
    assert btc1h.files == 111


def test_manifest_refuse_on_tamper(manifest_tamper):
    with pytest.raises(DataLockError):
        assert_manifest(manifest_tamper)


def test_loader_refuses_bytes_drift(tmp_path):
    rows = assert_manifest()
    rel = next(r[2] for r in rows if r[2].startswith("BTCUSDT/1h/"))
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "bench_data", "binance_klines")
    zp = os.path.join(root, rel)
    corrupt = tmp_path / "corrupt.zip"
    b = bytearray(open(zp, "rb").read())
    mid = len(b) // 2
    b[mid] ^= 0x01
    corrupt.write_bytes(bytes(b))
    # monkeypatch loader DATA_DIR to the corrupt copy with same relative name
    from unittest import mock
    import kestrel.data.loader as loader
    fake_root = tmp_path / "bench_data" / "binance_klines"
    (fake_root / os.path.dirname(rel)).mkdir(parents=True)
    shutil.copy(str(corrupt), str(fake_root / rel))
    with mock.patch.object(loader, "DATA_DIR", str(fake_root)):
        with mock.patch.object(loader, "assert_manifest", lambda *a, **k: rows):
            with pytest.raises(Exception):
                loader._load_channel("BTCUSDT", "1h", rows)


# ------------------------------------------------- M2.4 / A-1 no-lookahead
def test_adapter_reads_never_past_t(btc1h):
    o, h, l, c, v = btc1h.o, btc1h.h, btc1h.l, btc1h.c, btc1h.v
    audit = AdapterAudit()
    ts = list(range(200, 1400, 7))
    for t in ts:
        quantize_window(o, h, l, c, v, t, audit)
        assert audit.max_read <= t
    assert audit.violations == 0


def test_mutation_b_future_reads_fire_audit(btc1h):
    """HL-5: mutation (b) MUST make the audit fire. Vendor semantics: the
    future mutation shifts the window by exactly one bar (off=1) — the
    adapter reads t+1 (beyond t) and the audit records it. The mutation
    changes behavior (0 → 1 violation), which is the flip requirement."""
    o, h, l, c, v = btc1h.o, btc1h.h, btc1h.l, btc1h.c, btc1h.v
    t = 80_000   # n=80,581 → future reads reach t+1 only (off=1 shift)
    audit = AdapterAudit()
    quantize_window(o, h, l, c, v, t, audit, future=True)
    assert audit.violations == 1
    assert audit.max_read == t + 1
    clean = AdapterAudit()
    quantize_window(o, h, l, c, v, t, clean, future=False)
    assert clean.violations == 0 and clean.max_read == t


# ------------------------------------------------------ vendor semantics
def test_adapter_matches_naive_reference_on_real_window(btc1h):
    """Independent naive python re-derivation (from the spec/vendor text)
    must equal the numpy adapter on a real window."""
    o, h, l, c, v = btc1h.o, btc1h.h, btc1h.l, btc1h.c, btc1h.v
    t = 40_000
    W16 = W
    cur = list(range(t - W16 + 1, t + 1))
    prev = list(range(t - 2 * W16 + 1, t + 1 - W16))
    allc = list(c[prev]) + list(c[cur])
    cl = allc[W16:]
    rets = [cl[-1] / allc[-1 - k] - 1.0 for k in (1, 4, 8, 16)]
    rng = max(h[cur]) - min(l[cur])
    pos = (c[t] - min(l[cur])) / rng if rng > 1e-12 else 0.5
    prng = max(h[prev]) - min(l[prev])
    rexp = rng / prng if prng > 1e-12 else 1.0
    vdel = (sum(v[cur]) / W16) - (sum(v[prev]) / W16)
    gap = o[t] - c[t - 1]
    feats_ref = [1 if r >= 0.0 else -1 for r in rets] + \
                [1 if pos >= 0.85 else -1, 1 if rexp >= 1.0 else -1,
                 1 if vdel >= 0.0 else -1, 1 if gap >= 0.0 else -1]
    ra0 = sum(abs(cl[i] / cl[i - 1] - 1.0) for i in range(1, W16)) / (W16 - 1)
    rv = sum(v[cur]) / sum(v[prev])
    rg = abs(gap) / (cl[-1] * 0.002)
    # vendor semantics: flag = (rv outside band) OR (rg >= 5.0)
    flag_ref = (not (0.85 <= rv <= 1.09)) or (rg >= 5.0)
    feats, flag, _ = quantize_window(o, h, l, c, v, t)
    assert feats == feats_ref
    assert flag == bool(flag_ref)


def test_quantize_many_deterministic(btc1h):
    o, h, l, c, v = btc1h.o, btc1h.h, btc1h.l, btc1h.c, btc1h.v
    ts = list(range(100, 1500, 11))
    f1, g1 = quantize_many(o, h, l, c, v, ts)
    f2, g2 = quantize_many(o, h, l, c, v, ts)
    assert np.array_equal(f1, f2) and np.array_equal(g1, g2)
    assert set(np.unique(f1)).issubset({-1, 1})
    # feature mix sanity: both signs occur over the sweep
    assert (f1 == 1).any() and (f1 == -1).any()


# ------------------------------------------------------------- M2.1 fields
def test_features_semantics(btc1h):
    o, h, l, c, v = btc1h.o, btc1h.h, btc1h.l, btc1h.c, btc1h.v
    t = 50_000
    fs = features(o, h, l, c, v)
    n = len(c)
    assert all(np.asarray(fs[k]).shape == (n,) for k in fs)
    assert np.allclose(fs["ret1"][t], c[t] / c[t - 1] - 1.0, atol=0, rtol=0)
    assert np.allclose(fs["ret16"][t], c[t] / c[t - 16] - 1.0, atol=0, rtol=0)
    assert np.isnan(fs["ret64"][63]) and not np.isnan(fs["ret64"][64])
    lo16 = l[t - 15: t + 1].min(); hi16 = h[t - 15: t + 1].max()
    assert abs(fs["pos_in_range"][t] - (c[t] - lo16) / (hi16 - lo16)) < 1e-15
    # warmup contract per field (documented in features.py header)
    assert np.isnan(fs["ret1"][0]) and not np.isnan(fs["ret1"][1])
    assert np.isnan(fs["ret4"][3]) and not np.isnan(fs["ret4"][4])
    assert np.isnan(fs["ret16"][15]) and not np.isnan(fs["ret16"][16])
    assert np.isnan(fs["ret64"][63]) and not np.isnan(fs["ret64"][64])
    assert np.isnan(fs["pos_in_range"][14]) and not np.isnan(fs["pos_in_range"][15])
    assert np.isnan(fs["vol16"][15]) and not np.isnan(fs["vol16"][16])
    for k in ("volume_delta", "range_expansion", "regime_rv"):
        assert np.isnan(fs[k][30]) and not np.isnan(fs[k][31]), k
    # regime_sigma stacks: std16 valid from t=16, then /shift16 → from t=32
    assert np.isnan(fs["regime_sigma"][31]) and not np.isnan(fs["regime_sigma"][32])
    assert np.isnan(fs["gap_abs"][0])


def test_features_deterministic_bit_for_bit(btc1h):
    o, h, l, c, v = btc1h.o, btc1h.h, btc1h.l, btc1h.c, btc1h.v
    f1 = features(o, h, l, c, v)
    f2 = features(o, h, l, c, v)
    for k in f1:
        assert np.array_equal(f1[k], f2[k], equal_nan=True)
