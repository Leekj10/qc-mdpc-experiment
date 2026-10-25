# 补充实验报告

本轮补充实验采用新的主种子 `20260911`，不覆盖原正式结果。

## 实验矩阵

| 层次 | 参数 | 条件 | 调度 | 密钥/错误规模 |
|---|---|---|---|---|
| 时序位置与幅度 | `P2=(3001,37,66)` | RAND、TYPE-I、NCW-shallow | C0、FRO-1、FRO-2、FRO-3、FRO-4、Round-2 +2、Uniform +2 | 每组 12 把密钥，每把 400 个错误 |
| 第三个工作点 | `P3=(4001,41,82)` | RAND、TYPE-I、NCW-shallow | 同上 | 每组 12 把密钥，每把 400 个错误 |

第三个工作点先用 4 把新 RAND 密钥、每个候选 `t` 300 个错误进行标定；在 `t∈{70,72,74,76,78,80,82}` 中，选择 `t=82`，因为其 C0 观测 DFR 为 `2.5×10^-3`，落入可测区间。

## 主要观察

- `Uniform +2` 在 P2/P3 的三个条件下均显著恶化，观测 DFR 约为 `0.079--0.189`。
- `Round-2 +2` 在 P2 的 RAND 和 NCW-shallow 中没有优于 C0，在 TYPE-I 中也未显示稳定收益。
- P2 上 FRO-1/FRO-2 通常优于 C0，但低失败数下密钥聚类区间较宽，不能替代原有正式迁移结果。
- P3 上 RAND 的 FRO-2 汇总 DFR 为 `4.17×10^-4`，C0/FRO-2 风险比为 4.00；TYPE-I 的 FRO-3 汇总 DFR 为 `2.08×10^-4`，风险比为 8.00。
- P3 的 NCW-shallow 批次中 C0 没有失败，因此该条件下的处理效应无法分辨。
- 首轮偏移增加会提高平均迭代数，体现出 DFR 与收敛成本之间的权衡。

## 统计与解释边界

每个单元包含 12 把密钥和 4,800 个配对实例。DFR 为观测失败数除以试验数；零失败仅给出 Wilson 上界 `3/4800=6.25×10^-4`。风险比区间采用 10,000 次、以密钥为重采样单位的百分位 bootstrap。该规模用于补充敏感性和调度形状检查，不用于替换 92--94 把密钥的正式结果，也不支持 BIKE 生产参数 DFR 改善的结论。

## 文件

- 原始矩阵：`supplemental_data_full/p2_temporal_ablation/matrix.json`、`supplemental_data_full/p3_third_point/matrix.json`
- 聚类分析：`supplemental_data_full/supplemental_analysis.json`
- 图表源表：`supplemental_data_full/temporal_ablation_source.csv`
- 图表脚本：`make_supplemental_figure.py`
- 图表：`publication_figures/fig5_temporal_ablation.{pdf,svg,png}`

本轮没有把 FRO-2 宣称为 BIKE-Flip 的普遍替代，也没有把 NCW-shallow 称为精确 gathering-key。原有 BIKE-Flip/Backflip 比较仍作为现代译码器参照，补充实验的新增价值是识别“时序位置 × 偏移幅度”的交互边界。
