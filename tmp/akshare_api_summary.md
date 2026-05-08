# AkShare 股票财报数据接口调研总结

## 一、利润表 (Profit Sheet)

### 1. `stock_profit_sheet_by_report_em(symbol)`
- **参数**: `symbol` (带市场前缀，如 `'sh600519'`, `'sz000001'`)
- **返回**: DataFrame (约 203 列)
- **关键字段**:
  - `REPORT_DATE` - 报告日期
  - `TOTAL_OPERATE_INCOME` - 营业总收入
  - `OPERATE_INCOME` - 营业收入
  - `TOTAL_OPERATE_COST` - 营业总成本
  - `OPERATE_COST` - 营业成本
  - `SALE_EXPENSE` - 销售费用
  - `MANAGE_EXPENSE` - 管理费用
  - `FINANCE_EXPENSE` - 财务费用
  - `OPERATE_PROFIT` - 营业利润
  - `TOTAL_PROFIT` - 利润总额
  - `INCOME_TAX` - 所得税费用
  - `NETPROFIT` - 净利润
  - `PARENT_NETPROFIT` - 归母净利润
  - `BASIC_EPS` - 基本每股收益
  - `DILUTED_EPS` - 稀释每股收益
- **说明**: 按报告期（季报/年报）获取利润表，包含同比字段（`_YOY`）

### 2. `stock_profit_sheet_by_quarterly_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **返回**: DataFrame (约 204 列)
- **说明**: 按单季度数据

### 3. `stock_profit_sheet_by_yearly_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **返回**: DataFrame (约 203 列)
- **说明**: 按年度报告

### 4. `stock_profit_sheet_by_report_delisted_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **说明**: 退市股票利润表

### 5. `stock_financial_benefit_ths(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码 (如 `'600519'`)
  - `indicator`: `{'按报告期', '按年度', '按单季度'}`
- **返回**: DataFrame (约 47 列)
- **关键字段**:
  - `报告期`
  - `净利润`
  - `营业总收入`
  - `营业总成本`
  - `归属于母公司所有者的净利润`
  - `扣除非经常性损益后的净利润`
  - `基本每股收益`

### 6. `stock_financial_benefit_new_ths(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码
  - `indicator`: `{'按报告期', '一季报', '中报', '三季报', '年报'}`
- **说明**: 新版同花顺利润表

### 7. `stock_financial_report_sina(stock, symbol)`
- **参数**:
  - `stock`: 股票代码 (如 `'600519'`)
  - `symbol`: `{'利润表', '资产负债表', '现金流量表'}`
- **返回**: DataFrame (利润表 83 列)
- **关键字段**:
  - `报告日`
  - `营业总收入`
  - `营业收入`
  - `营业总成本`
  - `营业成本`
  - `销售费用`
  - `管理费用`
  - `财务费用`
  - `营业利润`
  - `利润总额`
  - `所得税费用`
  - `净利润`
  - `归属于母公司所有者的净利润`
  - `基本每股收益`
  - `稀释每股收益`

---

## 二、资产负债表 (Balance Sheet)

### 1. `stock_balance_sheet_by_report_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **返回**: DataFrame (约 319 列)
- **关键字段**:
  - `REPORT_DATE` - 报告日期
  - `TOTAL_ASSETS` - 资产总计
  - `TOTAL_CURRENT_ASSETS` - 流动资产合计
  - `TOTAL_NONCURRENT_ASSETS` - 非流动资产合计
  - `TOTAL_LIABILITIES` - 负债合计
  - `TOTAL_CURRENT_LIAB` - 流动负债合计
  - `TOTAL_NONCURRENT_LIAB` - 非流动负债合计
  - `TOTAL_EQUITY` - 所有者权益合计
  - `TOTAL_PARENT_EQUITY` - 归属于母公司所有者权益合计
  - `MINORITY_EQUITY` - 少数股东权益
  - `MONETARYFUNDS` - 货币资金
  - `ACCOUNTS_RECE` - 应收账款
  - `INVENTORY` - 存货
  - `FIXED_ASSET` - 固定资产
  - `INTANGIBLE_ASSET` - 无形资产
  - `GOODWILL` - 商誉
  - `SHORT_LOAN` - 短期借款
  - `LONG_LOAN` - 长期借款
  - `BOND_PAYABLE` - 应付债券
  - `SHARE_CAPITAL` - 实收资本(或股本)
  - `CAPITAL_RESERVE` - 资本公积
  - `SURPLUS_RESERVE` - 盈余公积
  - `UNASSIGN_RPOFIT` - 未分配利润
