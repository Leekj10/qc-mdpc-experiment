# 论文补丁草稿（tier-upgrade）

本文件给出对 `lw-vs/en/main.tex` 与 `lw-vs/zh/main.tex` 的**具体替换/新增文本**。
分两部分：

- **A 部分：定位修正（与实验结果无关，由文献核查确定，必须改）**
- **B 部分：增补章节（数字已按 2026-10-07 实测填入；T90 低 DFR 段落仍可随续采样收紧）**

不改 `main.tex` 本体，等各实验落地、`verify_numbers.py` 可覆盖后再统一应用并编译。

---

# A 部分：定位修正

## A1. 规范事实（EN，替换 §II 中一句 + 新增一句）

**现文（main.tex 约 L72）**：

> BIKE-Flip uses a high-to-low construction with a first-round protection term and is the
> tuned production decoder in BIKE specification v5.2 \cite{bike2024spec}.

**替换为**：

> BIKE-Flip uses a high-to-low construction in which the specification's margin $\delta$
> is present in \emph{every} iteration: with $T=\max(f(w),F_i(w_0))$ the specification
> sets $F_1=f(w_0)+\delta$, blends $f(w_0)$ with the floor $(v{+}1)/2$ in $F_2,F_3$ and
> adds $\delta$ there as well, and uses $(v{+}1)/2+\delta$ for $i\ge 4$
> \cite{bike2024spec}; the published rationale is that failures originate in iterations
> two and three when a few correct positions carry extreme counters while the
> syndrome-derived threshold has already fallen \cite{sendrier2024seminar}. We therefore
> stress that FRO-2 is \emph{not} the specification's schedule: it is a one-shot $+2$ on
> the first iteration of the binomial-threshold carrier, and the specification's margin
> is a permanent part of a differently shaped schedule.

**中文稿对应句**同义替换（§II 相关段落）。

## A2. 相关工作：建模文献段落（EN，新增于 §II 末）

> **Related modelling work.** Two lines of prior work overlap with our mechanism study and
> delimit what is new here. First, per-instance and per-round failure models: Kim and Park
> predict LDPC decoding failure with a logistic model over (iteration index, unsatisfied
> checks) for early termination \cite{kim2021logistic}; Paiva and Terada use the average
> number of uncorrected errors remaining after the first iteration as a small-sample DFR
> proxy across code sizes \cite{paiva2022pickyfix}; Annechini et al.\ model the
> syndrome-weight distribution before and after the first iteration
> \cite{annechini2024syndromedist} and later give a closed-form DFR model for the exact
> three-iteration parallel bit-flipping decoder, explicitly warning that extrapolating
> from proxy decoders is hazardous \cite{annechini2025closedform}. Second, DFR-level
> models and scaling laws: Vasseur and Sendrier's Markov model over (syndrome weight,
> error weight) \cite{vasseur2019dfr}, the conservative UPC-crossing model of
> \cite{conservative2019}, Vasseur's two-point extrapolation framework for DFR in the
> code size \cite{vasseur2021thesis}, Tillich's asymptotic law \cite{tillich2018dfr}, and
> the key-dependent Markov models of Arpin et al.\ \cite{arpin2025markov}. None of these
> uses round-one statistics \emph{counterfactually}---to predict the risk ratio of a
> different threshold schedule or a different operating point---which is the use we
> validate below.

## A3. 讨论：预先拆解"规范就持续加了 δ"这一反驳（EN，新增于 §discussion）

> One objection deserves an explicit answer. The production decoder sustains its margin
> $\delta$ across all iterations, whereas we report that sustaining an offset destroys the
> decoder (Section~\ref{sec:temporal}). Both statements are about perturbations of
> \emph{particular} schedules. Our sustained-offset arm displaces the later rounds of a
> schedule whose thresholds are derived from the current syndrome weight through the
> binomial model --- every later round of that carrier is individually calibrated, and
> shifting all of them breaks the calibration. The specification's schedule has a
> different shape: its later iterations are floored at $(v{+}1)/2$, the margin is present
> from the first iteration onwards by construction, and its calibration target is the
> whole schedule rather than each round separately. The correct reading of our result is
> therefore that a \emph{mid-flight} displacement of a calibrated per-round schedule is
> destructive, not that any schedule containing a constant margin must fail.

## A4. 声明边界（EN，加在 limitations 内）

> The offset-sensitivity window we measure is a measurement, not a theorem: no published
> analysis derives the two-sided sensitivity of a bit-flipping threshold to its offset,
> and neither do we.

