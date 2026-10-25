# Smoke 3 (memory-capped version): key construction cost + gather-matrix memory
# + syndrome cost.  NOTE: the machine is currently ~99% memory-used (a live T90
# run holds ~3.8 GB), so pools are kept small and per-key costs extrapolated.
import sys, time, gc
from pathlib import Path
import numpy as np
import psutil

ROOT = Path(r"D:/桌面/TOUGAO - c")
sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))
from qcmdpc.generators import KeyPool, random_key, uniform_fixed_weight, _child_seed

proc = psutil.Process()
print(f"baseline RSS {proc.memory_info().rss / 1e6:.1f} MB; "
      f"system available {psutil.virtual_memory().available / 1e9:.2f} GB")

for name, r, d in (("P1p", 4801, 45), ("L1", 12323, 71)):
    rng = np.random.default_rng(_child_seed(20260901, f"smoke3|{name}", 0))
    t0 = time.perf_counter()
    k = random_key(rng, r, d, "x")
    dt = (time.perf_counter() - t0) * 1000
    nb = k._I0.nbytes + k._I1.nbytes
    print(f"[single key {name}] r={r} d={d}: QCKey build {dt:.2f} ms | "
          f"_I0+_I1 {nb / 1e6:.2f} MB | dtype={k._I0.dtype} shape={k._I0.shape}")
    del k
    gc.collect()

for name, r, d, t, nk in (("P1p", 4801, 45, 92, 20), ("L1", 12323, 71, 134, 2)):
    p = {"id": name, "r": r, "d": d, "t": t, "n0": 2}
    r0 = proc.memory_info().rss
    t0 = time.perf_counter()
    pool = KeyPool(20260901, p, "SM", {"type": "random", "n_keys": nk})
    dt = time.perf_counter() - t0
    r1 = proc.memory_info().rss
    print(f"[KeyPool {name}] n_keys={nk}: build {dt:.2f} s ({dt / nk * 1000:.0f} ms/key) "
          f"| RSS delta {r1 - r0:.0f} MB ({(r1 - r0) / nk:.2f} MB/key)")
    del pool
    gc.collect()

for name, r, d, t in (("P1p_t92", 4801, 45, 92), ("P1p_t90", 4801, 45, 90),
                      ("L1_t134", 12323, 71, 134), ("L1_t155", 12323, 71, 155)):
    rng = np.random.default_rng(_child_seed(20260901, f"smoke3s|{name}", 0))
    key = random_key(rng, r, d, "x")
    n = 100
    errs = [uniform_fixed_weight(np.random.default_rng(_child_seed(20260901, f"smoke3e|{name}", i)),
                                 2 * r, t) for i in range(n)]
    t0 = time.perf_counter()
    ws = []
    for e in errs:
        ws.append(int(key.syndrome_from_global(e).sum()))
    dt = (time.perf_counter() - t0) / n * 1000
    t0 = time.perf_counter()
    for i in range(n):
        uniform_fixed_weight(np.random.default_rng(_child_seed(20260901, f"smoke3g|{name}", i)),
                             2 * r, t)
    dg = (time.perf_counter() - t0) / n * 1000
    print(f"[syndrome {name}] r={r} t={t}: syndrome {dt:.3f} ms | err-gen {dg:.3f} ms "
          f"| |s| mean={np.mean(ws):.0f}")
    del key, errs
    gc.collect()

print("\nAnalytic per-worker memory for KeyPool (gather matrices, exact):")
for name, r, d, nk in (("P1p 100 keys", 4801, 45, 100), ("L1 100 keys", 12323, 71, 100),
                       ("L1 64 keys", 12323, 71, 64), ("L1 20 keys", 12323, 71, 20),
                       ("L1 1 key", 12323, 71, 1)):
    mb = nk * d * r * 8 * 2 / 1e6
    print(f"   {name}: {mb:.0f} MB  (11 workers: {mb * 11 / 1e3:.2f} GB)")
print(f"available RAM now: {psutil.virtual_memory().available / 1e9:.2f} GB / "
      f"{psutil.virtual_memory().total / 1e9:.1f} GB total")
