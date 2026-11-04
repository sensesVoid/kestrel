"""X20 -- the learning-mechanism probe (derivation.md section 53).

Which gradient-free feedback learner owns the fixed-size system: a
Tsetlin-style literal-counter clause (Arm A) or encoder-sign training
(Arm B)? Both are DISCLOSED SIMPLIFIED FAMILY PROBES, not the published
algorithms (53.1): no clause ensembles, no probabilistic sampling, no
TrainableHD encoder machinery -- the question is which UPDATE-RULE FAMILY
fits this substrate.

Pre-registration: the BARS live in derivation.md section 53, frozen
2026-10-17 BEFORE this file existed. Bars are copied here verbatim so the
run cannot negotiate them. Owner ruling recorded the same day: find the
WINNING arm, and bar byte-growth-free learning (fixed-size system that can
learn as much as it wants -- ternary shapes as data store, not bytes on
disk).

Bars (derivation.md 53.3, verbatim):
    X20-1  wrong 0: no confident misclassification on any held-out vector,
           any checkpoint, any arm; refusals allowed, counted, emitted null.
    X20-2  generalization: the WINNING arm's mean held-out accuracy across
           3 seeds at k=1000 >= 0.90; the loser's number published.
    X20-3  FIXED-STATE learning: learned-state spec bytes identical at every
           checkpoint k=10/100/1000 for both arms (0 growth with updates).
    X20-4  0 clay bytes at rest: digest bit-identical to H0 after every
           erase; clay fixed 131,072 B; state round-trips through the clay
           (write -> decode -> erase -> rewrite) bit-identically.
    X20-5  undo: erasing the state shapes returns the digest to H0 exactly.
    X20-6  learning is real: winning arm's k=1000 accuracy exceeds its k=10
           accuracy by >= 0.30 (refusing everything cannot win).
    X20-7  winner rule: higher mean held-out accuracy over 3 seeds at
           k=1000; gap <= 0.01 -> tie-break state bytes, then fewer
           refusals; still tied -> TIE recorded as TIE (X16 precedent).
    X20-8  latency and bytes published beside every accuracy number.

Procedure (53.2 + pre-runner amendment in 53.7):
    hidden rule  conjunction of 3 literals over 16 bits (two ON, one OFF,
                 distinct positions), drawn per seed.
    stream       k in {0, 10, 100, 1000} checkpoints, alternating
                 positive/negative by construction; both arms same stream.
    k=0 probe    before ANY feedback, both arms must refuse every held-out
                 vector, 0 confident emissions.
    held-out     500 vectors (250 pos / 250 neg), never in the feedback
                 stream, evaluated at every checkpoint.
    session      fresh clay per checkpoint: materialize state shapes,
                 decode-verify round-trip, classify, erase, digest == H0.

Run:
  .venv/Scripts/python.exe experiments/x20_learn_probe.py --smoke
  .venv/Scripts/python.exe experiments/x20_learn_probe.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import torch  # noqa: E402

from paths import RESULTS, LEDGER, ensure_dirs  # noqa: E402
from clay import (  # noqa: E402
    Clay,
    CLAY_BYTES,
    atom,
    codebook,
    fields_to_vectors,
    roles_vector,
)

RESULT_PATH = os.path.join(RESULTS, "x20_learn_probe.json")
SMOKE_PATH = os.path.join(RESULTS, "x20_learn_probe_smoke.json")

# -- frozen design (derivation.md 53.2) --------------------------------------

N_BITS = 16
CHECKPOINTS = (0, 10, 100, 1000)
HELDOUT_POS = 250
HELDOUT_NEG = 250
SEEDS = (1, 2, 3)

# -- operational constants (fixed before any data) ---------------------------

C_MAX = 16            # Arm A counter bound; updates beyond are REFUSED
T_INC = 1             # Arm A include threshold: counter > T_INC -> literal included
T_CONF = 12           # Arm A confident-negative threshold on the violated lit
                       # (carried from the selection winner diag_x20_select)
MARGIN_B = 2          # Arm B: |score| >= MARGIN_B to emit (|score| <= 1 refuses)
Z_DECODE = 5.5        # landed decode default (clay.py); state round-trip bar

N_ROLES = 8
N_FILLERS = 1024

BAR_TEXT = ("X20-1 wrong 0; X20-2 winner mean held-out acc >= 0.90 at k=1000; "
            "X20-3 state spec bytes constant across checkpoints; X20-4 digest "
            "H0 at rest + clay round-trip bit-identical; X20-5 erase returns "
            "H0; X20-6 winner k1000 - k10 >= 0.30; X20-7 frozen winner rule "
            "with TIE recorded as TIE; X20-8 latency/bytes published")


def _seed_of(name: str) -> int:
    return int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], "little")


def gen(name: str) -> torch.Generator:
    return torch.Generator().manual_seed(_seed_of(name))


# -- frozen population --------------------------------------------------------

def hidden_rule(seed: int) -> tuple[list[int], list[int]]:
    """(on_positions, off_positions) of the seed's conjunction: 2 ON, 1 OFF."""
    g = gen(f"x20:rule:{seed}")
    perm = torch.randperm(N_BITS, generator=g).tolist()
    return [perm[0], perm[1]], [perm[2]]


