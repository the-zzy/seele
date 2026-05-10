-- 添加每日盈亏快照表，持久化每日盈亏计算结果
-- 避免每次请求时全量重算

CREATE TABLE IF NOT EXISTS portfolio_daily_pnl (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date DATE NOT NULL COMMENT '交易日期',
    market_value FLOAT NOT NULL DEFAULT 0 COMMENT '当日收盘持仓总市值',
    daily_pnl FLOAT NOT NULL DEFAULT 0 COMMENT '当日盈亏',
    cumulative_pnl FLOAT NOT NULL DEFAULT 0 COMMENT '累计盈亏',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_trade_date (trade_date),
    KEY idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日盈亏快照表';
