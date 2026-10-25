#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Two things the paper currently lacks: a lower-DFR measurement, and a
predictive (rather than descriptive) use of the first-round model.

Motivation
----------
The paper measures the first-round effect at DFR around 1e-3 and reports a local
UPC-tail model that predicts the *direction* of the effect.  Two gaps follow:

  (a) the effect has never been measured more than half an order of magnitude
      below that, so it is unknown whether first-round conservatism still helps
      as the decoder improves -- the trend across t=92/94/96 (RR 7.00 -> 2.82 ->
      1.87) says the effect grows as DFR falls, but t<=90 had zero C0 failures in
      the samples available;
  (b) the model predicts a sign but never a magnitude, so nothing is actually
      predicted out of sample.

Both are addressable with the same machinery.  The model inputs A_0, A_1 are
computed from FIRST-ROUND UPC STATISTICS ONLY -- no decoder is run to obtain
them -- so the fitting side is nearly free; only the validation side needs
samples.

Phases
------
  A  t=90 at P1', a large sample, C0 vs FRO-2            (~2.5 h)  lower-DFR test
  B  first-round UPC tail statistics at t in 88..96      (~10 min) model inputs
  C  the missing offsets +1 and +3 at t=92               (~1 h)   more fit points
  D  fit the model on all (t, delta) pairs and validate   (free)

Every phase checkpoints, so the script can be interrupted and resumed.

Run:  python lw-vs/scripts/exp_lowdfr_model.py [--phase A,B,C,D]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
OUT = ROOT / "lw-vs" / "results" / "lowdfr_model"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder, make_threshold      # noqa: E402
from qcmdpc.generators import (KeyPool, make_error_generator,  # noqa: E402
                               random_key, uniform_fixed_weight, _child_seed)
from qcmdpc.stats import cluster_bootstrap_paired, wilson_upper  # noqa: E402

SEED = 20260901
R, D = 4801, 45
MAX_ITER = 20
N_WORKERS = int(os.environ.get("LM_WORKERS", "11"))

# ---------------------------------------------------------------- phase A
# 150 keys x 34,000 errors = 5.1e6 paired instances per arm.  At t=90 the t-sweep
# saw 1/30,000 C0 failures, so this sample should yield ~170 C0 failures -- enough
# for a key-clustered interval at the observed effect size.
A_T, A_KEYS, A_ERR = 90, 150, 34_000

# ---------------------------------------------------------------- phase C
C_T, C_KEYS, C_ERR = 92, 120, 4_200     # ~5e5 instances per arm per offset
C_OFFSETS = {"FROp1": [1, 0], "FROp3": [3, 0]}

# ---------------------------------------------------------------- phase B
B_TS = (88, 90, 92, 94, 96)
B_KEYS, B_ERR = 12, 300
B_DELTAS = (0, 1, 2, 3, -1)


def _pool_for(gid, n_keys):
    spec = {"type": "random", "n_keys": n_keys}
    return KeyPool(SEED, {"id": "P1prime", "r": R, "d": D, "t": A_T, "n0": 2}, gid, spec)


# --------------------------------------------------------------------------
def _work_pair(job):
    """One key: C0 vs one offset arm on the same (H,e,s), at a given t."""
    tag, t, ki, n_err, offsets, n_keys = job
    pool = _pool_for(f"lm{tag}", n_keys)
    key = pool.keys[ki]
    gspec = {"type": "random", "n_keys": n_keys}
    param = {"id": "P1prime", "r": R, "d": D, "t": t, "n0": 2}
    gen = make_error_generator(SEED, f"lm{tag}", key.key_id, param, gspec, key, None)
    dec0 = build_decoder("C0", {"algo": "bf_parallel",
                                "threshold": {"type": "classic"},
                                "max_iter": MAX_ITER}, D, t, R)
    dec1 = build_decoder("X", {"algo": "bf_parallel",
                               "threshold": {"type": "offset",
                                             "base": {"type": "classic"},
                                             "offsets": offsets},
                               "max_iter": MAX_ITER}, D, t, R)
    f0 = f1 = 0
    for eid in range(n_err):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        if not dec0(key, s.copy()).success:
            f0 += 1
        if not dec1(key, s.copy()).success:
            f1 += 1
    return ki, f0, f1, n_err


def _work_upc(job):
    """First-round UPC tail counts. No decoder is run; this is the cheap side."""
    t, ki = job
    pool = _pool_for("lmupc", B_KEYS)
    key = pool.keys[ki]
    gspec = {"type": "random", "n_keys": B_KEYS}
    param = {"id": "P1prime", "r": R, "d": D, "t": t, "n0": 2}
    gen = make_error_generator(SEED, "lmupc", key.key_id, param, gspec, key, None)
    thr = make_threshold({"type": "classic"}, D, t, 2 * R)
    q1 = {d: 0 for d in B_DELTAS}
    q0 = {d: 0 for d in B_DELTAS}
    n1 = n0 = 0
    for eid in range(B_ERR):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        u = key.upc_fast(s)
        tau1 = thr(0, int(s.sum()))
        sup = e.astype(bool)
        n1 += int(sup.sum()); n0 += int(sup.size - sup.sum())
        for d in B_DELTAS:
            q1[d] += int(np.count_nonzero(u[sup] >= tau1 + d))
            q0[d] += int(np.count_nonzero(u[~sup] >= tau1 + d))
    return t, ki, n1, n0, q1, q0


