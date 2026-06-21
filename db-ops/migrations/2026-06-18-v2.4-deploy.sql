-- v2.4 部署 SQL 汇总
-- 适用版本: feature/mainwave-scorer-v2.4
-- 执行顺序: 先改现有表，再建新表
-- 注意: 执行前请先备份数据库
-- 说明: 远程 MySQL 不支持 ALTER TABLE ... IF [NOT] EXISTS，所有字段变更均通过 information_schema 条件判断实现幂等

-- ============================================================
-- 1. portfolio_trade 交易费用字段
-- ============================================================
-- 最终结构：保留 commission、stamp_tax、transfer_fee 三个明细字段，删除 fee 合计字段

-- 1.1 添加 commission 字段（如不存在）
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_trade' AND column_name = 'commission');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_trade ADD COLUMN commission DECIMAL(18,2) DEFAULT 0 COMMENT '券商佣金/手续费' AFTER amount",
    'SELECT "commission column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 1.2 添加 stamp_tax 字段（如不存在）
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_trade' AND column_name = 'stamp_tax');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_trade ADD COLUMN stamp_tax DECIMAL(18,2) DEFAULT 0 COMMENT '印花税' AFTER commission",
    'SELECT "stamp_tax column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 1.3 添加 transfer_fee 字段（如不存在）
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_trade' AND column_name = 'transfer_fee');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_trade ADD COLUMN transfer_fee DECIMAL(18,2) DEFAULT 0 COMMENT '过户费' AFTER stamp_tax",
    'SELECT "transfer_fee column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 1.4 补齐 NULL 值
UPDATE portfolio_trade SET commission = 0 WHERE commission IS NULL;
UPDATE portfolio_trade SET stamp_tax = 0 WHERE stamp_tax IS NULL;
UPDATE portfolio_trade SET transfer_fee = 0 WHERE transfer_fee IS NULL;

