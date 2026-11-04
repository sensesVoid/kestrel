"""M3 tests (2/3): fill mechanics — stop touch, gap-through, EXIT_EARLY
chain map, blackout windows, horizon edge. A-3 tie re-derived per test."""
from decimal import Decimal

import numpy as np

from kestrel.backtest import BacktestEngine
from tests.m3_fixtures import ch, set_bar, em, EPOCH_MID, IVMS

D = Decimal


def test_stop_touch_midbar_fills_at_level_minus_floor():
    c = ch(60)                                   # ATR=2: stop 94, target 106
    set_bar(c, 22, 100.0, 103.0, 93.0, 100.0)    # low dips through stop
    reel = BacktestEngine(c).run(10_000.0, em({20: (1, 1.0)}),
                                 t_start=17, t_end=30)
    t0 = reel.trades[0]
    assert t0["exit_bar"] == 22
    # fill = stop 94 - max(2bps, half-range 5) = 89 exactly (no extra slip)
    assert D(t0["exit_px"]) == D("89.0")
    assert D(t0["slippage"]) == D("5.0")
    assert D(t0["gross"]) == D("2") * (D("89.0") - D("100.0"))
    assert D(t0["net"]) == D("-22") - D("0.2") - D("0.178") - D("5.0")
    assert D(t0["equity_after"]) == D("10000") + D(t0["net"])
    assert D(reel.recon_sum_vs_trades) == 0


def test_gap_through_stop_fills_at_open_and_trips_daily_kill():
    c = ch(60)
    set_bar(c, 22, 40.0, 41.0, 39.0, 40.0)       # opens through stop 94
    reel = BacktestEngine(c).run(10_000.0,
                                 em({20: (1, 1.0), 23: (1, 1.0)}),
                                 t_start=17, t_end=30)
    t0 = reel.trades[0]
    assert D(t0["exit_px"]) == D("40.0")         # gap fill AT the open
    assert D(t0["slippage"]) == 0                # no extra slippage
    assert D(t0["net"]) == D("2") * (D("40.0") - D("100")) - D("0.2") - D("0.08")
    # realized -120.28 <= -1% of the 10000 day-start -> rule-3 trip
    assert [k["event"] for k in reel.kills] == ["daily_kill_refuse_only"]
    assert reel.refusals["governor_daily_kill_refuse_only_rest_of_day"] == 1


def test_exit_early_next_cell_reentry_and_chain_map():
    c = ch(60)
    dmap = {20: (1, 1.0), 21: (1, 1.0), 22: (-1, 1.0), 23: (1, 1.0)}
    reel = BacktestEngine(c).run(10_000.0, em(dmap), t_start=17, t_end=30)
    acts = {d["t"]: (d["action"], d["cause"]) for d in reel.decisions}
    assert acts[21] == ("HOLD", None)                 # c=+1 while long
    assert acts[22] == ("EXIT_EARLY_MORROW", None)    # licensed exit
    assert acts[23] == ("OPEN_LONG", None)            # next cell reentry
    assert [t["exit_bar"] for t in reel.trades] == [23, 27]
    d23 = next(d for d in reel.decisions if d["t"] == 23)
    assert d23["open"]["entry_bar"] == 24


def test_z_below_theta_blocks_early_exit():
    c = ch(60)
    reel = BacktestEngine(c).run(10_000.0, em({20: (1, 1.0), 21: (-1, 0.1)}),
                                 t_start=17, t_end=26)
    acts = {d["t"]: (d["action"], d["cause"]) for d in reel.decisions}
    assert acts[21] == ("REFUSE", "z_below_theta")    # no early exit
    assert [t["exit_bar"] for t in reel.trades] == [24]   # horizon exit
    assert reel.refusals["z_below_theta"] == 1


def test_no_inventory_short_refusal():
    reel = BacktestEngine(ch(60)).run(
        10_000.0, em({18: (-1, 1.0), 19: (1, 1.0)}), t_start=17, t_end=24)
    acts = {d["t"]: (d["action"], d["cause"]) for d in reel.decisions}
    assert acts[18] == ("REFUSE", "no_inventory_short")
    assert acts[19] == ("OPEN_LONG", None)


def test_horizon_end_beyond_data_refused():
    reel = BacktestEngine(ch(60)).run(10_000.0, em({57: (1, 1.0)}),
                                      t_start=17, t_end=58)
    acts = {d["t"]: (d["action"], d["cause"]) for d in reel.decisions}
    assert acts[57] == ("REFUSE", "horizon_end_beyond_data")
    assert reel.trades == []


def test_blackout_on_gap_slot_and_zero_volume():
    ot = EPOCH_MID + np.arange(60) * IVMS
    ot[9:] = ot[9:] + IVMS                     # cadence hole before bar 9
    reel = BacktestEngine(ch(60, ot=ot)).run(10_000.0, em({17: (1, 1.0)}),
                                             t_start=17, t_end=26)
    acts = {d["t"]: (d["action"], d["cause"]) for d in reel.decisions}
    assert acts[17] == ("REFUSE", "governor_blackout_no_health_data")
    assert reel.trades == []
    c2 = ch(60)
    c2.v[10] = 0.0                             # zero-volume bar in window
    reel2 = BacktestEngine(c2).run(10_000.0, em({17: (1, 1.0)}),
                                   t_start=17, t_end=26)
    assert reel2.refusals["governor_blackout_no_health_data"] >= 1
