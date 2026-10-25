"""Analysis of the revision arms (review_round1.md P0-1/P0-2). Parses run_log.txt,
computes failure rates, Wilson bounds, two-proportion z (Poisson-style conditional),
and archives a JSON summary."""
from __future__ import annotations

import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qcmdpc.stats import wilson_upper

LOG = "results/revision_arms/run_log.txt"
OUT = "results/revision_arms/analysis.json"


def parse():
    cells = {}
    for line in open(LOG, encoding="utf-8"):
        m = re.match(r"RESULT (\S+) \| (\d+) (.*) \| run_seconds=(\d+)", line.strip())
        if not m:
            continue
        name, total, dist, secs = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        fail = 0
        fm = re.search(r">(\d+):(\d+)", dist)
        if fm:
            fail = int(fm.group(2))
        # sanity: distribution counts must sum to total - failures
        counts = [int(x) for x in re.findall(r"(?:^|\s)\d+:(\d+)", " " + dist.split(">")[0])]
        cells[name] = {"trials": total, "failures": fail, "dfr": fail / total,
                       "upper95": wilson_upper(fail, total), "seconds": secs,
                       "dist_sum_check": sum(counts) + fail == total}
    return cells


def two_prop_z(f1, n1, f2, n2):
    pooled = (f1 + f2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    return (f1 / n1 - f2 / n2) / se if se > 0 else float("nan")


def main():
    cells = parse()
    out = {"cells": cells, "comparisons": {}}
    for cond in ["RAND", "WEAK12", "NCW12"]:
        a, b = cells.get(f"classic_o0_{cond}"), cells.get(f"classic_o2_{cond}")
        if a and b:
            z = two_prop_z(a["failures"], a["trials"], b["failures"], b["trials"])
            out["comparisons"][f"FRO2_vs_base_dynamic_{cond}"] = {
                "base_dfr": a["dfr"], "fro2_dfr": b["dfr"],
                "ratio": a["dfr"] / b["dfr"] if b["dfr"] else float("inf"),
                "z": z, "significant_0.05": abs(z) > 1.96}
        bf = cells.get(f"backflip_{cond}")
        if bf and a:
            out["comparisons"][f"backflip_vs_base_dynamic_{cond}"] = {
                "base_dfr": a["dfr"], "backflip_dfr": bf["dfr"],
                "backflip_upper95": bf["upper95"],
                "note": "backflip zero failures => bound only"}
    checks = {k: v["dist_sum_check"] for k, v in cells.items()}
    out["dist_sum_checks_all_ok"] = all(checks.values())
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    for k, v in cells.items():
        print(f"{k:26s} {v['failures']:5d}/{v['trials']} dfr={v['dfr']:.3e} U95={v['upper95']:.3e} sum_ok={v['dist_sum_check']}")
    print()
    for k, v in out["comparisons"].items():
        print(k, json.dumps(v))
    print("saved ->", OUT)


if __name__ == "__main__":
    main()
