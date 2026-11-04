"""L3 risk governor (spec §3.4, M3.5): hard-coded, non-negotiable, always-on.

Rules (v1):
1. per-trade notional at entry = 2.0% of equity, fixed (no vol scaling)
2. max concurrent positions: 1  (engine enforces; governor audits)
3. max daily realized loss ≤ 1.0% equity → kill-switch: REFUSE-ONLY for the
   rest of that UTC day (cause recorded in the ledger)
4. max drawdown ≤ 10% from equity peak → FULL STOP, manual re-arming only
   (sticky; refuses until an explicit rearm())
5. vol-regime filter: refuse new entries when vol16(t) >= the 95th
   percentile of the causal vol16 history (expanding window, no lookahead)
6. event blackout: windows carrying a missing cadence slot (snapshot gap) or
   a zero-volume bar inside the decision window are structurally REFUSE

Trip events are recorded with causes (A-4). All equity math is Decimal
(kernel-exact, A-3). Turning any rule off requires a new pre-registration.
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np

DAY_LOSS_CAP = 0.01          # 1.0% of equity (rule 3)
DRAWDOWN_CAP = 0.10          # 10% from equity peak (rule 4)
NOTIONAL_PCT = 0.02          # 2.0% at entry (rule 1)
MAX_POSITIONS = 1            # rule 2
TOP_VOL_PCTILE = 95.0        # rule 5 threshold percentile (causal, expanding)
MIN_VOL_HIST = 200           # minimum causal history before rule 5 applies


class Governor:
    """Driver-facing state; the engine calls register/mark day + refusals."""

    def __init__(self) -> None:
        self.peak: Decimal | None = None
        self.full_stop = False
        self.full_stop_cause: str | None = None
        self.kill_locked_day: str | None = None
        self.trips: list[dict] = []
        self._day_start_equity: dict[str, Decimal] = {}
        self._day_pnl: dict[str, Decimal] = {}

    # ------------------------------------------------------------ day start
    def mark_day(self, day_key: str, equity: Decimal) -> None:
        if day_key not in self._day_start_equity:
            self._day_start_equity[day_key] = equity
            self._day_pnl[day_key] = Decimal("0")

    def track_equity(self, equity: Decimal) -> None:
        """Per-bar equity high-water mark (rule 4 input)."""
        self.peak = max(self.peak, equity) if self.peak is not None else equity

    # -------------------------------------------------------------- entries
    def entry_refusal(self, day_key: str, vol16: float,
                      vol_hist: np.ndarray, blackout: bool) -> str | None:
        """Refusal cause for a would-be entry, or None if permitted."""
        if self.full_stop:
            return "governor_drawdown_full_stop_awaiting_rearm"
        if self.kill_locked_day == day_key:
            return "governor_daily_kill_refuse_only_rest_of_day"
        if blackout:
            return "governor_blackout_no_health_data"
        if vol_hist.shape[0] >= MIN_VOL_HIST and vol16 >= float(
                np.percentile(vol_hist, TOP_VOL_PCTILE)):
            return "governor_top_vol_percentile_regime"
        return None

    # ---------------------------------------------------------------- exits
    def on_exit(self, day_key: str, pnl: Decimal, equity: Decimal) -> None:
        """Register realized trade PnL; trip daily kill and drawdown stop.

        Call with the EXIT fill's day (realized then), pnl Decimal, equity
        AFTER the trade (Decimal)."""
        self._day_pnl[day_key] = self._day_pnl.get(
            day_key, Decimal("0")) + pnl
        self.peak = max(self.peak, equity) if self.peak is not None else equity
        if (not self.full_stop and self.peak is not None
                and equity <= self.peak * (Decimal(1) - Decimal(str(DRAWDOWN_CAP)))):
            self.full_stop = True
            self.full_stop_cause = "governor_drawdown_full_stop"
            self.trips.append({"event": "drawdown_full_stop",
                               "day": day_key,
                               "cause": "equity <= 90% of peak (rule 4)"})
        start_eq = self._day_start_equity.get(day_key)
        if (day_key not in self.kill_days()
                and start_eq is not None
                and self._day_pnl[day_key] <= start_eq * Decimal(str(-DAY_LOSS_CAP))):
            self.kill_locked_day = day_key
            self.trips.append({"event": "daily_kill_refuse_only",
                               "day": day_key,
                               "cause": "daily realized loss <= -1% (rule 3)"})

    def kill_days(self) -> set:
        return {x["day"] for x in self.trips if x.get("day") is not None}

    # ------------------------------------------------------------- re-arming
    def rearm(self) -> None:
        """Manual re-arming ONLY (rule 4). The daily refuse-only posture
        expires naturally at the next UTC day (day_key changes)."""
        self.full_stop = False
        self.full_stop_cause = None
