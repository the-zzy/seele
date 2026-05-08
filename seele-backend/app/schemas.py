"""
请求响应模式模块
"""

from datetime import date, datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator

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


class PctChgDistributionQuery(BaseModel):
    """涨幅分布统计-查询参数"""
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    threshold: float = Field(default=2.0, description="涨幅阈值，默认 2.0")
    amount_ma5_min: Optional[float] = Field(default=200000000.0, description="5日平均成交额最小值，默认2亿")
    amount_ma10_min: Optional[float] = Field(default=200000000.0, description="10日平均成交额最小值，默认2亿")
    turnover_ma5_min: Optional[float] = Field(default=2.0, description="5日平均换手率最小值，默认2%")
    turnover_ma10_min: Optional[float] = Field(default=2.0, description="10日平均换手率最小值，默认2%")


class BreakoutPickerQuery(BaseModel):
    """倍量突破选股-查询参数"""
    trade_date: str = Field(..., description="交易日期，格式 YYYY-MM-DD 或 YYYYMMDD")
    min_pct_chg: float = Field(default=3.0, description="最小涨幅，默认 3.0")
    max_pct_chg: float = Field(default=7.0, description="最大涨幅，默认 7.0")
    min_turnover: float = Field(default=2.0, description="最低换手率，默认 2.0")
    min_amount: float = Field(default=50000000.0, description="最低成交额，默认 50000000")
    exclude_st: bool = Field(default=True, description="排除 ST，默认 true")
    exclude_cyb: bool = Field(default=True, description="排除创业板，默认 true")
    exclude_kcb: bool = Field(default=True, description="排除科创板，默认 true")
    exclude_bse: bool = Field(default=True, description="排除北交所，默认 true")
    page_num: int = Field(default=1, description="页码，默认 1")
    page_size: int = Field(default=100, ge=1, le=100, description="每页条数，默认 100，最大 100")


class TrendPickerQuery(BaseModel):
    """趋势选股-查询参数"""
    trade_date: str = Field(..., description="交易日期，格式 YYYY-MM-DD 或 YYYYMMDD")
    min_pct_chg: float = Field(default=2.0, description="最小涨幅，默认 2.0")
    max_pct_chg: float = Field(default=8.0, description="最大涨幅，默认 8.0")
    min_turnover: float = Field(default=2.0, description="最低换手率，默认 2.0")
    min_amount: float = Field(default=200000000.0, description="最低成交额均值(10日)，默认 2亿")
    ma_alignment: bool = Field(default=True, description="均线多头排列，默认 true")
    macd_golden_cross: bool = Field(default=False, description="MACD金叉，默认 false")
    rsi_min: float = Field(default=40.0, description="RSI最小值，默认 40")
    rsi_max: float = Field(default=80.0, description="RSI最大值，默认 80")
    volume_ratio: float = Field(default=1.5, description="成交量/20日均量，默认 1.5")
    exclude_st: bool = Field(default=True, description="排除ST，默认 true")
    exclude_cyb: bool = Field(default=True, description="排除创业板，默认 true")
    exclude_kcb: bool = Field(default=True, description="排除科创板，默认 true")
    exclude_bse: bool = Field(default=True, description="排除北交所，默认 true")
    sort_field: str = Field(default="pct_chg", description="排序字段，默认 pct_chg")
    sort_order: str = Field(default="desc", description="排序方向，asc/desc，默认 desc")
    page_num: int = Field(default=1, description="页码，默认 1")
    page_size: int = Field(default=100, ge=1, le=100, description="每页条数，默认 100，最大 100")


