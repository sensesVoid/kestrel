# Project Kestrel — Kanban Board Card (GAP-10 style)

## 0. Tooling, MCP & context-gathering protocol (READ FIRST)

**Context gathering (every session, before any claim):**
1. `mem_bootstrap(project="Project_Kestrel")` at session start — load working
   context, active goal, last host/model, checkpoints. If memory is empty, say
   so; never fabricate.
2. Read `trading-agent-spec.md` (SPEC-1) + `CHECKLIST.md` + handoff
   `.agent_context/memory/kestrel_next.md` before asserting status.
3. **HABIT — check completed tasks before acting (FATAL if skipped):** before
   starting ANY task, read CHECKLIST.md and confirm the item is not already
   DONE with cited evidence. Never redo a finished task; never re-run a gate
   that has a passing record. If an item looks done but evidence is missing or
   stale, mark it `BLOCKED (verify)` and re-verify — do not silently redo.
   After completing a task, update CHECKLIST.md (status + evidence row) in the
   SAME commit, and `mem_checkpoint`. Reconcile the board at session start AND
   session end; a session that ends with the board out of date is a failure.
4. For codebase questions, prefer `codegraph_explore` (projectPath) over
   grep/read loops; use Read/Grep/Glob only when no index exists.
5. For library/API/CLI docs, use Context7 (`resolve-library-id` → docs) before
   web search. For web/current info, use websearch/webfetch.
6. For reverse-engineering/binary targets use REA; for security advisories use
   hound; for HF models/datasets use huggingface tools.
7. Persist context: `mem_observe(role, text)` per meaningful turn;
   `mem_checkpoint(goal, summary)` at every task boundary; `mem_graduate` to
   promote stable facts; `mem_sparsify` to keep memory sparse. Teach durable
   facts via `mem_write`/`sqac teach`.

**MCPs available (global, ~/.config/opencode/opencode.json):**
- codegraph, context7, hound, obsidian, huggingface, kaggle, rea, sqac
  (sqac memory dir `~/.sqacm`, AgentBridge cross-CLI continuity).
- obsidian vaults: personal, herald (Project_Herald).

**Anti-hallucination (tools):** never claim a tool result you didn't call;
never mark a checklist item DONE without a cited artifact/ledger key; if a
command's output is truncated/missing, re-run or say "unknown" — do not infer.

**Source of truth:** `trading-agent-spec.md` (DRAFT v1, builder-checked) → becomes
SPEC-1 at M0. This board tracks milestones, bars, and rungs. **Nothing is marked
DONE without a cited artifact/ledger row.** A redesign is a new R-suffix
pre-registration, never an edit of an old one (dual record).

**Status legend:** `TODO` · `IN PROGRESS` · `BLOCKED` · `DONE (evidence: …)` · `FAIL (as measured, R-suffix)`.

**Anti-hallucination rules (read before every update):**
1. A milestone is DONE only when its deliverable exists AND its bars touched
   are measured with a cited artifact path + ledger key. "Looks right" is not
   evidence.
2. Bars are frozen at the rung's own GAP-10 before the runner exists; the
   runner is named and verified ABSENT at freeze. No bar text moves except by
   owner ruling + amendment row.
3. A failing gate keeps its measured record; never regrade, never delete.
4. Predictions P1..P6 are non-binding but scored and published.
5. No live code, keys, or accounts until L2 paper gate passes.
6. No comparative scores vs other traders/funds/LLMs (AGI_BENCHMARK §3).
7. Update this board + handoff memory + (when applicable) sqac teach on every
   state change; footer-free commits via `git commit -F`.

---

## 0b. Frozen recommendations & inherited decisions (do not re-litigate)

Recorded 2026-11-05 (recommendation-first, owner-confirmed). Changing any of
these requires a new pre-registration (R-suffix), not an edit.

