# Trading AI Agent — Project Spec & Training-Data Plan

**Status:** DRAFT v1 2026-11-05, for owner sign-off. Source project:
`C:\Users\geral\Project_Herald` (Herald, morphogenetic AGI aspirant) — this
new project starts FROM Herald: its proven model core, its evaluation
discipline, and its documentation canon. Decisions taken with the owner
2026-11-05 (**recommendation-first, all three recommended options chosen**):
**(1) HYBRID model core** — conventional statistical layer + Herald's
WiRULE/Clay as the S1 fast decision mechanism; **(2) CRYPTO SPOT first** —
Binance data + paper ladder; **(3) PAPER-FIRST LADDER** — frozen backtests →
venue paper account → small live strictly after gated bars pass.

---

## 0. The goal, stated honestly

**Goal:** a working AI trading model — a program that runs end to end:

```
market bars → statistical features → S1 decision core → typed decision
(BUY / SELL / FLAT / REFUSE) → risk governor → paper execution → realized
outcome fed back causally, bar by bar
```

…with every claim falsifiable under the source project's own discipline
(frozen populations declared before any runner exists, no lookahead,
mutations that must flip, dual records, never regraded).

**What "working" means here (bars, not vibes):** the model trades only when
its calibrated edge exceeds measured trading costs; on frozen out-of-sample
windows it clears its expectancy and drawdown bars NET OF COSTS; it refuses
ALMOST EVERYTHING when its edge dies (regime change, cost regression,
calibration loss); it has zero lookahead reads; and it reaches a venue paper
environment for 30 consecutive days with zero critical operational errors.
Only then may the owner gate a small live account.

**Anti-goals (a failure even if it "works"):**
- **No guaranteed-profit implication anywhere in the docs.** Markets are
  adversarial and non-stationary; the honest baseline expectancy after
  costs is ZERO. The model's job is to prove, on frozen windows, that its
  edge is positive — and to STOP when it measurably isn't.
- **No comparative scores** vs other traders, funds, or LLMs (source:
  AGI_BENCHMARK §3 carried over). All performance bars are self-referential
  (the model vs its own no-trade baseline and its own cost model).
- No HFT/order-book latency alpha, no leverage/funding/perps, no sentiment
  or LLM alternative data, no multi-strategy claims — v1 scope is spot
  momentum/mean-reversion/flat on a frozen universe with a hard risk
  governor (details in §9, will-not-measure).
- No live code, keys, or accounts until the paper gate's frozen bars pass.

---

## 1. Approaches considered (owner decision 2026-11-05)

| Fork | Options | Decision + why |
|---|---|---|
| **Model core** | (A) Herald substrate only — port WiRULE+Clay wholesale; most faithful, slowest, highest engineering risk. (B) Conventional stack only — fastest, abandons the source lineage. (C) **HYBRID: battle-tested statistical/feature layer + Herald's WiRULE/Clay S1 decision core with calibration and refusal economics.** | **C (HYBRID).** Fastest path to a working model that still IS Herald-descended: the statistical layer (pandas/numpy/statsmodels, deterministic) is commodity engineering; the decision core is where Herald's proven machinery earns its keep. Estimate: ~6–10 focused sessions to M6 below, vs significantly more for A. |
| **Asset class** | Crypto spot (free 24/7 data, retail-executable, paper testnets) vs US equities (market-hour gaps, PDT rules) vs equities intraday LOB (hardest). | **CRYPTO SPOT.** Deepest continuous history (BTC klines from 2017), zero-cost data dumps, no market-hour modeling needed, Binance spot testnet exists, clean fee schedule to model. |
| **Deployment** | Paper-first ladder vs signals-only vs straight to small live. | **PAPER-FIRST LADDER.** Matches source-project culture (GAP-10: every rung pre-registered; nothing graded is regraded). Live access is an owner-gated rung, not a default. |

Trade-off the owner accepted knowingly: the hybrid keeps TWO systems to
maintain (stats layer + substrate) and needs a determinism wall between
them (§4.7). The alternative (A) reused everything but gambled months on
porting the substrate to continuous features before ANY working model
existed; (B) would have discarded the source entirely.

---

## 2. What transfers from Herald (and what is inverted)

### 2.1 The prior trading experiment — §80 G2-TR (source, PASSED)

