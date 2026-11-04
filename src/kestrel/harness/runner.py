"""Per-window runner (M5): train S1 on train slice, calibrate theta_z,
run the backtester on the test slice, collect A-bar-relevant metrics."""
from __future__ import annotations

from typing import Any, Dict

import numpy as np

from kestrel.s1 import train_s1, S1Core
from kestrel.backtest import BacktestEngine
from kestrel.stats.quantizer import quantize_window, W as W16


def run_window(channel, window, seed: int = 1, horizon: int = 4,
               theta_bps: float = 30.0, stress: float = 1.0) -> Dict[str, Any]:
    o = channel.o; h = channel.h; l = channel.l; c = channel.c; v = channel.v
    tr = slice(window.train_start_idx, window.train_end_idx)
    te = slice(window.test_start_idx, window.test_end_idx)

    # train
    core, theta_z, Xh, labels = train_s1(
        o[tr], h[tr], l[tr], c[tr], v[tr], c[tr].copy(),
        horizon=horizon, theta_bps=theta_bps, holdout_frac=0.15, seed=seed)

    # emit over test slice: build an emissions function keyed on GLOBAL t
    # but the backtester operates on the test slice arrays. Re-index: test
    # arrays are channel[test slice]; decision cell i in [W16-1, n_test-horizon).
    o_t = o[te]; h_t = h[te]; l_t = l[te]; c_t = c[te]; v_t = v[te]
    n_test = o_t.shape[0]

    def emissions(global_t_local):
        # global_t_local is an index into the test slice arrays
        t = global_t_local
        if t < W16 - 1 or t >= n_test - horizon:
            return (0, float("-inf"))
        feats, _flag, _stats = quantize_window(o_t, h_t, l_t, c_t, v_t, t)
        cls, z = core.emit([int(f) for f in feats], theta_z)
        return (cls, z)

    # channel-like object for the backtester (test slice)
    from types import SimpleNamespace
    ch_test = SimpleNamespace(o=o_t, h=h_t, l=l_t, c=c_t, v=v_t,
                              open_time=channel.open_time[te],
                              ivms=channel.ivms, pair=channel.pair,
                              interval=channel.interval, missing_slots=0)

    reel = BacktestEngine(ch_test, stress=stress).run(
        10000.0, emissions=emissions,
        t_start=W16, t_end=n_test - 2)

    # metrics
    trades = reel.trades
    net_bps = [float(t["net_bps"]) for t in trades] if trades else []
    expectancy = (sum(net_bps) / len(net_bps)) if net_bps else 0.0
    n_refuse = sum(reel.refusals.values())
    n_cells = len(reel.decisions)
    refuse_share = n_refuse / n_cells if n_cells else 0.0
    kills = reel.kills

    return {
        "window_idx": window.idx,
        "seed": seed,
        "theta_z": float(theta_z),
        "core_t": int(core.t),
        "n_trades": len(trades),
        "expectancy_bps": float(expectancy),
        "window_equity_final": float(reel.equity_final),
        "window_equity_start": float(reel.equity_start),
        "refuse_share": float(refuse_share),
        "refusals": dict(reel.refusals),
        "n_kills": len(kills),
        "kill_events": kills,
        "recon_sum_vs_trades": reel.recon_sum_vs_trades,
        "recon_equity_vs_sum": reel.recon_equity_vs_sum,
        "n_decisions": n_cells,
    }