**Language & performance policy (decided):**
- **(A) Python v1 as specced** — chosen. Fastest path to a working,
  bar-measured model; preserves Herald lineage via vendored S1 core; optimizes
  hot paths later only if profiling shows need (Rust SIMD extraction pattern,
  like sqac). Rust rewrite (B) and Python-core+Rust-execution (C) rejected
  for v1: months of porting risk, no bar benefit, and two fill-logic
  implementations risk A-3 reconciliation divergence. "Prod ready" here means
  reproducibility + operational continuity + risk caps, not throughput (1h bars,
  no HFT in scope per §9).

**Zero-byte learning (decided: leave as inherited property, NOT a graded bar):**
- Carried from Herald as a substrate property: checkpoints 131,072 B
  byte-neutral; session erase-to-H0 lifecycle unchanged (§3.3, §3.6).
- A-8 includes "substrate checkpoints byte-neutral" as a condition, but there
  is NO standalone zero-byte bar (no ZB-1/N-5-style "0 appended bytes per
  learned/decision item"). Zero-byte is reported/published, not a gate that can
  fail the trading run. Rationale: Kestrel bars measure trading edge; the
  substrate's byte-growth claim is orthogonal; §9 bans AGI/super-intelligence
  claims. If the substrate ever grew bytes at rest → vendoring/integration bug,
  not a measured bar failure.
- If Kestrel ever markets the 0-byte property, promote via R-suffix
  pre-registration (new bar), never a silent edit of A-8.

**Other frozen recommendations (from spec §10 / §1–§9):**
- Venue endpoint (OD-1): decide at M7; not blocking M0–M6.
- Universe expansion beyond BTC(+ETH) (OD-3): later pre-reg.
- Capital size for L3 (OD-4): absolute cap (e.g. ≤2% non-essential savings),
  not a currency amount.
- Project name/dir (OD-2): placeholder "Kestrel"; owner's call (resolve at/before M0).
- GARCH-family conditional vol: ANALYSIS-ONLY in v1 (L0 design packet), not a
  load-bearing M2 deliverable; no vol-scaled sizing in v1 (fixed 2% notional).
- θ_z calibration slice: held-out tail slice INSIDE the train fold (final 15%),
  never the graded test window.
- Stop/target: 3×ATR(16) stop, 2R target; mid-bar touch → level ± slippage;
  gap-through → bar open; next-bar-open execution for close-time decisions.

## Lane 0 — Pre-M0 (owner decisions + sign-off)

- [x] **P0.1** Owner sign-off on `trading-agent-spec.md` v1 (DRAFT → SPEC-1).
      *Evidence needed:* dated owner ruling in amendment log. → **DONE**:
      spec Amendments row 2026-11-05 (owner confirmed recommended option
      this session); header now SPEC-1.
- [x] **P0.2** Project name + repo directory final (placeholder "Kestrel").
      *Evidence needed:* owner ruling; rename if changed. → **DONE**: name
      "Kestrel" retained (same owner ruling). Also resolves OD-2.
- [ ] **P0.3** Venue endpoint confirmation (Binance global vs regional) —
      recommendation: decide at M7; not blocking M0–M6. *Status: deferred.*
- [ ] **P0.4** Universe expansion beyond BTC(+ETH) — later pre-reg, no blocker.
      *Status: deferred.*
- [ ] **P0.5** Capital size for L3 — needed only at L3 pre-reg; absolute cap
      (e.g. ≤2% non-essential savings). *Status: deferred.*

## Lane 1 — Milestones M0–M8

- [x] **M0** Repo bootstrap, vendor map with content-sha pins, house-law docs,
      GAP-10 boot spec. *Bars touched: — (pre-bars).*
      - [x] M0.1 Create directory skeleton: `specs/`, `experiments/`,
            `bench_data/`, `results/`, `src/`, `.venv`, `.agent_context/`,
            `.artifacts/`. → all present + `.venv` = Python 3.11.9.
      - [x] M0.2 Vendor map: pins recorded BEFORE first graded run (§112
            discipline). → `specs/VENDOR_MAP.md` + machine
            `.agent_context/vendor_pins.json` → moved to tracked
            `specs/vendor_pins.json` (memory dir untracked); 5 files pinned:
            `x28_wirule.py`
            `8a77c0ad…`, `clay.py` `c9dd9396…`, `paths.py` `aea5ac97…`,
            `x20_learn_probe.py` `0459b4e9…`, `tr1_replay.py` `10bd24af…`
            (carries quantizer templates L188–199 + quantize-table generator
            L282–347). Vendored under `src/vendor/`.
      - [x] M0.3 House-law docs imported (GAP-10, frozen populations,
            no-lookahead, refusal economics, mutations-must-flip, dual record,
            posterity). → `specs/HOUSE_LAWS.md` (HL-1..HL-10).
      - [x] M0.4 GAP-10 boot spec: name the L1 runner + artifact + ledger key
            and verify all three ABSENT. → `specs/GAP10_BOOT.md`;
            verification PASSED 2026-11-05 (`l1_walkforward.py` /
            `l1_walkforward.json` / `kestrel_beds` all absent), recorded
            before first graded run. L2/L3 names reserved.
      - [x] M0.5 Commit SPEC-1 (this spec) at M0 before any code. → sign-off
            amendment row 2026-11-05 + header SPEC-1 in
            `trading-agent-spec.md`; lands in the M0 commit.
      - [x] M0.6 `git commit -F` footer-free; append outcome row to memory.
- [ ] **M1** Data pipeline + frozen snapshot manifests (BTC 1h; ETH 1h next).
      *Bars touched: A-8 inputs.*
      - [ ] M1.1 Pull Binance monthly klines ZIPs into
            `bench_data/binance_klines/<PAIR>/<INTERVAL>/`.
      - [ ] M1.2 Build `snapshot.sha256` manifest (per-file hashes); `.gitattributes -text`.
      - [ ] M1.3 Gap protocol + repair packets (sha-pinned, appended, cause written).
      - [ ] M1.4 Data-quality gates (void bars, zero-volume, dup rows, survivorship).
      - [ ] M1.5 Manifest is sole source of truth; runner asserts manifest sha.
- [ ] **M2** L1 statistical layer + quantizer, unit-tested determinism,
      sha-pinned table. *Bars touched: A-1 adapter.*
      - [ ] M2.1 Returns {1,4,16,64}, position-in-range, volume delta, vol,
            vol-regime, quantizer ±1 vector K=8–10.
      - [ ] M2.2 Quantizer table sha asserted by every runner (quantizer lock).
      - [ ] M2.3 Determinism: pure numpy/pandas, no GPU; unit tests.
      - [ ] M2.4 No-lookahead adapter index audit (A-1): 0 reads beyond t.
- [ ] **M3** Backtester + cost model + exact accounting reel.
      *Bars touched: A-3, A-4.*
      - [ ] M3.1 Hand-rolled event loop (no vectorbt/quantlib in graded runs).
      - [ ] M3.2 Cost model: taker 0.10%/side VIP0 (20 bps RT) UNDER-estimate;
            stress ×2 (40 bps); slippage floor max(2 bps, ½ bar range on stop).
      - [ ] M3.3 Stop/target deterministic (3×ATR(16) stop, 2R target); mid-bar
            touch fills at level ± slippage; gap-through fills at bar open.
      - [ ] M3.4 Next-bar-open execution for close-time decisions; horizon-end
            fills at open(t+h); no partial fills in v1 (documented omission).
      - [ ] M3.5 Risk governor L3 (§3.4) hard-coded, non-negotiable.
      - [ ] M3.6 A-3 two-way reconciliation ties to 0 discrepancy.
      - [ ] M3.7 A-4 risk caps hold; kill-switch events published with causes.
- [ ] **M4** S1 core training on window 1 + calibration + refusal plumbing.
      *Bars touched: A-2 core.*
      - [ ] M4.1 WiRULE + Clay vendored, identity-asserted; checkpoints 131,072 B.
      - [ ] M4.2 Training: conditional counter registration over TRAIN, §80/§91
            study-episode protocol (one episode per arrived label, full recency
            window only).
      - [ ] M4.3 Typed verdicts BUY/SELL/FLAT/REFUSE; c=0 is REFUSE class.
      - [ ] M4.4 Emission contract (§3.3): c=+1+z≥θ_z+vol-filter → OPEN_LONG;
            c=−1 long → EXIT_EARLY; c=−1 flat → REFUSE no_inventory_short;
            z<θ_z or vol-filter fail → REFUSE with cause.
      - [ ] M4.5 θ_z calibrated per seed on held-out tail slice INSIDE train
            fold (final 15%); threshold table sha in run manifest.
      - [ ] M4.6 Realized-path labels (§4.4); zero-band θ=30 bps.
      - [ ] M4.7 Refuse-band share expected ~55–75% at h=4h.
- [ ] **M5** Walk-forward harness (windows/embargo/seal from §4.3).
      *Bars touched: A-5, A-8.*
      - [ ] M5.1 34 monthly windows (2023-07→2026-04), 30d test / 180d train,
            7-day embargo, seeds [1,2,3].
      - [ ] M5.2 Held-out seal 2026-05→2026-10 untouched by L1; opens at own gate.
      - [ ] M5.3 Window boundaries frozen as integer indices in pre-reg.
      - [ ] M5.4 Reproducibility: run manifest (package versions, seeds, pop sha,
            quantizer sha, threshold table sha); no network I/O in graded runs.
- [ ] **M6** GAP-10 freeze of L1 graded pre-reg (bars+predictions+mutations)
      → runner → graded run. *Bars touched: A-1..A-8 all.*
      - [ ] M6.1 Pre-reg frozen: bars A-1..A-8, predictions P1..P6, mutations
            (a)(b)(c) named; runner named and verified ABSENT.
      - [ ] M6.2 Absence re-verified: runner file, artifact, ledger key all absent.
      - [ ] M6.3 Runner landed; four pre-verdict repair disclosures (if any)
            recorded before verdict.
      - [ ] M6.4 Graded run executed; results published per-window + aggregated.
      - [ ] M6.5 Outcome row appended; board ticked; handoff refreshed;
            sqac teach; footer-free commit.
- [ ] **M7** Testnet adapter (paper-ops rung pre-reg frozen first).
      *Bars touched: L2 rung.*
      - [ ] M7.1 Venue endpoint decision (open decision #1).
      - [ ] M7.2 Binance Spot Testnet adapter (ccxt paper mode over testnet REST).
      - [ ] M7.3 30 consecutive calendar days, 0 ops errors, risk caps hold,
            no unexplained restarts.
      - [ ] M7.4 Paper ledger reconciles to A-3 accounting within tolerance.
- [ ] **M8** L3 live policy spec (owner-gated; NO code until sign-off).
      *Bars touched: L3 rung.*
      - [ ] M8.1 Fresh pre-reg: risk-absolute bars (max loss/day, max drawdown,
            secret handling).
      - [ ] M8.2 Capital size decision (open decision #4).
      - [ ] M8.3 Owner sign-off before any code.

## Lane 2 — Evaluation bars A-1..A-8 (status board)

| Bar | Description (short) | Status | Evidence |
|---|---|---|---|
| A-1 | No lookahead (adapter index audit 0 reads > t; mutation (b) fires) | TODO | — |
| A-2 | Refuse-band discipline (0 trades in zero-band; published causes) | TODO | — |
| A-3 | Cost-honest accounting (exact reconciliation, 0 discrepancy) | TODO | — |
| A-4 | Risk caps hold (0 breaches; kill-switch causes published) | TODO | — |
| A-5 | OOS expectancy (≥+5 bps/trade AND window equity ≥0 net of ×2 stress; kill clause) | TODO | — |
| A-6 | Regime switches (refuse before re-emit; sticky re-qualify) | TODO | — |
| A-7 | Mutations flip (a) poison→refusals, (b) lookahead→audit fires, (c) cost-off→degrade | TODO | — |
| A-8 | Lifecycle + reproducibility (bit-exact replay, byte-neutral checkpoints, no network) | TODO | — |

**Overall PASS:** all eight, every seed, every window. Failure recorded AS MEASURED.

## Lane 3 — Paper ladder rungs

- [ ] **L0** Design-time analysis (ACF, Hurst, vol regimes, θ feasibility) — published, never graded, never touches held-out. *Gate: feasible θ/h survive honesty check.*
- [ ] **L1** Walk-forward backtest (A-bars over frozen windows, 3 seeds). *Gate: all A-bars + predictions; replay manifest exact.*
- [ ] **L2** Venue paper (≥30 consecutive days, 0 ops errors). *Gate: paper ledger reconciles to A-3; owner reads record.*
- [ ] **L3** Small live (owner-gated; fresh pre-reg; small capital; kill-switch armed). *Gate: unlikely early; every rung-gap honest.*

## Lane 4 — Open decisions (owner's, recommendation-first)

- [x] OD-1 Venue endpoint confirmation — decide at M7. Recommendation: defer. *Status:* deferred (not resolved).
- [x] OD-2 Project name + repo directory — **RESOLVED 2026-11-05:** "Kestrel" retained per owner ruling (see P0.2).
- [ ] OD-3 Universe expansion beyond BTC(+ETH) — later pre-reg.
- [ ] OD-4 Capital size for L3 — absolute cap, not currency amount.

## Lane 5 — Cross-cutting / honesty

- [ ] Anti-goals respected (no guaranteed-profit implication, no comparative scores, no HFT/LOB, no leverage/perps, no sentiment/LLM alt data, no multi-strategy claims, no live code/keys/accounts pre-gate).
- [ ] Will-not-measure list (§9) honored.
- [ ] Posterity: footer-free commits; long messages via `git commit -F`; append-only outcome rows; recommendation-first at decision points; records mirrored into `.agent_context/memory/` + AGENTS.md snapshot.
- [ ] Windows resilience: incremental artifact writes per completed seed (STATUS_CONTROL_C_EXIT lesson); log to `.artifacts/`, never repo root.

---

## Amendment log (board-level)

| date | change | why |
|---|---|---|
| 2026-11-05 | Board card created (Kestrel kanban) from SPEC v1 milestones/bars/rungs; sqac MCP installed & registered; handoff memory created. | owner request: track completion, avoid misses/hallucination. |
| 2026-11-05 | **M0 executed:** SPEC-1 signed off (+od-2 name retained); 5 vendor files pinned (`specs/VENDOR_MAP.md`, `specs/vendor_pins.json` machine copy); house laws `specs/HOUSE_LAWS.md` (HL-1..10); GAP-10 boot `specs/GAP10_BOOT.md` with ABSENT verification PASSED; requirements pinned mirroring Herald stack (torch-hd is `torch-hd` dist, import `torchhd`); pinned deps install → `requirements.lock`. | Lane 1 start; owner sign-off this session. |
| 2026-11-05 | `.agent_context/` untracked (gitignored; spec-prescribed local-only); machine vendor pins relocated to tracked `specs/vendor_pins.json`; refs updated. | owner instruction: keep memory local-only. |

---

## Evidence index (fill as work lands)

| item | artifact path | ledger key | date |
|---|---|---|---|
| P0.1/P0.2 owner sign-off + name | `trading-agent-spec.md` (Amendments row + SPEC-1 header) | — | 2026-11-05 |
| M0.2 vendor pins (5 files) | `specs/VENDOR_MAP.md`, `specs/vendor_pins.json` | — | 2026-11-05 |
| M0.3 house laws | `specs/HOUSE_LAWS.md` | — | 2026-11-05 |
| M0.4 GAP-10 boot + ABSENT verification | `specs/GAP10_BOOT.md` (verification log inside) | `kestrel_beds.L1` (reserved) | 2026-11-05 |
| M0.6 M0 commit (SPEC-1 + all above) | this repo, footer-free commit | — | 2026-11-05 |
| M1.1 raw klines staged (666 zips, 11.62 MB, 0 failures) | `bench_data/binance_klines/` (manifest lands in M1.2) | — | 2026-11-05 |
