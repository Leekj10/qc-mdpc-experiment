# 项目复审报告（2026-09-23）

## 审查范围与结论

本次复审覆盖 `实验/qcmdpc-study` 的核心实现、预注册文件、正式/迁移/捕获/机制/补充/工程结果，`new` 下的中英文 Markdown 与期刊 LaTeX、图表生成与验证脚本，以及当时的 PDF/Word/HTML 交付件。以下主体记录的是 2026-09-23 的审查基线；后续处理状态见下方新增的小节。

核心方向性结果有证据支持：P1' 正式配对实验中，C0/FRO-2 失败数为 RAND 282/68、TYPE-I 372/68、NCW-shallow 141/31；关键风险比与主 CSV/JSON 一致，核心测试 `168/168`、BIKE-Flip 测试 `15/15` 通过。当前最需要优化的不是继续堆实验，而是修复成功判据、算法命名、稿件版本和投稿构建链。

## 2026-09-24 后续处理状态

- exact-recovery 追踪已加入译码器；G0、G2、G3 已完成并合并到 `formal_current/report.json`。278 把密钥、每臂 834,000 个配对实例中，C0/FRO-2 精确恢复失败为 795/167，零综合征错纠均为 0。合并报告记录了各组来源脚本哈希；三版差异已逐字节核对为报告聚合或默认输出目录变化，不能把该归档称为单一哈希重跑。
- NCW-ADAPT 已改为 STLR v2：轮次后重新计算 UPC，额外扫描与试探计入成本，并在中英文稿件中明确其为通用停滞触发原型。
- 失败分类已按 `ceil(max_iter/4)` 冻结窗口实现，调用方显式传入迭代预算；旧机制报告保留为 exploratory，不静默覆盖。
- 中英文源稿、Word/HTML/PDF 导出、图 1--7 清单、expanded confirmation seed 和 C 参考语义记录已同步；期刊 TeX 加入双栏 `table*`/`figure*` 适配，但仍需真实 TeX 引擎编译。
- manifest 现在同时哈希源文件、C 参考源和 PDF/DOCX/HTML/PNG/SVG 交付物；当前 PDF 是由 Edge 从 HTML 打印的最新交付件，不等价于真实期刊 TeX 编译结果。

## P0：投稿或科学结论前必须处理

### 1. 源稿与“最终”PDF/Word/HTML不是同一版本

- `new/manuscript.md`、`new/manuscript_en_journal_v4.tex`、`new/manuscript_zh_journal_v4.tex` 在 2026-09-22 更新；HTML 为 2026-09-16，PDF 为 2026-09-16，DOCX 为 2026-09-17。
- 当前源稿摘要写的是 `We introduce FRO-2, which raises...`；英文 PDF 仍是旧摘要 `We introduce a minimal temporal intervention...`。PDF/Word也没有当前源稿的扩大确认规模表述。
- 英文 PDF 的工程表右列已被裁切，表 5 的 `Trigger`、`ms/decode` 等列也不完整。当前 PDF 不能作为 9 月 22 日源稿的提交版本。

**处理顺序：**先冻结唯一源稿，再重建英文/中文 HTML、PDF、DOCX；逐页核对摘要、表 4--7、图 5--7，并让验证脚本比较源稿与交付件中的版本标记或关键句，而不是只检查固定字符串。

### 2. 主实验把“零综合征”当作成功，未量化错纠

- 静态 `bf_parallel` 在 `实验/qcmdpc-study/qcmdpc/decoders.py:235-252` 以 `s.sum()==0` 判成功；`实验/qcmdpc-study/formal_m5.py:68-72`据此统计失败。
- C 参考路径按解出的错误与真值的距离判定 exact recovery（`decoders.py:181-218`）；冻结语义文件也承认两者不同（`reference/FROZEN_REFERENCE_SEMANTICS.md:100-103`）。
- QC-MDPC 存在非零码字，因此零综合征不逻辑蕴含恢复到原始错误。现有跨实现比较只能说明不同样本上的总体接近，不能给出主样本中错纠率的上界。

