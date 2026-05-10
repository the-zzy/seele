-- 删除旧的快照表
DROP TABLE IF EXISTS portfolio_daily_pnl;

-- 每日持仓明细表：记录每天每只股票的持仓状态
CREATE TABLE IF NOT EXISTS portfolio_daily_position (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date DATE NOT NULL COMMENT '交易日期',
    symbol VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    quantity INT NOT NULL DEFAULT 0 COMMENT '当日收盘持仓股数',
    avg_cost FLOAT NOT NULL DEFAULT 0 COMMENT '平均成本',
    close_price FLOAT COMMENT '当日收盘价',
    market_value FLOAT DEFAULT 0 COMMENT '当日市值',
    day_buy FLOAT DEFAULT 0 COMMENT '当日买入金额',
    day_sell FLOAT DEFAULT 0 COMMENT '当日卖出金额',
    unrealized_pnl FLOAT DEFAULT 0 COMMENT '当日浮动盈亏',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_daily_position_date_symbol (trade_date, symbol),
    KEY idx_trade_date (trade_date),
    KEY idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日持仓明细表';

-- 每日资产汇总表：记录每天的整体资产状态
CREATE TABLE IF NOT EXISTS portfolio_daily_summary (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date DATE NOT NULL COMMENT '交易日期',
    total_invested FLOAT DEFAULT 0 COMMENT '总投入成本',
    total_market_value FLOAT DEFAULT 0 COMMENT '当日收盘总市值',
    daily_pnl FLOAT DEFAULT 0 COMMENT '当日盈亏',
    cumulative_pnl FLOAT DEFAULT 0 COMMENT '累计盈亏',
    realized_pnl FLOAT DEFAULT 0 COMMENT '已实现盈亏',
    unrealized_pnl FLOAT DEFAULT 0 COMMENT '浮动盈亏',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_trade_date (trade_date),
    KEY idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日资产汇总表';
