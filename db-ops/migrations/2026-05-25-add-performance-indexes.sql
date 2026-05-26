-- 性能优化：增加复合索引和单列索引
-- 优化接口响应时间，减少全表扫描

-- 0. stock_daily 交易日期单列索引（加速按日期 COUNT / GROUP BY）
-- 该表数据量最大（600万+），原有索引仅覆盖 (symbol, trade_date) 复合索引，
-- 无法高效支持仅按 trade_date 过滤的聚合查询。
CREATE INDEX IF NOT EXISTS idx_stock_daily_trade_date ON stock_daily(trade_date);

-- 1. stock_daily_indicator 复合索引（加速三表 JOIN）
CREATE INDEX IF NOT EXISTS idx_indicator_symbol_date ON stock_daily_indicator(symbol, trade_date);

-- 2. index_daily 复合索引（加速指数列表批量查询）
CREATE INDEX IF NOT EXISTS idx_index_daily_symbol_date ON index_daily(symbol, trade_date);

-- 3. stock_suspension 复牌日期索引（加速停牌记录过滤）
CREATE INDEX IF NOT EXISTS idx_stock_suspension_resume ON stock_suspension(resume_date);

-- 4. stock_basic 市场板块索引（加速主板过滤）
CREATE INDEX IF NOT EXISTS idx_stock_basic_market ON stock_basic(market);

-- 5. stock_basic 上市日期索引（加速上市状态判断）
CREATE INDEX IF NOT EXISTS idx_stock_basic_list_date ON stock_basic(list_date);

-- 6. sync_job_log 任务类型+日期复合索引（加速日志查询）
CREATE INDEX IF NOT EXISTS idx_sync_job_log_type_date ON sync_job_log(job_type, trade_date);

-- 7. stock_financial_indicator 报告期索引（加速财报分布统计）
CREATE INDEX IF NOT EXISTS idx_financial_report_date ON stock_financial_indicator(report_date);

-- 8. stock_daily (trade_date, symbol) 复合索引（避免 filesort，加速按日期分页查询）
CREATE INDEX IF NOT EXISTS idx_stock_daily_trade_date_symbol ON stock_daily(trade_date, symbol);

-- 9. stock_basic 覆盖索引（加速 mainwave-picker 等 JOIN 查询，避免回表）
CREATE INDEX IF NOT EXISTS idx_stock_basic_cover ON stock_basic(market, symbol, name, industry, area, float_market_cap);
