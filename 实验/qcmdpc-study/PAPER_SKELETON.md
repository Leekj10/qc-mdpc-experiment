# 论文骨架（分支 B 正式确认）——章节到数据的完整映射

> 状态（2026-09-03 晚修订）：**M5 正式全量池 gate_pass=TRUE（0.679 log₁₀，余量充足，McNemar p≤10⁻¹⁸）**→ 主线锁定分支 B（C4/DRIS 方法文），分支 C 素材（测量+机制+阴性对照）作为支撑章节全部保留。
> 所有数字以 `results/m5_formal/report.json`（正式）、`results/gate_h2_extended/`（预演）、`results/l1_c4_transfer/`（L1）为准。

## 拟定题目
**中文**：《QC-MDPC 比特翻转译码器的密钥依赖失败异质性：测量、机制与保守首轮调度》
**英文**：*Key-Dependent Failure Heterogeneity in QC-MDPC Bit-Flipping Decoders: Measurement, Mechanisms, and a Conservative First-Round Schedule*

## 一句话故事
在密钥级留出与预注册协议下，我们系统测量了现代 QC-MDPC 比特翻转译码器在随机/弱密钥/近码字压力条件下的失败异质性与失败机制，证明一个确定性的"保守首轮整数偏置"调度在所有条件组上显著降低条件失败率（2.5–9×），而阈值随机化（CPS）在同一框架下无收益——为解码器层的鲁棒性设计提供了可复现的实证基准。

## 章节 → 数据映射

| 章节 | 内容 | 数据来源 | 图表 |
|---|---|---|---|
| 1 引言 | NIST IR 8545 动机（DFR 密钥依赖是 BIKE 落选核心）；三点贡献 | 引用 | — |
| 2 背景与相关工作 | 解码器谱系（BF/BGF/BIKE-Flip/BF-Max/近码字感知）；攻击线（GJS→CRYPTO'23→CMC'25）；随机化近邻（in-place BF 2021）；阈值优化近邻（Kichna'25, Cai-Zhang'25） | 文献（引用前逐条核验） | — |
| 3 实验方法 | 环算术参考实现；冻结语义（param.h 提取）；条件组构造+结构自验证；种子派生；整钥 60/20/20；Wilson/3-N 规则；预注册协议全文 | `configs/pre_register.json`、`reference/FROZEN_REFERENCE_SEMANTICS.md` | 流程图（可选） |
| 4 测量结果 | (a) 条件梯度 G0/G2/G3；(b) 逐密钥异质性；(c) 失败机制分布（停滞/发散/早期误翻转） | `results/gate_h2_formal(+extended)`、`results/m1_p1_prescreen`、`results/m6_mechanism` | **F1, F2, T1** |
| 5 保守首轮调度（C4） | M4 搜索协议（successive halving，候选冻结）；S1/S2/S4/门控预演全链；改善 2.5–9×；门控 0.402<0.5 的诚实报告 | `results/m4_search/report.json`、`confirm_test.json`、`gate_*` | **F4, T1** |
| 6 机制分析 | 配对转移矩阵：6/7 救回（含全部早期误翻转）；+0.26 迭代代价；与 BIKE-Flip 哲学的一致性讨论 | `results/m6_mechanism/report.json` | **F3** |
| 7 阴性结果：阈值随机化 | 悬崖机制三点图谱（-1 发散/+1,+2 停滞/混合≈加权）；强调度上中性偏负；搜索框架内双表全败；"混合不消除方差"的观察 | `results/m2_p1_cps_probe`、`m2b_p1_cps_asym`、`m4_search` | 悬崖图谱表 |
| 8 方法学附注 | BF-Max tie-break 敏感性（逐样本依赖、聚合稳健）；BGF 仿射语义（截断+下限）；L1 探针零失败与官方 DFR 的一致性 | `results/m1_p2_l1_probe/tiebreak`、`m1_p2_l1_bfmax_prf` | 小表 |
| 9 局限与结论 | 玩具/缩放参数为主；L1 仅无害性+代理信号（转移未获证明）；Python 载体与 C 参考的语义差异；正式门控已通过（0.679）但外推到 2⁻¹²⁸ 不可验证 | — | — |

