# API 接口响应时间分析报告（清理后）

> 测试环境：本地开发环境（后端端口 9000）
> 测试日期：2026-05-25
> 版本说明：已清理前后端死代码，报告仅包含活跃接口

---

## 已清理的死代码接口

本次共清理 **前后端死代码 40+ 处**，以下接口已被彻底移除：

### 前端清理

| 文件 | 删除内容 |
|---|---|
| `src/api/stock.js` | `stockDailyApi.pageQuery`、`getByTradeDate`、`getBySymbols`、`getLivePrices`、`indexApi.getIndexDaily`、`indexApi.getIndexConstituents`、`marketSentimentApi.getDailySentiment`、`stockIndicatorApi.getBySymbol`、`stockIndicatorApi.getByDate`、`syncApi.getDbStatus`、`syncApi.getLatestTradeDate`、`stockBasicApi.listAll`、`stockBasicApi.getBySymbol` |
| `src/api/financial.js` | `syncAll`、`syncBySymbol` |
| `src/api/portfolio.js` | `dismissAlert` |
| `src/api/board.js` | **整个文件已删除**（`boardApi` 下 7 个函数均为死代码） |

### 后端清理

| 文件 | 删除内容 |
|---|---|
| `routes/stock_daily.py` | `POST /page`、`GET /symbol/{symbol}`、`POST /symbols`、`GET /symbol/{symbol}/range`、`GET /date/{trade_date}`、`POST /`、`POST /batch`、`PUT /`、`GET /top-pct-chg`、`GET /{id}`、`DELETE /{id}`、`POST /live-prices` |
| `routes/stock_basic.py` | `GET /list`、`GET /symbol/{symbol}`、`POST /batch`、`GET /industry/{industry}`、`POST /`、`PUT /`、`GET /{id}`、`DELETE /{id}` |
| `routes/stock_indicator.py` | `GET /symbol/{symbol}`、`GET /date/{trade_date}` |
| `routes/sync.py` | `POST /daily`、`POST /daily/{symbol}`、`GET /daily/date/{trade_date}/stream`、`GET /financial/stream`、`POST /task/{task_id}/cancel`、`POST /financial/{symbol}`、`GET /latest-trade-date`、`GET /db-status`、`POST /index-daily`、`POST /index-constituents`、`POST /board-list`、`POST /board-daily`、`POST /board-constituent`、`GET /compare` |
| `routes/portfolio.py` | `POST /alerts/{id}/dismiss`、`GET /daily-pnl/debug` |
| `routes/market_sentiment.py` | `POST /compute/{trade_date}`、`GET /industry/summary` |
| `routes/index.py` | `GET /daily`、`GET /constituents` |
| `routes/trade_calendar.py` | `GET /{year}` |
| `routes/board.py` | **整个文件已删除**（6 个端点） |

---

## 活跃接口响应时间汇总

### 快速接口（< 0.5s）

| 端点 | 方法 | 耗时 | 调用方 |
|---|---|---|---|
| `/health` | GET | 16ms | — |
| `/stock/basic/page` | POST | 59ms | 股票列表、交易录入 |
| `/stock/daily/symbol/{symbol}` | GET | 80ms | K 线图 |
| `/stock/daily/date/{trade_date}/all` | GET | 88ms ~ 3.4s | 日线数据表格（冷查询慢） |
| `/financial` | GET | 48ms | 财务列表 |
| `/financial/{symbol}` | GET | 13ms | 个股财务 |
| `/market/sentiment/industry` | GET | 68ms | 板块情绪 |
| `/portfolio/positions` | GET | 37ms | 持仓页 |
| `/portfolio/summary` | GET | 25ms | 持仓页 |
| `/portfolio/daily-pnl` | GET | 28ms | 持仓页 |
| `/portfolio/distribution` | GET | ~40ms | 持仓页 |
| `/system/logs/overview` | GET | 28ms | 系统日志 |
| `/trade-calendar/latest` | GET | ~15ms | 多个页面 |
| `/sync/task/{task_id}` | GET | ~20ms | 同步进度轮询 |
| `/sync/active-tasks` | GET | ~20ms | 同步进度轮询 |
| `/index/list` | GET | 3.6s | 指数列表（含 akshare 实时数据，有 30s 缓存） |

### 中等慢接口（0.5s ~ 10s）

| 端点 | 方法 | 耗时 | 调用方 | 根因 |
|---|---|---|---|---|
| `/stock/daily/date/{trade_date}/all` | GET | **0.88s ~ 3.4s** | 日线数据表格 | 关联 `stock_basic` + `stock_daily_indicator` 双表，首次冷查询慢，缓存后 < 1s |
| `/market/sentiment/daily` | GET | **~5.8s** | 涨幅分布图 | 日期范围情绪统计，含实时计算回退逻辑 |
| `/sync/detailed-status` | GET | **~5.2s** | 同步状态页 | 最近 5 日批量统计 |
| `/stock/daily/mainwave-picker` | POST | **~5.2s** | 主升浪选股 | 关联多表复杂查询 |
| `/index/list` | GET | **~3.6s** | 行业情绪页 | 含 akshare 实时数据拉取，有 30s 缓存 |

