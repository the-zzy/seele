"""
数据库模型模块
"""

from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint, BigInteger, TIMESTAMP, Index
from sqlalchemy.sql import func

from app.database import Base


class StockBasic(Base):
    """股票基础信息表"""
    __tablename__ = "stock_basic"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True, comment="股票代码")
    name = Column(String(100), nullable=False, comment="股票名称")
    area = Column(String(50), comment="所在地区")
    industry = Column(String(50), comment="所属行业")
    market = Column(String(20), comment="市场板块")
    float_market_cap = Column(Float, comment="流通市值(亿元)")
    list_date = Column(Date, comment="上市日期")


class StockDaily(Base):
    """股票日线数据表"""
    __tablename__ = "stock_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="股票代码")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    open = Column(Float, comment="开盘价")
    high = Column(Float, comment="最高价")
    low = Column(Float, comment="最低价")
    close = Column(Float, comment="收盘价")
    volume = Column(Float, comment="成交量")
    amount = Column(Float, comment="成交额")
    amplitude = Column(Float, comment="振幅")
    pct_chg = Column(Float, comment="涨跌幅")
    price_change = Column(Float, comment="涨跌额")
    turnover = Column(Float, comment="换手率")

    # 复合唯一索引 + 查询索引
    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_trade_date_symbol'),
        Index('idx_stock_daily_symbol_trade_date', 'symbol', 'trade_date'),
    )


class StockDailyIndicator(Base):
    """股票日线指标表（均线及平均值）"""
    __tablename__ = "stock_daily_indicator"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True, comment="股票代码")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    ma5 = Column(Float, comment="5日均线")
    ma10 = Column(Float, comment="10日均线")
    ma20 = Column(Float, comment="20日均线")
    ma30 = Column(Float, comment="30日均线")
    ma60 = Column(Float, comment="60日均线")
    vol_ma5 = Column(BigInteger, comment="5日平均成交量（股）")
    vol_ma10 = Column(BigInteger, comment="10日平均成交量（股）")
    amount_ma5 = Column(BigInteger, comment="5日平均成交额")
    amount_ma10 = Column(BigInteger, comment="10日平均成交额")
    turnover_ma5 = Column(Float, comment="5日平均换手率(%)")
    turnover_ma10 = Column(Float, comment="10日平均换手率(%)")
    chg_5d = Column(Float, comment="5日涨幅(%)")
    chg_10d = Column(Float, comment="10日涨幅(%)")
    macd_dif = Column(Float, comment="MACD DIF")
    macd_dea = Column(Float, comment="MACD DEA")
    macd_hist = Column(Float, comment="MACD 柱状图")
    rsi_6 = Column(Float, comment="RSI 6日")
    rsi_12 = Column(Float, comment="RSI 12日")
    rsi_24 = Column(Float, comment="RSI 24日")
    kdj_k = Column(Float, comment="KDJ K值")
    kdj_d = Column(Float, comment="KDJ D值")
    kdj_j = Column(Float, comment="KDJ J值")
    boll_upper = Column(Float, comment="布林上轨")
    boll_middle = Column(Float, comment="布林中轨")
    boll_lower = Column(Float, comment="布林下轨")
    adx = Column(Float, comment="ADX趋势强度")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        UniqueConstraint('symbol', 'trade_date', name='uq_indicator_symbol_date'),
    )


class PortfolioTrade(Base):
    """持仓交易记录表"""
    __tablename__ = 'portfolio_trade'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    trade_type = Column(String(10), nullable=False, comment='交易类型 BUY/SELL')
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    price = Column(Float, nullable=False, comment='成交价格')
    quantity = Column(Integer, nullable=False, comment='成交股数')
    amount = Column(Float, nullable=False, comment='成交金额')
    fee = Column(Float, default=0, comment='交易手续费')
    dividend = Column(Float, default=0, comment='分红金额')
    remark = Column(String(255), comment='备注')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class PortfolioPosition(Base):
    """持仓快照表：缓存当前持仓的实时计算结果"""
    __tablename__ = 'portfolio_position'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    quantity = Column(Integer, nullable=False, default=0, comment='持仓股数')
    avg_cost = Column(Float, nullable=False, default=0, comment='平均成本')
    current_price = Column(Float, comment='最新收盘价')
    market_value = Column(Float, comment='市值')
    unrealized_pnl = Column(Float, comment='浮动盈亏')
    unrealized_pnl_pct = Column(Float, comment='浮动盈亏百分比')
    stop_loss_price = Column(Float, comment='止损价')
    take_profit_price = Column(Float, comment='止盈价')
    alert_triggered = Column(Integer, nullable=False, default=0, comment='是否已触发提醒 0/1')
    group = Column(String(50), default='default', comment='持仓分组（如 core, watch）')
    remark = Column(String(255), comment='备注')
    first_buy_date = Column(Date, comment='首次买入日期')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        UniqueConstraint('group', 'symbol', name='uq_portfolio_position_group_symbol'),
    )


