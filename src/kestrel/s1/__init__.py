"""S1 core package (M4)."""
from .train import train_s1, train_test_split_indices
from .core import (
    S1Core, N_BITS, N_LIT, CLAY_BYTES, E_MIN, E_LIT, SEP_MIN, C_CAP, ARITY,
    sat_lits, save_checkpoint, load_checkpoint, clay_byte_neutral,
    VENDOR_N_BITS, VENDOR_E_MIN,
)
from .labels import realized_labels, label_counts, ZERO_BAND_BPS
from .calibration import calibrate_theta_z, threshold_table

__all__ = [
    "S1Core", "N_BITS", "N_LIT", "CLAY_BYTES", "E_MIN", "E_LIT", "SEP_MIN",
    "C_CAP", "ARITY", "sat_lits", "save_checkpoint", "load_checkpoint",
    "clay_byte_neutral", "realized_labels", "label_counts", "ZERO_BAND_BPS",
    "calibrate_theta_z", "threshold_table", "train_s1", "train_test_split_indices",
]
