"""Complete manuscript figure candidates using archived tables and Tol colors."""
from pathlib import Path
import csv
import json
import hashlib
import shutil
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import fitz
import evidence_redesign as base

ROOT = base.ROOT
OUT = ROOT/'v3/figure_research/complete_set'
OUT.mkdir(parents=True,exist_ok=True)
BLUE,GOLD,RED = base.BLUE,base.GOLD,base.RED
CONDS=base.CONDS
read=base.read
BASE_OUT=base.OUT

def save(fig,name):
    for ext in ('png','pdf','svg'):
        fig.savefig(OUT/f'{name}.{ext}',dpi=300,facecolor='white')
    plt.close(fig)

def style(ax):
    ax.grid(axis='x',alpha=.15)

def design():
    fig=plt.figure(figsize=(7.16,3.55),layout='constrained')
    gs=fig.add_gridspec(2,2,height_ratios=[1.55,1],width_ratios=[1,1])
    ax=fig.add_subplot(gs[0,0]);ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    ax.set_title('a  Paired decoding',loc='left')
    def box(x,y,w,h,text,col):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.015',
                     facecolor='white',edgecolor=col,linewidth=1.4))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=8)
    def arrow(x,y,xx,yy):
        ax.annotate('',xy=(xx,yy),xytext=(x,y),arrowprops=dict(arrowstyle='->',color='#555555',lw=1))
    box(.12,.73,.76,.21,'One instance: $(H,e,s)$\n$s=He^T$',BLUE)
    box(.04,.39,.39,.18,'C0\nbaseline',BLUE)
    box(.57,.39,.39,.18,'FRO-2\nround 1: +2',GOLD)
    arrow(.38,.72,.235,.59);arrow(.62,.72,.765,.59)
    box(.12,.055,.76,.18,'Paired outcomes → per-key statistics',RED)
    arrow(.235,.38,.38,.25);arrow(.765,.38,.62,.25)
    ax=fig.add_subplot(gs[0,1]);ax.set_title('b  Intervention schedule',loc='left')
    rounds=np.arange(1,7)
    ax.plot(rounds,np.zeros(6),'o-',color=BLUE,ms=5,label='C0')
    ax.step(rounds,[2,0,0,0,0,0],where='post',marker='s',ls='--',color=GOLD,mec='#333333',mew=.5,ms=5,label='FRO-2')
    ax.text(3.8,.4,'Same baseline\nfrom round 2',ha='center',fontsize=8)
    ax.set(xticks=rounds,yticks=[0,1,2],ylim=(-.25,2.65),xlabel='Decoding round',ylabel='Threshold offset Δτ')
    ax.legend(frameon=False,loc='upper right',ncol=2,fontsize=7)
    ax=fig.add_subplot(gs[1,:]);ax.axis('off')
    ax.set_title('c  Evidence streams · keys × error draws per key',loc='left')
    # Fresh-only gate is a subset of formal pool, not an independent sequential stage.
    labels=['Fresh-key subset','Formal pool','P2 / P3 confirmation','P4 held-out rule']
    details=['212 × 3,000','278 × 3,000','50 × 1,000 / cell','48 × 1,000']
    for i,(label,detail) in enumerate(zip(labels,details)):
        x=i/4+.015
        ax.add_patch(FancyBboxPatch((x,.17),.225,.63,transform=ax.transAxes,
                     boxstyle='round,pad=.005',fc='white',ec=[BLUE,GOLD,BLUE,RED][i],lw=1.2))
        ax.text(x+.1125,.63,label,transform=ax.transAxes,ha='center',fontsize=7.4)
        ax.text(x+.1125,.39,detail,transform=ax.transAxes,ha='center',fontsize=8,fontweight='bold')
    save(fig,'fig1_study_design')

