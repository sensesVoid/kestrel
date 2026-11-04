"""Hand-rolled event loop + exact accounting reel (M3.1, M3.3, M3.4, M3.6).

Deterministic, audit-first design (no vectorbt/quantlib). Timeline per bar:

  bar t (loaded channel arrays):
    [A] if a position is open, EXIT evaluation on bar t happens BEFORE the
        decision (a close-time decision always sees post-exit inventory)
    [B] decision cell at close of bar t: S1 emission (class, z) mapped
        through the §3.3 emission contract; entries fill at open(t+1)

Baked-in rules (spec §3.3/§3.4/§3.5):
- next-bar-open execution for ALL close-time decisions (causal law)
- stop = entry − 3×ATR(16 @ decision bar, causal, inclusive);
  target = entry + 2R
- mid-bar touch fills at LEVEL ± slippage floor (conservative/worse side);
  gap-through fills at that bar's OPEN (no extra slippage); same-bar stop
  AND target → adverse-first (stop wins)
- EXIT_EARLY decided at close t fills at open(t+1); horizon end fills at
  open(t+h). After an early exit NO re-entry until the next decision cell —
  the state machine yields exactly this (flat-by-open(t+1) ⇒ the close-t+1
  decision is the next chain); one decision chain per horizon is enforced
  by holding: c=+1 while long → HOLD; entries while open are impossible
- emission contract interpretation (documented): z ≥ θ_z gates
  state-changing actions — c=−1 while long with z < θ_z is REFUSE
  `z_below_theta` (no early exit); c=+1 while long is HOLD regardless
  (identical outcome; c=0 while long → REFUSE `zero_band`, published)
- no partial fills (documented omission)
- cells whose horizon would exceed loaded data: REFUSE
  `horizon_end_beyond_data` (honest edge, no synthetic exit)
- A-3 two-way reconciliation (Decimal, kernel-exact) runs at the end of
  EVERY run: (a) running ledger Σnet == Σ trade nets, (b) equity delta ==
  running Σnet. Any nonzero discrepancy raises.

Accounting: Decimal on the same float64 fills the engine decided with
(str-convert; quantity is Decimal arithmetic at 80-digit context precision,
used consistently on BOTH legs so the breakdown ties exactly). Bar
comparisons/fills stay float64 numpy. Blackout (rule 6): flagged bars
(bar AFTER a cadence hole) or zero-volume bars inside the decision window.

Equity is tracked as delta = sum of net PnL from a zero base (so the
accumulator never loses low-order digits against a large base); eq = eq0 +
delta. recon_b = delta - ledger_net, both accumulated from zero in the
same order, so it ties to 0 exactly.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
getcontext().prec = 80
from typing import Callable, Dict, List, Optional

import numpy as np

from .costs import Costs
from .governor import NOTIONAL_PCT, Governor

ATR_W = 16
HORIZON_DEFAULT = 4


class EngineError(RuntimeError):
    """Contract/structure violation or nonzero A-3 reconciliation."""


@dataclass
class Reel:
    pair: str = ""
    interval: str = ""
    stress: float = 1.0
    theta_z: float = 0.0
    horizon: int = HORIZON_DEFAULT
    trades: List[dict] = field(default_factory=list)
    decisions: List[dict] = field(default_factory=list)
    refusals: Dict[str, int] = field(default_factory=dict)
    kills: List[dict] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)
    daily_realized: Dict[str, str] = field(default_factory=dict)
    equity_start: str = "0"
    equity_final: str = "0"
    recon_sum_vs_trades: str = "0"
    recon_equity_vs_sum: str = "0"
    t_start: int = 0
    t_end: int = 0


def atr16(h: np.ndarray, l: np.ndarray, c: np.ndarray, t: int) -> float:
    """Causal 16-bar true-range mean ENDING at bar t (inclusive)."""
    assert t >= ATR_W, "ATR warmup not satisfied"
    tr = np.empty(ATR_W, dtype=np.float64)
    for k, i in enumerate(range(t - ATR_W + 1, t + 1)):
        pc = c[i - 1]
        tr[k] = max(h[i] - l[i], abs(h[i] - pc), abs(l[i] - pc))
    return float(tr.mean())


def _D(x) -> Decimal:
    return Decimal(str(x))


def _day(open_time_ms: int) -> str:
    return dt.datetime.fromtimestamp(open_time_ms / 1000.0,
                                     dt.timezone.utc).strftime("%Y-%m-%d")


class BacktestEngine:
    def __init__(self, ch, stress: float = 1.0) -> None:
        self.o = np.asarray(ch.o, dtype=np.float64)
        self.h = np.asarray(ch.h, dtype=np.float64)
        self.l = np.asarray(ch.l, dtype=np.float64)
        self.c = np.asarray(ch.c, dtype=np.float64)
        self.v = np.asarray(ch.v, dtype=np.float64)
        self.ot = np.asarray(ch.open_time, dtype=np.int64)
        self.n = int(self.c.shape[0])
        self.ivms = int(ch.ivms)
        self.pair = getattr(ch, "pair", "")
        self.interval = getattr(ch, "interval", "")
        d = np.diff(self.ot)
        self.gap_at = np.zeros(self.n, dtype=bool)
        self.gap_at[np.nonzero(d > self.ivms)[0] + 1] = True   # bar AFTER a hole
        self.zvol_at = self.v <= 0.0
        self.costs = Costs(stress)
        self.stress = float(stress)

    def vol16_series(self) -> np.ndarray:
        """Rolling 16-bar population std of ret1 (ddof=0); NaN warmup < 16."""
        r1 = np.full(self.n, np.nan, dtype=np.float64)
        r1[1:] = self.c[1:] / self.c[:-1] - 1.0
        r1z = np.where(np.isnan(r1), 0.0, r1)
        cs = np.cumsum(r1z)
        cs2 = np.cumsum(r1z * r1z)
        s = cs[ATR_W:] - cs[:-ATR_W]
        s2 = cs2[ATR_W:] - cs2[:-ATR_W]
        vol = np.full(self.n, np.nan, dtype=np.float64)
        vol[ATR_W:] = np.sqrt(np.maximum(s2 / ATR_W - (s / ATR_W) ** 2, 0.0))
        return vol

    def blackout_at(self, t: int, W: int = ATR_W) -> bool:
        s = slice(max(0, t - W + 1), t + 1)
        return bool(self.gap_at[s].any() or self.zvol_at[s].any())

    # ------------------------------------------------------------------- run
    def run(self, equity0: float,
            emissions: Optional[Callable[[int], tuple]] = None,
            theta_z: float = 0.30, horizon: int = HORIZON_DEFAULT,
            t_start: int = ATR_W + 1, t_end: Optional[int] = None) -> Reel:
        """Decision cells at close of bars [t_start .. t_end]; the last cell
        defaults to n-2 so its entry fills at bar n-1."""
        if t_end is None:
            t_end = self.n - 2
        reel = Reel(pair=self.pair, interval=self.interval,
                    stress=self.stress, theta_z=theta_z, horizon=horizon,
                    t_start=t_start, t_end=t_end)
        eq0 = _D(equity0)
        reel.equity_start = str(eq0)
        gov = Governor()
        gov.peak = eq0
        self._gov = gov
        vol = self.vol16_series()
        ledger_net = Decimal("0")
        delta = Decimal("0")
        eq = eq0  # current equity (eq0 + delta, maintained below)
        pos: Optional[dict] = None

        for t in range(t_start, t_end + 1):
            day_key = _day(int(self.ot[t]))
            gov.mark_day(day_key, eq)
            gov.track_equity(eq)
            reel.equity_curve.append({"bar": t, "equity": str(eq)})

            if pos is not None:
                pos, eq, ledger_net, delta = self._maybe_exit(
                    pos, t, reel, eq, gov, ledger_net, delta, eq0)

            cls, z = (0, float("-inf")) if emissions is None else emissions(t)
            act, cause = self._classify(cls, z, theta_z, t, pos, gov, vol, reel)
            reel.decisions.append({"t": t, "class": cls,
                                   "z": round(float(z), 6), "action": act,
                                   "cause": cause})
            if act == "OPEN_LONG":
                if t + 1 > self.n - 1 or t + horizon > self.n - 1 or t < ATR_W:
                    cause_ = ("horizon_end_beyond_data"
                              if (t + horizon > self.n - 1
                                  or t + 1 > self.n - 1) else "atr16_warmup")
                    self._bump(reel, cause_)
                    reel.decisions[-1]["action"] = "REFUSE"
                    reel.decisions[-1]["cause"] = cause_
                    continue
                pos = self._open_at_open(t, t + 1, eq, horizon, reel)
            elif act == "EXIT_EARLY_MORROW":
                if t + 1 > self.n - 1:
                    self._bump(reel, "horizon_end_beyond_data")
                    reel.decisions[-1]["action"] = "REFUSE"
                    reel.decisions[-1]["cause"] = "horizon_end_beyond_data"
                    continue
                pos["force_exit"] = t + 1

        # flush: a position that survived the last decision cell exits
        # deterministically on the remaining bars (its horizon end is
        # guaranteed in-bounds at open time)
        if pos is not None:
            for j in range(t_end + 1, self.n):
                day_key = _day(int(self.ot[j]))
                gov.mark_day(day_key, eq)
                gov.track_equity(eq)
                pos, eq, ledger_net, delta = self._maybe_exit(
                    pos, j, reel, eq, gov, ledger_net, delta, eq0)
                if pos is None:
                    break

        self._finish(reel, eq0, ledger_net, delta)
        return reel

    # -------------------------------------------------------- contract map
    def _classify(self, cls: int, z: float, theta_z: float, t: int, pos,
                  gov, vol: np.ndarray, reel: "Reel"):
        if pos is not None:
            if cls == 0:
                self._bump(reel, "zero_band")
                return "REFUSE", "zero_band"
            if cls == -1:
                if float(z) < theta_z:
                    self._bump(reel, "z_below_theta")
                    return "REFUSE", "z_below_theta"
                return "EXIT_EARLY_MORROW", None
            return "HOLD", None                          # c=+1, long
        if cls == 0:
            self._bump(reel, "zero_band")
            return "REFUSE", "zero_band"
        if float(z) < theta_z:
            self._bump(reel, "z_below_theta")
            return "REFUSE", "z_below_theta"
        if cls == -1:
            self._bump(reel, "no_inventory_short")
            return "REFUSE", "no_inventory_short"
        # cls == +1, flat: governor gates (rules 3-6; vol history ≤ t)
        vseg = vol[ATR_W: t + 1]
        cause = gov.entry_refusal(_day(int(self.ot[t])), float(vol[t]),
                                      vseg[~np.isnan(vseg)],
                                      self.blackout_at(t))
        if cause is not None:
            self._bump(reel, cause)
            return "REFUSE", cause
        return "OPEN_LONG", None

    @staticmethod
    def _bump(reel: "Reel", cause: str) -> None:
        reel.refusals[cause] = reel.refusals.get(cause, 0) + 1

    def _open_at_open(self, decision_t: int, entry_idx: int, eq: Decimal,
                      horizon: int, reel: "Reel") -> dict:
        entry = float(self.o[entry_idx])
        notional = _D(NOTIONAL_PCT) * eq
        qty = notional / _D(entry)
        fee_e = self.costs.fee(notional)
        atr = atr16(self.h, self.l, self.c, decision_t)
        stop = entry - 3.0 * atr
        target = entry + 2.0 * (3.0 * atr)
        reel.decisions[-1]["open"] = {
            "decision_bar": decision_t, "entry_bar": entry_idx,
            "entry": entry, "notional": str(notional), "qty": str(qty),
            "stop": stop, "target": target, "atr16": atr,
            "horizon_end_bar": decision_t + horizon}
        return {"entry_idx": entry_idx, "decision_idx": decision_t,
                "entry_px": entry, "qty_d": qty, "fee_entry_d": fee_e,
                "stop": stop, "target": target, "horizon": horizon,
                "force_exit": None}

    def _maybe_exit(self, pos, t: int, reel: "Reel", eq: Decimal, gov,
                    ledger_net: Decimal, delta: Decimal, eq0: Decimal):
        """Deterministic exit evaluation on bar t. Returns (pos_or_None,
        eq, ledger_net, delta)."""
        stop, target = pos["stop"], pos["target"]
        o_j = float(self.o[t])
        h_j = float(self.h[t])
        l_j = float(self.l[t])
        fe = pos["force_exit"]
        fill: Optional[float] = None
        slip_cost = Decimal("0")
        if fe is not None and t == fe:
            fill = o_j
        elif o_j <= stop:                     # gap-through stop
            fill = o_j
        elif o_j >= target:                   # gap-through target
            fill = o_j
        elif l_j <= stop:                     # touch stop mid-bar
            slip = self.costs.slip(_D(stop), h_j, l_j, is_stop=True)
            fill = stop - float(slip)
            slip_cost = slip
        elif h_j >= target:                   # touch target mid-bar
            slip = self.costs.slip(_D(target), h_j, l_j, is_stop=False)
            fill = target - float(slip)
            slip_cost = slip
        elif t == pos["decision_idx"] + pos["horizon"]:
            fill = o_j
        if fill is None:
            return pos, eq, ledger_net, delta
        self._settle(pos, _D(fill), slip_cost, eq, gov, t, reel)
        net = _D(reel.trades[-1]["net"])
        delta = delta + net
        ledger_net = ledger_net + net
        eq = eq0 + delta
        return None, eq, ledger_net, delta

    def _settle(self, pos, exit_px: Decimal, slip_cost: Decimal,
                eq: Decimal, gov, exit_bar: int, reel: "Reel") -> Decimal:
        qty = pos["qty_d"]
        entry_px = _D(pos["entry_px"])
        notional = qty * entry_px
        out_notional = qty * exit_px
        fee_e = pos["fee_entry_d"]
        fee_x = self.costs.fee(out_notional)
        gross = out_notional - notional
        net = gross - fee_e - fee_x - slip_cost
        eq2 = eq + net
        reel.trades.append({
            "entry_bar": pos["entry_idx"], "decision_bar": pos["decision_idx"],
            "exit_bar": exit_bar, "entry_px": str(entry_px),
            "exit_px": str(exit_px), "qty": str(qty),
            "notional": str(notional), "fee_entry": str(fee_e),
            "fee_exit": str(fee_x), "slippage": str(slip_cost),
            "gross": str(gross), "net": str(net),
            "net_bps": str((net / notional).scaleb(4)),
            "equity_after": str(eq2),
        })
        day_key = _day(int(self.ot[exit_bar]))
        gov.mark_day(day_key, eq2)
        gov.on_exit(day_key, net, eq2)
        return eq2

    def _finish(self, reel: "Reel", eq0: Decimal, ledger_net: Decimal,
                delta: Decimal) -> None:
        reel.kills = list(self._gov.trips)
        for k in sorted(self._gov._day_pnl):
            reel.daily_realized[k] = str(self._gov._day_pnl[k])
        reel.equity_final = str(eq0 + ledger_net)
        trades_net = sum((_D(x["net"]) for x in reel.trades), Decimal("0"))
        recon_a = ledger_net - trades_net
        recon_b = delta - ledger_net
        reel.recon_sum_vs_trades = str(recon_a.normalize())
        reel.recon_equity_vs_sum = str(recon_b.normalize())
        if recon_a != 0 or recon_b != 0:
            raise EngineError(f"A-3 reconciliation nonzero: {recon_a}/{recon_b}")
