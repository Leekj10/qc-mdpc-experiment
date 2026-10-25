#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Near-codeword-aware bit-flipping (Baldelli et al. 2026), fair matched comparison.

Motivation
----------
The audit asks for a fair modern baseline beyond BGF: specifically a layered or
near-codeword-aware method, compared on identical instances with C0 and FRO-2. The
paper's boundary section argues that error-floor/capture-recovery methods "address a
different failure mechanism" but has never tested that claim against an actual decoder.

What is implemented
-------------------
Algorithm 2 of "Near-Codewords Aware Bit Flipping Decoding of QC-MDPC Codes"
(Baldelli, Baldi, De Zuane, Santini; ISIT 2026), transcribed here:

    while s != 0 and Iter < IterMax:
        counters <- UPC(s);  J <- {i : counter_i >= threshold}
        for i in J:  e_hat_i ^= 1;  s ^= h_i
        if wt(s) == d:                       # a near-codeword syndrome has weight v
            if s matches a stored near-codeword syndrome at shift i:
                e_hat ^= m_i;  return e_hat
        Iter += 1

The look-up table of near-codeword syndromes is exactly `key.canonical_syndromes()`
shifted: syndrome(rot(h0,a), 0) = roll(s0, a) and syndrome(0, rot(h1,b)) = roll(s1, b),
which the project already provides and documents as shift-covariant.

Two things must be stated plainly:

  * The threshold rule is the CLASSIC one, matched to C0 and BGF-C3, so the only
    difference from C0 is the near-codeword recovery step. This is our transcription of a
    published algorithm, not the authors' code.
  * The method returns SUCCESS whenever the syndrome matches a near-codeword, because the
    syndrome then does become zero. The corrected estimate is the true error *plus* a
    near-codeword, so this is a deliberate zero-syndrome acceptance that need not be an
    exact recovery. We therefore report both zero-syndrome success and exact recovery;
    the gap between them is a concrete demonstration of why the study audits recovery
    separately rather than trusting the syndrome.

Run:  python lw-vs/scripts/exp_ncw_aware.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
OUT = ROOT / "lw-vs" / "results" / "ncw_aware"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder, make_threshold      # noqa: E402
from qcmdpc.generators import (KeyPool, make_error_generator,   # noqa: E402
                               _child_seed, ncw_pressure_error,
                               uniform_fixed_weight)
from qcmdpc.stats import wilson_upper, cluster_bootstrap_paired, sign_test_paired  # noqa: E402

SEED = 20260901
PARAM = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
E_PER_KEY = 3000
MAX_ITER = 20
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 100}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 100, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 100, "kappa": 12, "max_syn_weight": None,
                    "require_better_than_canonical": True}, "fresh_from": 8},
}
COND = {"G0": "RAND", "G2_d12": "TYPE-I", "G3": "NCW-shallow"}
EXPECTED = {"G0": 282, "G2_d12": 372, "G3": 141}      # archived C0 totals (gate)
N_WORKERS = int(os.environ.get("NCW_WORKERS", "10"))


# --------------------------------------------------------------------------
# the decoder
# --------------------------------------------------------------------------
def _cyclic_gaps(v: np.ndarray) -> np.ndarray | None:
    """Gaps between consecutive support elements, cyclically. None if v is zero."""
    idx = np.nonzero(v)[0]
    if idx.size == 0:
        return None
    return np.diff(np.concatenate([idx, idx[:1] + v.size]))


def build_ncw_table(key):
    """The two canonical near-codeword syndrome families: syndromes of (h0,0) and (0,h1),
    together with their supports and cyclic gap sequences, precomputed once per key."""
    s0, s1 = key.canonical_syndromes()
    out = {}
    for tag, base in (("a", s0), ("b", s1)):
        idx = np.nonzero(base)[0]
        out[tag] = {"base": base, "supp": idx, "gaps": _cyclic_gaps(base)}
    return out


