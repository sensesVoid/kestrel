"""M3 tests (3/3): governor rules 3-6 (unit) + engine drawdown integration."""
from decimal import Decimal

import numpy as np

from kestrel.backtest import Governor, BacktestEngine
from kestrel.backtest.governor import MIN_VOL_HIST
from tests.m3_fixtures import ch, set_bar, em

D = Decimal


def test_governor_daily_kill_trip_and_next_day_expiry():
    g = Governor()
    g.mark_day("2023-11-15", D("10000"))
    g.on_exit("2023-11-15", D("-101"), D("9899"))
    assert [k["event"] for k in g.trips] == ["daily_kill_refuse_only"]
    hist = np.zeros(int(MIN_VOL_HIST) - 1)     # top-vol rule stays off
    assert g.entry_refusal("2023-11-15", 0.0, hist, False) == \
        "governor_daily_kill_refuse_only_rest_of_day"
    assert g.entry_refusal("2023-11-16", 0.0, hist, False) is None


def test_governor_drawdown_trip_rearm_topvol_blackout():
    g = Governor()
    g.mark_day("2023-11-15", D("10000"))
    g.track_equity(D("10000"))                    # peak = high-water mark
    g.on_exit("2023-11-15", D("0"), D("8999"))       # 10.01% below peak
    assert [k["event"] for k in g.trips] == ["drawdown_full_stop"]
    hist = np.concatenate([np.zeros(190), np.ones(10)])   # p95 = 0.05
    assert g.entry_refusal("2023-11-16", 0.10, hist, False) == \
        "governor_drawdown_full_stop_awaiting_rearm"
    g.rearm()                                         # manual re-arm only
    assert g.entry_refusal("2023-11-16", 0.10, hist, False) == \
        "governor_top_vol_percentile_regime"
    assert g.entry_refusal("2023-11-16", 0.04, hist, False) is None
    assert g.entry_refusal("2023-11-16", 0.0, hist, True) == \
        "governor_blackout_no_health_data"


def test_engine_kill_lifts_next_utc_day():
    c = ch(60)
    set_bar(c, 22, 40.0, 41.0, 39.0, 40.0)            # engineered -1.2% day
    reel = BacktestEngine(c).run(10_000.0,
                                 em({20: (1, 1.0), 23: (1, 1.0),
                                     24: (1, 1.0)}),
                                 t_start=17, t_end=30)
    acts = {d["t"]: (d["action"], d["cause"]) for d in reel.decisions}
    assert acts[23] == ("REFUSE", "governor_daily_kill_refuse_only_rest_of_day")
    assert acts[24] == ("OPEN_LONG", None)            # next UTC day lifts


def test_engine_drawdown_full_stop_after_repeat_losses():
    """One -~0.9%-of-equity trade per UTC day: never trips the 1% daily
    kill, but cumulative drawdown crosses 10% after 12 days -> rule-4"""
    n = 360
    c = ch(n)
    P = np.empty(n)
    lvl = 100.0
    for k in range(0, n, 24):
        for j in range(24):
            P[k + j] = lvl if j <= 19 else lvl * 0.55
        lvl *= 0.55
    c.o = P
    c.c = P.copy()
    c.h = P + 1.0
    c.l = P - 1.0
    dmap = {24 * k + 18: (1, 1.0) for k in range(15)}
    reel = BacktestEngine(c).run(10_000.0, em(dmap), t_start=17, t_end=None)
    assert D(reel.recon_sum_vs_trades) == 0
    assert D(reel.recon_equity_vs_sum) == 0
    assert len(reel.trades) == 12                     # trip at trade 12
    assert [k["event"] for k in reel.kills] == ["drawdown_full_stop"]
    assert reel.refusals["governor_drawdown_full_stop_awaiting_rearm"] == 3
    assert D(reel.equity_final) < D("9000")
    assert all(D(v) > D("-101") for v in reel.daily_realized.values())
