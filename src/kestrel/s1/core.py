"""S1 core (M4): Herald's WiRULE weightless classifier adapted to Kestrel's
8-feature quantized trading stream, with Clay 131,072 B checkpoints.

Identity: vendored `src/vendor/x28_wirule.py` and `src/vendor/clay.py` are
sha256-pinned in `specs/vendor_pins.json`; this module asserts both pins at
import (M4.1).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

ROOT = str(Path(__file__).resolve().parents[3])
VENDOR = os.path.join(ROOT, "src", "vendor")
PINS = os.path.join(ROOT, "specs", "vendor_pins.json")


def _assert_identity():
    pins = json.load(open(PINS, encoding="utf-8"))
    by_path = {p["vendored"]: p["sha256"] for p in pins["pins"]}
    for rel in ("src/vendor/x28_wirule.py", "src/vendor/clay.py"):
        raw = open(os.path.join(ROOT, rel), "rb").read()
        if hashlib.sha256(raw).hexdigest() != by_path[rel]:
            raise RuntimeError(f"vendored {rel} drifted from its pin (S1 identity)")


_assert_identity()

sys.path.insert(0, VENDOR)
import x28_wirule as _X  # noqa: E402
import clay as _clay       # noqa: E402

# adapted constants (mechanism-faithful, trading-scaled)
VENDOR_N_BITS = _X.N_BITS
VENDOR_E_MIN = _X.E_MIN
VENDOR_E_LIT = _X.E_LIT
VENDOR_SEP_MIN = _X.SEP_MIN
VENDOR_C_CAP = _X.C_CAP
VENDOR_ARITY = _X.ARITY

N_BITS = 8
N_LIT = 2 * N_BITS
ARITY = 3
C_CAP = 10000
E_MIN = 50
E_LIT = 2
SEP_MIN = 2
CLAY_BYTES = _clay.CLAY_BYTES
D = _clay.D


def sat_lits(x: List[int]) -> List[int]:
    return ([i for i in range(N_BITS) if x[i] == 1]
            + [N_BITS + i for i in range(N_BITS) if not x[i]])


class S1Core:
    def __init__(self):
        self.c = [[0] * N_LIT for _ in range(2)]
        self.t = 0
        self.refused_updates = 0

    def state_bytes(self) -> int:
        return 2 * N_LIT + 8

    def update(self, x: List[int], y: int) -> None:
        assert y in (1, -1), "only +/-1 labels register (c=0 is REFUSE)"
        assert len(x) == N_BITS
        ci = 0 if y == 1 else 1
        for lit in sat_lits(x):
            if self.c[ci][lit] < C_CAP:
                self.c[ci][lit] += 1
            else:
                self.refused_updates += 1
        self.t += 1

    def is_confident(self):
        # R1: confidence gate is t >= E_MIN only (scoring doesn't need a
        # single conjunction). E_LIT/SEP_MIN retained for traceability.
        if self.t < E_MIN:
            return False, [], [], []
        return True, [], [], []

    def predict(self, x: List[int]) -> Tuple[Optional[int], float]:
        assert len(x) == N_BITS
        confident = self.t >= E_MIN
        if not confident:
            return None, 0.0
        active = sat_lits(x)
        score = sum(self.c[0][lit] - self.c[1][lit] for lit in active)
        # z: normalized magnitude (per-cell, continuous)
        z = abs(score) / max(E_LIT * N_LIT, 1)
        if score > 0:
            return 1, float(z)
        if score < 0:
            return -1, float(z)
        return None, 0.0

    def emit(self, x: List[int], theta_z: float) -> Tuple[int, float]:
        cls, z = self.predict(x)
        if cls is None or z < theta_z:
            return 0, float(z)
        return int(cls), float(z)

    def fields(self) -> List[int]:
        flat = list(self.c[0]) + list(self.c[1]) + [self.t]
        return flat

    def to_dict(self) -> Dict:
        return {"c": [row[:] for row in self.c], "t": self.t,
                "refused_updates": self.refused_updates}

    @classmethod
    def from_dict(cls, d: Dict) -> "S1Core":
        o = cls()
        o.c = [row[:] for row in d["c"]]
        o.t = d["t"]
        o.refused_updates = d.get("refused_updates", 0)
        return o


def save_checkpoint(core: S1Core, path: str) -> None:
    clay = _clay.Clay()
    arr = np.zeros(D, dtype=np.int16)
    flat = core.fields()
    for i, v in enumerate(flat):
        if i < D:
            arr[i] = int(v)
    clay.M = _clay.torch.from_numpy(arr.copy())
    clay.save(path)
    import os as _os
    assert _os.path.getsize(path) == CLAY_BYTES


def load_checkpoint(path: str) -> S1Core:
    clay = _clay.Clay.load(path)
    arr = clay.M.numpy()
    core = S1Core()
    flat = [int(v) for v in arr.tolist()[: (2 * N_LIT + 1)]]
    for i in range(N_LIT):
        core.c[0][i] = flat[i]
        core.c[1][i] = flat[N_LIT + i]
    core.t = flat[2 * N_LIT] if len(flat) > 2 * N_LIT else 0
    return core


def clay_byte_neutral() -> bool:
    clay = _clay.Clay()
    before = clay.digest()
    key = _clay.atom("kestrel:s1:probe")
    roles = _clay.roles_vector("role:", _X.N_ROLES)
    cb = _clay.codebook("f:", _X.N_FILLERS, transposed=True)
    fillers = _clay.fields_to_vectors(cb, [1, 2, 3, 4, 5, 6, 7, 8],
                                      n_entries=_X.N_FILLERS)
    clay.write(key, roles, fillers)
    clay.erase(key, roles, fillers)
    return clay.digest() == before
