# Seele 股票数据管理 API 文档（前端版）

> 所有接口前缀：`http://<host>:<port>/api`
> 
> 示例：`http://localhost:8000/api`

---

## 一、通用约定

### 1. 基础信息
| 项目 | 说明 |
|------|------|
| Base URL | `http://localhost:8000/api`（以实际部署为准） |
| Content-Type | `application/json` |
| 通用响应格式 | `{ code: 200, message: "success", data: ... }` |
| 日期格式 | **大部分接口支持 `2026-04-12` 或 `20260412`**（具体见备注） |

### 2. 通用分页响应结构
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [],
    "total": 0,
    "page_num": 1,
    "page_size": 10
  }
}
```

---

## 二、股票基础数据（`/stock/basic`）

### 2.1 分页查询股票列表（GET）
```
GET /api/stock/basic/list
```

**Query 参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page_num | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 100 |
| sort_field | string | 否 | 排序字段（symbol/name/industry/market/area/listDate） |
| sort_order | string | 否 | 排序方向：`asc` / `desc`，默认 `asc` |
| symbol | string | 否 | 股票代码，精确匹配 |
| name | string | 否 | 股票名称，模糊匹配 |
| industry | string | 否 | 行业，精确匹配 |
| market | string | 否 | 市场板块，精确匹配 |
| area | string | 否 | 地区，精确匹配 |
| exclude_st | bool | 否 | 是否过滤ST股票，默认 `false` |
| exclude_cyb | bool | 否 | 是否过滤创业板，默认 `false` |
| exclude_kcb | bool | 否 | 是否过滤科创板，默认 `false` |
| exclude_bse | bool | 否 | 是否过滤北交所，默认 `false` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      { "id": 1, "symbol": "000001", "name": "平安银行", "area": "深圳", "industry": "银行", "market": "主板", "list_date": "1991-04-03" }
    ],
    "total": 1,
    "page_num": 1,
    "page_size": 100
  }
}
```

---

### 2.2 分页查询股票列表（POST）
```
POST /api/stock/basic/page
```
**Body 参数**：与 2.1 的 Query 参数完全一致，以 JSON 传入。

---

### 2.3 根据股票代码查询
```
GET /api/stock/basic/symbol/{symbol}
```
**Path 参数**
| 参数 | 类型 | 说明 |
|------|------|------|
| symbol | string | 股票代码，如 `000001` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": { "id": 1, "symbol": "000001", "name": "平安银行", ... }
}
```

---

### 2.4 批量查询股票
```
POST /api/stock/basic/batch
```
**Body 参数**
```json
["000001", "000002", "600000"]
```

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "id": 1, "symbol": "000001", "name": "平安银行", ... },
    { "id": 2, "symbol": "000002", "name": "万科A", ... }
  ]
}
```

---

### 2.5 根据行业查询
```
GET /api/stock/basic/industry/{industry}
```

---

### 2.6 新增股票
```
POST /api/stock/basic
```
**Body 参数**
```json
{
  "symbol": "000001",
  "name": "平安银行",
  "area": "深圳",
  "industry": "银行",
  "market": "主板",
  "list_date": "1991-04-03"
}
```

---

### 2.7 更新股票
```
PUT /api/stock/basic
```
**Body 参数**
```json
{
  "id": 1,
  "name": "新名称"
}
```

---

### 2.8 根据 ID 查询
```
GET /api/stock/basic/{id}
```

---

### 2.9 删除股票
```
DELETE /api/stock/basic/{id}
```

---

## 三、股票日线数据（`/stock/daily`）

### 日线数据字段说明（新版）

前端拿到/传入的日线对象统一为以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 自增ID |
| symbol | string | **股票代码**（原 `code` 已改为 `symbol`） |
| trade_date | string | 交易日期，格式 `YYYY-MM-DD` |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | float | 成交量 |
| amount | float | 成交额 |
| amplitude | float | 振幅 |
| pct_chg | float | 涨跌幅 |
| price_change | float | 涨跌额 |
| turnover | float | 换手率 |