class PortfolioClosed(Base):
    """清仓盈亏记录表"""
    __tablename__ = 'portfolio_closed'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    total_buy_amount = Column(Float, nullable=False, comment='总买入金额')
    total_sell_amount = Column(Float, nullable=False, comment='总卖出金额')
    total_quantity = Column(Integer, nullable=False, comment='总股数')
    avg_buy_price = Column(Float, nullable=False, comment='平均买入价')
    avg_sell_price = Column(Float, nullable=False, comment='平均卖出价')
    open_date = Column(Date, nullable=False, comment='首次买入日期')
    close_date = Column(Date, nullable=False, comment='清仓日期')
    realized_pnl = Column(Float, nullable=False, comment='实现盈亏')
    pnl_pct = Column(Float, nullable=False, comment='盈亏百分比')
    total_fee = Column(Float, default=0, comment='总手续费')
    group = Column(String(50), default='default', comment='持仓分组')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class PortfolioDailyPosition(Base):
    """每日持仓明细表：记录每天每只股票的持仓状态"""
    __tablename__ = 'portfolio_daily_position'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    quantity = Column(Integer, nullable=False, default=0, comment='当日收盘持仓股数')
    avg_cost = Column(Float, nullable=False, default=0, comment='平均成本')
    close_price = Column(Float, comment='当日收盘价')
    market_value = Column(Float, default=0, comment='当日市值')
    day_buy = Column(Float, default=0, comment='当日买入金额')
    day_sell = Column(Float, default=0, comment='当日卖出金额')
    unrealized_pnl = Column(Float, default=0, comment='当日浮动盈亏')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_daily_position_date_symbol'),
        Index('idx_daily_position_symbol_trade_date', 'symbol', 'trade_date'),
    )


class PortfolioDailySummary(Base):
    """每日资产汇总表：记录每天的整体资产状态"""
    __tablename__ = 'portfolio_daily_summary'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, unique=True, index=True, comment='交易日期')
    total_invested = Column(Float, default=0, comment='总投入成本')
    total_market_value = Column(Float, default=0, comment='当日收盘总市值')
    daily_pnl = Column(Float, default=0, comment='当日盈亏')
    cumulative_pnl = Column(Float, default=0, comment='累计盈亏')
    realized_pnl = Column(Float, default=0, comment='已实现盈亏')
    unrealized_pnl = Column(Float, default=0, comment='浮动盈亏')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class PortfolioConfig(Base):
    """持仓配置表"""
    __tablename__ = 'portfolio_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    initial_capital = Column(Float, nullable=False, default=35000.0, comment='初始资金')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class MarketSentimentDaily(Base):
    """每日市场情绪统计表"""
    __tablename__ = 'market_sentiment_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, unique=True, index=True, comment='交易日期')
    total_stocks = Column(Integer, nullable=False, default=0, comment='当日参与统计的总股票数')
    up_count = Column(Integer, nullable=False, default=0, comment='上涨家数')
    down_count = Column(Integer, nullable=False, default=0, comment='下跌家数')
    flat_count = Column(Integer, nullable=False, default=0, comment='平盘家数')
    avg_pct_chg = Column(Float, comment='平均涨跌幅')
    strong_count = Column(Integer, nullable=False, default=0, comment='涨幅>=阈值的家数')
    strong_threshold = Column(Float, nullable=False, default=2.0, comment='强势阈值%')
    strong_percent = Column(Float, comment='强势占比%')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class IndustrySentimentDaily(Base):
    """每日板块情绪统计表"""
    __tablename__ = 'industry_sentiment_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    industry = Column(String(50), nullable=False, comment='行业名称')
    stock_count = Column(Integer, nullable=False, default=0, comment='板块内股票总数')
    up_count = Column(Integer, default=0, comment='上涨家数')
    down_count = Column(Integer, default=0, comment='下跌家数')
    flat_count = Column(Integer, default=0, comment='平盘家数')
    avg_pct_chg = Column(Float, comment='板块平均涨跌幅')
    max_pct_chg = Column(Float, comment='板块最大涨幅')
    min_pct_chg = Column(Float, comment='板块最大跌幅')
    strong_count = Column(Integer, default=0, comment='强势家数（涨幅>=阈值）')
    amount_sum = Column(Float, comment='板块总成交额')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        UniqueConstraint('trade_date', 'industry', name='uq_industry_sentiment_date_industry'),
    )


