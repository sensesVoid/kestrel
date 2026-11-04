"""Walk-forward window boundaries (M5.1, M5.3): 34 monthly windows,
30d test / 180d train, 7-day embargo, frozen as integer bar indices.

Held-out seal (2026-05-01..2026-10-31) is NEVER touched by L1.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import numpy as np

TRAIN_DAYS = 180
EMBARGO_DAYS = 7
TEST_DAYS = 30
N_WINDOWS = 34
# graded span: 2023-07-01 .. 2026-04-30
FIRST_TEST_MONTH = (2023, 7)
SEAL_START = datetime(2026, 5, 1, tzinfo=timezone.utc)


@dataclass
class Window:
    idx: int
    test_start_ms: int
    test_end_ms: int          # exclusive
    train_start_idx: int
    train_end_idx: int        # exclusive
    test_start_idx: int
    test_end_idx: int         # exclusive
    embargo_bars: int


def _month_starts(first_year, first_month, n):
    out = []
    y, m = first_year, first_month
    for _ in range(n):
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def build_windows(open_time_ms: np.ndarray) -> list:
    """Return 34 Window objects with integer bar indices. Raises if any
    boundary cannot be resolved (no silent partial windows)."""
    ot = np.asarray(open_time_ms, dtype=np.int64)
    ms_per_day = 86_400_000
    train_span = TRAIN_DAYS * ms_per_day
    embargo_span = EMBARGO_DAYS * ms_per_day
    test_span = TEST_DAYS * ms_per_day

    windows = []
    for i, (y, m) in enumerate(_month_starts(*FIRST_TEST_MONTH, N_WINDOWS)):
        ts = datetime(y, m, 1, tzinfo=timezone.utc)
        test_start_ms = int(ts.timestamp() * 1000)
        test_end_ms = test_start_ms + test_span
        # train window ends embargo before test_start
        train_end_ms = test_start_ms - embargo_span
        train_start_ms = train_end_ms - train_span
        # resolve indices via searchsorted (left)
        train_start_idx = int(np.searchsorted(ot, train_start_ms, side="left"))
        train_end_idx = int(np.searchsorted(ot, train_end_ms, side="left"))
        test_start_idx = int(np.searchsorted(ot, test_start_ms, side="left"))
        test_end_idx = int(np.searchsorted(ot, test_end_ms, side="left"))
        if (train_end_idx - train_start_idx < 100
                or test_end_idx - test_start_idx < 10):
            raise ValueError(f"window {i}: insufficient bars "
                             f"(train {train_end_idx-train_start_idx}, "
                             f"test {test_end_idx-test_start_idx})")
        # embargo bar count = bars between train_end and test_start
        embargo_bars = test_start_idx - train_end_idx
        windows.append(Window(
            idx=i, test_start_ms=test_start_ms, test_end_ms=test_end_ms,
            train_start_idx=train_start_idx, train_end_idx=train_end_idx,
            test_start_idx=test_start_idx, test_end_idx=test_end_idx,
            embargo_bars=embargo_bars))
    # seal check: last test window must end before seal
    last = windows[-1]
    assert last.test_end_ms <= int(SEAL_START.timestamp() * 1000), \
        "last window crosses into held-out seal"
    return windows
