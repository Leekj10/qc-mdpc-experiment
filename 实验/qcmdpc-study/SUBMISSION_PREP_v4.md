# 投稿准备与阶段 B 运行说明（draft_v4 / Q3 稳妥档）

- 日期：2026-09-05
- 依据：《QC-MDPC实验与实验计划对照结论_二次审查与优化建议.md》+ 本目录已批准的优化方案
- 状态：阶段 A（零成本统计补强 + 论文 P0 修订 + F3 图修复）已完成；阶段 B（两项补做实验）脚本已交付，待本地后台长跑。

---

## 1. 阶段 A 已完成（无需重跑）

| 产出 | 文件 | 说明 |
|---|---|---|
| 聚类稳健统计 | `qcmdpc/stats.py`（新增 `cluster_bootstrap_paired`/`holm_adjust`/`sign_test_paired`/`mcnemar_exact`） | 以密钥为重采样单位；支持 P0-6/7/8 |
| 统计脚本 | `analyze_cluster_stats.py` | 复用归档逐密钥计数，零译码成本 |
| 统计结果 | `results/m5_formal/cluster_stats.json`、`results/paper_figures/T_cluster.{md,tex}` | full pool + pure-fresh，RR/DFR差/log10RR 95% CI + Holm |
| 图修复 | `make_paper_figures.py`（F3 顶部留白 + NCW 标签）、`results/paper_figures/*.png` | P0-13 |
| 论文 | `paper/draft_v4.tex`（18 页，0 `\todo`，零错误/零未定义引用/零 overfull hbox） | P0-1..P0-11 + 最终复审 P1/P2 全部落实 |

关键结论（已验证，全部对回源数据）：6 个 pool×组组合的 cluster-bootstrap RR 95% CI **全部排除 1**；DFR 差 CI 全部排除 0；Holm 校正后最大 p 为 2.29e-8（pure-fresh NCW），主结论仍成立。

---

## 2. 阶段 B 运行说明（用户本地后台长跑）

按序执行；每步完成后把 `report.json`/`sweep.json` 交回，我做第二轮整合进 draft_v4。

### B1 第二缩放参数点迁移（检验效果是否只在 t=92）
1. ✅ 标定已完成（2026-09-05）：`results/calib_p2second/sweep.json`。发现 (3001,37) 的可测带在 2*d 之下：t≤64 零失败、t=66 C0 DFR=2.5e-3（命中）、t=68 偏高 2.4e-2。**已冻结 t=66 写入 `configs/p2second_transfer.json`**（FRO-2 的 +2 不重调）。
2. ✅ 正式迁移已完成（2026-09-05 12:12，≈52 min）：`results/p2second_transfer/report.json`（30 钥/组 ×3000 错误，90k/臂/组）。
3. ✅ 三项迁移判据**全部通过**：(a) 三组 FRO-2 点估计 < C0（direction_all_groups=true）；(b) RAND 逐密钥符号检验 p=4.9e-5 <0.05；(c) 三组 RR 95% CI 均排除 1（RAND [1.58,2.42]、WEAK-12 [2.57,4.14]、NCW-∩ [1.85,3.46]）。RR=1.95/3.21/2.51；Holm 后符号检验仍显著（7.2e-5/1.7e-7/7.2e-5）；worst-group Δ=0.384（小于 P1′ 的 0.679，冻结不重调的预期）。已整合进 draft_v4 新小节 §transfer2 + Table~\ref{tab:transfer2}，摘要/结论/限制同步。

