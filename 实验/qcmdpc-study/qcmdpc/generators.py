"""Key and error generators with structural self-validation (pre-registered).

Seed discipline (frozen): every object is derived from
    SHA-256(master_seed || context || index)
so key pools and error pools are exactly reproducible.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from .ring import QCKey


def _child_seed(master_seed: int, context: str, index: int) -> int:
    h = hashlib.sha256(f"{master_seed}|{context}|{index}".encode()).digest()
    return int.from_bytes(h[:8], "big")


# --------------------------------------------------------------------- keys
def random_key(rng: np.random.Generator, r: int, d: int, key_id: str = "") -> QCKey:
    supp = rng.choice(r, size=d, replace=False)
    h0 = np.zeros(r, dtype=np.uint8)
    h0[supp] = 1
    supp = rng.choice(r, size=d, replace=False)
    h1 = np.zeros(r, dtype=np.uint8)
    h1[supp] = 1
    return QCKey(h0, h1, key_id)


def type1_key(rng: np.random.Generator, r: int, d: int, delta: int, key_id: str = "") -> QCKey:
    """Type-I weak key: h0 contains a run of delta consecutive ones.

    Construction: run starts at a random position in h0; the remaining d-delta
    ones of h0 are placed uniformly outside the run; h1 stays fully random.
    Structural check: max cyclic run of h0 >= delta (verified by caller).
    """
    assert delta <= d
    start = int(rng.integers(0, r))
    run = np.array([(start + j) % r for j in range(delta)], dtype=np.int64)
    free = np.setdiff1d(np.arange(r), run)
    extra = rng.choice(free, size=d - delta, replace=False) if d > delta else np.array([], dtype=np.int64)
    h0 = np.zeros(r, dtype=np.uint8)
    h0[np.concatenate([run, extra])] = 1
    supp = rng.choice(r, size=d, replace=False)
    h1 = np.zeros(r, dtype=np.uint8)
    h1[supp] = 1
    return QCKey(h0, h1, key_id)


@dataclass
class NearCodeword:
    shift_a: int
    shift_b: int
    support: np.ndarray  # global support of the (d,d) near-codeword (weight 2d)
    syn_weight: int


def find_near_codeword(
    key: QCKey, max_syn_weight: int | None = None, require_better_than_canonical: bool = True
) -> NearCodeword | None:
    """Search (rot(h0,a), rot(h1,b)) pairs of minimal syndrome weight.

    Uses shift-covariance: syn(a,b) = roll(s0, a) XOR roll(s1, b), with a fixed
    to 0 and b fully scanned. The BEST pair found is returned (its actual
    syndrome weight is recorded in the structure report); optional filters:
    - max_syn_weight: absolute cap (config may set null = no cap)
    - require_better_than_canonical: min weight must beat (h0, h1) itself.
    """
    s0, s1 = key.canonical_syndromes()
    canonical_w = int(np.bitwise_xor(s0, s1).sum())
    r = key.r
    best_b, best_w = 0, canonical_w
    for b in range(r):
        w = int(np.bitwise_xor(s0, np.roll(s1, b)).sum())
        if w < best_w:
            best_b, best_w = b, w
    if require_better_than_canonical and best_w >= canonical_w:
        return None
    if max_syn_weight is not None and best_w > max_syn_weight:
        return None
    supp0 = (key.supp0 + 0) % r
    supp1 = (key.supp1 + best_b) % r + r
    return NearCodeword(0, best_b, np.sort(np.concatenate([supp0, supp1])), best_w)


# --------------------------------------------------------------------- errors
def uniform_fixed_weight(rng: np.random.Generator, n: int, t: int) -> np.ndarray:
    e = np.zeros(n, dtype=np.uint8)
    e[rng.choice(n, size=t, replace=False)] = 1
    return e


def ncw_pressure_error(
    rng: np.random.Generator, key: QCKey, ncw: NearCodeword, t: int, kappa: int
) -> np.ndarray:
    """G3 error: exactly kappa positions inside the near-codeword support,
    t-kappa uniform positions outside it (pre-registered G3 construction)."""
    assert kappa <= min(t, ncw.support.size)
    in_pos = rng.choice(ncw.support, size=kappa, replace=False)
    outside = np.setdiff1d(np.arange(key.n), ncw.support)
    other = rng.choice(outside, size=t - kappa, replace=False)
    e = np.zeros(key.n, dtype=np.uint8)
    e[np.concatenate([in_pos, other])] = 1
    return e


# --------------------------------------------------------------------- pools
class KeyPool:
    """Deterministic key pool for one condition group."""

    def __init__(self, master_seed: int, param: dict, group_id: str, group_spec: dict):
        self.master_seed = master_seed
        self.param = param
        self.group_id = group_id
        self.spec = group_spec
        self.r, self.d, self.t = param["r"], param["d"], param["t"]
        self.keys: list[QCKey] = []
        self.ncws: dict[str, NearCodeword | None] = {}
        self.reports: list[dict] = []
        self._build()

    def _build(self):
        n_keys = self.spec["n_keys"]
        gtype = self.spec["type"]
        built = 0
        attempts = 0
        max_attempts = n_keys * 20
        while built < n_keys and attempts < max_attempts:
            rng = np.random.default_rng(_child_seed(self.master_seed, f"key|{self.group_id}", attempts))
            kid = f"{self.group_id}-{built:04d}"
            if gtype == "random":
                key = random_key(rng, self.r, self.d, kid)
                ok = True
            elif gtype == "type1":
                delta = self.spec["delta"]
                key = type1_key(rng, self.r, self.d, delta, kid)
                ok = int(key.structure_report()["max_run_h0"]) >= delta  # structural validation
            elif gtype == "ncw":
                key = random_key(rng, self.r, self.d, kid)
                ncw = find_near_codeword(
                    key,
                    max_syn_weight=self.spec.get("max_syn_weight"),
                    require_better_than_canonical=self.spec.get("require_better_than_canonical", True),
                )
                ok = ncw is not None  # reject keys without a usable near-codeword
                if ok:
                    self.ncws[kid] = ncw
            else:
                raise ValueError(f"unknown group type {gtype}")
            attempts += 1
            if not ok:
                continue
            self.keys.append(key)
            rep = key.structure_report()
            rep["key_id"] = kid
            if gtype == "ncw":
                rep["ncw_shift_b"] = self.ncws[kid].shift_b
                rep["ncw_syn_weight"] = self.ncws[kid].syn_weight
            self.reports.append(rep)
            built += 1
        if built < n_keys:
            raise RuntimeError(
                f"group {self.group_id}: only {built}/{n_keys} keys passed structural validation"
            )
        self.attempts_total = attempts


def make_error_generator(master_seed: int, group_id: str, key_id: str, param: dict, group_spec: dict, key: QCKey, ncw=None):
    """Returns a generator yielding identical error sequences for every decoder.

    Errors are regenerated per (key_id, error_id) from a deterministic seed so
    all decoders are evaluated on exactly the same (H, e, s) pairs.
    """
    t = param["t"]
    n = 2 * param["r"]

    def gen(error_id: int) -> np.ndarray:
        rng = np.random.default_rng(_child_seed(master_seed, f"err|{group_id}|{key_id}", error_id))
        if group_spec["type"] == "ncw" and ncw is not None:
            return ncw_pressure_error(rng, key, ncw, t, group_spec["kappa"])
        return uniform_fixed_weight(rng, n, t)

    return gen
