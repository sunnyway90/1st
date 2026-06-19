# 债券收益率曲线计算模块

这是一个使用 Python、numpy、scipy、matplotlib 编写的债券收益率曲线计算示例项目。

## 功能

- 固定利率债券现金流生成
- 连续复利零息收益率曲线表示
- 基于市场债券价格的零息曲线 bootstrap
- 债券定价、到期收益率求解、远期利率计算
- 演示用 `main` 函数输出曲线结果并保存图表

## 运行演示

```bash
python3 -m pip install -e .
python3 -m yield_curve
```

演示会在当前目录生成 `yield_curve_demo.png`。

## 运行测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Deribit 比特币期权数据模块

项目也包含 `deribit_options` 模块，用于获取 Deribit 公开 API 的 BTC 期权数据，并基于保存的日度快照计算平值（ATM）期权变化。

Deribit 期权数据特征：

- 公开 HTTP API 地址为 `https://www.deribit.com/api/v2`，公共行情接口无需认证。
- 期权合约名通常为 `BTC-到期日-行权价-C/P`，例如 `BTC-9DEC24-102000-C`。
- `public/get_instruments` 提供到期日、行权价、期权类型等静态合约信息。
- `public/get_book_summary_by_currency?currency=BTC&kind=option` 提供当前 mark price、mark IV、标的价格、买卖价、持仓量和成交量。
- Deribit 公共接口直接提供当前 option chain 快照；ATM 历史日度变化需要定时保存快照，之后从 CSV 历史文件回放分析。
- `public/get_historical_volatility` 是标的历史波动率，不是期权链历史隐含波动率。

抓取当前 BTC 期权快照并追加到 CSV：

```bash
PYTHONPATH=src python3 -m deribit_options --snapshot-csv data/btc_option_snapshots.csv
```

从已保存快照计算 ATM 日度变化：

```bash
PYTHONPATH=src python3 -m deribit_options --history-csv data/btc_option_snapshots.csv --target-days-to-expiration 30
```

模块会在每个交易日选取最新快照，按目标到期日或目标剩余期限选择期权到期月，再用标的价格与行权价距离最小的 call/put 组合计算 ATM 的标的价格、行权价、平均 mark IV、跨式 mark price 及其日度变化。