-- 1.5 删除旧的 fee 合计字段（如存在）
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_trade' AND column_name = 'fee');
SET @sql := IF(@exist = 1,
    'ALTER TABLE portfolio_trade DROP COLUMN fee',
    'SELECT "fee column already dropped" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 1.6 统一字段注释与类型
ALTER TABLE portfolio_trade
    MODIFY COLUMN commission DECIMAL(18,2) DEFAULT 0 COMMENT '券商佣金/手续费',
    MODIFY COLUMN stamp_tax DECIMAL(18,2) DEFAULT 0 COMMENT '印花税',
    MODIFY COLUMN transfer_fee DECIMAL(18,2) DEFAULT 0 COMMENT '过户费';


-- ============================================================
-- 2. portfolio_config 新增默认费率字段
-- ============================================================

-- 2.1 添加 commission_rate 字段（如不存在）
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_config' AND column_name = 'commission_rate');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_config ADD COLUMN commission_rate DECIMAL(18,6) DEFAULT 0.000235 COMMENT '佣金费率' AFTER initial_capital",
    'SELECT "commission_rate column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2.2 添加 stamp_tax_rate 字段（如不存在）
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_config' AND column_name = 'stamp_tax_rate');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_config ADD COLUMN stamp_tax_rate DECIMAL(18,6) DEFAULT 0.0005 COMMENT '印花税税率' AFTER commission_rate",
    'SELECT "stamp_tax_rate column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2.3 添加 transfer_rate 字段（如不存在）
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'portfolio_config' AND column_name = 'transfer_rate');
SET @sql := IF(@exist = 0,
    "ALTER TABLE portfolio_config ADD COLUMN transfer_rate DECIMAL(18,6) DEFAULT 0.00001 COMMENT '过户费费率' AFTER stamp_tax_rate",
    'SELECT "transfer_rate column already exists" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2.4 对已有配置行写入默认值（避免 NULL）
UPDATE portfolio_config
SET commission_rate = 0.000235,
    stamp_tax_rate = 0.0005,
    transfer_rate = 0.00001
WHERE commission_rate IS NULL OR stamp_tax_rate IS NULL OR transfer_rate IS NULL;


-- ============================================================
-- 3. sync_job_log.extra_info 扩容为 TEXT
-- ============================================================

ALTER TABLE sync_job_log MODIFY COLUMN extra_info TEXT COMMENT '额外信息';


-- ============================================================
-- 4. 新增回测模块表
-- ============================================================

CREATE TABLE IF NOT EXISTS backtest_run (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE NULL COMMENT '结束日期（自动运行用）',
    `current_date` DATE NOT NULL COMMENT '当前已处理日期',
    initial_capital DECIMAL(18, 4) NOT NULL DEFAULT 40000 COMMENT '初始资金',
    cash DECIMAL(18, 4) NOT NULL DEFAULT 40000 COMMENT '剩余现金',
    status VARCHAR(20) NOT NULL DEFAULT 'running' COMMENT '状态 running/completed/failed',
    total_market_value DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '持仓总市值',
    total_return_pct DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '总收益率%',
    ai_model VARCHAR(50) NOT NULL DEFAULT 'deepseek-v4-pro' COMMENT 'AI 模型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_backtest_run_status (status),
    INDEX idx_backtest_run_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回测运行表';


CREATE TABLE IF NOT EXISTS backtest_trade (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL COMMENT '回测ID',
    symbol VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NULL COMMENT '股票名称',
    trade_type VARCHAR(10) NOT NULL COMMENT '交易类型 BUY/SELL',
    trade_date DATE NOT NULL COMMENT '交易日期',
    price DECIMAL(18, 4) NOT NULL COMMENT '成交价格',
    quantity INT NOT NULL COMMENT '成交股数（100倍数）',
    amount DECIMAL(18, 4) NOT NULL COMMENT '成交金额',
    fee DECIMAL(18, 4) DEFAULT 0 COMMENT '手续费',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_backtest_trade_run_id (run_id),
    INDEX idx_backtest_trade_trade_date (trade_date),
    CONSTRAINT fk_backtest_trade_run FOREIGN KEY (run_id) REFERENCES backtest_run(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回测交易记录表';


CREATE TABLE IF NOT EXISTS backtest_daily_snapshot (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL COMMENT '回测ID',
    trade_date DATE NOT NULL COMMENT '交易日期',
    cash DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '现金',
    total_market_value DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '总市值',
    total_asset DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '总资产',
    daily_pnl DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '当日盈亏',
    cumulative_pnl DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '累计盈亏',
    unrealized_pnl DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '浮动盈亏',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_backtest_snapshot_run_id (run_id),
    UNIQUE KEY uq_backtest_snapshot_run_date (run_id, trade_date),
    CONSTRAINT fk_backtest_snapshot_run FOREIGN KEY (run_id) REFERENCES backtest_run(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回测每日快照表';


CREATE TABLE IF NOT EXISTS backtest_decision_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL COMMENT '回测ID',
    trade_date DATE NOT NULL COMMENT '交易日期',
    prompt_snapshot TEXT NULL COMMENT '提示词快照',
    llm_raw_response TEXT NULL COMMENT 'LLM 原始响应',
    parsed_actions TEXT NULL COMMENT '解析后的动作(JSON)',
    latency_ms INT NULL COMMENT '耗时(ms)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_backtest_decision_run_id (run_id),
    CONSTRAINT fk_backtest_decision_run FOREIGN KEY (run_id) REFERENCES backtest_run(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回测 AI 决策日志表';


CREATE TABLE IF NOT EXISTS backtest_task (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL COMMENT '任务UUID',
    run_id INT NULL COMMENT '回测ID',
    status VARCHAR(20) NOT NULL DEFAULT 'running' COMMENT '状态 running/success/failed',
    result_json TEXT NULL COMMENT '任务结果JSON',
    error TEXT NULL COMMENT '错误信息',
    progress_current INT NULL COMMENT '进度当前值',
    progress_total INT NULL COMMENT '进度总数',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    finished_at TIMESTAMP NULL COMMENT '结束时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_backtest_task_task_id (task_id),
    INDEX idx_backtest_task_run_status (run_id, status),
    CONSTRAINT fk_backtest_task_run FOREIGN KEY (run_id) REFERENCES backtest_run(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回测后台任务表';