### B2 首轮翻转机制直接测量 —— ✅ 已完成并整合（2026-09-05）
- 运行：`python mechanism_firstround.py`（20 钥/组 ×1000 错误，≈20 min）→ `results/firstround_mech/report.json`。
- 结果（三组一致）：FRO-2 首轮总翻转 29–30→9；**首轮错误翻转 8.01/8.95/8.32 → 0.84/0.99/0.89（≈9× 更少）**；首轮后残余错误重量反而**升高** +5.2~+6.1（保守首轮的特征）；失败 21→7、25→6、10→1；迭代 +0.27。rescue 子集（C0 败/FRO-2 救）上 C0 残余 92.9–93.7 重于 FRO-2 的 87.4–88.1。
- 诚实解读：收益来自“避免首轮注入错翻”+后续轮恢复，而非首轮即降低残余 → 支持“广谱首轮稳定化”。已写入 draft_v4 §5.3 + Table~\ref{tab:firstround}，Limitations 同步；该测量为仿真特权信息（用 e_true），论文已标注为机制分析、非可部署解码器。

---

## 2.5 阶段 C：Q2 增强实验（冲二区）

| 项 | 脚本/配置 | 状态 | 输出 |
|---|---|---|---|
| Q2-C 分层模型敏感性 | `analyze_hierarchical.py`（零译码） | ✅ 完成 | `results/m5_formal/hierarchical.json`；BB 回归 OR 0.241/0.183/0.220（full）、0.213/0.181/0.271（pure-fresh），CI 排除 1；ρ≈0（无额外密钥过离散）→ 已写入 draft_v4 §3.4 |
| Q2-A κ>d 真捕获去混杂 | `capture_deconfound.py` + `configs/q2_capture_deconfound.json` | ✅ 完成 | `results/q2_capture/report.json`：uniform 3.54×[2.41,6.00]、κ12 4.75×[2.00,19.0] 受益；**κ46 RR=0.99[0.98,0.99] 略劣、κ60 双双 100% → FRO-2 非捕获/error-floor 防御**；捕获梯度 κ46/60 ≈742/870× uniform → 已写入 draft_v4 §capture + Table capture |
| Q2-B 迭代预算消融 | `iter_ablation.py` + `configs/q2_iter_ablation.json` | ✅ 完成 | `results/q2_iterablation/report.json`：budget 7/10/20 下 FRO-2 均优于 C0（RR 1.72–3.17，CI 排除 1）→ 非预算伪影 → 已写入 §robust + Table robust |
| Q2-D 密钥族对比 | `key_families.py` + `configs/q2_key_families.json` | ✅ 完成 | `results/q2_keyfamilies/report.json`：三密钥族 RR 4.17/4.44/4.33 CI 排除 1（Holm 后 p=0.0084/2.3e-5/0.0084）；捕获倾向族均匀错误下仅 1.04× random（不抬升）→ 已写入 §robust |

- Q2-A 设计要点：真捕获需 κ>d；为去混杂，**同一批密钥**上仅变错误构造（rand/κ12/κ46/κ60），批内对比与密钥筛选解耦；密钥批为 ncw-admissible（require_better_than_canonical=true）以保证 κ>d 为真捕获，故绝对 DFR 条件于该批（如实注明）。
- Q2-D 诚实标注：ncwadm 为“近码字容许/捕获倾向”结构弱钥族，是 gathering-ADJACENT 代理，**非** WWW2023 精确 gathering 类。
- 第二参数点正式门控已在 B1 完成（30 钥×3000，三判据全过），故 Q2 矩阵中该项无需重复。

---

## 2.6 最终复审（draft_v4）修订记录（2026-09-05）

