# Seele 正式环境数据接口文档

## 基础信息

| 项 | 内容 |
|---|---|
| 正式域名 | `<YOUR_DOMAIN>` |
| 基础地址 | `https://<YOUR_DOMAIN>/api` |
| 认证方式 | JWT Bearer Token |
| 请求头 | `Authorization: Bearer <token>` |
| Token 有效期 | 7 天 |

> 生产环境 Nginx 配置见 [deploy/nginx-seele.conf](../deploy/nginx-seele.conf)，API 反向代理到后端 `127.0.0.1:9000`。

---

## 认证接口

### 管理员登录获取 Token

| 项 | 说明 |
|---|---|
| URL | `POST /api/auth/login` |
| 文件 | [seele-backend/app/routes/auth.py](../seele-backend/app/routes/auth.py) |
| 说明 | **无需认证**，用于获取后续请求的 JWT |

#### 请求参数 (Body)

```json
{
  "password": "你的管理员密码"
}
```

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

> 管理员密码由环境变量 `ADMIN_PASSWORD` 配置，默认见 [seele-backend/app/config.py](../seele-backend/app/config.py)。

---

## 认证范围说明

后端在 [seele-backend/app/main.py](../seele-backend/app/main.py) 对大部分路由统一附加了认证依赖 `auth_dep = [Depends(get_current_user)]`。

**需要认证的模块（本文所有数据接口均在此列）**：

- `/api/stock/*` — 股票基础、日线、指标
- `/api/stock/daily/mainwave-picker` — 主升浪选股
- `/api/portfolio/*` — 持仓管理
- `/api/board/*` — 板块/ETF
- `/api/sync/*`、`/api/system_log/*` 等

**无需认证的接口**：

- `POST /api/auth/login`
- `GET /api/gallery/images`
- `POST /api/visitor/track`
- `/health`

---

## 请求示例

### cURL

```bash
# 1. 登录获取 token
curl -X POST https://<YOUR_DOMAIN>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"你的管理员密码"}'

# 2. 调用数据接口（将 <token> 替换为实际 token）
curl -X POST https://<YOUR_DOMAIN>/api/stock/daily/mainwave-picker \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"page_num":1,"page_size":10}'
```

### JavaScript / Axios

```javascript
const token = localStorage.getItem('seele_token')

axios.post('https://<YOUR_DOMAIN>/api/stock/daily/mainwave-picker', {
  page_num: 1,
  page_size: 10
}, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

---

## 1. 主升浪选股结果

| 项 | 说明 |
|---|---|
| URL | `POST /api/stock/daily/mainwave-picker` |
| 文件 | [seele-backend/app/routes/pickers.py](../seele-backend/app/routes/pickers.py) |
| 说明 | 关联日线、指标、财务表，返回符合主升浪条件的股票；**已强制过滤主板、非 ST、非创业板/科创板/北交所**。不满足选股条件但当前持仓的股票也会被补充返回。 |

### 请求参数 (Body)

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page_num | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 10 |
| sort_field | string | 否 | 排序字段，如 `symbol`、`close`、`score`、`trend_score` 等 |
| sort_order | string | 否 | `asc` / `desc` |
| symbol | string | 否 | 代码模糊 |
| name | string | 否 | 名称模糊 |
| industry | string | 否 | 行业 |
| market | string | 否 | 市场 |
| area | string | 否 | 地区 |
| trade_date | string | 否 | 交易日 `YYYY-MM-DD`，不传取指标表最新日期 |
| float_market_cap_min | float | 否 | 流通市值最小值（亿元） |
| close_max | float | 否 | 收盘价最大值 |
| avg_turnover_min | float | 否 | 10 日平均换手率最小值（%） |
| avg_amount_min | float | 否 | 10 日平均成交额最小值（元） |
| ma_bull | bool | 否 | 均线多头排列（收盘价 > MA5 > MA10） |
| exclude_st / exclude_cyb / exclude_kcb / exclude_bse | bool | 否 | 接口内部已强制为 true，传参无效 |

### 响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "id": 1,
        "trade_date": "2026-06-11",
        "symbol": "000001",
        "stock_name": "平安银行",
        "name": "平安银行",
        "industry": "银行",
        "market": "主板",
        "area": "深圳",
        "float_market_cap": 1234.56,
        "open": 10.0,
        "high": 10.2,
        "low": 9.9,
        "close": 10.1,
        "volume": 1000000,
        "amount": 10100000,
        "amplitude": 3.0,
        "pct_chg": 1.5,
        "price_change": 0.15,
        "turnover": 2.1,
        "ma5": 9.9,
        "ma10": 9.8,
        "ma20": 9.7,
        "ma30": 9.6,
        "ma60": 9.5,
        "vol_ma5": 900000,
        "vol_ma10": 950000,
        "amount_ma5": 9000000,
        "amount_ma10": 9500000,
        "turnover_ma5": 2.0,
        "turnover_ma10": 2.05,
        "chg_5d": 5.0,
        "chg_10d": 8.0,
        "adx": 25.0,
        "net_profit": 1000000,
        "net_profit_yoy": 10.0,
        "roe": 12.0,
        "is_holding": false,
        "bull_days_5": 4,
        "bull_days_10": 7,
        "bull_days_20": 16,
        "layer": 20,
        "launch_date": "2026-05-20",
        "launch_pct_chg": 18.5,
        "score": {
          "total": 75.0,
          "trend_score": 25.0,
          "strength_score": 30.0,
          "momentum_score": 20.0,
          "hard_pass": true
        }
      }
    ],
    "total": 100,
    "page_num": 1,
    "page_size": 10,
    "trade_date": "2026-06-11"
  }
}
```

