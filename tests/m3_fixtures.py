"""M3 test fixtures — deterministic, float64-exact synthetic channels.

Prices are kept binary-exact (.0/.5) so hand-computed expectations in the
tests are EXACT (A-3 semantics re-derived independently in each test).
"""
from types import SimpleNamespace

import numpy as np

IVMS = 3_600_000
EPOCH_MID = 1_700_006_400_000   # 2023-11-15 00:00:00 UTC (midnight anchor)


def ch(n=60, base=100.0, rng=1.0, ot=None):
    """Constant channel: o=c=base, h=base+rng, l=base-rng (true range 2rng).
    ot: optional open-time ms array (default 1h cadence from midnight)."""
    if ot is None:
        ot = EPOCH_MID + np.arange(n) * IVMS
    return SimpleNamespace(
        o=np.full(n, base), h=np.full(n, base + rng), l=np.full(n, base - rng),
        c=np.full(n, base), v=np.full(n, 1000.0),
        open_time=np.asarray(ot, dtype=np.int64),
        ivms=IVMS, pair="SYNTH", interval="1h", missing_slots=0)


def set_bar(ch, i, o, h, l, c, v=None):
    ch.o[i] = o; ch.h[i] = h; ch.l[i] = l; ch.c[i] = c
    if v is not None:
        ch.v[i] = v


def em(dmap=None, default=(0, -1e9)):
    dmap = dmap or {}
    return lambda t: dmap.get(t, default)