def _match_near_codeword(key, s, tab):
    """Return (tag, shift) if s is a near-codeword syndrome, else None.

    Two cyclic binary vectors are shifts of one another iff their cyclic gap sequences
    are rotations of one another; the rotation index k then gives the shift from the
    first support positions. Note that rotating "first 1 to position 0" is NOT a valid
    canonical form here -- it is not shift-invariant -- which is why the gap rotation is
    compared explicitly. A final array_equal confirms the match, so the routine cannot
    return a false positive.
    """
    if int(s.sum()) != key.d:
        return None
    gs = _cyclic_gaps(s)
    if gs is None:
        return None
    b0 = int(np.nonzero(s)[0][0])
    for tag, rec in tab.items():
        gb, A = rec["gaps"], rec["supp"]
        if gb.size != gs.size:
            continue
        d = gb.size
        for k in range(d):
            if np.array_equal(np.roll(gb, k), gs):
                # np.roll(x,k)[i] = x[(i-k) mod d], so gap gs[0] is gb[d-k] and B[0]
                # aligns with A[(d-k) mod d]; the array_equal below is the guard.
                a = int((b0 - int(A[(d - k) % d])) % key.r)
                if np.array_equal(np.roll(rec["base"], a), s):
                    return tag, a
                break
    return None


def _ncw_support(key, tag, shift):
    """Support of m_i: rot(h0, a) in block 0, or rot(h1, b) in block 1."""
    m = np.zeros(key.n, dtype=np.uint8)
    if tag == "a":
        m[:key.r] = np.roll(key.h0, shift)
    else:
        m[key.r:] = np.roll(key.h1, shift)
    return m


def bf_ncw_aware(key, s0, thr, max_iter, table, record_flips=False,
                 track_estimate=False):
    """Algorithm 2, with the CLASSIC threshold; returns (success, estimate, iters, used_ncw)."""
    s = s0.copy()
    est = np.zeros(key.n, dtype=np.uint8) if track_estimate else None
    it = 0
    used = False
    while s.sum() != 0 and it < max_iter:
        it += 1
        alpha = key.upc_fast(s)
        th = thr(it - 1, int(s.sum()))
        flips = np.nonzero(alpha >= th)[0]
        for p in flips:
            s = key.flip(s, int(p))
        if est is not None and flips.size:
            est[flips] ^= 1
        if int(s.sum()) == key.d:
            hit = _match_near_codeword(key, s, table)
            if hit is not None:
                m = _ncw_support(key, hit[0], hit[1])
                nz = np.nonzero(m)[0]
                for p in nz:
                    s = key.flip(s, int(p))
                if est is not None and nz.size:
                    est[nz] ^= 1
                used = True
                break
    return int(s.sum()) == 0, est, it, used


def _work(job):
    gid, ki, e_per_key = job
    g = GROUPS[gid]
    pool = KeyPool(SEED, PARAM, gid, g["spec"])
    key = pool.keys[ki]
    gen = make_error_generator(SEED, gid, key.key_id, PARAM, g["spec"], key,
                               pool.ncws.get(key.key_id))
    thr = make_threshold({"type": "classic"}, PARAM["d"], PARAM["t"], 2 * PARAM["r"])
    table = build_ncw_table(key)
    c0 = build_decoder("C0", {"algo": "bf_parallel",
                              "threshold": {"type": "classic"},
                              "max_iter": MAX_ITER}, PARAM["d"], PARAM["t"], PARAM["r"])
    zs = ex = c0_fail = c0_ex = ncw_used = 0
    it_sum = 0
    for eid in range(e_per_key):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        tr0 = c0(key, s.copy(), track_estimate=True)
        c0_fail += int(not tr0.success)
        c0_ex += int(tr0.estimated_error is not None
                     and not np.array_equal(tr0.estimated_error, e))
        ok, est, it, used = bf_ncw_aware(key, s, thr, MAX_ITER, table,
                                         track_estimate=True)
        it_sum += it
        ncw_used += int(used)
        zs += int(ok)
        ex += int(not np.array_equal(est, e))       # exact-recovery FAILURES
    return gid, ki, zs, ex, c0_fail, c0_ex, ncw_used, it_sum



