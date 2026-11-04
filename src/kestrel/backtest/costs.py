"""Cost model (frozen, load-bearing — spec §3.5, M3.2).

Binance spot taker at VIP0: 0.10% per side ≈ 20 bps round-trip, treated as
an UNDER-estimate (conservative). A stress multiplier ×2 makes fees 40 bps
RT; ALL expectancy bars must survive the stressed run (A-5).

Slippage floor (price units, conservative/worse side):
- minimum 2 bps of the fill level on ANY level-fill;
- if a STOP would be hit mid-bar: floor = max(2 bps of level, ½ of that
  bar's high−low range);
- gap-through fills fill at the bar's open with NO extra slippage (the
  open is already the deterministic worse-side price).
The stress multiplier scales ALL costs (fees and slippage floors) — the
documented conservative reading of the spec.
"""
from __future__ import annotations

from decimal import Decimal

TAKER_FEE_PCT = Decimal("0.001")        # 0.10% per side, VIP0
SLIP_FLOOR_BPS = Decimal("0.0002")      # 2 bps of the fill level
STRESS_X = 2                            # the ALL bars must survive ×2


class Costs:
    """Decimal-exact cost book. All arithmetic EXACT (A-3 kernel-exact)."""

    def __init__(self, stress: float = 1.0) -> None:
        assert stress >= 1.0, "stress multiplier >= 1.0"
        self.stress = Decimal(str(stress))

    def fee(self, notional: Decimal) -> Decimal:
        return notional * TAKER_FEE_PCT * self.stress

    def slip(self, level: Decimal, bar_high: float, bar_low: float,
             is_stop: bool) -> Decimal:
        bps = SLIP_FLOOR_BPS * level
        if is_stop:
            half_range = (Decimal(str(bar_high)) - Decimal(str(bar_low))) / 2
            return max(bps, half_range) * self.stress
        return bps * self.stress
