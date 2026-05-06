CREATE TABLE IF NOT EXISTS `portfolio_trade` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) NOT NULL,
  `name` varchar(100) NOT NULL,
  `trade_type` varchar(10) NOT NULL COMMENT 'BUY / SELL',
  `trade_date` date NOT NULL,
  `price` float NOT NULL,
  `quantity` int NOT NULL,
  `amount` float NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓交易记录表';

CREATE TABLE IF NOT EXISTS `portfolio_closed` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) NOT NULL,
  `name` varchar(100) NOT NULL,
  `total_buy_amount` float NOT NULL,
  `total_sell_amount` float NOT NULL,
  `total_quantity` int NOT NULL,
  `avg_buy_price` float NOT NULL,
  `avg_sell_price` float NOT NULL,
  `open_date` date NOT NULL COMMENT '首次买入日期',
  `close_date` date NOT NULL COMMENT '清仓日期',
  `realized_pnl` float NOT NULL COMMENT '实现盈亏',
  `pnl_pct` float NOT NULL COMMENT '盈亏百分比',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_symbol` (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='清仓盈亏记录表';

CREATE TABLE IF NOT EXISTS `portfolio_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `initial_capital` float NOT NULL DEFAULT 35000 COMMENT '初始资金',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓配置表';
