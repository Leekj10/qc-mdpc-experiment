"""Pre-registered expanded confirmation experiment for temporal threshold shaping.

This run is intentionally separate from the exploratory 12-key/400-error matrix.
It uses a fresh master seed, 50 fresh keys per condition, and 1,000 paired errors
per key at the two already calibrated work points P2 and P3.  Results are written
cell-by-cell so an interrupted run can be resumed without changing the protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

STUDY = Path(__file__).resolve().parents[1] / "实验" / "qcmdpc-study"
sys.path.insert(0, str(STUDY))
from qcmdpc.decoders import build_decoder  # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator  # noqa: E402
from qcmdpc.stats import wilson_upper  # noqa: E402


MASTER_SEED = 20260912
N_KEYS = 50
ERRORS_PER_KEY = 1000
GROUPS = {
    "G0": {"type": "random", "n_keys": N_KEYS},
    "G2_d12": {"type": "type1", "n_keys": N_KEYS, "delta": 12},
    "G3": {"type": "ncw", "n_keys": N_KEYS, "kappa": 12,
           "max_syn_weight": None, "require_better_than_canonical": True},
}
PARAMETERS = {
    "P2": {"id": "P2_expanded", "r": 3001, "d": 37, "t": 66, "n0": 2},
    "P3": {"id": "P3_expanded", "r": 4001, "d": 41, "t": 82, "n0": 2},
}


def specs():
    base = {"type": "classic"}

    def off(vals):
        return {"algo": "bf_parallel", "threshold": {"type": "offset", "base": base, "offsets": vals},
                "max_iter": 20, "fixed_iters": False}

    return {
        "C0": off([0]),
        "FRO-1": off([1, 0]),
        "FRO-2": off([2, 0]),
        "FRO-3": off([3, 0]),
        "R2-2": off([0, 2, 0]),
        "UNIFORM-2": off([2]),
    }


def run_cell(param: dict, gid: str, decoder_name: str, decoder_spec: dict,
             out_dir: Path, errors_per_key: int) -> dict:
    """Run or load one (parameter, group, decoder) cell."""
    cell_path = out_dir / f"{param['id']}__{gid}__{decoder_name}.json"
    if cell_path.exists():
        return json.loads(cell_path.read_text(encoding="utf-8"))
    pool = KeyPool(MASTER_SEED, param, gid, GROUPS[gid])
    dec = build_decoder(decoder_name, decoder_spec, param["d"], param["t"], param["r"])
    failures = np.zeros(len(pool.keys), dtype=np.int64)
    it_sum = 0
    t0 = time.time()
    for ki, key in enumerate(pool.keys):
        gen = make_error_generator(MASTER_SEED, gid, key.key_id, param, GROUPS[gid], key,
                                   pool.ncws.get(key.key_id))
        for eid in range(errors_per_key):
            e = gen(eid)
            traj = dec(key, key.syndrome_from_global(e))
            it_sum += traj.n_iters_run
            if not traj.success:
                failures[ki] += 1
    n = len(pool.keys) * errors_per_key
    elapsed = time.time() - t0
    row = {
        "parameter": param, "group": gid, "decoder": decoder_name,
        "seed": MASTER_SEED, "n_keys": len(pool.keys),
        "errors_per_key": errors_per_key, "failures": int(failures.sum()),
        "trials": n, "dfr": float(failures.sum() / n),
        "upper95": float(wilson_upper(int(failures.sum()), n)),
        "per_key_failures": failures.tolist(), "avg_iters": float(it_sum / n),
        "seconds": round(elapsed, 3), "ms_per_decode": float(1000 * elapsed / n),
    }
    cell_path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    print(f"{param['id']} {gid:7s} {decoder_name:10s} {row['failures']}/{n} "
          f"DFR={row['dfr']:.3e} avg_it={row['avg_iters']:.2f} ({elapsed/60:.1f} min)", flush=True)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "expanded_data"))
    ap.add_argument("--errors", type=int, default=ERRORS_PER_KEY)
    ap.add_argument("--keys", type=int, default=N_KEYS)
    ap.add_argument("--parameter", choices=["P2", "P3", "both"], default="both")
    ap.add_argument("--group", choices=list(GROUPS), default=None,
                    help="run one key condition (used for parallel cell execution)")
    ap.add_argument("--focus", nargs="+", choices=list(specs()), default=None,
                    help="run only selected decoder schedules")
    args = ap.parse_args()
    if args.keys != N_KEYS:
        raise SystemExit("This pre-registered confirmation run fixes n_keys=50; do not override it.")
    if args.errors != ERRORS_PER_KEY:
        raise SystemExit("This pre-registered confirmation run fixes errors_per_key=1000; do not override it.")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "protocol": "expanded_confirmation_v1", "seed": MASTER_SEED,
        "n_keys_per_condition": N_KEYS, "errors_per_key": ERRORS_PER_KEY,
        "groups": GROUPS, "parameters": PARAMETERS, "decoders": list(specs()),
        "pairing": "identical deterministic (H,e,s) within each cell",
        "cluster_unit": "key", "seed_rule": "SHA256(master|context|index)",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (out / "preregistration.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    selected = PARAMETERS if args.parameter == "both" else {args.parameter: PARAMETERS[args.parameter]}
    groups = [args.group] if args.group else list(GROUPS)
    decoder_specs = specs()
    if args.focus:
        decoder_specs = {k: decoder_specs[k] for k in args.focus}
    results = {}
    for pname, param in selected.items():
        results[pname] = {}
        for gid in groups:
            results[pname][gid] = {}
            for name, dspec in decoder_specs.items():
                results[pname][gid][name] = run_cell(param, gid, name, dspec, out, args.errors)
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Completed expanded confirmation in {out}")


if __name__ == "__main__":
    main()
