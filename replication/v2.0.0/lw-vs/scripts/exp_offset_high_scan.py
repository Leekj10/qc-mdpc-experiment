#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""High-offset extension of the P1' local scan (2026-11-16).

Purpose
-------
The cross-decoder table compares a first-round +2 on the classic carrier with
a first-round +2 on BIKE-Flip.  BIKE-Flip's baseline already carries the
specification's delta=3, so its round-one threshold is 32 at offset zero while
the classic binomial threshold is 29, and its "+2" arm reaches 34.  Relative to
the classic carrier, that arm is therefore a +5 offset, not a +2.

The existing local scan (exp_offset_scan_p1p.py) stops at +3, so the
alternative explanation "the BIKE-Flip reversal is a single unimodal offset
response overshooting at +5" cannot be excluded from the current archive.
This script measures CLASSIC at +4 and +5 on the same formal pools, same
seeds, same error streams and same budget, so the +5 regime of the classic
carrier becomes observable.

Arms
----
C0     [0]        baseline and gate
FRO-2  [2, 0]     gate (reproduces the archived FRO-2 counts exactly)
FRO-4  [4, 0]     NEW
FRO-5  [5, 0]     NEW

Protocol: lw-vs/results/offset_high_scan/protocol_offset_high.json, frozen
before any decode.  Gate: C0 and FRO-2 must reproduce the archived per-key
failure vectors on every condition, otherwise the run is void.

Run
---
  python lw-vs/scripts/exp_offset_high_scan.py --smoke
  python lw-vs/scripts/exp_offset_high_scan.py
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
OUT = ROOT / "lw-vs" / "results" / "offset_high_scan"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder                          # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator        # noqa: E402
from qcmdpc.stats import (wilson_upper, cluster_bootstrap_paired,  # noqa: E402
                          sign_test_paired)

SEED = 20260901
MAX_ITER = 20
N_WORKERS = int(os.environ.get("RC_WORKERS", "10"))

P1 = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
E_PER_KEY = 3000
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 100}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 100, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 100, "kappa": 12, "max_syn_weight": None,
                    "require_better_than_canonical": True}, "fresh_from": 8},
}
COND = {"G0": "RAND", "G2_d12": "TYPE-I", "G3": "NCW-shallow"}
EXPECTED = {"G0": (282, 68), "G2_d12": (372, 68), "G3": (141, 31)}

ARMS = {
    "C0":    [0],
    "FRO-2": [2, 0],
    "FRO-4": [4, 0],
    "FRO-5": [5, 0],
}
ARM_NOTE = {
    "C0": "baseline and gate",
    "FRO-2": "first round +2, gate",
    "FRO-4": "first round +4 (NEW 2026-11-16)",
    "FRO-5": "first round +5 (NEW 2026-11-16); equals BIKE-Flip +2 in total margin",
}


def _dec(name):
    return build_decoder(name, {"algo": "bf_parallel",
                                "threshold": {"type": "offset",
                                              "base": {"type": "classic"},
                                              "offsets": ARMS[name]},
                                "max_iter": MAX_ITER},
                         P1["d"], P1["t"], P1["r"])


def _work_p1(job):
    gid, ki, n_err = job
    pool = KeyPool(SEED, P1, gid, GROUPS[gid]["spec"])
    key = pool.keys[ki]
    gen = make_error_generator(SEED, gid, key.key_id, P1, GROUPS[gid]["spec"], key,
                               pool.ncws.get(key.key_id))
    decs = {n: _dec(n) for n in ARMS}
    fails = {n: 0 for n in ARMS}
    for eid in range(n_err):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        for n, d in decs.items():
            if not d(key, s.copy()).success:
                fails[n] += 1
    return gid, ki, fails


def _write_protocol(n_err):
    proto = {
        "phase": "OFFSET_HIGH_SCAN",
        "written_before": "any decode of FRO-4 or FRO-5",
        "purpose": ("Measure the classic carrier at first-round +4 and +5 so that the "
                    "BIKE-Flip +2 arm (total first-round margin +5 relative to ft(S0)) "
                    "can be compared at equal absolute offset."),
        "work_point": P1,
        "keys": "same formal pools, same fresh_from splits and same seeds as "
                "exp_offset_scan_p1p.py phase 1",
        "errors_per_key": n_err,
        "arms": {n: {"offsets": ARMS[n], "note": ARM_NOTE[n]} for n in ARMS},
        "gate": "C0 and FRO-2 must reproduce the archived per-key failure counts "
                "(G0 282/68, G2_d12 372/68, G3 141/31); otherwise the run is void.",
        "predictions": {
            "H_high": ("If the BIKE-Flip reversal is an overshoot of a single unimodal "
                       "offset response, the classic carrier should stop improving and "
                       "eventually reverse by +5. If the classic carrier still improves "
                       "at +5, the BIKE-Flip reversal is not explained by offset "
                       "magnitude alone."),
        },
        "reporting": "Every arm is reported regardless of direction.",
    }
    with open(OUT / "protocol_offset_high.json", "w", encoding="utf-8") as f:
        json.dump(proto, f, indent=1)


