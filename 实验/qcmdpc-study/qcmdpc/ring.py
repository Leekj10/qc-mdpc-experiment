"""F2[x]/(x^r - 1) ring arithmetic for n0=2 QC-MDPC codes (Python reference).

Conventions (frozen, see configs/pre_register.json):
- Code defined by H = [H0 | H1], each Hi an r x r circulant with first ROW h.
  H[i, k] = h[(i - k) mod r]  =>  syndrome s = H e^T satisfies
  s_i = sum_k e_k * h[(i-k) mod r]   (cyclic convolution).
- Column k of a block = np.roll(h, k).
- UPC at position k of a block: alpha_k = #{i : s_i = 1 and h[(i-k) mod r] = 1}
  = sum_{a in supp(h)} s[(a + k) mod r] = sum_{a} roll(s, -a)[k].
- Global positions: 0..r-1 -> block 0, r..2r-1 -> block 1.
"""
from __future__ import annotations

import numpy as np


class QCKey:
    """A QC-MDPC secret key: two circulant blocks h0, h1 (binary, weight d)."""

    def __init__(self, h0: np.ndarray, h1: np.ndarray, key_id: str = ""):
        h0 = np.asarray(h0, dtype=np.uint8)
        h1 = np.asarray(h1, dtype=np.uint8)
        assert h0.ndim == 1 and h0.shape == h1.shape, "blocks must be 1-D, same length"
        assert np.all((h0 == 0) | (h0 == 1)) and np.all((h1 == 0) | (h1 == 1))
        assert int(h0.sum()) == int(h1.sum()) > 0, "both blocks must have equal weight d>0"
        self.r = int(h0.shape[0])
        self.d = int(h0.sum())
        self.n = 2 * self.r
        self.h0, self.h1 = h0, h1
        self.key_id = key_id
        self.supp0 = np.nonzero(h0)[0]
        self.supp1 = np.nonzero(h1)[0]
        self._i16 = np.int16
        # gather index matrices for upc_fast (bit-exact, precomputed once)
        cols = np.arange(self.r, dtype=np.int32)
        self._I0 = (self.supp0.astype(np.int64)[:, None] + cols[None, :]) % self.r
        self._I1 = (self.supp1.astype(np.int64)[:, None] + cols[None, :]) % self.r

    # ------------------------------------------------------------------ syndrome
    def syndrome(self, e0: np.ndarray, e1: np.ndarray) -> np.ndarray:
        """s = H0 e0 + H1 e1 (mod 2) via sparse column XOR (exact)."""
        s = np.zeros(self.r, dtype=np.uint8)
        for k in np.nonzero(e0)[0]:
            s ^= np.roll(self.h0, int(k))
        for k in np.nonzero(e1)[0]:
            s ^= np.roll(self.h1, int(k))
        return s

    def syndrome_from_global(self, e: np.ndarray) -> np.ndarray:
        e = np.asarray(e, dtype=np.uint8)
        assert e.shape == (self.n,)
        return self.syndrome(e[: self.r], e[self.r :])

    def flip(self, s: np.ndarray, pos: int) -> np.ndarray:
        """Syndrome after flipping global position pos (returns new array)."""
        r = self.r
        if pos < r:
            col = np.roll(self.h0, pos)
        else:
            col = np.roll(self.h1, pos - r)
        return s ^ col

    # ------------------------------------------------------------------ UPC
    def upc(self, s: np.ndarray) -> np.ndarray:
        """NUPC vector alpha (length 2r): alpha_k = sum_{a in supp(h)} s[(a+k) % r].

        Roll-based reference implementation (kept as oracle for tests).
        """
        s_i16 = s.astype(self._i16)
        a0 = np.zeros(self.r, dtype=self._i16)
        for a in self.supp0:
            a0 += np.roll(s_i16, -int(a))
        a1 = np.zeros(self.r, dtype=self._i16)
        for a in self.supp1:
            a1 += np.roll(s_i16, -int(a))
        return np.concatenate([a0, a1])

    def upc_fast(self, s: np.ndarray) -> np.ndarray:
        """Bit-exact gather implementation of upc (used by all decoders).

        alpha_k = sum_j s[(supp_j + k) % r] = s[I].sum(axis=0); integer-only,
        verified equal to the roll-based reference by tests/test_core.py.
        """
        a0 = s[self._I0].sum(axis=0)
        a1 = s[self._I1].sum(axis=0)
        out = np.empty(2 * self.r, dtype=self._i16)
        out[: self.r] = a0
        out[self.r :] = a1
        return out

    # ------------------------------------------------- near-codeword utilities
    def canonical_syndromes(self):
        """Syndromes of (h0, 0) and (0, h1): used to search (d,d) near-codewords.

        Because syndrome is shift-covariant, syndrome of (rot(h0,a), rot(h1,b))
        equals roll(s0, a) XOR roll(s1, b).
        """
        s0 = np.zeros(self.r, dtype=np.uint8)
        for k in self.supp0:
            s0 ^= np.roll(self.h0, int(k))
        s1 = np.zeros(self.r, dtype=np.uint8)
        for k in self.supp1:
            s1 ^= np.roll(self.h1, int(k))
        return s0, s1

    def structure_report(self) -> dict:
        """Structural self-validation statistics (pre-registered)."""
        rep = {
            "r": self.r,
            "d": self.d,
            "max_run_h0": _max_cyclic_run(self.h0),
            "max_run_h1": _max_cyclic_run(self.h1),
        }
        s0, s1 = self.canonical_syndromes()
        rep["syn_weight_canonical"] = int((s0 ^ s1).sum())
        return rep


def _max_cyclic_run(v: np.ndarray) -> int:
    """Longest cyclic run of ones in binary vector v."""
    idx = np.nonzero(v)[0]
    if idx.size == 0:
        return 0
    r = v.size
    best = 1
    cur = 1
    # traverse sorted support cyclically
    gaps = np.diff(np.concatenate([idx, idx[:1] + r]))
    for g in gaps:
        if g == 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return min(best, idx.size)


def brute_syndrome(key: QCKey, e0: np.ndarray, e1: np.ndarray) -> np.ndarray:
    """O(r * w(e)) pure-Python reference syndrome (test oracle, small r only)."""
    r = key.r
    s = [0] * r
    for k in range(r):
        if e0[k]:
            for i in range(r):
                s[i] ^= int(key.h0[(i - k) % r])
    for k in range(r):
        if e1[k]:
            for i in range(r):
                s[i] ^= int(key.h1[(i - k) % r])
    return np.array(s, dtype=np.uint8)
