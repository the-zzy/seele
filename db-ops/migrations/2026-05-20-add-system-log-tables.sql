-- 系统日志表迁移
-- 创建 system_error_log 和 system_operation_log 两张表

CREATE TABLE IF NOT EXISTS system_error_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level VARCHAR(20) NOT NULL DEFAULT 'error' COMMENT '级别: error / warning / critical',
    source VARCHAR(100) NOT NULL COMMENT '来源模块',
    trace_id VARCHAR(50) NULL COMMENT '关联ID: task_id / log_id / pipeline_id',
    message VARCHAR(1000) NOT NULL COMMENT '错误消息',
    detail TEXT NULL COMMENT '详细内容: traceback等',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    INDEX idx_source (source),
    INDEX idx_level (level),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统错误日志表';

CREATE TABLE IF NOT EXISTS system_operation_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL COMMENT '操作类型: sync_manual / pipeline_start / pipeline_cancel / job_cancel / config_update',
    operator VARCHAR(50) NULL COMMENT '操作人',
    target_type VARCHAR(50) NULL COMMENT '操作对象类型: job / pipeline / stock / config',
    target_id VARCHAR(100) NULL COMMENT '对象标识',
    detail VARCHAR(1000) NULL COMMENT '操作详情',
    result VARCHAR(20) NULL COMMENT '结果: success / failed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    INDEX idx_operation_type (operation_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统操作日志表';