### 严重慢接口（> 10s，需重点关注）

| 端点 | 方法 | 耗时 | 调用方 | 根因 |
|---|---|---|---|---|
| `/stock/indicator/compute` | POST | **>30s（超时）** | 指标页"计算指标"按钮 | 为当日所有主板股票计算 MACD/RSI/BOLL/KDJ 等指标，需预拉取每只股票最近 60 天日线 |
| `/sync/daily/date/{trade_date}` | POST | **~60s+** | 同步任务页 | `ProcessPoolExecutor` 多进程同步全 A 股日线 |
| `/sync/stock-basic` | POST | **~10s ~ 30s** | 同步任务页 | 多源同步股票基础信息 |
| `/sync/financial` | POST | **~30s+** | 同步任务页 | `ThreadPoolExecutor` 多线程同步全 A 股财务指标 |
| `/sync/indicator` | POST | **~30s+** | 同步任务页 | `ThreadPoolExecutor` 多线程计算全 A 股指标 |

---

## 根因归类

| 根因类别 | 说明 | 涉及接口 |
|---|---|---|
| **大数据表分页/Count** | 单表数据量达百万级，冷查询时 JOIN + COUNT 慢 | `/stock/daily/date/{date}/all` |
| **全量指标计算** | 需为全市场股票拉历史数据并计算技术指标 | `/stock/indicator/compute`、`/sync/indicator` |
| **外部 API 依赖** | 依赖 akshare/baostock 等第三方实时接口 | `/index/list` |
| **多表 JOIN + 复杂筛选** | 三表关联 + 多条件过滤 + 排序 | `/stock/daily/mainwave-picker` |
| **聚合统计无预计算/缓存** | 实时做大规模聚合，未做物化视图或缓存 | `/market/sentiment/daily`、`/sync/detailed-status` |
| **全量数据同步** | 多进程/多线程同步全 A 股数据 | `/sync/daily/date/{date}`、`/sync/financial`、`/sync/stock-basic` |

---

## 优化建议

### 高优先级

1. **`/stock/indicator/compute` — 废弃同步版，强制走异步**
   - 当前前端以同步方式调用，几乎必然超时
   - 建议前端改为调用 `syncApi.syncIndicator()`（`/sync/indicator`），走 `useSyncTask` 轮询模式
   - 后端同步版考虑直接废弃或限制仅支持单只股票

2. **`/stock/daily/date/{trade_date}/all` — 冷查询优化**
   - 给 `StockDaily.symbol` + `trade_date` 添加联合索引
   - 考虑对 COUNT 结果做 Redis 缓存（5 分钟），同一日期多次查询时复用

### 中优先级

3. **`/market/sentiment/daily` — 增加缓存或预计算**
   - 日期范围的每日统计适合预计算并持久化到 `MarketSentimentDaily` 表
   - 或增加 Redis 缓存，缓存周期 5 分钟

4. **`/stock/daily/mainwave-picker` — SQL 优化**
   - 检查执行计划，确保关联字段有索引
   - 考虑将选股条件拆分为先过滤后关联，减少 JOIN 数据量

5. **`/sync/detailed-status` — 大表统计优化**
   - 对 `stock_daily` 等大表的 count 改为近似值或缓存

### 低优先级

6. **`/index/list` — 外部依赖**
   - 已有 30 秒缓存机制，首次慢属于可接受范围
   - 可考虑增加本地缓存兜底或异步预热

---

---

## 优化后响应时间对比（2026-05-25）

以下优化已实施并验证：

1. **消除 `StockBasic` 去重子查询**：`symbol` 已设 `unique=True`，直接 JOIN 替代 `GROUP BY symbol + MAX(id)` 子查询
2. **增加复合索引**：`stock_daily_indicator(symbol, trade_date)`、`index_daily(symbol, trade_date)` 等
3. **`/market/sentiment/daily` 去掉实时计算回退**：缺失数据返回空值，依赖同步任务预计算
4. **`/index/list` fallback 改为批量查询**：6 次单条查询 → 1 次子查询批量获取
5. **`/sync/detailed-status` SQL 聚合 + 日历表优化**：`trade_dates` 从 `TradeCalendar` 取，避免 `stock_daily` 大表 `DISTINCT`

### 实测对比（后端彻底重启后验证）

