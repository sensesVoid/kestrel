# AGENTS.md — Project Kestrel (snapshot)

Trading AI agent (algo trading + deep statistical analysis), forked from Herald.
Source of truth: `trading-agent-spec.md` (SPEC-1, signed off 2026-11-05).
Kanban: `CHECKLIST.md`. Handoff: `.agent_context/memory/kestrel_next.md`.

## Status
- M0 DONE (2026-11-05): SPEC-1 signed off; vendor pins (5 files,
  `specs/VENDOR_MAP.md` + `.agent_context/vendor_pins.json`); house laws
  (`specs/HOUSE_LAWS.md`); GAP-10 boot (`specs/GAP10_BOOT.md`, L1 names
  frozen + ABSENT-verified); deps pinned (Herald stack, `torch-hd` dist!)
  into `.venv` (Python 3.11.9); raw data staged (666 kline zips).
- Next: M1 data pipeline (sha-pinned snapshot manifest, quality gates).
- Decisions: HYBRID core · CRYPTO SPOT (Binance BTCUSDT 1h) · PAPER-FIRST LADDER.

## Memory protocol (sqac)
1. mem_bootstrap at session start (project="Project_Kestrel").
2. mem_observe for meaningful turns.
3. mem_checkpoint at task boundaries.
4. mem_search / mem_recall for recall; mem_graduate to promote; mem_sparsify to prune.

## Tracking rules
- Nothing DONE without cited artifact/ledger key (see CHECKLIST.md anti-hallucination rules).
- Failures recorded as measured; redesigns are R-suffix pre-registrations.
- Footer-free commits via `git commit -F`; long output to `.artifacts/`, never repo root.
- Windows: incremental artifact writes per completed seed.

## Pointers
- Herald canon: `C:\Users\geral\Project_Herald\specs\AGI_DERIVATION.md` (§80 G2-TR, §91, §112), `AGI_BENCHMARK.md` (§3).
- sqac memory dir: `~/.sqacm`.
