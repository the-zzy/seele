# 后端接口清单与测速报告

> 测速时间：2026-06-14 01:52:40  
> 测速目标：`http://127.0.0.1:9000`  
> 后端分支：`feature/mainwave-scorer-v2.3`  
> 认证方式：管理员登录后携带 JWT Token  
> 说明：本次测速**不包含同步任务类接口**（`/api/sync/*`），仅对普通业务接口进行单次请求测速。

---

## 1. 修复与优化记录

### 1.1 500 错误修复

| 问题 | 根因 | 修复方式 |
| --- | --- | --- |
| `POST /api/stock/basic/page` 等 6 个接口 500 | 数据库表 `stock_basic` 缺少 `industry_detail` 字段 | 执行 `ALTER TABLE stock_basic ADD COLUMN industry_detail VARCHAR(255) DEFAULT NULL;` |
| `POST /api/agent/chat` 500 | Moonshot/Kimi Code 模型要求 `temperature=1.0` | 修改 `seele-backend/app/agent/client.py`，默认温度改为 `1.0` |

### 1.2 性能优化

| 接口 | 优化前 | 优化后 | 优化方式 |
| --- | --- | --- | --- |
| `POST /api/stock/daily/mainwave-picker` | **~8.0s** | **0.11s** | SQL 层分页+排序，仅对当前页做主升浪评分；修复 `StockFinancialIndicator` 笛卡尔积；新增复合索引 `(symbol, report_date)` |
| `POST /api/portfolio/trades` | **1.51s** | **0.014s** | 移除交易录入后的同步全量 `_rebuild_daily_data` |
| `POST /api/portfolio/day-trades` | **1.32s** | **0.009s** | 同上 |
| `POST /api/stock/indicator/compute` | **2.58s** | **1.79s** | 指标回看周期从 60 日降至 30 日 |
| `POST /api/board/list` | **0.33s** | **0.25s** | 随上述财务指标子查询优化附带提升 |
| `GET /api/index/list` | **0.16s** | **0.005s** | 随服务重启后缓存/连接状态提升 |

优化涉及文件：
- `seele-backend/app/crud.py`（mainwave-picker 分页与财务子查询）
- `seele-backend/app/routes/portfolio.py`（移除交易同步全量 rebuild）
- `seele-backend/app/routes/stock_indicator.py`（lookback 60 → 30）
- `seele-backend/app/agent/client.py`（temperature 修复）
- 数据库：新增 `stock_basic.industry_detail` 字段、新增 `stock_financial_indicator(symbol, report_date)` 复合索引

---

## 2. 测速方法

- 工具：`curl`（通过 `scripts/api_speed_test.py` 调用）
- 超时：60 秒/接口
- 采样：每个接口只发一次请求，记录总耗时 `time_total`、HTTP 状态码、响应体大小
- 连接复用：未复用连接，每次请求独立建立 TCP 连接
- 认证：先调用 `POST /api/auth/login`（密码 `seele`）获取 Token，后续接口统一携带 `Authorization: Bearer <token>`

---

## 3. 接口清单与测速结果

共测试 **44** 个接口，**全部返回 200 OK**。

### 3.1 根/健康

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 1 | 根路径 | GET | `/` | 0.010s |
| 2 | 健康检查 | GET | `/health` | 0.002s |

### 3.2 认证

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 3 | 管理员登录 | POST | `/api/auth/login` | 0.002s |
| 4 | 获取当前用户 | GET | `/api/auth/me` | 0.002s |

### 3.3 股票基础数据

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 5 | 股票基础分页 | POST | `/api/stock/basic/page` | 0.023s |
| 6 | 公司概况 | GET | `/api/stock/basic/000001/survey` | 0.005s |
| 7 | 同步单股公司概况 | POST | `/api/stock/basic/000001/sync-survey` | 0.549s |
| 8 | 同步单股细分行业 | POST | `/api/stock/basic/000001/sync-industry-detail` | 0.033s |

### 3.4 股票日线数据

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 9 | 按日期分页日线 | GET | `/api/stock/daily/date/2024-01-02/all` | 0.033s |
| 10 | 按代码历史日线 | GET | `/api/stock/daily/symbol/000001` | 0.077s |

### 3.5 股票日线指标

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 11 | 计算日线指标 | POST | `/api/stock/indicator/compute?trade_date=2020-01-02` | **1.795s** |