**处理顺序：**在 P1'/P2/捕获边界的同一 `(H,e,s)` 样本上记录估计错误向量与 `e_hat==e`；报告零综合征错纠计数。若非零，重算主 DFR/RR；若为零，也应把该验证结果写入方法和补充材料。

### 3. NCW-ADAPT 的实现与名称不符

- `new/ncw_adaptive_experiment.py:45-62` 在正常轮翻转后仍使用翻转前的 `alpha` 选择恢复候选。
- 该实现没有计算或使用近码字结构分数，只在停滞后对 UPC 最大的 4 个位置做单比特试探；RAND、TYPE-I 和 NCW-shallow 都使用同一通用规则。
- 报告和正文称其为 `near-codeword-aware`，这一名称会让读者以为算法检测了近码字。

**处理顺序：**二选一：重算 18 个单元并把候选改为翻转后重新计算的 UPC；或暂时将算法和全部报告改名为 `stagnation-triggered local recovery`，把它降格为通用恢复原型。修正前不要把 NCW-ADAPT 作为近码字方法证据。

## P1：高优先级方法与叙述修正

### 4. 失败分类没有执行冻结的预注册定义

- 预注册顺序是 `divergence -> period2 -> stagnation -> early_misflip -> other`（`实验/qcmdpc-study/configs/pre_register.json:12-17`）。正文 `new/manuscript.md:122` 写成了相反的优先顺序。
- `实验/qcmdpc-study/qcmdpc/taxonomy.py:40-42` 使用 `len(traj.flip_positions)//4`，而冻结定义要求前 `ceil(iters/4)` 个迭代。

**处理顺序：**按冻结定义重跑 `m5_mechanism` 或明确声明该机制结果是偏离预注册的探索性重分类；同步修正图 2、正文和所有摘要性数字。

### 5. H2 门控应以纯新密钥结果作确认判定

正式全池包含早期门控阶段已经接触过的密钥；纯新子集为 212 把，`fresh_only_verification.json` 给出 worst-group 改善 0.687，而全池正文 `new/manuscript.md:161` 报 0.679。两者方向一致，但“test keys only”是预注册门槛。

**处理顺序：**把纯新子集的 0.687 明确标为 H2 test-key confirmation，全池 0.679 改成补充敏感性结果，并说明正式池是对中期池的扩展，不是完全独立的新池。

### 6. 捕获机制用词超出测量内容

`实验/qcmdpc-study/capture_deconfound.py:83-121` 生成的是 `kappa` 交叠错误并统计成功/失败，没有记录译码轨迹是否朝近码字汇聚、终态距离或吸引域比例。`kappa>d` 足以说明是 capture-prone 的结构化压力条件，但不能单独证明每次失败发生了“capture basin”。

**处理顺序：**正文将 `genuine near-codeword capture` 收紧为 `kappa>d structured-error stress/capture-prone condition`；只有补充终态/轨迹距离诊断后，才使用 capture mechanism/basin 术语。

### 7. 工程段有旧的零失败表述

`new/manuscript_en_journal_v4.tex:954-956` 与 `new/manuscript_zh_journal_v4.tex:734-735` 写 P3 存在零失败单元；当前 `engineering_analysis.json` 的 P3 15 个方法×条件单元失败数全部为正（最小为 1）。

**处理顺序：**删除“zero-failure cells”，改为“failure counts are sparse”；重导出所有格式。

## P2：投稿质量与二区竞争力

### 8. 双栏期刊 LaTeX 不能直接使用 longtable

英文 `new/manuscript_en_journal_v4.tex:5` 使用 IEEEtran journal 双栏，随后在表 1--7 使用 `longtable`（约 `:554,679,844,931,965,1000,1030`）；中文版本 `ctexart,twocolumn` 也在表 1--7 使用 `longtable`。`longtable` 不支持双栏。当前环境没有 LaTeX 引擎，且 PDF 来自 HTML render，不能证明期刊源可编译。

**处理顺序：**按目标期刊改成 `table`/`tabular`、双栏跨页表或目标模板允许的表格环境，然后用真实 TeX 引擎编译并检查 overfull、浮动体和图表宽度。

