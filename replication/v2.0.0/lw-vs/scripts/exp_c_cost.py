#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Deployment-level cost of the first-round offset, measured in the C reference.

Motivation (project audit W5)
-----------------------------
The study reports Python-reference costs only, and the audit asks for a compiled
implementation's numbers: UPC passes, mean/P99 iterations, wall-clock and memory, with
the Python prototype clearly distinguished from the deployment path.

What this measures, and what it must NOT be read as
---------------------------------------------------
The C reference (vvasseur/qcmdpc_decoder, GRAY_BGF / CLASSIC, built with the study's
FIRST_ROUND_OFFSET research patch) uses the **dynamic-distance threshold semantics** of
the reference implementation, where the threshold may consult the current distance to the
true error. That is simulation-privileged and is NOT the static target-weight semantics of
the main experiment. Therefore:

  * its DFR is reported only as a consistency check and is NOT comparable to the paper's
    static results;
  * only the RELATIVE cost between builds that share identical semantics (C0 vs FRO-2,
    both dynamic) is interpreted, and it is interpreted as an iteration/UPC cost, not as
    a deployment DFR claim.

Timing protocol: single-threaded (-T 1), R repetitions per build, minimum wall time
reported (robust to machine load), same 20-iteration budget as the paper.

Run:  python lw-vs/scripts/exp_c_cost.py
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "lw-vs" / "results" / "c_cost"
OUT = BIN
ROUNDS = int(os.environ.get("C_ROUNDS", "500000"))
REPS = int(os.environ.get("C_REPS", "5"))
MAX_ITER = 20

BUILDS = {
    "C0": {"exe": "c0_p1p.exe",
           "note": "CLASSIC, dynamic-distance semantics, no offset"},
    "FRO-2": {"exe": "fro2_p1p.exe",
              "note": "CLASSIC + FIRST_ROUND_OFFSET=2 (round 1 only), dynamic semantics"},
    "BGF": {"exe": "bgf_p1p.exe",
            "note": "GRAY_BGF with published affine constants (c0=13.53, c1=0.0069722); "
                    "these are BIKE Level-1 values and are mis-scaled for (4801,45) -- "
                    "cost only, not a quality comparison"},
}


def parse(out: str) -> dict:
    """Parse `<total> <iter>:<count> ... ><max_iter>:<failures>`."""
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    body = next((l for l in reversed(lines) if not l.startswith("-D")), "")
    toks = body.split()
    total = int(toks[0])
    hist: dict[int, int] = {}
    overflow = 0
    for t in toks[1:]:
        m = re.match(r"^>?(\d+):(\d+)$", t)
        if not m:
            continue
        it, cnt = int(m.group(1)), int(m.group(2))
        if t.startswith(">"):
            overflow = cnt
        else:
            hist[it] = cnt
    return {"total": total, "hist": hist, "overflow": overflow}


def stats(hist: dict[int, int], total: int, overflow: int,
          max_iter: int = MAX_ITER) -> dict:
    """Iteration distribution: mean, median, P95, P99 over all decodes.

    Decodes that exhaust the budget are bucketed at max_iter+1 so that a build which
    fails on a large fraction of samples still yields well-defined percentiles; a
    percentile landing in that bucket is flagged, because it means "at least max_iter".
    """
    h = dict(hist)
    if overflow:
        h[max_iter + 1] = h.get(max_iter + 1, 0) + overflow
    n = sum(h.values())
    if n == 0:
        return {}
    cum, pcts, truncated = 0, {}, {}
    for it in sorted(h):
        cum += h[it]
        for p in (50, 95, 99):
            if p not in pcts and cum >= p / 100.0 * n:
                pcts[p] = it
                truncated[p] = it > max_iter
    mean = sum(it * c for it, c in h.items()) / n
    return {"decodes": n, "mean_iters": mean,
            "p50_iters": pcts.get(50), "p95_iters": pcts.get(95),
            "p99_iters": pcts.get(99),
            "p99_is_at_least_budget": bool(truncated.get(99)),
            "mean_iters_capped_at_budget": mean,
            "over_max_iter": overflow,
            "dfr_dynamic_semantics": overflow / n}


def main() -> int:
    print(f"C reference cost run: {ROUNDS:,} decodes x {REPS} reps, -T 1, -i {MAX_ITER}")
    print(f"binaries: {BIN}\n")
    report = {"protocol": {"rounds_per_rep": ROUNDS, "repetitions": REPS,
                           "threads": 1, "max_iter": MAX_ITER,
                           "timing": "minimum wall time over repetitions",
                           "semantics": "C reference dynamic-distance (simulation-privileged); "
                                        "DFR not comparable to the static main experiment",
                           "build": {"target": "x86_64-windows-gnu", "opt": "-O2",
                                     "compiler": "zig cc (ziglang)",
                                     "avx": "disabled"},
                           "parameter": {"r": 4801, "d": 45, "t": 92, "index": 2}},
              "builds": {}}
    for name, spec in BUILDS.items():
        exe = BIN / spec["exe"]
        if not exe.exists():
            print(f"  !! {exe.name} missing -- build it first (see reference/BUILD_WINDOWS.md)")
            return 1
        times, parsed = [], None
        for _ in range(REPS):
            t0 = time.perf_counter()
            p = subprocess.run([str(exe), "-T", "1", "-N", str(ROUNDS), "-i", str(MAX_ITER),
                                "-q"], capture_output=True, text=True)
            times.append(time.perf_counter() - t0)
            parsed = parse(p.stdout)
        st = stats(parsed["hist"], parsed["total"], parsed["overflow"])
        best = min(times)
        st["best_wall_seconds"] = round(best, 3)
        st["decodes_per_second"] = round(ROUNDS / best, 1)
        st["wall_seconds_per_rep"] = [round(x, 2) for x in times]
        st["max_iter_reached_fraction"] = round(st["over_max_iter"] / st["decodes"], 6)
        report["builds"][name] = {"note": spec["note"], **st}
        print(f"  {name:6s} {st['decodes_per_second']:8.0f} dec/s  "
              f"mean_iters={st['mean_iters']:.3f}  p99={st['p99_iters']}  "
              f"over-budget={st['over_max_iter']}/{st['decodes']} "
              f"({100*st['max_iter_reached_fraction']:.3f}%)")

    # relative cost of the intervention under identical semantics
    c0, f2 = report["builds"].get("C0"), report["builds"].get("FRO-2")
    if c0 and f2:
        rel = {
            "iteration_cost_ratio": f2["mean_iters"] / c0["mean_iters"],
            "wall_cost_ratio": f2["best_wall_seconds"] / c0["best_wall_seconds"],
            "throughput_ratio": c0["decodes_per_second"] / f2["decodes_per_second"],
            "p99_iteration_delta": (f2["p99_iters"] or 0) - (c0["p99_iters"] or 0),
        }
        report["relative_cost_FRO2_over_C0"] = rel
        print(f"\n  FRO-2 / C0: iterations x{rel['iteration_cost_ratio']:.3f}  "
              f"wall x{rel['wall_cost_ratio']:.3f}  "
              f"throughput x{rel['throughput_ratio']:.3f}")
        print("  (same dynamic-distance semantics for both builds; relative cost only)")

    with open(OUT / "c_cost_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print(f"\n[done] {OUT / 'c_cost_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
