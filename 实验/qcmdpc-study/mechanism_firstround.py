"""First-round flip MECHANISM measurement (review round-3, B2).

For each identical (H, e, s) triple, run C0_base and C4_first_p2 (FRO-2) with
record_flips=True and extract ROUND-1 flip behaviour against the true error
support e:

    total_first     = |flip_positions[0]|
    correct_first   = |flip_positions[0] ∩ supp(e)|      (flips that remove a true error bit)
    incorrect_first = total_first - correct_first        (flips that add a wrong bit)
    residual_r1     = |supp(e) Δ flip_positions[0]| = t + total_first - 2*correct_first
    iters           = trajectory.n_iters_run
    success         = trajectory.success

Aggregates per group/arm (means over samples) plus PAIRED per-sample differences
(FRO-2 − C0) and a rescue-subset view (samples where C0 fails and FRO-2 succeeds).
Only logging is added; decode semantics (thresholds, flips, success rule) are
UNCHANGED. Uses simulation-privileged e_true, so this is a MECHANISM analysis,
not a deployable decoder (label accordingly in the paper).

Keys reuse the P1' formal-pool PREFIX: the pool is built with
n_keys = fresh_from + keys_per_group and indices [fresh_from, fresh_from+keys_per_group)
are used, which are exactly the formal run's first `keys_per_group` fresh keys
(the accepted-key sequence is deterministic in the attempt counter, independent
of n_keys), so the mechanism sample ties to the main table's key lineage.

Output: results/firstround_mech/report.json
Usage : python mechanism_firstround.py [--config configs/m1_p1_firstround_mech.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import build_decoder
from qcmdpc.generators import KeyPool, make_error_generator

OUT = "results/firstround_mech"


def round1_metrics(traj, e_support: set, t: int) -> dict:
    fp0 = set(traj.flip_positions[0]) if traj.flip_positions else set()
    total = len(fp0)
    correct = len(fp0 & e_support)
    incorrect = total - correct
    residual = t + total - 2 * correct
    return {"total": total, "correct": correct, "incorrect": incorrect,
            "residual_r1": residual, "iters": traj.n_iters_run, "success": bool(traj.success)}


def _mean(xs):
    return float(np.mean(xs)) if xs else None


def run_group(gid, gspec, cfg):
    param, seed = cfg["parameter"], cfg["seed"]
    E = cfg["errors_per_key"]
    K = cfg["keys_per_group"]
    fresh_from = cfg["fresh_from"][gid]
    spec = dict(gspec)
    spec["n_keys"] = fresh_from + K  # build the formal-pool prefix; use the fresh slice
    t0 = time.time()
    pool = KeyPool(seed, param, gid, spec)
    idxs = list(range(fresh_from, fresh_from + K))
    names = list(cfg["decoders"])
    decs = {n: build_decoder(n, d, param["d"], param["t"], param["r"])
            for n, d in cfg["decoders"].items()}
    t = param["t"]

    acc = {n: {"total": [], "correct": [], "incorrect": [], "residual_r1": [], "iters": [],
               "fails": 0} for n in names}
    paired = {"d_incorrect": [], "d_residual": [], "d_total": []}
    rescue = {"n": 0, "c0_incorrect": [], "c4_incorrect": [], "c0_residual": [], "c4_residual": []}
    n_samples = 0
    for ki in idxs:
        key = pool.keys[ki]
        gen = make_error_generator(seed, gid, key.key_id, param, spec, key, pool.ncws.get(key.key_id))
        for eid in range(E):
            e = gen(eid)
            e_support = set(int(x) for x in np.nonzero(e)[0])
            s0 = key.syndrome_from_global(e)
            m = {}
            for name in names:
                traj = decs[name](key, s0.copy(), record_flips=True)
                m[name] = round1_metrics(traj, e_support, t)
                acc[name]["total"].append(m[name]["total"])
                acc[name]["correct"].append(m[name]["correct"])
                acc[name]["incorrect"].append(m[name]["incorrect"])
                acc[name]["residual_r1"].append(m[name]["residual_r1"])
                acc[name]["iters"].append(m[name]["iters"])
                if not m[name]["success"]:
                    acc[name]["fails"] += 1
            b, c = names[0], names[1]
            paired["d_incorrect"].append(m[c]["incorrect"] - m[b]["incorrect"])
            paired["d_residual"].append(m[c]["residual_r1"] - m[b]["residual_r1"])
            paired["d_total"].append(m[c]["total"] - m[b]["total"])
            if (not m[b]["success"]) and m[c]["success"]:
                rescue["n"] += 1
                rescue["c0_incorrect"].append(m[b]["incorrect"])
                rescue["c4_incorrect"].append(m[c]["incorrect"])
                rescue["c0_residual"].append(m[b]["residual_r1"])
                rescue["c4_residual"].append(m[c]["residual_r1"])
            n_samples += 1
        if (ki - idxs[0] + 1) % 5 == 0:
            print(f"  [{gid}] {ki-idxs[0]+1}/{len(idxs)} keys, {time.time()-t0:.0f}s", flush=True)

    out = {"gid": gid, "n_keys": len(idxs), "E_per_key": E, "n_samples": n_samples,
           "seconds": round(time.time() - t0, 1), "arms": {}}
    for name in names:
        a = acc[name]
        out["arms"][name] = {
            "failures": a["fails"],
            "mean_total_first": _mean(a["total"]),
            "mean_correct_first": _mean(a["correct"]),
            "mean_incorrect_first": _mean(a["incorrect"]),
            "mean_residual_r1": _mean(a["residual_r1"]),
            "mean_iters": _mean(a["iters"]),
        }
    b, c = names[0], names[1]
    out["paired_diff_mean"] = {k: _mean(v) for k, v in paired.items()}
    out["rescue_subset"] = {
        "n_rescued": rescue["n"],
        "mean_c0_incorrect": _mean(rescue["c0_incorrect"]),
        "mean_c4_incorrect": _mean(rescue["c4_incorrect"]),
        "mean_c0_residual": _mean(rescue["c0_residual"]),
        "mean_c4_residual": _mean(rescue["c4_residual"]),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m1_p1_firstround_mech.json")
    args = ap.parse_args()
    cfg = json.load(open(args.config, encoding="utf-8"))
    names = list(cfg["decoders"])
    b, c = names[0], names[1]
    os.makedirs(OUT, exist_ok=True)
    report = {"config": args.config, "param": cfg["parameter"],
              "E_per_key": cfg["errors_per_key"], "keys_per_group": cfg["keys_per_group"],
              "note": ("round-1 flip mechanism; simulation-privileged (uses e_true); "
                       "logging-only instrumentation, decode semantics unchanged"),
              "groups": {}}
    for gid, gspec in cfg["groups"].items():
        print(f"[{gid}] starting ({time.strftime('%H:%M:%S')})", flush=True)
        r = run_group(gid, gspec, cfg)
        report["groups"][gid] = r
        with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        ab, ac = r["arms"][b], r["arms"][c]
        print(f"[{gid}] C0 incor1={ab['mean_incorrect_first']:.3f} res1={ab['mean_residual_r1']:.2f} "
              f"| FRO2 incor1={ac['mean_incorrect_first']:.3f} res1={ac['mean_residual_r1']:.2f} "
              f"| d_incor={r['paired_diff_mean']['d_incorrect']:+.3f} "
              f"d_res={r['paired_diff_mean']['d_residual']:+.3f} ({r['seconds']}s)", flush=True)

    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("\n== mechanism summary (FRO-2 minus C0, per identical sample) ==")
    for gid, r in report["groups"].items():
        pd = r["paired_diff_mean"]
        print(f"[{gid}] d_total={pd['d_total']:+.3f} d_correct={_mean_diff(r,b,c,'correct')} "
              f"d_incorrect={pd['d_incorrect']:+.3f} d_residual_r1={pd['d_residual']:+.3f} "
              f"| rescued={r['rescue_subset']['n_rescued']}")
    print("saved ->", os.path.join(OUT, "report.json"))


def _mean_diff(r, b, c, field):
    vb = r["arms"][b].get(f"mean_{field}_first")
    vc = r["arms"][c].get(f"mean_{field}_first")
    if vb is None or vc is None:
        return None
    return round(vc - vb, 4)


if __name__ == "__main__":
    main()
