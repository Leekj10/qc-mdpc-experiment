# Smoke 2: decode speed (single process/core) for bf_parallel at
# P1' (4801,45,92), P1' t=90, and BIKE-L1 (12323,71,134/155).
# Also the P1' budget ladder {4,6,8,12,20} for the budget-axis projection.
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(r"D:/桌面/TOUGAO - c")
sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))
from qcmdpc.decoders import build_decoder
from qcmdpc.generators import random_key, uniform_fixed_weight, _child_seed

SEED = 20260901


def build_arm(r, d, t, offsets, max_iter):
    return build_decoder("X", {"algo": "bf_parallel",
                               "threshold": {"type": "offset",
                                             "base": {"type": "classic"},
                                             "offsets": offsets},
                               "max_iter": max_iter}, d, t, r)


def bench_point(name, r, d, t, n_inst, budgets=(20,)):
    rng0 = np.random.default_rng(_child_seed(SEED, f"bench|{name}|key", 0))
    key = random_key(rng0, r, d, "bench")
    t0 = time.perf_counter()
    syns, sw0 = [], []
    for i in range(n_inst):
        rng = np.random.default_rng(_child_seed(SEED, f"bench|{name}|err", i))
        e = uniform_fixed_weight(rng, 2 * r, t)
        s = key.syndrome_from_global(e)
        syns.append(s)
        sw0.append(int(s.sum()))
    t_gen = time.perf_counter() - t0
    sw0 = np.array(sw0)
    print(f"[{name}] r={r} d={d} t={t} n={n_inst} | gen+syndrome "
          f"{t_gen / n_inst * 1000:.3f} ms/inst | |s0| mean={sw0.mean():.0f} "
          f"min={sw0.min()} max={sw0.max()}", flush=True)
    for budget in budgets:
        for arm, offs in (("C0", [0]), ("FRO-2", [2, 0])):
            dec = build_arm(r, d, t, offs, budget)
            t0 = time.perf_counter()
            fails = 0
            tot_it = 0
            for i in range(n_inst):
                res = dec(key, syns[i].copy())
                fails += (not res.success)
                tot_it += res.n_iters_run
            dt = time.perf_counter() - t0
            print(f"   budget={budget:2d} {arm:5s}: {dt / n_inst * 1000:8.3f} ms/dec "
                  f"{n_inst / dt:8.1f} dec/s  mean_iters={tot_it / n_inst:.3f}  "
                  f"fails={fails}/{n_inst}", flush=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "p1p"):
        bench_point("P1p_t92", 4801, 45, 92, 200, budgets=(4, 6, 8, 12, 20))
        bench_point("P1p_t90", 4801, 45, 90, 200, budgets=(20,))
    if which in ("all", "l1"):
        bench_point("L1_t134", 12323, 71, 134, 100, budgets=(20,))
        bench_point("L1_t155", 12323, 71, 155, 100, budgets=(20,))
