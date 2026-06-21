# 数据库变更记录

## 2026-06-22
- `portfolio_trade` 费用字段精简：删除 `fee` 合计字段，保留 `commission`、`stamp_tax`、`transfer_fee` 三个明细字段
- 合计费用由前端/接口实时计算，不再冗余存储
- 数据库层面对已有数据：将旧 `fee` 按 `commission = GREATEST(fee - stamp_tax - transfer_fee, 0)` 拆分填入 `commission`
- 适用版本：v2.4

## 2026-06-18
- `sync_job_log.extra_info` 从 `varchar(1000)` 扩容为 `text`
- 新增回测模块表：`backtest_run`、`backtest_trade`、`backtest_daily_snapshot`、`backtest_decision_log`、`backtest_task`
- 适用版本：v2.4

## 2026-06-15
- `portfolio_trade` 新增 `commission`、`stamp_tax`、`transfer_fee` 三个费用明细字段
- `portfolio_config` 新增 `commission_rate`、`stamp_tax_rate`、`transfer_rate` 默认费率字段
- 适用版本：v2.4

## 2026-06-08
- `board_constituent` 表新增 `name` 字段，用于存储成分股名称
- 适用版本：v2.4

## 2026-05-30
- 多项字段类型从 `FLOAT` 迁移到 `DECIMAL`，提升财务数据精度
- 适用版本：v2.1

## 2026-05-29
- 全库 collation 统一为 `utf8mb4_unicode_ci`
- 适用版本：v2.1

## 2026-05-28
- `portfolio_trade` 新增 `dividend` 字段，记录分红金额
- 新增 `visitor_log` 表，记录访客访问日志
- 适用版本：v2.1

## 2026-05-25
- 添加性能优化索引
- `stock_basic` 去重处理
- 适用版本：v2.1

## 2026-05-09
- 新增 `portfolio_daily_position` 每日持仓明细表
- 新增 `portfolio_daily_summary` 每日资产汇总表
- 适用版本：v2.1

## 2026-05-07
- 新增 `portfolio_position` 持仓快照表
- 适用版本：v2.1

## 2026-05-06
- 新增 `portfolio_trade` 表，存储持仓交易记录（买入/卖出）
- 新增 `portfolio_closed` 表，存储清仓后的盈亏记录
- 新增 `portfolio_config` 表，存储初始资金等持仓配置
- 支持持仓管理、每日盈亏计算与收益图表分析

## 2026-04-27
- `stock_daily_indicator` 表新增 `amount_ma5`、`amount_ma10` 字段
- 支持涨幅分布统计的成交额均值过滤条件

## 2026-04-26
- 初始表结构快照
- 表: `stock_basic`, `stock_daily`
- 新增 `stock_daily_indicator` 表，存储日线均线及平均成交量、平均换手率指标
