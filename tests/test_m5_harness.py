"""M5 tests: walk-forward window boundaries, manifest reproducibility,
per-window runner sanity (no network I/O)."""
from __future__ import annotations

import hashlib

import numpy as np
import pytest

from kestrel.harness import (
    build_windows, TRAIN_DAYS, EMBARGO_DAYS, TEST_DAYS, N_WINDOWS,
    build_manifest, manifest_sha,
)
from kestrel.harness.runner import run_window


@pytest.fixture(scope="module")
def btc1h():
    from kestrel.data import load
    return load("BTCUSDT", "1h")


def test_window_count_and_span(btc1h):
    wins = build_windows(btc1h.open_time)
    assert len(wins) == N_WINDOWS == 34
    # first test window starts 2023-07
    import datetime as dt
    first = wins[0]
    d0 = dt.datetime.fromtimestamp(first.test_start_ms / 1000, dt.timezone.utc)
    assert d0.year == 2023 and d0.month == 7
    # last test window ends on/before 2026-04-30 (seal untouched)
    last = wins[-1]
    d1 = dt.datetime.fromtimestamp(last.test_end_ms / 1000, dt.timezone.utc)
    assert d1 <= dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc)


def test_windows_monotonic_embargo_and_sizes(btc1h):
    wins = build_windows(btc1h.open_time)
    for i, w in enumerate(wins):
        assert w.train_end_idx <= w.test_start_idx
        assert w.embargo_bars >= EMBARGO_DAYS * 24 - 2  # ~168 bars, allow boundary
        assert w.test_end_idx > w.test_start_idx
        train_bars = w.train_end_idx - w.train_start_idx
        test_bars = w.test_end_idx - w.test_start_idx
        assert train_bars >= TRAIN_DAYS * 24 - 48  # ~4320, slack for partial days
        assert test_bars >= TEST_DAYS * 24 - 48   # ~720
    # test windows strictly increasing starts (overlap allowed for short months)
    for a, b in zip(wins, wins[1:]):
        assert a.test_start_ms < b.test_start_ms


def test_manifest_reproducible(btc1h):
    wins = build_windows(btc1h.open_time)
    m1 = build_manifest([1, 2, 3], wins, pop_sha="abc", quantizer_sha="def",
                        threshold_table_sha="ghi")
    m2 = build_manifest([1, 2, 3], wins, pop_sha="abc", quantizer_sha="def",
                        threshold_table_sha="ghi")
    assert m1["manifest_sha256"] == m2["manifest_sha256"]
    assert m1["n_windows"] == 34
    assert m1["no_network_io"] is True
    assert "versions" in m1
    assert manifest_sha(m1) == m1["manifest_sha256"]


def test_run_one_window(btc1h):
    wins = build_windows(btc1h.open_time)
    res = run_window(btc1h, wins[0], seed=1, horizon=4)
    assert res["window_idx"] == 0
    assert res["n_decisions"] > 0
    assert res["recon_sum_vs_trades"] == "0"
    from decimal import Decimal
    assert Decimal(res["recon_equity_vs_sum"]) == 0
    assert 0.0 <= res["refuse_share"] <= 1.0
    assert res["n_kills"] >= 0
    # window equity finite
    assert res["window_equity_final"] > 0


def test_run_window_different_seeds_reproducible(btc1h):
    wins = build_windows(btc1h.open_time)
    r1 = run_window(btc1h, wins[0], seed=1, horizon=4)
    r2 = run_window(btc1h, wins[0], seed=2, horizon=4)
    # deterministic core: theta_z and trade count identical across seeds
    assert r1["theta_z"] == r2["theta_z"]
    assert r1["n_trades"] == r2["n_trades"]
    assert r1["expectancy_bps"] == r2["expectancy_bps"]
