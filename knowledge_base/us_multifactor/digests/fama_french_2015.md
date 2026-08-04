# 导读：Fama & French (2015) A Five-Factor Asset Pricing Model

**标签**：五因子 · RMW · CMA · HML 冗余  
**出处**：Journal of Financial Economics, 2015  
**本地**：`papers/fama_french_2015_five_factor.pdf`

## 一句话

在三因子上加入 **盈利（RMW）** 与 **投资（CMA）**，对规模/价值/盈利/投资相关的平均收益描述更好；在作者样本中，加入后 **HML 常变得冗余**。

## 模型

\[
R_i-R_f=a_i+b_i Mkt + s_i SMB + h_i HML + r_i RMW + c_i CMA + e_i
\]

- **RMW**（Robust Minus Weak）：高运营盈利 − 低运营盈利  
- **CMA**（Conservative Minus Aggressive）：低投资（资产增长慢）− 高投资  

经济直觉常借助股利折现/估值恒等式：在其他条件相近时，更高预期盈利、更低投资（或更低价格）对应更高预期收益。

## 关键结论

1. 五因子整体优于三因子。
2. 主要硬伤：解释不了 **小市值 + 低盈利 + 高投资** 类股票的很低平均收益。
3. 因子具体定义方式（2×3 等）对主要结论不特别敏感。
4. 样本内 HML 对描述平均收益似乎多余——作者提醒可能具有样本特殊性，实务上许多人仍保留价值暴露。

## 与 Novy-Marx / q-factor

- 盈利维度与 Novy-Marx 毛利率文献一脉相承。  
- Hou–Xue–Zhang q-factor 用投资与 ROE，结构相近但理论动机与构建细节不同。

## 向 LLM 可问

- 「RMW 和 CMA 如何定义？」
- 「为什么加了盈利和投资后 HML 可能冗余？」
