"""Q2-A: kappa>d TRUE near-codeword capture, DE-CONFOUNDED (review round-3, Q2 priority-1).

Addresses the two methodological critiques of the original G3/NCW-intersecting group:
  (i)  capture requires kappa > d (wt(e+ncw)=t+2d-2kappa < t); the old group used
       kappa=12 < d=45, so it was a shallow-intersection control, not capture;
  (ii) the old group REJECTED keys lacking a better-than-canonical near-codeword,
       so it changed BOTH the key distribution and the error distribution (confound).

Design (de-confounded): ONE FIXED batch of keys and ONLY the error construction varies:
    rand  : uniform weight-t errors
    k12   : kappa=12  (shallow, kappa<d, control)
    k46   : kappa=46  (kappa>d, TRUE capture)
    k60   : kappa=60  (kappa>d, stronger capture)
Because every construction is evaluated on the SAME keys, the kappa-gradient and the
C0-vs-FRO-2 arm contrast are separated from any key-selection effect (the old G3
confound). The batch is built with require_better_than_canonical=True so each key
genuinely admits a near-codeword (needed for kappa>d to be a TRUE capture); hence
ABSOLUTE DFR levels are conditional on this ncw-admissible batch and are reported as
such, while the WITHIN-batch contrasts are de-confounded.
Each construction is evaluated on identical (H,e,s) for C0_base vs C4_first_p2
(paired).

Reports per construction: C0/FRO-2 DFR + Wilson U95, paired McNemar, per-key sign
test, key-cluster bootstrap RR CI; plus the C0 DFR gradient rand->k12->k46->k60
(capture severity) and whether FRO-2 still helps under true capture.

Output: results/q2_capture/report.json
Usage : python capture_deconfound.py [--config configs/q2_capture_deconfound.json]
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
from qcmdpc.generators import (KeyPool, _child_seed, ncw_pressure_error,
                               uniform_fixed_weight)
from qcmdpc.stats import (cluster_bootstrap_paired, holm_adjust, mcnemar_exact,
                          sign_test_paired, wilson_upper)

OUT = "results/q2_capture"
BOOT_SEED = 20260905


def run(cfg):
    param, seed = cfg["parameter"], cfg["seed"]
    E = cfg["errors_per_key"]
    K = cfg["keys_per_group"]
    kappas = cfg["kappas"]
    constructions = ["rand"] + [f"k{k}" for k in kappas]
    # Fixed key batch; genuine near-codewords (require_better_than_canonical=True) so
    # kappa>d is a TRUE capture. Within-batch contrasts are de-confounded; absolute
    # DFR is conditional on this ncw-admissible batch.
    spec = {"type": "ncw", "n_keys": K, "kappa": kappas[0],
            "max_syn_weight": None,
            "require_better_than_canonical": bool(cfg.get("require_better_than_canonical", True))}
    t0 = time.time()
    pool = KeyPool(seed, param, "Gcap", spec)
    decs = {n: build_decoder(n, d, param["d"], param["t"], param["r"])
            for n, d in cfg["decoders"].items()}
    names = list(cfg["decoders"])
    n = 2 * param["r"]
    t = param["t"]

    report = {"config": cfg.get("_path", "configs/q2_capture_deconfound.json"),
              "param": param, "E_per_key": E, "keys_per_group": K,
              "kappas": kappas, "note": ("de-confounded kappa>d capture: ONE fixed key "
                                         "batch, error construction varies; absolute DFR "
                                         "conditional on the ncw-admissible batch"),
              "constructions": {}}
    for cons in constructions:
        kappa = 0 if cons == "rand" else int(cons[1:])
        ckpt = os.path.join(OUT, f"cons_{cons}.json")
        if os.path.exists(ckpt):
            report["constructions"][cons] = json.load(open(ckpt, encoding="utf-8"))
            print(f"[{cons:6s}] kappa={kappa:3d}  loaded from checkpoint", flush=True)
            continue
        per_key = {nm: [] for nm in names}
        fail_idx = {nm: [] for nm in names}
        n_samples = 0
        for ki, key in enumerate(pool.keys):
            ncw = pool.ncws.get(key.key_id)
            counts = {nm: 0 for nm in names}
            for eid in range(E):
                rng = np.random.default_rng(_child_seed(seed, f"err|Gcap|{cons}|{key.key_id}", eid))
                if cons == "rand":
                    e = uniform_fixed_weight(rng, n, t)
                else:
                    e = ncw_pressure_error(rng, key, ncw, t, kappa)
                s0 = key.syndrome_from_global(e)
                for nm in names:
                    if not decs[nm](key, s0.copy()).success:
                        counts[nm] += 1
                        fail_idx[nm].append((ki, eid))
                n_samples += 1
            for nm in names:
                per_key[nm].append(counts[nm])
        b, c = names[0], names[1]
        s0f, s4f = set(fail_idx[b]), set(fail_idx[c])
        entry = {"kappa": kappa, "n_keys": K, "n_samples": n_samples,
                 "paired": {"c0_only": len(s0f - s4f), "c4_only": len(s4f - s0f),
                            "both": len(s0f & s4f),
                            "mcnemar_exact_p": mcnemar_exact(len(s0f - s4f), len(s4f - s0f))}}
        for nm in names:
            f = len(fail_idx[nm])
            u = wilson_upper(f, n_samples)
            entry[nm] = {"failures": f, "trials": n_samples, "dfr": f / n_samples,
                         "upper95": u, "log10_upper95": float(np.log10(u)),
                         "per_key_failures": per_key[nm]}
        entry["sign_test"] = sign_test_paired(per_key[b], per_key[c])
        entry["cluster_bootstrap"] = cluster_bootstrap_paired(per_key[b], per_key[c], E,
                                                              B=10000, seed=BOOT_SEED)
        report["constructions"][cons] = entry
        with open(ckpt, "w", encoding="utf-8") as f:
            json.dump(entry, f)
        print(f"[{cons:6s}] kappa={kappa:3d}  C0={entry[b]['failures']}/{n_samples} "
              f"({entry[b]['dfr']:.3e})  FRO2={entry[c]['failures']}/{n_samples} "
              f"({entry[c]['dfr']:.3e})  RR={entry['cluster_bootstrap']['point']['risk_ratio']:.2f} "
              f"CI[{entry['cluster_bootstrap']['ci']['risk_ratio'][0]:.2f},"
              f"{entry['cluster_bootstrap']['ci']['risk_ratio'][1]:.2f}] "
              f"({time.time()-t0:.0f}s)", flush=True)

    # C0 capture-severity gradient rand -> k12 -> k46 -> k60
    grad = {}
    base_dfr = report["constructions"]["rand"][names[0]]["dfr"]
    for cons in constructions:
        d = report["constructions"][cons][names[0]]["dfr"]
        grad[cons] = {"c0_dfr": d, "ratio_vs_rand": (d / base_dfr) if base_dfr > 0 else None}
    report["c0_capture_gradient"] = grad
    # Holm across constructions for the arm sign tests
    sp = [report["constructions"][c]["sign_test"]["p_two_sided"] for c in constructions]
    report["holm_sign"] = {c: p for c, p in zip(constructions, holm_adjust(sp))}
    report["seconds"] = round(time.time() - t0, 1)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/q2_capture_deconfound.json")
    args = ap.parse_args()
    cfg = json.load(open(args.config, encoding="utf-8"))
    cfg["_path"] = args.config
    os.makedirs(OUT, exist_ok=True)
    rep = run(cfg)
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print("\n== C0 capture-severity gradient (rand -> kappa>d) ==")
    for c, g in rep["c0_capture_gradient"].items():
        print(f"  {c:6s} C0 DFR={g['c0_dfr']:.3e}  x{g['ratio_vs_rand']:.2f} vs rand")
    print("holm_sign:", {k: f"{v:.2e}" for k, v in rep["holm_sign"].items()})
    print("saved ->", os.path.join(OUT, "report.json"))


if __name__ == "__main__":
    main()
