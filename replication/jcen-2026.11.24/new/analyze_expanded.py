"""Aggregate expanded confirmation cells with key-cluster bootstrap intervals."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent / "expanded_data"

def rr_boot(base, trt, B=10000, seed=20260912):
    base = np.asarray(base, float); trt = np.asarray(trt, float)
    rng = np.random.default_rng(seed); n = len(base)
    point = base.sum() / trt.sum() if trt.sum() else (base.sum()+.5)/.5
    idx = rng.integers(0, n, size=(B, n))
    den = trt[idx].sum(axis=1); num = base[idx].sum(axis=1)
    vals = num[den > 0] / den[den > 0]
    return {"point_rr": float(point), "ci95": [float(np.quantile(vals,.025)), float(np.quantile(vals,.975))],
            "finite_bootstrap": int(vals.size)}

def main():
    cells = {}
    for p in ROOT.glob("P*_expanded__*.json"):
        x = json.loads(p.read_text(encoding="utf-8"))
        cells.setdefault(x["parameter"]["id"], {}).setdefault(x["group"], {})[x["decoder"]] = x
    summary = {"protocol": json.loads((ROOT/"preregistration.json").read_text(encoding="utf-8")), "cells": {}}
    lines = ["parameter,group,decoder,failures,trials,dfr,upper95,avg_iters,rr_vs_c0,rr_lo,rr_hi"]
    for param, groups in sorted(cells.items()):
        summary["cells"][param] = {}
        for gid, decs in sorted(groups.items()):
            summary["cells"][param][gid] = {}
            base = decs.get("C0")
            for name, x in sorted(decs.items()):
                row = {k:x[k] for k in ("failures","trials","dfr","upper95","avg_iters","ms_per_decode")}
                if name != "C0" and base:
                    rr = rr_boot(base["per_key_failures"], x["per_key_failures"], seed=20260912 + sum(map(ord,param+gid+name)))
                    row["rr_vs_c0"] = rr
                    lines.append(f"{param},{gid},{name},{x['failures']},{x['trials']},{x['dfr']:.8g},{x['upper95']:.8g},{x['avg_iters']:.5g},{rr['point_rr']:.6g},{rr['ci95'][0]:.6g},{rr['ci95'][1]:.6g}")
                else:
                    row["rr_vs_c0"] = None
                    lines.append(f"{param},{gid},{name},{x['failures']},{x['trials']},{x['dfr']:.8g},{x['upper95']:.8g},{x['avg_iters']:.5g},,,")
                summary["cells"][param][gid][name] = row
    (ROOT/"expanded_analysis.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (ROOT/"expanded_summary.csv").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Aggregated {sum(len(d) for g in cells.values() for d in g.values())} cells")

if __name__ == "__main__": main()