---

## A1–A4 的中文稿对应文本（`zh/main.tex`）

**A1（§II 相关句替换）**：
> BIKE-Flip 采用由高到低的构造，且规范中的裕量 $\delta$ 出现在**每一轮**：以
> $T=\max(f(w),F_i(w_0))$ 为阈值时，规范取 $F_1=f(w_0)+\delta$，$F_2,F_3$ 在 $f(w_0)$ 与
> 下界 $(v{+}1)/2$ 之间线性过渡并同样加 $\delta$，$i\ge4$ 取 $(v{+}1)/2+\delta$
> \cite{bike2024spec}；已发表的机理依据是：失败发生在第 2–3 轮，此时少数正确位置的计数器
> 异常偏大而由综合征导出的阈值已经下降 \cite{sendrier2024seminar}。因此必须强调，
> **FRO-2 不是规范的调度**：它是在二项式阈值载体上对**第 1 轮**的一次性 $+2$，
> 而规范的裕量是另一种调度形状中永久存在的一部分。

**A2（§II 末新增"相关建模工作"段）**：
> 有两条既有工作线与本文的机理研究重叠，并界定了本文的新意。其一是逐实例/逐轮失败模型：
> Kim 与 Park 用（迭代序号，未满足校验数）的逻辑回归预测 LDPC 译码失败以提前终止
> \cite{kim2021logistic}；Paiva 与 Terada 以"首轮后剩余未纠正错误数"作为跨码长的
> 小样本 DFR 代理 \cite{paiva2022pickyfix}；Annechini 等建模首轮前后的综合征重量分布
> \cite{annechini2024syndromedist}，其后给出精确三轮并行比特翻转译码器的闭式 DFR 模型，
> 并**明确警告由代理译码器外推是危险的** \cite{annechini2025closedform}。其二是 DFR 层面的
> 模型与标度律：Vasseur–Sendrier 的（综合征重量×错误重量）马氏链 \cite{vasseur2019dfr}、
> 保守的 UPC 穿越模型 \cite{conservative2019}、Vasseur 关于 DFR 随码长变化的两点外推框架
> \cite{vasseur2021thesis}、Tillich 的渐近律 \cite{tillich2018dfr}，以及 Arpin 等**密钥依赖**
> 的马氏模型 \cite{arpin2025markov}。上述工作均**未把首轮统计量用于反事实预测**——
> 即预测另一套阈值调度或另一个工作点的**风险比**——而这正是本文验证的用法。

**A3（§讨论新增段）**：
> 有一个反驳需要正面回答：生产译码器在全部轮次都保留裕量 $\delta$，而本文却报告持续偏移会
> 摧毁译码器（§V-A）。两句话说的都是对**特定调度**的扰动。本文的持续偏移臂位移的是一个
> **由当前综合征重量经二项式模型导出阈值**的调度的后续轮次——该载体的每一轮都各自经过标定，
> 同时位移全部轮次会破坏这一标定。规范的调度形状不同：其后段迭代以下界 $(v{+}1)/2$ 为底，
> 裕量从第 1 轮起就按构造存在，其标定对象是**整个调度**而不是每一轮单独标定。因此本文结论
> 的正确读法是：**对已标定的逐轮调度做中途位移是有害的**，而不是"任何含常数裕量的调度必然失败"。

**A4（limitations 新增句）**：
> 本文测得的偏移敏感度窗口是一个**测量结果**而非定理：没有任何已发表分析推导出比特翻转阈值
> 对其偏移量的双边敏感度，本文也没有。

---

# B 部分：增补章节（依赖实验，数字待填）

## B1. 反事实模型的经验（EN，新增 §Discussion 小节；**不是** Model 节）

> **A counterfactual round-one model fails, and why.** Because the round-one flip
> counts $(n_{false},n_{true})$ and the post-round-one syndrome weight are computable
> from the initial state and the offset without running the offset's decoder, it is
> natural to fit $P(\text{fail}\mid\text{round-1 statistics})$ on the baseline arm and
> predict other offsets from it. On the same 92-key pool and instances as the headline
> result, such a model classifies baseline failures almost perfectly within its own arm
> (held-out-key AUC $0.995$) yet predicts the wrong sign for every beneficial offset:
> predicted risk ratios of $0.79$, $0.16$, $0.04$ against measured $3.46$, $3.86$,
> $3.97$ for $+1$, $+2$, $+3$ (all on the same held-out keys). Conditioning on the arm as well, with a strict
> double hold-out (keys and offset simultaneously), still fails: predicted $2.18$,
> $1.86$, $0.83$ against the same measured values, with the largest offset predicted in
> the wrong direction. The diagnosis is a post-treatment conditioning problem: a low
> count of flipped true errors means ``hard instance'' under the baseline but
> ``deferred by the intervention'' under a raised threshold, so the conditional failure
> probability is not transportable across offsets. We report this negative result
> because it is directly relevant to the caution, stated in
> \cite{annechini2025closedform}, that extrapolation from proxy decoders is hazardous,
> and because it bounds what round-one statistics can support: the aggregate exchange ratio explains why a
> conservative first round can help and tracks the sign across every measured point, but
> the per-instance round-one counts do not transfer counterfactually and were even
> sign-wrong for the largest offset; no validated quantitative predictor was obtained,
> and none is claimed.