---

### 3.1 分页查询日线数据
```
POST /api/stock/daily/page
```
**Body 参数**
```json
{
  "page_num": 1,
  "page_size": 20,
  "symbol": "000001",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```
> **注**：`symbol`、`start_date`、`end_date` 均为可选。

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "id": 1,
        "symbol": "000001",
        "trade_date": "2024-01-02",
        "open": 10.5,
        "high": 10.8,
        "low": 10.2,
        "close": 10.6,
        "volume": 1250000,
        "amount": 13250000,
        "amplitude": 5.71,
        "pct_chg": 0.95,
        "price_change": 0.10,
        "turnover": 0.65
      }
    ],
    "total": 242,
    "page_num": 1,
    "page_size": 20
  }
}
```

---

### 3.2 根据股票代码查询全部日线
```
GET /api/stock/daily/symbol/{symbol}
```
**Path 参数**
| 参数 | 说明 |
|------|------|
| symbol | 股票代码，如 `000001` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "id": 1, "symbol": "000001", "trade_date": "2024-01-02", ... },
    { "id": 2, "symbol": "000001", "trade_date": "2024-01-03", ... }
  ]
}
```

---

### 3.3 批量查询日线数据
```
POST /api/stock/daily/symbols
```
**Body 参数**
```json
["000001", "000002", "600000"]
```

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "id": 1, "symbol": "000001", "trade_date": "2024-01-02", ... },
    { "id": 5, "symbol": "000002", "trade_date": "2024-01-02", ... }
  ]
}
```

---

### 3.4 根据日期范围查询
```
GET /api/stock/daily/symbol/{symbol}/range?start_date=2024-01-01&end_date=2024-03-01
```
**Query 参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 是 | 开始日期 `YYYY-MM-DD` |
| end_date | string | 是 | 结束日期 `YYYY-MM-DD` |

---

### 3.5 根据交易日期查询
```
GET /api/stock/daily/date/{trade_date}
```
**Path 参数**
| 参数 | 说明 |
|------|------|
| trade_date | 交易日期，**支持 `2026-04-12` 或 `20260412`** |

> 后端会自动把带 `-` 的日期转成 `20260412` 去查询。

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "id": 1, "symbol": "000001", "trade_date": "2026-04-12", ... },
    { "id": 2, "symbol": "000002", "trade_date": "2026-04-12", ... }
  ]
}
```

---

### 3.6 根据交易日期获取全部 A 股数据（关联基础表）
```
GET /api/stock/daily/date/{trade_date}/all
```
**Path 参数**
| 参数 | 说明 |
|------|------|
| trade_date | 支持 `2026-04-12` 或 `20260412` |

**Query 参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| exclude_st | bool | 否 | 是否过滤ST股票，默认 `false` |
| exclude_cyb | bool | 否 | 是否过滤创业板，默认 `false` |
| exclude_bse | bool | 否 | 是否过滤北交所，默认 `false` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trade_date": "2026-04-12",
    "total": 5123,
    "list": [
      {
        "id": 1,
        "symbol": "000001",
        "trade_date": "2026-04-12",
        "stock_name": "平安银行",
        "industry": "银行",
        "market": "主板",
        "area": "深圳",
        "open": 10.5,
        "high": 10.8,
        "low": 10.2,
        "close": 10.6,
        "volume": 1250000,
        "amount": 13250000,
        "amplitude": 5.71,
        "pct_chg": 0.95,
        "price_change": 0.10,
        "turnover": 0.65
      }
    ]
  }
}
```
> 此接口会自动 `LEFT JOIN` `stock_basic` 表，补充 `stock_name`、`industry`、`market`、`area`。

---

### 3.7 获取交易日列表
```
GET /api/stock/daily/trade-dates
```
**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": ["2026-04-14", "2026-04-13", "2026-04-11", "2026-04-10"]
}
```

---

