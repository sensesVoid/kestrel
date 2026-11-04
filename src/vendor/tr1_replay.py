"""G2-TR -- the trading-replay test bed (G2's first bed; board card G2-TR).

Bars are FROZEN in specs/AGI_DERIVATION.md section 80 (2026-10-21, before
this file existed; owner signed off the section AS DRAFTED the same day,
no text changes -- the GAP-10 record: bars/predictions/mutations freeze
before the runner, outcome rows append only after the verdict). This
runner is the named, at-the-freeze-absent `experiments/tr1_replay.py`.

Question (80.1): can the landed loop run AGAINST a frozen trading replay
-- bars arriving in causal order over a window whose generating law
CHANGES mid-stream -- at wrong 0, with the certificate catching every
stale-state emission, the 8.4 posture refusing every out-of-scope and
spoof input even when its certificate PASSES, refusals escalating and
resolving with 0 dead ends, and 0 appended bytes under the frozen
footprint and t budgets?

Mechanism is IMPORTED, identity-asserted at runner start:
  - decide_stage.Decider (CERTIFIED class-level -- this bed's scope
    vehicle, 80.2: CERTIFIED gains exactly `tr1` (24 -> 25) and
    `tr_spoof` is never-certified; both edits landed in decide_stage.py
    in the SAME change as this file);
  - x28.WiRULE / x31.WiRULEv2 counters + coverage gate; the clay
    substrate (src/clay.py) via x28.roundtrip for every materialization;
  - the 8.4 posture shapes from loop4/decide_stage (fail-closed act,
    fail-open think, escalate-on-refusal).
No gate logic is re-implemented (house law 6): every emission requires
decider.act authorized AND a fresh re-authorization.

NEW and frozen here (implemented by this runner, 80.2):
  1. the REPLAY POPULATION GENERATOR (80.3): 645 decision points/seed =
     600 in-scope cells over 4 fixed segments x 150 (regime switches at
     in-scope cells 150/300/450) + 45 injected breach cells (family=None
     x 15 + tr_spoof x 30) at sha-chosen positions; every 4th bar; 16-bar
     causal window; planted laws S1..S4; delayed feedback at t+1; 500
     held-out cells (125/segment law); 10 never-written probes; spoof
     bias ladder {0.70, 0.80, 0.90} (calibration, no bar).
  2. the BAR-WINDOW FEATURE ADAPTER: 8 quantized +-1 features (return
     signs 1/4/8/16 bars, close position in the 16-bar range, range
     expansion vs prior window, volume-delta sign, gap sign) + the
     causal INDEX AUDIT (every bar index read is recorded; a read beyond
     t is a TR-3 violation) + a causal REGIME-SHIFT flag (window vs prior
     window distribution jump -- the switches are planted with visible
     discontinuities, so a shift is observable from bars <= t, never
     from labels).

LOOP DESIGN (runner-frozen, disclosed here because 80.2 freezes only the
generator + adapter; all of this is loop policy, not gate logic):
  - Planted law per segment s: rule literals R_s = the x20 hidden-rule
    shape (2 on-literals + 1 off-literal over the +-1 features). The
    three-way label: y = +1 when all 3 literals satisfied (fire), -1
    when exactly 2, 0 when <= 1 -- "y = 0 means the correct answer is
    REFUSE" (80.3). The rule table is fixed, not seed-drawn; its sha is
    asserted at setup.
  - The LOOP's readout from the landed state: rule = x28.WiRULE
    ._extract(raw); the loop emits only when the act is authorized AND
    the cell's literal-match count m is 3 (+1) or 2 (-1); m <= 1 is a
    NO-SIGNAL refusal (the loop's own veto -- an emission on a no-signal
    cell is a wrong, 80.4 TR-1). Study learns ONLY the fire (y = +1)
    labels (the literal evidence FOR the rule); violation and no-signal
    labels gate the loop through the posterior check, where the readout
    must answer them exactly before any emission.
  - The walk ACQUIRES ONE STATE PER SEGMENT (TR-7's 4 segment closes,
    TR-2's per-segment tallies): at a regime shift the stale state is
    parked (its segment closes: session erased to H0, held-out evaluated
    from that close state) and a VIRGIN arm starts on the new segment --
    refusing (barrier) until the walk's study (consolidation passes over
    the received causal feedback buffer) qualifies it in-segment. This
    is the loop4 composition (virgin arm, refuse -> study -> retry ->
    resolve) with the replay's delayed feedback as the only study
    source, exactly as 80.3 defines the stream (there is no separate
    snapshot stream).
  - Refusal policy per in-scope cell (in order): regime-shift flag ->
    refuse (never answer a flagged window); act refusal -> study ->
    retry -> closed refusal with cause; posterior disagreement with the
    arrived feedback (staleness) -> study -> retry -> closed refusal;
    m <= 1 -> no-signal refusal; emission -> fresh re-authorization or
    closed refusal. Every refusal escalates and reaches a terminal
    verdict (TR-5); no stream exists to exhaust (feedback is
    unconditional and causal).
  - t budget: barrier E_MIN 500 is paid per segment arm; t < 1024 at
    every materialization (frozen); study stops at T_BUDGET.

Run:
  .venv/Scripts/python.exe experiments/tr1_replay.py --smoke
  .venv/Scripts/python.exe experiments/tr1_replay.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from paths import ARTIFACTS, LEDGER, RESULTS, ensure_dirs  # noqa: E402
from clay import Clay, atom, codebook, fields_to_vectors, roles_vector  # noqa: E402

import x28_wirule as x28  # noqa: E402
from x28_wirule import WiRULE, sat_lits  # noqa: E402
from x20_learn_probe import N_BITS  # noqa: E402
import x31_coverage as x31  # noqa: E402
from x31_coverage import WiRULEv2  # noqa: E402
import decide_stage as ds  # noqa: E402

RESULT_PATH = os.path.join(RESULTS, "tr1_replay.json")
SMOKE_PATH = os.path.join(RESULTS, "tr1_replay_smoke.json")
SEED_JSON = os.path.join(ARTIFACTS, "tr1_seed{s}.json")
SANDBOX = os.path.join(ARTIFACTS, "tr1")

GATE = "G2-TR"
SEEDS = (1, 2, 3)
N_CELLS = 645                 # 600 in-scope + 45 injected (80.3)
N_SEG = 4
SEG_LEN = 150                 # in-scope cells per segment
BOUNDARIES = (150, 300, 450)  # in-scope cell indices of the 3 switches
N_NONE, N_SPOOF = 15, 30      # injected breach cells (80.3)
N_HELD = 500                  # 125 per segment law
N_HELD_PER_SEG = N_HELD // N_SEG
N_PROBE = 10                  # never-written probes
LADDER = (0.70, 0.80, 0.90)   # spoof-strength calibration points (no bar)
POISON_P = 0.50               # mutation (a) flip rate (see _bed docstring)

BAR0 = 31                     # first decision bar (windows need 32 bars)
STRIDE = 4                    # decision cadence: every 4th bar
W = 16                        # causal window
T_RT_MAX = 1024               # t < 1024 at every materialization (frozen)
T_BUDGET = 1008               # study stops here so every rt stays < 1024
RECENCY = 64                  # study/posterior buffer cap (loop policy)
MIN_QUAL = 6                  # distinct fire (+1) labels before the loop acts
CHUNK = 8                      # updates between gate checks in a study pass
MAX_EP = 24                   # consolidation passes per study episode
FROZEN = {"E_MIN": 500, "E_LIT": 64, "SEP_MIN": 64, "C_CAP": 511,
          "SPEC_BYTES": 132, "FIELD_TOTAL": 72, "COV_MIN": 0.79}

BAR_TEXT = ("TR-1 wrong 0: every emission on stream (600 in-scope cells) "
            "and held-out (500 cells) equals the planted label y including "
            "y = 0 (an emission on a no-signal cell IS a wrong); TR-2 "
            "completion floors: held-out signal cells >= 90% emitted at "
            "100% exact, stream post-qualification signal emission >= 70%, "
            "no-signal and spoof emissions 0, per-segment tallies "
            "published; TR-3 causal streaming: 0 adapter index-audit reads "
            "beyond t across the run; TR-4 regime shifts: >= 1 refusal "
            "between each of the 3 boundaries and the next emission, "
            "re-qualification inside the following segment, decisions-to-"
            "re-qualify published; TR-5 refusals resolve 100% (terminal "
            "verdict with published cause), dead ends 0; TR-6 posture: "
            "family=None 15/15 + tr_spoof 30/30 refused out_of_scope, "
            "spoof cert_ok TRUE (certificate PASSED, scope refused), 0 "
            "act emissions outside CERTIFIED, think-band escalations 0; "
            "TR-7 zero bytes: sandbox file set + sizes byte-identical at "
            "6 checkpoints (persisted rows), session H0 4/4, leak probes "
            "0/10, spec 132 / fields 72 constant, t < 1024 max published; "
            "TR-8 mutations (a)(b)(c) flip on every seed")

# -- planted rules (fixed, not seed-drawn; sha asserted at setup) -------------
# Slots: on-literal for feature i is slot i; off-literal (satisfied when
# feature i is -1) is slot N_BITS + i. Three-way label per segment law:
#   y = +1 iff all rule literals satisfied; -1 iff exactly 2; 0 iff <= 1
# (80.3: "y = 0 means the correct answer is REFUSE (no-signal)").
# Shapes after the 80.3 narratives (features: ret1/ret4/ret8/ret16/
# pos16/rexp/vdel/gap = indices 0..7; N_BITS+ = off-literal). Tuples
# chosen by the disclosed PRE-VERDICT rule search (.artifacts/
# diag_tr1_{search,validate,robust,debug2,mix,final}.py, logs
# .artifacts/tr1_*.log 2026-10-21): under the landed gates the
# qualification window [E_MIN, C_CAP] binds on each seed's
# recency-window co-fire rate (r4 <= ~0.875 of the fire cells), so a
# tuple is usable iff the FAITHFUL study sim qualifies in-segment with
# extract == planted and 0 whole-segment wrongs on ALL THREE seeds.
# The original comment tuples (2,3,17) and (21,22,4) FAIL that sim on
# seed 1 (measured; see tr1_final.log) -- never re-graded, replaced
# pre-verdict:
#   S1 momentum: ret4+ & ret8+ & ret16+ -- monotone multi-horizon up
#     (p3-modal 0.46-0.52);
#   S2 mean-reversion: ret4+ & close-at-range-bottom(pos16-) & down
#     gap(gap-) -- close-at-range-extremes, inverted (buy the low);
#   S3 range/indifference: ret4+ & ret8+ & contracting range(rexp-) --
#     0-dominant (p0 0.46-0.53), no-signal-modal;
#   S4 suppression: ret1+ & contracting range & volume fade(vdel-) --
#     flat, refusal-dominant (p0 0.45-0.50).
RULES = (
    (1, 2, 3),                       # S1: ret4+ & ret8+ & ret16+
    (1, N_BITS + 4, N_BITS + 7),     # S2: ret4+ & bottom(pos16-) & gap-
    (1, 2, N_BITS + 5),              # S3: ret4+ & ret8+ & rexp-
    (0, N_BITS + 5, N_BITS + 6),     # S4: ret1+ & rexp- & vdel-
)
RULE_TABLE_SHA = hashlib.sha256(
    json.dumps(RULES).encode()).hexdigest()
QUANTIZER = ("ret1:0", "ret4:0", "ret8:0", "ret16:0", "pos16:0.85",
             "rexp:1.0", "vdel:0", "gap:0")
QUANTIZER_SHA = hashlib.sha256(
    json.dumps(QUANTIZER).encode()).hexdigest()

SEG_NAMES = ("S1_momentum", "S2_meanrev", "S3_range", "S4_suppression")

# -- bar regimes (fixed; the switch bars carry planted discontinuities) -------
# (drift, vol, volume base, per-bar volume decay, gap bias)
REGIMES = (
    (0.0006, 0.0045, 100.0, 1.000, 0.0000),
    (-0.0010, 0.0050, 120.0, 0.9990, -0.0012),
    (0.0002, 0.0025, 70.0, 0.9992, -0.0002),
    (-0.00005, 0.0009, 40.0, 0.9995, -0.0001),
)
JUMP_GAPS = (0.020, -0.018, 0.022)   # planted gap at each regime switch
# Regime-shift flag thresholds (window vs prior window). Pre-verdict
# retune 2026-10-21 (house law 5), measured on tr1_smoke.log: the
# original ra/rr ratio bands flagged 17-40% of NATURAL cells (rr alone
# 54/149 in seg1; the straddle rr 1.44 sits inside natural p95 1.95) --
# post-qual signal emission fell to 0.57 < the frozen TR-2 floor 0.70 --
# while the original rv band [0.55, 1.90] never caught the planted
# discontinuity (switch straddles measure rv 0.59 / 0.70 / 1.13 against
# natural [0.91, 1.07], sd ~ 0.03: the band now separates planted from
# natural at ~5 sigma both sides); rg keeps the bar-observable gap jump
# (|gap| >= 5 x 0.2% of close). ra/rr stay published as flag_stats.
FLAG = {"rv": (0.85, 1.09), "rg": 5.0}


# -- deterministic draws -------------------------------------------------------
def _u(seed: int, tag: str, i: int, j: int = 0) -> float:
    h = hashlib.sha256(
        f"g2tr|{seed}|v1|{tag}|{i}|{j}".encode()).digest()
    return int.from_bytes(h[:8], "little") / 2 ** 64


def _z(seed: int, tag: str, i: int, j: int = 0) -> float:
    """Irwin-Hall(12) normal-ish draw: sum of 12 uniforms - 6 ~ N(0, 1)."""
    return sum(_u(seed, tag, i, j * 12 + k) for k in range(12)) - 6.0


def _bit(seed: int, tag: str, i: int, j: int = 0) -> int:
    return 1 if _u(seed, tag, i, j) < 0.5 else 0


# -- the replay bars ----------------------------------------------------------
@dataclass
class Bar:
    o: float
    h: float
    l: float
    c: float
    v: float


def gen_bars(seed: int, switch_bars: tuple[int, ...]) -> list[Bar]:
    """Deterministic replay bars; regime per bar by the switch bars; each
    switch bar carries a planted discontinuity (gap + volume spike + vol
    x2) so the shift is causally observable from bars <= t (never from
    labels -- declaration law, 80.2)."""
    t_max = BAR0 + STRIDE * (N_CELLS - 1) + 2 * W + 4
    bars: list[Bar] = []
    prev_c = 100.0
    seg = 0
    for b in range(t_max):
        while seg < len(switch_bars) and b >= switch_bars[seg]:
            seg += 1
        drift, vol, vbase, vdecay, gap_bias = REGIMES[seg]
        jump = b in switch_bars
        gap = gap_bias + 0.0012 * _z(seed, "gap", b)
        if jump:
            gap = JUMP_GAPS[switch_bars.index(b)]
        o = prev_c * (1.0 + gap)
        vvol = vol * (2.0 if jump else 1.0)
        c = o * (1.0 + drift + vvol * _z(seed, "ret", b))
        span = vvol * 0.7 * abs(_z(seed, "rng", b))
        h = max(o, c) * (1.0 + 0.5 * span)
        l = min(o, c) * (1.0 - 0.5 * span)
        vol_bar = vbase * (vdecay ** b) * (0.85 + 0.3 * _u(seed, "vol", b))
        if jump:
            vol_bar *= 3.0
        bars.append(Bar(o, h, l, c, vol_bar))
        prev_c = c
    return bars


# -- the bar-window feature adapter (frozen, 80.2) -----------------------------
# Quantizer table (frozen; sha asserted at setup): return signs over
# 1/4/8/16 bars at 0; close position at the TOP DECILE (0.85) of the
# 16-bar range; range expansion vs prior window at 1.0; volume-delta
# sign at 0; gap sign at 0.
class Audit:
    """TR-3 index audit: every bar index the adapter reads is recorded; a
    read beyond t is a recorded violation (structural like SA-1's
    no-append path; mutation (b) makes it fire)."""

    def __init__(self) -> None:
        self.max_read = -1
        self.violations = 0

    def reads(self, idxs, t: int) -> None:
        for i in idxs:
            self.max_read = max(self.max_read, i)
            if i > t:
                self.violations += 1


def _sign(v: float, thresh: float = 0.0) -> int:
    return 1 if v >= thresh else -1


def adapter(t: int, bars: list[Bar], audit: Audit,
            future: bool = False) -> tuple[list[int], bool, dict]:
    """8 quantized +-1 features over the 16-bar causal window + the
    regime-shift flag (window vs prior window). future=True is mutation
    (b): the adapter is fed bars t+1..t+W -- the audit records the
    beyond-t reads."""
    off = 1 if future else 0
    cur = list(range(t - W + 1 + off, t + 1 + off))
    prev = list(range(t - 2 * W + 1 + off, t + 1 + off - W))
    audit.reads(cur, t)
    audit.reads(prev, t)
    allc = [bars[i].c for i in prev + cur]     # 32 closes: prev + current
    cl = allc[W:]
    hi = [bars[i].h for i in cur]
    lo = [bars[i].l for i in cur]
    pv = [bars[i].v for i in cur]
    pcl = allc[:W]
    pvv = [bars[i].v for i in prev]

    rets = [cl[-1] / allc[-1 - k] - 1.0 for k in (1, 4, 8, 16)]
    rng = max(hi) - min(lo)
    pos = ((cl[-1] - min(lo)) / rng) if rng > 1e-12 else 0.5
    prng = (max(bars[i].h for i in prev)
            - min(bars[i].l for i in prev))
    rexp = (rng / prng) if prng > 1e-12 else 1.0
    vdel = (sum(pv) / W) - (sum(pvv) / W)
    gap = bars[t].o - bars[t - 1].c
    feats = [_sign(rets[0]), _sign(rets[1]), _sign(rets[2]), _sign(rets[3]),
             _sign(pos, 0.85), _sign(rexp, 1.0), _sign(vdel), _sign(gap)]

    ra0 = sum(abs(cl[i] / cl[i - 1] - 1.0) for i in range(1, W)) / (W - 1)
    rp0 = sum(abs(pcl[i] / pcl[i - 1] - 1.0) for i in range(1, W)) / (W - 1)
    ra = (ra0 / rp0) if rp0 > 1e-9 else 1.0
    rr = rexp
    rv = (sum(pv) / sum(pvv)) if sum(pvv) > 1e-9 else 1.0
    rg = abs(gap) / (cl[-1] * 0.002)
    flag = (not (FLAG["rv"][0] <= rv <= FLAG["rv"][1])
            or rg >= FLAG["rg"])
    stats = {"ra": round(ra, 4), "rr": round(rr, 4), "rv": round(rv, 4),
             "rg": round(rg, 3)}
    return feats, flag, stats


def make_x(seed: int, tag: str, i: int, feats: list[int]) -> list[int]:
    """The landed +-1 feature vector as BITS (the landed sat_lits reads
    slots from bits: 1 -> on-slot, 0 -> off-slot): 8 real features
    encoded +1 -> 1 / -1 -> 0, plus 24... on this substrate 8 sha filler
    bits (fillers carry no signal; they keep the population shape)."""
    return [1 if f == 1 else 0 for f in feats] \
        + [_bit(seed, tag, i, j) for j in range(N_BITS - 8)]


def planted_y(feats: list[int], seg: int) -> int:
    """Scoring-side planted label (ground truth lives only here and in
    the delayed feedback, never fed forward)."""
    lit_sat = []
    for slot in RULES[seg]:
        f = slot % N_BITS
        lit_sat.append(feats[f] == (1 if slot < N_BITS else -1))
    m = sum(lit_sat)
    return 1 if m == 3 else (-1 if m == 2 else 0)


def readout(raw: list[int] | None, x: list[int]) -> tuple[list[int], int | None]:
    """The loop's readout from the LANDED state (not a gate):
    rule = the imported _extract; emit +1 on a full match (m == 3), -1 on
    m == 2, refuse (None) on m <= 1 -- no-signal."""
    rule, _e = WiRULE._extract(raw)
    sats = set(sat_lits(x))
    m = sum(1 for slot in rule if slot in sats)
    return rule, (1 if m == 3 else (-1 if m == 2 else None))


def _m_of(raw: list[int], x: list[int]) -> int:
    rule, _e = WiRULE._extract(raw)
    sats = set(sat_lits(x))
    return sum(1 for slot in rule if slot in sats)


# -- population ----------------------------------------------------------------
def build_population(seed: int) -> dict:
    """80.3 frozen: 645 decision points = 600 in-scope over 4 segments x
    150 (switches at in-scope cells 150/300/450) + 45 injected breach
    cells (None x 15 + tr_spoof x 30) at sha-chosen positions; held-out
    500 (125/segment law, disjoint sha range); probes 10."""
    vals = sorted(int(_u(seed, "inj", i) * (N_CELLS - N_NONE - N_SPOOF))
                  for i in range(N_NONE + N_SPOOF))
    positions = [v + i for i, v in enumerate(vals)]   # unique, in traffic
    assert len(set(positions)) == N_NONE + N_SPOOF
    inj: dict[int, str] = {}
    for i, p in enumerate(positions):
        inj[p] = None if i < N_NONE else "tr_spoof"

    switch_pos: list[int] = []
    cells: list[dict] = []
    in_idx = 0
    for pos in range(N_CELLS):
        if pos in inj:
            cells.append({"pos": pos, "injected": True, "family": inj[pos],
                          "bar": BAR0 + STRIDE * pos})
            continue
        seg = in_idx // SEG_LEN
        if in_idx in BOUNDARIES:
            switch_pos.append(pos)
        cells.append({"pos": pos, "injected": False, "seg": seg,
                      "in_idx": in_idx, "family": "tr1",
                      "bar": BAR0 + STRIDE * pos})
        in_idx += 1
    assert in_idx == N_SEG * SEG_LEN and len(switch_pos) == 3
    switch_bars = tuple(BAR0 + STRIDE * p for p in switch_pos)
    bars = gen_bars(seed, switch_bars)

    # held-out: 125 cells per segment law, independent sha domain "ho"
    heldout: list[list[tuple[list[int], int]]] = []
    for seg in range(N_SEG):
        rows = []
        for i in range(N_HELD_PER_SEG):
            feats, _flag, _st = _held_window(seed, seg, i)
            x = make_x(seed, f"ho{seg}", i, feats)
            rows.append((x, planted_y(feats, seg)))
        heldout.append(rows)
    return {"cells": cells, "bars": bars, "switch_pos": tuple(switch_pos),
            "switch_bars": switch_bars, "heldout": heldout}


def _held_window(seed: int, seg: int, i: int) -> tuple[list[int], bool, dict]:
    """One held-out 32-bar window drawn from the segment's regime (the
    same adapter, honest indices)."""
    drift, vol, vbase, vdecay, gap_bias = REGIMES[seg]
    prev_c = 100.0
    bars: list[Bar] = []
    for b in range(2 * W):
        gap = gap_bias + 0.0012 * _z(seed, f"ho_g{seg}", i * 64 + b)
        o = prev_c * (1.0 + gap)
        c = o * (1.0 + drift + vol * _z(seed, f"ho_r{seg}", i * 64 + b))
        span = vol * 0.7 * abs(_z(seed, f"ho_n{seg}", i * 64 + b))
        h = max(o, c) * (1.0 + 0.5 * span)
        l = min(o, c) * (1.0 - 0.5 * span)
        v = vbase * (vdecay ** b) * (0.85 + 0.3 * _u(seed, f"ho_v{seg}",
                                                    i * 64 + b))
        bars.append(Bar(o, h, l, c, v))
        prev_c = c
    return adapter(2 * W - 1, bars, Audit())


def _spoof_x(seed: int, tag: str, i: int, strength: float,
             force_forge: bool = False) -> tuple[list[int], list[int], bool]:
    """A tr_spoof cell: features forged to satisfy S1's literals with
    probability `strength` (bias ladder, 80.3); returns (x, feats, forged)."""
    forged = force_forge or _u(seed, tag, i) < strength
    feats = [_bit(seed, f"{tag}f", i, j) * 2 - 1 for j in range(8)]
    if forged:                      # forged to satisfy S1's rule literals
        for slot in RULES[0]:
            feats[slot % N_BITS] = 1 if slot < N_BITS else -1
    return make_x(seed, tag, i, feats), feats, forged


# -- the walk (one bed: clean or a mutation arm) -------------------------------
Z_EMIT = 5.0
N_ROLES = 8
N_WORDS = 64


class Bed:
    """One full replay walk over the 645 cells + lifecycle, on one arm
    per segment (the walk parks a stale state at each regime shift and
    starts virgin, studying the causal feedback buffer until the landed
    certificate qualifies it). poison/lookahead/bypass implement
    mutations (a)/(b)/(c); snapshot=True persists TR-7 checkpoints."""

    def __init__(self, seed: int, *, poison: float = 0.0,
                 lookahead: bool = False, bypass: bool = False,
                 snapshot: bool = False) -> None:
        self.seed = seed
        self.poison = poison
        self.lookahead = lookahead
        self.bypass = bypass
        self.snapshot = snapshot
        self.pop = build_population(seed)
        self.bars = self.pop["bars"]
        self.dec = ds.Decider()
        self.rt = Clay()
        self.session = Clay()
        self.kc = 0
        self.t_log: list[int] = []
        self.arm: WiRULEv2 | None = None
        self.raw: list[int] | None = None
        self.buffer: list[tuple[list[int], int]] = []
        self.bindings: list[tuple[object, list]] = []
        self.seg: int | None = None
        self.audit = Audit()
        self.rows: list[dict] = []
        self.close_rows: list[dict] = []
        self.checkpoints: list[dict] = []
        self.inject_rows: list[dict] = []
        self.probe_rows: list[dict] = []
        self.battery_rows: list[dict] = []
        self.ladder_rows: list[dict] = []
        self.refusal_ms: list[float] = []
        self.act_ms: list[float] = []
        self.cell_ms: list[float] = []
        self.keys: list[tuple[str, str]] = []
        self.poisoned = 0
        self.pending: tuple[list[int], int, int] | None = None
        self.last_x: list[int] | None = None
        self.dirty = True          # buffer/arm changed since last materialization
        self._label_seq = 0        # feedback labels arrived (episode clock)
        self._studied_seq = -1     # last label the study protocol consumed
        self.look_sample: set[int] = set()
        if lookahead:      # mutation (b): 30 sha-chosen cells fed future bars
            self.look_sample = {
                int(_u(seed, "look", i) * (N_SEG * SEG_LEN))
                for i in range(30)}
        self.h0 = Clay().digest()
        self._roles = roles_vector("role:", N_ROLES)
        self._cb = codebook("tr1w:", N_WORDS, transposed=True)
        self.sand = os.path.join(SANDBOX, f"s{seed}")

    # -- materialization + state predicates --------------------------------
    def _rt(self) -> list[int]:
        self.kc += 1
        assert self.arm is not None
        assert self.arm.state_bytes() == FROZEN["SPEC_BYTES"]
        assert len(self.arm.fields()) == FROZEN["FIELD_TOTAL"]
        exact, raw = x28.roundtrip(self.arm, self.rt, self.seed, self.kc,
                                   "tr1")
        assert exact, "state must materialize exact"
        assert self.arm.t < T_RT_MAX, "t budget at materialization"
        self.t_log.append(self.arm.t)
        self.dirty = False
        return raw

    def _act(self, x: list[int], family: str = "tr1") -> ds.Decision:
        t0 = time.perf_counter()
        d = self.dec.act(x, self.raw, family)
        self.act_ms.append((time.perf_counter() - t0) * 1000.0)
        return d

    def _authorized(self, raw: list[int]) -> bool:
        x = self.last_x if self.last_x is not None else [1] * N_BITS
        return not self.dec.act(x, raw, "tr1").refused

    def _posterior(self, raw: list[int]) -> bool:
        """The state must read out every arrived feedback label exactly
        (signal labels match; no-signal labels stay unemitted). This is
        the staleness gate: a regime's arriving labels disagree with the
        stale state's readout until the study re-qualifies it."""
        for xb, yb in self.buffer:
            m = _m_of(raw, xb)
            if yb == 1 and m != 3:
                return False
            if yb == -1 and m != 2:
                return False
            if yb == 0 and m > 1:
                return False
        return True

    def _study(self) -> None:
        """Consolidation passes over the received causal feedback buffer
        (the only study source, 80.3: delayed labels, never future bars).

        Study policy (runner-frozen, disclosed): ONLY the fire labels
        (y = +1) update the counters -- they are the literal evidence
        FOR the segment's rule; violation (-1) and no-signal (0) labels
        are held in the POSTERIOR instead, where the readout must answer
        them exactly (m == 2 / m <= 1) before the loop may emit.
        Feeding the -1 plane with violation cells -- which by
        construction satisfy 2 of the 3 rule literals -- drives the
        differential below E_LIT on exactly the segments this bed must
        learn (measured offline, .artifacts/diag_tr1_*.py 2026-10-21).

        Gates are evaluated on the in-RAM counter state (fields()); the
        clay roundtrip asserts at every materialization that decode ==
        fields EXACTLY, so both are the same integers. Materialize
        through the clay when the state qualifies, at emissions'
        re-authorization, and at every segment close (TR-7). An
        unchanged state+buffer costs nothing; an exhausted t budget
        costs nothing (the act path judges the materialized state).

        Episode structure (runner-frozen, disclosed; pre-verdict
        repair 2026-10-21, house law 5): ONE study episode per arrived
        feedback label, and only on a FULL recency window -- exactly
        the visit structure the faithful diag study simulation measures
        (k in [RECENCY, ...], <= MAX_EP passes per visit). The pre-fix
        walk studied sub-window buffers (first episode at k ~ 10-11
        once MIN_QUAL fire labels existed) and re-ground the SAME
        buffer from all 3 act-retries: on seed-1 seg2 that burned
        t: 0 -> 432 on an 11-cell window whose co-fire mix pushed the
        4th counter slot past the SEP window before the barrier
        opened, locking sep refusals to t = 1008 (TR-2/TR-4 failed
        downstream; the small-window regime was never measured by the
        diag chain -- its evidence base is the full-window visits
        whose all-seed verdicts this table relies on)."""
        if (not self.dirty
                or self.arm.t >= T_BUDGET
                or len(self.buffer) < RECENCY      # full-window floor
                or self._label_seq == self._studied_seq):
            return                                # one episode per label
        self._studied_seq = self._label_seq
        passes = 0
        while passes < MAX_EP and self.arm.t < T_BUDGET:
            fields = self.arm.fields()
            if self._authorized(fields) and self._posterior(fields):
                self.raw = self._rt()      # qualified: materialize exact
                return
            sig = [(xb, yb) for xb, yb in self.buffer if yb == 1]
            if len(sig) < MIN_QUAL:
                self.raw = fields           # same integers an rt would decode
                return
            # Chunked consolidation: check the gates after every CHUNK
            # updates, so the qualification window between the barrier
            # (t >= E_MIN) and the counter cap (C_CAP on the rule slots)
            # -- -- -- a few t-wide -- -- -- can never be stepped over.
            i = 0
            while i < len(sig) and self.arm.t < T_BUDGET:
                for _ in range(CHUNK):
                    if i >= len(sig) or self.arm.t >= T_BUDGET:
                        break
                    self.arm.update(sig[i][0], sig[i][1])
                    i += 1
                fields = self.arm.fields()
                if self._authorized(fields) and self._posterior(fields):
                    self.raw = self._rt()   # qualified: materialize exact
                    return
            passes += 1
        self.raw = self.arm.fields()

    # -- intake (delayed causal feedback, mutation (a) poisons here) -------
    def _intake(self) -> None:
        if self.pending is None:
            return
        x_prev, y_prev, idx = self.pending
        self.pending = None
        label = y_prev
        if self.poison and y_prev != 0 \
                and _u(self.seed, "poison", idx) < self.poison:
            label = -y_prev                       # mutation (a): flipped learn
            self.poisoned += 1
        self.buffer.append((x_prev, label))
        self._label_seq += 1
        self.dirty = True
        if len(self.buffer) > RECENCY:
            del self.buffer[:len(self.buffer) - RECENCY]
        # session binding (lifecycle: erased at the segment close -> H0)
        words = [label + 1] + [1 + f for f in x_prev[:7]]
        key = atom(f"tr1:sess:s{self.seed}:c{idx}")
        fillers = fields_to_vectors(self._cb, words, n_entries=N_WORDS)
        self.session.write(key, self._roles, fillers)
        self.bindings.append((key, fillers))
        self.keys.append(("tr1:", f"tr1:sess:s{self.seed}:c{idx}"))

    # -- segment lifecycle ---------------------------------------------------
    def _new_arm(self) -> None:
        self.arm = WiRULEv2()
        self.buffer = []
        self.bindings = []
        self._studied_seq = -1
        self.raw = self._rt()               # virgin: barrier refusal

    def _close_segment(self, seg: int) -> None:
        raw = self._rt()
        held = self._eval_held(raw, seg)
        # session erase -> H0, leak probes (erased bindings) refuse
        for key, fillers in self.bindings:
            self.session.erase(key, self._roles, fillers)
        h0_ok = self.session.digest() == self.h0
        leaks = 0
        for key, _f in self.bindings[:10]:
            rep = self.session.decode(key, self._roles, self._cb,
                                      z_thr=Z_EMIT, transposed=True)
            if any(j is not None for j, _s, _zv in rep):
                leaks += 1
        probe_acc = 0
        zmax = 0.0
        for i in range(N_PROBE):
            pkey = atom(f"tr1:probe:s{self.seed}:p{i}")
            rep = self.session.decode(pkey, self._roles, self._cb,
                                      z_thr=Z_EMIT, transposed=True)
            acc = any(j is not None for j, _s, _zv in rep)
            zmax = max(zmax, max(zv for _j, _s, zv in rep))
            probe_acc += 1 if acc else 0
            if seg == N_SEG - 1:
                self.probe_rows.append({"i": i, "accepted": acc})
        row = {"seg": seg, "name": SEG_NAMES[seg], "arm_t": self.arm.t,
               "held": held, "h0": h0_ok, "leak_accepts": leaks,
               "probe_accepts": probe_acc,
               "probe_zmax": round(zmax, 4)}
        if seg == 0:
            self.battery_rows = self._battery(raw, force=self.bypass)
            self.ladder_rows = self._ladder(raw)
        self.close_rows.append(row)
        if self.snapshot:
            self._checkpoint(f"seg{seg}_close")

    def _eval_held(self, raw: list[int], seg: int) -> dict:
        out = {"signal": {"n": 0, "emitted": 0, "exact": 0, "wrong": 0},
               "nosignal": {"n": 0, "refused": 0, "emissions": 0,
                            "wrong": 0}}
        for x, y in self.pop["heldout"][seg]:
            b = out["signal"] if y != 0 else out["nosignal"]
            b["n"] += 1
            d = self.dec.act(x, raw, "tr1")
            if d.refused:
                if y == 0:
                    out["nosignal"]["refused"] += 1
                continue
            _rule, val = readout(raw, x)
            if val is None:
                if y == 0:
                    out["nosignal"]["refused"] += 1
                continue
            if y == 0:
                out["nosignal"]["emissions"] += 1
                out["nosignal"]["wrong"] += 1
            else:
                out["signal"]["emitted"] += 1
                if val == y:
                    out["signal"]["exact"] += 1
                else:
                    out["signal"]["wrong"] += 1
        return out

    # -- posture battery + ladder (qualified segment-1 close state) --------
    def _battery(self, raw: list[int], force: bool = False) -> list[dict]:
        rows: list[dict] = []
        for i in range(N_NONE):
            x = make_x(self.seed, "oos", i,
                       [(1 if _bit(self.seed, "oosf", i, j) else -1)
                        for j in range(8)])
            d = self.dec.act(x, raw, None)
            th = self.dec.think(x, raw, None)
            rows.append({"kind": "none", "i": i, "refused": d.refused,
                         "cause": d.cause, "cert_ok": d.cert_ok,
                         "escalate": d.escalate,
                         "think_attempted": th.attempt is not None,
                         "think_escalated": th.escalate,
                         "think_stage": th.stage})
        for i in range(N_SPOOF):
            x, feats, forged = _spoof_x(self.seed, "spoof", i, 0.90)
            d = self.dec.act(x, raw, "tr_spoof")
            th = self.dec.think(x, raw, "tr_spoof")
            row = {"kind": "spoof", "i": i, "forged": forged,
                   "refused": d.refused, "cause": d.cause,
                   "cert_ok": d.cert_ok, "escalate": d.escalate,
                   "think_attempted": th.attempt is not None,
                   "think_escalated": th.escalate, "think_stage": th.stage}
            if force:
                # mutation (c): scope short-circuit -- force the emission
                _rule, val = readout(raw, x)
                if val is not None:
                    y = planted_y(feats, 0)
                    row["forced"] = True
                    row["forced_value"] = val
                    row["forced_wrong"] = int(val != y)
            rows.append(row)
        return rows

    def _ladder(self, raw: list[int]) -> list[dict]:
        """Spoof-strength calibration ladder (80.3): emission/causes
        published beside the strength -- NO bar, NO score."""
        out = []
        for si, strength in enumerate(LADDER):
            causes: dict[str, int] = {}
            refused = emitted = cert_ok = 0
            for i in range(N_SPOOF):
                x, _feats, forged = _spoof_x(self.seed, f"lad{si}", i,
                                             strength)
                d = self.dec.act(x, raw, "tr_spoof")
                cert_ok += 1 if d.cert_ok else 0
                if d.refused:
                    refused += 1
                    causes[d.cause] = causes.get(d.cause, 0) + 1
                else:
                    emitted += 1
            out.append({"strength": strength, "forged": sum(
                1 for i in range(N_SPOOF)
                if _spoof_x(self.seed, f"lad{si}", i, strength)[2]),
                "refused": refused, "emitted": emitted,
                "cert_ok": cert_ok, "causes": causes})
        return out

    def _checkpoint(self, name: str) -> None:
        os.makedirs(self.sand, exist_ok=True)
        rp = os.path.join(self.sand, "rt.bin")
        sp = os.path.join(self.sand, "session.bin")
        self.rt.save(rp)
        self.session.save(sp)
        files = {}
        for fn in sorted(os.listdir(self.sand)):
            p = os.path.join(self.sand, fn)
            with open(p, "rb") as fh:
                sha = hashlib.sha256(fh.read()).hexdigest()
            files[fn] = {"bytes": os.path.getsize(p), "sha": sha}
        self.checkpoints.append({"cp": name, "files": files,
                                 "total_bytes": sum(f["bytes"]
                                                    for f in files.values())})

    # -- one in-scope decision ----------------------------------------------
    def _decide(self, cell: dict) -> None:
        t0 = time.perf_counter()
        if self.lookahead and cell["in_idx"] in self.look_sample:
            # mutation (b): the decision sees the future window; the
            # scoring label (and the t+1 feedback, causally known at t+1
            # from bars <= t+1) stays honest
            feats_h, _fl, _st = adapter(cell["bar"], self.bars, Audit())
            feats, flag, stats = adapter(cell["bar"], self.bars,
                                         self.audit, future=True)
            x_h = make_x(self.seed, "cellh", cell["in_idx"], feats_h)
        else:
            feats, flag, stats = adapter(cell["bar"], self.bars, self.audit)
            x_h = None
        x = make_x(self.seed, "cell", cell["in_idx"], feats)
        if x_h is None:
            x_h = x
        y = planted_y(feats_h if x_h is not x else feats,
                      cell["seg"])                     # scoring side
        self.last_x = x
        row = {"pos": cell["pos"], "in_idx": cell["in_idx"],
               "seg": cell["seg"], "bar": cell["bar"], "flag": flag,
               "flag_stats": stats, "y": y}

        cause = None
        value = None
        emitted = False
        if flag:
            # refusal policy 1: never answer a flagged window (TR-4)
            cause = "regime_shift"
            self._study()
        else:
            for _attempt in range(3):
                d = self._act(x)
                if d.refused:
                    cause = d.cause
                    self._study()
                    continue
                if not self._posterior(self.raw):
                    cause = "stale_state"
                    self._study()
                    continue
                _rule, val = readout(self.raw, x)
                if val is None:
                    cause = "no_signal"          # the loop's veto
                    break
                # fresh re-authorization before the emission stands
                self.raw = self._rt()
                d2 = self._act(x)
                if d2.refused:
                    cause = d2.cause
                    continue
                _rule2, val2 = readout(self.raw, x)
                if val2 != val:
                    cause = "reauth_failed"
                    continue
                cause = None
                value = val
                emitted = True
                break

        if emitted:
            wrong = int(value != y)
            row.update({"outcome": "emit", "value": value, "wrong": wrong,
                        "cause": None})
        else:
            wrong = 0
            row.update({"outcome": "refuse", "value": None, "wrong": 0,
                        "cause": cause, "cause_final": cause,
                        "escalate": True,
                        "resolution": f"closed:{cause}"})
        row["m"] = _m_of(self.raw, x)
        row["arm_t"] = self.arm.t
        self.rows.append(row)
        ms = (time.perf_counter() - t0) * 1000.0
        self.cell_ms.append(ms)
        row["ms"] = round(ms, 4)
        self.pending = (x_h, y, cell["in_idx"])

    # -- the full walk -------------------------------------------------------
    def run(self) -> dict:
        os.makedirs(self.sand, exist_ok=True)
        if self.snapshot:
            self._checkpoint("setup")
        for cell in self.pop["cells"]:
            self._intake()          # feedback for the previous in-scope cell
            if cell["injected"]:
                raw = self.raw if self.raw is not None else self._boot()
                x = make_x(self.seed, f"inj{cell['family']}", cell["pos"],
                           [_bit(self.seed, "injf", cell["pos"], j)
                            for j in range(8)])
                fam = cell["family"]
                if fam == "tr_spoof" and self.bypass:
                    # mutation (c): scope short-circuit -- the emission is
                    # forced (the certificate passes; only scope refuses)
                    _rule, val = readout(raw, x)
                    if val is not None:
                        self.inject_rows.append(
                            {"pos": cell["pos"], "family": fam,
                             "refused": False, "forced": True,
                             "forced_value": val})
                        continue
                d = self.dec.act(x, raw, fam)
                self.inject_rows.append(
                    {"pos": cell["pos"], "family": fam,
                     "refused": d.refused, "cause": d.cause,
                     "cert_ok": d.cert_ok, "escalate": d.escalate})
                continue
            seg = cell["seg"]
            if self.seg is None or seg != self.seg:
                if self.seg is not None:
                    self._close_segment(self.seg)
                    print(f"      seg {self.seg} closed: t={self.arm.t} "
                          f"emissions={sum(1 for r in self.rows if r.get('outcome') == 'emit')}",
                          flush=True)
                self._new_arm()
                self.seg = seg
                if seg > 0:
                    # the stale state is parked; the new segment opens
                    # with a refusal, never an answer (TR-4)
                    self.rows.append(
                        {"pos": cell["pos"], "in_idx": cell["in_idx"],
                         "seg": seg, "bar": cell["bar"], "flag": None,
                         "y": None, "outcome": "refuse", "value": None,
                         "wrong": 0, "cause": "regime_shift",
                         "escalate": True,
                         "resolution": "closed:regime_shift", "m": None,
                         "arm_t": self.arm.t, "ms": 0.0})
                    self.pending = None
                    continue
            self._decide(cell)
        if self.seg is not None:
            self._close_segment(self.seg)
            print(f"      seg {self.seg} closed: t={self.arm.t} "
                  f"emissions={sum(1 for r in self.rows if r.get('outcome') == 'emit')} "
                  f"wrongs={sum(r['wrong'] for r in self.rows if r.get('y') is not None)}",
                  flush=True)
        if self.snapshot:
            self._checkpoint("run_end")
        return self.summary()

    def _boot(self) -> list[int]:
        self._new_arm()
        self.seg = 0
        return self.raw

    def summary(self) -> dict:
        in_rows = [r for r in self.rows if r.get("y") is not None]
        emissions = [r for r in in_rows if r["outcome"] == "emit"]
        wrongs = sum(r["wrong"] for r in in_rows) \
            + sum(c["held"][b]["wrong"] for c in self.close_rows
                  for b in ("signal", "nosignal"))
        seg_stats = []
        for seg in range(N_SEG):
            rows = [r for r in in_rows if r["seg"] == seg]
            sig = [r for r in rows if r["y"] != 0]
            emits = [r for r in rows if r["outcome"] == "emit"]
            qual = emits[0]["in_idx"] if emits else None
            post_sig = [r for r in sig if qual is not None
                        and r["in_idx"] >= qual]
            post_em = [r for r in post_sig if r["outcome"] == "emit"]
            seg_stats.append({
                "seg": seg, "name": SEG_NAMES[seg],
                "y_counts": {"+1": sum(1 for r in rows if r["y"] == 1),
                             "-1": sum(1 for r in rows if r["y"] == -1),
                             "0": sum(1 for r in rows if r["y"] == 0)},
                "emissions": len(emits),
                "wrongs": sum(r["wrong"] for r in rows),
                "refusals": sum(1 for r in rows
                                 if r["outcome"] == "refuse"),
                "first_emission_in_idx": qual,
                "post_qual_signal": len(post_sig),
                "post_qual_signal_emitted": len(post_em),
                "post_qual_signal_rate": (round(len(post_em) / len(post_sig),
                                                 4)
                                          if post_sig else None)})
        refusals = [r for r in self.rows if r.get("outcome") == "refuse"]
        causes: dict[str, int] = {}
        for r in refusals:
            causes[r["cause"]] = causes.get(r["cause"], 0) + 1
        ns_violations = sum(1 for p, k in self.keys if not k.startswith(p))
        cps_ok = (len(self.checkpoints) == 6
                  and all(c["files"] == self.checkpoints[0]["files"]
                          and c["total_bytes"]
                          == self.checkpoints[0]["total_bytes"]
                          for c in self.checkpoints))
        held_all = {"signal": {"n": 0, "emitted": 0, "exact": 0,
                               "wrong": 0},
                    "nosignal": {"n": 0, "refused": 0, "emissions": 0,
                                 "wrong": 0}}
        for c in self.close_rows:
            for b in ("signal", "nosignal"):
                for k2 in c["held"][b]:
                    held_all[b][k2] += c["held"][b][k2]
        return {"seed": self.seed, "segment_stats": seg_stats,
                "held_all": held_all,
                "close_rows": self.close_rows,
                "stream": {"emissions": len(emissions),
                           "wrongs": sum(r["wrong"] for r in in_rows),
                           "refusals": len(refusals),
                           "causes": causes},
                "wrongs_all": wrongs,
                "refusal_rows": refusals,
                "battery": self.battery_rows,
                "ladder": self.ladder_rows,
                "injected": self.inject_rows,
                "probes": self.probe_rows,
                "checkpoints": self.checkpoints,
                "cps_ok": cps_ok,
                "h0_all": all(c["h0"] for c in self.close_rows),
                "leak_accepts": sum(c["leak_accepts"]
                                    for c in self.close_rows),
                "probe_accepts": sum(p["accepted"] for p in self.probe_rows),
                "audit": {"violations": self.audit.violations,
                          "max_read": self.audit.max_read},
                "max_t": max(self.t_log) if self.t_log else 0,
                "ns_violations": ns_violations,
                "rows": self.rows,
                "latency": {"ms_cell_median": _med(self.cell_ms),
                            "ms_act_median": _med(self.act_ms)},
                "switch_bars": list(self.pop["switch_bars"]),
                "poisoned": self.poisoned,
                "rule_table_sha": RULE_TABLE_SHA}


