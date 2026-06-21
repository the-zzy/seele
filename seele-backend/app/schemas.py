"""
请求响应模式模块
"""

from datetime import date, datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator

# ==================== 通用响应 ====================


class ResponseModel(BaseModel):
    """通用响应模型"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: Any = Field(default=None, description="数据")


class PageResult(BaseModel):
    """分页结果模型"""
    list: List[Any] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总条数")
    page_num: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=10, description="每页条数")


# ==================== 股票基础数据 ====================


class StockBasicCreate(BaseModel):
    """股票基础数据-创建"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    area: Optional[str] = Field(None, description="所在地区")
    industry: Optional[str] = Field(None, description="所属行业")
    market: Optional[str] = Field(None, description="市场板块")
    float_market_cap: Optional[float] = Field(None, description="流通市值(亿元)")
    list_date: Optional[date] = Field(None, description="上市日期")


class StockBasicUpdate(BaseModel):
    """股票基础数据-更新"""
    id: int = Field(..., description="股票ID")
    name: Optional[str] = Field(None, description="股票名称")
    area: Optional[str] = Field(None, description="所在地区")
    industry: Optional[str] = Field(None, description="所属行业")
    market: Optional[str] = Field(None, description="市场板块")
    float_market_cap: Optional[float] = Field(None, description="流通市值(亿元)")
    list_date: Optional[date] = Field(None, description="上市日期")


class StockBasicResponse(BaseModel):
    """股票基础数据-响应"""
    id: int
    symbol: str
    name: str
    area: Optional[str]
    industry: Optional[str]
    industry_detail: Optional[str] = None
    market: Optional[str]
    float_market_cap: Optional[float]
    list_date: Optional[str]

    @field_validator('list_date', mode='before')
    @classmethod
    def validate_list_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):  # datetime.date 对象
            return v.strftime('%Y-%m-%d')
        return str(v)

    class Config:
        from_attributes = True


class StockBasicWithFinancialResponse(StockBasicResponse):
    """股票基础数据（含财务指标）-响应"""
    roe: Optional[float] = None
    gross_profit_ratio: Optional[float] = None
    net_profit_ratio: Optional[float] = None
    net_profit_yoy: Optional[float] = None
    revenue_yoy: Optional[float] = None
    eps: Optional[float] = None
    debt_ratio: Optional[float] = None