class RangePickerQuery(BaseModel):
    """震荡选股-查询参数"""
    trade_date: str = Field(..., description="交易日期，格式 YYYY-MM-DD 或 YYYYMMDD")
    max_pct_chg_20d: float = Field(default=10.0, description="近20日最大涨幅，默认 10.0")
    min_amplitude_20d: float = Field(default=3.0, description="近20日平均振幅最小值，默认 3.0")
    bb_width_max: float = Field(default=0.08, description="布林带宽度最大值，默认 0.08")
    rsi_min: float = Field(default=35.0, description="RSI最小值，默认 35")
    rsi_max: float = Field(default=65.0, description="RSI最大值，默认 65")
    volume_shrink: bool = Field(default=True, description="近期缩量，默认 true")
    near_ma20: bool = Field(default=True, description="收盘价在MA20附近，默认 true")
    min_amount: float = Field(default=200000000.0, description="最低成交额均值(10日)，默认 2亿")
    exclude_st: bool = Field(default=True, description="排除ST，默认 true")
    exclude_cyb: bool = Field(default=True, description="排除创业板，默认 true")
    exclude_kcb: bool = Field(default=True, description="排除科创板，默认 true")
    exclude_bse: bool = Field(default=True, description="排除北交所，默认 true")
    sort_field: str = Field(default="bb_width", description="排序字段，默认 bb_width")
    sort_order: str = Field(default="asc", description="排序方向，asc/desc，默认 asc")
    page_num: int = Field(default=1, description="页码，默认 1")
    page_size: int = Field(default=100, ge=1, le=100, description="每页条数，默认 100，最大 100")


# ==================== 数据同步 ====================


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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

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


class PortfolioTradeQuery(BaseModel):
    """交易记录-查询"""
    page_num: int = Field(default=1, description='页码')
    page_size: int = Field(default=20, description='每页条数')
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


class StockFinancialIndicatorQuery(BaseModel):
    """财务指标-分页查询"""
    page_num: int = Field(default=1, description='页码')
    page_size: int = Field(default=20, description='每页条数')
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


class FinancialPickerQuery(BaseModel):
    """财务选股-查询参数"""
    roe_min: float = Field(default=15.0, description='ROE最小值，默认15')
    gross_profit_ratio_min: float = Field(default=30.0, description='毛利率最小值，默认30')
    net_profit_ratio_min: Optional[float] = Field(None, description='净利率最小值')
    net_profit_yoy_min: float = Field(default=20.0, description='净利润同比增长率最小值，默认20')
    revenue_yoy_min: float = Field(default=15.0, description='营收同比增长率最小值，默认15')
    debt_ratio_max: float = Field(default=60.0, description='资产负债率最大值，默认60')
    exclude_st: bool = Field(default=True, description='排除ST，默认true')
    exclude_cyb: bool = Field(default=True, description='排除创业板，默认true')
    exclude_kcb: bool = Field(default=True, description='排除科创板，默认true')
    exclude_bse: bool = Field(default=True, description='排除北交所，默认true')
    sort_field: str = Field(default='roe', description='排序字段，默认roe')
    sort_order: str = Field(default='desc', description='排序方向，asc/desc，默认desc')
    page_num: int = Field(default=1, description='页码，默认1')
    page_size: int = Field(default=100, ge=1, le=100, description='每页条数，默认100，最大100')


class MainwavePickerQuery(BaseModel):
    """主升浪选股-查询参数"""
    trade_date: str = Field(..., description='交易日期，格式 YYYY-MM-DD 或 YYYYMMDD')
    only_s_level: bool = Field(default=False, description='仅看硬核S级，默认false')
    exclude_st: bool = Field(default=True, description='排除ST，默认true')
    exclude_cyb: bool = Field(default=True, description='排除创业板，默认true')
    exclude_kcb: bool = Field(default=True, description='排除科创板，默认true')
    exclude_bse: bool = Field(default=True, description='排除北交所，默认true')
    sort_field: str = Field(default='level', description='排序字段，默认level')
    sort_order: str = Field(default='desc', description='排序方向，asc/desc，默认desc')
    page_num: int = Field(default=1, description='页码，默认1')
    page_size: int = Field(default=100, ge=1, le=100, description='每页条数，默认100，最大100')