- **说明**: 包含同比字段（`_YOY`）

### 2. `stock_balance_sheet_by_yearly_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **返回**: DataFrame (约 319 列)
- **说明**: 按年度报告

### 3. `stock_balance_sheet_by_report_delisted_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **说明**: 退市股票资产负债表

### 4. `stock_financial_debt_ths(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码
  - `indicator`: `{'按报告期', '按年度'}`
- **返回**: DataFrame (约 76 列)
- **关键字段**:
  - `报告期`
  - `所有者权益（或股东权益）合计`
  - `资产合计`
  - `负债合计`
  - `归属于母公司所有者权益合计`
  - `流动资产`
  - `货币资金`
  - `应收账款`
  - `存货`
  - `固定资产`
  - `无形资产`
  - `流动负债`
  - `短期借款`
  - `应付账款`
  - `长期借款`
  - `实收资本（或股本）`
  - `资本公积`
  - `未分配利润`

### 5. `stock_financial_debt_new_ths(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码
  - `indicator`: `{'按报告期', '按年度'}`
- **说明**: 新版同花顺资产负债表

### 6. `stock_financial_report_sina(stock, symbol='资产负债表')`
- **返回**: DataFrame (147 列)
- **关键字段**:
  - `报告日`
  - `流动资产`
  - `货币资金`
  - `交易性金融资产`
  - `应收票据及应收账款`
  - `存货`
  - `流动资产合计`
  - `非流动资产`
  - `长期股权投资`
  - `固定资产`
  - `无形资产`
  - `非流动资产合计`
  - `资产总计`
  - `流动负债`
  - `短期借款`
  - `应付票据及应付账款`
  - `流动负债合计`
  - `非流动负债`
  - `长期借款`
  - `应付债券`
  - `非流动负债合计`
  - `负债合计`
  - `实收资本`
  - `资本公积`
  - `盈余公积`
  - `未分配利润`
  - `归属于母公司股东权益合计`
  - `少数股东权益`
  - `所有者权益合计`

---

## 三、现金流量表 (Cash Flow Sheet)

### 1. `stock_cash_flow_sheet_by_report_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **返回**: DataFrame (约 254 列)
- **关键字段**:
  - `REPORT_DATE` - 报告日期
  - `NETCASH_OPERATE` - 经营活动产生的现金流量净额
  - `NETCASH_INVEST` - 投资活动产生的现金流量净额
  - `NETCASH_FINANCE` - 筹资活动产生的现金流量净额
  - `CCE_ADD` - 现金及现金等价物净增加额
  - `END_CCE` - 期末现金及现金等价物余额
  - `BEGIN_CCE` - 期初现金及现金等价物余额
  - `NETPROFIT` - 净利润
- **说明**: 包含同比字段（`_YOY`）

### 2. `stock_cash_flow_sheet_by_quarterly_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **返回**: DataFrame (约 253 列)
- **说明**: 按单季度数据

### 3. `stock_cash_flow_sheet_by_yearly_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **返回**: DataFrame (约 254 列)
- **说明**: 按年度报告

### 4. `stock_cash_flow_sheet_by_report_delisted_em(symbol)`
- **参数**: `symbol` (带市场前缀)
- **说明**: 退市股票现金流量表

### 5. `stock_financial_cash_ths(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码
  - `indicator`: `{'按报告期', '按年度', '按单季度'}`