### 9. 图和验证链存在漂移

- `make_figures.py:291-305` 只生成图 1--4并会重写 manifest；图 5、6、7由独立脚本生成。
- `new/README.md:43-55`、`publication_figure_manifest.json`、`figure_notes.md`、期刊稿的图号不一致：正文包含图 1--5、图 7，但图 6 没有进入期刊稿，也没有对应 caption；README 又称“五张主图、三张核心表”。
- `new/verify_package.py:50-59` 只验证图 1--5，不验证图 6/7、中文 DOCX、源稿与 PDF/Word 一致性。
- 图 2b 和图 4a 虽绘制 RR=1 虚线，但 x 轴分别从 2.5 和 1.3 开始（`make_figures.py:117-123,225-230`），无效应基准线在画布外不可见。

**处理顺序：**确定主文是否包含图 6；统一图号、caption、alt text、manifest 和 README；让验证脚本检查全部实际引用的图，并把 RR=1 纳入坐标范围或在图注列出基准。

### 10. 复现入口和归档锁定不足

- `new/README.md:57-69` 的重建流程没有生成中文稿、图 5--7、PDF，也没有说明最终导出顺序。
- 未提供 `requirements.txt`/`pyproject.toml`/lock 文件；补充脚本虽然记录自身 SHA-256，但没有锁定导入的 `qcmdpc` 库快照。
- （历史基线）`实验/qcmdpc-study/README.md:29-44` 曾硬编码旧的 `D:\桌面\TOUGAO` 路径并保留过时状态；当前 README 已改为相对路径，并明确 C 复核已完成、BGF-lite 仅作历史近似。
- 参考 C 源存在 ZIP 与当前参考目录字节差异，且 `FIRST_ROUND_OFFSET` patch 没有独立 patch 文件、上游 commit 或完整源码 hash 清单。

**处理顺序：**改用相对路径；增加最小环境锁定和一键重建说明；生成包含入口脚本、导入库、配置、数据和参考 C 源 hash 的 manifest；单独保存本地 patch 与 upstream 版本信息。

### 11. 作者/目标期刊材料未完成

英文/中文期刊源仍有 `[Author names]`、单位、CRediT 和待确认利益冲突占位符；2.4 cm 通用 margin 也不能代替目标期刊模板。提交前需完成作者元数据、伦理/利益冲突声明、致谢、数据许可证和目标期刊格式检查。

## 已成立的证据与应保留的边界

- P1' 同实例配对、逐密钥计数和 key-cluster bootstrap 的主数字与 `m5_formal/report.json`、`new/data/main_results.csv` 一致。
- 纯新子集、P2 transfer、扩大确认矩阵的方向与区间支持“在测试的标定 CLASSIC 载体上，首轮 +2 通常降低条件 DFR”。
- Uniform +2 的负对照、round-2-only 对照、真实 `kappa>d` 压力边界和 Level-1 零失败上界共同支持“时序位置重要，但生产收益未建立”。
- BIKE-Flip/Backflip 的语义、调参和预算差异已被多数位置诚实标注；不要写成普遍 SOTA 或生产替代方案。
- 论文最稳妥的定位是：**QC-MDPC CLASSIC 类译码的首轮阈值时序敏感性与严格条件风险评估**。它不是弱密钥恢复攻击、弱密钥检测器、生产 BIKE DFR 证明，也不是已经完成的 near-codeword-aware 译码器。

## 最小执行顺序

1. 冻结源稿与唯一结果目录；修正零综合征/精确恢复验证、失败分类、NCW-ADAPT 名称或实现。
2. 重新生成全部图、HTML、PDF、DOCX，并修正双栏表格；做源稿—交付件一致性验证。
3. 更新 README、figure manifest、figure notes、依赖/源码 hash 和参考 C patch 记录。
4. 最后补作者信息、硬件记录、目标期刊模板和 DOI/引用元数据核验。

在第 1 步完成前，不建议提交当前 PDF/Word，也不建议继续用“所有结果已闭合”描述整个项目。
