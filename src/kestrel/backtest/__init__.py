"""Backtester + cost model + exact accounting reel (M3) — bars A-3, A-4."""
from .costs import Costs, SLIP_FLOOR_BPS, TAKER_FEE_PCT, STRESS_X  # noqa: F401
from .governor import Governor  # noqa: F401
from .engine import BacktestEngine, EngineError, Reel  # noqa: F401
