"""Quick peek at prescreen summaries."""
import json, glob, os, sys

run = sys.argv[1] if len(sys.argv) > 1 else "results/m1_p1_prescreen"
for p in sorted(glob.glob(os.path.join(run, "*", "summary_*.json"))):
    s = json.load(open(p, encoding="utf-8"))
    g = os.path.basename(os.path.dirname(p))
    span = s.get("p90_minus_p10_log10")
    span_txt = f"{span:.2f}" if span is not None else "n/a(<10 nz keys)"
    print(
        f"{g:8s} {s['decoder']:8s} DFR={s['overall_dfr']:.3e} "
        f"zero={s['keys_zero_failures']}/{s['n_keys']} iters={s['avg_iters_run']:.2f} "
        f"span_log10={span_txt} modes={s['failure_modes']}"
    )