### 选股条件

选股逻辑位于 [seele-backend/app/crud.py](../seele-backend/app/crud.py) `StockBasicCRUD.get_mainwave_list`，按以下规则筛选：

#### 硬性门槛（不可关闭）

| 条件 | 说明 |
|---|---|
| 市场 | `stock_basic.market == "主板"` |
| ST 过滤 | 名称不含 `ST` |
| 创业板过滤 | 代码不以 `300%`、`301%` 开头 |
| 科创板过滤 | 代码不以 `688%`、`689%` 开头 |
| 财务过滤 | 若存在财务数据，要求 `net_profit > 0` 且 `total_revenue > 0` |
| 指标过滤 | `stock_daily_indicator.ma5` 非空且大于 0 |

#### 可选过滤参数

| 参数 | 过滤字段 | 说明 |
|---|---|---|
| close_max | `stock_daily.close <= close_max` | 收盘价上限 |
| avg_turnover_min | `stock_daily_indicator.turnover_ma10 >= avg_turnover_min` | 10 日平均换手率下限（%） |
| avg_amount_min | `stock_daily_indicator.amount_ma10 >= avg_amount_min` | 10 日平均成交额下限（元） |
| ma_bull | `close > ma5 > ma10` | 均线多头排列 |
| float_market_cap_min | 内存过滤 | 流通市值下限（亿元），见下方计算方式 |
| symbol / name / industry / market / area | 文本模糊匹配 | 代码、名称、行业、市场、地区 |

#### 流通市值估算

由于 `stock_basic.float_market_cap` 更新不及时，接口使用当日数据实时估算：

```
流通市值(亿元) ≈ (成交量 × 100 ÷ 换手率%) × 收盘价 ÷ 1亿
```

即：`total_shares = volume * 100.0 / turnover`，`float_market_cap = total_shares * close / 100000000`

#### 持仓补充

不满足选股条件但当前持仓的股票会被强制补充到结果中，并在 `is_holding` 字段标记为 `true`。

### 前端实际调用参数

接口封装：[seele-frontend/src/api/stock.js](../seele-frontend/src/api/stock.js) `getMainwavePicker`

三个 View 共用该接口：
- [MainwavePickerView.vue](../seele-frontend/src/views/MainwavePickerView.vue) — 选股页
- [MainwaveScorerView.vue](../seele-frontend/src/views/MainwaveScorerView.vue) — 评分页
- [MainwaveView.vue](../seele-frontend/src/views/MainwaveView.vue) — 分组页

