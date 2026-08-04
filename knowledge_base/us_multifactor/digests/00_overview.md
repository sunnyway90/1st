# 美股多因子总览（路线图）

本资料库面向：**美股横截面多因子 / 因子投资**。内容包括开放获取论文全文（PDF + 抽取文本）、论文中文导读、推荐书籍导读，以及可被大模型检索的文本块（`chunks/chunks.jsonl`）。

## 核心故事线

1. **CAPM 不够用**：市场 β 单独解释不了平均收益横截面。
2. **Fama–French 1992/1993**：规模（Size）与价值（B/M → HML）进入标准模型 → **三因子**。
3. **Jegadeesh–Titman / Carhart**：短期横截面动量 → **四因子**（+WML/UMD）。
4. **盈利与投资**：Novy-Marx 毛利率；Fama–French **五因子**（+RMW, +CMA）；Hou–Xue–Zhang **q-factor**（投资 + ROE）。
5. **AQR 实务扩展**：价值×动量全球（Value and Momentum Everywhere）、质量（QMJ）、低β（BAB）。

## 常用因子速查

| 因子 | 常见多空定义 | 关键论文 |
|------|--------------|----------|
| Market | Rm − Rf | CAPM / FF |
| Size (SMB) | 小市值 − 大市值 | FF 1992/93 |
| Value (HML) | 高 B/M − 低 B/M | FF 1992/93 |
| Momentum (WML) | 过去赢家 − 输家（常跳过近月） | JT 1993, Carhart 1997 |
| Profitability (RMW) | 高盈利 − 低盈利 | FF 2015, Novy-Marx 2013 |
| Investment (CMA) | 低投资 − 高投资 | FF 2015 |
| q 投资 / ROE | 低 I/A − 高 I/A；高 ROE − 低 ROE | Hou–Xue–Zhang 2015 |
| Quality (QMJ) | 高质量 − 垃圾 | Asness et al. |
| BAB | 杠杆低β − 高β | Frazzini–Pedersen |

## 数据从哪下

- Ken French Data Library：官方 FF 因子与组合
- AQR Datasets：QMJ、BAB、Value/Momentum 等
- Global-q：q-factor

## 怎么用本库回答问题

```bash
PYTHONPATH=src python3 -m multifactor_kb search "为什么价值要和动量一起用"
PYTHONPATH=src python3 -m multifactor_kb ask "五因子里 HML 为什么会冗余"
PYTHONPATH=src python3 -m multifactor_kb list
```

`search` 返回最相关文本块；`ask` 打印可直接粘贴给大模型的「检索上下文 + 问题」提示词。

## 版权说明

- 论文 PDF 仅收录作者/机构公开可下载的版本链接与本地副本，便于离线检索。
- **电子书不提供全文**，只给合法购买链接与导读。请勿把盗版 PDF 放进仓库。
