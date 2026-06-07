#!/bin/bash
# Seele v2.0 → v2.1 数据库迁移脚本
set -e

ENV_FILE="/www/seele/seele-backend/.env"
MIGRATIONS_DIR="/www/seele/db-ops/migrations"

# 从 .env 读取数据库密码
DB_PASS=$(grep '^DB_PASSWORD=' "$ENV_FILE" | cut -d '=' -f2-)
MYSQL_CMD="mysql -u root -p${DB_PASS} seele"

echo "========== [1/7] 统一 collation =========="
$MYSQL_CMD < $MIGRATIONS_DIR/2026-05-29-unify-collation.sql && echo "✅ [1/7] 完成"

echo ""
echo "========== [2/7] 分红字段 =========="
$MYSQL_CMD < $MIGRATIONS_DIR/2026-05-28-add-portfolio-trade-dividend.sql && echo "✅ [2/7] 完成"

echo ""
echo "========== [3/7] 访客日志表 =========="
$MYSQL_CMD < $MIGRATIONS_DIR/2026-05-28-add-visitor-log.sql && echo "✅ [3/7] 完成"

echo ""
echo "========== [4/7] 成分股 name 字段 =========="
$MYSQL_CMD < $MIGRATIONS_DIR/2026-06-08-board-constituent-name.sql && echo "✅ [4/7] 完成"

echo ""
echo "========== [5/7] 去重脚本 =========="
$MYSQL_CMD < $MIGRATIONS_DIR/2026-05-25-dedup-stock-basic.sql && echo "✅ [5/7] 完成"

echo ""
echo "========== [6/7] 索引优化 =========="
$MYSQL_CMD < $MIGRATIONS_DIR/2026-05-25-add-performance-indexes.sql && echo "✅ [6/7] 完成"

echo ""
echo "========== [7/7] FLOAT→DECIMAL 大迁移（14张表，stock_daily 719万行，可能几分钟） =========="
$MYSQL_CMD < $MIGRATIONS_DIR/2026-05-30-float-to-decimal.sql && echo "✅ [7/7] 完成"

echo ""
echo "========== 全部迁移完成，验证 =========="
$MYSQL_CMD -e "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='seele' AND TABLE_NAME='stock_daily' AND COLUMN_NAME='close';"
$MYSQL_CMD -e "SHOW COLUMNS FROM board_constituent LIKE 'name';"
$MYSQL_CMD -e "SHOW COLUMNS FROM portfolio_trade LIKE 'dividend';"
