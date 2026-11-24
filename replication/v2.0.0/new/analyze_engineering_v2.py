"""Summarize corrected engineering comparison (key-cluster bootstrap)."""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent/'engineering_data_v2'
METHODS=['C0','FRO-2','STLR','SR-NCW','BGF-C3']

def rr_boot(base, arm, B=10000, seed=20260916):
    base=np.asarray(base,float); arm=np.asarray(arm,float); rng=np.random.default_rng(seed); n=len(base)
    idx=rng.integers(0,n,size=(B,n)); den=arm[idx].sum(1); num=base[idx].sum(1)
    vals=np.divide(num,den,out=np.full(B,np.nan),where=den>0); vals=vals[np.isfinite(vals)]
    if arm.sum()==0 or vals.size==0: return {'point_rr':None,'ci95':None,'finite_bootstrap':int(vals.size)}
    return {'point_rr':float(base.sum()/arm.sum()),'ci95':[float(np.quantile(vals,.025)),float(np.quantile(vals,.975))], 'finite_bootstrap':int(vals.size)}

def main():
    cells={}
    for p in ROOT.glob('P*_engineering_v2__*.json'):
        x=json.loads(p.read_text(encoding='utf-8')); cells.setdefault(x['parameter']['id'],{}).setdefault(x['group'],{})[x['method']]=x
    out={'protocol':json.loads((ROOT/'preregistration.json').read_text(encoding='utf-8')),'cells':{}}; rows=[]
    for pid,groups in sorted(cells.items()):
        out['cells'][pid]={}
        for gid,methods in sorted(groups.items()):
            out['cells'][pid][gid]={}; base=methods['C0']
            for method in METHODS:
                x=methods[method]; row={k:x[k] for k in ('failures','trials','dfr','upper95','avg_iters','p99_iters','avg_upc_calls','avg_probes','trigger_rate','recovery_accept_rate','ms_per_decode')}
                row['rr_vs_c0']=None if method=='C0' else rr_boot(base['per_key_failures'],x['per_key_failures'],seed=20260916+sum(map(ord,pid+gid+method)))
                out['cells'][pid][gid][method]=row; rr=row['rr_vs_c0']
                rows.append({'parameter':pid,'group':gid,'method':method,**row,'rr_point':'' if rr is None or rr['point_rr'] is None else rr['point_rr'],'rr_lo':'' if rr is None or rr['ci95'] is None else rr['ci95'][0],'rr_hi':'' if rr is None or rr['ci95'] is None else rr['ci95'][1]})
    (ROOT/'engineering_analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    with (ROOT/'engineering_summary.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    # Keep a manuscript-facing cost table in the same pass as the statistical summary.
    # The parameter id is normalized to P2/P3 for compact table labels.
    cost_fields = [
        'parameter', 'group', 'method', 'failures', 'trials', 'dfr',
        'avg_iters', 'p99_iters', 'avg_upc_calls', 'avg_probes',
        'trigger_rate', 'recovery_accept_rate', 'ms_per_decode'
    ]
    cost_rows = []
    for row in rows:
        cost_row = {key: row[key] for key in cost_fields}
        cost_row['parameter'] = str(cost_row['parameter']).replace('_engineering_v2', '')
        cost_rows.append(cost_row)
    with (ROOT/'engineering_cost_table.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cost_fields)
        w.writeheader()
        w.writerows(cost_rows)
    pair_fields = [
        'parameter', 'group', 'comparison', 'base_method', 'arm_method',
        'base_failures', 'arm_failures', 'base_trials', 'arm_trials',
        'rr_point', 'rr_lo', 'rr_hi', 'finite_bootstrap'
    ]
    pair_rows = []
    for pid, groups in sorted(cells.items()):
        for gid, methods in sorted(groups.items()):
            for base_method, arm_method in [('C0', 'FRO-2'), ('C0', 'STLR'),
                                             ('C0', 'SR-NCW'), ('C0', 'BGF-C3'),
                                             ('FRO-2', 'STLR'), ('FRO-2', 'SR-NCW'),
                                             ('FRO-2', 'BGF-C3')]:
                base = methods[base_method]
                arm = methods[arm_method]
                rr = rr_boot(base['per_key_failures'], arm['per_key_failures'],
                             seed=20260916 + sum(map(ord, pid + gid + base_method + arm_method)))
                pair_rows.append({
                    'parameter': str(pid).replace('_engineering_v2', ''),
                    'group': gid,
                    'comparison': f'{base_method}/{arm_method}',
                    'base_method': base_method,
                    'arm_method': arm_method,
                    'base_failures': base['failures'],
                    'arm_failures': arm['failures'],
                    'base_trials': base['trials'],
                    'arm_trials': arm['trials'],
                    'rr_point': '' if rr['point_rr'] is None else rr['point_rr'],
                    'rr_lo': '' if rr['ci95'] is None else rr['ci95'][0],
                    'rr_hi': '' if rr['ci95'] is None else rr['ci95'][1],
                    'finite_bootstrap': rr['finite_bootstrap'],
                })
    with (ROOT/'engineering_pairwise_rr.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=pair_fields)
        w.writeheader()
        w.writerows(pair_rows)
    print(f'Aggregated {len(rows)} method-cells')

if __name__=='__main__': main()
