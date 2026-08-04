# 美股多因子资料库

面向 LLM 检索的美股多因子（factor investing）知识库：开放论文 PDF + 文本抽取、中文导读、书籍导读（无盗版全文）、以及关键词检索脚本。

## 目录结构

```
knowledge_base/us_multifactor/
  catalog/catalog.yaml   # 论文/书籍/数据源总目录
  digests/               # 中文导读（优先给 LLM）
  papers/                # 开放获取 PDF
  extracted/             # PDF 纯文本
  chunks/chunks.jsonl    # RAG 文本块
```

## 快速检索

```bash
PYTHONPATH=src python3 -m multifactor_kb list
PYTHONPATH=src python3 -m multifactor_kb search "价值与动量为什么负相关"
PYTHONPATH=src python3 -m multifactor_kb ask "五因子里 HML 为什么可能冗余"
```

把 `ask` 输出的提示词粘贴给任意大模型即可做「只依据资料库」的问答。

## 收录内容（摘要）

**论文（本地 PDF）**：Fama–French 1992/1993/2015、Novy-Marx 毛利率、Hou–Xue–Zhang q-factor、Value and Momentum Everywhere、Quality Minus Junk、Betting Against Beta、Fact/Fiction Value 等。

**论文（导读，无本地 PDF）**：Jegadeesh–Titman 动量、Carhart 四因子。

**书籍（仅导读 + 购买链接）**：Berkin & Swedroe《Factor-Based Investing》、Chincarini & Kim《QEPM》、Gray & Carlisle《Quantitative Value》、Antonacci《Dual Momentum》、López de Prado《AFML》。

**数据**：Ken French Data Library、AQR Datasets、Global-q。

## 版权

仅收录作者/机构公开可下载文献。电子书请自行合法购买，请勿向仓库添加盗版全文。