`specs/AGI_DERIVATION.md` §80 (LIVE canon, not archive): 8/8 bars,
9/9 predictions, 3 seeds, 1237.1 s, wrong 0 — the landed loop decided a
frozen 645-cell synthetic replay (4 planted law segments ×150 cells +
45 injected out-of-scope/spoof cells) where **y=0 meant the correct answer
was REFUSE** (no-signal). Stale state refused at every regime switch before
re-emitting; 0 lookahead reads (structural index audit); 45/45 injected
cells refused `out_of_scope` even when their certificate PASSED
(cert_ok TRUE — scope refusal despite passing confidence).

**§80.7 explicitly banned, for THAT experiment:** PnL/Sharpe/return/
drawdown (would become comparative scores under §3), execution realism
(fills/slippage/fees), portfolio construction, real-market data. **This
project inverts each deliberate ban** — those things are now the objective
— which is legitimate ONLY because the honesty rules move with it (§3–§5).

### 2.2 Direct transfers (carry verbatim)

- **GAP-10 pre-registration:** every rung's bars are frozen and committed
  BEFORE the runner that measures them exists (runner named + verified
  ABSENT at freeze). Absence of results artifact and ledger key is
  re-verified at freeze.
- **Frozen populations (house law 7):** full population, never samples;
  deterministic seeds; snapshots sha-pinned and committed; the eval runner
  performs no network I/O (population is frozen data; §112's network-free
  discipline).
- **No-lookahead structural audit** (§80 TR-3): an adapter-level index
  audit asserts decisions at bar t read only bars ≤ t. Mutation makes it
  fire on purpose.
