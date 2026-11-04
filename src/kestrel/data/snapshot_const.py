"""Frozen snapshot identity (M1.2/M1.5): the ONE number every runner asserts.

Recorded when the manifest was committed (commit a7b3b9e, 2026-11-05).
If the raw snapshot ever changes (new month, repair packet), the manifest is
regenerated and THIS constant is updated in the same commit — a runner that
loads with a stale constant refuses, never adapts silently (HL-2/HL-9).
"""

DATA_ROOT = "bench_data/binance_klines"
MANIFEST_REL = DATA_ROOT + "/snapshot.sha256"

# sha256 over the manifest file bytes (the manifest's own content pin)
MANIFEST_SHA = ("01b1c8cc88b6bac04c602b5a6ecc3a9606baeac5404ba46428bc"
                "7a2aa3544c56")
