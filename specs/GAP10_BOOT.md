# GAP-10 Boot Spec — Kestrel L1 (M0.4)

GAP-10 discipline (Herald): a graded experiment must have its canonical
runner path, artifact path, and ledger key **named in pre-registration and
verified ABSENT from the repo before the first graded run** — no
post-hoc naming, no renaming drift, no overwrite collisions.

## L1 — walk-forward graded exercise (freeze)

| slot | frozen value | verified |
|---|---|---|
| runner | `experiments/l1_walkforward.py` | ABSENT at M0 (see verification below) |
| artifact | `results/l1_walkforward.json` | ABSENT at M0 |
| ledger key | `kestrel_beds.L1` | ABSENT at M0 (no code exists; grep clean) |
| artifact mode | incremental writes per completed seed (HL-7 Windows rule) | design contract |

Verification (2026-11-05, recorded BEFORE first graded run):
- `experiments/l1_walkforward.py` — not on disk.
- `results/l1_walkforward.json` — not on disk.
- `kestrel_beds` token — zero occurrences in tracked files.
(Re-run checks: `Test-Path` on both paths + `git grep -l kestrel_beds` must
return nothing until L1's first run writes them; the runner itself asserts
on start that, if the artifact exists, its `manifest` records this spec.)

## Frozen field semantics (L1)

`kestrel_beds.L1` ledger rows carry: window metadata (§4.3 windows),
seed, manifest sha (code+data+vendor+quantizer+threshold-table versions),
per-window verdicts, fills, costs, and A-2..A-8 bar outcomes. Windows are
frozen as integer indices (HL-2); the runner refuses to start if any window
boundary resolves differently from the pre-reg.

## Reserved (not graded yet; do not run)

| rung | runner (reserved) | artifact (reserved) | ledger key (reserved) |
|---|---|---|---|
| L2 venue paper | `experiments/l2_paper.py` | `results/l2_paper.json` | `kestrel_beds.L2` |
| L3 gated live | `experiments/l3_live.py` | `results/l3_live.json` | `kestrel_beds.L3` |

L2/L3 runners are reserved names only; their specs and pre-regs land at their
own gates (after M7 venue decision OD-1). Nothing here licenses trading.

## R1+ pre-registration hook (M4 will pin)

At M4, the S1-core redesign / study-episode protocol row (R-suffix) will be
pre-registered in an update to this file BEFORE touching TRAIN bars, per
HL-1/HL-6 dual record.
