# Vendor Map — content-sha pins (M0.2)

**Discipline (spec §10 / Herald §112 reference-freeze):** vendored Herald sources
arrive with content-sha256 pins recorded in THIS repo's own ledger — in
`specs/VENDOR_MAP.md` (human) and `specs/vendor_pins.json` (machine,
asserted by runners at setup) — recorded **before** the first graded run.
Pinned at 2026-11-05. A runner that finds a sha mismatch **refuses to run**.
Changing a vendored file is a redesign: new R-suffix pre-registration, never a
silent edit (dual record).

| # | source (Herald) | vendored (Kestrel) | sha256 | bytes |
|---|---|---|---|---|
| 1 | `experiments/x28_wirule.py` | `src/vendor/x28_wirule.py` | `8a77c0ad672e2edfe1ae35465fc35fa0392076ef318d2dffd75d7f63da610dbe` | 16867 |
| 2 | `src/clay.py` | `src/vendor/clay.py` | `c9dd9396160cac43aaccb6dfcf1e2d7bfe686fab1da7a12d21354964ab1e088f` | 14300 |
| 3 | `src/paths.py` | `src/vendor/paths.py` | `aea5ac971d0f3ee03febcbca8ca5937a4e04c5d4fa9c733a970906a5155c3048` | 2657 |
| 4 | `experiments/x20_learn_probe.py` | `src/vendor/x20_learn_probe.py` | `0459b4e9a3363542f100660853701ab0eefe732e7b43bab5b77a9f4212087549` | 21911 |
| 5 | `experiments/tr1_replay.py` | `src/vendor/tr1_replay.py` | `10bd24afbc22484b0ec8be1dfe31fd208fcd7a92fceac9687c6830ced0c7cc6a` | 63080 |

## Roles

1. **`x28_wirule.py`** — the S1 kernel: WiRULE, the weightless network
   (derivation §61). Knowledge = literal-addressed counters; rule regenerated
   at readout from evidence `e(lit) = c[+][lit] − c[−][lit]` (ARITY=3), exact
   match at readout. Gates frozen 61.2 (E_MIN=500, E_LIT=64, SEP_MIN=64).
2. **`clay.py`** — the Clay substrate: hyperdimensional coding/copy machinery
   (`Clay`, CLAY_BYTES, atom, codebook, fields_to_vectors, roles_vector);
   byte-neutral 131,072 B checkpoints (A-8 condition).
3. **`paths.py`** — directory contract imported by `x28_wirule.py` (S1 friend).
4. **`x20_learn_probe.py`** — population source imported by `x28_wirule.py`
   (N_BITS, CHECKPOINTS, make_stream, make_heldout, hidden_rule; S1 friend;
   needs torch).
5. **`tr1_replay.py`** — Herald trading-replay runner, vendored whole so both
   quantizer artifacts are pinned without surgery:
   - **Quantizer templates:** `RULES` + `RULE_TABLE_SHA` (L188–195) and
     `QUANTIZER` + `QUANTIZER_SHA` (L196–199) — the 8 ±1 feature templates
     `ret{1,4,8,16}:0, pos16:0.85, rexp:1.0, vdel:0, gap:0` and the four
     frozen S1–S4 rule tuples (Seg names L201).
   - **Quantize-table generator:** the frozen bar-window feature adapter
     L282–347 — `Audit` (TR-3 index audit), `_sign`, `adapter()` (8 quantized
     ±1 features + regime-shift flag from `FLAG`), plus `make_x()` bit-landing
     (L350–356) and `planted_y()` (L359+) for the synthetic-side label path.

## Assertion contract (M2.2 onward)

- Vendored files are **frozen reference sources** (pin = content sha256),
  recorded in `specs/vendor_pins.json`; every graded runner asserts all pins
  at setup and refuses on mismatch.
- The Herald experiment import-closure of `tr1_replay.py` (x31_coverage →
  x29, x30, decide_stage → …) is deliberately NOT vendored: those siblings
  are harness plants for Herald's own benches, not for Kestrel real-data
  runs. Kestrel's quantizer module (M2) extracts the frozen constants
  (`QUANTIZER`, `RULES`, their shas) from the pinned bytes and asserts their
  `json.dumps` serialization shas — the quantizer lock, inherited §80.3.
- `clay.py` is runtime-importable by Kestrel (verified: imports clean atop
  numpy 2.4.6 / torch 2.14.1+cpu / torch-hd 5.8.4, 2026-11-05).
- Dependency note (docs, not pins): `clay.py` imports numpy, torch, **torchhd**;
  `x20_learn_probe.py` imports torch — hence `requirements.txt` pins both.
