-- v2.4 部署 SQL 汇总
-- 适用版本: feature/mainwave-scorer-v2.4
-- 执行顺序: 先改现有表，再建新表
-- 注意: 执行前请先备份数据库

-- ============================================================
-- 1. portfolio_trade 交易费用拆分
-- ============================================================
-- 佣金不再单独存储，统一作为 fee（手续费合计）的一部分。
-- fee = 券商佣金（不免五最低 5 元）+ 印花税 + 过户费。

ALTER TABLE portfolio_trade
    DROP COLUMN IF EXISTS commission,
    ADD COLUMN IF NOT EXISTS stamp_tax DECIMAL(18,2) DEFAULT 0 COMMENT '印花税' AFTER amount,
    ADD COLUMN IF NOT EXISTS transfer_fee DECIMAL(18,2) DEFAULT 0 COMMENT '过户费' AFTER stamp_tax;

-- fee 字段为三费合计，并扩容精度
ALTER TABLE portfolio_trade
    MODIFY COLUMN fee DECIMAL(18,2) DEFAULT 0 COMMENT '交易手续费合计';


-- ============================================================
-- 2. portfolio_config 新增默认费率字段
-- ============================================================

ALTER TABLE portfolio_config
    ADD COLUMN IF NOT EXISTS commission_rate DECIMAL(18,6) DEFAULT 0.000235 COMMENT '佣金费率' AFTER initial_capital,
    ADD COLUMN IF NOT EXISTS stamp_tax_rate DECIMAL(18,6) DEFAULT 0.0005 COMMENT '印花税税率' AFTER commission_rate,
    ADD COLUMN IF NOT EXISTS transfer_rate DECIMAL(18,6) DEFAULT 0.00001 COMMENT '过户费费率' AFTER stamp_tax_rate;

-- 对已有配置行写入默认值（避免 NULL）
UPDATE portfolio_config
SET commission_rate = 0.000235,
    stamp_tax_rate = 0.0005,
    transfer_rate = 0.00001
WHERE commission_rate IS NULL;


-- ============================================================
-- 3. sync_job_log.extra_info 扩容
-- ============================================================

ALTER TABLE sync_job_log
    MODIFY COLUMN extra_info TEXT COMMENT '额外信息';


-- ============================================================
-- 4. 新增回测模块表
-- ============================================================

CREATE TABLE IF NOT EXISTS backtest_run (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE NULL COMMENT '结束日期（自动运行用）',
    current_date DATE NOT NULL COMMENT '当前已处理日期',
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
