# scratch benchmark for stats-design review (decode rate at P1' t=90)
import sys, time, os
sys.path.insert(0, r"D:/桌面/TOUGAO - c/实验/qcmdpc-study")
from concurrent.futures import ProcessPoolExecutor

SEED = 20260901
P = {"id": "P1prime", "r": 4801, "d": 45, "t": 90, "n0": 2}


def work(ki, n_err=60):
    from qcmdpc.decoders import build_decoder
    from qcmdpc.generators import KeyPool, make_error_generator
    pool = KeyPool(SEED, P, "G0", {"type": "random", "n_keys": 100})
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "G0", key.key_id, P,
                               {"type": "random", "n_keys": 100}, key, None)
    dec = build_decoder("C0", {"algo": "bf_parallel",
                               "threshold": {"type": "classic"},
                               "max_iter": 20}, 45, 90, 4801)
    for eid in range(n_err):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        dec(key, s.copy())
    return n_err


if __name__ == "__main__":
    N = 10
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=N) as ex:
        tot = sum(ex.map(work, range(N)))
    dt = time.perf_counter() - t0
    rate = tot / dt
    print(f"{tot} decodes on {N} workers in {dt:.2f}s -> {rate:.0f} dec/s aggregate")
    for tm in (1.2, 2.4, 3.6, 7.2):
        print(f"  {tm:.1f}M decodes -> {tm*1e6/rate/3600:.2f} h")
    print("cpu_count:", os.cpu_count())