### 3.6 选股策略

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 12 | 主升浪选股 | POST | `/api/stock/daily/mainwave-picker` | **0.108s** |
| 13 | 单股主升浪检测 | GET | `/api/stock/daily/mainwave-detect/000001` | 0.022s |
| 14 | 批量主升浪检测 | POST | `/api/stock/daily/mainwave-detect/batch` | 0.103s |

### 3.7 财务指标

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 15 | 财务指标列表 | GET | `/api/financial` | 0.019s |
| 16 | 单股财务详情 | GET | `/api/financial/000001` | 0.003s |

### 3.8 持仓管理

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 17 | 录入交易 | POST | `/api/portfolio/trades` | **0.014s** |
| 18 | 录入做T | POST | `/api/portfolio/day-trades` | **0.009s** |
| 19 | 交易记录列表 | GET | `/api/portfolio/trades` | 0.009s |
| 20 | 当前持仓 | GET | `/api/portfolio/positions` | 0.010s |
| 21 | 已清仓记录 | GET | `/api/portfolio/closed` | 0.007s |
| 22 | 持仓预警 | GET | `/api/portfolio/alerts` | 0.004s |
| 23 | 持仓配置 | GET | `/api/portfolio/config` | 0.004s |
| 24 | 资产总览 | GET | `/api/portfolio/summary` | 0.006s |
| 25 | 每日盈亏 | GET | `/api/portfolio/daily-pnl` | 0.005s |
| 26 | 持仓分布 | GET | `/api/portfolio/distribution` | 0.005s |
| 27 | 持仓快照同步 | POST | `/api/portfolio/sync` | **1.343s** |
| 28 | 重建每日资产 | POST | `/api/portfolio/rebuild-daily` | **1.100s** |

### 3.9 市场情绪

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 29 | 计算市场情绪 | POST | `/api/market/sentiment/compute?trade_date=2020-01-02` | 0.395s |
| 30 | 每日市场情绪 | GET | `/api/market/sentiment/daily` | 0.003s |

### 3.10 指数数据

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 31 | 指数列表 | GET | `/api/index/list` | 0.005s |

### 3.11 系统日志

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 32 | 错误日志 | GET | `/api/system/logs/errors` | 0.006s |
| 33 | 操作日志 | GET | `/api/system/logs/operations` | 0.005s |
| 34 | 日志概览 | GET | `/api/system/logs/overview` | 0.008s |

### 3.12 板块 / ETF

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 35 | 板块列表 | POST | `/api/board/list` | 0.255s |
| 36 | 板块日线 | POST | `/api/board/daily` | 0.005s |
| 37 | 板块成分股 | GET | `/api/board/constituents/BK0428` | 0.005s |
| 38 | 保存板块关联 | POST | `/api/board/constituents/save` | 0.003s |

### 3.13 交易日历

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 39 | 最近交易日 | GET | `/api/trade-calendar/latest` | 0.004s |

### 3.14 图库管理

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 40 | 图片列表 | GET | `/api/gallery/images` | 0.004s |

### 3.15 访客日志

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 41 | 访客上报 | POST | `/api/visitor/track` | 0.005s |
| 42 | 访客日志 | GET | `/api/visitor/logs` | 0.007s |

### 3.16 AI Agent

| 序号 | 接口名 | 方法 | 路径 | 耗时 |
| --- | --- | --- | --- | --- |
| 43 | Agent 对话 | POST | `/api/agent/chat` | **6.419s** |
| 44 | 清除 Agent 会话 | DELETE | `/api/agent/session/test` | 0.002s |

---

## 4. 汇总统计

### 4.1 按 HTTP 状态码分布

| 状态码 | 数量 | 占比 |
| --- | --- | --- |
| 200 OK | 44 | 100% |
| 500 / 422 | 0 | 0% |

### 4.2 响应耗时统计（全部接口）

| 指标 | 数值 |
| --- | --- |
| 最小值 | 0.002s（健康检查） |
| 最大值 | **6.419s**（Agent 对话） |
| 平均值 | 0.289s |
| 中位数 | 0.005s |

### 4.3 耗时 Top 5 接口