针对《QC-MDPC_draft_v4_最终审查说明.md》的 P1/P2 与轻微项：
- P1-1 重编译：PDF/aux/log 与 tex 同步，18 页；overfull hbox 全部消除（tab:main/tab:comparators 用 \resizebox，Data-availability 长 URL 用 \sloppy，§4 标题缩短，preamble 加 \emergencystretch）。
- P1-3 κ>d 表述：§3.2 改为“shallow 组不测真捕获，真捕获见 §capture（单批、仅证无保护）”；Limitations 改为“generalization to further points and gathering remains open；单批 κ>d 不建立普适捕获结论”。
- P1-4 预注册分层：§3.1 明确 confirmatory core / pre-specified transfer / post-registration supplemental 三层；摘要与结论不再笼统称 “fully pre-registered”。
- P1-5 “every schedule tested” → “both tested CLASSIC-based schedules”（摘要+§capture）。
- P2-1 报告 H1 未达：§4.2 增加 P90−P10 实测 0.40/0.48/0.48 log10（预注册门槛 ≥3 未达）。
- P2-2/3/4/5 收紧：“not of the code family”→“in the tested QC-MDPC setting…”；“strictly stronger”→“simulation-privileged … performed better in the measured comparison”；“harmless”→“no degradation at the tested sample resolution”；CPS 结论改为“no measurable benefit in tested regimes + large penalties on marginal schedules”。
- P2-6 第二点非纯缩放：改称 “second calibrated operating point with different code and error parameters” + 新增 Table params（r,d,t,t/d,d/r）。
- P2-7 披露 n_nonfinite_rr（主 M5=0；补充实验≤107）+ DFR difference 作为补充稳健指标（§3.4）。
- P2-8 Q2 实验统一标注 post-registration supplemental sensitivity analysis（§robust/§capture/§firstround）。
- 轻微项：F1 横轴改 “formal-pool key index” 并重生成；test_core.py(13) 与 test_bikeflip.py(5) 分别运行均通过且 EXIT=0（合并 pytest 的挂起为会话拆卸问题，非测试失败）。
- 仍需作者侧：作者/单位/ORCID、CPU/核/RAM、Zenodo v4 快照+tag。
- **IEEE Access 模板移植已完成**：`make_ieee_version.py` 由 `draft_v4.tex` 生成 `draft_v4_ieee.tex`（ieeeaccess 双栏，13 页，0 错误；figure/table 提升为跨栏浮动；keywords 环境；\EOD）。作者/\address/\corresp/\doi 为占位（不虚构）；标题页有类自带的轻微 overfull（长标题/页眉横幅），IEEE 终排会重排；单栏 `draft_v4.tex` 仍为 0 overfull 的参考版。

---

## 3. 归档核验清单（P0-12）

纳入 GitHub（github.com/Leekj12410/qc-mdpc-experiment）+ Zenodo（doi:10.5281/zenodo.22296719，建议为 v4 建版本化 DOI + git tag）：

- 代码：`qcmdpc/{ring,generators,decoders,bikeflip,stats,taxonomy}.py`；`runner.py`、`formal_m5.py`、`formal_m5_mechanism.py`、`compare_bikeflip.py`、`compare_bikeflip_l1.py`、`analyze_fresh_only.py`、`verify_stats.py`、`calib_p1prime.py`、`make_paper_figures.py`；**新增** `analyze_cluster_stats.py`、`mechanism_firstround.py`、`calib_p2second.py`、`transfer_p2second.py`、`analyze_hierarchical.py`、`capture_deconfound.py`、`iter_ablation.py`、`key_families.py`。
- 配置：`configs/*.json`、`pre_register.json`、`pre_register_amendment_v1.md`、`pre_register_v2_l1_transfer.md`；**新增** `configs/m1_p1_firstround_mech.json`、`configs/p2second_transfer.json`、`configs/q2_capture_deconfound.json`、`configs/q2_iter_ablation.json`、`configs/q2_key_families.json`。
- 种子：master_seed=20260901 及派生规则、`seeds/`。
- 结果：`results/{m5_formal(report.json, fresh_only_verification.json, cluster_stats.json), m5_mechanism, cmp_bf_p1_formal, cmp_bf_l1, revision_arms, l1_c4_transfer, calib_p1prime, gate_h2_extended, paper_figures}`；**新增** `results/{calib_p2second, firstround_mech, p2second_transfer, q2_capture, q2_iterablation, q2_keyfamilies}` 与 `results/m5_formal/hierarchical.json`。
- 参考语义：`reference/{FROZEN_REFERENCE_SEMANTICS.md, BUILD_WINDOWS.md}` + C 两处 Windows 垫片 + 一行研究补丁。
- 论文：`paper/draft_v4.{tex,pdf}`（最终）；v1/v2/v3 作历史存档。
- 环境：软件版本 + 每组运行时间（已写入 draft_v4 §3.6）；硬件（CPU/内存/线程）作者侧填充。

