"""S1 quantizer boundary (M2.2): frozen ±1 templates + quantize-table
generator + TR-3 audit, extracted byte-faithfully from the pinned vendor.

Lock discipline (M2.2 / spec §80.3, inherited §112):
- ALL frozen constants (QUANTIZER, RULES, their shas, FLAG, W) are parsed
  from the PINNED vendored file `src/vendor/tr1_replay.py` — never edited
  in k source-of-x — and this module SELF-ASSERTS at import: vendored file
  sha must equal its pin in specs/vendor_pins.json and the recomputed
  serialization shas must equal the ones frozen in the vendored file.
  A drifted vendored file fails the import, so every runner that imports
  this module has the quantizer lock asserted (contract, M2.2).
- tr1_replay.py is a frozen REFERENCE source: its experiment harness
  import-closure (x28/x31/decide_stage cascade) is intentionally NOT
  vendored; only the constants block is executed here with N_BITS injected
  from `x20_learn_probe.py` (read numerically; no torch import in M2).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

ROOT = str(Path(__file__).resolve().parents[3])   # repo root
VENDOR = os.path.join(ROOT, "src", "vendor")
TR1 = os.path.join(VENDOR, "tr1_replay.py")
X20 = os.path.join(VENDOR, "x20_learn_probe.py")
PINS = os.path.join(ROOT, "specs", "vendor_pins.json")


def _assert_pin_and_parse():
    pins = json.load(open(PINS, encoding="utf-8"))
    pin = next(p for p in pins["pins"] if p["vendored"] == "src/vendor/tr1_replay.py")
    raw = open(TR1, "rb").read()
    if hashlib.sha256(raw).hexdigest() != pin["sha256"]:
        raise RuntimeError("vendored tr1_replay.py drifted from its pin (quantizer lock)")
    src = raw.decode("utf-8")
    i0 = next(i for i, l in enumerate(src.splitlines()) if l.startswith("RULES = ("))
    i1 = next(i for i, l in enumerate(src.splitlines()) if l.startswith("SEG_NAMES = "))
    block = "import hashlib, json\n" + "\n".join(src.splitlines()[i0:i1])
    x20 = open(X20, "rb").read().decode("utf-8")
    m = re.search(r"^N_BITS\s*=\s*(\d+)\s*$", x20, re.M)
    ns = {"N_BITS": int(m.group(1))}
    exec(block, ns)
    flag_m = re.search(r"^FLAG\s*=\s*(\{.*\})\s*$", src, re.M)
    ns["FLAG"] = eval(flag_m.group(1))
    # recompute the serialization shas from the parsed constants: lock.
    q_sha = hashlib.sha256(json.dumps(ns["QUANTIZER"]).encode()).hexdigest()
    r_sha = hashlib.sha256(json.dumps(ns["RULES"]).encode()).hexdigest()
    if ns["QUANTIZER_SHA"] != q_sha or ns["RULE_TABLE_SHA"] != r_sha:
        raise RuntimeError("quantizer serialization shas drifted (parsed != computed)")
    W_m = re.search(r"^W\s*=\s*(\d+)(\s*#.*)?$", src, re.M)
    return ns, {"QUANTIZER": ns["QUANTIZER"], "RULES": ns["RULES"],
                "QUANTIZER_SHA": q_sha, "RULE_TABLE_SHA": r_sha,
                "FLAG": ns["FLAG"], "N_BITS": int(m.group(1)),
                "W": int(W_m.group(1))}


_ns, FROZEN = _assert_pin_and_parse()

QUANTIZER: Tuple[str, ...] = tuple(FROZEN["QUANTIZER"])
RULES: Tuple[Tuple[int, int, int], ...] = tuple(FROZEN["RULES"])
QUANTIZER_SHA: str = FROZEN["QUANTIZER_SHA"]
RULE_TABLE_SHA: str = FROZEN["RULE_TABLE_SHA"]
FLAG: Dict[str, object] = FROZEN["FLAG"]
N_BITS: int = FROZEN["N_BITS"]
W: int = FROZEN["W"]           # 16-bar causal window (vendor line 133)

# template name -> their rendering (pos threshold 0.85 = top-decile position;
# rexp threshold 1.0; ret{1,4,8,16}, gap, vdel at 0)
THRESHOLDS = {"ret1": 0.0, "ret4": 0.0, "ret8": 0.0, "ret16": 0.0,
              "pos16": 0.85, "rexp": 1.0, "vdel": 0.0, "gap": 0.0}


class AdapterAudit:
    """TR-3 index audit (vendor verbatim semantics): records every bar index
    read by the adapter; any read beyond t is a structural violation that
    mutation (b) (future=True) must make fire (A-1)."""

    def __init__(self) -> None:
        self.max_read = -1
        self.violations = 0

    def reads(self, idxs, t: int) -> None:
        for i in idxs:
            self.max_read = max(self.max_read, int(i))
            if int(i) > t:
                self.violations += 1


def _sign(v: float, thresh: float = 0.0) -> int:
    return 1 if v >= thresh else -1


def quantize_window(o, h, l, c, v, t: int, audit: Optional[AdapterAudit] = None,
                    future: bool = False) -> Tuple[List[int], bool, Dict[str, float]]:
    """8 quantized ±1 features over the 16-bar causal window + regime-shift
    flag — vertex-for-vertex the vendored tr1_replay.adapter semantics on
    real arrays (frozen thresholds in THRESHOLDS/FLAG).

    t is an integer index into the ACTUAL loaded bars (windows freeze on
    bar indices, never timestamps — missing-bar holes are handled upstream).

    future=True is mutation (b): the adapter is fed bars t+1..t+W — the
    audit records the beyond-t reads (HL-5: mutations must flip).
    """
    W16 = W
    off = 1 if future else 0
    cur = list(range(t - W16 + 1 + off, t + 1 + off))
    prev = list(range(t - 2 * W16 + 1 + off, t + 1 + off - W16))
    if audit is not None:
        audit.reads(cur, t)
        audit.reads(prev, t)
    a_c = np.asarray(c, dtype=np.float64)
    a_h = np.asarray(h, dtype=np.float64)
    a_l = np.asarray(l, dtype=np.float64)
    a_v = np.asarray(v, dtype=np.float64)
    a_o = np.asarray(o, dtype=np.float64)
    allc = np.concatenate((a_c[prev], a_c[cur]))     # 32 closes: prev + cur
    cl = allc[W16:]
    hi = a_h[cur]
    lo = a_l[cur]
    pv = a_v[cur]
    pcl = a_c[prev]
    pvv = a_v[prev]

    rets = [cl[-1] / allc[-1 - k] - 1.0 for k in (1, 4, 8, 16)]
    rng = hi.max() - lo.min()
    pos = ((cl[-1] - lo.min()) / rng) if rng > 1e-12 else 0.5
    prng = a_h[prev].max() - a_l[prev].min()
    rexp = (rng / prng) if prng > 1e-12 else 1.0
    # FP-order parity with the vendored reference: vendor folds python
    # builtin sum() over small float lists (left-fold); mirror it exactly
    # for vdel/ra/rp/rv instead of pairwise-summation numpy reductions.
    pv_l = pv.tolist()
    pvv_l = pvv.tolist()
    vdel = (sum(pv_l) / W16) - (sum(pvv_l) / W16)
    # NOTE: vendor line 333 semantics kept verbatim: gap is anchored to
    # bars[t] (not t+off) even in future-mutation mode.
    gap = float(a_o[t]) - float(a_c[t - 1])
    feats = [_sign(rets[0]), _sign(rets[1]), _sign(rets[2]), _sign(rets[3]),
             _sign(pos, 0.85), _sign(rexp, 1.0), _sign(vdel), _sign(gap)]

    cl_l = cl.tolist()
    pcl_l = pcl.tolist()
    ra0 = sum(abs(cl_l[i] / cl_l[i - 1] - 1.0) for i in range(1, W16)) / (W16 - 1)
    rp0 = sum(abs(pcl_l[i] / pcl_l[i - 1] - 1.0) for i in range(1, W16)) / (W16 - 1)
    ra = (ra0 / rp0) if rp0 > 1e-9 else 1.0
    rr = rexp
    rv = (sum(pv_l) / sum(pvv_l)) if sum(pvv_l) > 1e-9 else 1.0
    rg = abs(gap) / (cl[-1] * 0.002)
    flag = (not (FLAG["rv"][0] <= rv <= FLAG["rv"][1])
            or rg >= FLAG["rg"])
    stats = {"ra": float(np.round(ra, 4)), "rr": float(np.round(rr, 4)),
             "rv": float(np.round(rv, 4)), "rg": float(np.round(rg, 3))}
    return feats, bool(flag), stats


def quantize_many(o, h, l, c, v, t_values, audit: Optional[AdapterAudit] = None,
                  future: bool = False):
    """Vectorized loop over t values; deterministic; returns arrays."""
    feats = np.empty((len(t_values), 8), dtype=np.int8)
    flags = np.empty(len(t_values), dtype=bool)
    for i, t in enumerate(t_values):
        f, flag, _ = quantize_window(o, h, l, c, v, int(t), audit, future)
        feats[i] = f
        flags[i] = flag
    return feats, flags
