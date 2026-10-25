"""Check every numeric cell of the five full body tables against archived data."""
from pathlib import Path
from decimal import Decimal
import csv
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHECKS = []


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def data(name):
    return read(ROOT / 'data' / name)


def table(name):
    with (HERE / 'source_data' / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))[1:]


def pick(rows, **kw):
    matches = [r for r in rows if all(r[k] == v for k, v in kw.items())]
    assert len(matches) == 1
    return matches[0]


def check(label, printed, expected, integer=False):
    token = str(printed).replace(',', '')
    actual = float(token)
    exponent = Decimal(token).as_tuple().exponent
    tolerance = 0 if integer else .5 * 10.**exponent
    passed = abs(actual-float(expected)) <= tolerance + abs(float(expected))*1e-12
    CHECKS.append({'label': label, 'printed': printed, 'expected': float(expected),
                   'rounding_tolerance': tolerance, 'pass': passed})


def triple(label, printed, values):
    numbers = re.findall(r'-?\d+(?:\.\d+)?(?:e-?\d+)?', printed)
    assert len(numbers) == 3, printed
    for suffix, value, expected in zip(('RR', 'low', 'high'), numbers, values):
        check(label + '/' + suffix, value, expected)


def main():
    main_rows = data('t1_formal_main.csv')
    for row in table('table1_body_main_cells.csv'):
        r = pick(main_rows, condition=row[0])
        for col, key in [(1, 'n_keys'), (2, 'c0_failures'), (3, 'c0_dfr'), (4, 'fro2_failures'), (5, 'fro2_dfr'), (7, 'holm_sign_p')]:
            check('Table I/' + row[0] + '/' + key, row[col], r[key], col in (1, 2, 4))
        triple('Table I/' + row[0], row[6], [r[k] for k in ('rr', 'rr_lo', 'rr_hi')])
    offsets = data('t1_offset_scan_p1p.csv')
    conditions = ['RAND', 'TYPE-I', 'NCW-shallow']
    arms = ['FRO-1', 'FRO-2', 'FRO-3', 'FRONEG', 'FRONEG2']
    for row, arm in zip(table('table2_body_offset_scan_cells.csv'), arms):
        for i, cond in enumerate(conditions, 1):
            r = pick(offsets, arm=arm, condition=cond)
            triple('Table II/' + arm + '/' + cond, row[i], [r[k] for k in ('rr_vs_c0', 'rr_lo', 'rr_hi')])
    temporal = data('t2_expanded_temporal.csv')
    for row in table('table3_body_temporal_cells.csv'):
        for i, (point, cond) in enumerate([(p, c) for p in ('P2', 'P3') for c in conditions], 1):
            r = pick(temporal, decoder=row[0], point=point, condition=cond)
            check('Table III/' + row[0] + '/' + point + '/' + cond, row[i], r['dfr' if row[0] == 'C0' else 'rr_vs_c0'])
    modern, bgf = data('t1_modern_scaled.csv'), data('t1_bgf_baseline.csv')
    for row in table('table5_body_modern_cells.csv'):
        r = pick(modern, condition=row[0]); b = pick(bgf, condition=row[0], arm='BGF-C3')
        for col, key in [(1, 'c0_dfr'), (2, 'fro2_dfr'), (3, 'bikeflip_dfr'), (5, 'bf_vs_fro2_mcnemar_p')]:
            check('Table V/' + row[0] + '/' + key, row[col], r[key])
        check('Table V/' + row[0] + '/bgf_dfr', row[4], b['dfr'])
        triple('Table V/' + row[0] + '/bgf_RR', row[6], [b[k] for k in ('rr_vs_c0', 'rr_lo', 'rr_hi')])
    rows = table('table4_body_added_cells.csv')
    raised = json.loads((ROOT / 'results/tier_upgrade/p1pp_main.json').read_text(encoding='utf-8'))
    for row, arm in zip(rows[:3], ('C0', 'FRO-2', 'FRONEG')):
        r = raised['arms'][arm]
        check('Table IV/raised/' + arm + '/failures', row[2], r['failures'], True)
        check('Table IV/raised/' + arm + '/trials', row[3], raised['trials'], True)
        if arm != 'C0': triple('Table IV/raised/' + arm, row[4], [r['rr'], *r['rr_ci95']])
    fair = {r['label']: r['value'] for r in data('t1_fair_l1.csv')}
    for row, arm, comparator in zip(rows[3:6], ('BF-official-20', 'BF-derived-20', 'BGF-tangent'), ('FRO-2', 'FRO-2', 'C0')):
        check('Table IV/' + arm + '/failures', row[2], fair['fair-L1 ' + arm + ' failures'], True)
        check('Table IV/' + arm + '/trials', row[3], fair['fair-L1 trials per arm'], True)
        check('Table IV/' + arm + '/p', row[5], fair[f'fair-L1 {arm} vs {comparator} McNemar p'])
    native = json.loads((ROOT / 'results/tier_upgrade/l1b_classic_carrier.json').read_text(encoding='utf-8'))
    for row, arm in zip(rows[6:8], ('C0', 'FRO-2')):
        check('Table IV/native/' + arm + '/failures', row[2], native['arms'][arm]['failures'], True)
        check('Table IV/native/' + arm + '/trials', row[3], native['trials'], True)
    cpa = {r['label']: r['value'] for r in data('t1_cpa128.csv')}
    for row, arm in zip(rows[8:11], ('C0', 'FRO-2', 'FRONEG')):
        check('Table IV/CPA/' + arm + '/failures', row[2], cpa['CPA-128 ' + arm + ' failures'], True)
        check('Table IV/CPA/' + arm + '/trials', row[3], cpa['CPA-128 trials per arm'], True)
        if arm != 'C0':
            triple('Table IV/CPA/' + arm, row[4], [cpa['CPA-128 ' + arm + suffix] for suffix in (' RR', ' RR lower', ' RR upper')])
    hold = {r['path']: r['value'] for r in data('t1_native_l1_holdout_flat.csv')}
    failure_values = [int(v) for k, v in hold.items() if k.startswith('observed_failures/')]
    assert len(failure_values) == 9
    check('Table IV/holdout/failures', rows[11][2], sum(failure_values), True)
    check('Table IV/holdout/trials', rows[11][3], int(hold['trials_per_cell'])*9, True)
    # Preserve the manuscript's discrepancy as evidence; do not silently repair the source.
    text = (ROOT / 'v3/en/main.tex').read_text(encoding='utf-8')
    line = next(s for s in text.splitlines() if 'BGF, tangent fit &' in s)
    original = line.split('&')[-1].replace('\\', '').strip()
    check('Original Table IV/tangent BGF p', original, fair['fair-L1 BGF-tangent vs C0 McNemar p'])
    offset_line = next(s for s in text.splitlines() if s.startswith('$-1$ &'))
    original_upper = re.search(r',\s*([0-9.]+)\]', offset_line.split('&')[-1]).group(1)
    check('Original Table II/NCW negative-one CI upper', original_upper,
          pick(offsets, condition='NCW-shallow', arm='FRONEG')['rr_hi'])
    candidate = [c for c in CHECKS if not c['label'].startswith('Original')]
    result = {'candidate_numeric_checks': len(candidate), 'candidate_failures': [c for c in candidate if not c['pass']],
              'original_manuscript_discrepancies': [c for c in CHECKS if c['label'].startswith('Original') and not c['pass']],
              'checks': CHECKS,
              'limits': 'Checks numeric cells and archived provenance, not a decoding rerun, fresh bootstrap, or proof of cross-offset optimality.'}
    (HERE / 'table_content_audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, indent=2))
    assert not result['candidate_failures']


if __name__ == '__main__':
    main()
