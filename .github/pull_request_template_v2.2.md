## feat: release v2.2.0 — 主线波浪评分迭代 & Portfolio 优化

**目标分支**: `main`
**源分支**: `feature/mainwave-scorer-v2.2`

---

### 版本

`v2.2.0`

---

### 变更摘要

| 类别 | 内容 |
|------|------|
| 核心功能 | 主线波浪评分 v2 迭代（分组展示、评分维度扩展） |
| 新增页面 | MainwaveView（主线波浪总览）、MainwaveGroupTable（分组表格） |
| Portfolio | 盈亏计算优化、Decimal→Float 适配、日快照/日汇总表 |
| 板块同步 | 新增板块/ETF 日线数据定时同步任务 |
| Agent | 流式请求补全 Bearer Token 认证头 |
| 版本管理 | 新增 UPGRADE.md 版本升级指南与检查清单 |
| 数据库 | FLOAT → DECIMAL(18,4) 大迁移、板块成分股 name 字段 |

---

### 主要变更

**前端**
- 新增 MainwaveView、MainwaveGroupTable 等主线波浪相关组件
- MainwaveScoreTable 样式优化（单元格居中对齐）
- MainwavePickerFilter 筛选逻辑增强
- Portfolio 视图交互和计算优化
- Sync 异步任务轮询逻辑完善（useSyncTask）
- Agent 聊天组件增加工具调用展示

**后端**
- mainwave_scorer.py 评分算法迭代
- portfolio.py / crud.py 盈亏计算和 Decimal 适配修复
- sync_worker.py 异步任务触发 + 客户端轮询模式
- scheduler_jobs.py 新增板块/ETF 日线同步定时任务
- models.py FLOAT → Numeric(18,4) 全量迁移
- agent/tools.py 工具函数 Decimal 类型处理修复

**DevOps / 文档**
- 新增 UPGRADE.md 版本升级管理规范
- 新增 6 份 SQL 迁移文件（见下方）
- 移除含凭据的部署脚本
- AI Review CI 配置调整

---

### 数据库迁移

如从 main 首次部署到 v2.2，需依次执行以下迁移：

1. db-ops/migrations/2026-05-09-add-portfolio-daily-tables.sql — Portfolio 日快照/日汇总表
2. db-ops/migrations/2026-05-09-add-portfolio-daily-pnl.sql — Portfolio 日盈亏字段补充
3. db-ops/migrations/2026-05-25-add-performance-indexes.sql — 性能优化索引
4. db-ops/migrations/2026-05-25-dedup-stock-basic.sql — stock_basic 去重
5. db-ops/migrations/2026-05-30-float-to-decimal.sql — FLOAT → DECIMAL(18,4) 核心迁移
6. db-ops/migrations/2026-06-08-board-constituent-name.sql — 板块成分股新增 name 字段

如当前数据库已是 v2.1 基线，则无需重复执行。

---

### 版本号更新位置

- [x] package.json
- [x] seele-frontend/package.json
- [x] seele-frontend/src/App.vue
- [x] seele-backend/app/__init__.py
- [x] seele-backend/app/main.py

---

### 部署前检查清单

- [ ] 数据库迁移已执行（或确认无需执行）
- [ ] 前端重新构建
- [ ] 按进程清理规则彻底停止旧服务
- [ ] 后端启动（9000 端口）
- [ ] 前端启动（8000 端口）
- [ ] /health 端点正常
- [ ] 主波浪评分页面加载正常
