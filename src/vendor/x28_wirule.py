"""X28 -- WiRULE, our own weightless network (derivation.md section 61).

Knowledge = 64 literal-addressed counters written by feedback (weightless
family: Tsetlin-counter / WiSARD-RAM lineage, no optimization, no
derivatives). The rule is REGENERATED at readout from evidence
e(lit) = c[+][lit] - c[-][lit] (top ARITY = 3 slots) and applied as an
exact match -- the L0/M0 law (rules applied at readout), and the measured
fix for X27's refusal anatomy (negatives of a conjunction can never
clear a negative margin).

Gates (frozen 61.2):
    G1 barrier: while state-carried t < E_MIN = 500 -> refuse all.
    Confidence: every rule literal e >= E_LIT = 64 AND
                e(3rd) - e(4th) >= SEP_MIN = 64, else refuse all.
    Readout:    m == 3 -> +1 ; m <= 2 -> -1 ; (confidence failure -> refuse)

Bars are copied from derivation 61.4 verbatim. Population is imported
from the X20 runner (61.3: identical to X20-X27 by construction).

Run:
  .venv/Scripts/python.exe experiments/x28_wirule.py --smoke
  .venv/Scripts/python.exe experiments/x28_wirule.py
"""

from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from paths import RESULTS, LEDGER, ensure_dirs  # noqa: E402
from clay import (  # noqa: E402
    Clay,
    CLAY_BYTES,
    atom,
    codebook,
    fields_to_vectors,
    roles_vector,
)

from x20_learn_probe import (  # noqa: E402
    N_BITS,
    CHECKPOINTS,
    make_stream,
    make_heldout,
    hidden_rule,
)

RESULT_PATH = os.path.join(RESULTS, "x28_wirule.json")
SMOKE_PATH = os.path.join(RESULTS, "x28_wirule_smoke.json")

# -- frozen constants (61.2) ------------------------------------------------------
N_LIT = 2 * N_BITS              # 32 literal slots
ARITY = 3                       # frozen-population constant (disclosed)
C_CAP = 511                     # counter cap: refuse, never saturate
E_MIN = 500                     # G1 barrier (X26/X27 continuity)
E_LIT = 64                      # min evidence per rule literal (~4 sigma)
SEP_MIN = 64                    # min gap e(3rd) - e(4th)
BARRIER_IDX = 64                # fields: 64 counters, then t
FIELD_TOTAL = 72                # 65 + 7 pad = 9 clay shapes of 8
SPEC_BYTES = 132                # 64 x int16 + int32 t

ARM_NAME = "WiRULE"
MODES = ("main", "flip")
SEEDS = (1, 2, 3)
HELDOUT_POS = HELDOUT_NEG = 250
N_ROLES, N_FILLERS, Z_DECODE = 8, 1024, 5.5

BAR_TEXT = ("X28-1 wrong 0 in mains; X28-2 acc@1000 >= 0.90; X28-3 spec "
            "132 constant; X28-4 digest H0 + roundtrip incl. barrier; "
            "X28-5 undo; X28-6 gain >= 0.30 (pre-data: implied by X28-2 "
            "under G1); X28-7 flip <= 0.10 or drop >= 0.15; X28-8 medians + "
            "extraction diagnostic published; probe: k in {0,10,100} "
            "emissions 0")


def sat_lits(x: list[int]) -> list[int]:
    return ([i for i in range(N_BITS) if x[i] == 1]
            + [N_BITS + i for i in range(N_BITS) if not x[i]])


def true_rule_lits(seed: int) -> list[int]:
    """Literal slots of the seed's hidden conjunction (diagnostic only)."""
    on, off = hidden_rule(seed)
    return sorted([on[0], on[1], N_BITS + off[0]])


