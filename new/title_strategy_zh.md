# 题目策略与选择

## 推荐主标题

**可测工作点下 QC-MDPC 比特翻转译码的首轮阈值稳定化：密钥条件研究**

## 选择理由

1. “可测工作点”和“密钥条件研究”准确限定了实验对象，避免把 Type-I、近码字和 gathering-adjacent proxy 混成同一类自然弱密钥。
2. “首轮稳定化”准确描述 FRO-2 的核心干预，比“新译码器”或“低 DFR 算法”更符合证据。
3. 标题不把论文包装成完整弱密钥分析；机制解释和真实近码字捕获边界在正文展开，跨实现复核作为方法证据而不是外部复现承诺。
4. 标题不使用“最优”“普适”“生产级优势”“解决 BIKE DFR”等不可由当前数据支持的措辞。

## 可用于英文投稿的对应标题

**First-Round Threshold Stabilization in QC-MDPC Bit-Flipping Decoding: A Key-Conditional Study at Measurable Operating Points**

## 不推荐的标题

- “A Novel QC-MDPC Decoder...” ：FRO-2 是 CLASSIC 的局部调度干预，不宜包装成完整新译码器。
- “A Universal Defense against Gathering Weak Keys...” ：当前没有精确 gathering-key 实验，且真实捕获条件下 FRO-2 无保护。
- “Optimal Threshold Selection...” ：搜索只覆盖预定义候选，不能支持全局最优。
