# Smoke 4: bit-exactness of the "no-decode" first-round feature recipe.
#   (a) F_delta = {i: alpha_i >= tau1+delta}  vs  the flip set bf_parallel
#       actually applies in its FIRST iteration with offsets [delta, 0];
#   (b) s1 = s0 XOR (XOR of H columns at F_delta) vs the decoder's first-round
#       syndrome, checked 3 ways (decoder bookkeeping, sequential flips,
#       independent syndrome_from_global on e XOR 1_F).
#   Plus clip-bite statistics for delta in {-1,1,2,3} at P1' and at L1 t=134.
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(r"D:/桌面/TOUGAO - c")
sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))
from qcmdpc.decoders import build_decoder, make_threshold
from qcmdpc.generators import KeyPool, make_error_generator, random_key, uniform_fixed_weight, _child_seed

SEED = 20260901
P1 = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
G0_SPEC = {"type": "random", "n_keys": 100}


def dec_with(offsets, d, t, r, max_iter=1):
    return build_decoder("X", {"algo": "bf_parallel",
                               "threshold": {"type": "offset",
                                             "base": {"type": "classic"},
                                             "offsets": offsets},
                               "max_iter": max_iter}, d, t, r)


# ---------------------------------------------------------------- PART A
# clip-bite statistics on realistic first-round syndromes (no decoding)
def part_a(name, r, d, t, n_inst, key=None):
    if key is None:
        rng = np.random.default_rng(_child_seed(SEED, f"A|{name}", 0))
        key = random_key(rng, r, d, "A")
    base = make_threshold({"type": "classic"}, d, t, 2 * r)
    lo, hi = max(1, (d + 1) // 2), d
    taus, sws, fc, nt, nf = [], [], {dl: [] for dl in (-1, 1, 2, 3)}, {dl: [] for dl in (-1, 1, 2, 3)}, {dl: [] for dl in (-1, 1, 2, 3)}
    t0 = time.perf_counter()
    for i in range(n_inst):
        rng = np.random.default_rng(_child_seed(SEED, f"A|{name}|err", i))
        e = uniform_fixed_weight(rng, 2 * r, t)
        s0 = key.syndrome_from_global(e)
        sw = int(s0.sum())
        tau1 = base(0, sw)
        alpha = key.upc_fast(s0)
        supp = e.astype(bool)
        sws.append(sw); taus.append(tau1)
        for dl in (-1, 1, 2, 3):
            F = alpha >= (tau1 + dl)
            fc[dl].append(int(F.sum()))
            nt[dl].append(int(np.count_nonzero(F & supp)))
            nf[dl].append(int(np.count_nonzero(F & ~supp)))
    dt = time.perf_counter() - t0
    print(f"[A:{name}] r={r} d={d} t={t} n={n_inst} | per-instance no-decode "
          f"features {dt / n_inst * 1000:.3f} ms (gen+syn+upc+4 flip sets)")
    print(f"   |s0| mean={np.mean(sws):.0f} [{min(sws)},{max(sws)}]  tau1 "
          f"mean={np.mean(taus):.1f} [{min(taus)},{max(taus)}]  lo={lo} hi={hi}")
    for dl in (-1, 1, 2, 3):
        bite = sum(1 for x in taus if not (lo <= x + dl <= hi))
        print(f"   delta={dl:+d}: clip-bite {bite}/{n_inst} | |F| mean={np.mean(fc[dl]):.1f} | "
              f"n_true mean={np.mean(nt[dl]):.1f} | n_false mean={np.mean(nf[dl]):.1f}")


# ---------------------------------------------------------------- PART B
def part_b():
    pool = KeyPool(SEED, P1, "G0", G0_SPEC)
    d, t, r = P1["d"], P1["t"], P1["r"]
    base = make_threshold({"type": "classic"}, d, t, 2 * r)
    ok_F = ok_s1_arr = ok_s1_w = 0
    tot = 0
    mismatch = []
    for ki in (8, 9, 20):
        key = pool.keys[ki]
        gen = make_error_generator(SEED, "G0", key.key_id, P1, G0_SPEC, key, None)
        for eid in range(5):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            sw0 = int(s0.sum())
            tau1 = base(0, sw0)
            alpha = key.upc_fast(s0)
            for delta in (-1, 0, 1, 2, 3):
                tot += 1
                F_model = np.flatnonzero(alpha >= tau1 + delta)
                dec = dec_with([delta, 0], d, t, r, max_iter=1)
                res = dec(key, s0.copy(), record_flips=True)
                if res.flip_positions:
                    F_dec = np.array(res.flip_positions[0], dtype=np.int64)
                else:
                    F_dec = np.array([], dtype=np.int64)
                mF = np.array_equal(F_model, F_dec)
                ok_F += mF
                # s1: sequential flips (decoder path)
                s1 = s0.copy()
                for p in F_model:
                    s1 = key.flip(s1, int(p))
                w1 = int(s1.sum())
                # independent path: H(e XOR 1_F) via the syndrome() routine
                f = np.zeros(key.n, dtype=np.uint8)
                f[F_model] = 1
                s1_ind = key.syndrome_from_global(e ^ f)
                mI = np.array_equal(s1, s1_ind)
                ok_s1_arr += mI
                mW = (w1 == res.syndrome_weights[0])
                ok_s1_w += mW
                if not (mF and mI and mW):
                    mismatch.append((ki, eid, delta, mF, mI, mW,
                                     int(F_model.size), int(F_dec.size),
                                     w1, res.syndrome_weights[0]))
    print(f"[B] first-round flip-set exactness: {ok_F}/{tot} match")
    print(f"[B] s1 array vs independent H(e XOR F): {ok_s1_arr}/{tot} match")
    print(f"[B] s1 weight vs decoder syndrome_weights[0]: {ok_s1_w}/{tot} match")
    print(f"[B] mismatches: {mismatch if mismatch else 'none'}")


if __name__ == "__main__":
    part_b()
    part_a("P1p", 4801, 45, 92, 500)
    part_a("L1_t134", 12323, 71, 134, 100)
    part_a("L1_t155", 12323, 71, 155, 100)
