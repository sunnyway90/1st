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