def failure_modes():
    rows=read('t1_failure_modes.csv')
    modes=[('stagnation','Stagnation',BLUE,''),('early_misflip','Early misflip',RED,'//'),('other','Other',GOLD,'..')]
    fig,axs=plt.subplots(1,3,figsize=(7.16,2.35),sharex=True,sharey=True,layout='constrained')
    for ax,c in zip(axs,CONDS):
        ax.set_title(c)
        for y,arm in [(1,'C0'),(0,'FRO-2')]:
            selected=[r for r in rows if r['condition']==c and r['arm']==arm]
            total=sum(int(r['count']) for r in selected)
            assert all(int(r['count'])==0 for r in selected if r['mode'] in ['divergence','period2'])
            left=0
            for mode,label,col,hatch in modes:
                n=int(next(r for r in selected if r['mode']==mode)['count']); pct=100*n/total
                ax.barh(y,pct,left=left,height=.5,color=col,hatch=hatch,edgecolor='white',lw=.7)
                if pct>8: ax.text(left+pct/2,y,str(n),ha='center',va='center',fontsize=8,
                                  color='white' if col==BLUE else '#111111')
                left+=pct
            ax.text(101.5,y,f'n={total}',va='center',fontsize=7)
        ax.set(xlim=(0,133),xticks=[0,50,100],yticks=[1,0],yticklabels=['C0','FRO-2'],ylim=(-.55,1.55))
    fig.supxlabel('Share among failures (%) · segment labels: counts · divergence / period-2: zero',fontsize=8)
    fig.legend(handles=[plt.Rectangle((0,0),1,1,fc=col,hatch=hatch,label=label) for _,label,col,hatch in modes],
               loc='outside upper center',ncol=3,frameon=False)
    save(fig,'panel_failure_modes')

def controls():
    rows=read('t1_round_controls.csv')
    arms=['FRO-2','R2one','FRONEG','R2plus']
    labels=['+2: round 1','+2: round 2','−1: round 1','+2: rounds 2+']
    fig,axs=plt.subplots(1,3,figsize=(7.16,2.8),sharex=True,sharey=True,layout='constrained')
    for ax,c in zip(axs,CONDS):
        for j,arm in enumerate(arms):
            r=next(r for r in rows if r['condition']==c and r['arm']==arm)
            v,lo,hi=[float(r[k]) for k in ('rr_vs_c0','rr_lo','rr_hi')]
            col=GOLD if arm=='FRO-2' else BLUE if arm=='R2one' else RED
            ax.errorbar(v,3-j,xerr=[[v-lo],[hi-v]],fmt='s' if arm=='FRO-2' else 'o',
                        color=col,mec='#333333',mew=.4,capsize=2,ms=4)
            ax.text(.97,3-j+.19,f'{v:.3g}',transform=ax.get_yaxis_transform(),ha='right',fontsize=7)
        ax.axvline(1,color='#555555',ls=':',lw=1)
        ax.set(title=c,xscale='log',xlim=(.008,10),ylim=(-.5,3.6),
               yticks=[3,2,1,0],yticklabels=labels,xticks=[.01,.1,1,10],xticklabels=['0.01','0.1','1','10'])
        style(ax)
    fig.supxlabel("Primary point P1′: C0 / arm · 95% key-cluster bootstrap CI",fontsize=8)
    save(fig,'panel_primary_round_controls')

def transfer():
    rows=read('t2_transfer_p2.csv')
    fig,ax=plt.subplots(figsize=(7.16,1.85),layout='constrained')
    for j,c in enumerate(CONDS):
        r=next(r for r in rows if r['condition']==c)
        v,lo,hi=[float(r[k]) for k in ('rr','rr_lo','rr_hi')]
        ax.errorbar(v,2-j,xerr=[[v-lo],[hi-v]],fmt='s',color=GOLD,mec='#333333',capsize=3)
        ax.text(hi+.10,2-j,f'{v:.2f} [{lo:.2f}, {hi:.2f}]',fontsize=8,va='center')
    ax.axvline(1,color='#555555',ls=':',lw=1)
    ax.set(yticks=[2,1,0],yticklabels=CONDS,xlim=(.8,6),ylim=(-.5,2.5),
           xlabel='Independent P2 transfer: C0 / FRO-2 · 95% archived CI · 30 keys × 3,000 / condition')
    save(fig,'panel_independent_transfer')

