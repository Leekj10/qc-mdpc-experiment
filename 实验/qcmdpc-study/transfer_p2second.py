"""Second-point TRANSFER run: frozen FRO-2 (+2) at a new scaled operating point.

Protocol (review round-3, B1; mirrors formal_m5.py's paired design):
- config configs/p2second_transfer.json supplies the NEW (r,d,t), groups, decoders;
- arms C0_base (offset [0]) vs C4_first_p2 (offset [2,0], FROZEN from P1', NOT re-tuned);
- identical (H, e, s) triples per key/error (paired); per-sample outcomes logged
  -> exact McNemar; per-key counts logged -> sign test + cluster bootstrap;
- all keys are fresh test keys at this new point (fresh_from=0);
- group-level checkpointing: each group written immediately; resume with --groups.

This is a TRANSFER / generalization check, NOT a re-tuned gate. The script reports
the pre-specified criteria honestly:
  (a) direction: FRO-2 DFR < C0 DFR in every group;
  (b) RAND per-key sign test p < 0.05;
  (c) RAND or worst-group cluster-bootstrap RR 95% CI excludes 1.
If a criterion fails, the result is reported as bounded generalization (no spin).

Estimated runtime (Python, r=3001): ~30 keys x 3000 err x 2 arms x 3 groups
= 540k decodes @ ~8-12 ms => ~1.5-2 h (background). Use the C path to speed up.
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
from qcmdpc.stats import (cluster_bootstrap_paired, holm_adjust, mcnemar_exact,
                          sign_test_paired, wilson_upper)

OUT = "results/p2second_transfer"
BOOT_SEED = 20260905


def run_group(gid, gspec, cfg):
    param = cfg["parameter"]
    seed = cfg["seed"]
    E = cfg["errors_per_key"]
    spec = dict(gspec)
    spec["n_keys"] = cfg["keys_per_group"]
    t0 = time.time()
    pool = KeyPool(seed, param, gid, spec)
    idxs = list(range(len(pool.keys)))  # fresh_from=0: new point, all keys fresh
    decs = {n: build_decoder(n, d, param["d"], param["t"], param["r"])
            for n, d in cfg["decoders"].items()}
    names = list(cfg["decoders"])
    per_key = {n: [] for n in names}
    fail_idx = {n: [] for n in names}
    n_samples = 0
    for ki in idxs:
        key = pool.keys[ki]
        gen = make_error_generator(seed, gid, key.key_id, param, spec, key, pool.ncws.get(key.key_id))
        counts = {n: 0 for n in names}
        for eid in range(E):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            for name in names:
                if not decs[name](key, s0.copy()).success:
                    counts[name] += 1
                    fail_idx[name].append((ki, eid))
            n_samples += 1
        for name in names:
            per_key[name].append(counts[name])
        if (ki + 1) % 5 == 0:
            print(f"  [{gid}] {ki+1}/{len(idxs)} keys, {time.time()-t0:.0f}s", flush=True)

    b, c = names[0], names[1]
    s0f, s4f = set(fail_idx[b]), set(fail_idx[c])
    res = {"gid": gid, "n_keys": len(idxs), "E_per_key": E, "n_samples": n_samples,
           "paired": {"c0_only": len(s0f - s4f), "c4_only": len(s4f - s0f),
                      "both": len(s0f & s4f),
                      "mcnemar_exact_p": mcnemar_exact(len(s0f - s4f), len(s4f - s0f))},
           "seconds": round(time.time() - t0, 1)}
    for name in names:
        f = len(fail_idx[name])
        u = wilson_upper(f, n_samples)
        res[name] = {"failures": f, "trials": n_samples, "dfr": f / n_samples,
                     "upper95": u, "log10_upper95": float(np.log10(u)),
                     "per_key_failures": per_key[name]}
    # cluster-robust + sign test on this group's keys
    res["sign_test"] = sign_test_paired(per_key[b], per_key[c])
    res["cluster_bootstrap"] = cluster_bootstrap_paired(per_key[b], per_key[c], E,
                                                        B=10000, seed=BOOT_SEED)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/p2second_transfer.json")
    ap.add_argument("--groups", default=None, help="comma list, for resume")
    args = ap.parse_args()
    cfg = json.load(open(args.config, encoding="utf-8"))
    names = list(cfg["decoders"])
    b, c = names[0], names[1]
    os.makedirs(OUT, exist_ok=True)
    report_path = os.path.join(OUT, "report.json")
    report = json.load(open(report_path, encoding="utf-8")) if os.path.exists(report_path) else {
        "config": args.config, "param": cfg["parameter"], "E_per_key": cfg["errors_per_key"],
        "keys_per_group": cfg["keys_per_group"], "groups": {}}

    want = [x.strip() for x in (args.groups or ",".join(cfg["groups"])).split(",") if x.strip()]
    for gid in want:
        gfile = os.path.join(OUT, f"group_{gid}.json")
        if os.path.exists(gfile):
            print(f"[{gid}] already done, skipping", flush=True)
            report["groups"][gid] = json.load(open(gfile, encoding="utf-8"))
            continue
        print(f"[{gid}] starting ({time.strftime('%H:%M:%S')})", flush=True)
        r = run_group(gid, cfg["groups"][gid], cfg)
        with open(gfile, "w", encoding="utf-8") as f:
            json.dump(r, f)
        report["groups"][gid] = r
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print(f"[{gid}] C0={r[b]['failures']}/{r[b]['trials']} C4={r[c]['failures']}/{r[c]['trials']} "
              f"McNemar p={r['paired']['mcnemar_exact_p']:.2e} ({r['seconds']}s)", flush=True)

    done = [g for g in cfg["groups"] if g in report["groups"]]
    if not done:
        return
    # ---- transfer criteria (honest, not a re-tuned gate) ----
    j = {n: max(report["groups"][g][n]["log10_upper95"] for g in done) for n in names}
    report["worst_group_log10U"] = j
    report["improvement_log10"] = j[b] - j[c]
    report["direction_all_groups"] = all(
        report["groups"][g][c]["dfr"] < report["groups"][g][b]["dfr"] for g in done)
    sign_p = {g: report["groups"][g]["sign_test"]["p_two_sided"] for g in done}
    report["holm_sign"] = {g: p for g, p in zip(done, holm_adjust([sign_p[g] for g in done]))}
    rr_ci = {g: report["groups"][g]["cluster_bootstrap"]["ci"]["risk_ratio"] for g in done}
    report["rand_significant"] = bool("G0" in done and sign_p.get("G0", 1.0) < 0.05)
    report["ci_excludes_1"] = {g: bool(lo is not None and lo > 1.0) for g, (lo, hi) in rr_ci.items()}
    worst_g = max(done, key=lambda g: report["groups"][g][b]["log10_upper95"])
    report["transfer_criteria"] = {
        "a_direction_all_groups": report["direction_all_groups"],
        "b_rand_significant": report["rand_significant"],
        "c_ci_excludes_1_rand_or_worst": bool(
            report["ci_excludes_1"].get("G0", False) or report["ci_excludes_1"].get(worst_g, False)),
        "worst_group": worst_g,
    }
    report["groups_completed"] = done
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("\nworst-group log10U:", {k: round(v, 4) for k, v in j.items()},
          f"improvement={report['improvement_log10']:.4f}")
    print("direction_all_groups:", report["direction_all_groups"])
    for g in done:
        lo, hi = rr_ci[g]
        print(f"  [{g}] RR CI=[{lo:.2f},{hi:.2f}] excl1={report['ci_excludes_1'][g]} "
              f"sign p={sign_p[g]:.2e} (Holm {report['holm_sign'][g]:.2e})")
    print("TRANSFER CRITERIA:", report["transfer_criteria"])
    print("saved ->", report_path)


if __name__ == "__main__":
    main()
