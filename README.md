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

快照 CSV 还会保存 24h `high` / `low` / `last` / `volume_usd`，供没有 tick 时估计流动性和限价成交。

### 无 tick 时的流动性与挂单成交

不要用 mark / mid 当成交价。小资金、宽价差、等恐慌成交时，回测至少要同时看四件事：

1. **流动性刻画**：相对价差 `(ask-bid)/mid`、用 Black-76 vega 把价差换成 IV 点、是否双边报价、24h 成交量、持仓量、换手、last 是否还在买卖价之间。
2. **预定限价**：限价只能用上一根快照的买一/卖一生成，例如买单挂在 `bid - k * spread`。不能用当天的 low 当买入价，那是偷看了当天最低点。
3. **触及 + 成交量**：只有 24h low/high 或 OHLC bar 真正穿越该限价，并且 bar 成交量足够覆盖你的张数（默认最多吃该 bar 成交量的 10%）才算成交。成交价是限价，不是 bar 的最低/最高。
4. **逆向选择**：成交后用买一（多头）或卖一（空头）或 bar close 盯市。恐慌里成交后价格继续走坏，会记成 adverse selection，而不是完美抄底。

评分桶：`liquid` / `tradable_passive` / `fragile` / `unusable`。策略是否靠谱看 `verdict`：`plausible_if_patient`、`fragile`、`spread_dominates`、`no_capacity`、`untradable`。`required_edge` 是半价差加上成交后的中位逆向选择，你的信号优势必须明显大于它。

对整条期权链打流动性分：

```bash
PYTHONPATH=src python3 -m deribit_options --liquidity --size 0.1 --side buy --passive-spreads 1.0
```

用小时 OHLC（不是 tick）估计“先看第一根收盘，再把限价挂到价差之外，后面会不会成交”：

```bash
PYTHONPATH=src python3 -m deribit_options --fill-sim --size 0.1 --side buy --passive-spreads 1.0 --resolution 60 --lookback-hours 168
```

如果已经按天存了快照，用快照里的 24h high/low 做同样的无前瞻成交估计：

```bash
PYTHONPATH=src python3 -m deribit_options --history-csv data/btc_option_snapshots.csv --fill-sim --require-panic
```

`--require-panic` 只统计标的大动、IV 跳升或期权自身振幅很大的 bar。更细的 OHLC 来自 `public/get_tradingview_chart_data`；当前买一/卖一数量和 bid IV / ask IV 来自 `public/ticker`。

## 微信公众号文章抓取工具 (`wechat_scraper`)

项目包含 `wechat_scraper` 模块，用于抓取微信公众号文章并导出为 Markdown / HTML / JSON / TXT。

### 模式 1：单篇文章（无需登录）

直接抓取公开文章链接：

```bash
python3 -m pip install -e .
python3 -m wechat_scraper fetch "https://mp.weixin.qq.com/s/YCs1l2lkHeoqcuYMdxY6ZA" --format md
```

### 模式 2：批量抓取（需要自己的公众号后台登录态）

1. 浏览器打开 [微信公众平台](https://mp.weixin.qq.com/) 并扫码登录
2. 打开开发者工具 (F12) → Network，刷新页面
3. 从任意请求中复制 `Cookie`，以及 URL 里的 `token=...` 参数

```bash
export WECHAT_MP_COOKIE='你的cookie'
export WECHAT_MP_TOKEN='你的token'

# 搜索公众号，拿到 fakeid
python3 -m wechat_scraper search "人民日报"

# 列出最近文章
python3 -m wechat_scraper list --fakeid <fakeid> --count 10

# 批量下载正文
python3 -m wechat_scraper download --fakeid <fakeid> --limit 20 --format md
```

注意：批量模式调用的是公众号后台搜索/列表接口，请控制频率，避免账号被限制。仅建议用于个人学习、备份自己关注的公开内容。
