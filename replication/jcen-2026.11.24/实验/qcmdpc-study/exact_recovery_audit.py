"""Audit zero-syndrome success against exact error recovery on P1' samples.

The historical formal run counted ``syndrome == 0`` as success.  This script
replays the same deterministic fresh-key pool and error streams while tracking
the decoder's flip parity, then reports both the historical outcome and exact
recovery.  It writes only to ``results/exact_recovery_audit_20260923`` by
default and can be resumed group by group.

Examples (from this directory)::

    python exact_recovery_audit.py --keys 2 --errors 20
    python exact_recovery_audit.py --full

``--keys`` and ``--errors`` are pilot controls.  ``--full`` uses the frozen
formal pool (92/94/92 fresh keys and 3,000 errors/key).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import build_decoder
from qcmdpc.generators import KeyPool, make_error_generator
from qcmdpc.stats import wilson_upper
from search_m4 import CANDIDATES


OUT = Path(__file__).resolve().parent / "results" / "exact_recovery_audit_20260923"
PARAM = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
SEED = 20260901
FULL_ERRORS = 3000
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 100}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 100, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 100, "kappa": 12,
                      "max_syn_weight": None, "require_better_than_canonical": True},
           "fresh_from": 8},
}
ARMS = {"C0_base": CANDIDATES["C0_base"], "FRO-2": CANDIDATES["C4_first_p2"]}
PROTOCOL = "exact_recovery_audit_v1"


def _script_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _summary_row(name: str, counts: dict[str, int], n: int, seconds: float,
                 n_keys: int, errors_per_key: int) -> dict:
    zero = counts["zero_syndrome"]
    exact = counts["exact_recovery"]
    mis = counts["zero_syndrome_miscorrection"]
    nonzero = counts["nonzero_syndrome"]
    return {
        "decoder": name,
        "n_keys": n_keys,
        "errors_per_key": errors_per_key,
        "processed": n,
        "trials": n,
        "zero_syndrome": zero,
        "nonzero_syndrome": nonzero,
        "zero_syndrome_rate": zero / n if n else None,
        "zero_syndrome_miscorrections": mis,
        "exact_recovery": exact,
        "exact_recovery_failures": n - exact,
        "exact_recovery_rate": exact / n if n else None,
        "miscorrection_rate_among_zero_syndrome": mis / zero if zero else 0.0,
        "zero_syndrome_upper95_if_zero": wilson_upper(0, n) if n else None,
        "seconds": round(seconds, 3),
        "ms_per_decode": 1000.0 * seconds / n if n else None,
        "count_identity": "processed = zero_syndrome + nonzero_syndrome; "
                          "exact_recovery_failures = nonzero_syndrome + "
                          "zero_syndrome_miscorrections",
    }


def run_group(gid: str, n_keys: int | None, errors_per_key: int,
              out_dir: Path) -> dict:
    g = GROUPS[gid]
    pool = KeyPool(SEED, PARAM, gid, g["spec"])
    start_idx = g["fresh_from"]
    stop_idx = len(pool.keys) if n_keys is None else min(start_idx + n_keys, len(pool.keys))
    idxs = list(range(start_idx, stop_idx))
    if not idxs:
        raise ValueError(f"{gid}: no keys selected")
    decs = {name: build_decoder(name, spec, PARAM["d"], PARAM["t"], PARAM["r"])
            for name, spec in ARMS.items()}
    counts = {
        name: {"zero_syndrome": 0, "nonzero_syndrome": 0,
               "zero_syndrome_miscorrection": 0, "exact_recovery": 0}
        for name in ARMS
    }
    per_key = {name: [] for name in ARMS}
    arm_seconds = {name: 0.0 for name in ARMS}
    total = len(idxs) * errors_per_key
    t0 = time.time()
    for pos, ki in enumerate(idxs, 1):
        key = pool.keys[ki]
        gen = make_error_generator(SEED, gid, key.key_id, PARAM, g["spec"], key,
                                   pool.ncws.get(key.key_id))
        key_counts = {name: {k: 0 for k in counts[name]} for name in ARMS}
        for eid in range(errors_per_key):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            for name, dec in decs.items():
                arm_start = time.perf_counter()
                traj = dec(key, s0.copy(), track_estimate=True)
                arm_seconds[name] += time.perf_counter() - arm_start
                if traj.estimated_error is None:
                    raise RuntimeError(f"{name} did not return an estimate")
                zero = bool(traj.success)
                exact = bool(np.array_equal(traj.estimated_error, e))
                if zero:
                    key_counts[name]["zero_syndrome"] += 1
                else:
                    key_counts[name]["nonzero_syndrome"] += 1
                if zero and not exact:
                    key_counts[name]["zero_syndrome_miscorrection"] += 1
                if exact:
                    key_counts[name]["exact_recovery"] += 1
        for name in ARMS:
            for k in counts[name]:
                counts[name][k] += key_counts[name][k]
            per_key[name].append({"key_index": ki, **key_counts[name]})
        elapsed = time.time() - t0
        print(f"[{gid}] {pos}/{len(idxs)} keys processed; "
              f"{elapsed/60:.1f} min elapsed", flush=True)
    elapsed = time.time() - t0
    rows = {name: _summary_row(name, counts[name], total, arm_seconds[name],
                               len(idxs), errors_per_key) for name in ARMS}
    return {
        "gid": gid,
        "parameter": PARAM,
        "seed": SEED,
        "fresh_index_range": [start_idx, stop_idx],
        "n_keys": len(idxs),
        "errors_per_key": errors_per_key,
        "processed": total,
        "seconds": round(elapsed, 3),
        "arms": rows,
        "per_key": per_key,
    }


def aggregate_groups(group_rows: dict[str, dict]) -> dict[str, dict]:
    """Pool count-preserving fields across completed groups."""
    out: dict[str, dict] = {}
    for result in group_rows.values():
        for name, row in result["arms"].items():
            agg = out.setdefault(name, {"decoder": name, "n_keys": 0,
                                        "errors_per_key": row["errors_per_key"],
                                        "processed": 0, "trials": 0,
                                        "zero_syndrome": 0, "nonzero_syndrome": 0,
                                        "zero_syndrome_miscorrections": 0,
                                        "exact_recovery": 0,
                                        "exact_recovery_failures": 0,
                                        "seconds": 0.0})
            for field in ("n_keys", "processed", "trials", "zero_syndrome",
                          "nonzero_syndrome", "zero_syndrome_miscorrections",
                          "exact_recovery", "exact_recovery_failures", "seconds"):
                agg[field] += row[field]
    for row in out.values():
        n = row["processed"]
        zero = row["zero_syndrome"]
        row["zero_syndrome_rate"] = zero / n if n else None
        row["exact_recovery_rate"] = row["exact_recovery"] / n if n else None
        row["miscorrection_rate_among_zero_syndrome"] = (
            row["zero_syndrome_miscorrections"] / zero if zero else 0.0)
        row["ms_per_decode"] = 1000.0 * row["seconds"] / n if n else None
        row["count_identity"] = (
            "processed = zero_syndrome + nonzero_syndrome; "
            "exact_recovery_failures = nonzero_syndrome + "
            "zero_syndrome_miscorrections")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--group", action="append", choices=list(GROUPS),
                    help="repeat to select groups; defaults to all groups")
    ap.add_argument("--keys", type=int, default=None,
                    help="pilot keys per group from the formal fresh-key range")
    ap.add_argument("--errors", type=int, default=None,
                    help=f"errors per key; default is {FULL_ERRORS} for --full")
    ap.add_argument("--full", action="store_true",
                    help="use the complete formal pool: 92/94/92 keys x 3000 errors")
    args = ap.parse_args()
    if args.full and (args.keys is not None or args.errors is not None):
        raise SystemExit("--full cannot be combined with --keys or --errors")
    if args.full:
        n_keys, errors = None, FULL_ERRORS
    else:
        n_keys = args.keys if args.keys is not None else 1
        errors = args.errors if args.errors is not None else 20
        if n_keys < 1 or errors < 1:
            raise SystemExit("--keys and --errors must be positive")
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    groups = args.group or list(GROUPS)
    manifest_path = out / "manifest.json"
    manifest = {
        "protocol": PROTOCOL,
        "parameter": PARAM,
        "seed": SEED,
        "formal_fresh_from": {g: GROUPS[g]["fresh_from"] for g in GROUPS},
        "arms": list(ARMS),
        "selection": {"groups": groups, "keys_per_group": n_keys,
                       "errors_per_key": errors},
        "success_definitions": {
            "zero_syndrome": "decoder trajectory ended with syndrome weight zero",
            "exact_recovery": "tracked flip parity equals generated error vector",
            "zero_syndrome_miscorrection": "zero_syndrome and not exact_recovery",
        },
        "script_sha256": _script_sha256(),
        "created_unix": time.time(),
    }
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        prior_selection = prior.get("selection", {})
        if prior.get("protocol") != PROTOCOL or prior.get("script_sha256") != manifest["script_sha256"]:
            raise SystemExit(f"Refusing to mix incompatible audit in {out}; choose a new --out")
        if prior_selection.get("errors_per_key") != errors:
            raise SystemExit("Existing audit uses a different --errors; choose a new --out")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    all_report = {"manifest": manifest, "groups": {}}
    report_path = out / "report.json"
    if report_path.exists():
        all_report = json.loads(report_path.read_text(encoding="utf-8"))
    for gid in groups:
        path = out / f"group_{gid}.json"
        if path.exists():
            print(f"[{gid}] existing result found; skipping", flush=True)
            all_report["groups"][gid] = json.loads(path.read_text(encoding="utf-8"))
            continue
        print(f"[{gid}] starting exact-recovery audit", flush=True)
        result = run_group(gid, n_keys, errors, out)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        all_report["groups"][gid] = result
        report_path.write_text(json.dumps(all_report, indent=2), encoding="utf-8")
        for name, row in result["arms"].items():
            print(f"[{gid}] {name}: zero={row['zero_syndrome']}/{row['processed']} "
                  f"miscorrect={row['zero_syndrome_miscorrections']} "
                  f"exact={row['exact_recovery']}/{row['processed']} "
                  f"({row['seconds']:.1f}s)", flush=True)
    all_report["overall"] = aggregate_groups(all_report["groups"])
    report_path.write_text(json.dumps(all_report, indent=2), encoding="utf-8")
    print(f"Completed exact-recovery audit in {out}")


if __name__ == "__main__":
    main()
