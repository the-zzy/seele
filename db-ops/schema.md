# 数据库表结构快照

**数据库:** `seele`  
**记录时间:** 2026-04-26  
**总表数:** 3

---

## stock_basic

股票基础信息表

| 字段名 | 类型 | 可空 | 说明 |
|--------|------|------|------|
| id | int | NOT NULL | 主键 |
| symbol | varchar(20) | NULL | 股票代码 |
| name | varchar(50) | NULL | 股票名称 |
| area | varchar(50) | NULL | 地区 |
| industry | varchar(50) | NULL | 行业 |
| cnspell | varchar(50) | NULL | 拼音简写 |
| market | varchar(20) | NULL | 市场 |
| list_date | varchar(20) | NULL | 上市日期 |
| act_name | varchar(100) | NULL | 实控人名称 |
| act_ent_type | varchar(50) | NULL | 实控人类型 |
| fullname | varchar(255) | NULL | 公司全称 |
| enname | varchar(255) | NULL | 英文名称 |
| exchange | varchar(10) | NULL | 交易所 |

**索引:**
- `PRIMARY` (id) UNIQUE

---

## stock_daily

股票日线数据表

| 字段名 | 类型 | 可空 | 说明 |
|--------|------|------|------|
| id | int | NOT NULL | 主键 |
| symbol | varchar(10) | NOT NULL | 股票代码 |
| trade_date | date | NOT NULL | 交易日期 |
| open | decimal(10,2) | NULL | 开盘价 |
| high | decimal(10,2) | NULL | 最高价 |
| low | decimal(10,2) | NULL | 最低价 |
| close | decimal(10,2) | NULL | 收盘价 |
| volume | bigint | NULL | 成交量（股） |
| amount | decimal(15,2) | NULL | 成交额 |
| amplitude | decimal(10,2) | NULL | 振幅 |
| pct_chg | decimal(10,2) | NULL | 涨跌幅(%) |
| price_change | decimal(10,2) | NULL | 涨跌额 |
| turnover | decimal(10,2) | NULL | 换手率(%) |

**索引:**
- `PRIMARY` (id) UNIQUE
- `symbol_date` (symbol, trade_date) UNIQUE
- `uk_symbol_trade_date` (symbol, trade_date) UNIQUE

---

## stock_daily_indicator

股票日线指标表（均线及平均值）

| 字段名 | 类型 | 可空 | 说明 |
|--------|------|------|------|
| id | int | NOT NULL | 主键 |
| symbol | varchar(10) | NOT NULL | 股票代码 |
| trade_date | date | NOT NULL | 交易日期 |
| ma5 | decimal(10,2) | NULL | 5日均线 |
| ma10 | decimal(10,2) | NULL | 10日均线 |
| ma20 | decimal(10,2) | NULL | 20日均线 |
| ma30 | decimal(10,2) | NULL | 30日均线 |
| ma60 | decimal(10,2) | NULL | 60日均线 |
| vol_ma5 | bigint | NULL | 5日平均成交量（股） |
| vol_ma10 | bigint | NULL | 10日平均成交量（股） |
| turnover_ma5 | decimal(10,2) | NULL | 5日平均换手率(%) |
| turnover_ma10 | decimal(10,2) | NULL | 10日平均换手率(%) |
| created_at | timestamp | NULL | 创建时间 |
| updated_at | timestamp | NULL | 更新时间 |

**索引:**
- `PRIMARY` (id) UNIQUE
- `uk_symbol_date` (symbol, trade_date) UNIQUE
- `idx_symbol_date` (symbol, trade_date)

---

---

## portfolio_trade

持仓交易记录表

| 字段名 | 类型 | 可空 | 说明 |
|--------|------|------|------|
| id | int | NOT NULL | 主键 |
| symbol | varchar(20) | NOT NULL | 股票代码 |
| name | varchar(100) | NOT NULL | 股票名称 |
| trade_type | varchar(10) | NOT NULL | 交易类型 BUY/SELL |
| trade_date | date | NOT NULL | 交易日期 |
| price | float | NOT NULL | 成交价格 |
| quantity | int | NOT NULL | 成交股数 |
| amount | float | NOT NULL | 成交金额 |
| created_at | timestamp | NULL | 创建时间 |
| updated_at | timestamp | NULL | 更新时间 |

**索引:**
- `PRIMARY` (id) UNIQUE
- `idx_symbol` (symbol)
- `idx_trade_date` (trade_date)

---

## portfolio_closed

清仓盈亏记录表

| 字段名 | 类型 | 可空 | 说明 |
|--------|------|------|------|
| id | int | NOT NULL | 主键 |
| symbol | varchar(20) | NOT NULL | 股票代码 |
| name | varchar(100) | NOT NULL | 股票名称 |
| total_buy_amount | float | NOT NULL | 总买入金额 |
| total_sell_amount | float | NOT NULL | 总卖出金额 |
| total_quantity | int | NOT NULL | 总股数 |
| avg_buy_price | float | NOT NULL | 平均买入价 |
| avg_sell_price | float | NOT NULL | 平均卖出价 |
| open_date | date | NOT NULL | 首次买入日期 |
| close_date | date | NOT NULL | 清仓日期 |
| realized_pnl | float | NOT NULL | 实现盈亏 |
| pnl_pct | float | NOT NULL | 盈亏百分比 |
| created_at | timestamp | NULL | 创建时间 |
| updated_at | timestamp | NULL | 更新时间 |

**索引:**
- `PRIMARY` (id) UNIQUE
- `idx_symbol` (symbol)

---

## portfolio_config

持仓配置表

| 字段名 | 类型 | 可空 | 说明 |
|--------|------|------|------|
| id | int | NOT NULL | 主键 |
| initial_capital | float | NOT NULL | 初始资金，默认 35000 |
| created_at | timestamp | NULL | 创建时间 |
| updated_at | timestamp | NULL | 更新时间 |

**索引:**
- `PRIMARY` (id) UNIQUE

---

## 备注

- `stock_daily` 存在重复的唯一索引：`symbol_date` 和 `uk_symbol_trade_date` 索引字段相同，可优化合并。
- 总表数: 6
