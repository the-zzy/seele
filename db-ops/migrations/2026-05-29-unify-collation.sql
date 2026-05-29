-- 全库 collation 统一修复脚本
-- 问题: stock_basic 等少数表使用 utf8mb4_0900_ai_ci，与大多数表(utf8mb4_unicode_ci)不一致
-- 触发场景: stock_daily.symbol IN (SELECT stock_basic.symbol ...) 等跨表 JOIN/子查询
-- 错误码: MySQL 1267 - Illegal mix of collations
-- 目标: 统一为 utf8mb4_unicode_ci（现有大多数表已使用，改动量最小）
-- 执行前建议: mysqldump 备份，或在低峰期执行

-- ========================================
-- 1. 修复表级默认 collation（影响后续新增字段）
-- ========================================
ALTER TABLE stock_basic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE stock_financial_indicator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ========================================
-- 2. 修复字段级 collation（共 18 列）
-- ========================================

-- stock_basic (13 列)
ALTER TABLE stock_basic MODIFY symbol varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY name varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY area varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY industry varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY cnspell varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY market varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY list_date varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY act_name varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY act_ent_type varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY fullname varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY enname varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
ALTER TABLE stock_basic MODIFY exchange varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;

-- portfolio 相关 (3 列)
ALTER TABLE portfolio_closed MODIFY symbol varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码';
ALTER TABLE portfolio_position MODIFY symbol varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码';
ALTER TABLE portfolio_trade MODIFY symbol varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码';

-- stock_daily_indicator (1 列)
ALTER TABLE stock_daily_indicator MODIFY symbol varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码';

-- stock_financial_indicator (2 列)
ALTER TABLE stock_financial_indicator MODIFY symbol varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码';
ALTER TABLE stock_financial_indicator MODIFY name varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '股票名称';