- **Refusal economics / refusal when no edge** (§80.3 y=0 → REFUSE):
  reinterpreted as the cost-band — when the model's edge does not clear
  measured costs (§5.2's θ), the ONLY correct answer is REFUSE. This is
  §80's own mechanism shape, unchanged.
- **Regime-shift discipline** (§80 TR-4 + DOC-1R's sticky qualification):
  at a detected regime boundary the STALE state must refuse before it
  re-emits; re-qualification inside the following window with
  decisions-to-re-qualify published; sticky qualification so a passing
  state isn't eroded by post-qual noise (the DOC-1 → DOC-1R lesson).
- **Mutations must flip** (§80 TR-8 shape): poisoned feedback → the model
  refuses the poison; lookahead → audit fires; cost model removed → bars
  must degrade (proving costs are load-bearing).
- **Dual record, never regraded** (DOC-1/DOC-1R precedent; S-B closed
  "as disclosed"): a failing gate keeps its measured record; a revised
  gate is a NEW pre-registration (R-suffix), never an edit of the old one.
- **Posterity discipline:** footer-free commits; long commit messages via
  `git commit -F <file>`; append-only outcome rows; explicit
  recommendation-first presentation at every decision point; records in
  `.agent_context/memory/` mirrored into a shared AGENTS.md snapshot.
- **Calibration honesty:** z-threshold/quantizer tables sha-pinned at
  setup, asserted by the runner (§80.3 quantizer discipline).

### 2.3 Deliberate inversions (with their honesty price)

| In §80 (source experiment) | In this project | Price paid |
|---|---|---|
| Planted generating laws | REAL market bars, law unknown | "Wrong 0" is impossible; wrongness redefined structurally (§5.1), not by planted truth |
| PnL/Sharpe banned | Net-of-cost expectancy + drawdown are FIRST-CLASS bars | Bars are self-referential thresholds only; never comparative |
| Synthetic replay, no fills | Cost model + testnet fills | Slippage uncertainty is a bar input, stress-tested ×2 (§4.5) |
| Benchmark-labelled bay | Product-labelled ladder | A working model requires the L3 gate (owner-gated live) |

### 2.4 Source map (internal documentation to import)

| Herald artifact | What the new project imports |
|---|---|
| `specs/AGI_DERIVATION.md` §80 (G2-TR) | The replay-bed shape: frozen stream cells, causal adapter audit, refuse bands, regime-shift refusal, spoof posture discipline |
| `specs/AGI_DERIVATION.md` §80.8 runner-repairs | The FOUR pre-verdict repair lessons (rule-table re-pick by measured sim, unsatisfiable count fix, full-window episode protocol, threshold retune) — read before designing any population/statistics sim |
| `specs/AGI_DERIVATION.md` §112 (MATH-1R) | Real-data population discipline on frozen snapshots (sha-pinned, committed, exclusion histogram) + "no installs mid-gate"; the Z=3.5 elision lesson: a mechanism constant may be runner-tuned when a disclosed cause + independent checker exists |
| `experiments/x1_thinker.py`, `x2_math.py` | The mechanism wiring to vendor: `Cues`/`A`/`roles`/`handoff`, `build_world`/`build_mclay`/`build_codebook`, `mode_a`, `write_number`, Z-verdict/refuse plumbing |
| `experiments/x28_wirule.py` (freeze-set, content-sha-pinned) | WiRULE weightless counter core — the S1 kernel |
| `src/clay.py` (freeze-set) | Clay substrate: 65,536 ternary coords, 131,072 B checkpoints, `_seed_of`, erase-to-H0 lifecycle |
| `experiments/alpha_register.py` | 25K co-residency reference (Phase B/later rungs only) |
| `AGI_BENCHMARK.md` §3 | Honesty rules that carry: benchmark not comparative; negative results recorded |
| `AGI_CHECKLIST.md` | Board-card pattern (kanban of gated lanes) for the new repo |
| `.agent_context/memory/*.md` + AGENTS.md snapshot | Shared-memory janitor pattern, recommendation-first ruling, footer-free `-F` commits |
| §91/X2 math mechanism | The model's arithmetic kernel is ALREADY exact (MATH-1-style exactness is the accounting bar's foundation) |

---

## 3. Architecture (hybrid, five layers)

```
L0 data ─→ L1 statistical layer ─→ L2 S1 decision core ─→ L3 risk governor ─→ L4 execution
 (frozen)     (deterministic)        (WiRULE+Clay)        (hard caps)         (paper first)
        ▲──────────────── causal feedback: realized bar t+1 only ────────────────┘
```

### 3.1 L0 — data layer

- **Binance public dumps** (data.binance.vision) only — NO exchange API
  calls during graded runs. Monthly spot klines per pair per interval as
  `ZIP→CSV`, fields as shipped: `open_time, open, high, low, close,
  volume, close_time, quote_asset_volume, number_of_trades,
  taker_buy_base_vol, taker_buy_quote_vol, ignore`.
- Pull ONCE into `bench_data/binance_klines/<PAIR>/<INTERVAL>/` (the
  source repo's frozen-snapshot convention), build `snapshot.sha256`
  manifest with per-file hashes; `.gitattributes` `-text` for all data
  files (byte-exact, the GSM8K lesson); packets land with the sha printed
  in the commit body.
- **Gap protocol:** exchange downtime → missing rows are re-downloaded in
  separate repair packets; repair packets are sha-pinned rows APPENDED to
  the manifest with a written cause (never silently merged).
- Candles are the v1 granularity: **1h bars** primary (≥ 79k bars/coin
  history ≥ 2019), 1d and 4h as coarser views; 1m is the Phase-B ladder
  (out of v1 bars).

### 3.2 L1 — statistical layer (deterministic, interpretable, offline)

All features are causal functions of bars ≤ t. Defaults:

- **Returns:** log close-to-close, windows {1, 4, 16, 64} bars.
- **Position in range:** close's percentile position in the trailing
  16-bar range (the §80 adapter's feature shape).
- **Volume:** volume-delta sign (taker_buy_base vs prior window), quote-
  volume concentration.
- **Volatility:** rolling realized vol (20, 100 bars), simple annualized;
  **regime state:** vol percentile vs trailing 500 bars (<25 / mid / >75
  pct) — the regime classifier for §3.4's switch discipline.
- **Autocorrelation diagnostics** (optional, for window selection, not
  per-bar features): ACF decay, Ljung-Box on residuals after a simple
  AR fit, Hurst exponent snapshots — these feed DESIGN-TIME analysis
  (which windows/horizons are plausibly tradeable) and are published in
  the analysis packet; they never gate a bar by themselves.
- **GARCH-family conditional vol (ANALYSIS-ONLY in v1, builder-check
  resolution):** GARCH(1,1)/EGARCH on in-window returns lives in the L0
  design packet (regime analysis, feasibility) — it is NOT a load-bearing
  M2 deliverable and does NOT scale position size in v1. Position sizing
  is FIXED notional at entry (§3.4 rule 1). Vol-scaled sizing may become
  its own later-rung pre-registration.
- **Quantizer (the S1 boundary):** all L1 per-bar features collapse to a
  frozen ±1 vector, K features (start K=8–10, mirroring §80.3's 8-feature
  adapter): return signs, position-in-range, range expansion, volume
  delta, gap, vol-regime bits. Table enumeration is static; its sha is
  asserted by every runner (quantizer lock, inherited).

### 3.3 L2 — S1 decision core (Herald's kernel, adapted)

- **WiRULE** (weightless NN counter state + regenerated-rule readout) as
  the fast classifier over the quantized window; **Clay** shapes/codes
  carry the certified rule families; checkpoints are 131,072 B, byte-
  neutral; session erase-to-H0 lifecycle unchanged (report, but held to
  substrate granularity rather than bars in v1).
- **Training:** classic conditional counter registration over the
  TRAIN window's stream, per the §80/§91 study-episode protocol (one
  episode per arrived label, full recency window only — the §80.8 repair
  (3) lesson). Registration runs on the frozen TRAIN population only.
- **Typed S1 verdicts:** `BUY(+1) / SELL(−1) / FLAT(0*) / REFUSE`.
  `y=0` (zero-band class, §5.2) is the REFUSE answer: the model emits a
  trade ONLY when its mapped class is ±1 AND its calibration score (z)
  clears the per-window threshold (θ_z); under threshold → REFUSE.
  The z-threshold is calibrated per seed on a held-out slice of the same
  window and is part of the pre-registration, not a knob to tune after
  seeing test results (the §112 Z-elision lesson: tuning requires a
  disclosed cause + an independent checker, disclosed live).
- **Calibrated response (the A1 core, Phase-A):** emitted = confidence
  report (class, z, calibration ECE on the window) + a typed trade order.
  In Phase-A, certainty proof lives in the A-bars (§5), not yet in a
  separate A2 ledger.
- **θ_z calibration slice (leakage rule, builder-check resolution):**
  calibrated per seed on a HELD-OUT TAIL SLICE INSIDE THAT WINDOW'S
  TRAIN FOLD (final 15% of the fold, pop-style disjoint block; the fold's
  labels are causal by construction) — NEVER from the graded test
  window. The threshold table sha prints in the run manifest.
- **Emission contract (v1, builder-check resolution — the action space):**
  S1 emits `(class ∈ {+1, 0, −1}, z)` per decision cell; the executor maps:
  - `c=0` → **REFUSE** (the zero-band; the §80 y=0 shape verbatim).
  - `c=+1, flat, z ≥ θ_z, vol-filter passes → OPEN_LONG` at next-bar-open.
  - `c=+1, already long → HOLD` (no re-entry logic in v1).
  - `c=−1, long → EXIT_EARLY` at next-bar-open (explicit early exit —
    listed as a licensed exit beside stop/target).
  - `c=−1, flat → REFUSE` with cause `no_inventory_short` (spot has no
    naked short; recorded as a refusal-with-cause, counted in refusal
    stats — **not** an A-2 wrong).
  - any `c=±1` with `z < θ_z` or vol-filter failing → **REFUSE** with the
    published cause.
  - After an early exit inside a horizon: NO re-entry until the next
    decision cell (one decision chain per horizon). Mid-horizon S1 calls
    are still made and scored for the ledger; they are just not executed.
  - FLAT is not an independent verdict; `c=0` IS the flat/no-signal class.
- **Honesty note (adopted from the source's own end-to-end audit):** the
  S1 core alone is a classifier on quantized features; NO claim of market
  understanding is made BY ITS ARCHITECTURE; the claim is made by its
  measured, non-comparative bars. Any narrative beyond that is forbidden
  in commit messages and docs.

### 3.4 L3 — risk governor (hand-written, NOT learned, changes never without new pre-registration)

Hard-coded, non-negotiable, always-on; these are the anti-melt safeguards:

1. **Per-trade size = 2.0% of equity, notional AT ENTRY, fixed (no
   volatility scaling in v1).**
2. **Max concurrent positions:** 1 (Phase-A/B), 3 (Phase-C, co-sized).
3. **Max daily realized loss ≤ 1.0% equity → REFUSE-ONLY for the day**
   (kill-switch, must record its cause in the ledger).
4. **Max drawdown ≤ 10% equity → full stop + manual re-arming only**
   (owner or a signed recovery pre-registration that re-qualifies the core
   on fresh windows first — sticky qualification discipline).
5. **Vol-regime filter:** no new positions in the top vol-percentile
   regime unless the model is long-vol aware (v1: simply refuse).
6. **Event blackout:** exchange-downtime / repair-packet / snapshot-gap
   windows are structurally REFUSE windows (no health data → no trades).

### 3.5 L4 — execution (paper-first)

- **Phase-A/B:** deterministic backtester with an explicit event loop,
  hand-rolled (no vectorbt/quantlib magic in graded runs — determinism and
  auditability outweigh convenience; others allowed ONLY as cross-check
  tools publishing secondary numbers when they disagree and by how much).
- **Cost model (frozen, load-bearing):** Binance spot taker fee 0.10% per
  side at VIP0 (≈ 20 bps round-trip) **UNDER-ESTIMATE enforced:** an
  optional stress multiplier ×2 (40 bps) that ALL expectancy bars must
  survive; slippage floor: max(2 bps, ½ of the bar's range if a stop
  would be hit mid-bar, computed conservatively).
- **Stop/target (v1, deterministic — builder-check resolution):** at
  entry, stop = 3×ATR(16) below entry; target = 2R above entry (1R = entry
  − stop). Both levels are deterministic functions of frozen bar data at
  the entry bar. Mid-bar touch → fill at the LEVEL ± slippage floor
  (conservative side); gap-through the level instead of touching → fill
  at that bar's open (worse side, deterministic). If neither hits, exit at
  the horizon end per the schedule below.
- **Fills in the backtester:** next-bar-open execution for all
  close-time decisions (no same-bar fills — structurally forbidden by the
  causal law); horizon end fills at open(bar t+h); no partial-fill
  modeling in v1 (documented omission).
- **Phase-C (paper):** Binance **Spot Testnet** (or ccxt's paper mode over
  the testnet REST), same order surface as live, 30-day continuity bar
  (§7 L2). Keys stay in env vars; the agent never logs secrets.

### 3.6 Determinism wall (the hybrid's discipline requirement)

- L1+backtester: pure `numpy`/`pandas` determinism (no GPU). L2 substrate:
  torch CPU tensors + the source project's seeded `_seed_of` keying.
- Every graded run prints the run manifest: package versions (pinned,
  mirror of the source's `results.json` pattern), seed list, population
  sha, quantizer sha, threshold table sha.
- Time-of-day/no wall-clock in decision paths, tests only artifacts.

---

## 4. Training-data plan (recommendations, frozen-first)

### 4.1 Universe & granularity (recommendation)

- **Phase-A/B v1 universe: BTCUSDT only.** Deepest, most liquid, least
  noise; drops cross-pair selection out of the hardest first pass.
- **Add ETHUSDT in Phase-B** as the second stream (co-residency of two
  instruments = the §80 CERTIFIED-family scope-widening exercise: each
  instrument declares its decision family exactly like §80.2's
  per-instrument declaration law; scope widens only through
  pre-registration).
- **Granularity: 1h primary** (clean 24/7 continuous history ≥ Aug 2017
  for BTC), with 4h/1d for regime views; 1m reserved for Phase-C work
  (never graded in v1).
- Standalone pairs beyond two instruments: a LATER scope-widening
  pre-registration, never in passing.

### 4.2 Acquisition sources (in priority order; all free)

1. **data.binance.vision** monthly ZIPs — spot klines per interval:
   `data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-YM.zip` (BTC 1h from
   2017-08); plus daily-current files for delta updates. ~4.7M 1h bars for
   BTC (2017 → 2026-11); ~79k bars since 2019-01.
2. **ccxt** (later, adapter-development only, Phase-B testnet): never used
   to build graded populations (either testnet or frozen dumps only).
3. **Alternate/secondary checks (NOT part of graded data):** Yahoo Finance
   / CryptoDataDownload / TradingView — allowed only for plausibility
   cross-checks outside graded runs (a disagreement itself is published
   data-hygiene info — the 3-source corroboration idea carried over).

### 4.3 Slices (the frozen population protocol)

For every graded run, the population is declared in a pre-registration
**before** the runner exists:

- **TRAIN:** 2019-01-01 → 2023-06-30 (4.5y ≈ 39,800 1h bars BTC).
- **EMBARGO:** 7 days (168 bars) after every walk-forward train window —
  kills serial-correlation leakage at the seam (purged-walk-forward).
- **TEST (walk-forward, monthly rolling, sliding on bar counts):** windows
  of 30d test / 180d train, **graded span 2023-07-01 → 2026-04-30 = 34
  monthly windows at L1**; results published per-window AND aggregated.
- **HELD-OUT seal:** 2026-05-01 → 2026-10-31 (6 windows) is part of the
  full 40-month span but touches NO bar of any graded L1 run; it opens at
  its own separate gate after L1 passes (same bars, own pre-registration;
  declared in the first pre-reg from day one, never touched by design-time
  analysis). *(Builder-check resolution: the earlier draft's "≈40 windows"
  counted the seal; L1 grades 34 — pinned here so P4 can freeze on it.)*
- Every window boundary is frozen as integer indices in the pre-reg; the
  runner asserts the blob sha of `bench_data/...` at setup (population
  pin, as at §112).

### 4.4 Labels (the edge contract)

Momentum/mean-reversion/flat via the S1 core, labels so constructed:
- **Label = realized-path label (builder-check resolution):** the label
  for a decision cell t is the net-of-cost return of the DETERMINISTIC
  FILL PATH the backtester would realize if the full trade were taken at
  that cell (entry open(t+1), exits at stop/target/horizon end per §3.5's
  conventions). This makes label edge == realizable edge by construction
  and A-3's reconciliation almost structural. Computed at close t from
  frozen bars; REVEALED to training only at path end (the §80 feedback
  law: cell t's label arrives causally at t+h, never the future bars).
- **Zero-band θ (the REFUSE class):** net cost = round-trip taker fees
  (20 bps) + stress slippage (2 bps/side default) ⇒ labels:
  +1 if label ≥ θ, −1 if ≤ −θ, REFUSE(0) otherwise. Default θ from a
  per-window grid pre-registration — v1 boot uses **θ = 30 bps** (costs
  22 bps + 8 bps edge floor) — so a correct trade means the mechanism is
  confident the trade covers its measured costs plus an edge floor;
  anything within the band is by definition no-edge and the ONLY correct
  answer is REFUSE. **This single decision is the honest core of the
  whole project; relabeling it downward (chasing hit-rate) is the
  classic fraud-adjacent move and is forbidden by the bars (A-2 refuses
  in-band trades; A-5's expectancy bar sits on top of it).**
- Near band and stale labels are the same REFUSE class (no ambiguous
  third answer FLAT — `c=0` is the only flat/no-signal class).

### 4.5 Class balance & the "wrong" definition

Per window, the REFUSE band is expected to claim ~55–75% of cells at h=4h
on BTC (θ 30 bps vs ~0.9–1.2% per-4h σ): the model MUST be refusing more
often than trading — §80's TR-2 floor is inverted structurally: **an
emission inside the refuse band is a wrong** (structurally measurable
WITHOUT knowing future prices: the class map is a deterministic function
of the frozen label universe — same-slice identically to §80's y=0).
Wrongness is thus decisively defined, not "a losing trade" per se (losing
trades are a drawdown/expectancy matter, gated separately).

### 4.6 Data-quality gates (pre-registration, published with every packet)

- Void bars, zero-volume bars, exchange-downtime patches → dropped with
  drop-timestamps listed; a repair packet reghash-refers the gap.
- Duplicate rows (the dumps' `close_time` duplicates) → de-duplicated with
  crystal cause in the manifest.
- **Survivorship:** universe freezes at PULL-TIME with delisted pairs
  INCLUDED in the manifest; v1 (BTC(+ETH)) is unaffected but the
  convention holds for later scope-widenings.
- The manifest is the ONLY source of truth — every graded runner re-derives
  its population by asserting the manifest sha, никогда by trusting a
  local copy in place.

### 4.7 What is NOT in the data v1

Order-book depth, funding/perp rates, sentiment, on-chain, macro series,
news. Phase-C gate may add funding-rate READS as health data only (never
features) if a later pre-reg says so. All else stays will-not-measure.

---

## 5. Evaluation bars, A-1..A-8 (drafted; frozen at the rung's own GAP-10)

Declared at pre-registration per graded run, bars frozen before the runner
exists. **A run PASSes iff, on every seed (default 3 seeds, sha-keyed per
the source's `g2tr|seed|v1` pattern) and every frozen TEST window:**

| # | bar |
|---|---|
| **A-1 no lookahead** | adapter's index audit: 0 reads beyond t per decision; mutation (b) makes it fire on the sampled cell set |
| **A-2 refuse-band discipline** | 0 trades emitted inside the zero-band (the y=0 → REFUSE class); REFUSE cells' emission share published; refusals carry published causes; no stream exhaustion (the §80 TR-2/TR-5 shape) |
| **A-3 cost-honest accounting** | every ledger PnL entry reconciles EXACTLY (kernel-exact math per N-1) to the fee/slippage model and to the frozen horizon price path; no phantom profit; every fill attributed to next-bar-open of its decision bar; the two-way reconciliation ties to 0 discrepancy |
| **A-4 risk caps hold** | 0 breaches of §3.4's caps; kill-switch events published with causes; position-size series published per window |
| **A-5 out-of-sample expectancy** | TWO floors, BOTH per window, BOTH net of stress costs (×2): (i) mean per-trade net expectancy ≥ +5 bps; (ii) window net equity PnL ≥ 0 with sizing fixed at 2.0% notional-at-entry (per-trade and equity denominators pinned separately — a floor recorded against the wrong denominator is a design defect, not a measured failure). Paired vs the no-trade baseline = exactly 0 by construction. **Kill clause:** after ANY daily kill-switch trip (§3.4 rule 3) inside a window, the posture for the REST of that window is REFUSE-only; any trade taken after a trip is itself a bar failure. |
| **A-6 regime switches** | at vol-percentile regime boundary events (≥ N events/window pre-counted), the state refuses at least once before re-emitting; sticky re-qualification; decisions-to-re-qualify published (the DOC-1R sticky shape) |
| **A-7 mutations flip** | (a) poisoned feedback: flip labels on the stream → held-out collapse to refusals at 0 wrong-in-band; (b) lookahead feed → A-1 audit fires + wrong-in-band appears; (c) **cost-model off → bars degrade measurably** (expectancy/in-band metrics move in the obviously-fraud-favoring direction, proving the cost model is load-bearing, not decorative) |
| **A-8 lifecycle + reproducibility** | run manifest replays bit-exact under pinned versions; substrate checkpoints byte-neutral; all graded runs re-runnable from the frozen snapshot with NO network I/O |

**Overall PASS:** all eight bars, every seed, every window. A failure is
recorded AS MEASURED; a redesign = new R-suffix pre-registration (never a
regrade — dual record).

**Predictions P1..P6 at each rung (non-binding):** P1 in-run population ==
frozen pin exactly; P2 refuse-band share within its frozen prior ±
tolerance; P3 regime events per window within prior range; P4 window count
and boundaries exact; P5 run wall-clock inside an honest window; P6 zero
network reads during a graded run. Misses recorded, never regraded
non-bindingly (as at §112/SR1).

**Boot numbers for the first rung (RECOMMENDATION, owner-confirmed at that
rung's freeze):** seeds [1,2,3]; K=8 quantizer; h=4 bars; θ=30 bps;
windows per §4.3; stress costs ×2 covered; expectancy floor per window:
≥ +5 bps average across windows AND ≥ −15 bps in the worst window
(disclosure: the FIRST graded rung is allowed a floor this small; raising
it is rung-2's problem); max-drawdown cap 10%.

---

## 6. Paper-first ladder (L0 → L3, each rung its own GAP-10)

| Rung | What happens | Gate to next |
|---|---|---|
| **L0 design-time analysis** | statistical packets over frozen TRAIN (ACF, Hurst, vol regimes, feasibility of θ) — published analysis, never graded, never touches held-out | feasible θ/h survive honesty check |
| **L1 walk-forward backtest** | the A-bars run over the frozen windows (this is THE graded rung, 3 seeds) | all A-bars + predictions; replay manifest exact |
| **L2 venue paper** | same code against Binance Spot Testnet live feed for ≥ 30 consecutive calendar days: ops errors 0 (order rejects, fills≠sim fills within tolerance, key/permission faults → fail), risk caps hold, no restarts unexplained | paper ledger reconciles to the A-3 accounting within tolerance; owner reads the record |
| **L3 small live** | strict owner-gated: fresh pre-registration (bars TURN INTO risk-absolute bars: max loss/day, max drawdown, secret handling); small capital; kill-switch armed; positions ≤ 1 | unlikely early; every rung-gap is honest |

Nothing in the ladder auto-advances. Each rung names its runner BEFORE the
runner exists.

---

## 7. Repo & environment of the new project

- **New directory (owner names it).** Suggested pattern mirror: memory
  (.agent_context/memory + AGENTS.md snapshot), specs/, experiments/,
  bench_data/, results/, src/, .venv. Untracked .agent_context carried
  (as here).
- **Python 3.11** (source's version), venv-first; never system Python (the
  torchhd/torch lesson); NEVER run inline `python -c` through PowerShell
  (write a script file); LONG commands get output redirection +
  backgrounding, log to `.artifacts/`, NEVER the repo root.
- **Pinned deps:** numpy, pandas, statsmodels (`arch` optional,
  analysis-only at L0 — never a graded-run dependency), torch (CPU),
  **no heavy framework for the backtester** (hand-rolled event loop),
  ccxt (Phase-C only rung). Every graded run prints its versions and pins
  them in a lockfile.
- **Vendored source files with content-sha pins** (the freeze-culture
  carried over): the S1 kernel (`x28_wirule.py` + friends), `clay.py`,
  quantizer templates, and the quantize-table generator. The pins live in
  the new repo's own ledger on arrival, BEFORE first graded run, exactly
  like §112's reference-freeze discipline.
- **Windows notes carried:** `git commit -F` messages; schtask/Start-
  Process detachment gotchas (`STATUS_CONTROL_C_EXIT` when sessions die —
  incremental artifact writes per completed seed are the standing
  resilience rule (the 2026-10-26 MATH-1R run #2 lesson)).

---

## 8. Build milestones (implementation order)

| M | Deliverable | Bars touched |
|---|---|---|
| M0 | repo bootstrap, vendor map with sha pins, house-law docs, GAP-10 boot spec | — |
| M1 | data pipeline + frozen snapshot manifests (BTC 1h; ETH 1h next) | A-8 inputs |
| M2 | L1 statistical layer + quantizer, unit-tested determinism, sha-pinned table | A-1 adapter |
| M3 | backtester + cost model + exact accounting reel | A-3, A-4 |
| M4 | S1 core training on window 1 + calibration + refusal plumbing | A-2 core |
| M5 | walk-forward harness (windows/embargo/seal from §4.3) | A-5, A-8 |
| M6 | **GAP-10 freeze of the L1 graded pre-reg (bars+predictions+mutations) → runner → graded run** | **A-1..A-8 all** |
| M7 | testnet adapter (paper-ops rung pre-reg frozen first) | L2 rung |
| M8 | L3 live policy spec (owner-gated; NO code until sign-off) | L3 rung |

M4 and M6 are the two places where a failed bar is informative — never a
regrade; the R-suffix path is the only response to a design miss.

---

## 9. Will-not-measure (v1)

- Comparative performance vs other traders/funds/LLMs, any leaderboard.
- HFT, order-book depth signals, latency alpha, maker-only strategies
  (taker-only cost model is v1's honesty floor).
- Leverage, futures/perps, funding arb, shorting beyond the mechanism's
  sell side (v1 trades spot long/flat + short-closure only where sell is
  legal → spot sell = closing inventory; NO naked short).
- Sentiment/news/on-chain/macro features; alternative-data alpha.
- Cross-pair co-integration or portfolio optimization beyond §3.4's caps.
- The source project's AGI claims (this project makes NO AGI/super-
  intelligence claims; the models stay named as mechanisms).

---

## 10. Open decisions (owner's, listed recommendation-first)

1. **Venue endpoint confirmation** — Binance global vs regional endpoint
   (data dumps are region-agnostic; testnet choice matters at M7 only).
   Recommendation: decide at M7, nothing blocks M0–M6.
2. **Project name + repo directory.** Recommendation: separate directory
   beside this one, e.g. `~/Project_Kestrel` (placeholder; owner's call).
3. **Universe expansion beyond BTC(+ETH)** — later pre-reg, no blocker.
4. **Capital size for L3** — needed only at the L3 pre-registration;
   recommendation: the pre-reg names an absolute cap (e.g. ≤ 2% of
   non-essential savings) rather than a currency amount.

---

*Prepared as the master spec for the new project. On owner sign-off this
document becomes the new repo's SPEC-1 (committed there at M0, before any
code), and §5/§6 freeze-by-freeze under that repo's own GAP-10 law.*

---

## Amendments

| date | change | why |
|---|---|---|
| 2026-11-05 | **Builder check folded (six questions, all resolved in-document, zero promoted to the owner):** (1) windows/seal contradiction fixed — L1 grades 34 windows (2023-07→2026-04); the 6-month seal opens at its own later gate (§4.3). (2) Emission contract defined — `c=0` is the only flat class; SELL-with-no-inventory is a refusal-with-cause, structurally prohibited from being a naked short, not an A-2 wrong; EXIT_EARLY licensed; no re-entry inside a horizon (§3.3). (3) θ_z calibration slice pinned INSIDE the train fold's tail, never the graded window (§3.3). (4) stop/target levels + mid-bar fill conventions made deterministic functions of frozen OHLC; labels unified with the accounting fill path (realized-path labels), removing the close→open label/accounting offset (§3.5, §4.4). (5) A-5 split into per-trade bps floor AND window equity floor with fixed 2% notional sizing; GARCH demoted to L0-analysis-only (§3.2, §3.4, §5). (6) kill clause mapped — any daily kill trip inside a window forces REFUSE-only for the window's remainder; trading past it is the bar failure (§5 A-5). | fresh builder subagent review of the v1 draft; house pattern: pre-deliverable check, disclosed repairs, nothing hidden |