---

## 4. Q3 投稿准备度验收清单

- [x] 13 项 P0 全部关闭（draft_v4 逐条可追溯，见文件头 v4 变更块）。
- [x] 主结果在 full formal pool（278 钥/834k 臂）与 pure-fresh subset（212 钥/636k 臂）分别报告。
- [x] cluster-bootstrap RR / DFR 差 / log10-RR 95% CI 已算；主比较 CI 不跨越"无改善"基准。
- [x] 三组主比较 Holm 校正后仍显著；原始 p 与校正 p 并列（Table 6 / T_cluster）。
- [x] 三组逐密钥符号检验（full + pure-fresh）均在正文/表内。
- [x] 全文无禁区表述（见 §5 核查命令）；无 "278 fresh"、无 WEAK-12=gathering 防御、无 HQC 可推广、无 optimal/dominance-over-shipped/solve-DFR/2^-128 主张。
- [x] 标题/摘要/贡献/结论按审查 §11 定位、采用 §10.1 允许表述。
- [x] Reproducibility 段 + 环境/运行时间表（§3.6）；硬件为作者侧占位。
- [x] F3 顶部标注不裁切、NCW 标签可渲染；F1/F2/T1 与正文数字一致。
- [x] B2 首轮机制已诚实整合（draft_v4 §5.3 + Table firstround；方向如实：错误翻转↓、残余↑）。
- [x] B1 第二点迁移已诚实整合（draft_v4 §transfer2 + Table transfer2；三判据全过，Δ=0.384 如实小于 P1′ 的 0.679）。
- [x] Q2-C 分层敏感性（BB 回归 OR CI 排除 1；ρ≈0）已整合 draft_v4 §3.4。
- [x] Q2-A 真捕获去混杂整合（draft_v4 §capture + Table capture；如实：κ>d 下 FRO-2 无受益、非捕获防御；捕获梯度 ≈742/870×）。
- [x] Q2-B 迭代预算消融整合（draft_v4 §robust + Table robust；非预算伪影）。
- [x] Q2-D 密钥族整合（draft_v4 §robust；三族均受益；捕获倾向族均匀错误下不抬升）。
- [x] 最终复审 P1/P2 措辞与一致性修订（κ>d 分层、预注册三层、H1 未达、措辞收紧、参数表、n_nonfinite 披露、supplemental 标注）。
- [x] overfull hbox 全部消除；PDF 18 页与 tex 同步。
- [x] test_core/test_bikeflip 分别运行通过且正常退出。
- [ ] 归档快照核验（Zenodo 含 v4 + 新脚本/结果；git tag）。
- [x] draft_v4：0 \todo、零错误编译、零 undefined citation/ref。
- [x] 期刊模板移植：IEEE Access 版 `draft_v4_ieee.tex` 已生成并编译通过（双栏 13 页、0 错误）；图清晰度/作者信息待作者侧终检。
- [x] Q2 升级路径已列明（κ>d 捕获、gathering、第二点正式门控放大；见方案 §4）。

---

## 5. 禁区表述核查命令（投稿前再跑一次）

```powershell
Set-Location (Join-Path (Get-Location) '实验\qcmdpc-study\paper')
Select-String -Path draft_v4.tex -Pattern '278 fresh|gathering defense behaving|HQC-adjacent|cheapest known|dominance over the shipped|solve.*DFR|2\^\{-128\} is achieved'
# 期望：无匹配（或仅出现在否定/限制语境）
```

---

## 6. 作者侧待办（非科学内容）

1. `\author{}` 作者名/单位/ORCID；
2. Reproducibility 表硬件行（CPU 型号、物理/逻辑核、内存）；
3. 期刊模板移植（IEEE Access 或 Springer CC/IET），移植后复查分页与图清晰度；
4. 确认 Kichna（JIAS）与 InPlaceBF（Springer CCIS）两条 DOI 的 venue 全名/年；
5. Zenodo 快照更新为 v4 + 阶段 B 新结果，打 git tag。
