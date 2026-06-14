# Seele 数据接口文档（对外版）

## 基础信息

| 项 | 内容 |
|---|---|
| 基础地址 | `https://<YOUR_DOMAIN>/api` |
| 认证方式 | JWT Bearer Token |
| 请求头 | `Authorization: Bearer <token>` |
| Token 有效期 | 7 天 |

---

## 认证接口

### 管理员登录获取 Token

| 项 | 说明 |
|---|---|
| URL | `POST /api/auth/login` |
| 说明 | **无需认证**，用于获取后续请求的 JWT |

#### 请求参数 (Body)

```json
{
  "password": "管理员密码"
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

---

## 请求示例

### cURL

```bash
# 1. 登录获取 token
curl -X POST https://<YOUR_DOMAIN>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"管理员密码"}'

# 2. 调用备选池接口（将 <token> 替换为实际 token）
curl -X POST https://<YOUR_DOMAIN>/api/stock/daily/mainwave-picker \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"page_num":1,"page_size":10}'
```

---

## 1. 获取备选池接口

| 项 | 说明 |
|---|---|
| 接口名称 | 获取备选池接口 |
| URL | `POST /api/stock/daily/mainwave-picker` |
| 说明 | 返回主升浪备选股票池。结果包含股票基础信息、日线行情、均线指标、财务指标、评分和分组信息。不满足选股条件但当前持仓的股票也会被补充返回，并在 `is_holding` 字段标记。 |

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

---

## 2. 选股条件

### 硬性门槛（不可关闭）

| 条件 | 说明 |
|---|---|
| 市场 | 主板 |
| ST 过滤 | 名称不含 `ST` |
| 创业板过滤 | 代码不以 `300`、`301` 开头 |
| 科创板过滤 | 代码不以 `688`、`689` 开头 |
| 财务过滤 | 若存在财务数据，要求净利润 > 0 且总营收 > 0 |
| 指标过滤 | MA5 非空且大于 0 |

### 可选过滤参数

| 参数 | 说明 |
|---|---|
| close_max | 收盘价上限 |
| avg_turnover_min | 10 日平均换手率下限（%） |
| avg_amount_min | 10 日平均成交额下限（元） |
| ma_bull | 均线多头排列：收盘价 > MA5 > MA10 |
| float_market_cap_min | 流通市值下限（亿元），按当日数据实时估算 |
| symbol / name / industry / market / area | 代码、名称、行业、市场、地区模糊匹配 |

### 流通市值估算

```
流通市值(亿元) ≈ (成交量 × 100 ÷ 换手率%) × 收盘价 ÷ 1亿
```

### 持仓补充

不满足选股条件但当前持仓的股票会被强制补充到结果中，`is_holding` 字段标记为 `true`。

### 前端实际调用参数

#### 默认筛选条件

| 前端字段 | 默认值 | 说明 |
|---|---|---|
| tradeDate | 自动填充最近交易日 | 交易日 |
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
| symbol | symbol | 去除前后空格，非空才传 |
| name | name | 去除前后空格，非空才传 |
| tradeDate | trade_date | 非空才传 |
| floatMarketCapMin | float_market_cap_min | 非 null 才传 |
| closeMax | close_max | 非 null 才传 |
| avgTurnoverMin | avg_turnover_min | 非 null 才传 |
| avgAmountMin | avg_amount_min | **乘以 100,000,000（元）** |
| maBull | ma_bull | 为 true 时才传 |

#### 各页面调用差异

| 页面 | 分页 | 默认排序 | 特殊说明 |
|---|---|---|---|
| 选股页 | 分页（10/20/50/100） | `score` / `desc` | 点击表头切换排序 |
| 评分页 | 分页（10/20/50/100） | `score` / `desc` | 趋势/强势/动量分字段会做后端字段映射 |
| 分组页 | 不分页 | `score` / `desc` | 固定 `page_num: 1, page_size: 9999`，一次性拉取全部 |

---

## 3. 评分说明

| 字段 | 类型 | 说明 |
|---|---|---|
| total | float | 总分 = 趋势分 + 强势分 + 动量分 |
| trend_score | float | 趋势分 |
| strength_score | float | 强势分 |
| momentum_score | float | 动量分 |
| hard_pass | bool | 是否 `total >= 60` |

### 趋势分（trend_score）

遍历启动日到最近交易日的每个交易日，根据收盘价与均线相对位置计分：

| 条件 | 得分 |
|---|---|
| 收盘价 ≥ MA5 | +3 |
| 收盘价 < MA5 | -1 |
| 收盘价 ≥ MA10 | +2 |
| 收盘价 < MA10 | -2 |
| 收盘价 ≥ MA20 | +1 |
| 收盘价 < MA20 | -3 |

### 强势分（strength_score）

遍历启动日到最近交易日的每个交易日，根据当日涨跌幅计分：

| 涨跌幅 | 得分 |
|---|---|
| > 9% | +3 |
| 5% ~ 9% | +2 |
| 0% ~ 5% | +1 |
| -5% ~ 0% | -1 |
| -9% ~ -5% | -2 |
| < -9% | -3 |

### 动量分（momentum_score）

遍历启动日到最近交易日的每个交易日，结合涨跌幅与换手率相对五日平均换手率计分：

| 条件 | 得分 |
|---|---|
| 涨幅 > 5% 且 换手率 > 五日平均换手率 | `+5 × (turnover / turnover_ma5)` |
| 跌幅 < -5% 且 换手率 > 五日平均换手率 | `-5 × (turnover / turnover_ma5)` |

### 通过标准

- `hard_pass = total >= 60`

---

## 4. 分组说明

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

1. 根据分层结果确定窗口：20 日组用 20 日窗口、10 日组用 10 日窗口、5 日组 / OFF 用 5 日窗口。
2. 从窗口最远交易日往前遍历，找到第一个触发以下任一条件的交易日作为启动日：
   - 单日跌幅 < -2%
   - 连续两天涨幅 < 1%
3. 若未触发上述条件，则取窗口内最早有数据的交易日作为启动日。

### 启动日至今涨幅

```
launch_pct_chg = (current_close - launch_close) / launch_close × 100%
```

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
- 分页接口 `data` 包含 `list`、`total`、`page_num`、`page_size`，选股结果额外包含 `trade_date`。

---

## 5. 板块-个股关联保存接口

| 项 | 说明 |
|---|---|
| 接口名称 | 保存板块与个股的关联关系 |
| URL | `POST /api/board/constituents/save` |
| 说明 | 新增或更新板块与个股的映射关系。`board_code` + `constituent_symbol` 为唯一键，已存在则更新 `name` 和 `update_date`，不存在则插入。接口会自动校验板块和个股的有效性。 |

### 请求参数 (Body)

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| board_code | string | **是** | 板块/ETF 代码，必须是 `board_info` 表中已存在的 `code` |
| constituent_symbol | string | **是** | 股票代码，必须是 `stock_basic` 表中已存在的 `symbol` |
| name | string | 否 | 成分股名称 |
| update_date | string | 否 | 更新日期 `YYYY-MM-DD` |

### 有效板块说明

`board_code` 必须是 `board_info` 表中已有的记录。该表的有效板块类型如下：

| category 值 | 含义 | 示例 |
|---|---|---|
| `industry` | 行业板块 | `BK0428`（银行）、`BK0437`（证券） |
| `concept` | 概念板块 | `BK0545`（人工智能）、`BK0550`（芯片） |
| `etf` | ETF 基金 | `510050`（50ETF）、`510300`（300ETF） |

> 完整列表可通过 `POST /api/board/list` 查询。

### 请求示例

```bash
curl -X POST https://<YOUR_DOMAIN>/api/board/constituents/save \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "board_code": "BK0428",
    "constituent_symbol": "000001",
    "name": "平安银行",
    "update_date": "2026-06-12"
  }'
