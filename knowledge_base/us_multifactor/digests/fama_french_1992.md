# 导读：Fama & French (1992) The Cross-Section of Expected Stock Returns

**标签**：基础文献 · Size · Value · β 之谜  
**出处**：Journal of Finance, 1992  
**本地**：`papers/fama_french_1992_cross_section.pdf`（扫描版，抽取质量一般）

## 一句话

用 **规模** 与 **账面市值比（B/M）** 就能基本抓住美股平均收益的横截面差异；单独看市场 β，在控制规模后与平均收益关系几乎是 **平的**。

## 关键结论

1. **Size**：小市值股票平均收益更高（Banz 规模效应再确认）。
2. **Value**：高 B/M（价值股）平均收益高于低 B/M（成长股）。
3. Size + B/M 组合后，可吸收与杠杆、E/P 等相关的横截面模式。
4. 允许 β 中与规模无关的变动后，β–收益关系平坦 → 对 Sharpe–Lintner–Black CAPM 的严重挑战。

## 方法要点

- Fama–MacBeth 横截面回归：每月把个股收益对特征（β、Size、B/M、E/P、杠杆等）回归，再对斜率时间序列求均值。
- β 估计与分组设计对结论敏感，但「β 解释力弱、Size/B/M 强」这一主线稳健。

## 对后来的影响

直接催生 1993 三因子时间序列模型（SMB、HML），成为量化与学术因子研究的起点。

## 向 LLM 可问

- 「1992 文为什么说 CAPM 的 β 不够？」
- 「B/M 和 E/P、杠杆之间是什么关系？」
