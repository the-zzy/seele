-- 2026-06-15: portfolio_trade 费用明细拆分
-- 适用版本: feature/mainwave-scorer-v2.4
-- 变更原因: 交易费用拆分为佣金、印花税、过户费三个明细字段，并支持配置默认费率

-- 1. 给 portfolio_trade 新增三费明细字段
ALTER TABLE portfolio_trade
ADD COLUMN commission DECIMAL(18,2) DEFAULT 0 COMMENT '手续费/佣金' AFTER amount,
ADD COLUMN stamp_tax DECIMAL(18,2) DEFAULT 0 COMMENT '印花税' AFTER commission,
ADD COLUMN transfer_fee DECIMAL(18,2) DEFAULT 0 COMMENT '过户费' AFTER stamp_tax;

-- 2. 调整 fee 字段精度与注释，作为三费合计
ALTER TABLE portfolio_trade
MODIFY COLUMN fee DECIMAL(18,2) DEFAULT 0 COMMENT '交易手续费合计';

-- 3. 给 portfolio_config 新增默认费率字段
ALTER TABLE portfolio_config
ADD COLUMN commission_rate DECIMAL(18,6) DEFAULT 0.000235 COMMENT '佣金费率' AFTER initial_capital,
ADD COLUMN stamp_tax_rate DECIMAL(18,6) DEFAULT 0.0005 COMMENT '印花税税率' AFTER commission_rate,
ADD COLUMN transfer_rate DECIMAL(18,6) DEFAULT 0.00001 COMMENT '过户费费率' AFTER stamp_tax_rate;

-- 4. 对已有配置行写入默认值（避免 NULL）
UPDATE portfolio_config
SET commission_rate = 0.000235,
    stamp_tax_rate = 0.0005,
    transfer_rate = 0.00001
WHERE commission_rate IS NULL;
