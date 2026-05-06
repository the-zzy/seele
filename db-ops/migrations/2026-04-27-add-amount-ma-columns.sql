-- 为 stock_daily_indicator 表添加成交额均值字段
-- 执行时间: 2026-04-27
-- 说明: 支持涨幅分布统计的成交额过滤条件

ALTER TABLE `stock_daily_indicator`
  ADD COLUMN `amount_ma5` decimal(15,2) DEFAULT NULL COMMENT '5日平均成交额' AFTER `vol_ma10`,
  ADD COLUMN `amount_ma10` decimal(15,2) DEFAULT NULL COMMENT '10日平均成交额' AFTER `amount_ma5`;
