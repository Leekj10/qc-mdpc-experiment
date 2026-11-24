#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BIKE-Flip first-round-only margin arm: total margin 2 (offset -1).

The decoder-transfer experiment already archived offsets 0 and +2 (total
first-round margins 3 and 5).  This adds offset -1 (total 2) on the same
paired instances so the author's 2/3/5 question can be answered in the
first-round-only framing used by the paper.

Run: python lw-vs/scripts/exp_bike_first_round_margin.py
"""
from __future__ import annotations

import json
import os
import sys
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
from qcmdpc.stats import holm_adjust  # noqa: E402

OUT = ROOT / "lw-vs" / "results" / "bike_delta_scan"
OUT.mkdir(parents=True, exist_ok=True)
E_PER_KEY = 2000
NB_ITER = 7
DELTA = 3
OFFSET = -1
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
    fail = np.zeros(n_err, dtype=np.uint8)
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        res = bike_flip_offset(key, s0.copy(), a, b, DELTA, NB_ITER, OFFSET)
        fail[eid] = 0 if res.success else 1
    return ki, fail


def main() -> None:
    keys = TEST_KEYS
    jobs = [(ki, E_PER_KEY) for ki in keys]
    with ProcessPoolExecutor(max_workers=min(N_WORKERS, len(jobs))) as ex:
        res = list(ex.map(_work, jobs))
    res.sort(key=lambda x: x[0])
    fail = np.stack([r[1] for r in res])
    np.savez_compressed(OUT / "bike_first_round_m1.npz",
                        keys=np.array(keys, dtype=np.int32),
                        e_per_key=np.array([E_PER_KEY], dtype=np.int32),
                        fail_m1=fail)

    arch = np.load(ROOT / "lw-vs" / "results" / "decoder_transfer" / "decoder_transfer_full.npz")
    f0 = arch["fail_bike7_0"]
    fp2 = arch["fail_bike7_p2"]
    base = f0
    summary = {
        "framing": "first-round-only margin, delta=3 for all rounds, 7-round budget",
        "trials_per_arm": len(keys) * E_PER_KEY,
        "validation": "offset 0 and +2 come from the archived decoder-transfer npz",
        "margins": {},
    }
    for name, arr in (("2 (offset -1)", fail), ("3 (offset 0)", f0), ("5 (offset +2)", fp2)):
        summary["margins"][name] = {
            "failures": int(arr.sum()),
            "dfr": float(arr.mean()),
            "per_key_min": int(arr.sum(axis=1).min()),
            "per_key_max": int(arr.sum(axis=1).max()),
        }
    c2 = cluster_bootstrap_paired(base.sum(axis=1), fail.sum(axis=1), E_PER_KEY)
    c5 = cluster_bootstrap_paired(base.sum(axis=1), fp2.sum(axis=1), E_PER_KEY)
    summary["margin3_vs_margin2"] = {
        "rr": c2["point"]["risk_ratio"], "rr_ci95": c2["ci"]["risk_ratio"],
        "mcnemar_p": mcnemar_exact(int(((base == 0) & (fail == 1)).sum()),
                                   int(((base == 1) & (fail == 0)).sum())),
        "keys_better": int((fail.sum(axis=1) < base.sum(axis=1)).sum()),
        "keys_worse": int((fail.sum(axis=1) > base.sum(axis=1)).sum()),
    }
    summary["margin3_vs_margin5"] = {
        "rr": c5["point"]["risk_ratio"], "rr_ci95": c5["ci"]["risk_ratio"],
        "mcnemar_p": mcnemar_exact(int(((base == 0) & (fp2 == 1)).sum()),
                                   int(((base == 1) & (fp2 == 0)).sum())),
        "keys_better": int((fp2.sum(axis=1) < base.sum(axis=1)).sum()),
        "keys_worse": int((fp2.sum(axis=1) > base.sum(axis=1)).sum()),
    }
    (OUT / "bike_first_round_margin_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
