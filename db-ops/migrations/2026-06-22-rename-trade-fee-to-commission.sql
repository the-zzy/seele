-- 2026-06-22: portfolio_trade 费用字段精简
-- 适用版本: feature/mainwave-scorer-v2.4
-- 变更原因: 去掉冗余的 fee 合计字段，只保留 commission、stamp_tax、transfer_fee 三个明细字段；合计费用由前端/接口实时计算
-- 说明: 远程 MySQL 不支持 ALTER TABLE ... IF [NOT] EXISTS，所有字段变更均通过 information_schema 条件判断实现幂等

-- 1. 确保 commission 字段存在
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_trade' AND column_name = 'commission');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_trade ADD COLUMN commission DECIMAL(18,2) DEFAULT 0 COMMENT '券商佣金/手续费' AFTER amount",
    'SELECT "commission column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. 确保 stamp_tax 字段存在
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_trade' AND column_name = 'stamp_tax');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_trade ADD COLUMN stamp_tax DECIMAL(18,2) DEFAULT 0 COMMENT '印花税' AFTER commission",
    'SELECT "stamp_tax column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3. 确保 transfer_fee 字段存在
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_trade' AND column_name = 'transfer_fee');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_trade ADD COLUMN transfer_fee DECIMAL(18,2) DEFAULT 0 COMMENT '过户费' AFTER stamp_tax",
    'SELECT "transfer_fee column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 4. 补齐 NULL 值
UPDATE portfolio_trade SET commission = 0 WHERE commission IS NULL;
UPDATE portfolio_trade SET stamp_tax = 0 WHERE stamp_tax IS NULL;
UPDATE portfolio_trade SET transfer_fee = 0 WHERE transfer_fee IS NULL;

-- 5. 将旧的 fee 合计拆分为 commission（仅对未设置 commission 的记录）
UPDATE portfolio_trade
SET commission = GREATEST(fee - stamp_tax - transfer_fee, 0)
WHERE fee IS NOT NULL AND fee > 0 AND commission = 0;

-- 6. 删除旧的 fee 字段（如存在）
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_trade' AND column_name = 'fee');
SET @sql := IF(@exist = 1,
    'ALTER TABLE portfolio_trade DROP COLUMN fee',
    'SELECT "fee column already dropped" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 7. 调整字段注释
ALTER TABLE portfolio_trade
    MODIFY COLUMN commission DECIMAL(18,2) DEFAULT 0 COMMENT '券商佣金/手续费',
    MODIFY COLUMN stamp_tax DECIMAL(18,2) DEFAULT 0 COMMENT '印花税',
    MODIFY COLUMN transfer_fee DECIMAL(18,2) DEFAULT 0 COMMENT '过户费';
