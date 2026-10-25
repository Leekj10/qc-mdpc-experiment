# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# Bar comparisons -> BarComparison -> param inherit (categorical separation).
# Parameter sweep -> LineTrend/plot_sweep.py -> param inherit (markers + lines).
# Forest intervals -> cross-type inherit -> param inherit (full archived CIs).
# User's TNR, Tol palette, exact IEEE widths and vector exports override CNS defaults.
# Domain tables contain paired key counts, not the assets' biological replicates.
"""Rebuild publication figure candidates without modifying manuscript or inputs."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Patch
from matplotlib.ticker import LogLocator, NullLocator
import numpy as np
import fitz
from PIL import Image, ImageOps, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / 'data'
OUT = HERE / 'figures'
OUT.mkdir(exist_ok=True)
SOURCE = HERE / 'source_data'
SOURCE.mkdir(exist_ok=True)
INK, BLUE, GOLD, RED, GREY = '#222222', '#004488', '#DDAA33', '#BB5566', '#777777'
CONTROL = '#888888'
CONDS = ['RAND', 'TYPE-I', 'NCW-shallow']
mpl.rcParams.update({
    'font.family': 'Times New Roman', 'font.size': 8,
    'axes.titlesize': 9, 'axes.labelsize': 8, 'xtick.labelsize': 8,
    'ytick.labelsize': 8, 'legend.fontsize': 8,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.linewidth': .65, 'xtick.major.width': .65, 'ytick.major.width': .65,
    'xtick.direction': 'out', 'ytick.direction': 'out',
    'legend.frameon': False, 'pdf.fonttype': 42, 'ps.fonttype': 42,
    'svg.fonttype': 'none', 'savefig.dpi': 300,
    'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': INK,
    'mathtext.fontset': 'custom', 'mathtext.rm': 'Times New Roman',
    'mathtext.it': 'Times New Roman:italic', 'mathtext.bf': 'Times New Roman:bold',
})
USED = {}
QA = {}
CAPTIONS = {}


def read(name):
    path = DATA / name
    USED[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    shutil.copy2(path, SOURCE / name)
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def pick(rows, **criteria):
    found = [r for r in rows if all(r[k] == v for k, v in criteria.items())]
    assert len(found) == 1, criteria
    return found[0]


def title(ax, letter, text):
    ax.set_title(f'({letter})  {text}', loc='left', pad=8, fontweight='bold')


def grid(ax, axis='y'):
    ax.set_axisbelow(True)
    ax.grid(axis=axis, which='major', color='#DDDDDD', linewidth=.45)
    ax.tick_params(length=3, pad=3)


def labelbars(ax, bars, fmt='.2f', offset=3):
    for b in bars:
        ax.annotate(format(b.get_height(), fmt),
                    (b.get_x() + b.get_width()/2, b.get_height()),
                    xytext=(0, offset), textcoords='offset points',
                    ha='center', va='bottom', fontsize=8)


def save(fig, name, caption):
    # Preserve the exact artboard width. Cropping with bbox=tight changes IEEE size.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    outside = []
    for txt in fig.findobj(mpl.text.Text):
        if not txt.get_visible() or not txt.get_text():
            continue
        box = txt.get_window_extent(renderer)
        if not fig.bbox.padded(1).contains(box.x0, box.y0) or not fig.bbox.padded(1).contains(box.x1, box.y1):
            # Log axes instantiate off-screen ticks which are clipped by the axis.
            if txt in sum([list(a.get_xticklabels()) + list(a.get_yticklabels()) for a in fig.axes], []):
                continue
            outside.append(txt.get_text())
    assert not outside, (name, outside)
    for ext in ('pdf', 'svg', 'png'):
        fig.savefig(OUT / f'{name}.{ext}', dpi=300, facecolor='white')
    CAPTIONS[name] = caption
    plt.close(fig)


def study_design():
    fig, ax = plt.subplots(figsize=(7.16, 1.65))
    fig.subplots_adjust(left=.025, right=.98, top=.94, bottom=.07)
    ax.set(xlim=(0, 10), ylim=(-.15, 2.3)); ax.axis('off')
    def box(x, y, w, h, text, color=INK, fill='white'):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=color, lw=1))
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=9)
    def arrow(x, y, endx, endy):
        ax.annotate('', xy=(endx, endy), xytext=(x, y),
                    arrowprops={'arrowstyle': '->', 'lw': 1, 'color': INK})
    ax.text(.1, 2.1, '(a)  Paired instances', fontweight='bold', fontsize=9)
    ax.text(3.4, 2.1, '(b)  One-round intervention', fontweight='bold', fontsize=9)
    ax.text(8.1, 2.1, '(c)  Key-level inference', fontweight='bold', fontsize=9)
    box(.05, .49, 1.8, 1.0, 'Same key H\nSame error e\nSame syndrome s')
    box(3.4, 1.1, 1.25, .58, 'C0: +0', CONTROL)
    box(3.4, .2, 1.25, .58, 'FRO-2: +2', GOLD, '#FFF5D9')
    ax.text(4.03, 1.85, 'Round 1', ha='center')
    box(5.4, 1.1, 1.7, .58, 'C0 schedule', CONTROL)
    box(5.4, .2, 1.7, .58, 'C0 schedule', CONTROL)
    ax.text(6.25, 1.85, 'Rounds 2 onward', ha='center')
    arrow(1.9, .99, 3.35, 1.4); arrow(1.9, .99, 3.35, .5)
    arrow(4.68, 1.39, 5.35, 1.39); arrow(4.68, .49, 5.35, .49)
    box(8.15, .59, 1.7, .8, 'Paired outcomes\nResample keys')
    arrow(7.13, 1.39, 8.1, 1.0); arrow(7.13, .49, 8.1, 1.0)
    save(fig, 'fig1_study_design', 'Paired design. Each schedule decodes the same (H,e,s). FRO-2 adds two only in round one; subsequent rounds use the baseline schedule. Outcomes are aggregated by key, which is the unit resampled for uncertainty.')


def primary():
    agg, keys = read('t1_formal_main.csv'), read('t1_per_key.csv')
    fig = plt.figure(figsize=(7.16, 4.15))
    gs = fig.add_gridspec(2, 6, left=.075, right=.985, bottom=.13, top=.90,
                          hspace=.72, wspace=1.1, height_ratios=[1, 1.12])
    a, b = fig.add_subplot(gs[0, :3]), fig.add_subplot(gs[0, 3:])
    x = np.arange(3)
    for arm, off, color, hatch, label in [('c0', -.19, CONTROL, '', 'C0'), ('fro2', .19, GOLD, '//', 'FRO-2')]:
        vals = [float(pick(agg, condition=c)[f'{arm}_dfr'])*10000 for c in CONDS]
        bars = a.bar(x+off, vals, width=.34, color=color, edgecolor=INK,
                     linewidth=.6, hatch=hatch, label=label)
        labelbars(a, bars, '.1f')
    a.set(xticks=x, xticklabels=CONDS, ylabel='Failures per 10,000 decodes', ylim=(0, 16.5))
    title(a, 'a', 'Absolute failure rate'); grid(a)
    a.legend(ncol=2, loc='upper left', fontsize=8, handlelength=1.3, borderaxespad=0)
    rr = np.array([float(pick(agg, condition=c)['rr']) for c in CONDS])
    lo = np.array([float(pick(agg, condition=c)['rr_lo']) for c in CONDS])
    hi = np.array([float(pick(agg, condition=c)['rr_hi']) for c in CONDS])
    bars = b.bar(x, rr, width=.52, color=GOLD, edgecolor=INK, linewidth=.6,
                 yerr=[rr-lo, hi-rr], capsize=3, error_kw={'lw': 1, 'capthick': 1})
    for xx, v, upper in zip(x, rr, hi):
        b.text(xx, upper+.2, f'{v:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    b.axhline(1, ls='--', lw=.9, color=INK)
    b.set(xticks=x, xticklabels=CONDS, ylabel='Risk ratio C0 / FRO-2', ylim=(0, 8.6), yticks=[0, 2, 4, 6, 8])
    title(b, 'b', 'Relative effect + 95% CI'); grid(b)
    summary = {}
    for i, c in enumerate(CONDS):
        ax = fig.add_subplot(gs[1, 2*i:2*i+2])
        rows = [r for r in keys if r['condition'] == c]
        counts = Counter(int(r['c0_failures'])-int(r['fro2_failures']) for r in rows)
        assert sum(counts.values()) == int(pick(agg, condition=c)['n_keys'])
        for arm in ('c0', 'fro2'):
            assert sum(int(r[f'{arm}_failures']) for r in rows) == int(pick(agg, condition=c)[f'{arm}_failures'])
        for delta, count in sorted(counts.items()):
            ax.bar(delta, count, width=.82, color=GOLD if delta > 0 else RED if delta < 0 else GREY,
                   edgecolor=INK, linewidth=.5, hatch='//' if delta < 0 else '')
        good, bad, tied = sum(n for d, n in counts.items() if d > 0), sum(n for d, n in counts.items() if d < 0), counts[0]
        summary[c] = {'keys': len(rows), 'improved': good, 'worsened': bad, 'tied': tied}
        ax.set(xlim=(-2.8, 10.7), ylim=(0, 33), xticks=[-2, 0, 2, 4, 6, 8, 10], yticks=[0, 10, 20, 30], xlabel='Failures avoided per key')
        title(ax, chr(99+i), f'{c}  (n = {len(rows)})')
        ax.axvline(0, color=GREY, lw=.7, ls=':'); grid(ax)
        if i == 0: ax.set_ylabel('Number of keys')
        ax.text(.97, .96, f'{good} improved\n{bad} worsened\n{tied} tied', transform=ax.transAxes, ha='right', va='top', fontsize=8)
    fig.text(.075, .025, 'Paired formal pool: 278 key-condition units; 3,000 decodes per key and schedule.', fontsize=8)
    QA['primary_key_counts'] = summary
    save(fig, 'fig2_main_results', 'FRO-2 lowers the observed primary failure rate across all three sampling conditions. (a) Absolute failures per 10,000 decodes; these bars are point estimates. (b) C0/FRO-2 risk ratios with archived 95% key-cluster bootstrap intervals. (c-e) Distribution of paired failures avoided per key, including all 278 key-condition units and negative and zero differences. Each key has 3,000 decodes per schedule. Improved/worsened counts denote observed differences, not individual-key significance tests.')


def mechanism():
    rows = read('t1_mechanism_firstround.csv')
    fig, axs = plt.subplots(1, 3, figsize=(7.16, 2.2))
    fig.subplots_adjust(left=.07, right=.985, top=.77, bottom=.24, wspace=.4)
    metrics = [('mean_incorrect_first', 'Incorrect flips', 11),
               ('mean_correct_first', 'Correct flips', 28),
               ('mean_residual_r1', 'Residual errors', 105)]
    for i, (ax, (key, heading, ylim)) in enumerate(zip(axs, metrics)):
        x = np.arange(3)
        for arm, off, color, hatch in [('C0', -.19, CONTROL, ''), ('FRO-2', .19, GOLD, '//')]:
            v = [float(pick(rows, condition=c, arm=arm)[key]) for c in CONDS]
            bars = ax.bar(x+off, v, width=.34, color=color, edgecolor=INK, linewidth=.55, hatch=hatch)
            labelbars(ax, bars, '.1f', 2)
        for j, c in enumerate(CONDS):
            ratio = float(pick(rows, condition=c, arm='FRO-2')[key])/float(pick(rows, condition=c, arm='C0')[key])
            ax.text(j, ylim*.93, f'{ratio:.2f}x', ha='center', fontsize=8, color=INK)
        ax.set(xticks=x, xticklabels=['RAND', 'TYPE-I', 'NCW'], ylim=(0, ylim))
        title(ax, chr(97+i), heading); grid(ax)
        if i == 0: ax.set_ylabel('Mean positions per decode')
    fig.legend(handles=[Patch(fc=CONTROL, ec=INK, linewidth=.55, label='C0'), Patch(fc=GOLD, ec=INK, hatch='//', label='FRO-2')],
               loc='upper center', bbox_to_anchor=(.52, 1.01), ncol=2, handlelength=1.3)
    fig.text(.07, .035, 'Ratios above bars: FRO-2 / C0.  Each arm: 20 keys x 1,000 decodes per condition.', fontsize=8)
    save(fig, 'fig3_mechanism', 'FRO-2 suppresses incorrect flips more strongly than correct flips, while leaving more residual errors after round one. Bars show archived absolute means; labels above each pair give FRO-2/C0. NCW denotes NCW-shallow. Each condition uses 20 keys and 1,000 errors per key. Aggregate means alone do not provide intervals; none are fabricated. Panels use separate vertical scales, explicitly labelled in their ticks.')


def temporal():
    primary = read('t1_round_controls.csv')
    expanded = read('t2_expanded_temporal.csv')
    fig, axs = plt.subplots(1, 3, figsize=(7.16, 4.4), sharey=True)
    # Symmetric artboard: axes span .14-.875 (centre .5075) so the plot block
    # sits on the canvas centre instead of right of it once the figure is
    # centred in a one-column text block.
    fig.subplots_adjust(left=.14, right=.875, bottom=.16, top=.86, wspace=.16)
    prim = ['FRO-2', 'R2one', 'FRONEG', 'R2plus']
    extra = ['FRO-1', 'FRO-2', 'FRO-3', 'R2-2', 'UNIFORM-2']
    labels = ['Round 1: +2', 'Round 2: +2', 'Round 1: -1', 'Rounds 2+: +2',
              'Round 1: +1', 'Round 1: +2', 'Round 1: +3', 'Round 2: +2', 'All rounds: +2']
    ys = [10, 9, 8, 7, 4.4, 3.4, 2.4, 1.4, .4]
    for i, (ax, c) in enumerate(zip(axs, CONDS)):
        ax.axvspan(.005, 1, color='#F9EDF0', zorder=0)
        ax.axvline(1, ls='--', color=INK, lw=.85)
        ax.axhline(5.65, color=GREY, lw=.7)
        for arm, y in zip(prim, ys[:4]):
            r = pick(primary, condition=c, arm=arm)
            v, lo, hi = [float(r[k]) for k in ('rr_vs_c0', 'rr_lo', 'rr_hi')]
            ax.errorbar(v, y, xerr=[[v-lo], [hi-v]], fmt='D', color=CONTROL,
                        ms=4.3, capsize=2.2, elinewidth=1.05, markeredgewidth=.7)
        for arm, y in zip(extra, ys[4:]):
            for point, offset, color, marker, fill in [('P2', .15, BLUE, 'o', BLUE), ('P3', -.15, RED, 's', 'white')]:
                r = pick(expanded, condition=c, point=point, decoder=arm)
                v, lo, hi = [float(r[k]) for k in ('rr_vs_c0', 'rr_lo', 'rr_hi')]
                ax.errorbar(v, y+offset, xerr=[[v-lo], [hi-v]], fmt=marker, color=color,
                            mfc=fill, ms=4, capsize=2, elinewidth=1, markeredgewidth=.8)
        ax.set(xscale='log', xlim=(.005, 20), ylim=(-.3, 11.35), yticks=ys,
               yticklabels=labels, xticks=[.01, .1, 1, 10], xticklabels=['0.01', '0.1', '1', '10'])
        ax.xaxis.set_minor_locator(NullLocator())
        title(ax, chr(97+i), c)
        ax.text(.025, 10.95, 'Primary point', transform=ax.get_yaxis_transform(), va='center', fontsize=8, fontweight='bold')
        ax.text(.025, 6.15, 'Transfer points', transform=ax.get_yaxis_transform(), va='center', fontsize=8, fontweight='bold')
        grid(ax, 'x')
    handles = [Line2D([], [], marker='D', color=CONTROL, ls='', label="P1'"),
               Line2D([], [], marker='o', color=BLUE, ls='', label='P2'),
               Line2D([], [], marker='s', color=RED, mfc='white', ls='', label='P3')]
    fig.legend(handles=handles, loc='upper center', ncol=3, bbox_to_anchor=(.5075, 1))
    fig.text(.5075, .065, 'Risk ratio C0 / intervention (95% archived intervals)', ha='center', fontsize=9)
    fig.text(.5075, .02, 'Below 1: more failures     |     Above 1: fewer failures', ha='center', fontsize=8)
    points = {r['point']: (r['r'], r['d'], r['t']) for r in expanded}
    save(fig, 'fig4_temporal_dissociation', 'The effect depends on round and persistence. Upper rows show primary-point round controls with archived 95% key-cluster intervals. Lower rows show P2 (filled circles) and P3 (open squares), each with 50 keys and 1,000 errors per key and schedule, and archived 95% intervals. Shading identifies risk ratios below one, not statistical significance. Primary R2one and expanded R2-2 are separate campaigns. Primary point: (4801,45,92); P2: (' + ','.join(points['P2']) + '); P3: (' + ','.join(points['P3']) + ').')


def scope():
    transfer, capture = read('t2_transfer_p2.csv'), read('t3_capture_gradient.csv')
    ncw = read('t1_ncw_aware_capture.csv')
    fig = plt.figure(figsize=(7.16, 2.8))
    gs = fig.add_gridspec(1, 3, left=.105, right=.985, bottom=.25, top=.79,
                          width_ratios=[.92, 1.3, 1], wspace=.6)
    a, b, cax = [fig.add_subplot(gs[0, i]) for i in range(3)]
    for j, cond in enumerate(CONDS):
        r = pick(transfer, condition=cond)
        v, lo, hi = [float(r[k]) for k in ('rr', 'rr_lo', 'rr_hi')]
        a.barh(2-j, v, height=.5, color=GOLD, edgecolor=INK, lw=.5,
               xerr=[[v-lo], [hi-v]], capsize=2, error_kw={'lw': 1})
        a.text(v+.08, 2-j+.27, f'{v:.2f}', fontsize=8)
    a.axvline(1, color=INK, lw=.8, ls='--')
    a.set(yticks=[2, 1, 0], yticklabels=['RAND', 'TYPE-I', 'NCW'], xlim=(0, 4.7),
          ylim=(-.6, 2.7), xticks=[0, 2, 4], xlabel='C0 / FRO-2 (95% CI)')
    title(a, 'a', 'Independent P2'); grid(a, 'x')
    for label, source, key, color, marker, offset, filled in [
        ('C0', capture, 'c0_dfr', CONTROL, 'o', -1.6, False),
        ('FRO-2', capture, 'fro2_dfr', GOLD, 's', 0, True),
        ('NCW-aware', ncw, 'ncw_exact_recovery_dfr', RED, '^', 1.6, True)]:
        xs = np.array([int(r['kappa']) for r in source])
        b.scatter(xs+offset, [float(r[key]) for r in source], c=color if filled else 'white',
                  edgecolors=INK if color == GOLD else color, marker=marker, s=26, linewidths=.8, zorder=3, label=label)
    b.set(yscale='log', ylim=(5e-5, 1.9), xlim=(-5, 65), xticks=[0, 12, 46, 60],
          yticks=[1e-4, 1e-2, 1], yticklabels=['0.0001', '0.01', '1'],
          xlabel='Constructed overlap kappa', ylabel='Absolute DFR')
    b.yaxis.set_minor_locator(NullLocator()); title(b, 'b', 'Reliability boundary'); grid(b)
    for j, r in enumerate(capture):
        if int(r['kappa']) == 60:
            cax.text(.5, 0, 'Both saturated\nunresolved', transform=cax.get_yaxis_transform(),
                     ha='center', va='center', fontsize=8)
            continue
        v, lo, hi = [float(r[k]) for k in ('rr', 'rr_lo', 'rr_hi')]
        cax.errorbar(v, 3-j, xerr=[[v-lo], [hi-v]], fmt='s', color=GOLD,
                     mec=INK, mew=.6, ms=4.5, capsize=2.5, elinewidth=1.2)
        cax.text(.97, 3-j+.27, f'{v:.3g}', transform=cax.get_yaxis_transform(), ha='right', fontsize=8)
    cax.axvline(1, color=INK, lw=.8, ls='--')
    cax.set(xscale='log', xlim=(.65, 24), ylim=(-.5, 3.65), yticks=[3, 2, 1, 0],
            yticklabels=['0', '12', '46', '60'], xticks=[1, 5, 20], xticklabels=['1', '5', '20'],
            xlabel='C0 / FRO-2 (95% CI)', ylabel='Overlap kappa')
    cax.xaxis.set_minor_locator(NullLocator()); title(cax, 'c', 'Relative effect'); grid(cax, 'x')
    fig.legend(handles=b.get_legend_handles_labels()[0], labels=b.get_legend_handles_labels()[1],
               loc='upper center', bbox_to_anchor=(.61, 1.01), ncol=3, handletextpad=.35, columnspacing=1)
    fig.text(.105, .035, 'P2: 30 keys x 3,000 decodes / condition.  Boundary: 40,000 decodes / construction.', fontsize=8)
    save(fig, 'fig5_scope_and_boundary', 'Benefits transfer to an independent P2 campaign but disappear or reverse under the tested high-overlap constructions. (a) Independent P2 risk ratio, with archived 95% intervals. (b) Absolute DFR at four tested overlaps; marker offsets only prevent occlusion. NCW-aware uses exact-recovery failure, not zero-syndrome failure. (c) C0/FRO-2 and archived 95% intervals. At overlap 60 both methods fail on all trials; no resolved population ranking or degenerate [1,1] interval is plotted. The overlap axis uses actual numeric spacing; no unmeasured transition is interpolated.')


def window():
    rows = read('t1_offset_scan_p1p.csv')
    archive = HERE / 'previous_window_design'
    archive.mkdir(exist_ok=True)
    for ext in ('pdf', 'svg', 'png'):
        old = OUT / f'fig6_threshold_window.{ext}'
        if old.exists() and not (archive / old.name).exists():
            shutil.copy2(old, archive / old.name)
    offsets = [-2, -1, 0, 1, 2, 3]
    arms = ['FRONEG2', 'FRONEG', 'C0', 'FRO-1', 'FRO-2', 'FRO-3']
    fig = plt.figure(figsize=(7.16, 4.05))
    gs = fig.add_gridspec(2, 3, left=.085, right=.985, bottom=.14, top=.88,
                          hspace=.8, wspace=.38, height_ratios=[1, 1.2])
    overview = fig.add_subplot(gs[0, :])
    for i, (cond, col, marker, ls) in enumerate(zip(CONDS, [BLUE, RED, GOLD], ['o', 's', '^'], ['-', '--', ':'])):
        selected = [pick(rows, condition=cond, arm=arm) for arm in arms]
        vals = [float(r['dfr']) for r in selected]
        overview.plot(offsets, vals, color=col, marker=marker, ls=ls, lw=1.2, ms=4.3,
                    mec=INK, mew=.45, label=cond)
        ax = fig.add_subplot(gs[1, i])
        positive = selected[3:]
        rr = [float(r['rr_vs_c0']) for r in positive]
        ax.axvspan(1.83, 2.17, color='#FFF5D9', zorder=0)
        ax.plot([1, 2, 3], rr, color=col, marker=marker, ls=ls, lw=1.2,
                ms=4.5, mec=INK, mew=.5)
        for off, r in zip([1, 2, 3], positive):
            v, lo, hi = [float(r[k]) for k in ('rr_vs_c0', 'rr_lo', 'rr_hi')]
            ax.errorbar(off, v, yerr=[[v-lo], [hi-v]], fmt='none', color=col, capsize=3, lw=1)
            ax.text(off, hi+.2, f'{v:.2f}', ha='center', va='bottom', fontsize=8)
        ax.axhline(1, color=GREY, ls='--', lw=.8)
        ax.set(xlim=(.65, 3.35), ylim=(0, 8.5), xticks=[1, 2, 3], xticklabels=['+1', '+2', '+3'],
               yticks=[0, 2, 4, 6, 8], xlabel='Round-one offset')
        if i == 0:
            ax.set_ylabel('Risk ratio C0 / variant')
        title(ax, chr(98+i), cond); grid(ax)
    overview.set(yscale='log', xticks=offsets, xticklabels=['-2', '-1', '0', '+1', '+2', '+3'],
                 ylabel='Absolute DFR', xlim=(-2.2, 3.2), ylim=(7e-5, 1),
                 yticks=[1e-4, .01, 1], yticklabels=['0.0001', '0.01', '1'])
    overview.yaxis.set_minor_locator(NullLocator())
    overview.axvline(0, color=GREY, ls=':', lw=.8); grid(overview)
    title(overview, 'a', 'Full offset range: absolute failure rate')
    fig.legend(*overview.get_legend_handles_labels(), loc='upper center', ncol=3, bbox_to_anchor=(.53, 1.01))
    fig.text(.53, .025, 'Positive offsets: common linear scale; 95% key-cluster intervals. Shading marks +2.', ha='center', fontsize=8)
    save(fig, 'fig6_threshold_window', 'The first round has an asymmetric two-sided response at the primary point. (a) Full six-offset absolute DFR on a logarithmic scale. (b-d) All positive offsets, separated by sampling condition on identical zero-based linear risk-ratio axes, with archived 95% key-cluster intervals. Labels give point estimates and the pale band identifies +2, not statistical superiority. Intervals overlap; marginal intervals do not establish that +2 beats +1 or +3. Connecting segments only guide the eye between measured integer offsets. Negative-offset ratio intervals remain in the complete numeric scan table; the full negative-offset failure rates remain in panel (a).')


def failure_modes():
    rows, totals = read('t1_failure_modes.csv'), read('t1_formal_main.csv')
    fig, axs = plt.subplots(1, 3, figsize=(7.16, 2.1), sharex=True)
    fig.subplots_adjust(left=.075, right=.985, top=.77, bottom=.28, wspace=.35)
    modes = [('stagnation', CONTROL, '', 'Stagnation'), ('early_misflip', RED, '//', 'Early misflip'), ('other', GOLD, '..', 'Other')]
    for i, (ax, c) in enumerate(zip(axs, CONDS)):
        total = pick(totals, condition=c)
        for y, arm, prefix in [(1, 'C0', 'c0'), (0, 'FRO-2', 'fro2')]:
            selected = [r for r in rows if r['condition'] == c and r['arm'] == arm]
            assert sum(int(r['count']) for r in selected) == int(total[f'{prefix}_failures'])
            assert all(int(r['count']) == 0 for r in selected if r['mode'] in ('divergence', 'period2'))
            left = 0
            for mode, color, hatch, _ in modes:
                v = int(pick(selected, mode=mode)['count']) / int(total[f'{prefix}_trials']) * 10000
                ax.barh(y, v, left=left, height=.48, color=color, hatch=hatch, edgecolor='white', lw=.5)
                left += v
            ax.text(left+.15, y, f'{left:.2f}', va='center', fontsize=8)
        ax.set(yticks=[1, 0], yticklabels=['C0', 'FRO-2'], xlim=(0, 15), ylim=(-.6, 1.6), xticks=[0, 5, 10, 15])
        title(ax, chr(97+i), c); grid(ax, 'x')
    fig.legend(handles=[Patch(fc=col, hatch=hatch, label=label) for _, col, hatch, label in modes],
               loc='upper center', ncol=3, bbox_to_anchor=(.53, 1.02))
    fig.text(.53, .07, 'Failure-mode events per 10,000 total decodes', ha='center', fontsize=9)
    save(fig, 'supp_failure_modes', 'Absolute failure-mode burden declines with FRO-2. Stacks are normalized by all decodes in each formal condition, not only failures. Segment categories use the archived preregistered quarter-budget classifier. Divergence and period-2 counts are zero in these data. All five categories were checked; zero categories have no visible area. Totals equal the formal failure counts. This campaign is distinct from the 20-key first-round-mean campaign in Fig.3.')


def primary_table():
    rows = read('t1_formal_main.csv')
    headers = ['Condition', 'Keys', 'C0 failures / trials', 'FRO-2 failures / trials', 'RR [95% CI]', 'Holm p']
    values = []
    texrows = []
    for c in CONDS:
        r = pick(rows, condition=c)
        ci = f"{float(r['rr']):.2f} [{float(r['rr_lo']):.2f}, {float(r['rr_hi']):.2f}]"
        vals = [c, r['n_keys'], f"{int(r['c0_failures']):,} / {int(r['c0_trials']):,}",
                f"{int(r['fro2_failures']):,} / {int(r['fro2_trials']):,}", ci, f"{float(r['holm_sign_p']):.3g}"]
        values.append(vals)
        texrows.append(' & '.join(vals) + r' \\')
    fig, ax = plt.subplots(figsize=(7.16, 1.2))
    fig.subplots_adjust(left=.025, right=.985, bottom=.20, top=.94)
    ax.axis('off')
    table = ax.table(cellText=values, colLabels=headers, cellLoc='center',
                     colWidths=[.14, .07, .205, .215, .24, .13], bbox=[0, .04, 1, .96])
    table.auto_set_font_size(False); table.set_fontsize(8)
    for (row, col), cell in table.get_celld().items():
        cell.visible_edges = ''
        cell.PAD = .08
        if row == 0:
            cell.visible_edges = 'TB'; cell.set_linewidth(.8)
            cell.get_text().set_fontweight('bold')
        if row == 3:
            cell.visible_edges = 'B'; cell.set_linewidth(.8)
    fig.text(.025, .055, 'RR = C0 / FRO-2.  95% key-cluster intervals; Holm-adjusted two-sided key sign tests.', fontsize=8)
    save(fig, 'table1_primary_summary', 'Compact primary table. Counts and denominators remain together; exact absolute rates are obtained by division and visualized in Fig.2a. RR intervals and Holm-adjusted key sign-test p-values use the archived formal analysis. The table carries exact inference; the figure emphasizes the effect and heterogeneity.')
    tex = '\\begin{tabular}{l r r r c r}\n\\toprule\n' + ' & '.join(headers) + r' \\' + '\n\\midrule\n' + '\n'.join(texrows) + '\n\\bottomrule\n\\end{tabular}\n'
    (HERE / 'table1_primary_summary.tex').write_text(tex, encoding='utf-8')


def manuscript_tables():
    """Retain every body-table cell, including denominators and nominal tests."""
    source = (ROOT / 'v3/en/main.tex').read_text(encoding='utf-8')
    QA['manuscript_sha256'] = hashlib.sha256((ROOT / 'v3/en/main.tex').read_bytes()).hexdigest()
    blocks = re.findall(r'\\begin\{table\*\}(.*?)\\end\{table\*\}', source, re.S)
    assert len(blocks) == 5
    specs = [
        ('main', 'Primary comparison', ['Condition', 'Keys', 'C0\nfailures', 'C0\nDFR', 'FRO-2\nfailures', 'FRO-2\nDFR', 'RR [95% CI]', 'Holm p'],
         [.14, .055, .085, .10, .085, .10, .245, .105], 1.65,
         'Primary point (4801,45,92). RR = C0 / FRO-2; 95% key-cluster CI; Holm-adjusted key sign test.'),
        ('offset_scan', 'First-round offset scan', ['Offset', 'RAND', 'TYPE-I', 'NCW-shallow'],
         [.10, .30, .30, .30], 2.1,
         'Entries: RR [95% key-cluster CI]. RR > 1 favours the offset. Primary point (4801,45,92).'),
        ('temporal', 'Temporal confirmation', ['Schedule', 'RAND', 'TYPE-I', 'NCW', 'RAND', 'TYPE-I', 'NCW'],
         [.17, .1383, .1383, .1384, .1383, .1383, .1384], 2.65,
         'C0 row: absolute DFR. Other rows: RR C0 / schedule. 50 keys x 1,000 errors per cell.\nBold: maximum RR in each column, including ties. NCW = NCW-shallow.'),
        ('added', 'Production-scale measurements', ['Setting', 'Variant', 'Failures', 'Trials', 'RR [95% CI]', 'p'],
         [.255, .215, .075, .105, .255, .095], 4.5,
         'RR = C0 / variant. p: nominal exact McNemar (comparators vs FRO-2; tangent BGF vs C0).\nDynamic hold-out: 3 conditions x 3 offsets; 1,000,000 trials per cell, not one pooled population.\nZero-event upper bounds (3/N): 9.38e-5 per 32,000; 3e-6 per hold-out cell. Zero failures do not imply zero risk.'),
        ('modern', 'Modern-decoder comparison', ['Condition', 'C0', 'FRO-2', 'BIKE-Flip', 'BGF-C3', 'p\nvs FRO-2', 'RR [95% CI]\nC0 / BGF'],
         [.14, .12, .12, .12, .12, .12, .26], 1.65,
         'Primary point (4801,45,92). Method columns: DFR. p: BIKE-Flip vs FRO-2; RR: C0 / BGF-C3.\nPaired static semantics; 20-round budget. Tests are nominal, not key-clustered or multiplicity-adjusted.'),
    ]

    def text_cell(cell):
        cell = cell.strip().replace('{,}', ',')
        cell = re.sub(r'\\multirow\{\d+\}\{\*\}\{([^{}]*)\}', r'\1', cell)
        cell = re.sub(r'\\textbf\{([^{}]*)\}', r'\1', cell)
        cell = re.sub(r'([0-9.]+)\\times10\^\{(-?\d+)\}', r'\1e\2', cell)
        return cell.replace('$', '').replace('\\%', '%').strip()

    coverage = []
    for index, (block, spec) in enumerate(zip(blocks, specs), 1):
        label, heading, headers, widths, height, note = spec
        assert f'\\label{{tab:{label}}}' in block
        raw = re.search(r'\\begin\{tabular\}\{[^\n]*\}\s*(.*?)\\end\{tabular\}', block, re.S).group(1)
        body = raw.split('\\midrule', 1)[1].split('\\bottomrule', 1)[0]
        segments = re.split(r'\\\\', body)
        cells, bold, separators = [], [], []
        for segment in segments:
            if '\\midrule' in segment and cells:
                separators.append(len(cells))
            segment = segment.replace('\\midrule', '').strip()
            if not segment:
                continue
            row = segment.split('&')
            assert len(row) == len(headers), (label, row)
            bold.append(['\\textbf' in cell for cell in row])
            cells.append([text_cell(cell) for cell in row])
        assert len(cells) == [3, 5, 6, 12, 3][index-1], (label, len(cells))
        if label == 'offset_scan':
            archived_hi = float(pick(read('t1_offset_scan_p1p.csv'), condition='NCW-shallow', arm='FRONEG')['rr_hi'])
            QA['table2_ci_display_correction'] = {'manuscript': cells[3][3], 'archived_upper': archived_hi}
            old_cell = cells[3][3]
            cells[3][3] = old_cell.replace('0.120]', f'{archived_hi:.3f}]')
            block = block.replace(old_cell, cells[3][3])
        if label == 'added':
            cells[0][0] = 'Raised weight\n(12323,71,172)'
            cells[3][0] = 'Comparators\n(12323,71,172)'
            cells[6][0] = 'Production weight\n(12323,71,134)'
            cells[8][0] = 'CPA-128\n(10163,71,140)'
            cells[11][0] = 'Dynamic hold-out\n(12323,71,134)'
            cells[3][1] = 'BIKE-Flip, published'
            cells[4][1] = 'BIKE-Flip, derived'
            archived_p = {r['label']: float(r['value']) for r in read('t1_fair_l1.csv')}['fair-L1 BGF-tangent vs C0 McNemar p']
            QA['table4_p_correction'] = {'manuscript': cells[5][5], 'archived': archived_p,
                                         'candidate': f'{archived_p:.3g}'}
            cells[5][5] = f'{archived_p:.3g}'
            block = block.replace('& 0.013 \\\\', '& ' + f'{archived_p:.3g}' + ' \\\\')
        if label == 'modern':
            bgf = read('t1_bgf_baseline.csv')
            for row in cells:
                r = pick(bgf, condition=row[0], arm='BGF-C3')
                old = row[6]
                row[6] = f"{float(r['rr_vs_c0']):.3f} [{float(r['rr_lo']):.3f}, {float(r['rr_hi']):.3f}]"
                block = block.replace('$' + old + '$', '$' + row[6] + '$')
            block = block.replace('& RR \\\\', '& RR [95\\% CI] \\\\')
        fig, ax = plt.subplots(figsize=(7.16, height))
        fig.subplots_adjust(left=.025, right=.985, top=.97, bottom=.03)
        ax.axis('off')
        if label == 'temporal':
            ax.text(.3775, .79, 'P2 (3001,37,66)', ha='center', fontweight='bold', fontsize=8)
            ax.text(.7925, .79, 'P3 (4001,41,82)', ha='center', fontweight='bold', fontsize=8)
        ax.text(0, .96, f'Table {index}.  {heading}', fontsize=9, fontweight='bold', va='top')
        top = .74 if label == 'temporal' else .83
        bottom = .22 if label in ('modern', 'temporal') else .17 if label != 'added' else .14
        table = ax.table(cellText=cells, colLabels=headers, cellLoc='center',
                         colWidths=widths, bbox=[0, bottom, 1, top-bottom])
        table.auto_set_font_size(False); table.set_fontsize(8)
        for (r, c), cell in table.get_celld().items():
            cell.visible_edges = ''; cell.PAD = .04
            if r == 0:
                cell.visible_edges = 'TB'; cell.set_linewidth(.8)
                cell.get_text().set_fontweight('bold')
                cell.get_text().set_color(INK)
            elif bold[r-1][c]:
                cell.get_text().set_fontweight('bold')
            if r == len(cells):
                cell.visible_edges += 'B'; cell.set_linewidth(.8)
            if r in separators:
                cell.visible_edges += 'B'; cell.set_linewidth(.45)
            if c == 0 and r > 0:
                cell.get_text().set_ha('left')
        if label == 'added':
            row_height = (top-bottom)/(len(cells)+1)
            for start, count in [(0, 3), (3, 3), (6, 2), (8, 3), (11, 1)]:
                label_text = cells[start][0] if count > 1 else 'Hold-out, dynamic'
                table[start+1, 0].get_text().set_text('')
                y = top - row_height*(1 + start + count/2)
                ax.text(.01, y, label_text, fontsize=8, ha='left', va='center', linespacing=1.3)
        ax.text(0, .01, note, fontsize=8, va='bottom', linespacing=1.45)
        name = f'table{index}_body_{label}'
        save(fig, name, f'Full manuscript Table {index}: {heading}. All {len(cells)} data rows and all {len(headers)} columns are retained. ' + note.replace('\n', ' '))
        (HERE / f'{name}.tex').write_text('\\begin{table*}[!t]\n' + block + '\\end{table*}\n', encoding='utf-8')
        with (SOURCE / f'{name}_cells.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f); writer.writerow(headers); writer.writerows(cells)
        coverage.append({'body_label': f'tab:{label}', 'output': name, 'rows': len(cells), 'columns': len(headers)})
    QA['body_tables'] = coverage


def deliverables():
    combined = fitz.open()
    export = {}
    thumbs = []
    for name in CAPTIONS:
        path = OUT / f'{name}.pdf'
        with fitz.open(path) as doc:
            p = doc[0]
            fonts = p.get_fonts(full=True)
            embedded = all(bool(doc.extract_font(f[0])[3]) for f in fonts)
            assert embedded and all('TimesNewRoman' in f[3].replace('-', '') for f in fonts), fonts
            assert not p.get_images(full=True)
            assert abs(p.rect.width/72 - 7.16) < 1e-4
            root = ET.parse(OUT / f'{name}.svg').getroot()
            assert not root.findall('.//{http://www.w3.org/2000/svg}image')
            export[name] = {'width_inches': p.rect.width/72, 'height_inches': p.rect.height/72,
                            'embedded_fonts': [f[3] for f in fonts], 'raster_images': 0,
                            'svg_text_nodes': len(root.findall('.//{http://www.w3.org/2000/svg}text')),
                            'min_pdf_span_pt': min(s['size'] for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans'])}
            combined.insert_pdf(doc)
        im = Image.open(OUT / f'{name}.png').convert('RGB')
        im.thumbnail((1074, 660))
        tile = Image.new('RGB', (1100, im.height+48), 'white')
        ImageDraw.Draw(tile).text((14, 7), name, fill=INK)
        tile.paste(im, ((1100-im.width)//2, 30))
        thumbs.append(tile)
    combined.save(HERE / 'all_candidates.pdf'); combined.close()
    contact = Image.new('RGB', (2200, sum(max(thumbs[i].height, thumbs[i+1].height if i+1 < len(thumbs) else 0) for i in range(0, len(thumbs), 2))), '#EDEDED')
    y = 0
    for i in range(0, len(thumbs), 2):
        contact.paste(thumbs[i], (0, y))
        if i+1 < len(thumbs): contact.paste(thumbs[i+1], (1100, y))
        y += max(thumbs[i].height, thumbs[i+1].height if i+1 < len(thumbs) else 0)
    contact.save(HERE / 'contact_sheet.jpg', quality=94)
    QA['exports'] = export
    QA['palette'] = {'control': CONTROL, 'text_and_axes': INK, 'gold': GOLD, 'blue': BLUE, 'red': RED}
    QA['source_sha256'] = USED
    QA['inputs_unchanged'] = all(hashlib.sha256((DATA/name).read_bytes()).hexdigest() == sha for name, sha in USED.items())
    assert QA['inputs_unchanged']
    (HERE / 'validation.json').write_text(json.dumps(QA, indent=2), encoding='utf-8')
    (HERE / 'captions.json').write_text(json.dumps(CAPTIONS, indent=2), encoding='utf-8')
    sections = []
    for name, cap in CAPTIONS.items():
        sections.append(f'<section><h2>{name}</h2><img src="figures/{name}.svg" alt="{html.escape(name)}"><p>{html.escape(cap)}</p><p><a href="figures/{name}.pdf">PDF</a> | <a href="figures/{name}.svg">SVG</a> | <a href="figures/{name}.png">PNG</a></p></section>')
    (HERE / 'preview.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>QC-MDPC figure candidates</title><style>body{max-width:1100px;margin:30px auto;padding:0 24px;color:#222;font:16px Georgia,serif}section{border-top:1px solid #bbb;padding:20px 0}img{width:100%;height:auto}h1{font-size:26px}h2{font-size:19px}p{line-height:1.5}a{color:#004488}</style><h1>QC-MDPC figure candidates · 2026-10-23</h1>' + ''.join(sections) + '</html>', encoding='utf-8')
    comparisons = []
    old_dir = HERE / 'previous_actual_figures'
    old_dir.mkdir(exist_ok=True)
    for name in list(CAPTIONS)[:5]:
        old = ROOT / 'v3/figures' / f'{name}.pdf'
        if not old.exists():
            continue
        shutil.copy2(old, old_dir / old.name)
        with fitz.open(old) as doc:
            doc[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(old_dir / f'{name}.png')
        comparisons.append(f'<section><h2>{name}</h2><div class="pair"><div><h3>Current manuscript</h3><img src="previous_actual_figures/{name}.png"></div><div><h3>New candidate</h3><img src="figures/{name}.svg"></div></div></section>')
    (HERE / 'comparison.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Figure comparison</title><style>body{margin:25px;font:16px Georgia,serif;color:#222}h2{font-size:20px}h3{font-size:16px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:28px}img{width:100%;height:auto}section{padding:20px 0;border-top:1px solid #aaa}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><h1>Current manuscript / new candidates</h1>' + ''.join(comparisons) + '</html>', encoding='utf-8')
    manuscript = (ROOT / 'v3/en/main.tex').read_text(encoding='utf-8')
    figures = re.findall(r'\\dblfig\{([^}]+)\}.*?\{(fig:[^}]+)\}', manuscript)
    assert len(figures) == 5
    QA['body_figures'] = [{'body_number': i, 'label': label, 'output': Path(file).stem} for i, (file, label) in enumerate(figures, 1)]
    ordered = [(manuscript.index('{' + item['label'] + '}'), item['output'], f"Figure {item['body_number']}") for item in QA['body_figures']]
    ordered += [(manuscript.index('{' + item['body_label'] + '}'), item['output'], f'Table {i}') for i, item in enumerate(QA['body_tables'], 1)]
    body_sections = []
    body_pdf = fitz.open()
    for _, name, label in sorted(ordered):
        with fitz.open(OUT / f'{name}.pdf') as doc:
            body_pdf.insert_pdf(doc)
        body_sections.append(f'<section><h2>{label}: {name}</h2><img src="figures/{name}.svg"><p>{html.escape(CAPTIONS[name])}</p><a href="figures/{name}.pdf">PDF</a> | <a href="figures/{name}.svg">SVG</a></section>')
    body_pdf.save(HERE / 'body_complete.pdf'); body_pdf.close()
    (HERE / 'body_complete.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>正文五图五表完整对应</title><style>body{max-width:1150px;margin:30px auto;padding:0 20px;font:16px Georgia,serif;color:#222}section{border-top:1px solid #bbb;padding:20px 0}h2{font-size:19px}img{width:100%;height:auto}p{line-height:1.6}</style><h1>正文 5 张图 + 5 张表：完整候选</h1><p>按正文引用顺序列出。候选尚未替换进论文；表格保留全部数据列。正文图3对应时间消融，正文图4对应机制，文件名数字沿用原工程命名。</p>' + ''.join(body_sections) + '</html>', encoding='utf-8')
    (HERE / 'validation.json').write_text(json.dumps(QA, indent=2), encoding='utf-8')
    with zipfile.ZipFile(HERE / 'PDF_SVG_candidates.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in CAPTIONS:
            for ext in ('pdf', 'svg'):
                archive.write(OUT / f'{name}.{ext}', f'{ext.upper()}/{name}.{ext}')
        for name in ('captions.json', 'validation.json', 'table1_primary_summary.tex', 'build_figures.py'):
            archive.write(HERE / name, name)
        for path in HERE.glob('table*_body_*.tex'):
            archive.write(path, path.name)
        for path in SOURCE.glob('*.csv'):
            archive.write(path, f'source_data/{path.name}')
        for name in ('audit_tables.py', 'table_content_audit.json', '图6与正文表格内容核验.md'):
            archive.write(HERE / name, name)
    with zipfile.ZipFile(HERE / 'body_5figures_5tables.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for _, name, label in sorted(ordered):
            for ext in ('pdf', 'svg'):
                archive.write(OUT / f'{name}.{ext}', f'{ext.upper()}/{name}.{ext}')
        for path in HERE.glob('table*_body_*.tex'):
            archive.write(path, f'LaTeX/{path.name}')
        archive.write(HERE / 'validation.json', 'validation.json')
        archive.write(HERE / 'captions.json', 'captions.json')


if __name__ == '__main__':
    study_design(); primary(); mechanism(); temporal(); scope(); window(); failure_modes(); primary_table(); manuscript_tables()
    subprocess.run([sys.executable, str(HERE / 'audit_tables.py')], check=True)
    deliverables()
    print(json.dumps({'output': str(HERE), 'figures': len(CAPTIONS), 'all_sources_unchanged': QA['inputs_unchanged']}, indent=2))
