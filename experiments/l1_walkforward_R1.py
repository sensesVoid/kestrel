#!/usr/bin/env python
"""L1 graded runner, R1 redesign (R-suffix). Delegates to l1_walkforward.py
with --suffix R1 so the GAP-10 frozen names are honored:
  runner:   experiments/l1_walkforward_R1.py
  artifact: results/l1_walkforward_R1.json
  ledger:   kestrel_beds.L1.R1
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0], "--suffix", "R1"]
runpy.run_path(os.path.join(ROOT, "experiments", "l1_walkforward.py"),
               run_name="__main__")
