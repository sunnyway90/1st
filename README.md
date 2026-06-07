# 我的第一个仓库

这是用来学习编程的仓库。

## 下载美股日线数据

仓库包含一个纯 Python 标准库脚本，可以下载美国当前上市股票从 2010 年至今的日线数据，并按股票保存为 CSV。

```bash
python3 scripts/download_us_daily.py \
  --start 2010-01-01 \
  --output data/us_daily \
  --manifest data/us_daily_manifest.csv \
  --workers 4
```

输出：

- `data/us_daily/AAPL.csv`：单只股票的日线数据，字段为 `Date,Open,High,Low,Close,Adj Close,Volume`。
- `data/us_daily_manifest.csv`：每只股票的下载状态、行数、输出路径和错误信息。

常用选项：

- `--symbols AAPL,MSFT,NVDA`：只下载指定股票。
- `--symbols-file symbols.txt`：从文本文件读取股票代码，每行一个。
- `--limit 10`：只下载前 10 只股票，适合先做烟测。
- `--include-etfs`：同时下载 ETF；默认只下载股票。
- `--force`：覆盖已存在的 CSV；默认会跳过已有文件，便于断点续跑。

示例烟测：

```bash
python3 scripts/download_us_daily.py --symbols AAPL,MSFT --limit 2 --output data/smoke --manifest data/smoke_manifest.csv
```

数据源说明：

- 股票清单来自 Nasdaq Trader 的 `nasdaqlisted.txt` 和 `otherlisted.txt`，覆盖当前美国主要交易所上市证券。
- 价格数据来自 Yahoo Finance 图表接口。
- 这个免费组合不包含完整历史退市股票，因此不能消除幸存者偏差。如果你需要“2010 年至今曾经上市过的全部股票”，应使用 Polygon、Tiingo、Nasdaq Data Link、CRSP 等包含退市证券和历史代码变更的数据源。
