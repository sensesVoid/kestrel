# House Laws — Kestrel (imported from Herald canon)

These laws govern every Kestrel milestone, bar, and rung. They are carried
from Project Herald's evaluation discipline (AGI_DERIVATION, AGI_BENCHMARK,
GAP reports) and bind all agents and runners. A violation is a bar failure,
not a stylistic nit.

## HL-1 GAP-10 pre-registration
A graded run is measurable only if the experiment/artifact/ledger-key names
were pinned, and runner-existence verified ABSENT, before the first run
(current: `specs/GAP10_BOOT.md`). No post-hoc naming, no renaming after a run.

## HL-2 Frozen full populations
Parameters, windows, seeds, costs, thresholds are frozen in pre-registration
before data is touched by the graded path. Populations are complete and
fixed: no selective exclusion, no "best-of-N" surfacing, no silent defaults.

## HL-3 No-lookahead audit
Every graded runner reads bars causally (adapter may index ≤ t only, with the
TR-3 `Audit` recording every index read; any beyond-t read is a structural
violation that a mutation must make fire). Next-bar-open execution for
close-time decisions; gap-through fills at bar open (§3.4, §4.1).

## HL-4 Refusal economics
`c = 0 → REFUSE` is a first-class verdict. Refusals are emitted with typed
causes (incl. no_inventory_short, regulation/kill-clause, low-confidence);
the refuse-band share is **published, never tuned to look active**. GLM
(vertical-margin) discipline at readout: refuse when evidence insufficient
(§3.3). Refuse-only mode is forced for a window's remainder after any daily
kill trip (§5 A-5).

## HL-5 Mutations must flip
Every structural guarantee has an enumerated negative control: feed the
adapter future bars (mutation (b)) and violations must fire; break a gate and
behavior must visibly change. A guarantee whose mutation changes nothing is
not a guarantee (structural, SA-1 lineage).

## HL-6 Dual record / never regrade
Measured failures are recorded as measured. A redesign is a NEW R-suffix
pre-registration (dual record) — never an edit of a frozen pre-reg, never a
re-grade of the same window, never a re-run of a passed gate without cause.
Checklist items marked DONE need a cited artifact/ledger row; "done" without
evidence is a fatal error.

## HL-7 Posterity & memory
- Footer-free commits via `git commit -F <file>` (no Generated-with trailers).
- Append-only outcome rows in memory ledgers; long output to `.artifacts/`,
  never repo root.
- Windows resilience: **incremental artifact writes per completed seed**
  (the 2026-10-26 MATH-1R lesson); schtask/Start-Process detachment gotchas
  assumed (`STATUS_CONTROL_C_EXIT` risk).
- Recommendation-first: the builder recommends the best option and acts;
  the owner re-litigates via R-suffix, not by veto-in-chat after the fact.

## HL-8 Honesty & labels
Single ground truth per bar; realized-path labels computed through the SAME
deterministic fill path as accounting (no separate label logic; §4.4).
Zero-band θ = 30 bps. §9 bans AGI/super-human claims outright: Kestrel is a
trading tool with measured bars.

## HL-9 Version & environment pinning
Every graded run prints and locks versions (`requirements.txt` +
`requirements.lock`, vendor + quantizer + threshold-table shas in the run
manifest, §5 A-8). Pure Python 3.11 venv; no global installs; determinism =
numpy/pandas only in stats layer, torch CPU in core layer.

## HL-10 Checkpoint byte-neutrality (inherited, reported not barred)
Substrate checkpoints are 131,072 B and byte-neutral at rest; session
lifecycle is erase-to-H0 (§3.3, §3.6). v1 reports this property (A-8
condition); it is NOT a graded bar — a byte-growth-at-rest finding means a
vendoring/integration bug, not a bar failure. Marketing the property requires
a new R-suffix pre-registration.