#### API 层默认参数

```javascript
{
  page_num: 1,
  page_size: 10,
  sort_field: 'symbol',
  sort_order: 'asc'
}
```

调用方传入的参数会覆盖以上默认值。

#### 前端筛选表单默认值

| 前端字段 | 默认值 | 说明 |
|---|---|---|
| symbol | `''` | 代码模糊 |
| name | `''` | 名称模糊 |
| tradeDate | `''`（加载后自动填充最近交易日） | 交易日 |
| floatMarketCapMin | `200` | 流通市值 ≥ 200 亿 |
| closeMax | `300` | 收盘价 ≤ 300 元 |
| avgTurnoverMin | `2` | 10 日平均换手率 ≥ 2% |
| avgAmountMin | `2` | 10 日平均成交额 ≥ 2 亿 |
| maBull | `true` | 均线多头排列（默认勾选） |

#### 字段转换规则

| 前端字段 | 后端参数 | 转换说明 |
|---|---|---|
| pageNum | page_num | 直接使用 |
| pageSize | page_size | 直接使用 |
| sortField | sort_field | 直接使用 |
| sortOrder | sort_order | 直接使用 |
| symbol | symbol | trim 后非空才传 |
| name | name | trim 后非空才传 |
| tradeDate | trade_date | 非空才传 |
| floatMarketCapMin | float_market_cap_min | 非 null 才传 |
| closeMax | close_max | 非 null 才传 |
| avgTurnoverMin | avg_turnover_min | 非 null 才传 |
| avgAmountMin | avg_amount_min | **乘以 100,000,000（元）** |
| maBull | ma_bull | 为 true 时才传 |

> 注意：`avgAmountMin` 前端输入单位是"亿"，传给后端时自动转换为元。

#### 各页面调用差异

| 页面 | 分页 | 默认排序 | 特殊说明 |
|---|---|---|---|
| 选股页 | 分页（10/20/50/100） | `score` / `desc` | 点击表头切换排序 |
| 评分页 | 分页（10/20/50/100） | `score` / `desc` | `trendScore` / `strengthScore` / `momentumScore` 会映射为后端字段 |
| 分组页 | 不分页 | `score` / `desc` | 固定 `page_num: 1, page_size: 9999`，一次性拉取全部 |

---

## 2. 主升浪评分

| 项 | 说明 |
|---|---|
| 获取方式 | 不是独立接口，内嵌在 **主升浪选股结果** 的 `score` 字段中 |
| 计算服务 | [seele-backend/app/services/mainwave_scorer.py](../seele-backend/app/services/mainwave_scorer.py) |

### 评分字段

| 字段 | 类型 | 说明 |
|---|---|---|
| total | float | 总分 = 趋势分 + 强势分 + 动量分 |
| trend_score | float | 趋势分 |
| strength_score | float | 强势分 |
| momentum_score | float | 动量分 |
| hard_pass | bool | 是否 `total >= 60` |

### 评分计算规则

评分考察区间：**从启动日（`launch_date`）到最近交易日** 的每个交易日日线数据。

#### 趋势分（trend_score）

遍历考察区间内每个交易日，根据收盘价与均线相对位置计分：

| 条件 | 得分 |
|---|---|
| 收盘价 ≥ MA5 | +3 |
| 收盘价 < MA5 | -1 |
| 收盘价 ≥ MA10 | +2 |
| 收盘价 < MA10 | -2 |
| 收盘价 ≥ MA20 | +1 |
| 收盘价 < MA20 | -3 |

#### 强势分（strength_score）

遍历考察区间内每个交易日，根据当日涨跌幅计分：

| 涨跌幅 | 得分 |
|---|---|
| > 9% | +3 |
| 5% ~ 9% | +2 |
| 0% ~ 5% | +1 |
| -5% ~ 0% | -1 |
| -9% ~ -5% | -2 |
| < -9% | -3 |

#### 动量分（momentum_score）

遍历考察区间内每个交易日，结合涨跌幅与换手率相对五日平均换手率计分：