## 主张账本（claims ledger）——写作时逐条对照（2026-09-03 修订）
**可以主张（正式尺度数字，2026-09-03 晚更新）**：
- C4（保守首轮 +2）在三条件组、92–94 把全新密钥、834k 配对样本上显著降低条件 DFR：**4.1×/5.5×/4.5×**，最差组 U₉₅ 改善 **0.679 log₁₀**，精确 McNemar p ≤ 2×10⁻¹⁸，逐钥符号检验 p ≤ 10⁻¹¹；
- 条件差异在正式尺度显著且**非单调**：Type-I 更差（G2/G0=1.29, z=+2.28），近码字压力组反而更好（G3/G0=0.50, z=-4.85，反直觉，附机制讨论）；
- 条件异质性是**解码器依赖的**（弱调度显著、强调度被压平；密钥级离散在强调度下泊松一致）；
- L1 上首轮偏置**无害**（偏移 0/+2/+4 × 三条件 × 10⁶ 全零失败，DFR<3×10⁻⁶），迭代代价可量化（+2 → 28% 实例多 1 轮）；L1 结构压力表现为收敛变慢（WEAK12 的 3 轮实例 2.07×）；
- 阈值随机化（CPS）在本设计空间内无收益且边缘载体上有悬崖代价（完整阴性对照）；
- 失败机制分类及配对转移（6/7 救回，M6）；
- G2-C4 残余风险集中仅作为**提示性观察**（扩展尺度 z=+2.74，正式尺度 z=+1.57 不显著）。

**禁止主张**：
- 任何 2⁻¹²⁸/IND-CCA2/provably secure 表述；
- "消除/根治反应攻击"；
- "优于 BIKE-Flip"（未做同参数对照，只可说"哲学一致、载体不同"）；
- L1 上的任何 DFR 点估计（探针只能给上界）；
- "首个随机化 QC-MDPC 调度"（in-place BF 2021 在先）；
- "强解码器下组间梯度不显著"的旧表述（已被正式尺度推翻：G2/G0=1.29 z=+2.28、G3/G0=0.50 z=-4.85 均显著；引用时必须用正式尺度数字并说明非单调方向）；
- 已撤回的 z≈-3.1 旧算结果不得出现在任何草稿中。

## 投稿前必补（硬性清单，2026-09-03 晚更新）
1. ~~全量 M5 正式判定~~ **已完成**（gate_pass=TRUE，数字已入图表/T1）；
2. ~~C 交叉验证~~ **已闭环**（zig cc；BGF z≈0.89、CLASSIC 动态 z≈-1.02；L1 BGF 10⁷ 零失败；语义差异归档 §6）；
3. **BF-Max tie-break 规则对照原文**（arXiv 被网络阻断，需换环境重试；论文中先以"两种 tie-break 均报告"方式规避）；
4. **文献核验**：已核销 Bartz-Liva 2019、SV19、Arpin Markov、AI4CBC 2025/440、in-place BF ICETE 2020；**仍挂起**：ePrint 2026/1616、Gellersen CiC 2025、Matthews-McMillon DCC 2025、Cai-Zhang ISCAS 2025 DOI、Kichna DOI；
5. ~~L1 上的 C4 对照~~ **已完成**（预注册 v2：转移未获证明但无害性成立，如实报告）；
6. **英文初稿写作**（章节映射见上表；图表 F1–F4/T1 已是正式数据版）。

## 目标期刊（与既定策略一致）
主投：Cryptography and Communications / IET Information Security（核验当年 SCIE 状态）；
结果强：Designs, Codes and Cryptography；
不默认保底 CMC/IEEE Access（预警名单核查后决定）。
