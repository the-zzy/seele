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
| [VERSION](VERSION) | 项目版本号（纯文本） |
| [package.json](package.json) | `"version"` |
| [seele-frontend/package.json](seele-frontend/package.json) | `"version"` |
| [seele-frontend/src/App.vue](seele-frontend/src/App.vue) | 侧边栏 masthead 硬编码版本号 |
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

### v2.3.0 (2026-06-14)

**分支**: `feature/mainwave-scorer-v2.3`

**代码变更范围**:
- 主线波浪评分 v2.3 优化（`mainwave-picker`、组合交易、指标计算性能）
- 前端移动端适配（Vant 4 + 自定义 SCSS）
- 修复 `stock_basic`、`financial`、`mainwave-detect` 和 `agent chat` 500 错误
- 新增版本管理（`VERSION` 文件、`/api/version`、前端版本检查）
- `sync-job-log` 样式紧凑化、主波浪表格居中
- Agent chat stream 请求补充 Bearer token
- 清理临时 `daily_repair` 脚本和备份文件

**数据库迁移**：

v2.3.0 新增迁移（从 v2.2 升级必须执行）：

| 迁移文件 | 说明 |
|----------|------|
| `db-ops/migrations/2026-05-29-unify-collation.sql` | 统一全库 collation 为 `utf8mb4_unicode_ci` |
| `db-ops/migrations/2026-06-08-board-constituent-name.sql` | `board_constituent` 新增 `name` 字段 |
| `scripts/add_industry_detail_column.py` | `stock_basic` 新增 `industry_detail` 字段 |

> 如果从 v2.1 或更早基线升级，还需先补执行「v2.1.0 → v2.2.0 间累积的历史迁移」章节中的 SQL。
> `2026-05-28-add-visitor-log.sql` 和 `2026-05-30-float-to-decimal.sql` 已在 v2.2 前累积迁移中列出，请勿重复执行。

**配置变更**:
- `deploy/nginx-seele.conf` 增加 SSL 覆盖警告
- `deploy/seele-backend.service` 路径改为占位符

**依赖变更**: 无新增

**升级步骤**:
1. 备份数据库
2. 按顺序执行数据库迁移
3. 清理前端构建缓存后重新构建 `npm run build`
4. 上传前后端代码
5. 检查 `seele-backend.service` 路径指向
6. 修改 Nginx 配置时**不要覆盖 SSL 段**，reload nginx
7. 重启后端并验证 `https://<YOUR_DOMAIN>/api/version`

---

### v2.2.0 (2026-06-10)

**分支**: `feature/mainwave-scorer-v2.2`

**代码变更范围**:
- 主线波浪评分算法重构（`mainwave_scorer.py` 大改）
- 新增 `MainwaveView` 总览页面、`MainwaveGroupTable` 分组组件
- Portfolio 日交易（T+0）记录功能完善
- Agent chat stream 请求 Bearer token 修复
- Decimal → float 转换修复（agent/tools.py、portfolio.py）
- Sync worker 与同步任务端点优化

**数据库迁移**: 无（沿用 v2.1 已执行的迁移）

**配置变更**: 无

**依赖变更**: 无

**升级步骤**:
1. 拉取 `feature/mainwave-scorer-v2.2` 最新代码
2. 前端重新构建 `npm run build`
3. 按进程清理规则彻底停止旧 Python 进程
4. 启动后端（9000 端口）
5. 启动前端（8000 端口）
6. 验证 `/health` 端点
7. 验证主波浪评分页面、组合日交易功能、Agent 对话流

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
- [ ] 版本号已更新（package.json ×2、App.vue、__init__.py、main.py）
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

### Nginx / HTTPS
- [ ] 已确认 Nginx 配置包含 443 SSL 监听（生产环境必须）
- [ ] 已确认 HTTP 80 端口会 301 重定向到 HTTPS
- [ ] 更新 Nginx 配置时**不能直接覆盖**，需合并保留 Certbot/SSL 段
- [ ] 已验证 `https://<YOUR_DOMAIN>/` 和 `https://<YOUR_DOMAIN>/api/version` 可正常访问
```

---

## 远程手动操作备忘（示例）

> ⚠️ **安全警示**：以下命令中的 `<PROD_IP>`、`<PROD_USER>`、`<DEPLOY_DIR>`、`<NGINX_CONF_PATH>` 是占位符。
> 替换为真实值后**仅用于本地执行或内部加密文档**，禁止将真实 IP、用户名、路径、密码提交到 Git 仓库。

```bash
# 1. 备份数据库
mysqldump -u root -p seele > <DEPLOY_DIR>/backups/seele-$(date +%Y%m%d_%H%M%S).sql

# 2. 执行 v2.3.0 增量迁移（从 v2.2 升级）
mysql -u root -p seele < <DEPLOY_DIR>/db-ops/migrations/2026-05-29-unify-collation.sql
mysql -u root -p seele < <DEPLOY_DIR>/db-ops/migrations/2026-06-08-board-constituent-name.sql

# 如从 v2.1 或更早基线升级，需先补执行「v2.1.0 → v2.2.0 间累积的历史迁移」中的 SQL

# 3. 添加 industry_detail 字段
cd <DEPLOY_DIR>/seele-backend
source .venv/bin/activate
python scripts/add_industry_detail_column.py

# 4. 重启后端
systemctl restart seele-backend
```

---

## 部署教训

### 2026-06-14 v2.3.0 部署

**问题 1：Nginx 配置覆盖导致 HTTPS 失效**

现象：`https://<YOUR_DOMAIN>/` 无法访问，`http://` 正常。

原因：部署脚本直接用新配置覆盖了 `<NGINX_CONF_PATH>`，只保留了 80 端口监听，丢失了 Certbot 自动生成的 443 SSL 段和 HTTP→HTTPS 301 重定向。

正确处理：
1. 修改 Nginx 配置前先做备份：`cp <NGINX_CONF_PATH> <NGINX_CONF_PATH>.bak.$(date +%Y%m%d_%H%M%S)`
2. 不要整体替换，只修改需要变更的部分（如 `root` 路径、`location` 段）
3. 修改后检查 `nginx -t`，并确认 `ss -tlnp | grep :443` 有监听
4. 必须验证 `https://<YOUR_DOMAIN>/` 和 `https://<YOUR_DOMAIN>/api/version`

**问题 2：Systemd 服务路径与实际部署目录不一致**

现象：`systemctl restart seele-backend` 失败，`Failed to load environment files: No such file or directory`。

原因：旧服务文件指向 `<OLD_DEPLOY_DIR>/seele-backend`，而实际代码已部署到 `<DEPLOY_DIR>/seele-backend`。

正确处理：
1. 部署前检查 `WorkingDirectory` 和 `EnvironmentFile` 是否指向当前部署目录
2. 服务文件应与代码一起上传/更新，不能假设远程路径永远不变
3. 修改服务文件后执行 `systemctl daemon-reload`

**问题 3：前端构建缓存错误**

现象：`npm run build` 报 `ModuleHotAcceptDependency`。

正确处理：构建前清理缓存：
```bash
rm -rf dist node_modules/.cache ../node_modules/.cache
npx vue-cli-service build --mode production
```

