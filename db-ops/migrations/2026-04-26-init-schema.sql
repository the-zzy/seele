-- 初始表结构（已存在）
-- 执行时间: 2026-04-26
-- 说明: 项目初始化时已创建的表，此处记录用于参考

CREATE TABLE IF NOT EXISTS `stock_basic` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) DEFAULT NULL,
  `name` varchar(50) DEFAULT NULL,
  `area` varchar(50) DEFAULT NULL,
  `industry` varchar(50) DEFAULT NULL,
  `cnspell` varchar(50) DEFAULT NULL,
  `market` varchar(20) DEFAULT NULL,
  `list_date` varchar(20) DEFAULT NULL,
  `act_name` varchar(100) DEFAULT NULL,
  `act_ent_type` varchar(50) DEFAULT NULL,
  `fullname` varchar(255) DEFAULT NULL,
  `enname` varchar(255) DEFAULT NULL,
  `exchange` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `stock_daily` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(10) NOT NULL,
  `trade_date` date NOT NULL,
  `open` decimal(10,2) DEFAULT NULL,
  `high` decimal(10,2) DEFAULT NULL,
  `low` decimal(10,2) DEFAULT NULL,
  `close` decimal(10,2) DEFAULT NULL,
  `volume` bigint DEFAULT NULL,
  `amount` decimal(15,2) DEFAULT NULL,
  `amplitude` decimal(10,2) DEFAULT NULL,
  `pct_chg` decimal(10,2) DEFAULT NULL,
  `price_change` decimal(10,2) DEFAULT NULL,
  `turnover` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_symbol_trade_date` (`symbol`,`trade_date`),
  KEY `idx_symbol_date` (`symbol`,`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