- **返回**: DataFrame (约 72 列)
- **关键字段**:
  - `报告期`
  - `现金及现金等价物净增加额`
  - `经营活动产生的现金流量净额`
  - `投资活动产生的现金流量净额`
  - `筹资活动产生的现金流量净额`
  - `期末现金及现金等价物余额`
  - `销售商品、提供劳务收到的现金`
  - `购买商品、接受劳务支付的现金`
  - `收回投资收到的现金`
  - `购建固定资产、无形资产和其他长期资产支付的现金`
  - `吸收投资收到的现金`
  - `偿还债务支付的现金`

### 6. `stock_financial_cash_new_ths(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码
  - `indicator`: `{'按报告期', '一季报', '中报', '三季报', '年报'}`
- **说明**: 新版同花顺现金流量表

### 7. `stock_financial_report_sina(stock, symbol='现金流量表')`
- **返回**: DataFrame (71 列)
- **关键字段**:
  - `报告日`
  - `经营活动产生的现金流量净额`
  - `销售商品、提供劳务收到的现金`
  - `经营活动现金流入小计`
  - `购买商品、接受劳务支付的现金`
  - `经营活动现金流出小计`
  - `投资活动产生的现金流量净额`
  - `收回投资所收到的现金`
  - `投资活动现金流入小计`
  - `购建固定资产、无形资产和其他长期资产所支付的现金`
  - `投资活动现金流出小计`
  - `筹资活动产生的现金流量净额`
  - `吸收投资收到的现金`
  - `筹资活动现金流入小计`
  - `偿还债务支付的现金`
  - `筹资活动现金流出小计`
  - `现金及现金等价物净增加额`
  - `期初现金及现金等价物余额`
  - `期末现金及现金等价物余额`

---

## 四、主要财务指标 (Key Financial Indicators)

### 1. `stock_financial_analysis_indicator(symbol, start_year)`
- **参数**:
  - `symbol`: 股票代码 (如 `'600519'`)
  - `start_year`: 起始年份 (如 `'2023'`)
- **返回**: DataFrame (约 86 列)
- **关键字段**:
  - `日期`
  - `摊薄每股收益(元)`
  - `加权每股收益(元)`
  - `每股净资产_调整前(元)`
  - `每股经营性现金流(元)`
  - `总资产利润率(%)`
  - `主营业务利润率(%)`
  - `总资产净利润率(%)`
  - `成本费用利润率(%)`
  - `营业利润率(%)`
  - `销售净利率(%)`
  - `销售毛利率(%)`
  - `净资产收益率(%)`
  - `加权净资产收益率(%)`
  - `主营业务收入增长率(%)`
  - `净利润增长率(%)`
  - `净资产增长率(%)`
  - `总资产增长率(%)`
  - `应收账款周转率(次)`
  - `存货周转率(次)`
  - `固定资产周转率(次)`
  - `总资产周转率(次)`
  - `流动比率`
  - `速动比率`
  - `现金比率(%)`
  - `资产负债率(%)`
  - `股东权益比率(%)`
  - `产权比率(%)`
- **说明**: 新浪财经财务指标，数据较全但更新可能滞后

### 2. `stock_financial_analysis_indicator_em(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码 (带市场前缀)
  - `indicator`: `{'按报告期', '按年度'}`
- **返回**: DataFrame (列数不固定)
- **说明**: 东方财富财务指标，目前部分股票可能返回 None（接口不稳定）

### 3. `stock_financial_abstract_ths(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码
  - `indicator`: `{'按报告期', '按年度', '按单季度'}`
- **返回**: DataFrame (约 25 列)
- **关键字段**:
  - `报告期`
  - `净利润`
  - `净利润同比增长率`
  - `扣非净利润`
  - `营业总收入`
  - `营业总收入同比增长率`
  - `基本每股收益`
  - `每股净资产`
  - `每股资本公积金`
  - `每股未分配利润`
  - `每股经营现金流`
  - `销售净利率`
  - `销售毛利率`
  - `净资产收益率`
  - `净资产收益率-摊薄`
  - `营业周期`
  - `存货周转率`
  - `存货周转天数`
  - `应收账款周转天数`
  - `流动比率`
  - `速动比率`
  - `保守速动比率`
  - `产权比率`
  - `资产负债率`
- **说明**: 同花顺主要指标，数据简洁，包含同比增长率