def _run(fn, jobs):
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        return list(ex.map(fn, jobs))


def _summarise(res, n_keys, e_per_key, offname):
    per0 = np.zeros(n_keys, dtype=np.int64)
    per1 = np.zeros(n_keys, dtype=np.int64)
    for ki, f0, f1, _ in res:
        per0[ki] = f0; per1[ki] = f1
    n = n_keys * e_per_key
    boot = cluster_bootstrap_paired(per0, per1, e_per_key, B=10000, seed=20260905)
    return {
        "arm": offname, "n_keys": n_keys, "errors_per_key": e_per_key, "trials": n,
        "c0_failures": int(per0.sum()), "c0_dfr": float(per0.sum() / n),
        "arm_failures": int(per1.sum()), "arm_dfr": float(per1.sum() / n),
        "c0_upper95": wilson_upper(int(per0.sum()), n),
        "rr": boot["point"]["risk_ratio"],
        "rr_ci95": boot["ci"]["risk_ratio"],
        "rr_excludes_1": boot["rr_excludes_1"],
        "per_key_c0": per0.tolist(), "per_key_arm": per1.tolist(),
    }


# --------------------------------------------------------------------------
def phase_A() -> None:
    p = OUT / "phaseA_t90.json"
    if p.exists():
        print("[A] cached"); return
    print(f"[A] t={A_T} at P1', {A_KEYS} keys x {A_ERR} errors  "
          f"({A_KEYS*A_ERR*2/1e6:.1f}M decodes)")
    t0 = time.time()
    res = _run(_work_pair, [("A", A_T, ki, A_ERR, [2, 0], A_KEYS) for ki in range(A_KEYS)])
    cell = _summarise(res, A_KEYS, A_ERR, "FRO-2")
    cell.update({"t": A_T, "wall_seconds": round(time.time() - t0, 1),
                 "note": "lower-DFR test: an order of magnitude below the main result"})
    json.dump(cell, p.open("w", encoding="utf-8"), indent=1)
    print(f"    C0 {cell['c0_failures']}/{cell['trials']} DFR={cell['c0_dfr']:.3e}  "
          f"FRO-2 {cell['arm_failures']}  RR={cell['rr']:.3f} "
          f"[{cell['rr_ci95'][0]:.3f}, {cell['rr_ci95'][1]:.3f}] "
          f"excl1={cell['rr_excludes_1']}  ({cell['wall_seconds']}s)")


def phase_C() -> None:
    for name, offs in C_OFFSETS.items():
        p = OUT / f"phaseC_t{C_T}_{name}.json"
        if p.exists():
            print(f"[C] {name} cached"); continue
        print(f"[C] t={C_T}, offsets={offs}, {C_KEYS} keys x {C_ERR} errors")
        t0 = time.time()
        res = _run(_work_pair, [("C", C_T, ki, C_ERR, offs, C_KEYS) for ki in range(C_KEYS)])
        cell = _summarise(res, C_KEYS, C_ERR, name)
        cell.update({"t": C_T, "offsets": offs, "wall_seconds": round(time.time() - t0, 1)})
        json.dump(cell, p.open("w", encoding="utf-8"), indent=1)
        print(f"    C0 {cell['c0_failures']} FRO {cell['arm_failures']}  "
              f"RR={cell['rr']:.3f} [{cell['rr_ci95'][0]:.3f}, {cell['rr_ci95'][1]:.3f}] "
              f"excl1={cell['rr_excludes_1']}  ({cell['wall_seconds']}s)")


def phase_B() -> None:
    p = OUT / "phaseB_upc_tails.json"
    if p.exists():
        print("[B] cached"); return
    print(f"[B] first-round UPC tails at t in {B_TS}, {B_KEYS} keys x {B_ERR} errors "
          f"(no decoding)")
    out = {}
    for t in B_TS:
        res = _run(_work_upc, [(t, ki) for ki in range(B_KEYS)])
        n1 = sum(x[2] for x in res); n0 = sum(x[3] for x in res)
        q1 = {d: sum(x[4][d] for x in res) for d in B_DELTAS}
        q0 = {d: sum(x[5][d] for x in res) for d in B_DELTAS}
        n = 2 * R
        p1 = {d: q1[d] / n1 for d in B_DELTAS}
        p0 = {d: q0[d] / n0 for d in B_DELTAS}
        model = {}
        for d in B_DELTAS:
            if d == 0:
                continue
            A1 = p1[d] / p1[0] if p1[0] else float("nan")
            A0 = p0[d] / p0[0] if p0[0] else float("nan")
            inc_av = (n - t) * (p0[0] - p0[d])
            cor_df = t * (p1[0] - p1[d])
            model[str(d)] = {"A1": A1, "A0": A0, "incorrect_avoided": inc_av,
                             "correct_deferred": cor_df,
                             "rho": inc_av / cor_df if cor_df > 0 else float("inf")}
        out[str(t)] = {"t": t, "q1": {str(k): v for k, v in q1.items()},
                       "q0": {str(k): v for k, v in q0.items()},
                       "p1": {str(k): v for k, v in p1.items()},
                       "p0": {str(k): v for k, v in p0.items()},
                       "model": model}
        m2 = model.get("2", {})
        print(f"    t={t}: A1(2)={m2.get('A1', float('nan')):.4f} "
              f"A0(2)={m2.get('A0', float('nan')):.5f} rho(2)={m2.get('rho', float('nan')):.3f}")
    json.dump(out, p.open("w", encoding="utf-8"), indent=1)


