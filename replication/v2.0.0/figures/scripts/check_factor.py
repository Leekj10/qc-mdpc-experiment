"""Verify figure 2 and tables 2–3 against stored paired arrays; no simulation."""
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT.parent
ARM = ("plain_0", "plain_p2", "post_0", "post_p2")
POOLS = (
    ("P1prime", "Original", "poststep_factor_full.npz", (90, 29, 96, 262), (2.47, 1.97, 2.97)),
    ("P2", "Original", "poststep_factor_full_P2.npz", (204, 83, 255, 623), (5.32, 4.70, 5.95)),
    ("P1prime", "Fresh", "poststep_confirm_P1_full.npz", (80, 21, 101, 271), (2.49, 2.01, 2.97)),
    ("P2", "Fresh", "poststep_confirm_P2_full.npz", (196, 79, 256, 607), (5.09, 4.45, 5.74)),
)
BOOTSTRAP_SEED = 20260905
BOOTSTRAP_DRAWS = 10_000


def summarize():
    counts_out, contrasts_out, inter_out = [], [], []
    for point, sample, filename, advertised_counts, advertised_interval in POOLS:
        with np.load(ARCHIVE / 'lw-vs' / 'audit_poststep' / 'poststep_factor' / filename, allow_pickle=False) as a:
            fail = np.array([a["fail_"+s] for s in ARM], dtype=np.int64)
            main = np.array([a["main_"+s] for s in ARM], dtype=np.int64)
            scan = np.array([a["scans_"+s] for s in ARM], dtype=np.int64)
            assert fail.shape == main.shape == scan.shape == (4, 46, 2000)
            assert np.all((fail == 0) | (fail == 1))
            assert np.all((main >= 0) & (main <= 20))
            assert np.all(scan[:2] == main[:2])
            assert np.all((scan[2:] >= main[2:]) & (scan[2:] <= 2 + main[2:]))
            assert np.array_equal(a["first_plain_0"], a["first_post_0"])
            assert np.array_equal(a["first_plain_p2"], a["first_post_p2"])
            keys, errors = fail.shape[1:]
            per_key = fail.sum(axis=2)
            rnd = np.random.default_rng(BOOTSTRAP_SEED)
            # The same cluster draw is applied to all four variants within each pool.
            ix = rnd.integers(0, keys, size=(BOOTSTRAP_DRAWS, keys))
            rd = np.array([per_key[1]-per_key[0], per_key[3]-per_key[2]]) * (1000/errors)
            counts = tuple(map(int, per_key.sum(axis=1)))
            assert counts == advertised_counts
            for i, k in enumerate(ARM):
                counts_out.append(dict(point=point, sample=sample,
                                       postprocessing=("Off" if i < 2 else "On"),
                                       offset=(0 if i % 2 == 0 else 2), keys=keys,
                                       errors_per_key=errors, decodes=keys*errors, failures=counts[i],
                                       main_rounds_mean=f"{main[i].mean():.9f}",
                                       total_scans_mean=f"{scan[i].mean():.9f}"))
            for i, policy in enumerate(("Off", "On")):
                estimate = rd[i].mean()
                lo, hi = np.quantile(rd[i][ix].mean(axis=1), (.025, .975))
                assert (hi < 0 if i == 0 else lo > 0)
                contrasts_out.append(dict(point=point, sample=sample, postprocessing=policy,
                                          difference_per_1000=float(estimate), ci95_low=float(lo),
                                          ci95_high=float(hi)))
            delta = rd[1]-rd[0]
            lo, hi = np.quantile(delta[ix].mean(axis=1), (.025, .975))
            values = (float(delta.mean()), float(lo), float(hi))
            assert np.allclose(np.round(values, 2), advertised_interval)
            inter_out.append(dict(point=point, sample=sample, interaction_per_1000=values[0],
                                  ci95_low=values[1], ci95_high=values[2]))
    return counts_out, contrasts_out, inter_out


def main():
    checked = 0
    names = ('factor_counts_and_work.csv', 'factor_offset_contrasts.csv', 'factor_interaction.csv')
    for name, rows in zip(names, summarize(), strict=True):
        with (ROOT/'source_data'/name).open(encoding='utf8', newline='') as source:
            expected = list(csv.DictReader(source))
        if len(expected) != len(rows):
            raise ValueError(f'Unexpected row count in {name}')
        for i, (row, want) in enumerate(zip(rows, expected, strict=True), 1):
            if row.keys() != want.keys():
                raise ValueError(f'Unexpected fields in {name}')
            for field, value in row.items():
                valid = (np.isclose(value, float(want[field]), rtol=0, atol=1e-12)
                         if isinstance(value, float) else str(value) == want[field])
                if not valid:
                    raise ValueError(f'{name}, row {i}, field {field}: {value} != {want[field]}')
            checked += 1
    print(f'PASS: {checked} rows verified from saved paired outcomes.')


if __name__ == '__main__':
    main()
