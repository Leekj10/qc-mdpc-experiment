#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BIKE-Flip first-round margin scan at P1'.

Question (from the author, 2026-11-17): the BIKE-Flip v5.2 baseline already
carries a first-round margin delta=3.  Is delta=2 better?  What does delta=5
do?  This scan measures the three total first-round margins {2,3,5} on the
same paired instances that the decoder-transfer experiment used.

Design
------
- Work point P1' (r,d,t) = (4801,45,92), G0 keys 54..99 (46 keys), 2,000
  errors per key, identical (H,e,s) across arms, SEED 20260901.
- BIKE-Flip v5.2 schedule, (a,b) from the A.2.4 tangent rule at P1', 7-round
  spec budget, static-distance semantics, round-1 margin = delta only.
- Validation: the delta=3 arm must reproduce the archived bike7_0 per-key
  failure vector exactly; otherwise the run aborts (no analysis).
- Inference: key-cluster percentile bootstrap (B=10000, seed 20260905),
  exact McNemar as a nominal instance-level check.

Run
---
  python lw-vs/scripts/exp_bike_delta_scan.py --smoke
  python lw-vs/scripts/exp_bike_delta_scan.py --run
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from qcmdpc.bikeflip import derive_bikeflip_affine  # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator  # noqa: E402
from qcmdpc.stats import cluster_bootstrap_paired, mcnemar_exact  # noqa: E402
from exp_decoder_transfer import (P1, G0_SPEC, TEST_KEYS, SEED,  # noqa: E402
                                  bike_flip_offset)

OUT = ROOT / "lw-vs" / "results" / "bike_delta_scan"
OUT.mkdir(parents=True, exist_ok=True)
E_PER_KEY = 2000
NB_ITER = 7
DELTAS = (2, 3, 5)
N_WORKERS = int(os.environ.get("DT_WORKERS", "10"))

_POOL = None


def _get_pool():
    global _POOL
    if _POOL is None:
        _POOL = KeyPool(SEED, P1, "G0", G0_SPEC)
    return _POOL


def _work(job):
    ki, n_err = job
    pool = _get_pool()
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "G0", key.key_id, P1, G0_SPEC, key, None)
    r, d, t = P1["r"], P1["d"], P1["t"]
    a, b, _ = derive_bikeflip_affine(r, d, t)
    fail = {dl: np.zeros(n_err, dtype=np.uint8) for dl in DELTAS}
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        for dl in DELTAS:
            res = bike_flip_offset(key, s0.copy(), a, b, dl, NB_ITER, 0)
            fail[dl][eid] = 0 if res.success else 1
    return ki, fail


def _protocol(nkeys: int, nerr: int) -> None:
    path = OUT / "protocol_bike_delta_scan.json"
    if path.exists():
        return
    doc = {
        "phase": "BIKE_DELTA_SCAN",
        "written_by": "Claude (session 2026-11-17)",
        "written_before": "any delta-scan decode",
        "purpose": "Compare total first-round margins delta=2,3,5 for BIKE-Flip "
                   "at P1' on the frozen decoder-transfer instances.",
        "work_point": P1,
        "keys": "G0 pool keys 54..99 (46 keys), identical to the decoder-transfer experiment",
        "errors_per_key": nerr,
        "decoder": "BIKE-Flip v5.2 schedule, A.2.4 (a,b) at P1', 7-round budget, "
                   "static-distance semantics; only the round-1 margin delta varies",
        "arms": list(DELTAS),
        "validation": "delta=3 per-key failures must equal archived bike7_0 exactly",
        "inference": "key-cluster percentile bootstrap B=10000 seed=20260905; "
                     "exact McNemar nominal",
        "n_keys": nkeys,
    }
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")


def run(smoke: bool) -> None:
    keys = TEST_KEYS[:2] if smoke else TEST_KEYS
    nerr = 100 if smoke else E_PER_KEY
    _protocol(len(keys), nerr)
    print(f"[run] {len(keys)} keys, {nerr} errors/key, deltas={DELTAS}, workers={N_WORKERS}")
    t0 = time.time()
    jobs = [(ki, nerr) for ki in keys]
    with ProcessPoolExecutor(max_workers=min(N_WORKERS, len(jobs))) as ex:
        res = list(ex.map(_work, jobs))
    res.sort(key=lambda x: x[0])
    dt = time.time() - t0
    print(f"[run] done in {dt:.1f}s")

    fail = {dl: np.stack([r[1][dl] for r in res]) for dl in DELTAS}
    np.savez_compressed(
        OUT / ("bike_delta_scan_smoke.npz" if smoke else "bike_delta_scan.npz"),
        keys=np.array(keys, dtype=np.int32),
        e_per_key=np.array([nerr], dtype=np.int32),
        **{f"fail_d{dl}": fail[dl] for dl in DELTAS},
    )
    if smoke:
        print("[smoke] saved; run without --smoke for the full scan")
        return

    # validation against the archived delta=3 arm
    archived = np.load(ROOT / "lw-vs" / "results" / "decoder_transfer" / "decoder_transfer_full.npz")
    ref = archived["fail_bike7_0"]
    if ref.shape != fail[3].shape or not np.array_equal(ref, fail[3]):
        raise SystemExit("[validation] delta=3 does not reproduce archived bike7_0; abort")

    summary = {"keys": [keys[0], keys[-1]], "n_keys": len(keys),
               "errors_per_key": nerr, "trials_per_arm": len(keys) * nerr,
               "validation": "delta=3 == archived bike7_0 (exact)"}
    base = fail[3]
    for dl in DELTAS:
        if dl == 3:
            continue
        c = cluster_bootstrap_paired(base.sum(axis=1), fail[dl].sum(axis=1), nerr)
        b_only = int(((base == 0) & (fail[dl] == 1)).sum())
        t_only = int(((base == 1) & (fail[dl] == 0)).sum())
        summary[f"delta{3}_vs_delta{dl}"] = {
            "failures_delta3": int(base.sum()),
            "failures_other": int(fail[dl].sum()),
            "dfr_delta3": float(base.mean()),
            "dfr_other": float(fail[dl].mean()),
            "risk_ratio": c["point"]["risk_ratio"],
            "rr_ci95": c["ci"]["risk_ratio"],
            "dfr_diff": c["point"]["dfr_diff"],
            "mcnemar_base_only": b_only,
            "mcnemar_other_only": t_only,
            "mcnemar_p": mcnemar_exact(b_only, t_only),
            "keys_improved_vs_delta3": int((fail[dl].sum(axis=1) < base.sum(axis=1)).sum()),
            "keys_worsened_vs_delta3": int((fail[dl].sum(axis=1) > base.sum(axis=1)).sum()),
            "keys_tied_vs_delta3": int((fail[dl].sum(axis=1) == base.sum(axis=1)).sum()),
        }
    # delta2 vs delta5 contrast
    c25 = cluster_bootstrap_paired(fail[5].sum(axis=1), fail[2].sum(axis=1), nerr)
    summary["delta5_vs_delta2"] = {
        "failures_delta5": int(fail[5].sum()),
        "failures_delta2": int(fail[2].sum()),
        "risk_ratio_delta5_over_delta2": c25["point"]["risk_ratio"],
        "rr_ci95": c25["ci"]["risk_ratio"],
    }
    (OUT / "bike_delta_scan_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if not (args.smoke or args.run):
        ap.error("pass --smoke or --run")
    run(args.smoke)