```

### 响应示例（成功-新建）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "saved": true,
    "is_created": true,
    "id": 12345,
    "board_code": "BK0428",
    "constituent_symbol": "000001",
    "name": "平安银行",
    "update_date": "2026-06-12"
  }
}
```

### 响应示例（成功-更新）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "saved": true,
    "is_created": false,
    "id": 12345,
    "board_code": "BK0428",
    "constituent_symbol": "000001",
    "name": "平安银行",
    "update_date": "2026-06-12"
  }
}
```

### 响应示例（失败-板块不存在）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "saved": false,
    "reason": "板块代码 BK9999 不存在"
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| saved | bool | 是否保存成功 |
| is_created | bool | `true` 表示本次为新建，`false` 表示更新 |
| id | int | 关联记录 ID |
| board_code | string | 板块代码 |
| constituent_symbol | string | 股票代码 |
| name | string | 成分股名称 |
| update_date | string | 更新日期 `YYYY-MM-DD` |
| reason | string | 保存失败原因（仅 `saved: false` 时返回） |

---

## 6. 公司概况接口（东方财富 F10）

| 项 | 说明 |
|---|---|
| 数据来源 | 东方财富 `http://f10.eastmoney.com/CompanySurvey/CompanySurveyAjax?code={Market}{symbol}` |
| 数据表 | `stock_company_profile` |