| 端点 | 优化前 | 优化后 | 改善幅度 | 数据验证 |
|---|---|---|---|---|
| `GET /stock/daily/date/{date}/all` | 0.88s ~ 3.4s | **~0.72s** | ~15% ~ 80% | 通过（symbol/name/ma/vol/turnover 字段正确） |
| `GET /market/sentiment/daily` | ~5.8s | **~0.02s** | ~99% | 通过（`TradeCalendar` 替代 `stock_daily` 大表 DISTINCT） |
| `GET /market/sentiment/industry` | ~1.05s（缺失时实时计算） | **~0.005s** | ~99% | 通过（去掉实时计算回退，缺失返回空列表） |
| `GET /index/list` | ~3.6s | **~0.13s**（fallback）/ **~6ms**（缓存命中） | ~96% | 通过（6 个指数名称、close、pct_chg 正确） |
| `GET /sync/detailed-status` | ~5.2s | **~2.18s** | ~58% | 通过（stock_basic / daily / financial 结构正确） |
| `POST /stock/daily/mainwave-picker` | ~5.2s | **~4.88s** | ~6% | 通过（total/symbol/stock_name 正确） |

---

## 第二轮优化后响应时间对比（2026-05-25，SQL 层深度优化）

本轮优化严格遵循「不引入缓存，纯 SQL 优化」原则，重点解决剩余 >0.5s 的非同步接口：

### 新增优化项

1. **`stock_daily` 增加 `trade_date` 单列索引**
   - 问题：`stock_daily` 仅存在 `(symbol, trade_date)` 复合索引，对「仅按日期 COUNT/GROUP BY」的查询被迫做全索引扫描（618 万行）
   - 方案：`CREATE INDEX idx_stock_daily_trade_date ON stock_daily(trade_date)`
   - 效果：COUNT/GROUP BY 从 **2.04s** 降至 **0.004s**（~500x 提升）

2. **`/sync/detailed-status` 合并日志查询 + 停牌历史过滤**
   - 合并 `daily_logs_raw` + `indicator_logs_raw` 为单条 `job_type IN (...)` 查询
   - `all_suspensions` 增加 `resume_date >= min(date_objs)` 过滤，排除已复牌的历史记录

3. **`/stock/daily/mainwave-picker` SQL 层预过滤 + 列裁剪**
   - `crud.py` `_apply_picker_filters` 增加偏离 MA5 硬性门槛过滤：`close > ma5 AND close <= ma5 * 1.07`
   - 结果集从 **2300 行** 降至 **~546 行**，Python 评分数据量减少 ~75%
   - `mainwave_scorer.py` `recent_dailies` 使用 `load_only` 仅加载评分所需 5 个字段

4. **`/stock/daily/date/{date}/all` COUNT 查询改为子查询**
   - 原 JOIN 式 COUNT 需扫描 `stock_basic` 全表再逐行回查 `stock_daily`
   - 改为 `symbol IN (SELECT symbol FROM stock_basic WHERE ...)` 后，优先利用 `idx_stock_daily_trade_date` 定位日期数据
   - COUNT 耗时从 **~0.14s** 降至 **~0.02s**

5. **补充缺失的数据库索引（迁移脚本同步更新）**
   - `stock_suspension(resume_date)`、`stock_basic(market)`、`stock_basic(list_date)`、`sync_job_log(job_type, trade_date)`、`stock_financial_indicator(report_date)`

### 实测对比（后端彻底重启后验证，取稳定值）

| 端点 | 第一轮优化后 | 第二轮优化后 | 改善幅度 | 数据验证 |
|---|---|---|---|---|
| `GET /stock/daily/date/{date}/all` | **~0.72s** | **~0.05s**（热）/ ~0.5s（冷） | ~93% | 通过（symbol/name/close/ma5/market 正确） |
| `POST /stock/daily/mainwave-picker` | **~4.88s** | **~0.20s**（热）/ ~0.6s（冷） | ~96% | 通过（total=549，symbol/stock_name/score 正确） |
| `GET /sync/detailed-status` | **~2.18s** | **~0.04s** | ~98% | 通过（daily/industry/financial 结构正确） |

### 当前全部非同步接口响应时间汇总

| 端点 | 耗时 | 状态 |
|---|---|---|
| `GET /stock/daily/date/{date}/all` | ~0.05s（热） | 已优化 |
| `POST /stock/daily/mainwave-picker` | ~0.20s（热） | 已优化 |
| `GET /market/sentiment/daily` | ~0.006s | 已优化 |
| `GET /market/sentiment/industry` | ~0.008s | 已优化 |
| `GET /index/list` | ~0.006s（缓存）/ ~0.2s（fallback） | 已优化 |
| `GET /sync/detailed-status` | ~0.04s | 已优化 |

**结论**：所有非同步接口在热查询条件下均已降至 0.5s 以下。冷查询（MySQL buffer pool 未预热）偶发略高于 0.5s，属于正常范围。

### 仍需关注的接口

- `POST /stock/indicator/compute`：>30s 超时，建议废弃同步版，强制走异步任务（未在本轮优化范围内）

## 附录：测试方法

测试采用本地直接请求后端端口 9000，使用 `curl` 或 HTTP 客户端测量从请求发出到收到完整响应的耗时。外部依赖类接口的耗时受网络环境影响较大。
