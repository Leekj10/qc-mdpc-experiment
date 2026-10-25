"""Extended interim gate run (strengthens the pre-formal evidence; does NOT
replace the reserved full-pool formal decision).

Design changes vs gate_h2_formal.py (documented here before execution):
- pools extended to 32/24/32 keys (frozen seed derivation => prefix-identical
  to all previous pools; keys >= 8/6/8 remain never used in any SEARCH;
  keys 8..19/6..14/8..19 were used in the interim gate only, and the frozen
  per-(key,error_id) generator makes the first 2500 errors identical, so this
  run is a strict sample-size extension plus brand-new keys >= 20/15/20);
- E_PER_KEY = 3000;
- output to results/gate_h2_extended (original run stays frozen).
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gate_h2_formal as base

base.OUT = "results/gate_h2_extended"
base.E_PER_KEY = 3000
base.GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 32}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 24, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 32, "kappa": 12, "max_syn_weight": None, "require_better_than_canonical": True}, "fresh_from": 8},
}

if __name__ == "__main__":
    base.main()