### 4. `stock_financial_abstract_new_ths(symbol, indicator)`
- **参数**:
  - `symbol`: 股票代码
  - `indicator`: `{'按报告期', '一季报', '中报', '三季报', '年报'}`
- **返回**: DataFrame (长格式，约 1200 行 x 10 列)
- **关键字段**:
  - `report_date`
  - `report_name`
  - `report_period`
  - `quarter_name`
  - `metric_name`
  - `value`
  - `single`
  - `yoy`
  - `mom`
  - `single_yoy`
- **说明**: 新版同花顺主要指标，长格式，指标包括:
  - `parent_holder_net_profit` - 归母净利润
  - `basic_eps` - 基本每股收益
  - `calc_per_net_assets` - 每股净资产
  - `inventory_turnover_ratio` - 存货周转率
  - `current_ratio` - 流动比率
  - `equity_ratio` - 产权比率
  - `assets_debt_ratio` - 资产负债率
  - `sale_gross_margin` - 销售毛利率
  - `sale_net_interest_ratio` - 销售净利率
  - `index_weighted_avg_roe` - 加权平均净资产收益率
  等 24 个指标

### 5. `stock_financial_abstract(symbol)`
- **参数**: `symbol` (如 `'600519'`)
- **返回**: DataFrame (约 104 列，宽格式)
- **关键字段**:
  - `选项`
  - `指标`
  - 各报告期列（如 `20260331`, `20251231` 等）
- **说明**: 新浪财经财务摘要，行是指标，列是报告期，包含归母净利润、营业总收入、营业成本、净利润、扣非净利润等常用指标

---

## 五、股票列表/基本信息 (Stock List / Basic Info)

### 1. `stock_info_sh_name_code(symbol)`
- **参数**: `symbol`: `{'主板A股': '1', '主板B股': '2', '科创板': '8'}`
- **返回**: DataFrame (约 1703 行 x 6 列)
- **字段**:
  - `证券代码`
  - `证券简称`
  - `证券全称`
  - `公司简称`
  - `公司全称`
  - `上市日期`
- **说明**: 上海证券交易所股票列表

### 2. `stock_info_sz_name_code(symbol)`
- **参数**: `symbol`: `{'A股列表', 'B股列表', 'CDR列表', 'AB股列表'}`
- **返回**: DataFrame (约 2889 行 x 7 列)
- **字段**:
  - `板块`
  - `A股代码`
  - `A股简称`
  - `A股上市日期`
  - `A股总股本`
  - `A股流通股本`
  - `所属行业`
- **说明**: 深圳证券交易所股票列表

### 3. `stock_info_bj_name_code()`
- **返回**: DataFrame (约 312 行 x 8 列)
- **字段**:
  - `证券代码`
  - `证券简称`
  - `总股本`
  - `流通股本`
  - `上市日期`
  - `所属行业`
  - `地区`
  - `报告日期`
- **说明**: 北京证券交易所股票列表

### 4. `stock_zh_a_spot()`
- **返回**: DataFrame (约 5512 行 x 14 列)
- **字段**:
  - `代码`
  - `名称`
  - `最新价`
  - `涨跌额`
  - `涨跌幅`
  - `买入`
  - `卖出`
  - `昨收`
  - `今开`
  - `最高`
  - `最低`
  - `成交量`
  - `成交额`
  - `时间戳`
- **说明**: 新浪财经 A 股实时行情，包含所有 A 股（含北交所）

### 5. `stock_individual_info_em(symbol)`
- **参数**: `symbol` (如 `'600519'`)
- **返回**: DataFrame (约 10 行 x 2 列)
- **字段**:
  - `item`
  - `value`
- **说明**: 东方财富个股基本信息，包含:
  - `最新` - 最新价
  - `股票代码`
  - `股票简称`
  - `总股本`
  - `流通股`
  - `总市值`
  - `流通市值`
  - `行业`
  - `上市时间`