### 6.1 查询公司概况

| 项 | 说明 |
|---|---|
| URL | `GET /api/stock/basic/{symbol}/survey` |
| 说明 | 返回已同步的公司概况数据。若未同步，返回 `data: null` 并提示调用同步接口。 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "000001",
    "company_full_name": "平安银行股份有限公司",
    "english_name": "Ping An Bank Co., Ltd.",
    "chairman": "谢永林",
    "general_manager": "冀光恒",
    "secretary": "周强",
    "legal_representative": "谢永林",
    "phone": "0755-82080387",
    "email": "PAB_db@pingan.com.cn",
    "fax": "0755-82080386",
    "website": "bank.pingan.com",
    "office_address": "中国广东省深圳市深南东路5047号",
    "reg_address": "中华人民共和国广东省深圳市罗湖区深南东路5047号",
    "postcode": "518001,518033",
    "reg_capital": "194.1亿",
    "employees": 41698,
    "founded_date": "1987-12-22",
    "company_profile": "平安银行股份有限公司是一家总部设在深圳的全国性股份制商业银行...",
    "business_scope": "吸收公众存款；发放短期、中期和长期贷款...",
    "industry_detail": "金融业-货币金融服务",
    "exchange": "深圳证券交易所",
    "updated_at": "2026-06-12 10:30:00"
  }
}
```

### 6.2 同步公司概况

| 项 | 说明 |
|---|---|
| URL | `POST /api/stock/basic/{symbol}/sync-survey` |
| 说明 | 实时调用东方财富 F10 接口抓取数据，保存或更新到 `stock_company_profile` 表。 |

#### 请求示例

```bash
curl -X POST https://<YOUR_DOMAIN>/api/stock/basic/000001/sync-survey \
  -H "Authorization: Bearer <token>"
```

#### 响应示例（成功）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "synced": true,
    "symbol": "000001",
    "company_full_name": "平安银行股份有限公司",
    "updated_at": "2026-06-12 10:30:00"
  }
}
```