| 条件 | 得分 |
|---|---|
| 涨幅 > 5% 且 换手率 > 五日平均换手率 | `+5 × (turnover / turnover_ma5)` |
| 跌幅 < -5% 且 换手率 > 五日平均换手率 | `-5 × (turnover / turnover_ma5)` |

#### 通过标准

- `hard_pass = total >= 60`
- 总分由三个维度相加，无上限/下限硬截断

---

## 3. 主升浪分组

| 项 | 说明 |
|---|---|
| 获取方式 | 不是独立接口，字段内嵌在 **主升浪选股结果** 中 |
| 计算服务 | [seele-backend/app/services/mainwave_scorer.py](../seele-backend/app/services/mainwave_scorer.py) |

### 分组字段

| 字段 | 类型 | 说明 |
|---|---|---|
| bull_days_5 | int | 最近 5 日多头排列天数 |
| bull_days_10 | int | 最近 10 日多头排列天数 |
| bull_days_20 | int | 最近 20 日多头排列天数 |
| layer | int / string | 分层结果：20 / 10 / 5 / `'OFF'` |
| launch_date | string | 启动日 `YYYY-MM-DD` |
| launch_pct_chg | float | 启动日至今涨幅（%） |

### 多头排列定义

当日满足 `MA5 > MA10 > MA20` 即视为多头排列。

### 分层规则

| 分组 | 条件 | 优先级 |
|---|---|---|
| **20 日组** | 最近 20 个交易日中 ≥ 16 天多头排列（80%） | 高 |
| **10 日组** | 最近 10 个交易日中 ≥ 7 天多头排列（70%） | 中 |
| **5 日组** | 最近 5 个交易日中 ≥ 4 天多头排列（80%） | 低 |
| **OFF** | 以上都不满足 | 最低 |

### 启动日计算

启动日用于确定评分考察区间和 `launch_pct_chg`：

1. 根据分层结果确定窗口：20 日组用 20 日窗口、10 日组用 10 日窗口、5 日组/OFF 用 5 日窗口。
2. 从窗口最远交易日往前遍历，找到第一个触发以下任一条件的交易日作为启动日：
   - 单日跌幅 < -2%
   - 连续两天涨幅 < 1%
3. 若未触发上述条件，则取窗口内最早有数据的交易日作为启动日。

### 启动日至今涨幅

```
launch_pct_chg = (current_close - launch_close) / launch_close × 100%
```

---

## 4. 股票当前日线获取

### 4.1 按交易日期获取全市场 A 股日线

| 项 | 说明 |
|---|---|
| URL | `GET /api/stock/daily/date/{trade_date}/all` |
| 文件 | [seele-backend/app/routes/stock_daily.py](../seele-backend/app/routes/stock_daily.py) |
| 说明 | 关联 `stock_basic` 和 `stock_daily_indicator`，返回指定交易日的 A 股日线 |

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| trade_date | path | 是 | 交易日，支持 `YYYY-MM-DD` 或 `YYYYMMDD` |
| exclude_st | bool | 否 | 过滤 ST |
| exclude_cyb | bool | 否 | 过滤创业板 |
| exclude_kcb | bool | 否 | 过滤科创板 |
| exclude_bse | bool | 否 | 过滤北交所 |
| symbol | string | 否 | 代码或名称模糊搜索 |
| min_pct_chg | float | 否 | 最小涨幅百分比过滤 |
| sort_field | string | 否 | 排序字段 |
| sort_order | string | 否 | `asc` / `desc` |
| page_num | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 10，最大 500 |