class StockBasicQuery(BaseModel):
    """股票基础数据-分页查询"""
    page_num: int = Field(default=1, description="页码")
    page_size: int = Field(default=10, description="每页条数")
    sort_field: Optional[str] = Field(None, description="排序字段")
    sort_order: Optional[str] = Field(default="asc", description="排序方向")
    symbol: Optional[str] = Field(None, description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    industry: Optional[str] = Field(None, description="行业")
    market: Optional[str] = Field(None, description="市场")
    area: Optional[str] = Field(None, description="地区")
    exclude_st: bool = Field(default=False, description="是否过滤ST股票")
    exclude_cyb: bool = Field(default=False, description="是否过滤创业板")
    exclude_kcb: bool = Field(default=False, description="是否过滤科创板")
    exclude_bse: bool = Field(default=False, description="是否过滤北交所")


class MainwavePickerQuery(StockBasicQuery):
    """主升浪选股查询参数"""
    trade_date: Optional[str] = Field(None, description="交易日期(YYYY-MM-DD)")
    float_market_cap_min: Optional[float] = Field(None, description="流通市值最小值(亿元)")
    close_max: Optional[float] = Field(None, description="收盘价最大值")
    avg_turnover_min: Optional[float] = Field(None, description="10日平均换手率最小值(%)")
    avg_amount_min: Optional[float] = Field(None, description="10日平均成交额最小值(元)")
    ma_bull: Optional[bool] = Field(None, description="均线多头排列")


class MainwaveDetectQuery(BaseModel):
    """主升浪阶段检测-单只股票"""
    symbol: str = Field(..., description="股票代码")
    min_gain_pct: float = Field(default=180.0, description="最小涨幅阈值(%)")
    window_days: int = Field(default=30, description="窗口交易日数")
    start_date: Optional[str] = Field(None, description="查询起始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="查询结束日期 YYYY-MM-DD")


class MainwaveBatchDetectQuery(BaseModel):
    """主升浪阶段检测-批量"""
    symbols: List[str] = Field(..., description="股票代码列表")
    min_gain_pct: float = Field(default=180.0, description="最小涨幅阈值(%)")
    window_days: int = Field(default=30, description="窗口交易日数")
    start_date: Optional[str] = Field(None, description="查询起始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="查询结束日期 YYYY-MM-DD")


# ==================== 股票停牌信息 ====================


class StockSuspensionCreate(BaseModel):
    """股票停牌信息-创建"""
    symbol: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    suspend_date: date = Field(..., description="停牌日期")
    resume_date: Optional[date] = Field(None, description="复牌日期")
    reason: Optional[str] = Field(None, description="停牌原因")


class StockSuspensionQuery(BaseModel):
    """股票停牌信息-查询"""
    symbol: Optional[str] = Field(None, description="股票代码")
    suspend_date: Optional[date] = Field(None, description="停牌日期")


# ==================== 股票日线数据 ====================


class StockDailyCreate(BaseModel):
    """股票日线数据-创建"""
    trade_date: str = Field(..., description="交易日期")
    symbol: str = Field(..., description="股票代码")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    close: Optional[float] = Field(None, description="收盘价")
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    amplitude: Optional[float] = Field(None, description="振幅")
    pct_chg: Optional[float] = Field(None, description="涨跌幅")
    price_change: Optional[float] = Field(None, description="涨跌额")
    turnover: Optional[float] = Field(None, description="换手率")


class StockDailyUpdate(BaseModel):
    """股票日线数据-更新"""
    id: int = Field(..., description="日线ID")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    close: Optional[float] = Field(None, description="收盘价")
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    amplitude: Optional[float] = Field(None, description="振幅")
    pct_chg: Optional[float] = Field(None, description="涨跌幅")
    price_change: Optional[float] = Field(None, description="涨跌额")
    turnover: Optional[float] = Field(None, description="换手率")


class StockDailyResponse(BaseModel):
    """股票日线数据-响应"""
    id: int
    symbol: str
    trade_date: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[float]
    amount: Optional[float]
    amplitude: Optional[float]
    pct_chg: Optional[float]
    price_change: Optional[float]
    turnover: Optional[float]

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):  # datetime.date 对象
            return v.strftime('%Y-%m-%d')
        return str(v)

    class Config:
        from_attributes = True


class StockDailyWithIndicatorResponse(StockDailyResponse):
    """股票日线数据（含指标）-响应"""
    stock_name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    area: Optional[str] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma30: Optional[float] = None
    ma60: Optional[float] = None
    vol_ma5: Optional[int] = None
    vol_ma10: Optional[int] = None
    amount_ma5: Optional[int] = None
    amount_ma10: Optional[int] = None
    turnover_ma5: Optional[float] = None
    turnover_ma10: Optional[float] = None


class StockDailyQuery(BaseModel):
    """股票日线数据-分页查询"""
    page_num: int = Field(default=1, description="页码")
    page_size: int = Field(default=10, description="每页条数")
    symbol: Optional[str] = Field(None, description="股票代码")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")


# ==================== 股票日线指标 ====================


class StockDailyIndicatorResponse(BaseModel):
    """股票日线指标-响应"""
    id: int
    symbol: str
    trade_date: str
    ma5: Optional[float]
    ma10: Optional[float]
    ma20: Optional[float]
    ma30: Optional[float]
    ma60: Optional[float]
    vol_ma5: Optional[int]
    vol_ma10: Optional[int]
    turnover_ma5: Optional[float]
    turnover_ma10: Optional[float]
    chg_5d: Optional[float] = None
    chg_10d: Optional[float] = None
    macd_dif: Optional[float] = None
    macd_dea: Optional[float] = None
    macd_hist: Optional[float] = None
    rsi_6: Optional[float] = None
    rsi_12: Optional[float] = None
    rsi_24: Optional[float] = None
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None
    kdj_j: Optional[float] = None
    boll_upper: Optional[float] = None
    boll_middle: Optional[float] = None
    boll_lower: Optional[float] = None
    created_at: Optional[str]
    updated_at: Optional[str]

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class ComputeIndicatorResult(BaseModel):
    """计算指标结果"""
    total: int = Field(..., description="处理股票总数")
    success: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")
    trade_date: str = Field(..., description="交易日期")


class PctChgDistributionItem(BaseModel):
    """涨幅分布统计-单日数据"""
    trade_date: str = Field(..., description="交易日期")
    total_stocks: int = Field(..., description="当日总股票数")
    matched_count: int = Field(..., description="涨幅超过阈值的股票数")
    matched_percent: float = Field(..., description="涨幅超过阈值的百分比")


# ==================== 市场情绪 ====================


class DailySentimentQuery(BaseModel):
    """每日市场情绪查询参数"""
    start_date: str = Field(..., description='开始日期')
    end_date: str = Field(..., description='结束日期')



# ==================== 数据同步 ====================


class SyncJobLogCreate(BaseModel):
    """同步任务日志-创建"""
    job_type: str = Field(..., description='任务类型: stock_basic / daily / financial / indicator')
    trigger_type: str = Field(default='scheduled', description='触发方式: scheduled / manual')
    trade_date: Optional[str] = Field(None, description='关联交易日')


class SyncJobLogUpdate(BaseModel):
    """同步任务日志-更新"""
    id: int
    status: Optional[str] = Field(None, description='状态')
    ended_at: Optional[datetime] = Field(None, description='结束时间')
    duration_seconds: Optional[int] = Field(None, description='执行耗时(秒)')
    success_count: Optional[int] = Field(None, description='成功处理数')
    failed_count: Optional[int] = Field(None, description='失败/异常数')
    skipped_count: Optional[int] = Field(None, description='跳过数')
    total_count: Optional[int] = Field(None, description='总处理数')
    trade_date: Optional[str] = Field(None, description='关联交易日')
    error_message: Optional[str] = Field(None, description='错误信息')
    extra_info: Optional[str] = Field(None, description='额外信息')


class SyncJobLogResponse(BaseModel):
    """同步任务日志-响应"""
    id: int
    job_type: str
    trigger_type: str
    status: str
    started_at: str
    ended_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    success_count: Optional[int] = None
    failed_count: Optional[int] = None
    skipped_count: Optional[int] = None
    total_count: Optional[int] = None
    trade_date: Optional[str] = None
    error_message: Optional[str] = None
    extra_info: Optional[str] = None

    @field_validator('started_at', 'ended_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class SyncJobLogQuery(BaseModel):
    """同步任务日志-查询"""
    page_num: int = Field(default=1, description='页码')
    page_size: int = Field(default=10, description='每页条数')
    job_type: Optional[str] = Field(None, description='任务类型')
    status: Optional[str] = Field(None, description='状态')
    trigger_type: Optional[str] = Field(None, description='触发方式')
    days: Optional[int] = Field(None, description='最近N天')


class SyncResult(BaseModel):
    """同步结果"""
    success: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")


class CompareResult(BaseModel):
    """对比结果"""
    trade_date: str
    db_count: int
    api_count: int
    only_in_db: List[str] = Field(default_factory=list)
    only_in_api: List[str] = Field(default_factory=list)
    differences: List[str] = Field(default_factory=list)
    summary: str


# ==================== 持仓管理 ====================


class PortfolioTradeCreate(BaseModel):
    """交易记录-创建"""
    symbol: str = Field(..., description='股票代码')
    name: str = Field(..., description='股票名称')
    trade_type: str = Field(..., description='交易类型 BUY/SELL')
    trade_date: str = Field(..., description='交易日期')
    price: float = Field(..., description='成交价格')
    quantity: int = Field(..., description='成交股数')
    amount: Optional[float] = Field(None, description='成交金额（不传则自动计算）')
    stamp_tax: Optional[float] = Field(None, description='印花税')
    transfer_fee: Optional[float] = Field(None, description='过户费')
    commission: Optional[float] = Field(None, description='券商佣金/手续费（不传则自动计算）')
    dividend: Optional[float] = Field(0, description='分红金额')
    remark: Optional[str] = Field(None, description='备注')

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('amount', mode='before')
    @classmethod
    def validate_amount(cls, v, info):
        if v is not None:
            return v
        data = info.data
        price = data.get('price')
        quantity = data.get('quantity')
        if price is not None and quantity is not None:
            return round(price * quantity, 4)
        return v


class PortfolioDayTradeCreate(BaseModel):
    """做T交易记录-创建"""
    symbol: str = Field(..., description='股票代码')
    name: str = Field(..., description='股票名称')
    trade_date: str = Field(..., description='交易日期')
    buy_price: float = Field(..., description='买入价格')
    sell_price: float = Field(..., description='卖出价格')
    quantity: int = Field(..., description='成交股数')

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)


class PortfolioTradeResponse(BaseModel):
    """交易记录-响应"""
    id: int
    symbol: str
    name: str
    trade_type: str
    trade_date: str
    price: float
    quantity: int
    amount: float
    stamp_tax: Optional[float] = 0
    transfer_fee: Optional[float] = 0
    commission: Optional[float] = 0
    total_fee: Optional[float] = None
    dividend: Optional[float] = 0
    remark: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @model_validator(mode='after')
    def compute_total_fee(self):
        if self.total_fee is None:
            self.total_fee = round(
                float(self.commission or 0)
                + float(self.stamp_tax or 0)
                + float(self.transfer_fee or 0),
                2,
            )
        return self

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class PortfolioTradeUpdate(BaseModel):
    """交易记录-更新"""
    trade_date: Optional[str] = Field(None, description='交易日期')
    trade_type: Optional[str] = Field(None, description='交易类型 BUY/SELL')
    price: Optional[float] = Field(None, description='成交价格')
    quantity: Optional[int] = Field(None, description='成交股数')
    amount: Optional[float] = Field(None, description='成交金额')
    stamp_tax: Optional[float] = Field(None, description='印花税')
    transfer_fee: Optional[float] = Field(None, description='过户费')
    commission: Optional[float] = Field(None, description='券商佣金/手续费')
    dividend: Optional[float] = Field(None, description='分红金额')
    remark: Optional[str] = Field(None, description='备注')

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('amount', mode='before')
    @classmethod
    def validate_amount(cls, v, info):
        if v is not None:
            return v
        data = info.data
        price = data.get('price')
        quantity = data.get('quantity')
        if price is not None and quantity is not None:
            return round(price * quantity, 4)
        return v


class PortfolioTradeQuery(BaseModel):
    """交易记录-查询"""
    page_num: int = Field(default=1, description='页码')
    page_size: int = Field(default=10, description='每页条数')
    symbol: Optional[str] = Field(None, description='股票代码')
    trade_type: Optional[str] = Field(None, description='交易类型 BUY/SELL')


class PortfolioClosedResponse(BaseModel):
    """清仓记录-响应"""
    id: int
    symbol: str
    name: str
    total_buy_amount: float
    total_sell_amount: float
    total_quantity: int
    avg_buy_price: float
    avg_sell_price: float
    open_date: str
    close_date: str
    realized_pnl: float
    pnl_pct: float
    total_fee: Optional[float] = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator('open_date', 'close_date', mode='before')
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class PositionItem(BaseModel):
    """当前持仓项"""
    symbol: str = Field(..., description='股票代码')
    name: str = Field(..., description='股票名称')
    quantity: int = Field(..., description='持仓股数')
    avg_cost: float = Field(..., description='平均成本')
    current_price: Optional[float] = Field(None, description='最新收盘价')
    market_value: Optional[float] = Field(None, description='市值')
    unrealized_pnl: Optional[float] = Field(None, description='浮动盈亏')
    unrealized_pnl_pct: Optional[float] = Field(None, description='浮动盈亏百分比')


class PortfolioSummary(BaseModel):
    """资产总览"""
    total_invested: float = Field(0.0, description='总投入')
    total_market_value: float = Field(0.0, description='总市值')
    total_pnl: float = Field(0.0, description='总盈亏（含已实现+浮动）')
    total_pnl_pct: float = Field(0.0, description='总收益率')
    realized_pnl: float = Field(0.0, description='已实现盈亏')
    unrealized_pnl: float = Field(0.0, description='浮动盈亏')
    position_count: int = Field(0, description='持仓股票数')
    initial_capital: float = Field(0.0, description='初始资金')
    total_return_pct: float = Field(0.0, description='基于初始资金的总收益率')


class PortfolioConfigUpdate(BaseModel):
    """持仓配置-更新"""
    initial_capital: float = Field(..., description='初始资金')
    commission_rate: Optional[float] = Field(0.000235, description='佣金费率')
    stamp_tax_rate: Optional[float] = Field(0.0005, description='印花税税率')
    transfer_rate: Optional[float] = Field(0.00001, description='过户费费率')


class DailyPnlItem(BaseModel):
    """每日盈亏序列项"""
    date: str = Field(..., description='日期')
    market_value: float = Field(..., description='当日总市值')
    daily_pnl: float = Field(..., description='当日盈亏')
    cumulative_pnl: float = Field(..., description='累计盈亏')


class PositionDistributionItem(BaseModel):
    """持仓分布项"""
    symbol: str = Field(..., description='股票代码')
    name: str = Field(..., description='股票名称')
    market_value: float = Field(..., description='市值')
    ratio: float = Field(..., description='占比')


# ==================== 财务指标 ====================


class StockFinancialIndicatorCreate(BaseModel):
    """财务指标-创建"""
    symbol: str = Field(..., description='股票代码')
    name: Optional[str] = Field(None, description='股票名称')
    report_date: Optional[date] = Field(None, description='报告期')
    net_profit: Optional[float] = Field(None, description='净利润')
    net_profit_yoy: Optional[float] = Field(None, description='净利润同比增长率(%)')
    deduct_net_profit: Optional[float] = Field(None, description='扣非净利润')
    total_revenue: Optional[float] = Field(None, description='营业总收入')
    revenue_yoy: Optional[float] = Field(None, description='营收同比增长率(%)')
    gross_profit_ratio: Optional[float] = Field(None, description='销售毛利率(%)')
    net_profit_ratio: Optional[float] = Field(None, description='销售净利率(%)')
    roe: Optional[float] = Field(None, description='净资产收益率(%)')
    roe_diluted: Optional[float] = Field(None, description='净资产收益率-摊薄(%)')
    eps: Optional[float] = Field(None, description='基本每股收益')
    bps: Optional[float] = Field(None, description='每股净资产')
    ops_cash_flow_per_share: Optional[float] = Field(None, description='每股经营现金流')
    current_ratio: Optional[float] = Field(None, description='流动比率')
    quick_ratio: Optional[float] = Field(None, description='速动比率')
    debt_ratio: Optional[float] = Field(None, description='资产负债率(%)')
    total_assets: Optional[float] = Field(None, description='资产总计(万元)')
    total_equity: Optional[float] = Field(None, description='所有者权益合计(万元)')
    operate_cash_flow: Optional[float] = Field(None, description='经营活动现金流净额')


class StockFinancialIndicatorResponse(BaseModel):
    """财务指标-响应"""
    symbol: str
    name: Optional[str] = None
    report_date: Optional[str] = None
    net_profit: Optional[float] = None
    net_profit_yoy: Optional[float] = None
    deduct_net_profit: Optional[float] = None
    total_revenue: Optional[float] = None
    revenue_yoy: Optional[float] = None
    gross_profit_ratio: Optional[float] = None
    net_profit_ratio: Optional[float] = None
    roe: Optional[float] = None
    roe_diluted: Optional[float] = None
    eps: Optional[float] = None
    bps: Optional[float] = None
    ops_cash_flow_per_share: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_ratio: Optional[float] = None
    total_assets: Optional[float] = None
    total_equity: Optional[float] = None
    operate_cash_flow: Optional[float] = None
    updated_at: Optional[str] = None

    @field_validator('report_date', mode='before')
    @classmethod
    def validate_report_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('updated_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class PortfolioPositionResponse(BaseModel):
    """持仓快照-响应"""
    id: int
    symbol: str
    name: str
    quantity: int
    avg_cost: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    alert_triggered: int = 0
    group: Optional[str] = 'default'
    remark: Optional[str] = None
    first_buy_date: Optional[str] = None
    current_holding_start_date: Optional[str] = None
    current_pnl: Optional[float] = None
    current_pnl_pct: Optional[float] = None
    updated_at: Optional[str] = None

    @field_validator('first_buy_date', mode='before')
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('updated_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class PortfolioPositionUpdate(BaseModel):
    """持仓快照-更新止损止盈等"""
    stop_loss_price: Optional[float] = Field(None, description='止损价')
    take_profit_price: Optional[float] = Field(None, description='止盈价')
    group: Optional[str] = Field(None, description='持仓分组')
    remark: Optional[str] = Field(None, description='备注')


class PortfolioAlertResponse(BaseModel):
    """持仓预警-响应"""
    symbol: str
    name: str
    current_price: float
    alert_type: str = Field(..., description='预警类型 stop_loss / take_profit')
    target_price: float
    pnl_pct: float


class StockFinancialIndicatorQuery(BaseModel):
    """财务指标-分页查询"""
    page_num: int = Field(default=1, description='页码')
    page_size: int = Field(default=10, description='每页条数')
    symbol: Optional[str] = Field(None, description='股票代码')
    name: Optional[str] = Field(None, description='股票名称')
    industry: Optional[str] = Field(None, description='所属行业')
    market: Optional[str] = Field(None, description='市场板块')
    sort_field: Optional[str] = Field(None, description='排序字段')
    sort_order: Optional[str] = Field(default='desc', description='排序方向')
    roe_min: Optional[float] = Field(None, description='ROE最小值')
    roe_max: Optional[float] = Field(None, description='ROE最大值')
    gross_profit_ratio_min: Optional[float] = Field(None, description='毛利率最小值')
    gross_profit_ratio_max: Optional[float] = Field(None, description='毛利率最大值')
    net_profit_ratio_min: Optional[float] = Field(None, description='净利率最小值')
    net_profit_ratio_max: Optional[float] = Field(None, description='净利率最大值')
    net_profit_yoy_min: Optional[float] = Field(None, description='净利润增长率最小值')
    net_profit_yoy_max: Optional[float] = Field(None, description='净利润增长率最大值')
    revenue_yoy_min: Optional[float] = Field(None, description='营收增长率最小值')
    revenue_yoy_max: Optional[float] = Field(None, description='营收增长率最大值')
    debt_ratio_min: Optional[float] = Field(None, description='资产负债率最小值')
    debt_ratio_max: Optional[float] = Field(None, description='资产负债率最大值')


# ==================== 指数数据 ====================


class IndexDailyQuery(BaseModel):
    """指数日线查询"""
    symbol: Optional[str] = Field(None, description='指数代码')
    start_date: Optional[str] = Field(None, description='开始日期 YYYY-MM-DD')
    end_date: Optional[str] = Field(None, description='结束日期 YYYY-MM-DD')
    page_num: int = Field(default=1, ge=1, description='页码')
    page_size: int = Field(default=50, ge=1, le=200, description='每页条数')


class IndexConstituentQuery(BaseModel):
    """指数成分股查询"""
    index_symbol: str = Field(..., description='指数代码')
    page_num: int = Field(default=1, ge=1, description='页码')
    page_size: int = Field(default=100, ge=1, le=500, description='每页条数')


class IndexDailyResponse(BaseModel):
    """指数日线响应"""
    symbol: str
    name: Optional[str]
    trade_date: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    preclose: Optional[float]
    volume: Optional[float]
    amount: Optional[float]
    pct_chg: Optional[float]

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    class Config:
        from_attributes = True


class IndexConstituentResponse(BaseModel):
    """指数成分股响应"""
    index_symbol: str
    constituent_symbol: str
    update_date: Optional[str]

    @field_validator('update_date', mode='before')
    @classmethod
    def validate_update_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    class Config:
        from_attributes = True


class LivePriceRequest(BaseModel):
    """实盘价格请求"""
    symbols: List[str] = Field(..., description='股票代码列表', max_length=50)


# ==================== 板块/ETF数据 ====================


class BoardInfoCreate(BaseModel):
    """板块/ETF信息-创建"""
    code: str = Field(..., description='板块/ETF代码')
    name: str = Field(..., description='板块/ETF名称')
    category: str = Field(..., description='类型: industry/concept/etf')
    exchange: Optional[str] = Field(None, description='交易所')
    source: Optional[str] = Field(None, description='数据来源')


class BoardInfoResponse(BaseModel):
    """板块/ETF信息-响应"""
    code: str
    name: str
    category: str
    exchange: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


class BoardInfoQuery(BaseModel):
    """板块/ETF信息-分页查询"""
    page_num: int = Field(default=1, ge=1, description='页码')
    page_size: int = Field(default=50, ge=1, le=500, description='每页条数')
    category: Optional[str] = Field(None, description='类型过滤: industry/concept/etf')
    keyword: Optional[str] = Field(None, description='名称模糊搜索')
    trade_date: Optional[str] = Field(None, description='指定交易日 YYYY-MM-DD，不传则取最新')


class BoardDailyQuery(BaseModel):
    """板块日线-分页查询"""
    code: str = Field(..., description='板块/ETF代码')
    page_num: int = Field(default=1, ge=1, description='页码')
    page_size: int = Field(default=50, ge=1, le=500, description='每页条数')
    start_date: Optional[str] = Field(None, description='开始日期 YYYY-MM-DD')
    end_date: Optional[str] = Field(None, description='结束日期 YYYY-MM-DD')


class BoardConstituentCreate(BaseModel):
    """板块成分股-创建"""
    board_code: str = Field(..., description='板块/ETF代码')
    constituent_symbol: str = Field(..., description='成分股代码')
    name: Optional[str] = Field(None, description='成分股名称')
    update_date: Optional[date] = Field(None, description='更新日期')


class BoardConstituentResponse(BaseModel):
    """板块成分股-响应"""
    board_code: str
    constituent_symbol: str
    update_date: Optional[str] = None

    @field_validator('update_date', mode='before')
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    class Config:
        from_attributes = True


class BoardDailyCreate(BaseModel):
    """板块/ETF日线-创建"""
    code: str = Field(..., description='板块/ETF代码')
    trade_date: str = Field(..., description='交易日期')
    open: Optional[float] = Field(None, description='开盘价')
    high: Optional[float] = Field(None, description='最高价')
    low: Optional[float] = Field(None, description='最低价')
    close: Optional[float] = Field(None, description='收盘价')
    volume: Optional[float] = Field(None, description='成交量')
    amount: Optional[float] = Field(None, description='成交额')
    pct_chg: Optional[float] = Field(None, description='涨跌幅')


class BoardDailyResponse(BaseModel):
    """板块/ETF日线-响应"""
    id: int
    code: str
    trade_date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    pct_chg: Optional[float] = None

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_trade_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    class Config:
        from_attributes = True


class BoardDailyQuery(BaseModel):
    """板块/ETF日线-分页查询"""
    code: str = Field(..., description='板块/ETF代码')
    start_date: Optional[str] = Field(None, description='开始日期 YYYY-MM-DD')
    end_date: Optional[str] = Field(None, description='结束日期 YYYY-MM-DD')
    page_num: int = Field(default=1, ge=1, description='页码')
    page_size: int = Field(default=100, ge=1, le=1000, description='每页条数')


# ==================== 同步任务链 ====================


class PipelineStepCreate(BaseModel):
    """任务链步骤-创建"""
    name: str = Field(..., description='步骤名称')
    job_type: str = Field(..., description='任务类型')
    trade_date: Optional[str] = Field(None, description='关联交易日')
    skip_on_fail: bool = Field(default=False, description='失败时是否跳过继续')


class PipelineCreate(BaseModel):
    """同步任务链-创建"""
    chain_type: str = Field(..., description='预设链类型: daily / full / board')
    trade_date: Optional[str] = Field(None, description='交易日 YYYY-MM-DD')
    steps: Optional[List[PipelineStepCreate]] = Field(None, description='自定义步骤列表')


class PipelineStepResponse(BaseModel):
    """任务链步骤-响应"""
    name: str
    job_type: str
    status: str
    trade_date: Optional[str] = None
    task_id: Optional[str] = None
    log_id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    skip_on_fail: bool = False


class PipelineResponse(BaseModel):
    """同步任务链-响应"""
    pipeline_id: str
    chain_type: str
    status: str
    trade_date: Optional[str] = None
    steps: List[PipelineStepResponse] = Field(default_factory=list)
    started_at: str
    finished_at: Optional[str] = None
    error: Optional[str] = None


# ==================== 系统日志 ====================


class SystemErrorLogCreate(BaseModel):
    """系统错误日志-创建"""
    level: str = Field(default='error', description='级别: error / warning / critical')
    source: str = Field(..., description='来源模块')
    trace_id: Optional[str] = Field(None, description='关联ID')
    message: str = Field(..., description='错误消息')
    detail: Optional[str] = Field(None, description='详细内容')


class SystemErrorLogResponse(BaseModel):
    """系统错误日志-响应"""
    id: int
    level: str
    source: str
    trace_id: Optional[str] = None
    message: str
    detail: Optional[str] = None
    created_at: str

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class SystemErrorLogQuery(BaseModel):
    """系统错误日志-查询"""
    page_num: int = Field(default=1, description='页码')
    page_size: int = Field(default=10, description='每页条数')
    level: Optional[str] = Field(None, description='级别')
    source: Optional[str] = Field(None, description='来源模块')
    days: Optional[int] = Field(None, description='最近N天')


class SystemOperationLogCreate(BaseModel):
    """系统操作日志-创建"""
    operation_type: str = Field(..., description='操作类型')
    operator: Optional[str] = Field(None, description='操作人')
    target_type: Optional[str] = Field(None, description='操作对象类型')
    target_id: Optional[str] = Field(None, description='对象标识')
    detail: Optional[str] = Field(None, description='操作详情')
    result: Optional[str] = Field(None, description='结果: success / failed')


class SystemOperationLogResponse(BaseModel):
    """系统操作日志-响应"""
    id: int
    operation_type: str
    operator: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    detail: Optional[str] = None
    result: Optional[str] = None
    created_at: str

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class SystemOperationLogQuery(BaseModel):
    """系统操作日志-查询"""
    page_num: int = Field(default=1, description='页码')
    page_size: int = Field(default=10, description='每页条数')
    operation_type: Optional[str] = Field(None, description='操作类型')
    days: Optional[int] = Field(None, description='最近N天')


class SystemLogOverviewResponse(BaseModel):
    """系统日志概览-响应"""
    today_error_count: int = Field(default=0, description='今日错误数')
    today_operation_count: int = Field(default=0, description='今日操作数')
    latest_sync_logs: List[SyncJobLogResponse] = Field(default_factory=list, description='各任务类型最新同步记录')


# ==================== 图库管理 ====================


class GalleryImageResponse(BaseModel):
    """图库图片-响应"""
    id: int
    filename: str
    original_name: str
    file_size: int
    mime_type: str
    url_path: str
    created_at: str

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


# ==================== 公司概况 ====================


class StockCompanyProfileCreate(BaseModel):
    """公司概况-创建/更新"""
    symbol: str = Field(..., description='股票代码')
    company_full_name: Optional[str] = Field(None, description='公司全称')
    english_name: Optional[str] = Field(None, description='英文名称')
    chairman: Optional[str] = Field(None, description='董事长')
    general_manager: Optional[str] = Field(None, description='总经理')
    secretary: Optional[str] = Field(None, description='董事会秘书')
    legal_representative: Optional[str] = Field(None, description='法人代表')
    phone: Optional[str] = Field(None, description='联系电话')
    email: Optional[str] = Field(None, description='电子邮箱')
    fax: Optional[str] = Field(None, description='传真')
    website: Optional[str] = Field(None, description='公司网址')
    office_address: Optional[str] = Field(None, description='办公地址')
    reg_address: Optional[str] = Field(None, description='注册地址')
    postcode: Optional[str] = Field(None, description='邮政编码')
    reg_capital: Optional[str] = Field(None, description='注册资本')
    employees: Optional[int] = Field(None, description='员工人数')
    founded_date: Optional[str] = Field(None, description='成立日期')
    company_profile: Optional[str] = Field(None, description='公司简介')
    business_scope: Optional[str] = Field(None, description='经营范围')
    industry_detail: Optional[str] = Field(None, description='所属证监会行业')
    exchange: Optional[str] = Field(None, description='所属交易所')


class StockCompanyProfileResponse(BaseModel):
    """公司概况-响应"""
    symbol: str
    company_full_name: Optional[str] = None
    english_name: Optional[str] = None
    chairman: Optional[str] = None
    general_manager: Optional[str] = None
    secretary: Optional[str] = None
    legal_representative: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    office_address: Optional[str] = None
    reg_address: Optional[str] = None
    postcode: Optional[str] = None
    reg_capital: Optional[str] = None
    employees: Optional[int] = None
    founded_date: Optional[str] = None
    company_profile: Optional[str] = None
    business_scope: Optional[str] = None
    industry_detail: Optional[str] = None
    exchange: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator('updated_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


# ==================== 访客日志 ====================


class VisitorLogTrack(BaseModel):
    """访客日志-前端上报"""
    path: Optional[str] = Field(None, description='访问路径')
    screen_resolution: Optional[str] = Field(None, description='屏幕分辨率')
    language: Optional[str] = Field(None, description='浏览器语言')
    timezone: Optional[str] = Field(None, description='时区')
    platform: Optional[str] = Field(None, description='操作系统平台')
    referrer: Optional[str] = Field(None, description='来源页面')


class VisitorLogResponse(BaseModel):
    """访客日志-响应"""
    id: int
    ip_address: str
    user_agent: Optional[str] = None
    path: str
    method: str
    referrer: Optional[str] = None
    screen_resolution: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    platform: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    created_at: str

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class VisitorLogQuery(BaseModel):
    """访客日志-查询"""
    page_num: int = Field(default=1, description='页码')
    page_size: int = Field(default=20, description='每页条数')
    ip_address: Optional[str] = Field(None, description='IP地址')
    days: Optional[int] = Field(None, description='最近N天')


# ==================== 回测 ====================


class BacktestCreate(BaseModel):
    """回测-创建"""
    start_date: str = Field(..., description='开始日期 YYYY-MM-DD')
    end_date: Optional[str] = Field(None, description='结束日期 YYYY-MM-DD（自动运行用）')
    initial_capital: Optional[float] = Field(default=40000, description='初始资金')
    ai_model: Optional[str] = Field(default='deepseek-v4-pro', description='AI 模型')


class BacktestResponse(BaseModel):
    """回测-响应"""
    id: int
    start_date: str
    end_date: Optional[str] = None
    current_date: str
    initial_capital: float
    cash: float
    status: str
    total_market_value: float
    total_return_pct: float
    ai_model: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator('start_date', 'end_date', 'current_date', mode='before')
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class BacktestTradeAction(BaseModel):
    """回测-AI 交易动作"""
    symbol: str
    quantity: int


class BacktestDecisionOutput(BaseModel):
    """回测-AI 决策输出"""
    sell: List[BacktestTradeAction] = Field(default_factory=list)
    buy: List[BacktestTradeAction] = Field(default_factory=list)
    reasoning: str = Field(default='', description='决策理由')


class BacktestTradeResponse(BaseModel):
    """回测交易记录-响应"""
    id: int
    run_id: int
    symbol: str
    name: Optional[str] = None
    trade_type: str
    trade_date: str
    price: float
    quantity: int
    amount: float
    fee: Optional[float] = 0
    created_at: Optional[str] = None

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class BacktestSnapshotResponse(BaseModel):
    """回测每日快照-响应"""
    id: int
    run_id: int
    trade_date: str
    cash: float
    total_market_value: float
    total_asset: float
    daily_pnl: float
    cumulative_pnl: float
    unrealized_pnl: float
    created_at: Optional[str] = None

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class BacktestDecisionLogResponse(BaseModel):
    """回测 AI 决策日志-响应"""
    id: int
    run_id: int
    trade_date: str
    parsed_actions: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: Optional[str] = None

    @field_validator('trade_date', mode='before')
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d')
        return str(v)

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if hasattr(v, 'strftime'):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return str(v)

    class Config:
        from_attributes = True


class BacktestStepResponse(BaseModel):
    """回测-手动步进响应"""
    run: BacktestResponse
    snapshot: Optional[BacktestSnapshotResponse] = None
    trades: List[BacktestTradeResponse] = Field(default_factory=list)
    reasoning: str = Field(default='', description='AI 决策理由')
    pool: List[dict] = Field(default_factory=list, description='当日可买入池子')


class BacktestQuery(BaseModel):
    """回测-列表查询"""
    page_num: int = Field(default=1, ge=1, description='页码')
    page_size: int = Field(default=20, ge=1, le=100, description='每页条数')
    status: Optional[str] = Field(None, description='状态过滤')

