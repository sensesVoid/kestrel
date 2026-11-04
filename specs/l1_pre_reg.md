# L1 Graded Pre-Registration (M6.1, GAP-10 freeze)

Frozen 2026-11-05 BEFORE the runner exists. Runner/artifact/ledger names are
fixed here and verified ABSENT at freeze (M6.2). Any change after the first
graded run requires a new R-suffix pre-registration (dual record).

## Identity (GAP-10 slots)

| slot | frozen value | verified |
|---|---|---|
| runner | `experiments/l1_walkforward.py` | ABSENT at freeze (see M6.2) |
| artifact | `results/l1_walkforward.json` | ABSENT at freeze |
| ledger key | `kestrel_beds.L1` | ABSENT at freeze (only reserved-name mention in specs/GAP10_BOOT.md) |
| artifact mode | incremental writes per completed seed (HL-7 Windows rule) | design contract |

## Frozen parameters

- seeds: [1, 2, 3] (sha-keyed per source `g2tr|seed|v1`)
- quantizer: K=8 (frozen QUANTIZER sha, asserted at import)
- horizon h = 4 bars
- zero-band theta = 30 bps (costs 22 bps + 8 bps edge floor)
- windows: 34 monthly (2023-07 -> 2026-04), 30d test / 180d train, 7-day
  embargo; boundaries frozen as integer bar indices (HL-2)
- held-out seal: 2026-05-01 -> 2026-10-31 (untouched by L1)
- stress costs: x2 (40 bps RT)
- sizing: 2.0% notional at entry, fixed
- population: bench_data/binance_klines snapshot.sha256 (self_sha 01b1c8cc...)
- no network I/O in graded runs (A-8)

## Bars (A-1..A-8) — frozen text (spec section 5)

| Bar | text |
|---|---|
| A-1 | no lookahead: adapter index audit 0 reads beyond t per decision; mutation (b) makes it fire on the sampled cell set |
| A-2 | refuse-band discipline: 0 trades emitted inside the zero-band; REFUSE cells' emission share published; refusals carry published causes; no stream exhaustion |
| A-3 | cost-honest accounting: every ledger PnL entry reconciles EXACTLY to fee/slippage model + frozen horizon price path; two-way reconciliation ties to 0 |
| A-4 | risk caps hold: 0 breaches of section 3.4 caps; kill-switch events published with causes; position-size series published per window |
| A-5 | OOS expectancy: (i) mean per-trade net expectancy >= +5 bps; (ii) window net equity PnL >= 0 (both net of x2 stress). Kill clause: after any daily kill trip, posture for rest of window is REFUSE-only |
| A-6 | regime switches: at vol-percentile boundary events (>= N events/window pre-counted), state refuses at least once before re-emitting; sticky re-qualification |
| A-7 | mutations flip: (a) poisoned feedback -> held-out collapse to refusals at 0 wrong-in-band; (b) lookahead feed -> A-1 audit fires + wrong-in-band appears; (c) cost-model off -> bars degrade measurably |
| A-8 | lifecycle + reproducibility: run manifest replays bit-exact; substrate checkpoints byte-neutral; no network I/O |

## Predictions P1..P6 (non-binding, recorded)

- P1: in-run population == frozen pin exactly
- P2: refuse-band share within frozen prior (55-75%) +/- tolerance
- P3: regime events per window within prior range
- P4: window count and boundaries exact (34 windows)
- P5: run wall-clock inside an honest window
- P6: zero network reads during a graded run

Boot numbers (recommendation, owner-confirmed): seeds [1,2,3]; K=8; h=4;
theta=30 bps; stress x2; expectancy floor per window >= +5 bps average
across windows and >= -15 bps worst window; max-drawdown cap 10%.

## Mutations (A-7)

- (a) poisoned feedback: flip labels on the stream -> held-out collapse to
  refusals at 0 wrong-in-band
- (b) lookahead feed: adapter reads bars t+1..t+W -> A-1 audit fires +
  wrong-in-band appears
- (c) cost-model off: disable fees/slippage -> expectancy/in-band metrics
  move in the obviously-fraud-favoring direction

## Four pre-verdict repair disclosures (HL-1/HL-6)

Recorded here before verdict if any repair is applied during the run:
- (none yet; to be appended by the runner if a repair is applied)

## Absence verification (M6.2, 2026-11-05)

- experiments/l1_walkforward.py — ABSENT (verified)
- results/l1_walkforward.json — ABSENT (verified)
- kestrel_beds.L1 ledger key — ABSENT (only reserved-name mention in
  specs/GAP10_BOOT.md, which is the reservation doc, not code)

## R-suffix hook

Any redesign after a graded failure = new R-suffix pre-registration, never an
edit of this document (dual record).
