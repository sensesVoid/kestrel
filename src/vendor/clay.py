"""Clay: a fixed-size ternary memory that remembers how to become a shape.

Phase 1 substrate, following clay.md section 5.1.

The clay is the only thing on disk and its size never changes. Shapes are
never stored: a shape is regenerated from its name, projected as data, and
dropped. Atoms and codebooks are regenerated from seeds and live in RAM.

Representation (clay.md section 4):
    D            = 65,536
    clay         = 65,536 int16 counters = 131,072 bytes
    atoms        = dense +-1, from SHA-256 of the name
    bind         = elementwise product (self-inverse)
    write/erase  = add / subtract key (x) sum_i role_i (x) filler_i
    activate     = clay (x) key, held in RAM only
    decode       = dot against a codebook; accept on z alone, z >= 5.5
    z            = (best - mean of the rest) / std of the rest, same row

Two torchHD notes that shape the code below:

  * ``torchhd.bind`` overrides ``__eq__``, so ``torch.equal(a, b)`` is False
    for equal MAP tensors. Every identity check here uses ``(a == b).all()``
    or goes through numpy bytes.
  * ``torchhd.random`` takes a ``torch.Generator``, not ``seed=``. Name-keyed
    determinism therefore goes through ``manual_seed(seed_of(name))``.

MAP is float32 and cannot hold int16 counters, so the clay is a raw torch
int16 tensor. torchHD supplies atoms, bind, and decode scoring.
"""

from __future__ import annotations

import hashlib

import numpy as np
import torch
import torchhd

# ---------------------------------------------------------------- specification

D = 65536
"""Dimensions of the clay and of every atom."""

CLAY_DTYPE = torch.int16
"""On-disk and in-RAM counter type. Non-saturating; overflow is refused."""

CLAY_BYTES = D * 2
"""131,072. Constant at every load. Gate T1."""

TIE_BREAK_ATOM = 0
"""When a vote sum is exactly 0, fall back to this atom. Gate T0."""


def _seed_of(name: str) -> int:
    """name -> 64-bit seed, from SHA-256. The only source of randomness."""
    return int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], "little")


# ---------------------------------------------------------------------- atoms


def atom(name: str, *, dimensions: int = D) -> torch.Tensor:
    """Dense +-1 vector for ``name``, regenerated from its seed, never stored.

    ``dimensions`` is a parameter so gate D0 can vary D without touching the
    seed derivation: a given name still yields the same leading coordinates.
    """
    generator = torch.Generator().manual_seed(_seed_of(name))
    return torchhd.random(1, dimensions, vsa="MAP", generator=generator)[0]


def roles_vector(prefix: str, n_roles: int, *, dimensions: int = D) -> torch.Tensor:
    """(n_roles, D) stack of ``prefix:i`` atoms."""
    return torch.stack([atom(f"{prefix}{i}", dimensions=dimensions) for i in range(n_roles)])


def codebook(prefix: str, n_entries: int, *, dimensions: int = D,
             transposed: bool = False) -> torch.Tensor:
    """(n_entries, D) float32 codebook, or (D, n_entries) if transposed.

    RAM only, never written to disk.

    Gate note from clay.md 5.3 item 8: every codebook must hold at least 64
    entries or the z-score has nothing to standardize against. Callers pad
    rather than shrinking below this.

    ``transposed=True`` returns a contiguous (D, n_entries) copy. Scoring wants
    exactly this shape, and a contiguous right operand is 6x faster than a
    transposed view: 45.6 ms vs 285.3 ms for 8 x 1024 at D = 65,536. The
    transpose of a contiguous tensor is a stride-swapped view, which torch
    cannot feed to BLAS without materializing it first.
    """
    cb = torch.stack(
        [atom(f"{prefix}{i}", dimensions=dimensions) for i in range(n_entries)]
    ).to(torch.float32)
    return cb.T.contiguous() if transposed else cb


# ------------------------------------------------------------------- the clay


def _verdicts(scores: torch.Tensor, *, z_thr: float):
    """Turn an (n_rows, n_entries) score matrix into per-row verdicts.

    Shared by ``decode`` and ``decode_many`` so the two cannot drift apart.

    Acceptance is z alone, where z = (best - mean of rest) / std of rest, read
    from the winning row (clay.md 5.3 item 1).

    No absolute score floor. Score is dot/D and unbounded: a never-written
    key's best score runs 0.265 at load 25 to 1.643 at load 1000 because the
    clay grows as sqrt(load) and the dot is never normalized. Over 1600 pure
    noise draws score exceeds 0.5 EVERY time (max 5.01), so an absolute floor
    cannot distinguish signal from crosstalk at any load. z is a ratio to the
    row's own spread, so it does not grow with load, and pure noise over the
    same 1600 draws peaks at z = 4.78.

    z_thr defaults to 5.5, not clay.md's 5.0. Measured across 3 seeds x 14
    loads, a bar of 5.0 produces 1 confident wrong and 20 unwritten-key false
    accepts; 5.5 produces zero of each and does not cost capacity -- cap stays
    100 shapes (800 pairs). This is K1's request, confirmed.
    """
    out = []
    for row in scores:
        best = int(row.argmax())
        rest = torch.cat([row[:best], row[best + 1:]])
        z = (row[best] - rest.mean()) / max(float(rest.std()), 1e-12)
        out.append((best if z >= z_thr else None, float(row[best]), float(z)))
    return out


