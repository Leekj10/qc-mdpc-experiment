"""Evidence-driven candidates; read archived CSVs, never modify inputs."""
from pathlib import Path
import csv
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'v3/figure_research/previews'
OUT.mkdir(parents=True, exist_ok=True)
BLUE, GOLD, RED = '#004488', '#DDAA33', '#BB5566'
CONDS = ['RAND', 'TYPE-I', 'NCW-shallow']
plt.rcParams.update({'font.family':'Times New Roman', 'font.size':9,
 'axes.titlesize':10,'axes.labelsize':9,'legend.fontsize':8,
 'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,
 'mathtext.fontset':'custom','mathtext.rm':'Times New Roman',
 'mathtext.it':'Times New Roman:italic','mathtext.bf':'Times New Roman:bold',
 'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})

def read(name):
    with (ROOT/'data'/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def save(fig, name):
    for ext in ('png','pdf','svg'):
        fig.savefig(OUT/f'{name}.{ext}', dpi=300, facecolor='white')
    plt.close(fig)

def main():
    agg, keys = read('t1_formal_main.csv'), read('t1_per_key.csv')
    fig = plt.figure(figsize=(7.16,4.6), layout='constrained')
    gs = fig.add_gridspec(2,3, height_ratios=[1,1.65])
    a = fig.add_subplot(gs[0,:])
    for i,c in enumerate(CONDS):
        r = next(r for r in agg if r['condition']==c)
        rr,lo,hi = [float(r[k]) for k in ('rr','rr_lo','rr_hi')]
        a.errorbar(rr,2-i,xerr=[[rr-lo],[hi-rr]],fmt='o',color=GOLD,
                   markeredgecolor='#292929',capsize=3,elinewidth=1.6)
        a.text(hi+.12,2-i,f'{rr:.2f} [{lo:.2f}, {hi:.2f}]',va='center',fontsize=8)
    a.axvline(1,color='#777777',ls=':',lw=1)
    a.set(yticks=[2,1,0],yticklabels=CONDS,xlim=(.8,10.1),ylim=(-.5,2.6),
          xlabel='Failure-rate ratio C0 / FRO-2  (95% key-bootstrap CI)',
          title='a  Overall reduction, with uncertainty',xticks=[1,2,4,6,8,10])
    for i,c in enumerate(CONDS):
        ax=fig.add_subplot(gs[1,i])
        rows=[r for r in keys if r['condition']==c]
        counts=Counter(int(r['c0_failures'])-int(r['fro2_failures']) for r in rows)
        for d,n in sorted(counts.items()):
            ax.bar(d,n,width=.8,
                   color=GOLD if d>0 else RED if d<0 else '#777777',
                   edgecolor='#333333',linewidth=.5,
                   hatch='//' if d<0 else None,zorder=3)
        ax.axvline(0,color='#777777',lw=.8,ls=':')
        good=sum(n for d,n in counts.items() if d>0)
        bad=sum(n for d,n in counts.items() if d<0)
        ax.set(xlim=(-2.7,10.7),ylim=(0,30),xticks=[-2,0,2,4,6,8,10],
               title=f'{chr(98+i)}  {c} · {len(rows)} keys',
               xlabel='Failures avoided per key\n(C0 − FRO-2); 3,000 decodes')
        ax.text(.97,.96,f'{good} improved\n{bad} worsened\n{counts[0]} tied',
                ha='right',va='top',transform=ax.transAxes,fontsize=8)
        if i==0: ax.set_ylabel('Number of keys')
        else: ax.tick_params(labelleft=False)
    save(fig,'01_main_key_evidence')

def temporal():
    rows=read('t2_expanded_temporal.csv')
    schedules=['FRO-1','FRO-2','FRO-3','R2-2','UNIFORM-2']
    labels=['Round 1: +1','Round 1: +2','Round 1: +3','Round 2: +2','All rounds: +2']
    fig,axs=plt.subplots(1,3,figsize=(7.16,3.25),sharex=True,sharey=True,layout='constrained')
    for ax,c in zip(axs,CONDS):
        for p,offset,col,marker in [('P2',.12,BLUE,'o'),('P3',-.12,RED,'s')]:
            for j,s in enumerate(schedules):
                r=next(r for r in rows if r['condition']==c and r['point']==p and r['decoder']==s)
                v,lo,hi=[float(r[k]) for k in ('rr_vs_c0','rr_lo','rr_hi')]
                ax.errorbar(v,4-j+offset,xerr=[[v-lo],[hi-v]],fmt=marker,color=col,
                            ms=4,capsize=2,elinewidth=1.2,mfc=col if p=='P2' else 'white')
        ax.axvline(1,color='#555555',ls=':',lw=1)
        ax.axhline(.5,color='#cccccc',lw=.7)
        ax.set(xscale='log',xlim=(.006,20),ylim=(-.5,4.6),
               yticks=range(5),yticklabels=labels[::-1],title=c,
               xticks=[.01,.1,1,10],xticklabels=['0.01','0.1','1','10'])
        ax.grid(axis='x',which='major',alpha=.15)
    fig.supxlabel('Failure-rate ratio C0 / intervention · 95% archived bootstrap CI',fontsize=9)
    fig.legend(handles=[Line2D([],[],marker='o',color=BLUE,ls='',label='P2'),
                       Line2D([],[],marker='s',mfc='white',color=RED,ls='',label='P3')],
               loc='outside upper center',ncol=2,frameon=False)
    save(fig,'02_temporal_categorical')

def boundary():
    rows=read('t3_capture_gradient.csv')
    ncw=read('t1_ncw_aware_capture.csv')
    fig,axs=plt.subplots(1,2,figsize=(7.16,3.25),layout='constrained',gridspec_kw={'width_ratios':[1.25,1]})
    ax=axs[0]
    arms=[('C0','c0_dfr',BLUE,'o',-.20),('FRO-2','fro2_dfr',GOLD,'s',0),
          ('NCW-aware (exact recovery)','ncw_exact_recovery_dfr',RED,'^',.20)]
    for name,k,col,m,off in arms:
        source=ncw if k.startswith('ncw') else rows
        ax.scatter(np.arange(4)+off,[float(r[k]) for r in source],color=col,
                   marker=m,s=36,edgecolors='#333333',linewidths=.5,label=name,zorder=3)
    ax.set(yscale='log',ylim=(6e-5,1.5),xticks=range(4),xticklabels=['0','12','46','60'],
           xlabel='Constructed near-codeword overlap κ (categorical positions)',
           ylabel='Absolute decoding failure rate', title='a  Absolute reliability')
    ax.grid(axis='y',which='major',alpha=.15)
    ax.text(3,.45,'κ = 60: both saturated',ha='center',fontsize=8)
    ax.legend(loc='lower right',frameon=False,fontsize=7)
    ax=axs[1]
    for i,r in enumerate(rows):
        v,lo,hi=[float(r[k]) for k in ('rr','rr_lo','rr_hi')]
        ax.errorbar(v,3-i,xerr=[[v-lo],[hi-v]],fmt='s',color=GOLD,
                    mec='#333333',capsize=3,ms=5)
        lab = ('both saturated; unresolved' if int(r['kappa']) == 60
               else f'{v:.3g} [{lo:.3g}, {hi:.3g}]')
        ax.text(.045,3-i+.2,lab,fontsize=8,
                transform=ax.get_yaxis_transform(),bbox=dict(facecolor='white',edgecolor='none',pad=.5))
    ax.axvline(1,color='#555555',ls=':',lw=1)
    ax.set(xscale='log',xlim=(.75,25),ylim=(-.45,3.7),yticks=range(4),
           yticklabels=['κ = 60','κ = 46','κ = 12','κ = 0'],title='b  Relative effect',
           xlabel='C0 / FRO-2 (95% archived CI)',xticks=[1,2,5,10,20],
           xticklabels=['1','2','5','10','20'])
    save(fig,'03_boundary_absolute_relative')

def mechanism():
    rows=read('t1_mechanism_firstround.csv')
    metrics=[('mean_incorrect_first','Incorrect flips'),
             ('mean_correct_first','Correct flips'),('mean_residual_r1','Residual errors')]
    fig,axs=plt.subplots(1,3,figsize=(7.16,2.55),sharex=True,sharey=True,layout='constrained')
    for ax,(k,title),col,m in zip(axs,metrics,[RED,GOLD,BLUE],['s','o','^']):
        for j,c in enumerate(CONDS):
            base=next(r for r in rows if r['condition']==c and r['arm']=='C0')
            fro=next(r for r in rows if r['condition']==c and r['arm']=='FRO-2')
            b,f=float(base[k]),float(fro[k]); v=f/b
            ax.plot([0,v],[2-j,2-j],color=col,lw=2)
            ax.scatter(v,2-j,color=col,marker=m,s=35,edgecolor='#333333',linewidth=.5,zorder=3)
            ax.text(.03,2-j+.18,f'{b:.2f} → {f:.2f}  ({v:.2f}×)',fontsize=8)
        ax.axvline(1,color='#777777',ls=':',lw=1)
        ax.set(xlim=(0,1.22),ylim=(-.45,2.55),xticks=[0,.5,1],
               yticks=[2,1,0],yticklabels=CONDS,title=title)
    fig.supxlabel('FRO-2 / C0 mean · labels show absolute means · 20 keys × 1,000 trials per arm',fontsize=8)
    save(fig,'04_mechanism_asymmetry')

if __name__=='__main__':
    main(); temporal(); boundary(); mechanism()
    print(OUT)
