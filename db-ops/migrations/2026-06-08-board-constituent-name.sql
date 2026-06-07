-- 2026-06-08: board_constituent 表增加 name 字段
-- 同步时从东方财富 API 获取成分股名称存入此字段，
-- 避免依赖 stock_basic 的 OUTER JOIN（stock_basic 数据不全时名称为空）

ALTER TABLE board_constituent
    ADD COLUMN name VARCHAR(100) COMMENT '成分股名称' AFTER constituent_symbol;

-- 从 stock_basic 回填已有数据的名称
UPDATE board_constituent AS bc
    INNER JOIN stock_basic AS sb ON bc.constituent_symbol = sb.symbol
SET bc.name = sb.name
WHERE bc.name IS NULL;
