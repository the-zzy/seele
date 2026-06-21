# 远程数据库迁移操作手册

> 本文档用于指导 Seele 项目远程生产环境（阿里云 ECS）的数据库迁移操作。
>
> 适用服务器：`8.138.165.208`（Alibaba Cloud Linux，MySQL 8.0.45 Source distribution）

## 一、迁移前准备

### 1.1 备份数据库

**任何迁移操作前必须先备份。**

```bash
ssh -i ~/.ssh/id_ed25519 root@8.138.165.208
mysqldump -u root -p seele > /tmp/seele_backup_$(date +%Y%m%d_%H%M%S).sql
```

### 1.2 停止后端服务

防止迁移过程中有写入导致锁表或数据不一致：

```bash
systemctl stop seele-backend
# 确认 9000 端口无监听
ss -tlnp | grep 9000
```

### 1.3 确认当前数据库状态

```bash
cd /www/seele/seele-backend
DB_PASS=$(grep '^DB_PASSWORD=' .env | cut -d= -f2)
mysql -u root -p"$DB_PASS" seele -e "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name IN ('portfolio_trade', 'portfolio_config', 'sync_job_log', 'board_constituent') AND column_name IN ('name', 'commission', 'stamp_tax', 'transfer_fee', 'fee', 'commission_rate', 'stamp_tax_rate', 'transfer_rate', 'extra_info') ORDER BY table_name, ordinal_position;"
mysql -u root -p"$DB_PASS" seele -e "SHOW TABLES LIKE 'backtest%';"
```

## 二、迁移脚本规范

### 2.1 脚本存放位置

所有迁移脚本统一放在：

```
db-ops/migrations/YYYY-MM-DD-<brief-description>.sql
```

### 2.2 脚本内容要求

- 每个脚本顶部必须包含：适用版本、变更原因、执行顺序说明
- 必须幂等（可重复执行不报错）
- 必须避免破坏已有数据

### 2.3 远程 MySQL 特殊限制

远程 MySQL 版本显示为 `8.0.45 Source distribution`，但实际**不支持**以下语法：

```sql
-- 不支持
ALTER TABLE xxx DROP COLUMN IF EXISTS column_name;
ALTER TABLE xxx ADD COLUMN IF NOT EXISTS column_name ...;
```

**正确写法**：使用 `information_schema.columns` 做条件判断。

```sql
SET @exist := (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE()
    AND table_name = 'portfolio_trade'
    AND column_name = 'fee');
SET @sql := IF(@exist = 1,
    'ALTER TABLE portfolio_trade DROP COLUMN fee',
    'SELECT "fee column already dropped" AS msg');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
```

### 2.4 保留字处理

`current_date` 是 MySQL 保留字，用作列名时必须加反引号：

```sql
CREATE TABLE backtest_run (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `current_date` DATE NOT NULL COMMENT '当前已处理日期',
    ...
);
```

## 三、迁移执行流程

### 3.1 标准执行脚本模板

在远程服务器上创建 `/tmp/run_migrations.sh`：

```bash
#!/bin/bash
set -e

cd /www/seele/seele-backend
DB_PASS=$(grep '^DB_PASSWORD=' .env | cut -d= -f2)
DB_OPTS="-u root -p$DB_PASS seele"

# 按顺序执行迁移脚本
for f in /tmp/migrations/*.sql; do
    echo "=== Running $(basename $f) ==="
    mysql $DB_OPTS < "$f"
    echo "OK"
done

echo "=== Migration completed ==="
```

### 3.2 上传并执行

```bash
# 本地执行
scp -i ~/.ssh/id_ed25519 db-ops/migrations/2026-*.sql root@8.138.165.208:/tmp/migrations/
scp -i ~/.ssh/id_ed25519 /tmp/run_migrations.sh root@8.138.165.208:/tmp/run_migrations.sh
ssh -i ~/.ssh/id_ed25519 root@8.138.165.208 'bash /tmp/run_migrations.sh'
```

### 3.3 迁移后验证

```bash
mysql -u root -p"$DB_PASS" seele -e "DESCRIBE portfolio_trade;"
mysql -u root -p"$DB_PASS" seele -e "DESCRIBE portfolio_config;"
mysql -u root -p"$DB_PASS" seele -e "SHOW TABLES LIKE 'backtest%';"
```

## 四、v2.4 迁移记录

**迁移时间**：2026-06-22
**涉及版本**：feature/mainwave-scorer-v2.4
**操作人员**：Claude Code

### 4.1 已执行脚本

| 脚本 | 状态 | 说明 |
|------|------|------|
| `2026-06-08-board-constituent-name.sql` | 已提前应用，本次跳过 | `board_constituent` 增加 `name` 字段 |
| `2026-06-15-add-trade-fee-breakdown.sql` | 已应用 | `portfolio_trade` 增加三费明细字段；`portfolio_config` 增加默认费率 |
| `2026-06-18-expand-sync-job-log-extra-info.sql` | 已应用 | `sync_job_log.extra_info` 从 `varchar(1000)` 扩容为 `text` |
| `2026-06-18-v2.4-deploy.sql` | 部分应用 | 回测表已创建；费用字段部分因与 06-15 重复已跳过 |
| `2026-06-22-rename-trade-fee-to-commission.sql` | 已应用 | 删除旧 `fee` 字段，保留三费明细 |

### 4.2 本次遇到的问题

1. **远程 MySQL 不支持 `IF [NOT] EXISTS` 语法**
   - 原始迁移脚本中的 `DROP COLUMN IF EXISTS`、`ADD COLUMN IF NOT EXISTS` 均报语法错误
   - 解决：改用 `information_schema.columns` 条件判断或先检查字段是否存在

2. **`current_date` 保留字导致建表失败**
   - `backtest_run` 表中的 `current_date` 列未加反引号
   - 解决：提取 CREATE TABLE 语句后用 `sed` 给 `current_date` 加反引号

3. **迁移脚本之间存在依赖和重复**
   - `2026-06-18-v2.4-deploy.sql` 与 `2026-06-15-add-trade-fee-breakdown.sql` 都修改了 `portfolio_trade` 和 `portfolio_config`
   - 解决：按时间顺序执行，已应用的部分通过字段存在性检查跳过

### 4.3 迁移后最终表结构

- `portfolio_trade`：包含 `commission`、`stamp_tax`、`transfer_fee`，无 `fee`
- `portfolio_config`：包含 `commission_rate`、`stamp_tax_rate`、`transfer_rate`
- `sync_job_log.extra_info`：`text` 类型
- `board_constituent`：包含 `name` 字段
- 新增回测表：`backtest_run`、`backtest_trade`、`backtest_daily_snapshot`、`backtest_decision_log`、`backtest_task`

## 五、回滚方案

如果迁移后服务无法启动：

```bash
systemctl stop seele-backend
mysql -u root -p seele < /tmp/seele_backup_YYYYMMDD_HHMMSS.sql
systemctl start seele-backend
```

## 六、检查清单

- [ ] 迁移前已备份数据库
- [ ] 后端服务已停止
- [ ] 迁移脚本已按顺序执行
- [ ] 关键表结构已验证
- [ ] 后端服务已重新启动
- [ ] 健康检查返回 200
- [ ] 临时迁移文件已清理