class Clay:
    """65,536 int16 counters. Fixed size. Every write is exactly undoable."""

    def __init__(self, *, dimensions: int = D):
        self.dimensions = dimensions
        self.M = torch.zeros(dimensions, dtype=CLAY_DTYPE)

    # -- identity -----------------------------------------------------------

    def digest(self) -> str:
        """SHA-256 of the counter bytes. The bit-identity witness for T1/T4/K0."""
        return hashlib.sha256(self.M.numpy().tobytes()).hexdigest()

    def equal(self, other: "Clay") -> bool:
        return self.digest() == other.digest()

    # -- persistence --------------------------------------------------------

    def save(self, path) -> None:
        """Write exactly CLAY_BYTES. Size is asserted, not assumed."""
        self.M.numpy().tofile(path)
        written = self.M.numpy().nbytes
        if written != CLAY_BYTES:
            raise ValueError(f"clay wrote {written} bytes, expected {CLAY_BYTES}")

    @classmethod
    def load(cls, path, *, dimensions: int = D) -> "Clay":
        """Load from a file alone. T2: a fresh process must need nothing else."""
        clay = cls(dimensions=dimensions)
        raw = np.fromfile(path, dtype=np.int16)
        if raw.size != dimensions:
            raise ValueError(f"clay file holds {raw.size} counters, expected {dimensions}")
        clay.M = torch.from_numpy(raw.copy())
        return clay

    # -- arithmetic ---------------------------------------------------------

    def _accumulate(self, key: torch.Tensor, shape: torch.Tensor, sign: int) -> None:
        """M += sign * key (x) shape, refusing rather than saturating.

        int32 arithmetic then a range check, per clay.md 5.3 item 7: saturating
        counters break undo. A refused write leaves the clay untouched.
        """
        delta = key.to(torch.int32) * shape.to(torch.int32) * sign
        new = self.M.to(torch.int32) + delta
        peak = int(new.abs().max())
        if peak > 32767:
            raise OverflowError(f"write would reach {peak}, above int16 limit: refused")
        self.M = new.to(CLAY_DTYPE)

    @staticmethod
    def _project(roles: torch.Tensor, fillers: torch.Tensor) -> torch.Tensor:
        """sum_i role_i (x) filler_i, in int32."""
        if roles.shape[0] != fillers.shape[0]:
            raise ValueError(f"{roles.shape[0]} roles but {fillers.shape[0]} fillers")
        return (roles.to(torch.int32) * fillers.to(torch.int32)).sum(dim=0)

    def write(self, key: torch.Tensor, roles: torch.Tensor, fillers: torch.Tensor) -> None:
        self._accumulate(key, self._project(roles, fillers), +1)

    def erase(self, key: torch.Tensor, roles: torch.Tensor, fillers: torch.Tensor) -> None:
        """Exact inverse of write. Gate T4 compares digests, not statistics."""
        self._accumulate(key, self._project(roles, fillers), -1)

    # -- read ---------------------------------------------------------------

    def activate(self, key: torch.Tensor) -> torch.Tensor:
        """M (x) key. Transient: the caller drops it, the clay is unchanged."""
        return self.M.to(torch.int32) * key.to(torch.int32)

    def decode(self, key: torch.Tensor, roles: torch.Tensor, cb: torch.Tensor,
               *, z_thr: float = 5.5, transposed: bool = False):
        """Read each role's filler out of the activated clay.

        ``cb`` is a float32 codebook of n entries, built by ``codebook()``.
        Pass ``transposed=True`` (and build it that way) to score against a
        contiguous (D, n_entries) copy: 45.6 ms instead of 285.3 ms per
        8-field shape at D = 65,536. Returns a list of
        ``(index_or_None, score, z)`` per role, in role order. ``None`` means
        refused: the clay declined to answer rather than guessing.

        Scores are ``dot(probe, codebook) / D`` (clay.md 5.1), NOT cosine. A
        write stores ``key (x) role (x) filler`` and probing with
        ``key (x) role`` recovers that filler at unit magnitude. Cosine divides
        by |probe|, which grows like sqrt(load); at load 100 the same reads
        0.035. Measured at load 1: dot 1.0066, cosine 0.356.

        Acceptance is z alone at 5.5; see ``_verdicts`` for why there is no
        absolute score floor.
        """
        x = self.activate(key)
        probes = x.unsqueeze(0) * roles.to(torch.int32)          # (n_roles, D)
        probes = probes.to(torch.float32)
        scores = (probes @ cb) / self.dimensions if transposed else (probes @ cb.T) / self.dimensions
        return _verdicts(scores, z_thr=z_thr)

    def decode_many(self, keys: list[torch.Tensor], roles: torch.Tensor,
                    cb: torch.Tensor, *, z_thr: float = 5.5,
                    transposed: bool = True):
        """Decode many shapes against the same role layout, one batched matmul.

        Same verdicts as calling ``decode`` per shape — verified bit-identical,
        including z — because BLAS computes each output row independently. Only
        the batching changes: 1.85 ms per probe at batch 320 against 4.66 ms at
        batch 8, a 2.5x saving that is what makes a full-population capacity
        sweep affordable on CPU.

        Returns a list of per-shape verdict lists, in the order of ``keys``.
        """
        if not keys:
            return []
        activated = torch.stack([self.activate(k) for k in keys])       # (n, D)
        probes = (activated.unsqueeze(1) * roles.to(torch.int32)).reshape(-1, self.dimensions)
        probes = probes.to(torch.float32)
        scores = (probes @ cb) / self.dimensions if transposed else (probes @ cb.T) / self.dimensions
        flat = _verdicts(scores, z_thr=z_thr)
        n_roles = roles.shape[0]
        return [flat[i * n_roles:(i + 1) * n_roles] for i in range(len(keys))]


