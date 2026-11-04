# kestrel-next (handoff) — 2026-11-05 (post-M0)

## Facts
- Project Kestrel: trading AI agent (algo trading + deep statistical analysis),
  forked from Herald. Repo: C:\Users\geral\Project_Kestrel. Git initialized,
  2 commits (91263b1 folder+doc, 71839ea .gitattributes * -text) + M0 commit
  landing this run. M0 DONE (see Evidence index).
- Master spec: trading-agent-spec.md is now **SPEC-1** (signed off 2026-11-05,
  header + amendment row). Authoritative copy is THIS repo's.
- Owner decisions (2026-11-05, all recommended): (1) HYBRID model core
  (stats layer + WiRULE/Clay S1), (2) CRYPTO SPOT (Binance, BTCUSDT first, 1h),
  (3) PAPER-FIRST LADDER (backtest → testnet 30d → owner-gated small live),
  (4) spec v1 signed off as SPEC-1; name "Kestrel" retained (OD-2 resolved).
- Standing ruling: for owner-decision points, the builder provides + acts on
  its best recommendation; owner re-litigates via R-suffix pre-registration.
- Vendor pins (M0.2, before first graded run): 5 files in `src/vendor/` with
  sha256 in `specs/VENDOR_MAP.md` + `.agent_context/vendor_pins.json`:
  x28_wirule.py 8a77c0ad…, clay.py c9dd9396…, paths.py aea5ac97…,
  x20_learn_probe.py 0459b4e9…, tr1_replay.py 10bd24af… (quantizer templates
  L188–199 + quantize-table generator L282–347).
- House laws: `specs/HOUSE_LAWS.md` (HL-1..HL-10).
- GAP-10 boot: `specs/GAP10_BOOT.md` — L1 names frozen
  (`experiments/l1_walkforward.py`, `results/l1_walkforward.json`,
  `kestrel_beds.L1`); ABSENT verification PASSED 2026-11-05; L2/L3 reserved.
- Deps: `requirements.txt` (mirrors Herald stack: numpy 2.4.6, pandas 3.0.6,
  scipy 1.17.1, torch 2.14.1, torch-hd 5.8.4, pytest 8.3.4) → `.venv`
  (Python 3.11.9); lock = `requirements.lock`. GOTCHA: the distribution name
  is `torch-hd` (import `torchhd`); "torchhd" is NOT on PyPI.
- Raw data staged: 666 Binance monthly kline ZIPs (BTCUSDT+ETHUSDT ×
  1h/4h/1d, 2017-08→2026-10), 11.62 MB, 0 failures, in
  `bench_data/binance_klines/`. Manifest + gap protocol = M1 work.
- sqac MCP installed & registered globally (memory dir ~/.sqacm);
  mem_bootstrap / mem_observe / mem_checkpoint / teach in use.
- Kanban board: C:\Users\geral\Project_Kestrel\CHECKLIST.md. Lane 0 P0.1/P0.2
  DONE; M0.1–M0.6 DONE; OD-2 resolved. Anti-hallucination rules §0 (habit:
  check DONE items before acting — FATAL if skipped).

## Decisions
- Tracking discipline: nothing DONE without cited artifact/ledger key; failures
  recorded as measured; redesigns are R-suffix pre-registrations (dual record).
- Milestone order (implementation): M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8.
  M4 and M6 are the two places a failed bar is informative (never a regrade).
- Language: Python v1 as specced (Rust only as targeted SIMD hot-path later).
- Zero-byte learning: inherited substrate property (byte-neutral checkpoints,
  erase-to-H0), reported not barred in v1; promote via R-suffix if claimed.
- Memory protocol: mem_bootstrap at session start; mem_observe per meaningful
  turn; mem_checkpoint at task boundaries; mem_search/mem_recall for recall;
  mem_graduate to promote stable facts; mem_sparsify to keep sparse.

## Gotchas
- Herald is PAUSED (mid-MATH-1R, seed 1 passed, seeds 2–3 never completed;
  stale run-#1 artifact reverted). Do not resume Herald work unless owner says.
- Python: use venv-first, Python 3.11 for the project (source's version); never
  system Python; NEVER run inline `python -c` via PowerShell (write a script);
  long commands → redirect output to .artifacts/, never repo root.
- Windows: STATUS_CONTROL_C_EXIT when sessions die → incremental artifact
  writes per completed seed; schtask/Start-Process detachment gotchas.
- Graded runs: no network I/O; population frozen sha-pinned; runner asserts
  manifest sha at setup.
- `.gitattributes * -text` everywhere (byte-exact, sha pins cannot drift).
- Footer-free commits; long messages via `git commit -F <file>`.

## Next (recommended, in order)
1. M1: data pipeline — build `snapshot.sha256` manifest (per-file sha256 over
   the 666 staged zips), `.gitattributes -text` for data dir, gap protocol,
   data-quality gates (void bars, zero-volume, dup rows, survivorship),
   runner asserts manifest sha. BTC 1h first, ETH 1h next.
2. M2: L1 statistical layer + quantizer (vendored templates), determinism
   unit tests, no-lookahead adapter audit (A-1).
3. Do NOT start M2 until M1 manifest sha is pinned and committed.

## Open blockers
- None. (P0.1/P0.2/OD-2 resolved; OD-1/OD-3/OD-4 deliberately deferred at
  M7/L2/L3 gates.)

## Evidence index
| item | artifact | ledger key | date |
|---|---|---|---|
| Owner sign-off + name | spec Amendments row 2026-11-05 | — | 2026-11-05 |
| Vendor pins (5 files) | `specs/VENDOR_MAP.md`, `.agent_context/vendor_pins.json` | — | 2026-11-05 |
| House laws | `specs/HOUSE_LAWS.md` | — | 2026-11-05 |
| GAP-10 boot + verification | `specs/GAP10_BOOT.md` | `kestrel_beds.L1` | 2026-11-05 |
| Raw data staged | `bench_data/binance_klines/` (666 zips) + `.artifacts/fetch.log` | — | 2026-11-05 |