def phase1(n_err=E_PER_KEY, groups=None) -> bool:
    gids = list(GROUPS) if groups is None else [g for g in groups if g in GROUPS]
    print(f"[high scan] P1' arms {list(ARMS)} at {n_err} errors/key, groups {gids}")
    rep = {"phase": "high", "parameter": P1, "errors_per_key": n_err,
           "arms": {n: {"offsets": ARMS[n], "note": ARM_NOTE[n]} for n in ARMS},
           "groups": {}}
    gate = True
    for gid in gids:
        g = GROUPS[gid]
        pool = KeyPool(SEED, P1, gid, g["spec"])
        idxs = list(range(g["fresh_from"], len(pool.keys)))
        res = list(ProcessPoolExecutor(max_workers=N_WORKERS).map(
            _work_p1, [(gid, k, n_err) for k in idxs]))
        n_keys, n_dec = len(idxs), len(idxs) * n_err
        per = {n: np.zeros(n_keys, dtype=np.int64) for n in ARMS}
        for _, ki, fails in res:
            j = idxs.index(ki)
            for n in ARMS:
                per[n][j] = fails[n]
        cell = {"condition": COND[gid], "n_keys": n_keys, "trials": n_dec, "arms": {}}
        for n in ARMS:
            k = int(per[n].sum())
            d = {"failures": k, "trials": n_dec, "dfr": k / n_dec,
                 "upper95": wilson_upper(k, n_dec),
                 "per_key_failures": per[n].tolist()}
            if n != "C0":
                boot = cluster_bootstrap_paired(per["C0"], per[n], n_err,
                                                B=10000, seed=20260905)
                sg = sign_test_paired(per["C0"], per[n])
                d["rr_vs_C0"] = boot["point"]["risk_ratio"]
                d["rr_ci95"] = boot["ci"]["risk_ratio"]
                d["rr_excludes_1"] = boot["rr_excludes_1"]
                d["sign_test"] = sg
            cell["arms"][n] = d
        c0, f2 = int(per["C0"].sum()), int(per["FRO-2"].sum())
        ok = (c0, f2) == EXPECTED[gid]
        gate &= ok
        print(f"  [{COND[gid]:12s}] C0 {c0} (archive {EXPECTED[gid][0]}) "
              f"FRO-2 {f2} (archive {EXPECTED[gid][1]}) {'OK' if ok else '*** MISMATCH ***'}")
        for n in ("FRO-4", "FRO-5"):
            a = cell["arms"][n]
            print(f"     {n:7s} {a['failures']:5d}/{n_dec}  DFR={a['dfr']:.4e}  "
                  f"RR={a['rr_vs_C0']:.3f} [{a['rr_ci95'][0]:.3f}, {a['rr_ci95'][1]:.3f}] "
                  f"excl1={a['rr_excludes_1']}", flush=True)
        rep["groups"][gid] = cell
    rep["gate_passed"] = gate
    name = "phase1_high_smoke.json" if n_err != E_PER_KEY else "phase1_high.json"
    with open(OUT / name, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print(f"  gate: {'PASS' if gate else 'FAIL'}")
    return gate


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--groups", default=None,
                    help="comma-separated subset of G0,G2_d12,G3 (default: all)")
    a = ap.parse_args()
    gsel = None if not a.groups else [x.strip() for x in a.groups.split(",")]
    t0 = time.time()
    if a.smoke:
        # Gate is not expected to hold on a reduced sample; report only.
        ok = phase1(n_err=100, groups=gsel)
    else:
        _write_protocol(E_PER_KEY)
        ok = phase1(E_PER_KEY, groups=gsel)
    print(f"elapsed {time.time() - t0:.1f}s")
    sys.exit(0 if ok or a.smoke else 1)
