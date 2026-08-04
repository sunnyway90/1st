# 导读：Fama & French (1993) Common Risk Factors in the Returns on Stocks and Bonds

**标签**：三因子 · SMB · HML · 时间序列  
**出处**：Journal of Financial Economics, 1993  
**本地**：`papers/fama_french_1993_common_risk_factors.pdf`

## 一句话

把 1992 的横截面发现改写成 **可交易因子组合** 的时间序列模型：股票收益由 **市场 + SMB + HML** 共同驱动；债券另有期限与违约因子。

## 三因子形式

\[
R_i - R_f = a_i + b_i(R_m-R_f) + s_i\,\mathrm{SMB} + h_i\,\mathrm{HML} + e_i
\]

- **SMB**：小市值组合收益 − 大市值组合收益  
- **HML**：高 B/M − 低 B/M（价值减成长）

## 关键结论

1. 三股票市场因子能解释多数股票组合平均收益与共同变动。
2. 用 **时间序列回归斜率** 作为因子载荷，对股票和债券都有清晰风险敏感度解释（相对纯特征横截面回归更便于加入债券）。
3. 债券侧：期限与违约相关因子捕捉国债/公司债共同变动；低等级公司债另当别论。

## 实务含义

- Ken French 数据库按类似规则公开月度/日度因子，是回测基准。
- 检验新策略时常报告相对 FF3 的 α。

## 向 LLM 可问

- 「SMB/HML 怎么排序构建？」
- 「时间序列三因子和 Fama–MacBeth 横截面有何区别？」