## B2. 生产锚点段落（EN，替换现 §production-boundary 部分文本）

> At the true production parameters $(r,d)=(12323,71)$ with the error weight raised from
> the production value $t=134$ to $t^{*}=172$ — the smallest TESTED increase that brings the
> baseline failure rate into the measurable band, located by a bracketed scan in which
> $t=170$ still gave zero failures in 1{,}200 trials and $t=195$ gave 99.9\% — the
> first-round $+2$ offset gives a risk ratio of $4.48$ [2.97, 7.25] and a single $-1$
> gives $0.162$ [0.119, 0.209] (32 keys, 1{,}500 errors each, paired instances). The
> archived production-parameter runs had covered only offsets $0$, $+2$ and $+4$; the
> negative direction had never been tested, and at these code parameters the window is
> now measured to be two-sided. At the production error weight itself no failure is
> measurable for any arm (32{,}000 paired trials each, rule-of-three bound
> $9.4\times10^{-5}$), but the round-one decision margin is: the baseline flips 101.2
> positions on average, 87.5 true and 13.8 false; $+2$ reduces false flips to 2.3
> (a factor of 6.0) while deferring 25.5 true flips, and $-1$ raises false flips to
> 31.2 (a factor of 2.3). The exchange ratio — avoided false flips per deferred true
> flip — is 0.450 at $+2$, against 0.546 at the calibrated point. The measurable
> production cost of the offset is convergence: $+2$ needs 2.446 iterations on average
> against 2.054 for the baseline, and $-1$ also costs (2.232) — the baseline schedule is
> the fastest of the three. The specification's own first-round margin behaves the same
> way under its own decoder: removing it raises the two-round convergence fraction from
> 0.09\% to 37.35\%, while doubling it lowers it further, and all four ablations record
> zero failures in 8{,}000 trials each. A measurable convergence cost thus coexists with a
> robustness benefit that is not measurable at Level-1 sample sizes; the ablation shows
> no resolvable failure-rate difference in either direction, and we do not claim the
> trade is favourable.

## B3. 低 DFR 段落（EN，新增于 §results）

> On the same 92-key pool used for the headline result, lowering the error weight from
> $t=92$ to $t=90$ moves the baseline DFR from $1.022\times10^{-3}$ to
> $7.07\times10^{-5}$ — a factor of 14 — while the risk ratio stays at 3.71
> [2.69, 5.57] (130 baseline failures in 1{,}840{,}000 paired trials; 60 keys improved,
> 6 worsened, 26 ties, sign-test $p=2.7\times10^{-12}$), i.e.\ the effect persists over an
> order of magnitude in DFR at approximately the same magnitude as at $t=92$. A pooled
> $t$-sweep point at $t=92$ ($7.00$ [3.64, 23.5], a \emph{different} 30-key pool) lies
> above both with a point estimate outside the main pool's interval, although the two
> intervals overlap; the pool-to-pool spread of point estimates therefore exceeds the
> variation induced by the error weight over this range. We
> do not claim that the effect grows as the failure rate falls.

---

## 待办清单（应用补丁前）

1. B 部分数字已填（见 `analysis_cells.csv` / 各 JSON）；`sendrier2024seminar`、`kim2021logistic`、
   `paiva2022pickyfix`、`annechini2025closedform`、`annechini2024syndromedist`、`conservative2019`、
   `vasseur2019dfr`、`vasseur2021thesis`、`tillich2018dfr`、`arpin2025markov` 等新增引用须进 `refs.bib`；
2. 新增的每个数字加进 `verify_numbers.py` 的检查清单；
3. 中英两稿同步（中文稿对应段落目前尚未写）；
4. 编译验证（pdflatex/xelatex + bibtex）。
