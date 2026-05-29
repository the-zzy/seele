-- 清理 stock_basic 表中的重复 symbol 记录并添加唯一约束
-- 执行时间: 2026-05-25
-- 问题: stock_basic 表中 symbol 列缺少唯一索引，导致 upsert_batch 的 ON DUPLICATE KEY UPDATE 失效，
--       每次同步都会插入重复记录，进而导致所有 JOIN stock_basic 的查询产生笛卡尔积。

-- Step 1: 查看重复情况（可选，执行前确认）
-- SELECT symbol, COUNT(*) as cnt FROM stock_basic GROUP BY symbol HAVING cnt > 1;

-- Step 2: 删除重复记录，保留每个 symbol 中 id 最大的一条（最新插入）
DELETE sb1 FROM stock_basic sb1
INNER JOIN stock_basic sb2
WHERE sb1.id < sb2.id AND sb1.symbol = sb2.symbol;

-- Step 3: 添加唯一索引（兼容 MySQL 5.7+）
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
               WHERE table_schema = DATABASE()
               AND table_name = 'stock_basic'
               AND index_name = 'uk_symbol');
SET @sql := IF(@exist = 0, 'ALTER TABLE stock_basic ADD UNIQUE INDEX uk_symbol (symbol)', 'SELECT "Index already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