### 3.8 根据日期和涨幅筛选股票
```
GET /api/stock/daily/top-pct-chg?trade_date=2026-04-14&min_pct_chg=5.0
```
**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trade_date | string | 是 | 交易日期，格式 `2026-04-14` 或 `20260412` |
| min_pct_chg | float | 否 | 最小涨幅百分比，默认 `5.0` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trade_date": "2026-04-14",
    "min_pct_chg": 5.0,
    "total_stocks": 5499,
    "matched_count": 285,
    "matched_percent": 5.18,
    "list": [
      {
        "id": 7036575,
        "trade_date": "2026-04-14",
        "symbol": "601588",
        "stock_name": "北辰实业",
        "industry": "房地产开发",
        "market": "主板",
        "area": "北京",
        "open": 1.91,
        "high": 2.07,
        "low": 1.88,
        "close": 2.07,
        "volume": 157827171.0,
        "amount": 318952040.97,
        "amplitude": 10.11,
        "pct_chg": 10.11,
        "price_change": 0.19,
        "turnover": 5.93
      }
    ]
  }
}
```

---

### 3.9 倍量突破选股（数据库层计算）
```
POST /api/stock/daily/breakout-picker
```

**请求参数**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trade_date | string | 是 | 交易日期，格式 `YYYY-MM-DD` 或 `YYYYMMDD` |
| min_pct_chg | number | 否 | 最小涨幅，默认 `3.0` |
| max_pct_chg | number | 否 | 最大涨幅，默认 `7.0` |
| min_turnover | number | 否 | 最低换手率，默认 `2.0` |
| min_amount | number | 否 | 最低成交额，默认 `50000000` |
| exclude_st | boolean | 否 | 排除 ST，默认 `true` |
| exclude_cyb | boolean | 否 | 排除创业板，默认 `true` |
| exclude_kcb | boolean | 否 | 排除科创板，默认 `true` |
| exclude_bse | boolean | 否 | 排除北交所，默认 `true` |
| page_num | int | 否 | 页码，默认 `1` |
| page_size | int | 否 | 每页条数，默认 `100`，最大 `100` |

**计算逻辑**
- 单日过滤：`close > open` 且 `pct_chg` 在范围内 且 `turnover >= min_turnover` 且 `amount >= min_amount`
- 历史指标（不含当日）：
  - `ma250` = 前 250 条 `close` 的均值
  - `high_60` = 前 60 条 `high` 的最大值
  - `avg_volume_20` = 前 20 条 `volume` 的均值
- 信号判定（三个同时为 `true` 才返回）：
  - `above_ma250` = `close > ma250`
  - `is_breakout` = `close >= high_60`
  - `is_double_volume` = `volume >= avg_volume_20 * 2`
- 后续跟踪（基于信号日之后的数据）：
  - `current_return` = 截至最新收盘价的累计涨幅（%）
  - `max_return` = 截至目前最高价的累计涨幅（%）
  - `latest_date` = 最新数据日期（信号日之后）

> 所有计算在数据库层通过 SQL 窗口函数完成，前端只需传入参数即可拿到最终结果。

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trade_date": "2024-04-22",
    "total": 12,
    "page_num": 1,
    "page_size": 100,
    "list": [
      {
        "symbol": "000001",
        "name": "平安银行",
        "trade_date": "2024-04-22",
        "open": 10.20,
        "close": 10.80,
        "high": 10.90,
        "low": 10.15,
        "volume": 1250000,
        "amount": 135000000,
        "turnover": 3.5,
        "pct_chg": 5.88,
        "ma250": 10.45,
        "high_60": 10.85,
        "avg_volume_20": 520000,
        "above_ma250": true,
        "is_breakout": true,
        "is_double_volume": true,
        "current_return": 8.52,
        "max_return": 12.30,
        "latest_date": "2024-04-25",
        "signals": "站上年线 | 突破平台 | 倍量"
      }
    ]
  }
}
```

---