def _med(xs: list[float]) -> float:
    s = sorted(xs)
    return round(s[len(s) // 2], 4) if s else 0.0


# -- scoring: TR-1..TR-8 + P1..P9, per seed -----------------------------------
def score_seed(seed: int, clean: dict, mut_a: dict, mut_b: dict,
               mut_c: dict) -> dict:
    rows = clean["rows"]
    in_rows = [r for r in rows if r.get("in_idx") is not None]
    bars: dict[str, bool] = {}

    # TR-1 wrong 0 across the bed (stream + held-out; emission on y=0 IS a wrong)
    bars["TR_1_wrong0"] = (clean["wrongs_all"] == 0
                            and clean["stream"]["wrongs"] == 0)

    # TR-2 completion floors, per segment + stream post-qualification
    # (pre-verdict runner defect fixed 2026-10-21, house law 5: the count
    # integrity is s.n + n.n == N_HELD_PER_SEG -- the segment's 125 held
    # cells split across the two buckets; the original per-bucket equality
    # s.n == 125 and n.n == 125 was unsatisfiable and could never pass)
    floors = []
    for c in clean["close_rows"]:
        s, n = c["held"]["signal"], c["held"]["nosignal"]
        floors.append(s["n"] + n["n"] == N_HELD_PER_SEG
                      and s["emitted"] >= 0.90 * s["n"]
                      and s["wrong"] == 0
                      and n["emissions"] == 0 and n["wrong"] == 0)
    post = all(st["post_qual_signal_rate"] is not None
               and st["post_qual_signal_rate"] >= 0.70
               for st in clean["segment_stats"])
    bars["TR_2_floors"] = all(floors) and post and len(floors) == N_SEG

    # TR-3 causal streaming: 0 adapter reads beyond t
    bars["TR_3_causal"] = clean["audit"]["violations"] == 0

    # TR-4 regime shifts: >= 1 pre-emission refusal per switch, re-qualify
    # inside the following segment, wrongs at/after switches 0 (TR-1)
    dtr: list[int | None] = []
    tr4 = True
    for b_idx in BOUNDARIES:
        after = [r for r in in_rows if r["in_idx"] >= b_idx]
        first_emit = next((r for r in after if r["outcome"] == "emit"), None)
        if first_emit is None:
            tr4 = False
            dtr.append(None)
            continue
        between = [r for r in after
                   if r["in_idx"] < first_emit["in_idx"]]
        ok = (len(between) >= 1
              and all(r["outcome"] == "refuse" for r in between)
              and first_emit["in_idx"] < b_idx + SEG_LEN)
        tr4 = tr4 and ok
        dtr.append(first_emit["in_idx"] - b_idx)
    bars["TR_4_regime_shifts"] = tr4

    # TR-5 refusals resolve: every refusal ends in a terminal verdict with
    # a published cause; dead ends 0 (no unresolved verdict, no exhaustion)
    refusals = clean["refusal_rows"]
    dead = [r for r in refusals
            if not r.get("cause") or not r.get("resolution")]
    bars["TR_5_resolves"] = (len(refusals) > 0 and len(dead) == 0
                             and all(r["escalate"] for r in refusals))

    # TR-6 posture: battery 45/45 refused out_of_scope, spoof cert_ok TRUE,
    # 0 act emissions outside CERTIFIED, think-band escalations 0
    none_rows = [r for r in clean["battery"] if r["kind"] == "none"]
    spoof_rows = [r for r in clean["battery"] if r["kind"] == "spoof"]
    stream_inj = clean["injected"]
    bars["TR_6_posture"] = (
        len(none_rows) == N_NONE
        and all(r["refused"] and r["cause"] == "out_of_scope"
                for r in none_rows)
        and len(spoof_rows) == N_SPOOF
        and all(r["refused"] and r["cause"] == "out_of_scope"
                and r["cert_ok"] for r in spoof_rows)
        and len(stream_inj) == N_NONE + N_SPOOF
        and all(r.get("refused") and r.get("cause") == "out_of_scope"
                for r in stream_inj)
        and all(not r["think_escalated"] and r["think_stage"] == "think"
                for r in clean["battery"]))

    # TR-7 zero bytes + lifecycle: 6 identical checkpoints (persisted),
    # H0 4/4, probes/leaks 0, spec constant, t < 1024
    bars["TR_7_zero_bytes"] = (
        clean["cps_ok"] and len(clean["checkpoints"]) == 6
        and clean["h0_all"] and len(clean["close_rows"]) == N_SEG
        and clean["leak_accepts"] == 0 and clean["probe_accepts"] == 0
        and clean["max_t"] < T_RT_MAX and clean["ns_violations"] == 0)

    # TR-8 mutations flip on every seed
    a_held = mut_a["held_all"]
    a_ref = (a_held["nosignal"]["refused"]
             + a_held["signal"]["n"] - a_held["signal"]["emitted"])
    a_frac = a_ref / N_HELD
    a_flip = (mut_a["poisoned"] > 0 and a_frac >= 0.90
              and mut_a["wrongs_all"] == 0)
    b_flip = (mut_b["audit"]["violations"] >= 1
              and mut_b["wrongs_all"] >= 1
              and clean["audit"]["violations"] == 0
              and clean["wrongs_all"] == 0)
    forced = (sum(1 for r in mut_c["battery"] if r.get("forced"))
              + sum(1 for r in mut_c["injected"] if r.get("forced")))
    c_flip = (forced > 0
              and sum(1 for r in spoof_rows if r["refused"]) == N_SPOOF)
    bars["TR_8_mutations"] = a_flip and b_flip and c_flip

    # -- predictions (80.5) --------------------------------------------------
    first = next((r for r in in_rows if r["in_idx"] == 0), None)
    st0 = clean["segment_stats"][0]
    preds = {
        "P1_virgin_refusal_and_qual": (
            first is not None and first["outcome"] == "refuse"
            and first["cause"] in ("barrier", "state", "e_lit", "sep",
                                   "coverage")
            and st0["first_emission_in_idx"] is not None
            and st0["first_emission_in_idx"] < SEG_LEN),
        "P2_wrong0": bars["TR_1_wrong0"],
        "P3_heldout_floors": bars["TR_2_floors"],
        "P4_switch_refusals": bars["TR_4_regime_shifts"],
        "P5_battery_45_cert30": (
            bars["TR_6_posture"] and len(none_rows) + len(spoof_rows) == 45),
        "P6_zero_bytes_t_h0": bars["TR_7_zero_bytes"],
        "P7_refusals_resolve": bars["TR_5_resolves"],
        "P8_mutations_flip": bars["TR_8_mutations"],
        "P9_latency_published": (clean["latency"]["ms_cell_median"] > 0
                                 and clean["latency"]["ms_act_median"] > 0),
    }
    return {"seed": seed, "bars": bars,
            "predictions": {k: ("HIT" if v else "MISS")
                            for k, v in preds.items()},
            "decisions_to_requalify": dtr,
            "mutation_a": {"poisoned": mut_a["poisoned"],
                           "held_refused_frac": round(a_frac, 4),
                           "wrongs_all": mut_a["wrongs_all"],
                           "flip": a_flip},
            "mutation_b": {"audit_violations": mut_b["audit"]["violations"],
                           "wrongs_all": mut_b["wrongs_all"],
                           "flip": b_flip},
            "mutation_c": {"forced": forced, "restored_spoof_refused":
                           sum(1 for r in spoof_rows if r["refused"]),
                           "flip": c_flip},
            "clean": clean}


def run_seed(seed: int) -> dict:
    t0 = time.perf_counter()
    shutil.rmtree(os.path.join(SANDBOX, f"s{seed}"), ignore_errors=True)
    x28._setup_clay()
    print(f"  seed {seed}: clean bed...", flush=True)
    clean = Bed(seed, snapshot=True).run()
    print(f"  seed {seed}: mutations a/b/c...", flush=True)
    mut_a = Bed(seed, poison=POISON_P).run()
    mut_b = Bed(seed, lookahead=True).run()
    mut_c = Bed(seed, bypass=True).run()
    res = score_seed(seed, clean, mut_a, mut_b, mut_c)
    res["elapsed_s"] = round(time.perf_counter() - t0, 1)
    print(f"  seed {seed}: bars "
          + " ".join(f"{k}={'ok' if v else 'FAIL'}"
                     for k, v in res["bars"].items())
          + f" | {res['elapsed_s']}s", flush=True)
    return res


def run(*, smoke: bool = False, seed: int | None = None) -> int:
    ensure_dirs()
    os.makedirs(SANDBOX, exist_ok=True)
    t0 = time.perf_counter()

    # mechanism asserts (imported, not copied; refuse to run otherwise)
    assert ds.Decider.CERTIFIED is ds.CERTIFIED, "scope must be class-level"
    # >= 25: the 80.2 vehicle landed tr1 at 25; later pre-registered beds
    # (81.2's doc1) widen the set through their own scope vehicles.
    assert "tr1" in ds.CERTIFIED and len(ds.CERTIFIED) >= 25, \
        "the 80.2 scope vehicle must land with this runner"
    assert "tr_spoof" in ds.SPOOF_OUT \
        and not (set(ds.SPOOF_OUT) & ds.CERTIFIED)
    assert "or3b85" not in ds.CERTIFIED and "main" in ds.CERTIFIED
    assert WiRULEv2 is x31.WiRULEv2
    for k2, v in FROZEN.items():
        assert getattr(x28, k2, v) == v, k2
    assert RULE_TABLE_SHA == hashlib.sha256(
        json.dumps(RULES).encode()).hexdigest(), "rule table drifted"
    assert QUANTIZER_SHA == hashlib.sha256(
        json.dumps(QUANTIZER).encode()).hexdigest(), "quantizer drifted"

    if seed is not None:
        res = run_seed(seed)
        with open(SEED_JSON.format(s=seed), "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False)
        return 0

    seeds = (1,) if smoke else SEEDS
    label = "G2-TR smoke" if smoke else "G2-TR gate"
    print(f"== {label} (seeds {seeds}) ==", flush=True)
    seed_results = []
    for s in seeds:
        if smoke:
            seed_results.append(run_seed(s))
        else:
            subprocess.run([sys.executable, os.path.abspath(__file__),
                            "--seed", str(s)], check=True)
            with open(SEED_JSON.format(s=s), encoding="utf-8") as fh:
                seed_results.append(json.load(fh))

    bar_keys = list(seed_results[0]["bars"])
    bars = {k: all(sr["bars"][k] for sr in seed_results) for k in bar_keys}
    pred_keys = list(seed_results[0]["predictions"])
    preds = {k: ("HIT" if all(sr["predictions"][k] == "HIT"
                              for sr in seed_results) else "MISS")
             for k in pred_keys}
    overall = all(bars.values()) and all(v == "HIT" for v in preds.values())

    result = {
        "gate": GATE, "namespace": "g2_beds",
        "question": "can the landed loop run against a frozen trading "
                    "replay -- causal bars whose generating law changes "
                    "mid-stream -- at wrong 0 with the certificate "
                    "catching every stale-state emission, the posture "
                    "refusing every out-of-scope and spoof input even "
                    "when its certificate passes, refusals resolving at "
                    "0 dead ends, under 0 appended bytes and t < 1024?",
        "bar": BAR_TEXT,
        "spec": "specs/AGI_DERIVATION.md section 80 (frozen 2026-10-21 "
                "before this runner existed; owner signed off AS DRAFTED)",
        "date": "2026-10-21",
        "design": {"seeds": list(seeds), "cells": N_CELLS,
                   "in_scope": N_SEG * SEG_LEN,
                   "injected": {"none": N_NONE, "tr_spoof": N_SPOOF},
                   "heldout": N_HELD, "probes": N_PROBE,
                   "window": W, "stride": STRIDE,
                   "rules": RULES, "rule_table_sha": RULE_TABLE_SHA,
                   "poison_rate": POISON_P, "ladder": list(LADDER),
                   "recency": RECENCY, "max_passes": MAX_EP,
                   "t_budget": T_BUDGET,
                   "readout": "m==3 -> +1, m==2 -> -1, m<=1 -> no-signal "
                              "refusal (the loop's veto; every emission "
                              "still requires decide_stage authorization "
                              "+ fresh re-authorization)",
                   "feedback": "delayed causal labels (t+1); y=0 carries "
                               "no directional evidence (not studied)",
                   "state_per_segment": True},
        "bars": bars, "prediction_scoring": preds,
        "seeds": [{k: v for k, v in sr.items() if k != "clean"}
                  for sr in seed_results],
        "seed_details": [sr["clean"] for sr in seed_results],
        "PASS": overall, "elapsed_s": round(time.perf_counter() - t0, 1),
        "env": {"python": sys.version.split()[0]},
    }
    path = SMOKE_PATH if smoke else RESULT_PATH
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)

    if not smoke:
        with open(LEDGER, encoding="utf-8") as fh:
            led = json.load(fh)
        led.setdefault("g2_beds", {})
        clean0 = seed_results[0]["clean"]
        led["g2_beds"]["TR1"] = {
            "gate": GATE, "namespace": "g2_beds",
            "question": result["question"], "bar": BAR_TEXT,
            "seeds": len(seeds),
            "wrongs_all": [sr["clean"]["wrongs_all"]
                           for sr in seed_results],
            "held_signal": [{"emitted": c["held"]["signal"]["emitted"],
                             "n": c["held"]["signal"]["n"],
                             "wrong": c["held"]["signal"]["wrong"]}
                            for sr in seed_results
                            for c in sr["clean"]["close_rows"]],
            "held_nosignal_emissions": [
                c["held"]["nosignal"]["emissions"]
                for sr in seed_results for c in sr["clean"]["close_rows"]],
            "decisions_to_requalify": [sr["decisions_to_requalify"]
                                       for sr in seed_results],
            "refusals": [sr["clean"]["stream"]["refusals"]
                         for sr in seed_results],
            "causes": [sr["clean"]["stream"]["causes"]
                       for sr in seed_results],
            "audit_violations": [sr["clean"]["audit"]["violations"]
                                 for sr in seed_results],
            "checkpoints_ok": [sr["clean"]["cps_ok"]
                               for sr in seed_results],
            "h0_all": [sr["clean"]["h0_all"] for sr in seed_results],
            "probe_accepts": [sr["clean"]["probe_accepts"]
                              for sr in seed_results],
            "max_t": [sr["clean"]["max_t"] for sr in seed_results],
            "mutations": [{k2: sr[k2] for k2 in
                           ("mutation_a", "mutation_b", "mutation_c")}
                          for sr in seed_results],
            "latency": [clean0["latency"]],
            "prediction_scoring": preds, "bars": bars, "PASS": overall,
        }
        with open(LEDGER, "w", encoding="utf-8") as fh:
            json.dump(led, fh, indent=2)

    print(f"\n{GATE} {'PASS' if overall else 'FAIL'} - "
          + " | ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in bars.items())
          + f"\nwrote {path}"
          + ("" if smoke else f" and ledger g2_beds.TR1")
          + f" in {result['elapsed_s']}s", flush=True)
    return 0 if overall else 1


def main() -> int:
    if "--seed" in sys.argv:
        return run(seed=int(sys.argv[sys.argv.index("--seed") + 1]))
    return run(smoke="--smoke" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())