# --------------------------------------------------------------------------
# phase 2: the capture-prone conditions, where this decoder is designed to help
# --------------------------------------------------------------------------
CAP_PARAM = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
CAP_SEED = 20260901
CAP_K = 20
CAP_E = 2000
CAP_KAPPAS = [12, 46, 60]
CAP_SPEC = {"type": "ncw", "n_keys": CAP_K, "kappa": CAP_KAPPAS[0],
            "max_syn_weight": None, "require_better_than_canonical": True}
CAP_N = 2 * CAP_PARAM["r"]


def _work_capture(job):
    """One key of the fixed batch, one construction: C0 and NCW-aware paired."""
    cons, ki = job
    kappa = 0 if cons == "rand" else int(cons[1:])
    pool = KeyPool(CAP_SEED, CAP_PARAM, "Gcap", CAP_SPEC)
    key = pool.keys[ki]
    ncw = pool.ncws.get(key.key_id)
    thr = make_threshold({"type": "classic"}, CAP_PARAM["d"], CAP_PARAM["t"], CAP_N)
    table = build_ncw_table(key)
    c0 = build_decoder("C0", {"algo": "bf_parallel",
                              "threshold": {"type": "classic"},
                              "max_iter": MAX_ITER},
                       CAP_PARAM["d"], CAP_PARAM["t"], CAP_PARAM["r"])
    c0_fail = zs = ex = c0_ex = used = 0
    for eid in range(CAP_E):
        rng = np.random.default_rng(_child_seed(CAP_SEED, f"err|Gcap|{cons}|{key.key_id}", eid))
        e = (uniform_fixed_weight(rng, CAP_N, CAP_PARAM["t"]) if cons == "rand"
             else ncw_pressure_error(rng, key, ncw, CAP_PARAM["t"], kappa))
        s = key.syndrome_from_global(e)
        t0 = c0(key, s.copy(), track_estimate=True)
        c0_fail += int(not t0.success)
        c0_ex += int(not np.array_equal(t0.estimated_error, e))
        ok, est, _, u = bf_ncw_aware(key, s, thr, MAX_ITER, table, track_estimate=True)
        zs += int(ok); ex += int(not np.array_equal(est, e)); used += int(u)
    return cons, ki, c0_fail, c0_ex, zs, ex, used


def run_capture(report) -> bool:
    print("\n[phase 2] capture-prone conditions (fixed ncw-admissible batch, "
          f"{CAP_K} keys x {CAP_E} errors)")
    pool = KeyPool(CAP_SEED, CAP_PARAM, "Gcap", CAP_SPEC)
    report["capture"] = {
        "batch": "ONE fixed ncw-admissible key batch; only the error construction varies",
        "kappas": CAP_KAPPAS, "n_keys": CAP_K, "errors_per_key": CAP_E,
        "note": "kappa>d is a genuine capture condition; absolute DFR is conditional on "
                "this ncw-admissible batch, within-batch contrasts are de-confounded",
        "cells": {}}
    ncw_fired_any = 0
    for cons in ["rand"] + [f"k{k}" for k in CAP_KAPPAS]:
        jobs = [(cons, ki) for ki in range(len(pool.keys))]
        res = list(ProcessPoolExecutor(max_workers=N_WORKERS).map(_work_capture, jobs))
        n_dec = len(jobs) * CAP_E
        c0f = sum(r[2] for r in res); c0e = sum(r[3] for r in res)
        zs = sum(r[4] for r in res); ex = sum(r[5] for r in res)
        used = sum(r[6] for r in res)
        ncw_fired_any += used
        kappa = 0 if cons == "rand" else int(cons[1:])
        report["capture"]["cells"][cons] = {
            "kappa": kappa, "trials": n_dec,
            "c0_failures": c0f, "c0_dfr": c0f / n_dec,
            "c0_exact_recovery_failures": c0e,
            "ncw_zero_syndrome": zs, "ncw_zero_syndrome_dfr": zs / n_dec,
            "ncw_exact_recovery_failures": ex, "ncw_exact_recovery_dfr": ex / n_dec,
            "ncw_triggered": used, "ncw_trigger_rate": used / n_dec,
            "ncw_upper95_zero_syndrome": wilson_upper(zs, n_dec),
        }
        print(f"  kappa={kappa:3d}: C0 fails {c0f:6d}/{n_dec} ({100*c0f/n_dec:6.2f}%)  |  "
              f"NCW-aware zero-syndrome {zs:6d} ({100*zs/n_dec:6.2f}%)  "
              f"exact-recovery fails {ex:6d}  step-fired {used:5d}", flush=True)
    if ncw_fired_any == 0:
        print("  !! the near-codeword step never fired in any capture condition")
    return True


