-- 访客日志表
CREATE TABLE IF NOT EXISTS `visitor_log` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `ip_address` VARCHAR(64) NOT NULL COMMENT 'IP地址',
    `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '浏览器User-Agent',
    `path` VARCHAR(255) NOT NULL COMMENT '访问路径',
    `method` VARCHAR(10) NOT NULL COMMENT 'HTTP方法',
    `referrer` VARCHAR(500) DEFAULT NULL COMMENT '来源页面',
    `screen_resolution` VARCHAR(20) DEFAULT NULL COMMENT '屏幕分辨率',
    `language` VARCHAR(50) DEFAULT NULL COMMENT '浏览器语言',
    `timezone` VARCHAR(50) DEFAULT NULL COMMENT '时区',
    `platform` VARCHAR(50) DEFAULT NULL COMMENT '操作系统平台',
    `country` VARCHAR(50) DEFAULT NULL COMMENT '国家/地区',
    `city` VARCHAR(50) DEFAULT NULL COMMENT '城市',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '访问时间',
    PRIMARY KEY (`id`),
    KEY `idx_visitor_log_ip` (`ip_address`),
    KEY `idx_visitor_log_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='访客日志表';
