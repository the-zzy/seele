-- 板块/ETF基础信息表
CREATE TABLE IF NOT EXISTS board_info (
    code VARCHAR(20) PRIMARY KEY COMMENT '板块/ETF代码',
    name VARCHAR(100) NOT NULL COMMENT '板块/ETF名称',
    category VARCHAR(20) NOT NULL COMMENT '类型: industry/concept/etf',
    exchange VARCHAR(10) COMMENT '交易所',
    source VARCHAR(20) COMMENT '数据来源'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块/ETF基础信息表';

-- 板块/ETF成分股映射表
CREATE TABLE IF NOT EXISTS board_constituent (
    id INT AUTO_INCREMENT PRIMARY KEY,
    board_code VARCHAR(20) NOT NULL COMMENT '板块/ETF代码',
    constituent_symbol VARCHAR(20) NOT NULL COMMENT '成分股代码',
    update_date DATE COMMENT '更新日期',
    UNIQUE KEY uq_board_constituent (board_code, constituent_symbol),
    KEY idx_board_code (board_code),
    KEY idx_constituent_symbol (constituent_symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块/ETF成分股映射表';

-- 板块/ETF日线数据表
CREATE TABLE IF NOT EXISTS board_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) NOT NULL COMMENT '板块/ETF代码',
    trade_date DATE NOT NULL COMMENT '交易日期',
    open FLOAT COMMENT '开盘价',
    high FLOAT COMMENT '最高价',
    low FLOAT COMMENT '最低价',
    close FLOAT COMMENT '收盘价',
    volume FLOAT COMMENT '成交量',
    amount FLOAT COMMENT '成交额',
    pct_chg FLOAT COMMENT '涨跌幅',
    UNIQUE KEY uq_board_daily_date_code (trade_date, code),
    KEY idx_code (code),
    KEY idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块/ETF日线数据表';
