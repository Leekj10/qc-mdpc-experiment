from __future__ import annotations
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent/'ncw_adaptive_data_v2'

def rr_boot(base,trt,B=10000,seed=20260913):
    base=np.asarray(base,float); trt=np.asarray(trt,float); rng=np.random.default_rng(seed); n=len(base)
    point=base.sum()/trt.sum() if trt.sum() else (base.sum()+.5)/.5
    idx=rng.integers(0,n,size=(B,n)); den=trt[idx].sum(1); num=base[idx].sum(1); vals=num[den>0]/den[den>0]
    return {'point_rr':float(point),'ci95':[float(np.quantile(vals,.025)),float(np.quantile(vals,.975))],'finite_bootstrap':int(vals.size)}

def main():
    rows=[json.loads(p.read_text(encoding='utf-8')) for p in ROOT.glob('P*_stlr_v2__*.json')]
    cells={}
    for x in rows: cells.setdefault(x['parameter']['id'],{}).setdefault(x['group'],{})[x['decoder']]=x
    out={'protocol':json.loads((ROOT/'preregistration.json').read_text(encoding='utf-8')),'cells':{}}
    csv=['parameter,group,decoder,failures,trials,dfr,upper95,avg_iters,avg_upc_calls,avg_probes,recoveries,recovery_accepts,rr_vs_c0,rr_lo,rr_hi,rr_vs_fro2,rr2_lo,rr2_hi']
    for p,gs in sorted(cells.items()):
      out['cells'][p]={}
      for g,ds in sorted(gs.items()):
        out['cells'][p][g]={}; c0=ds['C0']; f2=ds['FRO-2']
        for name,x in sorted(ds.items()):
          row={k:x[k] for k in ['failures','trials','dfr','upper95','avg_iters','avg_upc_calls','avg_probes','recoveries_total','recovery_accepts_total']}
          if name!='C0':
            r0=rr_boot(c0['per_key_failures'],x['per_key_failures'],seed=20260913+sum(map(ord,p+g+name)))
            row['rr_vs_c0']=r0
          else: row['rr_vs_c0']=None
          if name not in ('C0','FRO-2'):
            r2=rr_boot(f2['per_key_failures'],x['per_key_failures'],seed=20261013+sum(map(ord,p+g+name)))
            row['rr_vs_fro2']=r2
          else: row['rr_vs_fro2']=None
          out['cells'][p][g][name]=row
          a=row['rr_vs_c0']; b=row['rr_vs_fro2']
          csv.append(f"{p},{g},{name},{x['failures']},{x['trials']},{x['dfr']:.8g},{x['upper95']:.8g},{x['avg_iters']:.6g},{x['avg_upc_calls']:.6g},{x['avg_probes']:.6g},{x.get('recoveries_total',0)},{x.get('recovery_accepts_total',0)},{'' if not a else a['point_rr']},{'' if not a else a['ci95'][0]},{'' if not a else a['ci95'][1]},{'' if not b else b['point_rr']},{'' if not b else b['ci95'][0]},{'' if not b else b['ci95'][1]}")
    (ROOT/'stlr_analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    (ROOT/'stlr_summary.csv').write_text('\n'.join(csv)+'\n',encoding='utf-8')
    print('aggregated',len(rows),'cells')

if __name__=='__main__': main()
