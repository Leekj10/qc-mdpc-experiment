# -*- coding: utf-8 -*-
"""Export the exact formal-pool (H, e) instances for the C same-pool replication.

The binary format is read by runner.c:
  magic "QMD1"
  uint32 r, d, t, n_keys, errors_per_key
  for each key:  uint16 supp0[d], uint16 supp1[d]
  for each key:  errors_per_key x uint16 error positions[t]

Run from anywhere:
  python lw-vs/scripts/replication/export_instances.py --group G0 --keys 92 \
      --errors 3000 --out lw-vs/scripts/replication/instances/g0.bin
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "实验" / "qcmdpc-study"
sys.path.insert(0, str(STUDY))
from qcmdpc.generators import KeyPool, make_error_generator  # noqa: E402

PARAM = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
SEED = 20260901
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 100}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 100, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 100, "kappa": 12,
                    "max_syn_weight": None,
                    "require_better_than_canonical": True}, "fresh_from": 8},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=sorted(GROUPS))
    ap.add_argument("--keys", type=int, default=None,
                    help="number of formal keys (default: all after fresh_from)")
    ap.add_argument("--errors", type=int, default=3000)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    g = GROUPS[args.group]
    pool = KeyPool(SEED, PARAM, args.group, g["spec"])
    idxs = list(range(g["fresh_from"], len(pool.keys)))
    if args.keys is not None:
        idxs = idxs[: args.keys]
    r, d, t = PARAM["r"], PARAM["d"], PARAM["t"]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(b"QMD1")
        fh.write(struct.pack("<5I", r, d, t, len(idxs), args.errors))
        for ki in idxs:
            key = pool.keys[ki]
            for supp in (key.supp0, key.supp1):
                assert supp.size == d
                fh.write(np.asarray(supp, dtype="<u2").tobytes())
        for ki in idxs:
            key = pool.keys[ki]
            gen = make_error_generator(SEED, args.group, key.key_id, PARAM,
                                       g["spec"], key, pool.ncws.get(key.key_id))
            for eid in range(args.errors):
                e = gen(eid)
                pos = np.nonzero(e)[0]
                assert pos.size == t
                fh.write(np.asarray(pos, dtype="<u2").tobytes())
    print(f"wrote {out}: group={args.group} keys={len(idxs)} "
          f"errors/key={args.errors} r={r} d={d} t={t}")


if __name__ == "__main__":
    main()
