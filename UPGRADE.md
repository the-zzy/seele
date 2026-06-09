# Seele 版本升级指南

> 本文档规范版本发布流程，每次升级版本号后必须按清单执行对应步骤，防止遗漏。

---

## 升级流程规范

### 1. 升级前准备

- [ ] 确认当前基线版本（代码分支 + 数据库状态）
- [ ] 对比上一个版本，梳理变更范围（代码 / 数据库 / 配置）
- [ ] 在测试环境预演升级步骤，确认无遗漏

### 2. 版本号更新

涉及版本号的位置（必须全部同步修改）：

| 文件 | 字段 |
|------|------|
| [package.json](package.json) | `"version"` |
| [seele-frontend/package.json](seele-frontend/package.json) | `"version"` |
| [seele-backend/app/__init__.py](seele-backend/app/__init__.py) | `__version__` |
| [seele-backend/app/main.py](seele-backend/app/main.py) | `FastAPI(version=...)` |

更新后提交：
```bash
git add -A
git commit -m "chore: bump version to X.Y.Z"
```

### 3. 数据库迁移检查

每次发版必须检查以下目录的变更：

- `db-ops/migrations/` — 是否有新增或修改的 SQL 迁移文件
- `seele-backend/app/models.py` — 模型是否有新增/删除/修改

如果存在迁移，在目标数据库按顺序执行新增 SQL 文件。

### 4. 配置变更检查

- `seele-backend/app/config.py` — 是否有新的环境变量或默认值调整
- `.env` 文件（本地）— 是否有新增配置项（**生产环境的 .env 需同步更新，但不提交到 git**）

### 5. 依赖变更检查

- `requirements.txt` 或 `pyproject.toml` 是否有新增 Python 包
- `package.json` 是否有新增 npm 包
- 如有变更，在目标环境执行安装

### 6. 部署与验证

- [ ] 停止旧进程（按 [CLAUDE.md](CLAUDE.md) 的进程清理规则执行）
- [ ] 拉取新代码 / 上传构建产物
- [ ] 执行数据库迁移（如有）
- [ ] 安装新依赖（如有）
- [ ] 启动后端（9000 端口）
- [ ] 构建并启动前端（8000 端口）
- [ ] 验证 `/health` 端点
- [ ] 验证核心业务链路（登录、数据查询等）
- [ ] 检查日志无异常报错

---

## 版本升级记录

### v2.2.0 (2026-06-10)

**分支**: `feature/mainwave-scorer-v2.2`

**代码变更范围**:
- 主线波浪评分功能迭代（v2.1 基础上继续开发）
- 新增 `MainwaveGroupTable`、`MainwaveView` 等前端组件
- Portfolio 相关计算和接口优化
- Sync 异步任务和轮询逻辑完善

**数据库迁移**: 无（沿用 v2.1 已执行的迁移）

**配置变更**: 无

**依赖变更**: 无

**升级步骤**:
1. 拉取 `feature/mainwave-scorer-v2.2` 最新代码
2. 前端重新构建
3. 按进程清理规则重启后端 + 前端
4. 验证主波浪评分页面正常加载

---

### v2.1.0 → v2.2.0 间累积的历史迁移（从 main 首次部署到 v2.2 需执行）

如果从 `main` 直接升级到 `v2.2`，需要依次执行以下 SQL 迁移：

| 迁移文件 | 说明 |
|----------|------|
| `db-ops/migrations/2026-05-09-add-portfolio-daily-tables.sql` | Portfolio 日快照/日汇总表 |
| `db-ops/migrations/2026-05-09-add-portfolio-daily-pnl.sql` | Portfolio 日盈亏字段补充 |
| `db-ops/migrations/2026-05-25-add-performance-indexes.sql` | 性能优化索引 |
| `db-ops/migrations/2026-05-25-dedup-stock-basic.sql` | stock_basic 去重 |
| `db-ops/migrations/2026-05-30-float-to-decimal.sql` | **核心：FLOAT → DECIMAL(18,4) 大迁移** |
| `db-ops/migrations/2026-06-08-board-constituent-name.sql` | board_constituent 新增 name 字段 |

---

## 升级检查清单模板

每次发版时复制以下模板，逐项勾选：

```markdown
## vX.Y.Z 升级检查清单

### 代码
- [ ] 版本号已更新（package.json ×2、__init__.py、main.py）
- [ ] 版本号变更已提交到当前分支
- [ ] 分支已推送远程

### 数据库
- [ ] 已对比 models.py 变更
- [ ] 已确认需执行的 SQL 迁移文件列表
- [ ] 已在目标环境执行迁移（或确认无需迁移）

### 配置
- [ ] 已检查 config.py / .env 是否有新增配置项
- [ ] 生产环境 .env 已同步更新

### 依赖
- [ ] 已检查 requirements.txt / package.json 变更
- [ ] 已在目标环境安装新依赖

### 部署
- [ ] 已按进程清理规则彻底停止旧服务
- [ ] 后端已启动并监听 9000 端口
- [ ] 前端已构建并监听 8000 端口
- [ ] /health 端点返回正常
- [ ] 核心业务链路验证通过
```