class WiRULE:
    name = ARM_NAME

    def __init__(self):
        # plane 0 = class +1, plane 1 = class -1; slot i = x_i,
        # slot 32+i = NOT x_i (61.2)
        self.c = [[0] * N_LIT for _ in range(2)]
        self.t = 0
        self.refused_updates = 0

    def state_bytes(self) -> int:
        return SPEC_BYTES

    def update(self, x: list[int], y: int) -> None:
        ci = 0 if y == 1 else 1
        for lit in sat_lits(x):
            if self.c[ci][lit] < C_CAP:
                self.c[ci][lit] += 1
            else:
                self.refused_updates += 1     # refuse, never saturate
        self.t += 1

    def fields(self) -> list[int]:
        flat = list(self.c[0]) + list(self.c[1]) + [self.t]
        while len(flat) < FIELD_TOTAL:
            flat.append(0)
        return flat

    # -- readout (from DECODED state only) ---------------------------------

    @staticmethod
    def _extract(raw: list[int]) -> tuple[list[int], list[int]]:
        """(rule slots sorted, evidence vector) from decoded counters."""
        e = [raw[i] - raw[N_LIT + i] for i in range(N_LIT)]
        top = sorted(range(N_LIT), key=lambda i: (-e[i], i))[:ARITY + 1]
        return sorted(top[:ARITY]), e

    @staticmethod
    def _confident(rule: list[int], e: list[int]) -> bool:
        if min(e[i] for i in rule) < E_LIT:
            return False
        ordered = sorted(range(N_LIT), key=lambda i: (-e[i], i))
        return (e[ordered[ARITY - 1]] - e[ordered[ARITY]]) >= SEP_MIN

    def predict(self, x: list[int], raw: list[int] | None) -> int | None:
        if raw is None or None in raw:
            return None
        if raw[BARRIER_IDX] < E_MIN:          # G1 barrier
            return None
        rule, e = self._extract(raw)
        if not self._confident(rule, e):      # native confidence (61.2)
            return None
        active = set(sat_lits(x))
        m = sum(1 for lit in rule if lit in active)
        if m == ARITY:                        # all rule literals satisfied
            return 1
        return -1                             # >= 1 violated

    def extract_diag(self, raw: list[int] | None) -> dict:
        if raw is None or None in raw:
            return {"extracted_rule": None, "confident": False}
        rule, e = self._extract(raw)
        return {"extracted_rule": rule,
                "evidence_at_rule": [e[i] for i in rule],
                "confident": self._confident(rule, e)}


_CB_T = None
_ROLES = None


def _setup_clay():
    global _ROLES, _CB_T
    if _ROLES is None:
        _ROLES = roles_vector("role:", N_ROLES)
        _CB_T = codebook("f:", N_FILLERS, transposed=True)


def roundtrip(arm: WiRULE, clay: Clay, seed: int, k: int, mode: str) -> tuple[bool, list]:
    """All 72 fields incl. barrier t (X28-4): write -> decode -> verify,
    erase (keys namespaced x28:)."""
    fields = arm.fields()
    assert len(fields) % N_ROLES == 0, len(fields)
    n_shapes = len(fields) // N_ROLES
    decoded: list[int] = []
    exact = True
    for j in range(n_shapes):
        chunk = fields[j * N_ROLES:(j + 1) * N_ROLES]
        key = atom(f"x28:wirule:{mode}:s{seed}:k{k}:sh{j}")
        fillers = fields_to_vectors(_CB_T, chunk, n_entries=N_FILLERS)
        clay.write(key, _ROLES, fillers)
        rep = clay.decode(key, _ROLES, _CB_T, z_thr=Z_DECODE, transposed=True)
        for idx, _, _z in rep:
            if idx is None:
                exact = False
                decoded.append(None)
            else:
                decoded.append(int(idx))
        clay.erase(key, _ROLES, fillers)
    return exact, decoded