### 3.9a 趋势选股
```
POST /api/stock/daily/trend-picker
```

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trade_date | string | 是 | 交易日期，格式 `YYYY-MM-DD` 或 `YYYYMMDD` |
| min_pct_chg | number | 否 | 最小涨幅，默认 `2.0` |
| max_pct_chg | number | 否 | 最大涨幅，默认 `8.0` |
| min_turnover | number | 否 | 最低换手率，默认 `2.0` |
| min_amount | number | 否 | 最低成交额均值(10日)，默认 `200000000` |
| ma_alignment | boolean | 否 | 均线多头排列，默认 `true` |
| macd_golden_cross | boolean | 否 | MACD金叉，默认 `false` |
| rsi_min | number | 否 | RSI最小值，默认 `40` |
| rsi_max | number | 否 | RSI最大值，默认 `80` |
| volume_ratio | number | 否 | 成交量/20日均量，默认 `1.5` |
| exclude_st | boolean | 否 | 排除ST，默认 `true` |
| exclude_cyb | boolean | 否 | 排除创业板，默认 `true` |
| exclude_kcb | boolean | 否 | 排除科创板，默认 `true` |
| exclude_bse | boolean | 否 | 排除北交所，默认 `true` |
| sort_field | string | 否 | 排序字段，可选 `pct_chg`/`volume_ratio`/`rsi_14`/`ma5`/`ma10`/`ma20`/`ma60`/`turnover`/`amount`/`symbol`/`name`/`score`，默认 `pct_chg` |
| sort_order | string | 否 | 排序方向，`asc`/`desc`，默认 `desc` |
| page_num | int | 否 | 页码，默认 `1` |
| page_size | int | 否 | 每页条数，默认 `100`，最大 `100` |

**计算逻辑**
- 预筛选（最近10日）：沪深主板非ST、涨幅绝对值均值 > 2%、换手率均值 > 2%、成交额均值 > `min_amount`
- 趋势信号：
  - 均线多头排列（MA5 > MA10 > MA20 > MA60）
  - MACD金叉：当日 DIF > 0 且前一日 DIF <= 0（DIF 上穿零轴近似）
  - RSI 在健康区间（默认 40~80）
  - 成交量放大（>= 1.5 倍20日均量）