def modern():
    rows=read('t1_modern_scaled.csv'); bgf=read('t1_bgf_baseline.csv')
    hold={r['path']:r['value'] for r in read('t1_native_l1_holdout_flat.csv')}
    fig=plt.figure(figsize=(7.16,4.35),layout='constrained')
    gs=fig.add_gridspec(2,3,height_ratios=[1.25,1])
    methods=[('C0','c0_dfr',BLUE,'o'),('FRO-2','fro2_dfr',GOLD,'s'),
             ('BIKE-Flip','bikeflip_dfr',RED,'D'),('BGF-C3',None,BLUE,'^')]
    for i,c in enumerate(CONDS):
        ax=fig.add_subplot(gs[0,i]);r=next(r for r in rows if r['condition']==c)
        for j,(arm,k,col,m) in enumerate(methods):
            v=float(r[k]) if k else float(next(q for q in bgf if q['condition']==c and q['arm']==arm)['dfr'])
            ax.scatter(v,3-j,color=col,marker=m,s=32,facecolors='white' if arm=='BGF-C3' else col,
                       edgecolors=BLUE if arm=='BGF-C3' else '#222222',linewidth=.8,zorder=3)
            ax.text(v*1.14,3-j,f'{v:.3g}',va='center',fontsize=7)
        ax.set(xscale='log',xlim=(7e-5,3.5e-3),ylim=(-.5,3.5),yticks=[3,2,1,0],
               yticklabels=[m[0] for m in methods] if i==0 else [],title=c,xlabel='Absolute DFR at P1′')
        style(ax)
    ax=fig.add_subplot(gs[1,:2])
    for c,col,m,ls in [('RAND',BLUE,'o','-'),('TYPE-I',RED,'s','--'),('NCW',GOLD,'^',':')]:
        ax.plot([0,2,4],[float(hold[f'two_round_convergence_percent/offset_{o}/{c}']) for o in [0,2,4]],
                color=col,marker=m,ls=ls,ms=4,mec='#333333',mew=.4,label=c)
    ax.set(xticks=[0,2,4],xticklabels=['+0','+2','+4'],ylim=(0,105),
           xlabel='First-round offset · native BIKE Level-1',ylabel='Converged within 2 rounds (%)')
    ax.legend(frameon=False,ncol=3,fontsize=7,loc='upper right')
    ax=fig.add_subplot(gs[1,2]);ax.axis('off')
    ax.text(.04,.97,'Hold-out resolution',va='top',fontweight='bold',fontsize=10)
    ax.text(.04,.76,'1,000,000 trials / cell\n0 observed failures\n\nDFR upper bound ≈ 3×10⁻⁶\n(rule of three)\n\nNo resolved DFR ranking\nfrom these zero counts.',va='top',fontsize=8,linespacing=1.4)
    save(fig,'fig7_modern_decoders')

def sensitivity():
    rows=read('t1_t_sensitivity.csv')
    fig,axs=plt.subplots(1,2,figsize=(7.16,2.8),layout='constrained')
    ax=axs[0]
    for arm,col,m in [('c0',BLUE,'o'),('fro2',GOLD,'s')]:
        t=np.array([int(r['t']) for r in rows]);v=np.array([float(r[f'{arm}_dfr']) for r in rows])
        ax.plot(t,np.where(v>0,v,np.nan),color=col,marker=m,ms=5,mec='#333333',mew=.4,label='C0' if arm=='c0' else 'FRO-2')
    ax.set(yscale='log',xticks=[88,90,92,94,96],xlabel='Error weight t',ylabel='DFR · positive observations',ylim=(2e-5,.07))
    ax.legend(frameon=False);ax.set_title('a  Sensitivity sweep')
    ax=axs[1];ax.axis('off')
    table=ax.table(cellText=[['88','0 / 30,000','0 / 30,000'],['90','1 / 30,000','0 / 30,000']],
                   colLabels=['t','C0 failures','FRO-2 failures'],cellLoc='center',bbox=[0,.5,1,.4])
    table.auto_set_font_size(False);table.set_fontsize(8)
    for (r,c),cell in table.get_celld().items():
        cell.set_edgecolor('#cccccc')
        if r==0: cell.set_facecolor(BLUE);cell.get_text().set_color('white')
    ax.set_title('b  Zero-event cells remain explicit')
    ax.text(0,.38,'Zero failures ≠ zero true DFR.\nRule-of-three upper bound: ≈ 1×10⁻⁴.\nNo artificial epsilon on the log axis.\nSeparate t=90 upgrade campaign excluded.',va='top',fontsize=8,linespacing=1.7)
    save(fig,'supp_t_sensitivity')