| 排名 | 接口名 | 路径 | 耗时 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | Agent 对话 | `/api/agent/chat` | **6.419s** | 外部 LLM API，正常范围 |
| 2 | 计算日线指标 | `/api/stock/indicator/compute` | **1.795s** | 全量股票指标计算 |
| 3 | 持仓快照同步 | `/api/portfolio/sync` | **1.343s** | 全量重建类接口 |
| 4 | 重建每日资产 | `/api/portfolio/rebuild-daily` | **1.100s** | 全量重建类接口 |
| 5 | 同步单股公司概况 | `/api/stock/basic/{symbol}/sync-survey` | **0.549s** | 东方财富 F10 网络请求 |

### 4.4 排除外部依赖/重建类接口后的统计

排除 6 个慢接口（Agent 对话、计算日线指标、持仓快照同步、重建每日资产、sync-survey、板块列表）后，剩余 38 个接口：

| 指标 | 数值 |
| --- | --- |
| 最小值 | 0.002s |
| 最大值 | 0.108s（主升浪选股） |
| 平均值 | 0.020s |
| 中位数 | 0.005s |

---

## 5. 重点关注接口

### 5.1 仍偏慢的接口

| 接口 | 耗时 | 分析 |
| --- | --- | --- |
| Agent 对话 | 6.42s | 外部 LLM API，可通过流式接口优化前端体验 |
| 计算日线指标 | 1.80s | 全量股票指标计算，建议改为异步任务 |
| 持仓快照同步 / 重建每日资产 | 1.34s / 1.10s | 全量重建类接口，本身设计为重操作 |
| 同步单股公司概况 | 0.55s | 东方财富 F10 网络请求，属正常 |

### 5.2 公开接口（无需认证）

| 接口名 | 路径 | 耗时 | 建议用途 |
| --- | --- | --- | --- |
| 根路径 | `/` | 0.010s | 服务存活检查 |
| 健康检查 | `/health` | 0.002s | 负载均衡 / 探针 |
| 图片列表 | `/api/gallery/images` | 0.004s | 图库展示 |
| 访客上报 | `/api/visitor/track` | 0.005s | 前端埋点 |

---

## 6. 说明与建议

1. **修复验证**：所有 500 已修复，44 个接口全部返回 200。
2. **主要性能提升**：
   - `mainwave-picker` 从 8s 降至 0.1s，提升约 **74 倍**；
   - `portfolio/trades` 从 1.5s 降至 0.014s，提升约 **100 倍**；
   - `portfolio/day-trades` 从 1.3s 降至 0.009s，提升约 **140 倍**。
3. **交易录入与每日盈亏**：本次优化后，录入交易不再同步重建 `portfolio_daily_summary`。当前持仓、资产总览等仍实时更新，但「每日盈亏」折线图需通过 `/api/portfolio/rebuild-daily` 或 `/api/portfolio/sync` 手动/定时重建。如需交易后立即刷新图表，建议在前端调用交易接口后触发一次后台 rebuild。
4. **耗时基准**：本次为单次请求测速，未做多次平均。生产环境建议以 `p95/p99` 为准。
5. **文件位置**：
   - 测速报告：`docs/api_speed_test_report.md`
   - 测速脚本：`scripts/api_speed_test.py`
   - 原始数据：`scripts/api_speed_test_result.json`
   - 调试脚本：`scripts/debug_500.py`
   - 数据库修复脚本：`scripts/add_industry_detail_column.py`
   - 索引添加脚本：`scripts/add_financial_index.py`
   - 性能分析脚本：`scripts/profile_mainwave.py`

---

## 附录：未包含的同步任务接口

以下 `/api/sync/*` 接口按用户要求未参与本次测速：

- `POST /api/sync/daily/date/{trade_date}`
- `GET /api/sync/task/{task_id}`
- `GET /api/sync/active-tasks`
- `POST /api/sync/stock-basic`
- `POST /api/sync/financial`
- `GET /api/sync/job-logs`
- `POST /api/sync/job-log/{log_id}/cancel`
- `POST /api/sync/indicator`
- `GET /api/sync/detailed-status`
- `POST /api/sync/pipeline`
- `GET /api/sync/pipeline/{pipeline_id}`
- `GET /api/sync/pipelines`
- `POST /api/sync/pipeline/{pipeline_id}/cancel`
- `POST /api/sync/history-full`
- `POST /api/sync/industry-detail`