- 评分规则（0~100）：多头排列30分、MACD金叉25分、RSI健康20分、放量15分、站上年线10分

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trade_date": "2024-04-22",
    "total": 28,
    "page_num": 1,
    "page_size": 100,
    "list": [
      {
        "symbol": "000001",
        "name": "平安银行",
        "industry": "银行",
        "trade_date": "2024-04-22",
        "open": 10.20,
        "close": 10.80,
        "high": 10.90,
        "low": 10.15,
        "volume": 1250000,
        "amount": 135000000,
        "turnover": 3.5,
        "pct_chg": 5.88,
        "ma5": 10.50,
        "ma10": 10.30,
        "ma20": 10.10,
        "ma60": 9.80,
        "macd_dif": 0.15,
        "macd_dea": 0.12,
        "rsi_14": 58.5,
        "volume_ratio": 2.1,
        "trend_score": 85,
        "signals": "多头排列 | MACD金叉 | RSI健康 | 明显放量 | 站上均线"
      }
    ]
  }
}
```

---

### 3.9b 震荡选股
```
POST /api/stock/daily/range-picker
```

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trade_date | string | 是 | 交易日期，格式 `YYYY-MM-DD` 或 `YYYYMMDD` |
| max_pct_chg_20d | number | 否 | 近20日涨幅绝对值均值上限，默认 `10.0` |
| min_amplitude_20d | number | 否 | 近20日平均振幅最小值，默认 `3.0` |
| bb_width_max | number | 否 | 布林带宽度最大值，默认 `0.08` |
| rsi_min | number | 否 | RSI最小值，默认 `35` |
| rsi_max | number | 否 | RSI最大值，默认 `65` |
| volume_shrink | boolean | 否 | 近期缩量，默认 `true` |
| near_ma20 | boolean | 否 | 收盘价在MA20附近，默认 `true` |
| min_amount | number | 否 | 最低成交额均值(10日)，默认 `200000000` |
| exclude_st | boolean | 否 | 排除ST，默认 `true` |
| exclude_cyb | boolean | 否 | 排除创业板，默认 `true` |
| exclude_kcb | boolean | 否 | 排除科创板，默认 `true` |
| exclude_bse | boolean | 否 | 排除北交所，默认 `true` |
| sort_field | string | 否 | 排序字段，可选 `bb_width`/`rsi_14`/`ma5`/`ma10`/`ma20`/`pct_chg`/`turnover`/`amount`/`symbol`/`name`/`score`，默认 `bb_width` |
| sort_order | string | 否 | 排序方向，`asc`/`desc`，默认 `asc` |
| page_num | int | 否 | 页码，默认 `1` |
| page_size | int | 否 | 每页条数，默认 `100`，最大 `100` |

**计算逻辑**
- 预筛选（最近10日）：沪深主板非ST、涨幅绝对值均值 > 2%、换手率均值 > 2%、成交额均值 > `min_amount`
- 震荡信号：
  - 布林带收口（宽度 <= `bb_width_max`）
  - RSI 中性区间（默认 35~65）
  - 均线缠绕（MA5/MA10/MA20 接近，可选）
  - 近期缩量（<= 0.9 倍20日均量，可选）
  - 收盘价在 MA20 附近（偏差 <= 3%，可选）
- 评分规则（0~100）：布林带收口30分、RSI中性25分、均线缠绕20分、缩量15分、振幅适中10分

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trade_date": "2024-04-22",
    "total": 15,
    "page_num": 1,
    "page_size": 100,
    "list": [
      {
        "symbol": "000001",
        "name": "平安银行",
        "industry": "银行",
        "trade_date": "2024-04-22",
        "open": 10.20,
        "close": 10.35,
        "high": 10.40,
        "low": 10.15,
        "volume": 450000,
        "amount": 46575000,
        "turnover": 1.2,
        "pct_chg": 0.49,
        "bb_lower": 10.10,
        "bb_middle": 10.35,
        "bb_upper": 10.60,
        "bb_width": 0.048,
        "ma5": 10.33,
        "ma10": 10.35,
        "ma20": 10.36,
        "rsi_14": 52.0,
        "avg_amplitude_20": 3.5,
        "volume_ratio": 0.75,
        "range_score": 78,
        "signals": "明显收口 | RSI中性 | 均线缠绕 | 明显缩量 | 振幅适中"
      }
    ]
  }
}
```

---

### 3.10 统计日期范围内每天涨幅超过阈值的股票占比（柱状图）
```
GET /api/stock/daily/pct-chg-distribution?start_date=2026-04-01&end_date=2026-04-14&threshold=2.0
```

**Query 参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 是 | 开始日期，格式 `2026-04-01` 或 `20260401` |
| end_date | string | 是 | 结束日期，格式 `2026-04-14` 或 `20260414` |
| threshold | float | 否 | 涨幅阈值百分比，默认 `2.0` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "start_date": "2026-04-01",
    "end_date": "2026-04-14",
    "threshold": 2.0,
    "list": [
      {
        "trade_date": "2026-04-01",
        "total_stocks": 5499,
        "matched_count": 1250,
        "matched_percent": 22.73
      },
      {
        "trade_date": "2026-04-02",
        "total_stocks": 5499,
        "matched_count": 890,
        "matched_percent": 16.18
      }
    ]
  }
}
```

> 此接口仅统计沪深主板且非ST股票。`matched_percent` 可直接用于 ECharts 等柱状图展示。

---

### 3.11 获取连续缩量的股票列表
```
GET /api/stock/daily/shrinking-volume
```

**Query 参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| min_days | int | 否 | 最小连续缩量天数，默认 `1` |
| max_days | int | 否 | 最大连续缩量天数，默认不限制 |
| lookback | int | 否 | 用于计算的历史交易日数量，默认 `30`，范围 `10~120` |
| page_num | int | 否 | 页码，默认 `1` |
| page_size | int | 否 | 每页条数，默认 `20`，最大 `500` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "min_days": 1,
    "max_days": null,
    "total": 128,
    "page_num": 1,
    "page_size": 20,
    "list": [
      {
        "symbol": "000001",
        "latest_trade_date": "2026-04-18",
        "latest_volume": 1000000,
        "latest_close": 10.5,
        "consecutive_days": 3
      }
    ]
  }
}
```