#### 响应示例（失败）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "synced": false,
    "reason": "从东方财富抓取 000001 数据失败"
  }
}
```

### 6.3 字段映射说明

| 响应字段 | 东方财富原始字段 | 说明 |
|---|---|---|
| `company_full_name` | `jbzl.gsmc` | 公司全称 |
| `english_name` | `jbzl.ywmc` | 英文名称 |
| `chairman` | `jbzl.dsz` | 董事长 |
| `general_manager` | `jbzl.zjl` | 总经理 |
| `secretary` | `jbzl.dm` | 董事会秘书 |
| `legal_representative` | `jbzl.frdb` | 法人代表 |
| `phone` | `jbzl.lxdh` | 联系电话 |
| `email` | `jbzl.dzxx` | 电子邮箱 |
| `fax` | `jbzl.cz` | 传真 |
| `website` | `jbzl.gswz` | 公司网址 |
| `office_address` | `jbzl.bgdz` | 办公地址 |
| `reg_address` | `jbzl.zcdz` | 注册地址 |
| `postcode` | `jbzl.yzbm` | 邮编 |
| `reg_capital` | `jbzl.zczb` | 注册资本 |
| `employees` | `jbzl.gyrs` | 员工人数 |
| `founded_date` | `fxxg.clrq` | 成立日期 |
| `company_profile` | `jbzl.gsjj` | 公司简介（已去除多余空白） |
| `business_scope` | `jbzl.jyfw` | 经营范围（已去除多余空白） |
| `industry_detail` | `jbzl.sszjhhy` | 所属证监会行业 |
| `exchange` | `jbzl.ssjys` | 所属交易所 |

### 6.4 数据库建表语句

项目未使用 Alembic 迁移，首次部署需手动执行：

```sql
CREATE TABLE stock_company_profile (
    symbol VARCHAR(20) PRIMARY KEY COMMENT '股票代码',
    company_full_name VARCHAR(200) COMMENT '公司全称',
    english_name VARCHAR(200) COMMENT '英文名称',
    chairman VARCHAR(100) COMMENT '董事长',
    general_manager VARCHAR(100) COMMENT '总经理',
    secretary VARCHAR(100) COMMENT '董事会秘书',
    legal_representative VARCHAR(100) COMMENT '法人代表',
    phone VARCHAR(50) COMMENT '联系电话',
    email VARCHAR(100) COMMENT '电子邮箱',
    fax VARCHAR(50) COMMENT '传真',
    website VARCHAR(200) COMMENT '公司网址',
    office_address VARCHAR(500) COMMENT '办公地址',
    reg_address VARCHAR(500) COMMENT '注册地址',
    postcode VARCHAR(20) COMMENT '邮政编码',
    reg_capital VARCHAR(50) COMMENT '注册资本',
    employees INT COMMENT '员工人数',
    founded_date VARCHAR(20) COMMENT '成立日期',
    company_profile TEXT COMMENT '公司简介',
    business_scope TEXT COMMENT '经营范围',
    industry_detail VARCHAR(100) COMMENT '所属证监会行业',
    exchange VARCHAR(50) COMMENT '所属交易所',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 7. 细分行业同步接口

| 项 | 说明 |
|---|---|
| 数据来源 | 东方财富 F10 `CompanySurveyAjax` 接口中的 `sszjhhy`（证监会行业） |
| 存储位置 | `stock_basic.industry_detail` |
| 说明 | 为 `stock_basic` 中每只股票补充细分行业信息。已存在的 `industry` 字段保留不变。 |

### 7.1 单只同步

| 项 | 说明 |
|---|---|
| URL | `POST /api/stock/basic/{symbol}/sync-industry-detail` |
| 说明 | 实时抓取单只股票的细分行业并更新到 `stock_basic` |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "synced": true,
    "symbol": "000001",
    "industry_detail": "金融业-货币金融服务"
  }
}
```

### 7.2 批量同步（后台异步）

| 项 | 说明 |
|---|---|
| URL | `POST /api/sync/industry-detail` |
| 说明 | 遍历全部股票，并发抓取细分行业并批量更新。后台执行，返回 `task_id` 和 `log_id` 供轮询。 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "log_id": 12345,
    "status": "running",
    "hint": "细分行业同步任务已提交后台执行，约需 5-10 分钟，请稍后刷新页面查看"
  }
}
```

### 7.3 查询同步进度

复用现有任务查询接口：

```bash
GET /api/sync/task/{task_id}
```

### 7.4 数据库变更

`stock_basic` 表需新增字段：

```sql
ALTER TABLE stock_basic ADD COLUMN industry_detail VARCHAR(100) COMMENT '细分行业（证监会行业）';
```

### 7.5 字段映射

| 数据库字段 | 东方财富原始字段 | 示例 |
|---|---|---|
| `industry_detail` | `jbzl.sszjhhy` | `金融业-货币金融服务` |
| | `jbzl.sshy`（fallback） | `银行` |
