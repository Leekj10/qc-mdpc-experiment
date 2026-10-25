"""Experiment runner: fixed-key x error-pool matrix, all decoders on identical
(H, e, s) pairs. Writes JSONL samples + per-key summary + manifest.

Usage:
    python runner.py --config configs/pilot_p0.json --out results/pilot_p0
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import build_decoder
from qcmdpc.generators import KeyPool, make_error_generator
from qcmdpc.stats import per_key_summary, wilson_upper
from qcmdpc.taxonomy import classify_failure


def run(config_path: str, out_dir: str, sample_failures_jsonl: bool = True):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    param = cfg["parameter"]
    master_seed = cfg["seed"]
    errors_per_key = cfg["errors_per_key"]
    started = time.time()
    manifest = {
        "config_sha256": hashlib.sha256(open(config_path, "rb").read()).hexdigest(),
        "config_path": config_path,
        "parameter": param,
        "seed": master_seed,
        "errors_per_key": errors_per_key,
        "start_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "groups": {},
    }

    for group_id, gspec in cfg["groups"].items():
        pool = KeyPool(master_seed, param, group_id, gspec)
        gdir = os.path.join(out_dir, group_id)
        os.makedirs(gdir, exist_ok=True)
        with open(os.path.join(gdir, "key_structure_report.json"), "w", encoding="utf-8") as f:
            json.dump(pool.reports, f, indent=1)

        group_out = {"key_report_attempts": pool.attempts_total, "decoders": {}}
        for dec_name, dspec in cfg["decoders"].items():
            run_dec = build_decoder(dec_name, dspec, param["d"], param["t"], param["r"])
            failures = np.zeros(len(pool.keys), dtype=np.int64)
            trials = np.full(len(pool.keys), errors_per_key, dtype=np.int64)
            mode_counts: dict[str, int] = {}
            iter_sum = 0
            sample_path = os.path.join(gdir, f"samples_{dec_name}.jsonl")
            fs = open(sample_path, "w", encoding="utf-8") if sample_failures_jsonl else None
            t0 = time.time()
            for ki, key in enumerate(pool.keys):
                ncw = pool.ncws.get(key.key_id)
                egen = make_error_generator(master_seed, group_id, key.key_id, param, gspec, key, ncw)
                e_support_cache = {}
                for eid in range(errors_per_key):
                    e = egen(eid)
                    s0 = key.syndrome_from_global(e)
                    need_flips = True  # log flips for taxonomy (pilot; drop for scale runs)
                    traj = run_dec(key, s0, record_flips=need_flips)
                    iter_sum += traj.n_iters_run
                    if not traj.success:
                        failures[ki] += 1
                        e_sup = set(int(x) for x in np.nonzero(e)[0])
                        mode = classify_failure(
                            traj,
                            e_sup,
                            max_iter=int(dspec.get("max_iter", param["t"])),
                        )
                        mode_counts[mode] = mode_counts.get(mode, 0) + 1
                        if fs is not None:
                            fs.write(
                                json.dumps(
                                    {
                                        "key_id": key.key_id,
                                        "error_id": eid,
                                        "decoder": dec_name,
                                        "mode": mode,
                                        "iters": traj.n_iters_run,
                                        "sw_first": traj.syndrome_weights[0] if traj.syndrome_weights else None,
                                        "sw_last": traj.syndrome_weights[-1] if traj.syndrome_weights else None,
                                    }
                                )
                                + "\n"
                            )
            if fs is not None:
                fs.close()
            n_decodes = len(pool.keys) * errors_per_key
            summary = per_key_summary(failures, trials)
            summary["decoder"] = dec_name
            summary["avg_iters_run"] = iter_sum / max(1, n_decodes)
            summary["failure_modes"] = mode_counts
            summary["wall_seconds"] = round(time.time() - t0, 1)
            summary["ms_per_decode"] = round(1000.0 * (time.time() - t0) / max(1, n_decodes), 3)
            with open(os.path.join(gdir, f"summary_{dec_name}.json"), "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=1)
            group_out["decoders"][dec_name] = summary
        manifest["groups"][group_id] = {
            "n_keys": len(pool.keys),
            "decoders": list(cfg["decoders"].keys()),
        }

    manifest["end_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest["wall_seconds_total"] = round(time.time() - started, 1)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    # console report
    print(f"[done] {out_dir}  total {manifest['wall_seconds_total']} s")
    for gid, g in manifest["groups"].items():
        for d in g["decoders"]:
            s = json.load(open(os.path.join(out_dir, gid, f"summary_{d}.json"), encoding="utf-8"))
            print(
                f"  {gid:8s} {d:8s} DFR={s['overall_dfr']:.3e}  zero-keys={s['keys_zero_failures']}/{s['n_keys']}"
                f"  avg_iters={s['avg_iters_run']:.2f}  {s['ms_per_decode']} ms/dec"
            )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run(args.config, args.out)