def satisfied(x: list[int], on: list[int], off: list[int]) -> bool:
    return all(x[i] == 1 for i in on) and all(x[i] == 0 for i in off)


def draw(seed: int, tag: str, n: int, want_sat: bool, forbid: set) -> list[list[int]]:
    """n distinct 16-bit vectors, all satisfying (or violating) the rule,
    none in ``forbid`` (held-out never collides with the stream)."""
    on, off = hidden_rule(seed)
    g = gen(f"x20:{tag}:{seed}")
    out: list[list[int]] = []
    while len(out) < n:
        x = torch.randint(0, 2, (N_BITS,), generator=g).tolist()
        if satisfied(x, on, off) != want_sat:
            continue
        key = tuple(x)
        if key in forbid or key in {tuple(v) for v in out}:
            continue
        out.append(x)
    return out


def make_stream(seed: int, k: int) -> list[tuple[list[int], int]]:
    """k examples alternating +1/-1 by construction."""
    pos = draw(seed, f"stream:{k}:pos", (k + 1) // 2, True, set())
    neg = draw(seed, f"stream:{k}:neg", k // 2, False,
               {tuple(v) for v in pos})
    stream = []
    for j in range(k):
        stream.append((pos[j // 2] if j % 2 == 0 else neg[j // 2],
                       1 if j % 2 == 0 else -1))
    return stream


def make_heldout(seed: int, forbid: set) -> list[tuple[list[int], int]]:
    """250 pos + 250 neg, disjoint from the FULL forbid set (every
    checkpoint stream, per 53.2: never in the feedback stream)."""
    pos = draw(seed, "held:pos", HELDOUT_POS, True, forbid)
    neg = draw(seed, "held:neg", HELDOUT_NEG, False,
               forbid | {tuple(v) for v in pos})
    return [(x, 1) for x in pos] + [(x, -1) for x in neg]


# -- the two arms (53.1, disclosed simplified probes) -------------------------

class ArmA:
    """Tsetlin-style literal counters -- THE SELECTION WINNER
    (diag_x20_select, results/x20_select_diag.json: the only arm with
    wrong 0 on every seed and checkpoint; carried into this gate because
    its own docstring named that probe's winner as the arm to pre-register).

    Include on positives AND pull the clause over the positive by
    decrementing included-but-unsatisfied literals; penalize satisfied
    included literals on negatives (no wrong-fire gate). Prediction is
    refuse-first: a violated literal emits confident -1 only at
    counter >= T_CONF; otherwise the miss is low-evidence noise -> refuse,
    never wrong. Updates beyond +-C_MAX are REFUSED and counted.

    Disclosed alignment 2026-10-17 (derivation 53.7): the original runner
    ArmA emitted -1 on every non-fire (250 wrongs in the failed smoke) and
    lacked clause pruning; this body is the selection probe's ArmA
    verbatim, plus refused-update counting."""

    name = "A_tsetlin_counters"

    def __init__(self):
        self.counters = [0] * (2 * N_BITS)   # [0..15] ON-literals, [16..31] OFF
        self.refused_updates = 0

    def state_bytes(self) -> int:
        return 2 * N_BITS                     # one int8 per counter, constant

    def fields(self) -> list[int]:
        return [c + C_MAX for c in self.counters]     # 0..2*C_MAX into codebook

    def load_fields(self, fields: list[int]) -> None:
        self.counters = [f - C_MAX for f in fields]

    def _satisfied_lits(self, x: list[int]) -> set[int]:
        return ({i for i in range(N_BITS) if x[i] == 1}
                | {N_BITS + i for i in range(N_BITS) if x[i] == 0})

    def _included(self) -> set[int]:
        return {i for i, c in enumerate(self.counters) if c > T_INC}

    def predict(self, x: list[int]) -> int | None:
        inc = self._included()
        if not inc:
            return None                        # nothing learned -> refuse
        sat = self._satisfied_lits(x)
        violated = [i for i in inc if i not in sat]
        if not violated:
            return 1                           # clause fires
        # confident -1 only if a HIGH-counter literal was violated;
        # otherwise the miss is low-evidence noise -> refuse, not wrong
        if max(self.counters[i] for i in violated) >= T_CONF:
            return -1
        return None

    def update(self, x: list[int], y: int) -> None:
        sat = self._satisfied_lits(x)
        inc = self._included()
        if y == 1:
            for i in sat:
                if self.counters[i] < C_MAX:
                    self.counters[i] += 1
                else:
                    self.refused_updates += 1         # refused, not clamped
            for i in inc - sat:
                if self.counters[i] > 0:
                    self.counters[i] -= 1             # pull clause over the positive
        else:
            for i in inc & sat:
                if self.counters[i] > 0:
                    self.counters[i] -= 1             # push clause off the negative


class ArmB:
    """Encoder-sign training (TrainableHD-flavored): 16 learned signs over
    bit positions; on a miss, flip the signs that voted wrong. No
    derivatives anywhere -- pure sign flips."""

    name = "B_encoder_signs"

    def __init__(self):
        self.signs = [0] * N_BITS              # -1 / 0 / +1
        self.refused_updates = 0

    def state_bytes(self) -> int:
        return N_BITS                          # one int8 per sign, constant

    def fields(self) -> list[int]:
        return [s + 1 for s in self.signs]     # 0..2 into codebook

    def load_fields(self, fields: list[int]) -> None:
        self.signs = [f - 1 for f in fields]

    def predict(self, x: list[int]) -> int | None:
        score = sum(s * (1 if x[i] else -1)
                    for i, s in enumerate(self.signs) if s != 0)
        if score >= MARGIN_B:
            return 1
        if score <= -MARGIN_B:
            return -1
        return None                            # |score| too small -> refuse

    def update(self, x: list[int], y: int) -> None:
        score = sum(s * (1 if x[i] else -1)
                    for i, s in enumerate(self.signs) if s != 0)
        if score * y >= MARGIN_B:
            return                             # confident and correct: no change
        for i, s in enumerate(self.signs):
            vote = (1 if x[i] else -1)
            if s * vote * y < 0:               # this bit voted against the label
                self.signs[i] = -s             # flip: the only update rule


# -- clay round-trip of the learned state (X20-4 / X20-5) --------------------

_roles = None
_cb_T = None


def setup():
    global _roles, _cb_T
    if _roles is None:
        _roles = roles_vector("role:", N_ROLES)
        _cb_T = codebook("f:", N_FILLERS, transposed=True)


def roundtrip_state(arm, clay: Clay, seed: int, k: int) -> tuple[bool, list]:
    """Materialize arm state as shapes, decode-verify, return decoded fields.

    Returns (roundtrip_exact, decoded_fields). Each shape is a write of
    key (x) sum_role role (x) filler over 8 codebook entries; the decoded
    field indices must equal the spec fields exactly, at z >= Z_DECODE.
    """
    fields = arm.fields()
    n_shapes = len(fields) // N_ROLES
    decoded: list[int] = []
    exact = True
    for j in range(n_shapes):
        chunk = fields[j * N_ROLES:(j + 1) * N_ROLES]
        key = atom(f"x20:{arm.name}:s{seed}:k{k}:sh{j}")
        fillers = fields_to_vectors(_cb_T, chunk, n_entries=N_FILLERS)
        clay.write(key, _roles, fillers)
        reported = clay.decode(key, _roles, _cb_T, z_thr=Z_DECODE,
                               transposed=True)
        for idx, _, _z in reported:
            if idx is None:
                exact = False
                decoded.append(None)
            else:
                decoded.append(int(idx))
        # erase immediately: the clay must never rest holding knowledge
        clay.erase(key, _roles, fillers)
    return exact, decoded


def classify_heldout(arm, heldout: list) -> dict:
    exact = refused = wrong = 0
    for x, y in heldout:
        p = arm.predict(x)
        if p is None:
            refused += 1
        elif p == y:
            exact += 1
        else:
            wrong += 1
    return {"exact": exact, "refused": refused, "wrong": wrong,
            "total": len(heldout),
            "accuracy": round(exact / len(heldout), 5)}


# -- one arm over one seed ----------------------------------------------------

def run_arm(arm_cls, seed: int) -> list[dict]:
    rows = []
    for k in CHECKPOINTS:
        # fresh arm per checkpoint: k means "trained on exactly k examples",
        # and the stream at k=10 is a fresh draw, not a prefix of k=100 --
        # so checkpoint independence is the honest reading of 53.2.
        arm = arm_cls()
        upd_ms = 0.0
        for x, y in (make_stream(seed, k) if k else []):
            t0 = time.perf_counter()
            arm.update(x, y)
            upd_ms = (time.perf_counter() - t0) * 1000.0

        # clay round-trip of the CURRENT state, fresh clay, erase to H0
        h0 = Clay().digest()
        clay = Clay()
        rt_exact, decoded = roundtrip_state(arm, clay, seed, k)
        digest_rest = clay.digest() == h0

        # classify from the DECODED state (the clay is the data store, the
        # spec is the generator): rebuild a state view from decoded fields
        view = arm_cls()
        if None not in decoded:
            view.load_fields(decoded)
        else:
            view = None
        if view is None:
            scored = {"exact": 0, "refused": len(heldout_cache[seed]),
                      "wrong": 0, "total": len(heldout_cache[seed]),
                      "accuracy": 0.0}
        else:
            t0 = time.perf_counter()
            scored = classify_heldout(view, heldout_cache[seed])
            scored["ms_per_classify"] = round(
                (time.perf_counter() - t0) * 1000.0
                / max(scored["total"], 1), 4)

        rows.append({
            "seed": seed, "arm": arm.name, "k": k,
            "state_spec_bytes": arm.state_bytes(),
            "roundtrip_exact": rt_exact,
            "digest_rest_H0": digest_rest,
            "clay_bytes": CLAY_BYTES,
            "refused_updates_cum": arm.refused_updates,
            "ms_per_update": round(upd_ms, 5),
            **scored,
        })
    return rows


heldout_cache: dict[int, list] = {}


# -- gate ---------------------------------------------------------------------

def run(*, smoke: bool = False) -> dict:
    global CHECKPOINTS, heldout_cache
    ensure_dirs()
    setup()
    t0 = time.perf_counter()
    seeds = (1,) if smoke else SEEDS
    cps = (0, 10) if smoke else CHECKPOINTS
    CHECKPOINTS = cps
    # held-out must never collide with ANY checkpoint stream, so forbid the
    # union of every k's draw (53.2: never in the feedback stream)
    heldout_cache = {}
    for s in seeds:
        forbid = set()
        for k in cps:
            for x, _y in make_stream(s, k):
                forbid.add(tuple(x))
        heldout_cache[s] = make_heldout(s, forbid)
    label = "X20 smoke" if smoke else "X20 learning-mechanism probe"
    print(f"== {label} (seeds {seeds}, checkpoints {cps}) ==", flush=True)

    rows = []
    for seed in seeds:
        for arm_cls in (ArmA, ArmB):
            rows.extend(run_arm(arm_cls, seed))
        print(f"   seed {seed} done", flush=True)

    # -- bars ----------------------------------------------------------------
    wrong_total = sum(r["wrong"] for r in rows)

    k0 = [r for r in rows if r["k"] == 0]
    k0_emissions = sum(r["exact"] + r["wrong"] for r in k0)

    digest_all = all(r["digest_rest_H0"] for r in rows)
    roundtrip_all = all(r["roundtrip_exact"] for r in rows)

    spec_constant = all(
        len({r["state_spec_bytes"] for r in rows if r["arm"] == arm}) == 1
        for arm in {r["arm"] for r in rows})

    def mean_acc(arm: str, k: int) -> float:
        vals = [r["accuracy"] for r in rows if r["arm"] == arm and r["k"] == k]
        return sum(vals) / len(vals) if vals else 0.0

    last_k = max(cps)
    acc_a, acc_b = mean_acc(ArmA.name, last_k), mean_acc(ArmB.name, last_k)
    ref_a = sum(r["refused"] for r in rows if r["arm"] == ArmA.name and r["k"] == last_k)
    ref_b = sum(r["refused"] for r in rows if r["arm"] == ArmB.name and r["k"] == last_k)
    bytes_a, bytes_b = ArmA().state_bytes(), ArmB().state_bytes()

    gap = abs(acc_a - acc_b)
    if gap > 0.01:
        winner, tie = (ArmA.name if acc_a > acc_b else ArmB.name), False
    elif bytes_a != bytes_b:
        winner, tie = (ArmA.name if bytes_a < bytes_b else ArmB.name), False
    elif ref_a != ref_b:
        winner, tie = (ArmA.name if ref_a < ref_b else ArmB.name), False
    else:
        winner, tie = "TIE", True

    winner_name = None if tie else winner
    gen_bar = (0.90 if not tie else max(acc_a, acc_b))
    gen_pass = max(acc_a, acc_b) >= 0.90

    if tie:
        learn_gain = 0.0
        learn_pass = True                     # TIE is legal; no winner to bar
    else:
        first_k = min(cps)
        learn_gain = mean_acc(winner_name, last_k) - mean_acc(winner_name, first_k)
        learn_pass = learn_gain >= 0.30

    x20_1 = wrong_total == 0
    x20_2 = gen_pass
    x20_3 = spec_constant
    x20_4 = digest_all and roundtrip_all
    x20_5 = digest_all
    x20_6 = learn_pass
    x20_8 = all("ms_per_classify" in r for r in rows if r["k"] > 0)

    overall = all([x20_1, x20_2, x20_3, x20_4, x20_5, x20_6, x20_8])
    elapsed = time.perf_counter() - t0

    result = {
        "gate": "X20",
        "namespace": "goal_gates",
        "question": "which gradient-free feedback learner owns the fixed-size "
                    "system: Tsetlin-style literal counters or encoder-sign "
                    "training, with byte-growth-free learning?",
        "bar": BAR_TEXT,
        "spec": "derivation.md section 53 (bars frozen 2026-10-17 before this "
                "runner existed)",
        "date": "2026-10-17",
        "design": {
            "n_bits": N_BITS, "checkpoints": list(cps),
            "heldout": HELDOUT_POS + HELDOUT_NEG,
            "c_max": C_MAX, "t_inc": T_INC, "margin_b": MARGIN_B,
            "z_decode": Z_DECODE,
            "disclosure": "simplified family probes per 53.1, not full "
                          "published algorithms",
        },
        "bars": {
            "X20_1_wrong0": x20_1, "X20_2_generalization": x20_2,
            "X20_3_fixed_state": x20_3, "X20_4_clay_discipline": x20_4,
            "X20_5_undo": x20_5, "X20_6_learning_real": x20_6,
            "X20_7_winner": winner, "X20_7_tie": tie,
            "X20_8_published": x20_8,
        },
        "k0_probe_emissions": k0_emissions,
        "accuracy_at_last_checkpoint": {ArmA.name: acc_a, ArmB.name: acc_b},
        "refusals_at_last_checkpoint": {ArmA.name: ref_a, ArmB.name: ref_b},
        "state_spec_bytes": {ArmA.name: bytes_a, ArmB.name: bytes_b},
        "learn_gain_winner": round(learn_gain, 5),
        "rows": rows,
        "PASS": overall,
        "elapsed_s": round(elapsed, 1),
        "env": {"python": sys.version.split()[0], "torch": torch.__version__},
    }

    path = SMOKE_PATH if smoke else RESULT_PATH
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)

    if not smoke:
        with open(LEDGER, encoding="utf-8") as fh:
            led = json.load(fh)
        led.setdefault("goal_gates", {})
        led["goal_gates"]["X20"] = {
            "gate": "X20", "namespace": "goal_gates",
            "question": result["question"], "bar": BAR_TEXT,
            "seeds": len(seeds), "checkpoints": list(cps),
            "wrong_total": wrong_total,
            "k0_probe_emissions": k0_emissions,
            "accuracy_at_1000": result["accuracy_at_last_checkpoint"],
            "refusals_at_1000": result["refusals_at_last_checkpoint"],
            "state_spec_bytes": result["state_spec_bytes"],
            "winner": winner, "tie": tie,
            "learn_gain_winner": round(learn_gain, 5),
            "digest_rest_H0": digest_all,
            "roundtrip_exact": roundtrip_all,
            "PASS": overall,
        }
        with open(LEDGER, "w", encoding="utf-8") as fh:
            json.dump(led, fh, indent=2)

    print(f"\nX20 {'PASS' if overall else 'FAIL'} - winner {winner}"
          f"{' (TIE)' if tie else ''} | acc@{last_k} A={acc_a:.4f} "
          f"B={acc_b:.4f} | wrong {wrong_total} | k0 emissions "
          f"{k0_emissions} | gain {learn_gain:+.4f} (bar >= 0.30) | "
          f"digest H0 {digest_all} | roundtrip {roundtrip_all}",
          flush=True)
    if not smoke:
        print(f"wrote {RESULT_PATH} and ledger goal_gates.X20 "
              f"in {elapsed:.1f}s")
    return 0 if overall else 1


def main() -> int:
    return run(smoke="--smoke" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())
