-- 给 stock_daily_indicator 表添加 5日涨幅和10日涨幅字段
ALTER TABLE stock_daily_indicator
ADD COLUMN chg_5d FLOAT COMMENT '5日涨幅(%)' AFTER turnover_ma10,
ADD COLUMN chg_10d FLOAT COMMENT '10日涨幅(%)' AFTER chg_5d;
