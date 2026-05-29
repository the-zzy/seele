-- 2026-05-28: portfolio_trade 表新增 dividend 字段
-- 适用版本: feature/mainwave-scorer-v2
-- 变更原因: 支持交易记录填写分红金额，纳入清仓盈亏计算

ALTER TABLE portfolio_trade
ADD COLUMN dividend FLOAT DEFAULT 0 COMMENT '分红金额' AFTER fee;
