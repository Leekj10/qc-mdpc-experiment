"""Analyze supplemental matrices with key-cluster bootstrap intervals."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np


def rr_boot(base: np.ndarray, trt: np.ndarray, n_err: int, seed: int = 20260911, B: int = 10000):
    rng = np.random.default_rng(seed)
    n = len(base)
    point = (base.sum() + (0.5 if trt.sum() == 0 else 0.0)) / (trt.sum() + (0.5 if trt.sum() == 0 else 0.0))
    idx = rng.integers(0, n, size=(B, n))
    b = base[idx].sum(axis=1).astype(float)
    t = trt[idx].sum(axis=1).astype(float)
    ok = t > 0
    vals = (b[ok] / t[ok])
    if vals.size < B // 2:
        return {"point_rr": float(point), "ci95": [None, None], "finite_bootstrap": int(vals.size), "note": "sparse treatment failures; interval unresolved"}
    return {"point_rr": float(point), "ci95": [float(np.quantile(vals, .025)), float(np.quantile(vals, .975))],
            "finite_bootstrap": int(vals.size), "note": "key-cluster percentile bootstrap"}


def analyze(path: Path):
    obj = json.loads((path / "matrix.json").read_text(encoding="utf-8"))
    nerr = obj["errors_per_key"]
    decs = obj["decoders"]
    out = {"label": obj["label"], "parameter": obj["parameter"], "errors_per_key": nerr,
           "groups": {}, "method": {"bootstrap": 10000, "unit": "key", "seed": 20260911}}
    for gid, g in obj["matrix"].items():
        d = g["decoders"]
        base = np.array(d["C0"]["per_key_failures"], dtype=float)
        out["groups"][gid] = {"pooled": {name: {"failures": d[name]["failures"], "trials": d[name]["trials"],
                                                   "dfr": d[name]["dfr"], "upper95": d[name]["upper95"],
                                                   "avg_iters": d[name]["avg_iters"], "ms_per_decode": d[name]["ms_per_decode"]}
                                          for name in decs},
                               "risk_ratios_vs_C0": {}}
        for name in decs:
            if name == "C0":
                continue
            trt = np.array(d[name]["per_key_failures"], dtype=float)
            stable = sum((i + 1) * ord(ch) for i, ch in enumerate(f"{obj['label']}|{gid}|{name}"))
            out["groups"][gid]["risk_ratios_vs_C0"][name] = rr_boot(base, trt, nerr,
                                                                        seed=20260911 + stable % 100000)
        finite = {name: d[name]["dfr"] for name in decs}
        out["groups"][gid]["best_nonuniform"] = min((k for k in decs if k != "UNIFORM-2"), key=lambda k: finite[k])
    (path / "analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def main():
    root = Path(__file__).resolve().parent / "supplemental_data_full"
    allout = {"p2": analyze(root / "p2_temporal_ablation"), "p3": analyze(root / "p3_third_point")}
    (root / "supplemental_analysis.json").write_text(json.dumps(allout, indent=2), encoding="utf-8")
    for label, x in allout.items():
        print(label, x["parameter"])
        for gid, g in x["groups"].items():
            print(gid, "best=", g["best_nonuniform"], "RR", {k: v["point_rr"] for k,v in g["risk_ratios_vs_C0"].items()})


if __name__ == "__main__":
    main()
