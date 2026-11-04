"""Paths for the Clay project.

One place that knows the layout, so gate runners and diagnostics do not each
hard-code a relative path and silently break when moved.

    specs/      the AGI board, findings and handoff (source of truth); specs/archive/ holds the 15 pre-AGI specs
    src/        the substrate (clay.py) and the fresh-process verifier
    experiments/ gate runners and diagnostics
    results/    the evidence ledger (results.json) and reports
    .artifacts/ regenerable working files (clay binaries, seed-stat caches)

Every path is absolute and derived from this file's location, so any script can
be run from any working directory.
"""

from __future__ import annotations

import os

# ROOT is the repo root, which is this file's parent directory -- paths.py
# lives in src/. Getting this wrong silently offsets every path by one level.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SPECS = os.path.join(ROOT, "specs")
SRC = os.path.join(ROOT, "src")
EXPERIMENTS = os.path.join(ROOT, "experiments")
RESULTS = os.path.join(ROOT, "results")
ARTIFACTS = os.path.join(ROOT, ".artifacts")

# -- documents ---------------------------------------------------------------
# The three live AGI documents (2026-10-19). The 15 pre-AGI specs they
# consolidate live in specs/archive/ and are referenced, never read at runtime.

AGI_CHECKLIST = os.path.join(SPECS, "AGI_CHECKLIST.md")
AGI_FINDINGS = os.path.join(SPECS, "AGI_FINDINGS.md")
AGI_HANDOFF = os.path.join(SPECS, "AGI_HANDOFF.md")
AGI_BENCHMARK = os.path.join(SPECS, "AGI_BENCHMARK.md")
SPEC_ARCHIVE = os.path.join(SPECS, "archive")

# -- evidence ----------------------------------------------------------------

LEDGER = os.path.join(RESULTS, "results.json")
T3_REPORT = os.path.join(RESULTS, "t3_wide_report.json")

# -- regenerable working files (gitignored) ----------------------------------

T1_CLAY = os.path.join(ARTIFACTS, "clay_t1.bin")
T2_CLAY = os.path.join(ARTIFACTS, "clay_t2.bin")
T3_STATS = os.path.join(ARTIFACTS, "t3_seed_stats.json")
PIPE_BUDGET = os.path.join(ARTIFACTS, "pipe_stage_budget.json")

# -- the fresh-process verifier T2 spawns ------------------------------------

RECALL_FRESH = os.path.join(SRC, "recall_fresh.py")

SPEC_FILES = (AGI_CHECKLIST, AGI_FINDINGS, AGI_HANDOFF, AGI_BENCHMARK)


def ensure_artifacts() -> None:
    """Create the artifacts directory. Call before writing any working file."""
    os.makedirs(ARTIFACTS, exist_ok=True)


def ensure_dirs() -> None:
    """Create every directory the project expects to exist."""
    for d in (SPECS, SRC, EXPERIMENTS, RESULTS, ARTIFACTS):
        os.makedirs(d, exist_ok=True)