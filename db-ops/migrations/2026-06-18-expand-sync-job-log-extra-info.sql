-- 2026-06-18: sync_job_log.extra_info 字段扩容
-- 适用版本: feature/mainwave-scorer-v2.4
-- 变更原因: 指标同步等任务写入的统计信息超过原 varchar(1000) 长度限制

ALTER TABLE sync_job_log
MODIFY COLUMN extra_info TEXT COMMENT '额外信息';
