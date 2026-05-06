-- 新增 stock_daily_indicator 表
-- 执行时间: 2026-04-26
-- 说明: 存储股票日线均线及平均成交量、平均换手率等指标

CREATE TABLE IF NOT EXISTS `stock_daily_indicator` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(10) NOT NULL COMMENT '股票代码',
  `trade_date` date NOT NULL COMMENT '交易日期',
  `ma5` decimal(10,2) DEFAULT NULL COMMENT '5日均线',
  `ma10` decimal(10,2) DEFAULT NULL COMMENT '10日均线',
  `ma20` decimal(10,2) DEFAULT NULL COMMENT '20日均线',
  `ma30` decimal(10,2) DEFAULT NULL COMMENT '30日均线',
  `ma60` decimal(10,2) DEFAULT NULL COMMENT '60日均线',
  `vol_ma5` bigint DEFAULT NULL COMMENT '5日平均成交量（股）',
  `vol_ma10` bigint DEFAULT NULL COMMENT '10日平均成交量（股）',
  `turnover_ma5` decimal(10,2) DEFAULT NULL COMMENT '5日平均换手率(%)',
  `turnover_ma10` decimal(10,2) DEFAULT NULL COMMENT '10日平均换手率(%)',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_symbol_date` (`symbol`,`trade_date`),
  KEY `idx_symbol_date` (`symbol`,`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
