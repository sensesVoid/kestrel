"""M3 tests (1/3): baseline contract, cost math, ATR16, exact accounting."""
from decimal import Decimal
from types import SimpleNamespace

import numpy as np
import pytest

from kestrel.backtest import (Costs, Governor, BacktestEngine, EngineError,
                              Reel)
from kestrel.backtest.engine import atr16
from tests.m3_fixtures import ch, set_bar, em

D = Decimal


def test_baseline_all_refuse_reconciles_zero():
    reel = BacktestEngine(ch(60)).run(10_000.0, emissions=None,
                                      t_start=20, t_end=40)
    assert reel.trades == []
    assert D(reel.equity_start) == D(reel.equity_final) == D("10000")
    assert reel.refusals == {"zero_band": 21}          # t = 20..40
    assert len(reel.decisions) == 21
    assert len(reel.equity_curve) == 21
    assert D(reel.recon_sum_vs_trades) == 0
    assert D(reel.recon_equity_vs_sum) == 0


def test_costs_and_atr_units():
    assert Costs().fee(D("1000")) == D("1")            # 0.10 %/side
    assert Costs(2.0).fee(D("1000")) == D("2")         # stress x2
    s = Costs().slip(D("94"), 103.0, 93.0, is_stop=True)
    assert s == D("5")                                 # max(2bps, (103-93)/2)
    assert Costs().slip(D("94"), 103.0, 93.0, is_stop=False) == D("0.0188")
    # ATR16 hand-built: bars 0..16 have true range i+1 (h-l, closes flat)
    n = 20
    c = ch(n, rng=1.0)
    for i in range(17):
        set_bar(c, i, 100.0, 100.0 + (i + 1) * 1.0, 100.0, 100.0)
    # window t-15..t = bars 1..16 -> TR = 2..17 -> mean 9.5 exact
    assert atr16(c.h, c.l, c.c, 16) == 9.5


def test_exact_flat_path_accounting():
    c = ch(60)   # TR = 2 every bar -> ATR(30) = 2, stop 94, target 106
    reel = BacktestEngine(c).run(10_000.0, em({30: (1, 1.0)}),
                                 t_start=17, t_end=40)
    assert len(reel.trades) == 1
    t0 = reel.trades[0]
    assert t0["entry_bar"] == 31 and t0["exit_bar"] == 34
    assert D(t0["entry_px"]) == D(t0["exit_px"]) == D("100.0")
    assert D(t0["notional"]) == D("200") and D(t0["qty"]) == D("2")
    assert D(t0["fee_entry"]) == D(t0["fee_exit"]) == D("0.2")
    assert D(t0["slippage"]) == 0 and D(t0["gross"]) == 0
    assert D(t0["net"]) == D("-0.4")
    assert D(t0["equity_after"]) == D("9999.6")
    assert reel.refusals == {"zero_band": 23}          # all cells but t=30
    assert D(reel.recon_sum_vs_trades) == 0
    assert D(reel.recon_equity_vs_sum) == 0


def test_stress_doubles_costs():
    reel = BacktestEngine(ch(60), stress=2.0).run(
        10_000.0, em({30: (1, 1.0)}), t_start=17, t_end=40)
    t0 = reel.trades[0]
    assert D(t0["fee_entry"]) == D(t0["fee_exit"]) == D("0.4")
    assert D(t0["net"]) == D("-0.8")
    assert D(t0["equity_after"]) == D("9999.2")
    assert reel.stress == 2.0
    assert D(reel.recon_equity_vs_sum) == 0


def test_reconciliation_raises_on_corrupt_ledger():
    eng = BacktestEngine(ch(60))
    eng._gov = Governor()
    with pytest.raises(EngineError):
        eng._finish(Reel(), D("9999"), D("10000"), D("1"))