def main() -> int:
    started = time.time()
    print(f"NCW-aware (Algorithm 2, CLASSIC threshold) at P1' "
          f"{PARAM['r']},{PARAM['d']},{PARAM['t']}; {E_PER_KEY} errors/key; "
          f"workers={N_WORKERS}\n")
    report = {"param": PARAM, "seed": SEED, "errors_per_key": E_PER_KEY,
              "max_iter": MAX_ITER,
              "algorithm": "Baldelli et al. 2026 (ISIT), Algorithm 2, transcribed; "
                           "threshold = CLASSIC, matched to C0 and BGF-C3",
              "near_codeword_table": "key.canonical_syndromes() shifts; 2r entries",
              "note": "reports zero-syndrome success AND exact-recovery failures "
                      "separately, because near-codeword acceptance need not recover e",
              "groups": {}}
    gate_ok = True
    for gid in GROUPS:
        g = GROUPS[gid]
        pool = KeyPool(SEED, PARAM, gid, g["spec"])
        idxs = list(range(g["fresh_from"], len(pool.keys)))
        res = list(ProcessPoolExecutor(max_workers=N_WORKERS).map(
            _work, [(gid, ki, E_PER_KEY) for ki in idxs]))
        n_keys, n_dec = len(idxs), len(idxs) * E_PER_KEY
        zs = sum(r[2] for r in res)
        ex = sum(r[3] for r in res)
        c0f = sum(r[4] for r in res)
        c0e = sum(r[5] for r in res)
        used = sum(r[6] for r in res)
        its = sum(r[7] for r in res) / n_dec
        gate_ok &= (c0f == EXPECTED[gid])
        cell = {
            "condition": COND[gid], "n_keys": n_keys, "trials": n_dec,
            "c0_failures": c0f, "c0_archived": EXPECTED[gid],
            "c0_exact_recovery_failures": c0e,
            "ncw_zero_syndrome": zs, "ncw_zero_syndrome_dfr": zs / n_dec,
            "ncw_exact_recovery_failures": ex,
            "ncw_exact_recovery_dfr": ex / n_dec,
            "ncw_miscorrections": zs - (n_dec - ex),
            "ncw_triggered": used, "ncw_trigger_rate": used / n_dec,
            "ncw_avg_iters": its,
            "ncw_upper95_zero_syndrome": wilson_upper(zs, n_dec),
            "ncw_upper95_exact_recovery": wilson_upper(ex, n_dec),
        }
        report["groups"][gid] = cell
        print(f"  [{COND[gid]:12s}] C0 fails {c0f:4d} (archive {EXPECTED[gid]:4d}) "
              f"{'OK' if c0f==EXPECTED[gid] else '*** MISMATCH ***'}")
        print(f"     NCW-aware: zero-syndrome {zs:4d}/{n_dec} ({100*zs/n_dec:.3f}%)  "
              f"exact-recovery failures {ex:4d} ({100*ex/n_dec:.3f}%)  "
              f"miscorrections {zs - (n_dec-ex):4d}")
        print(f"     near-codeword step fired {used:5d}/{n_dec} "
              f"({100*used/n_dec:.3f}%), mean iters {its:.3f}", flush=True)

    run_capture(report)
    report["gate_passed"] = gate_ok
    report["wall_seconds"] = round(time.time() - started, 1)
    with open(OUT / "report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print(f"\nreproducibility gate: {'PASS' if gate_ok else 'FAIL'}")
    print(f"[done] {OUT / 'report.json'} ({report['wall_seconds']:.0f} s)")
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