def phase_D() -> None:
    """Assemble every (model input, measured effect) pair and test whether the
    model's quantities predict the measured risk ratio out of sample."""
    print("[D] assembling (prediction, measurement) pairs")
    upc = json.load(open(OUT / "phaseB_upc_tails.json", encoding="utf-8"))
    pairs = []

    def add(t, delta, rr, src, lo=None, hi=None):
        m = upc.get(str(t), {}).get("model", {}).get(str(delta))
        if m is None or rr is None:
            return
        pairs.append({"t": t, "delta": delta, "rho": m["rho"], "A1": m["A1"],
                      "A0": m["A0"], "inc_avoided": m["incorrect_avoided"],
                      "cor_deferred": m["correct_deferred"],
                      "rr_measured": rr, "rr_lo": lo, "rr_hi": hi, "source": src})

    # already-archived measurements
    arch = ROOT / "lw-vs" / "results" / "round_controls"
    p1 = arch / "phase1_round_controls.json"
    if p1.exists():
        d = json.load(open(p1, encoding="utf-8"))
        by = {a: c["arms"][a] for c in d["groups"].values() for a in c["arms"]}
        for arm, delta in (("FRO-2", 2), ("FRONEG", -1)):
            a = by.get(arm, {})
            add(92, delta, a.get("rr_vs_C0"), "round_controls/P1'",
                (a.get("rr_ci95") or [None, None])[0], (a.get("rr_ci95") or [None, None])[1])
    ts = ROOT / "lw-vs" / "data" / "t1_t_sensitivity.csv"
    if ts.exists():
        import csv
        for row in csv.DictReader(open(ts, encoding="utf-8-sig")):
            if row["rr"]:
                add(int(row["t"]), 2, float(row["rr"]), "phase2 t-sweep",
                    float(row["rr_lo"]), float(row["rr_hi"]))
    # this run's own results
    pa = OUT / "phaseA_t90.json"
    if pa.exists():
        c = json.load(open(pa, encoding="utf-8"))
        add(c["t"], 2, c["rr"], "phaseA t=90",
            c["rr_ci95"][0], c["rr_ci95"][1])
    for name, offs in C_OFFSETS.items():
        pc = OUT / f"phaseC_t{C_T}_{name}.json"
        if pc.exists():
            c = json.load(open(pc, encoding="utf-8"))
            add(c["t"], offs[0], c["rr"], f"phaseC {name}",
                c["rr_ci95"][0], c["rr_ci95"][1])

    if not pairs:
        print("    no pairs assembled yet"); return
    print(f"    {len(pairs)} pairs:")
    for q in sorted(pairs, key=lambda x: (x["t"], x["delta"])):
        print(f"      t={q['t']} d={q['delta']:>2}  rho={q['rho']:.3f}  "
              f"inc_av={q['inc_avoided']:.2f}  RR={q['rr_measured']:.3f}  [{q['source']}]")

    # Does rho order the measured effect?  Spearman on (rho, log RR).
    rh = np.array([q["rho"] for q in pairs])
    lg = np.log(np.array([q["rr_measured"] for q in pairs]))
    if len(pairs) >= 4:
        from scipy.stats import spearmanr, pearsonr
        rho_sp, p_sp = spearmanr(rh, lg)
        r_pe, p_pe = pearsonr(np.log(rh), lg)
        print(f"\n    Spearman(rho, log RR) = {rho_sp:.3f}  p={p_sp:.4f}")
        print(f"    Pearson(log rho, log RR) = {r_pe:.3f}  p={p_pe:.4f}")
    else:
        rho_sp = p_sp = r_pe = p_pe = None

    summary = {"n_pairs": len(pairs), "pairs": pairs,
               "spearman_rho_logRR": rho_sp, "spearman_p": p_sp,
               "pearson_logrho_logRR": r_pe, "pearson_p": p_pe}
    json.dump(summary, (OUT / "phaseD_model_fit.json").open("w", encoding="utf-8"), indent=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="A,B,C,D")
    a = ap.parse_args()
    ph = [x.strip().upper() for x in a.phase.split(",") if x.strip()]
    t0 = time.time()
    if "A" in ph: phase_A()
    if "B" in ph: phase_B()
    if "C" in ph: phase_C()
    if "D" in ph: phase_D()
    print(f"\n[done] {OUT}  ({time.time()-t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
