# 数据库变更记录

## 2026-04-27
- `stock_daily_indicator` 表新增 `amount_ma5`、`amount_ma10` 字段
- 支持涨幅分布统计的成交额均值过滤条件

## 2026-05-06
- 新增 `portfolio_trade` 表，存储持仓交易记录（买入/卖出）
- 新增 `portfolio_closed` 表，存储清仓后的盈亏记录
- 新增 `portfolio_config` 表，存储初始资金等持仓配置
- 支持持仓管理、每日盈亏计算与收益图表分析

## 2026-04-26
- 初始表结构快照
- 表: `stock_basic`, `stock_daily`
- 新增 `stock_daily_indicator` 表，存储日线均线及平均成交量、平均换手率指标