# ---------------------------------------------------------------- ground truth


def content(i: int, m: int, v: int, *, tag: str = "shape") -> list[int]:
    """Deterministic filler fields of shape i. Regenerable, so never stored.

    The tag separates the ground truth stream from the atom stream: a shape's
    fields must not be predictable from its key's atom.
    """
    generator = torch.Generator().manual_seed(_seed_of(f"{tag}-content:{i}"))
    return torch.randint(0, v, (m,), generator=generator).tolist()


# --------------------------------------------------------------------- shapes

N_ROLES = 8
"""Fields per shape: roles role:0..7."""

N_FILLERS = 1024
"""Codebook size, per clay.md section 4. Also the value range of a field."""


def shape_key(i: int, *, tag: str = "shape") -> torch.Tensor:
    """The address of shape i. A seed name, not a stored vector."""
    return atom(f"{tag}-key:{i}")


def shape_ground_truth(i: int, *, roles: int = N_ROLES, fillers: int = N_FILLERS,
                       tag: str = "shape") -> tuple[torch.Tensor, list[int]]:
    """(roles, ground-truth field indices) for shape i, both regenerated from i.

    The fields are indices, not vectors. The vectors live in the codebook, so a
    field is written as cb[index] and decoded back to index. Keeping the two
    apart is what makes ground truth regenerable without the codebook in RAM.
    """
    return roles_vector("role:", roles), content(i, roles, fillers, tag=tag)


def fields_to_vectors(cb: torch.Tensor, fields: list[int], *, n_entries: int) -> torch.Tensor:
    """Index a codebook into the (n_roles, D) filler stack a write needs.

    Accepts either orientation of ``cb``: (n_entries, D), or the (D, n_entries)
    transposed form that ``codebook(..., transposed=True)`` returns for fast
    scoring. Orientation is resolved against ``n_entries``, not against
    ``len(fields)`` -- the number of fields in a shape is unrelated to the
    codebook size, so matching on it silently picks the wrong axis.
    """
    idx = torch.tensor(fields, dtype=torch.long)
    if cb.shape[0] == n_entries:
        return cb[idx]                  # (n_entries, D)
    if cb.shape[1] == n_entries:
        return cb[:, idx].T             # (D, n_entries) -> (n_roles, D)
    raise ValueError(
        f"codebook {tuple(cb.shape)} has no axis of length n_entries={n_entries}"
    )


def vectors_to_fields(reported: list) -> list:
    """Accepted indices from a decode, or None where the clay refused."""
    return [j for j, _, _ in reported]


def classify(reported: list, truth: list[int]) -> str:
    """One recall, one of three labels. Never "probably right".

    exact    — every field accepted and equal to ground truth
    refused  — at least one field declined (None)
    wrong    — all fields accepted and at least one differs

    A wrong is worse than a refusal (clay.md rule 2), so the classifier must not
    blur them: a partially-refused read is a refusal, never a wrong.
    """
    accepted = [j for j, _, _ in reported]
    if any(j is None for j in accepted):
        return "refused"
    if all(j is not None and j == t for j, t in zip(accepted, truth)):
        return "exact"
    return "wrong"