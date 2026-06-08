-- 性能优化：增加复合索引和单列索引
-- 优化接口响应时间，减少全表扫描
-- 大表加索引使用 ALGORITHM=INPLACE, LOCK=NONE 避免锁表

-- 0. stock_daily 交易日期单列索引（加速按日期 COUNT / GROUP BY）
-- 该表数据量最大（600万+），原有索引仅覆盖 (symbol, trade_date) 复合索引，
-- 无法高效支持仅按 trade_date 过滤的聚合查询。
ALTER TABLE stock_daily ADD INDEX idx_stock_daily_trade_date (trade_date), ALGORITHM=INPLACE, LOCK=NONE;

-- 1. stock_daily_indicator 复合索引（加速三表 JOIN）
ALTER TABLE stock_daily_indicator ADD INDEX idx_indicator_symbol_date (symbol, trade_date), ALGORITHM=INPLACE, LOCK=NONE;

-- 2. index_daily 复合索引（加速指数列表批量查询）
ALTER TABLE index_daily ADD INDEX idx_index_daily_symbol_date (symbol, trade_date), ALGORITHM=INPLACE, LOCK=NONE;

-- 3. stock_suspension 复牌日期索引（加速停牌记录过滤）
ALTER TABLE stock_suspension ADD INDEX idx_stock_suspension_resume (resume_date), ALGORITHM=INPLACE, LOCK=NONE;

-- 4. stock_basic 市场板块索引（加速主板过滤）
ALTER TABLE stock_basic ADD INDEX idx_stock_basic_market (market), ALGORITHM=INPLACE, LOCK=NONE;

-- 5. stock_basic 上市日期索引（加速上市状态判断）
ALTER TABLE stock_basic ADD INDEX idx_stock_basic_list_date (list_date), ALGORITHM=INPLACE, LOCK=NONE;

-- 6. sync_job_log 任务类型+日期复合索引（加速日志查询）
ALTER TABLE sync_job_log ADD INDEX idx_sync_job_log_type_date (job_type, trade_date), ALGORITHM=INPLACE, LOCK=NONE;

-- 7. stock_financial_indicator 报告期索引（加速财报分布统计）
ALTER TABLE stock_financial_indicator ADD INDEX idx_financial_report_date (report_date), ALGORITHM=INPLACE, LOCK=NONE;

-- 8. stock_daily (trade_date, symbol) 复合索引（避免 filesort，加速按日期分页查询）
ALTER TABLE stock_daily ADD INDEX idx_stock_daily_trade_date_symbol (trade_date, symbol), ALGORITHM=INPLACE, LOCK=NONE;

-- 9. stock_basic 覆盖索引（加速 mainwave-picker 等 JOIN 查询，避免回表）
ALTER TABLE stock_basic ADD INDEX idx_stock_basic_cover (market, symbol, name, industry, area, float_market_cap), ALGORITHM=INPLACE, LOCK=NONE;