def classify(arm: WiRULE, heldout: list, raw: list[int] | None) -> dict:
    """Always from the DECODED state; refused field -> refused vector.
    Latency = MEDIAN ms per classification (X28-8)."""
    exact = refused = wrong = 0
    times: list[float] = []
    for x, y in heldout:
        t0 = time.perf_counter()
        p = arm.predict(x, raw)
        times.append((time.perf_counter() - t0) * 1000.0)
        if p is None:
            refused += 1
        elif p == y:
            exact += 1
        else:
            wrong += 1
    times.sort()
    ms = times[len(times) // 2] if times else 0.0
    return {"exact": exact, "refused": refused, "wrong": wrong,
            "total": len(heldout),
            "accuracy": round(exact / len(heldout), 5),
            "ms_per_classify": round(ms, 5)}


def run_arm(mode: str, seed: int, cps: tuple, heldout: list) -> list[dict]:
    rows = []
    for k in cps:
        arm = WiRULE()
        upd_times: list[float] = []
        for x, y in (make_stream(seed, k) if k else []):
            t0 = time.perf_counter()
            arm.update(x, -y if mode == "flip" else y)   # 61.3 label flip
            upd_times.append((time.perf_counter() - t0) * 1000.0)
        upd_times.sort()
        upd_ms = upd_times[len(upd_times) // 2] if upd_times else 0.0

        h0 = Clay().digest()
        clay = Clay()
        rt_exact, decoded = roundtrip(arm, clay, seed, k, mode)
        digest_rest = clay.digest() == h0

        scored = classify(arm, heldout, decoded)
        diag = arm.extract_diag(decoded)
        true_rule = true_rule_lits(seed)
        rows.append({
            "seed": seed, "arm": ARM_NAME, "mode": mode, "k": k,
            "state_spec_bytes": arm.state_bytes(),
            "roundtrip_exact": rt_exact,
            "digest_rest_H0": digest_rest,
            "clay_bytes": CLAY_BYTES,
            "ms_per_update": round(upd_ms, 6),
            "refused_updates": arm.refused_updates,
            "true_rule": true_rule,
            "rule_match": diag.get("extracted_rule") == true_rule,
            "confident": diag.get("confident", False),
            "extracted_rule": diag.get("extracted_rule"),
            **scored,
        })
    return rows


heldout_cache: dict[int, list] = {}


def run(*, smoke: bool = False) -> dict:
    ensure_dirs()
    _setup_clay()
    t0 = time.perf_counter()
    seeds = (1,) if smoke else SEEDS
    cps = (0, 10) if smoke else CHECKPOINTS

    for s in seeds:
        forbid: set = set()
        for k in cps:
            for x, _y in make_stream(s, k):
                forbid.add(tuple(x))
        heldout_cache[s] = make_heldout(s, forbid)

    label = "X28 smoke" if smoke else "X28 WiRULE weightless gate"
    print(f"== {label} (seeds {seeds}, checkpoints {cps}) ==", flush=True)

    rows: list[dict] = []
    for mode in MODES:
        for seed in seeds:
            rows.extend(run_arm(mode, seed, cps, heldout_cache[seed]))
        print(f"   {mode} done", flush=True)

    mains = [r for r in rows if r["mode"] == "main"]
    flips = [r for r in rows if r["mode"] == "flip"]
    last_k = max(cps)

    def mean_at(rs: list, k: int) -> float:
        vals = [r["accuracy"] for r in rs if r["k"] == k]
        return round(sum(vals) / len(vals), 5) if vals else 0.0

    acc1000 = mean_at(mains, last_k)
    acc10 = mean_at(mains, 10) if 10 in cps else 0.0
    flip1000 = mean_at(flips, last_k)
    k1000 = [r for r in mains if r["k"] == last_k]
    exact1000 = sum(r["exact"] for r in k1000)
    refused1000 = sum(r["refused"] for r in k1000)

    mains_wrong = sum(r["wrong"] for r in mains)
    early = [r for r in mains if r["k"] < E_MIN]
    early_emissions = sum(r["exact"] + r["wrong"] for r in early)

    spec_constant = all(r["state_spec_bytes"] == SPEC_BYTES for r in rows)
    digest_all = all(r["digest_rest_H0"] for r in rows)
    roundtrip_all = all(r["roundtrip_exact"] for r in rows)

    # extraction diagnostic (X28-8): k = last_k rows, both modes
    extraction = {
        mode: {str(s): {
            "extracted": next((r["extracted_rule"] for r in rows
                               if r["mode"] == mode and r["seed"] == s
                               and r["k"] == last_k), None),
            "true": true_rule_lits(s),
            "match": next((r["rule_match"] for r in rows
                           if r["mode"] == mode and r["seed"] == s
                           and r["k"] == last_k), None),
            "confident": next((r["confident"] for r in rows
                               if r["mode"] == mode and r["seed"] == s
                               and r["k"] == last_k), None),
        } for s in seeds}
        for mode in MODES
    }

    x28_1 = mains_wrong == 0
    x28_2 = True if smoke else (acc1000 >= 0.90)
    x28_3 = spec_constant
    x28_4 = digest_all and roundtrip_all
    x28_5 = digest_all
    x28_6 = True if smoke else (acc1000 - acc10 >= 0.30)
    x28_7 = bool(flip1000 <= 0.10
                 or round(acc1000 - flip1000, 5) >= 0.15)
    x28_8 = all("ms_per_classify" in r and "ms_per_update" in r
                for r in rows)
    probe_ok = (early_emissions == 0)

    overall = all([x28_1, x28_2, x28_3, x28_4, x28_5, x28_6, x28_7, x28_8,
                   probe_ok])
    elapsed = time.perf_counter() - t0

    result = {
        "gate": "X28",
        "namespace": "goal_gates",
        "question": "does WiRULE -- our own weightless network (literal "
                    "counters + regenerated rule + confidence-gated rule "
                    "match) -- reach wrong 0 and >= 0.90 on the frozen "
                    "population?",
        "bar": BAR_TEXT,
        "spec": "derivation.md section 61 (bars and constants frozen "
                "2026-10-17 before any runner existed; owner: 'create our "
                "own Version of Weightless Neural Network ... pass all the "
                "requirements')",
        "date": "2026-10-17",
        "design": {
            "mechanism": "2 class-planes x 32 literal slots, feedback "
                         "counts (cap 511 refuse), rule regenerated at "
                         "readout as top-3 evidence slots, exact-match "
                         "emission under confidence gates",
            "constants": {"C_CAP": C_CAP, "E_MIN": E_MIN, "ARITY": ARITY,
                          "E_LIT": E_LIT, "SEP_MIN": SEP_MIN},
            "checkpoints": list(cps), "heldout": HELDOUT_POS + HELDOUT_NEG,
            "population": "imported from experiments/x20_learn_probe.py",
            "mutation": "label flip y -> -y on training (61.3)",
            "disclosure": "frozen conjunction family, known ARITY 3 "
                          "(61.5); X28-6 implied by X28-2 under G1 (61.4)",
        },
        "bars": {
            "X28_1_wrong0": x28_1, "X28_2_generalization": x28_2,
            "X28_3_fixed_state": x28_3, "X28_4_clay_discipline": x28_4,
            "X28_5_undo": x28_5, "X28_6_learning_real": x28_6,
            "X28_7_label_flip_reads": x28_7, "X28_8_published": x28_8,
            "probe_barrier_compliance": probe_ok,
        },
        "acc_at_1000": acc1000, "acc_at_10": acc10,
        "flip_acc_at_1000": flip1000,
        "exact_at_1000": exact1000, "refused_at_1000": refused1000,
        "probe_emissions_k_lt_500": early_emissions,
        "extraction": extraction,
        "comparison": {"X20": 0.5013, "X21": 0.5247, "X22": 0.0027,
                       "X23": 0.0073, "X24": 0.3353,
                       "X25_DWN": 0.4420, "X25_WINNOW": 0.3647,
                       "X25_BLOOM": 0.2093, "X25_TM": 0.3353,
                       "X26_VOTE": 0.6060, "X27_VOTE_W": 0.6927,
                       "note": "landed acc@1000 values, published per 61.4"},
        "exception": "none: no gradient method anywhere in this gate",
        "rows": rows,
        "PASS": overall,
        "elapsed_s": round(elapsed, 1),
        "env": {"python": sys.version.split()[0]},
    }

    path = SMOKE_PATH if smoke else RESULT_PATH
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)

    if not smoke:
        with open(LEDGER, encoding="utf-8") as fh:
            led = json.load(fh)
        led.setdefault("goal_gates", {})
        led["goal_gates"]["X28"] = {
            "gate": "X28", "namespace": "goal_gates",
            "question": result["question"], "bar": BAR_TEXT,
            "constants": result["design"]["constants"],
            "seeds": len(seeds), "checkpoints": list(cps),
            "mains_wrong_total": mains_wrong,
            "acc_at_1000": acc1000, "flip_acc_at_1000": flip1000,
            "exact_at_1000": exact1000, "refused_at_1000": refused1000,
            "probe_emissions_k_lt_500": early_emissions,
            "extraction": extraction,
            "digest_rest_H0": digest_all,
            "roundtrip_exact": roundtrip_all,
            "PASS": overall,
        }
        with open(LEDGER, "w", encoding="utf-8") as fh:
            json.dump(led, fh, indent=2)

    print(f"\nextraction diagnostic (k={last_k}):", flush=True)
    for mode in MODES:
        for s in seeds:
            d = extraction[mode][str(s)]
            print(f"   {mode:4} seed {s}: extracted {d['extracted']} "
                  f"true {d['true']} match={d['match']} "
                  f"confident={d['confident']}", flush=True)

    print(f"\nX28 {'PASS' if overall else 'FAIL'} - mains wrong "
          f"{mains_wrong} | acc@1000 {acc1000:.4f} (exact {exact1000}/1500, "
          f"refused {refused1000}) | flip {flip1000:.4f} | k<500 emissions "
          f"{early_emissions} | spec {spec_constant} | digest {digest_all} "
          f"| roundtrip {roundtrip_all}", flush=True)
    if not smoke:
        print(f"wrote {RESULT_PATH} and ledger goal_gates.X28 "
              f"in {elapsed:.1f}s")
    return 0 if overall else 1


def main() -> int:
    return run(smoke="--smoke" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())
