-- 添加持仓快照表和止损止盈字段
-- 用于优化持仓查询性能和支持止损止盈提醒

-- 1. 持仓快照表：缓存当前持仓的实时计算结果
CREATE TABLE IF NOT EXISTS portfolio_position (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    symbol VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    quantity INT NOT NULL DEFAULT 0 COMMENT '持仓股数',
    avg_cost FLOAT NOT NULL DEFAULT 0 COMMENT '平均成本',
    current_price FLOAT COMMENT '最新收盘价',
    market_value FLOAT COMMENT '市值',
    unrealized_pnl FLOAT COMMENT '浮动盈亏',
    unrealized_pnl_pct FLOAT COMMENT '浮动盈亏百分比',
    stop_loss_price FLOAT COMMENT '止损价',
    take_profit_price FLOAT COMMENT '止盈价',
    alert_triggered TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已触发提醒 0/1',
    `group` VARCHAR(50) DEFAULT 'default' COMMENT '持仓分组（如 core, watch）',
    remark VARCHAR(255) COMMENT '备注',
    first_buy_date DATE COMMENT '首次买入日期',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_symbol (`group`, symbol),
    KEY idx_group (`group`),
    KEY idx_alert_triggered (alert_triggered)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓快照表';

-- 2. 交易记录表添加手续费字段
ALTER TABLE portfolio_trade
    ADD COLUMN fee FLOAT DEFAULT 0 COMMENT '交易手续费' AFTER amount,
    ADD COLUMN remark VARCHAR(255) COMMENT '备注' AFTER fee;

-- 3. 清仓记录表添加手续费和分组字段
ALTER TABLE portfolio_closed
    ADD COLUMN total_fee FLOAT DEFAULT 0 COMMENT '总手续费' AFTER pnl_pct,
    ADD COLUMN `group` VARCHAR(50) DEFAULT 'default' COMMENT '持仓分组' AFTER total_fee;
