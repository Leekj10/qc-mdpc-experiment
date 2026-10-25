# Smoke 1: classic-threshold construction at BIKE-L1 scale (no decoding).
# Check 1 of the plumbing task.
import sys, time
from pathlib import Path

ROOT = Path(r"D:/桌面/TOUGAO - c")
sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))

from qcmdpc.decoders import make_threshold, _classic_threshold_factory

CASES = [
    ("P1prime", 45, 92, 9602),
    ("P4",      39, 76, 7214),
    ("L1",      71, 134, 24646),
    ("L1-t150", 71, 150, 24646),
    ("L1-t155", 71, 155, 24646),
    ("L1-t160", 71, 160, 24646),
]
SWS = [1, 2, 5, 10, 20, 40, 60, 80, 100, 120, 142, 160, 200, 250, 300, 400, 600, 900, 1200, 2000, 5000]

for name, d, t, n in CASES:
    t0 = time.perf_counter()
    th = make_threshold({"type": "classic"}, d=d, t=t, n=n)
    dt = (time.perf_counter() - t0) * 1000
    lo, hi = max(1, (d + 1) // 2), d
    vals = [th(0, sw) for sw in SWS]
    oor = [(sw, v) for sw, v in zip(SWS, vals) if not (lo <= v <= hi)]
    mono = all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))
    print(f"{name}: d={d} t={t} n={n} | build {dt:.2f} ms | lo={lo} hi={hi}")
    print(f"   th(0,sw) for sw={SWS}:")
    print(f"   {vals}")
    print(f"   out_of_range={oor}  non-increasing_in_S={mono}")
    # also sweep iteration index (static threshold must be constant in it)
    v_it = [th(it, 200) for it in (0, 1, 5, 19, 20, 100)]
    print(f"   th(it,200) it=0,1,5,19,20,100 -> {v_it}")
    # extreme small S (near convergence)
    v_small = [th(0, sw) for sw in (0, 1, 2, 3, 5)]
    print(f"   small-S {v_small}")
