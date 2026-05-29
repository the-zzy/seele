CREATE TABLE IF NOT EXISTS market_sentiment_daily (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date DATE NOT NULL COMMENT '交易日期',
    total_stocks INT NOT NULL DEFAULT 0 COMMENT '当日参与统计的总股票数',
    up_count INT NOT NULL DEFAULT 0 COMMENT '上涨家数',
    down_count INT NOT NULL DEFAULT 0 COMMENT '下跌家数',
    flat_count INT NOT NULL DEFAULT 0 COMMENT '平盘家数',
    avg_pct_chg DECIMAL(10,4) DEFAULT NULL COMMENT '平均涨跌幅',
    strong_count INT NOT NULL DEFAULT 0 COMMENT '涨幅>=阈值的家数',
    strong_threshold DECIMAL(5,2) NOT NULL DEFAULT 2.0 COMMENT '强势阈值%',
    strong_percent DECIMAL(5,2) DEFAULT NULL COMMENT '强势占比%',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_trade_date (trade_date),
    KEY idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日市场情绪统计';

CREATE TABLE IF NOT EXISTS industry_sentiment_daily (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date DATE NOT NULL COMMENT '交易日期',
    industry VARCHAR(50) NOT NULL COMMENT '行业名称',
    stock_count INT NOT NULL DEFAULT 0 COMMENT '板块内股票总数',
    up_count INT DEFAULT 0 COMMENT '上涨家数',
    down_count INT DEFAULT 0 COMMENT '下跌家数',
    flat_count INT DEFAULT 0 COMMENT '平盘家数',
    avg_pct_chg DECIMAL(10,4) DEFAULT NULL COMMENT '板块平均涨跌幅',
    max_pct_chg DECIMAL(10,4) DEFAULT NULL COMMENT '板块最大涨幅',
    min_pct_chg DECIMAL(10,4) DEFAULT NULL COMMENT '板块最大跌幅',
    strong_count INT DEFAULT 0 COMMENT '强势家数（涨幅>=阈值）',
    amount_sum DECIMAL(20,2) DEFAULT NULL COMMENT '板块总成交额',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_date_industry (trade_date, industry),
    KEY idx_trade_date (trade_date),
    KEY idx_industry (industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日板块情绪统计';