class StockFinancialIndicator(Base):
    """股票财务指标表（仅保留最新一期）"""
    __tablename__ = "stock_financial_indicator"

    __table_args__ = {
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    symbol = Column(String(20), primary_key=True, comment='股票代码')
    name = Column(String(100), comment='股票名称')
    report_date = Column(Date, comment='报告期')
    net_profit = Column(Float, comment='净利润')
    net_profit_yoy = Column(Float, comment='净利润同比增长率(%)')
    deduct_net_profit = Column(Float, comment='扣非净利润')
    total_revenue = Column(Float, comment='营业总收入')
    revenue_yoy = Column(Float, comment='营收同比增长率(%)')
    gross_profit_ratio = Column(Float, comment='销售毛利率(%)')
    net_profit_ratio = Column(Float, comment='销售净利率(%)')
    roe = Column(Float, comment='净资产收益率(%)')
    roe_diluted = Column(Float, comment='净资产收益率-摊薄(%)')
    eps = Column(Float, comment='基本每股收益')
    bps = Column(Float, comment='每股净资产')
    ops_cash_flow_per_share = Column(Float, comment='每股经营现金流')
    current_ratio = Column(Float, comment='流动比率')
    quick_ratio = Column(Float, comment='速动比率')
    debt_ratio = Column(Float, comment='资产负债率(%)')
    total_assets = Column(Float, comment='资产总计(万元)')
    total_equity = Column(Float, comment='所有者权益合计(万元)')
    operate_cash_flow = Column(Float, comment='经营活动现金流净额')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class StockSuspension(Base):
    """股票停牌信息表"""
    __tablename__ = 'stock_suspension'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), comment='股票名称')
    suspend_date = Column(Date, nullable=False, index=True, comment='停牌日期')
    resume_date = Column(Date, comment='复牌日期')
    reason = Column(String(255), comment='停牌原因')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        UniqueConstraint('symbol', 'suspend_date', name='uq_suspension_symbol_date'),
    )


class IndexDaily(Base):
    """指数日线数据表"""
    __tablename__ = 'index_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='指数代码')
    name = Column(String(50), comment='指数名称')
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    open = Column(Float, comment='开盘价')
    high = Column(Float, comment='最高价')
    low = Column(Float, comment='最低价')
    close = Column(Float, comment='收盘价')
    preclose = Column(Float, comment='前收盘价')
    volume = Column(Float, comment='成交量')
    amount = Column(Float, comment='成交额')
    pct_chg = Column(Float, comment='涨跌幅')

    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_index_daily_date_symbol'),
    )


class IndexConstituent(Base):
    """指数成分股映射表"""
    __tablename__ = 'index_constituent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    index_symbol = Column(String(20), nullable=False, index=True, comment='指数代码')
    constituent_symbol = Column(String(20), nullable=False, index=True, comment='成分股代码')
    update_date = Column(Date, comment='成分股更新日期')

    __table_args__ = (
        UniqueConstraint('index_symbol', 'constituent_symbol', name='uq_index_constituent'),
    )


class BoardInfo(Base):
    """板块/ETF基础信息表"""
    __tablename__ = 'board_info'

    code = Column(String(20), primary_key=True, comment='板块/ETF代码')
    name = Column(String(100), nullable=False, comment='板块/ETF名称')
    category = Column(String(20), nullable=False, comment='类型: industry/concept/etf')
    exchange = Column(String(10), comment='交易所')
    source = Column(String(20), comment='数据来源')


class BoardConstituent(Base):
    """板块/ETF成分股映射表"""
    __tablename__ = 'board_constituent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    board_code = Column(String(20), nullable=False, index=True, comment='板块/ETF代码')
    constituent_symbol = Column(String(20), nullable=False, index=True, comment='成分股代码')
    update_date = Column(Date, comment='更新日期')

    __table_args__ = (
        UniqueConstraint('board_code', 'constituent_symbol', name='uq_board_constituent'),
    )


class BoardDaily(Base):
    """板块/ETF日线数据表"""
    __tablename__ = 'board_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, index=True, comment='板块/ETF代码')
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    open = Column(Float, comment='开盘价')
    high = Column(Float, comment='最高价')
    low = Column(Float, comment='最低价')
    close = Column(Float, comment='收盘价')
    volume = Column(Float, comment='成交量')
    amount = Column(Float, comment='成交额')
    pct_chg = Column(Float, comment='涨跌幅')

    __table_args__ = (
        UniqueConstraint('trade_date', 'code', name='uq_board_daily_date_code'),
    )