### 6. `stock_zh_a_new_em()`
- **返回**: DataFrame (约 79 行 x 17 列)
- **字段**:
  - `序号`
  - `代码`
  - `名称`
  - `最新价`
  - `涨跌幅`
  - `涨跌额`
  - `成交量`
  - `成交额`
  - `振幅`
  - `最高`
  - `最低`
  - `今开`
  - `昨收`
  - `量比`
  - `换手率`
  - `市盈率-动态`
  - `市净率`
- **说明**: 东方财富新股列表

### 7. `stock_zh_a_st_em()`
- **返回**: DataFrame (约 266 行 x 17 列)
- **字段**: 同新股列表
- **说明**: 东方财富 ST 股票列表

### 8. `stock_zh_a_stop_em()`
- **返回**: DataFrame (约 291 行 x 17 列)
- **字段**: 同新股列表
- **说明**: 东方财富停牌股票列表

### 9. `stock_zh_a_hist(symbol, period, start_date, end_date, adjust)`
- **参数**:
  - `symbol`: 股票代码 (如 `'000001'`)
  - `period`: `{'daily', 'weekly', 'monthly'}`
  - `start_date`: 起始日期 (如 `'20250501'`)
  - `end_date`: 结束日期 (如 `'20250507'`)
  - `adjust`: `{'', 'qfq', 'hfq'}`
- **返回**: DataFrame (约 N 行 x 12 列)
- **字段**:
  - `日期`
  - `股票代码`
  - `开盘`
  - `收盘`
  - `最高`
  - `最低`
  - `成交量`
  - `成交额`
  - `振幅`
  - `涨跌幅`
  - `涨跌额`
  - `换手率`
- **说明**: 东方财富 A 股历史行情

### 10. `stock_zh_a_hist_min_em(symbol, start_date, end_date, period, adjust)`
- **参数**:
  - `symbol`: 股票代码
  - `start_date`: 起始日期
  - `end_date`: 结束日期
  - `period`: `{'1', '5', '15', '30', '60'}`
  - `adjust`: `{'', 'qfq', 'hfq'}`
- **返回**: DataFrame
- **说明**: 东方财富 A 股分时历史行情

---

## 六、其他相关接口

### 1. `stock_financial_report_sina(stock, symbol)`
- **说明**: 新浪财经财务报表，支持利润表、资产负债表、现金流量表，字段为中文，易于理解

### 2. `stock_financial_hk_analysis_indicator_em(symbol, indicator)`
- **参数**:
  - `symbol`: 港股代码 (如 `'00700'`)
  - `indicator`: `{'年报', '报告期'}`
- **说明**: 东方财富港股财务指标

### 3. `stock_financial_us_analysis_indicator_em(symbol, indicator)`
- **参数**:
  - `symbol`: 美股代码 (如 `'TSLA'`)
  - `indicator`: `{'年报', '报告期', '累计季报'}`
- **说明**: 东方财富美股财务指标

### 4. `stock_financial_us_report_em(stock, symbol, indicator)`
- **参数**:
  - `stock`: 美股代码
  - `symbol`: `{'资产负债表', '综合损益表', '现金流量表'}`
  - `indicator`: `{'年报', '报告期', '累计季报'}`
- **说明**: 东方财富美股财务报表

---

## 七、使用建议

- **获取 A 股财务报表（利润表、资产负债表、现金流量表）**: 优先使用 `stock_*_by_report_em` 系列（东方财富），数据全面且包含同比字段，但 `symbol` 需要带市场前缀（`sh`/`sz`）
- **获取中文列名、更易读的报表**: 使用 `stock_financial_report_sina`，`symbol` 只需股票代码
- **获取主要财务指标**: 使用 `stock_financial_abstract_ths`（同花顺），数据简洁且包含同比增长率；或使用 `stock_financial_analysis_indicator`（新浪财经），指标更全面
- **获取股票列表**: 使用 `stock_zh_a_spot`（新浪财经实时行情，速度快）或 `stock_info_sh_name_code` + `stock_info_sz_name_code` + `stock_info_bj_name_code`（交易所官方列表）
- **获取个股基本信息**: 使用 `stock_individual_info_em`（东方财富）
- **获取历史行情**: 使用 `stock_zh_a_hist`（东方财富，日级）或 `stock_zh_a_hist_min_em`（分钟级）
