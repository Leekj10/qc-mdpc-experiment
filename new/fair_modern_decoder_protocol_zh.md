# 现代译码器公平比较协议

修订稿把现代译码器证据分成不同比较层，而不是合并成单一排名。

| 层级 | 译码器 | 参数 | 语义 | 配对方式 | 解释 |
|---|---|---|---|---|---|
| 匹配静态比较 | C0、FRO-2、按规范公式实现的 BIKE-Flip | P1'=(4801,45,92) | 静态目标错误重量、零综合征成功 | 正式密钥池上的相同 (H,e,s) | 算法层比较；P1' 的 BIKE-Flip 系数由规范推导，不是官方参数 |
| 原生生产参考 | C0、FRO-2、spec-exact BIKE-Flip | Level 1=(12323,71,134) | BIKE-Flip 使用官方常数；载体方案使用本文静态规则 | 相同实例配对 | 生产边界和收敛检查；零失败时 DFR 不可分辨 |
| 语义参考 | C0、FRO-2、Backflip | P1' | C 参考实现的动态距离语义 | 参考实验内使用相同实例 | 不等价于可部署语义，因为阈值使用真实错误距离 |
| 工程参考 | C0、FRO-2、STLR、SR-NCW、BGF-C3 | P2/P3 | 静态 CLASSIC 阈值、统一 20 轮预算 | 每个单元使用相同实例配对 | 成本—DFR 参照；BGF-C3 不是官方调优 BGF |

每一层内部使用相同失败判据。统计不确定性以密钥为聚类单位进行 bootstrap，而不是把错误实例视为独立密钥。包内 BIKE-Flip 报告位于 `modern_comparison_data/bikeflip_p1_formal_report.json` 和 `modern_comparison_data/bikeflip_l1_report.json`，工程对照的配对区间位于 `engineering_data_v2/engineering_pairwise_rr.csv`。
