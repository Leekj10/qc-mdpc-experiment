"""Failure-mode taxonomy (decision-tree priority pre-registered):

    divergence -> period-2 oscillation -> stagnation -> early-misflip -> other

Definitions (frozen):
- divergence:  max(sw) > sw[0] and final weight >= sw[0]
- period-2:    last 6 weights alternate a,b,a,b,a,b with a != b
- stagnation:  >= 60% of iterations show zero weight change
- early-misflip: among the first ceil(max_iter/4) iterations, > 50% of flipped
                 positions lie outside the true error support (needs flip log)
"""
from __future__ import annotations

import math
import numpy as np

from .decoders import TrajectoryResult


def classify_failure(
    traj: TrajectoryResult,
    e_support: set[int] | None = None,
    max_iter: int | None = None,
) -> str:
    """Classify a failed trajectory using the frozen decision-tree priority.

    ``max_iter`` is the decoder's frozen iteration budget, not the number of
    logged rounds.  Callers should pass it explicitly because a decoder may
    stop before its budget on a successful or blocked trajectory.  The
    fallback keeps older callers usable by consulting ``traj.extra`` and then
    ``n_iters_run``.
    """
    if traj.success:
        return "success"
    sw = traj.syndrome_weights
    if not sw:
        return "other"
    w0 = sw[0]
    # 1) divergence
    if max(sw) > w0 and sw[-1] >= w0:
        return "divergence"
    # 2) period-2 oscillation
    if len(sw) >= 6:
        tail = sw[-6:]
        if tail[0] != tail[1] and all(tail[i] == tail[i % 2] for i in range(6)):
            return "period2"
    # 3) stagnation
    if len(sw) >= 2:
        diffs = np.abs(np.diff(sw))
        if (diffs == 0).mean() >= 0.6:
            return "stagnation"
    # 4) early mis-flip
    if e_support is not None and traj.flip_positions:
        if max_iter is None:
            max_iter = traj.extra.get("max_iter", traj.n_iters_run)
        q = max(1, math.ceil(int(max_iter) / 4))
        early = traj.flip_positions[:q]
        flips = [p for step in early for p in step]
        if flips:
            mis = sum(1 for p in flips if p not in e_support) / len(flips)
            if mis > 0.5:
                return "early_misflip"
    return "other"


MODES = ["success", "divergence", "period2", "stagnation", "early_misflip", "other"]
