# L1 Graded Pre-Registration — R1 (R-suffix redesign)

R-suffix redesign of the S1 core readout, registered 2026-11-05 AFTER the
original L1 graded run (commit dcfc9f1) recorded A-5 FAIL as measured
(expectancy -5122 bps, refuse share 0.919, 1998 trades). The original
A-5 FAIL remains recorded (dual record); this pre-reg does NOT regrade it.

## Why R1

Diagnostic (`.artifacts/m6_rdiag.py`): the original WiRULE readout (single
3-literal conjunction: +1 if all top-3 literals active else -1) has NEGATIVE
predictive power on BTCUSDT 1h at h=4 (corr(pred,label) = -0.163;
pred=+1 cells mean label -0.474). The mechanism learned a mean-reversion
shape but its readout forces -1 for every non-matching cell, inverting the
signal. BTCUSDT 4h returns show strong momentum (autocorr 0.72), so the
correct direction is momentum, not mean-reversion.

## Redesign (mechanism-faithful, readout changed)

- Counters (c[0]/c[1]) and registration unchanged (study-episode protocol).
- Readout changed from single-conjunction to dual-plane evidence SCORING:
  score(x) = sum_{lit in sat_lits(x)} (c[0][lit] - c[1][lit]).
  predict: +1 if score > 0, -1 if score < 0, None if score == 0.
  z = |score| / (E_LIT * N_LIT)  (per-cell, continuous).
- Confidence gate: t >= E_MIN (unchanged). E_LIT/SEP_MIN no longer gate
  (scoring doesn't need a single conjunction).
- theta_z calibrated on held-out tail at the 0.6 quantile (was 0.7).
- Everything else (quantizer, features, backtester, governor, manifest)
  unchanged. Quantizer sha and feature set are NOT touched (M2 frozen).

## Identity (GAP-10 slots, R1)

| slot | frozen value |
|---|---|
| runner | `experiments/l1_walkforward_R1.py` |
| artifact | `results/l1_walkforward_R1.json` |
| ledger key | `kestrel_beds.L1.R1` |
| artifact mode | incremental writes per completed seed |

## Bars (A-1..A-8) — re-evaluated under R1

Same bar text as specs/l1_pre_reg.md. A-5 floor: >= +5 bps mean per trade
AND window equity >= 0 (net of x2 stress).

## Absence verification (2026-11-05)

- experiments/l1_walkforward_R1.py — ABSENT at freeze
- results/l1_walkforward_R1.json — ABSENT at freeze
- kestrel_beds.L1.R1 — ABSENT at freeze

## Dual record

The original L1 graded run (commit dcfc9f1, results/l1_walkforward.json)
with A-5 FAIL remains recorded as measured. This R1 pre-reg is a NEW
design, not a regrade.
