-- 2026-06-22: portfolio_trade 费用字段精简
-- 适用版本: feature/mainwave-scorer-v2.4
-- 变更原因: 去掉冗余的 fee 合计字段，只保留 commission、stamp_tax、transfer_fee 三个明细字段；合计费用由前端/接口实时计算

-- 1. 确保 commission 字段存在
ALTER TABLE portfolio_trade ADD COLUMN IF NOT EXISTS commission DECIMAL(18,2) DEFAULT 0 COMMENT '券商佣金/手续费' AFTER amount;

-- 2. 补齐 NULL 值
UPDATE portfolio_trade SET fee = 0 WHERE fee IS NULL;
UPDATE portfolio_trade SET commission = 0 WHERE commission IS NULL;
UPDATE portfolio_trade SET stamp_tax = 0 WHERE stamp_tax IS NULL;
UPDATE portfolio_trade SET transfer_fee = 0 WHERE transfer_fee IS NULL;

-- 3. 将旧的 fee 合计拆分为 commission（仅对未设置 commission 的记录）
UPDATE portfolio_trade
SET commission = GREATEST(fee - stamp_tax - transfer_fee, 0)
WHERE fee > 0 AND commission = 0;

-- 4. 删除旧的 fee 字段
ALTER TABLE portfolio_trade DROP COLUMN IF EXISTS fee;

-- 5. 调整字段注释
ALTER TABLE portfolio_trade
MODIFY COLUMN commission DECIMAL(18,2) DEFAULT 0 COMMENT '券商佣金/手续费',
MODIFY COLUMN stamp_tax DECIMAL(18,2) DEFAULT 0 COMMENT '印花税',
MODIFY COLUMN transfer_fee DECIMAL(18,2) DEFAULT 0 COMMENT '过户费';