class SyncJobLog(Base):
    """同步任务执行日志表"""
    __tablename__ = 'sync_job_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False, index=True, comment='任务类型: stock_basic / daily / financial / indicator')
    trigger_type = Column(String(20), nullable=False, default='scheduled', comment='触发方式: scheduled / manual')
    status = Column(String(20), nullable=False, default='running', comment='状态: running / success / failed / skipped')
    started_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, index=True, comment='开始时间')
    ended_at = Column(TIMESTAMP, nullable=True, comment='结束时间')
    duration_seconds = Column(Integer, nullable=True, comment='执行耗时(秒)')
    success_count = Column(Integer, nullable=True, default=0, comment='成功处理数')
    failed_count = Column(Integer, nullable=True, default=0, comment='失败/异常数')
    skipped_count = Column(Integer, nullable=True, default=0, comment='跳过数')
    total_count = Column(Integer, nullable=True, default=0, comment='总处理数')
    trade_date = Column(String(8), nullable=True, comment='关联交易日')
    error_message = Column(String(2000), nullable=True, comment='错误信息')
    extra_info = Column(String(1000), nullable=True, comment='额外信息')


class TradeCalendar(Base):
    """交易日历表"""
    __tablename__ = 'trade_calendar'

    trade_date = Column(Date, primary_key=True, nullable=False, comment='日期')
    is_trading_day = Column(Integer, nullable=False, default=1, comment='是否交易日: 1是 0否')
    year = Column(Integer, nullable=False, index=True, comment='年份')
    quarter = Column(Integer, nullable=False, comment='季度')
    month = Column(Integer, nullable=False, comment='月份')
    week = Column(Integer, nullable=False, comment='周数')
    weekday = Column(Integer, nullable=False, comment='星期几: 0=周一 6=周日')
    is_weekend = Column(Integer, nullable=False, default=0, comment='是否周末: 1是 0否')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')


class SystemErrorLog(Base):
    """系统错误日志表"""
    __tablename__ = 'system_error_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False, default='error', index=True, comment='级别: error / warning / critical')
    source = Column(String(100), nullable=False, index=True, comment='来源模块')
    trace_id = Column(String(50), nullable=True, comment='关联ID: task_id / log_id / pipeline_id')
    message = Column(String(1000), nullable=False, comment='错误消息')
    detail = Column(String(4000), nullable=True, comment='详细内容: traceback等')
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, index=True, comment='创建时间')

    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'comment': '系统错误日志表'},
    )


class SystemOperationLog(Base):
    """系统操作日志表"""
    __tablename__ = 'system_operation_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_type = Column(String(50), nullable=False, index=True, comment='操作类型: sync_manual / pipeline_start / pipeline_cancel / job_cancel / config_update')
    operator = Column(String(50), nullable=True, comment='操作人')
    target_type = Column(String(50), nullable=True, comment='操作对象类型: job / pipeline / stock / config')
    target_id = Column(String(100), nullable=True, comment='对象标识')
    detail = Column(String(1000), nullable=True, comment='操作详情')
    result = Column(String(20), nullable=True, comment='结果: success / failed')
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, index=True, comment='创建时间')

    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'comment': '系统操作日志表'},
    )


class GalleryImage(Base):
    """图库图片表"""
    __tablename__ = 'gallery_image'

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, comment='存储文件名')
    original_name = Column(String(255), nullable=False, comment='原始文件名')
    file_size = Column(Integer, nullable=False, comment='文件大小(字节)')
    mime_type = Column(String(50), nullable=False, comment='MIME类型')
    url_path = Column(String(500), nullable=False, comment='访问路径')
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, comment='创建时间')


class VisitorLog(Base):
    """访客日志表"""
    __tablename__ = 'visitor_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(64), nullable=False, index=True, comment='IP地址')
    user_agent = Column(String(500), comment='浏览器User-Agent')
    path = Column(String(255), nullable=False, comment='访问路径')
    method = Column(String(10), nullable=False, comment='HTTP方法')
    referrer = Column(String(500), comment='来源页面')
    screen_resolution = Column(String(20), comment='屏幕分辨率')
    language = Column(String(50), comment='浏览器语言')
    timezone = Column(String(50), comment='时区')
    platform = Column(String(50), comment='操作系统平台')
    country = Column(String(50), comment='国家/地区')
    city = Column(String(50), comment='城市')
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False, index=True, comment='访问时间')