### 响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "id": 1,
        "trade_date": "2026-06-11",
        "symbol": "000001",
        "open": 10.0,
        "high": 10.2,
        "low": 9.9,
        "close": 10.1,
        "volume": 1000000,
        "amount": 10100000,
        "amplitude": 3.0,
        "pct_chg": 1.5,
        "price_change": 0.15,
        "turnover": 2.1,
        "ma5": 9.9,
        "ma10": 9.8,
        "ma20": 9.7,
        "ma30": 9.6,
        "ma60": 9.5,
        "vol_ma5": 900000,
        "vol_ma10": 950000,
        "turnover_ma5": 2.0,
        "turnover_ma10": 2.05,
        "stock_name": "平安银行",
        "industry": "银行",
        "market": "主板",
        "area": "深圳"
      }
    ],
    "total": 5000,
    "page_num": 1,
    "page_size": 10,
    "trade_date": "2026-06-11"
  }
}
```

### 4.2 按股票代码获取全部历史日线

| 项 | 说明 |
|---|---|
| URL | `GET /api/stock/daily/symbol/{symbol}` |
| 说明 | 返回单只股票全部历史日线（含指标） |

---

## 5. 板块涨幅

### 5.1 板块/ETF 列表（含涨幅）

| 项 | 说明 |
|---|---|
| URL | `POST /api/board/list` |
| 文件 | [seele-backend/app/routes/board.py](../seele-backend/app/routes/board.py) |
| 说明 | 分页查询板块/ETF 列表，返回指定交易日或最新交易日的涨跌幅 |

### 请求参数 (Body)

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page_num | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 50，最大 500 |
| category | string | 否 | 类型过滤：`industry` / `concept` / `etf` |
| keyword | string | 否 | 名称模糊搜索 |
| trade_date | string | 否 | 指定交易日 `YYYY-MM-DD`，不传取最新 |

### 响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "code": "BK0429",
        "name": "银行",
        "category": "industry",
        "exchange": "SZ",
        "source": "ths",
        "constituent_count": 42,
        "latest_close": 1234.56,
        "latest_pct_chg": 2.35,
        "latest_trade_date": "2026-06-11",
        "amount": 560000000,
        "chg_5d": 5.2,
        "chg_10d": 8.1
      }
    ],
    "total": 500,
    "page_num": 1,
    "page_size": 50
  }
}
```

### 5.2 其他相关接口

| URL | 方法 | 说明 |
|---|---|---|
| `/api/board/daily` | POST | 单板块/ETF 日线数据分页查询 |
| `/api/board/constituents/{code}` | GET | 板块成分股列表含最新行情 |

---

## 6. 当前持仓

| 项 | 说明 |
|---|---|
| URL | `GET /api/portfolio/positions` |
| 文件 | [seele-backend/app/routes/portfolio.py](../seele-backend/app/routes/portfolio.py) |
| 说明 | 获取当前持仓及浮动盈亏，`current_price` / `market_value` / `unrealized_pnl` 会按最新日线实时重新计算 |

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| group | string | 否 | 持仓分组过滤，如 `default` |

### 响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "symbol": "000001",
      "name": "平安银行",
      "quantity": 1000,
      "avg_cost": 9.8,
      "current_price": 10.1,
      "market_value": 10100.0,
      "unrealized_pnl": 300.0,
      "unrealized_pnl_pct": 3.06,
      "stop_loss_price": 9.0,
      "take_profit_price": 11.0,
      "alert_triggered": 0,
      "group": "default",
      "remark": null,
      "first_buy_date": "2026-05-01",
      "updated_at": "2026-06-11 15:30:00",
      "history_pnl": 300.0,
      "history_pnl_pct": 3.06
    }
  ]
}
```

### 6.1 相关辅助接口

| URL | 方法 | 说明 |
|---|---|---|
| `/api/portfolio/summary` | GET | 资产总览 |
| `/api/portfolio/daily-pnl` | GET | 每日盈亏时间序列 |
| `/api/portfolio/distribution` | GET | 当前持仓占总资产分布 |
| `/api/portfolio/alerts` | GET | 止损/止盈预警持仓 |
| `/api/portfolio/positions/{symbol}` | PUT | 更新持仓止损止盈/分组/备注 |

---

## 通用响应说明

接口统一返回：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

- `code != 200` 表示业务异常或参数错误。
- 分页接口 `data` 包含 `list`、`total`、`page_num`、`page_size`（选股结果额外包含 `trade_date`）。
- 列表接口 `data` 为数组。
