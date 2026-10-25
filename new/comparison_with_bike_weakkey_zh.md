# 与 BIKE 弱密钥论文的对照审查

## 对照文献

Nosouhi MR, Shah SW, Pan L, Zolotavkin Y, Nanda A, Gauravaram P, Doss R. *Weak-Key Analysis for BIKE Post-Quantum Key Encapsulation Mechanism*. IEEE Transactions on Information Forensics and Security, 18:2160--2174, 2023. DOI: [10.1109/TIFS.2023.3264153](https://doi.org/10.1109/TIFS.2023.3264153). 公开预印本：arXiv:2204.13885。

本文对照以 Crossref 的正式元数据和 Semantic Scholar 的公开摘要为基础。由于当前外部网络无法稳定获取 arXiv 全文，下面的比较定位为“摘要、元数据和本稿证据链的结构对照”，不是逐页复核该 TIFS 论文的所有实验细节。

## 研究问题的差异

| 维度 | Nosouhi 等 | 本稿 |
|:--|:--|:--|
| 核心问题 | 弱密钥是否会提高 BIKE 的平均 DFR 并影响 IND-CCA 风险 | 首轮阈值保守化是否能降低给定密钥和结构条件下的条件 DFR |
| 干预对象 | 提出 key-check 机制，改变被接受的密钥总体 | FRO-2，仅改变 CLASSIC 第一轮阈值，密钥总体不变 |
| 主要证据 | BIKE 实现、弱密钥实验、安全含义和 key-check 方案 | 同实例配对、按密钥聚类、留出确认、机制诊断和失败边界 |
| 安全结论 | 讨论弱密钥对 BIKE IND-CCA 的潜在威胁 | 不声称攻击、密钥恢复或 BIKE 目标 DFR 改善 |
| 工程输出 | 密钥检查方向 | 译码调度的局部消融和可复现基准 |

两者不是同一类贡献，也不应互相替代。TIFS 论文回答“哪些密钥可能危险、是否应拒绝这些密钥”；本稿回答“在密钥已经给定时，第一轮调度是否改变失败轨迹”。因此，本稿将 key filtering 和 decoder scheduling 写成互补关系，而不是把 FRO-2 描述为弱密钥检测器。

## 本稿已达到的相近标准

1. **问题边界明确。** 本稿将 RAND、Type-I、浅层 NCW、gathering-adjacent proxy 和真正近码字捕获分开，避免把所有结构都叫作 weak key。
2. **实验单位更严格。** C0 和 FRO-2 在相同 $(H,e,s)$ 上配对，密钥而不是错误样本是跨密钥推断单位；这比只报告 pooled DFR 更能回应密钥依赖问题。
3. **方法机制可追踪。** UPC 尾概率模型、首轮翻转诊断、统一偏移阴性对照和 $kappa>d$ 捕获边界构成一条可证伪证据链。
4. **结果没有包装成生产优势。** BIKE Level 1 的零失败只报告 rule-of-three 上界；Backflip 和调优后的 BIKE-Flip 被保留为性能参照。
5. **现在补上了算法入口。** 正文新增算法 1，说明 C0/FRO-2 的输入、首轮偏移、UPC 计算、综合征更新和配对记录；源码入口与实验脚本也逐一列出。

## 与高水平 BIKE 论文相比仍需补强的部分

### 1. “弱密钥分析”还不等于“弱密钥检测”

本稿的 Type-I 和近码字条件是压力测试构造，gathering-adjacent proxy 也不是精确 gathering-key。因而题目和摘要应继续使用“structured weak-key stress tests”或“key-conditional decoding risk”，不能改成“weak-key detection”或“gathering defense”。若目标是安全方向二区，需要新增精确 gathering-key 生成/筛选算法、自然发生率、检测复杂度和误拒绝率。当前仓库的 `key_families.py` 实现的是 near-codeword-admissible 筛选器，不能改名为 gathering-key 算法。

### 2. 需要把算法复杂度写成可核查的量

FRO-2 的核心成本是每次译码最多一次整数阈值加法，状态、UPC 计算和内存访问与 C0 相同；但平均迭代数会增加。当前正文已增加渐近复杂度、wall-clock 和平均迭代数，仍应补总 UPC 次数、迭代分位数，并区分 Python 参考实现与部署实现。

### 3. 需要更明确地连接 BIKE 安全语境

本稿已说明不等于 key recovery 或 IND-CCA 证明，但引言应明确：条件 DFR 下降只有在目标参数、拒绝语义、常数时间约束和错误反馈接口下才可能转化为系统安全收益。建议在讨论中保留“decoder-layer evidence”措辞，并避免把 4.15--5.47 倍直接写成 BIKE 安全提升。

### 4. 需要区分三种复现

- **回归验证：** 同一实现的单元测试和直接定义对拍。
- **跨实现复核：** 同一研究项目中 Python 与 C 两条代码路径在不同样本上的方向一致；本稿当前已有。
- **独立实验室复现：** 未接触搜索结果的外部团队，独立重写代码、生成密钥/错误、执行冻结配置并输出结果；本稿尚未完成。

当前正文已经将第二种情况改称“跨实现复核”，并把第三种情况列为投稿前的外部有效性增强项。

## 投稿前优先级

### 必须做

- 补作者、CPU 型号和内存；编译器、线程和 wall-clock 已写入正文。
- 核验正文现有的最小复现命令，并确认 Zenodo 快照包含所有 JSON、配置和脚本。
- 核对 Nosouhi 等 [25]、Wang 等 [5]、BIKE 规范和近期 near-codeword 工作的版本与 DOI。
- 在方法或补充材料中保留算法 1，以及 C0/FRO-2 的阈值表和停止条件。

### 强烈建议做

- 由未看过搜索结果的同事或外部团队执行一次盲复现。
- 增加精确 gathering-key 或连续结构指标实验。
- 补充运行时间、UPC 次数、迭代分布和常数时间/时序风险。
- 增加第三个独立标定点，或给出首轮阈值偏移到局部 DFR 变化的半解析界。

### 不建议做

- 不要为了“像顶刊”堆叠更多图；当前四图三表已经覆盖主效应、机制、迁移/捕获边界、研究协议和核心比较。
- 不要把跨实现复核改写成独立实验室复现。
- 不要把 gathering-adjacent proxy 改写成 exact gathering-key。
- 不要把 FRO-2 写成优于 BIKE-Flip/Backflip 的生产级新译码器。

## 结论

本稿的合适定位是“QC-MDPC 密钥条件译码风险的实验方法与局部调度机制研究”，而不是完整的 BIKE 弱密钥检测或密码学安全证明。与 TIFS 类论文相比，当前版本已补齐摘要压缩、算法 1、源码入口、最小复现命令、wall-clock、跨实现术语和分层现代译码器表；尚不能由写作替代的缺口是精确 gathering-key 构造、外部盲复现、第三参数点、完整工程成本和生产尾部分析。