def compose(name,parts):
    """Stack full-width vector PDF panels; export editable SVG and PNG too."""
    docs=[fitz.open(p) for p in parts]; width=515.52
    heights=[d[0].rect.height*width/d[0].rect.width for d in docs]
    out=fitz.open();page=out.new_page(width=width,height=sum(heights))
    y=0
    for d,h in zip(docs,heights):
        page.show_pdf_page(fitz.Rect(0,y,width,y+h),d,0);y+=h
    out.save(OUT/f'{name}.pdf')
    page.get_pixmap(matrix=fitz.Matrix(300/72,300/72)).save(OUT/f'{name}.png')
    (OUT/f'{name}.svg').write_text(page.get_svg_image(text_as_path=False),encoding='utf-8')
    for d in docs:d.close()
    out.close()

def publish():
    # Keep source figure names; no image numbered fig6 exists in the manuscript.
    for ext in ('png','pdf','svg'):
        shutil.copyfile(BASE_OUT/f'01_main_key_evidence.{ext}',OUT/f'fig2_main_results.{ext}')
    compose('fig3_mechanism',[BASE_OUT/'04_mechanism_asymmetry.pdf',OUT/'panel_failure_modes.pdf'])
    compose('fig4_temporal_dissociation',[BASE_OUT/'02_temporal_categorical.pdf',OUT/'panel_primary_round_controls.pdf'])
    compose('fig5_scope_and_boundary',[OUT/'panel_independent_transfer.pdf',BASE_OUT/'03_boundary_absolute_relative.pdf'])
    stems=['fig1_study_design','fig2_main_results','fig3_mechanism','fig4_temporal_dissociation','fig5_scope_and_boundary','fig7_modern_decoders']
    atlas=fitz.open()
    for stem in stems:
        with fitz.open(OUT/f'{stem}.pdf') as d:atlas.insert_pdf(d)
    atlas.save(OUT/'完整图集.pdf');atlas.close()
    titles=['图1 配对研究设计','图2 总体收益与逐密钥证据','图3 首轮机制与失败构成',
            '图4 干预时机：扩展参数点与主参数点','图5 独立迁移与失效边界','图7 现代译码器与原生L1收敛']
    cards=''.join(f'<section><h2>{t}</h2><a href="{s}.pdf">矢量PDF</a> · <a href="{s}.svg">SVG</a><img src="{s}.png" alt="{t}"></section>' for s,t in zip(stems,titles))
    (OUT/'图集预览.html').write_text('<!doctype html><meta charset="utf-8"><title>完整重绘图集</title><style>body{max-width:1100px;margin:24px auto;font-family:Arial,sans-serif;background:#f1f1f1;color:#202020}section{background:white;margin:24px 0;padding:18px}img{width:100%;display:block}h2{font-size:20px}a{color:#004488}</style><h1>论文完整图集 · Tol High Contrast</h1><p>按正文图号排列。区间、样本量与数据限制见配套说明。</p>'+cards,encoding='utf-8')
    source=OUT/'source_data';source.mkdir(exist_ok=True)
    for name in ['t1_formal_main.csv','t1_per_key.csv','t1_mechanism_firstround.csv',
                 't1_failure_modes.csv','t1_round_controls.csv','t2_transfer_p2.csv',
                 't2_expanded_temporal.csv','t3_capture_gradient.csv','t1_ncw_aware_capture.csv',
                 't1_modern_scaled.csv','t1_bgf_baseline.csv','t1_native_l1_holdout_flat.csv','t1_t_sensitivity.csv']:
        shutil.copyfile(ROOT/'data'/name,source/name)

if __name__=='__main__':
    paths=list((ROOT/'data').glob('*.csv'))
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    design();failure_modes();controls();transfer();modern();sensitivity();publish()
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    assert before==after
    (OUT/'data_integrity.json').write_text(json.dumps({'csv_sha256':after,'unchanged':True},indent=2),encoding='utf-8')
    print(OUT)