> `consecutive_days` 表示从最近一个交易日往前推，成交量连续递减的天数（最近一天比前一天少算 1 天）。结果按 `consecutive_days` 降序排列。返回的 `list` 中每个元素为完整日线数据字段，额外附加 `consecutive_days`。

---

### 3.12 新增/更新日线数据（Upsert）
```
POST /api/stock/daily
```
**Body 参数**
```json
{
  "trade_date": "2024-01-02",
  "symbol": "000001",
  "open": 10.5,
  "high": 10.8,
  "low": 10.2,
  "close": 10.6,
  "volume": 1250000,
  "amount": 13250000,
  "amplitude": 5.71,
  "pct_chg": 0.95,
  "price_change": 0.10,
  "turnover": 0.65
}
```
> 若 `trade_date` + `symbol` 已存在，则更新；不存在则插入。

---

### 3.13 批量新增日线数据
```
POST /api/stock/daily/batch
```
**Body 参数**
```json
[
  { "trade_date": "2024-01-02", "symbol": "000001", "open": 10.5, ... },
  { "trade_date": "2024-01-02", "symbol": "000002", "open": 15.2, ... }
]
```

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": "成功创建 2 条数据"
}
```

---

### 3.14 更新日线数据
```
PUT /api/stock/daily
```
**Body 参数**
```json
{
  "id": 1,
  "close": 11.0,
  "volume": 1500000
}
```

---

### 3.15 根据 ID 查询
```
GET /api/stock/daily/{id}
```

---

### 3.16 删除日线数据
```
DELETE /api/stock/daily/{id}
```

---

## 四、数据同步（`/sync`）

> 这些接口用于**从 Baostock 拉取数据并写入数据库**，通常由后台/管理员调用。

### 4.1 同步所有股票日线数据
```
POST /api/sync/daily
```
**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": "同步完成，成功: 125000, 失败: 23"
}
```

---

### 4.2 同步单只股票日线数据
```
POST /api/sync/daily/{symbol}
```
**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": "同步完成: 000001, 更新 512 条"
}
```

---

### 4.3 按日期同步全部 A 股日线数据（后台异步）
```
POST /api/sync/daily/date/{trade_date}
```
**Path 参数**
| 参数 | 说明 |
|------|------|
| trade_date | 如 `2026-04-12` 或 `20260412` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "b444e856-0630-4f1b-96d6-ae72b993cacc",
    "trade_date": "2026-04-12",
    "status": "running",
    "hint": "同步任务已提交后台执行，约需 5-10 秒，请稍后刷新页面查看"
  }
}
```

> 此接口为**后台异步执行**，前端可立即收到响应，无需等待。随后可通过 **4.5 查询同步任务状态** 轮询进度。

---

### 4.4 对比数据库与基础表数据
```
GET /api/sync/compare?trade_date=2026-04-12
```
**Query 参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trade_date | string | 是 | `YYYY-MM-DD` |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trade_date": "2026-04-12",
    "db_count": 5280,
    "basic_count": 5342,
    "only_in_basic": ["000003", "000004"],
    "only_in_db": [],
    "differences": [],
    "summary": "对比日期: 2026-04-12 | 数据库: 5280条 | 基础表: 5342条 | 缺失: 2条"
  }
}
```

---

### 4.5 查询同步任务状态（轮询）
```
GET /api/sync/task/{task_id}
```
**Path 参数**
| 参数 | 说明 |
|------|------|
| task_id | 4.3 接口返回的 task_id |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "b444e856-0630-4f1b-96d6-ae72b993cacc",
    "trade_date": "2026-04-12",
    "status": "running",
    "started_at": "2026-04-19T10:30:00",
    "finished_at": null,
    "progress": {
      "current": 1500,
      "total": 5499,
      "percent": 27.3
    },
    "result": null,
    "error": null
  }
}
```
> `status` 取值：`running` / `success` / `failed`。前端可定时轮询此接口获取进度。

---

### 4.6 按日期同步全部 A 股日线数据（SSE 实时推送）
```
GET /api/sync/daily/date/{trade_date}/stream
```
**Path 参数**
| 参数 | 说明 |
|------|------|
| trade_date | 如 `2026-04-12` 或 `20260412` |

**说明**
- 此接口使用 **Server-Sent Events (SSE)**，建立长连接后服务端会实时推送同步进度
- 比轮询更实时，推荐用于前端展示进度条
- 同步完成后服务端会自动关闭连接

**前端使用示例**
```javascript
const source = new EventSource('/api/sync/daily/date/2025-04-18/stream')

source.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log(data)
  // {
  //   "current": 1500,      // 当前处理到第几只
  //   "total": 5499,        // 总共多少只
  //   "status": "running",  // running / completed / failed
  //   "symbol": "002456",   // 当前股票代码
  //   "success": 1200,      // 成功数
  //   "skipped": 250,       // 跳过数
  //   "failed": 50          // 失败数
  // }
}

source.addEventListener('error', () => {
  source.close()
})
```

**SSE 数据流示例**
```
data: {"current": 10, "total": 5499, "status": "running", "symbol": "600001", "success": 8, "skipped": 1, "failed": 1}

data: {"current": 5499, "total": 5499, "status": "completed", "result": {"trade_date": "2025-04-18", "upserted": 5000, "skipped": 300, "failed": 199}}
```

---

## 五、独立脚本

### 5.1 同步全部 A 股历史日线数据

**文件**：`scripts/sync_history_data.py`

**用途**：一次性同步 **2020-01-01 至今** 全部沪深主板且非 ST 股票的日线数据到数据库。

**执行方式**：
```bash
.venv/Scripts/python scripts/sync_history_data.py
```

**行为说明**：
- 数据源：Baostock
- 股票范围：沪深主板且非 ST（约 3000+ 只）
- 写入策略：全量覆盖（`ON DUPLICATE KEY UPDATE`）
- 单只股票批量 upsert，大幅提升写入效率
- 自动请求频率控制，避免触发接口限制
- 预计耗时：1-4 小时（视网络情况而定）

**输出示例**：
```
============================================================
开始同步 A 股历史日线数据
日期范围: 20200101 ~ 20260422
============================================================
共 3062 只股票待同步（沪深主板且非 ST）

[    1/ 3062] 000001 | 写入  512 条 | 耗时 1.23s | 预计剩余 2.5小时
[    2/ 3062] 000002 | 写入  512 条 | 耗时 1.15s | 预计剩余 2.4小时
...
============================================================
同步完成
总耗时: 2.3小时
成功记录: 1567234
跳过/无数据: 123
异常: 0
============================================================
```

---

## 六、前端重点注意

1. **`code` 已全面替换为 `symbol`**：所有日线接口（包括路由、请求体、响应体）都不再使用 `code`，请统一改为 `symbol`。
2. **日期格式**：大部分接口支持带 `-` 的标准日期（`2026-04-12`），后端会自动处理。只有部分数据库原生查询接口（如 `/date/{trade_date}`）会做 `replace("-", "")` 转换。
3. **新增字段**：日线数据现在包含 `amplitude`（振幅）、`price_change`（涨跌额）、`turnover`（换手率），可用于更丰富的 K 线/列表展示。
4. **删除字段**：`preclose`、`adjustflag`、`tradestatus`、`pe_ttm`、`pb_mrq`、`ps_ttm`、`pcf_ncf_ttm`、`is_st` 已移除，前端请勿再引用。
5. **选股策略分页强制 100 条/页**：`breakout-picker`、`trend-picker`、`range-picker` 等选股类接口因计算量大、数据量多，前端调用时必须分页，且 `page_size` 固定为 `100`，不接受其他值。后端会对超过 100 的请求截断或报错。
