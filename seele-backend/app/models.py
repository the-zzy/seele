"""
数据库模型模块
"""

from sqlalchemy import Column, Integer, String, Float, Numeric, Date, Text, UniqueConstraint, BigInteger, TIMESTAMP, Index, ForeignKey
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
    industry_detail = Column(String(100), comment="细分行业（证监会行业）")
    market = Column(String(20), comment="市场板块")
    float_market_cap = Column(Numeric(18, 4), comment="流通市值(亿元)")
    list_date = Column(Date, comment="上市日期")

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class StockDaily(Base):
    """股票日线数据表"""
    __tablename__ = "stock_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="股票代码")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    open = Column(Numeric(18, 4), comment="开盘价")
    high = Column(Numeric(18, 4), comment="最高价")
    low = Column(Numeric(18, 4), comment="最低价")
    close = Column(Numeric(18, 4), comment="收盘价")
    volume = Column(Numeric(18, 4), comment="成交量")
    amount = Column(Numeric(18, 4), comment="成交额")
    amplitude = Column(Numeric(18, 4), comment="振幅")
    pct_chg = Column(Numeric(18, 4), comment="涨跌幅")
    price_change = Column(Numeric(18, 4), comment="涨跌额")
    turnover = Column(Numeric(18, 4), comment="换手率")

    # 复合唯一索引 + 查询索引
    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_trade_date_symbol'),
        Index('idx_stock_daily_symbol_trade_date', 'symbol', 'trade_date'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class StockDailyIndicator(Base):
    """股票日线指标表（均线及平均值）"""
    __tablename__ = "stock_daily_indicator"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True, comment="股票代码")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    ma5 = Column(Numeric(18, 4), comment="5日均线")
    ma10 = Column(Numeric(18, 4), comment="10日均线")
    ma20 = Column(Numeric(18, 4), comment="20日均线")
    ma30 = Column(Numeric(18, 4), comment="30日均线")
    ma60 = Column(Numeric(18, 4), comment="60日均线")
    vol_ma5 = Column(BigInteger, comment="5日平均成交量（股）")
    vol_ma10 = Column(BigInteger, comment="10日平均成交量（股）")
    amount_ma5 = Column(BigInteger, comment="5日平均成交额")
    amount_ma10 = Column(BigInteger, comment="10日平均成交额")
    turnover_ma5 = Column(Numeric(18, 4), comment="5日平均换手率(%)")
    turnover_ma10 = Column(Numeric(18, 4), comment="10日平均换手率(%)")
    chg_5d = Column(Numeric(18, 4), comment="5日涨幅(%)")
    chg_10d = Column(Numeric(18, 4), comment="10日涨幅(%)")
    macd_dif = Column(Numeric(18, 4), comment="MACD DIF")
    macd_dea = Column(Numeric(18, 4), comment="MACD DEA")
    macd_hist = Column(Numeric(18, 4), comment="MACD 柱状图")
    rsi_6 = Column(Numeric(18, 4), comment="RSI 6日")
    rsi_12 = Column(Numeric(18, 4), comment="RSI 12日")
    rsi_24 = Column(Numeric(18, 4), comment="RSI 24日")
    kdj_k = Column(Numeric(18, 4), comment="KDJ K值")
    kdj_d = Column(Numeric(18, 4), comment="KDJ D值")
    kdj_j = Column(Numeric(18, 4), comment="KDJ J值")
    boll_upper = Column(Numeric(18, 4), comment="布林上轨")
    boll_middle = Column(Numeric(18, 4), comment="布林中轨")
    boll_lower = Column(Numeric(18, 4), comment="布林下轨")
    adx = Column(Numeric(18, 4), comment="ADX趋势强度")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        UniqueConstraint('symbol', 'trade_date', name='uq_indicator_symbol_date'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class PortfolioTrade(Base):
    """持仓交易记录表"""
    __tablename__ = 'portfolio_trade'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    trade_type = Column(String(10), nullable=False, comment='交易类型 BUY/SELL')
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    price = Column(Numeric(18, 4), nullable=False, comment='成交价格')
    quantity = Column(Integer, nullable=False, comment='成交股数')
    amount = Column(Numeric(18, 4), nullable=False, comment='成交金额')
    stamp_tax = Column(Numeric(18, 2), default=0, comment='印花税')
    transfer_fee = Column(Numeric(18, 2), default=0, comment='过户费')
    commission = Column(Numeric(18, 2), default=0, comment='券商佣金/手续费')
    dividend = Column(Numeric(18, 4), default=0, comment='分红金额')
    remark = Column(String(255), comment='备注')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class PortfolioPosition(Base):
    """持仓快照表：缓存当前持仓的实时计算结果"""
    __tablename__ = 'portfolio_position'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    quantity = Column(Integer, nullable=False, default=0, comment='持仓股数')
    avg_cost = Column(Numeric(18, 4), nullable=False, default=0, comment='平均成本')
    current_price = Column(Numeric(18, 4), comment='最新收盘价')
    market_value = Column(Numeric(18, 4), comment='市值')
    unrealized_pnl = Column(Numeric(18, 4), comment='浮动盈亏')
    unrealized_pnl_pct = Column(Numeric(18, 4), comment='浮动盈亏百分比')
    stop_loss_price = Column(Numeric(18, 4), comment='止损价')
    take_profit_price = Column(Numeric(18, 4), comment='止盈价')
    alert_triggered = Column(Integer, nullable=False, default=0, comment='是否已触发提醒 0/1')
    group = Column(String(50), default='default', comment='持仓分组（如 core, watch）')
    remark = Column(String(255), comment='备注')
    first_buy_date = Column(Date, comment='首次买入日期')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        UniqueConstraint('group', 'symbol', name='uq_portfolio_position_group_symbol'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class PortfolioClosed(Base):
    """清仓盈亏记录表"""
    __tablename__ = 'portfolio_closed'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    total_buy_amount = Column(Numeric(18, 4), nullable=False, comment='总买入金额')
    total_sell_amount = Column(Numeric(18, 4), nullable=False, comment='总卖出金额')
    total_quantity = Column(Integer, nullable=False, comment='总股数')
    avg_buy_price = Column(Numeric(18, 4), nullable=False, comment='平均买入价')
    avg_sell_price = Column(Numeric(18, 4), nullable=False, comment='平均卖出价')
    open_date = Column(Date, nullable=False, comment='首次买入日期')
    close_date = Column(Date, nullable=False, comment='清仓日期')
    realized_pnl = Column(Numeric(18, 4), nullable=False, comment='实现盈亏')
    pnl_pct = Column(Numeric(18, 4), nullable=False, comment='盈亏百分比')
    total_fee = Column(Numeric(18, 4), default=0, comment='总手续费')
    group = Column(String(50), default='default', comment='持仓分组')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class PortfolioDailyPosition(Base):
    """每日持仓明细表：记录每天每只股票的持仓状态"""
    __tablename__ = 'portfolio_daily_position'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    symbol = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    quantity = Column(Integer, nullable=False, default=0, comment='当日收盘持仓股数')
    avg_cost = Column(Numeric(18, 4), nullable=False, default=0, comment='平均成本')
    close_price = Column(Numeric(18, 4), comment='当日收盘价')
    market_value = Column(Numeric(18, 4), default=0, comment='当日市值')
    day_buy = Column(Numeric(18, 4), default=0, comment='当日买入金额')
    day_sell = Column(Numeric(18, 4), default=0, comment='当日卖出金额')
    unrealized_pnl = Column(Numeric(18, 4), default=0, comment='当日浮动盈亏')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_daily_position_date_symbol'),
        Index('idx_daily_position_symbol_trade_date', 'symbol', 'trade_date'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class PortfolioDailySummary(Base):
    """每日资产汇总表：记录每天的整体资产状态"""
    __tablename__ = 'portfolio_daily_summary'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, unique=True, index=True, comment='交易日期')
    total_invested = Column(Numeric(18, 4), default=0, comment='总投入成本')
    total_market_value = Column(Numeric(18, 4), default=0, comment='当日收盘总市值')
    daily_pnl = Column(Numeric(18, 4), default=0, comment='当日盈亏')
    cumulative_pnl = Column(Numeric(18, 4), default=0, comment='累计盈亏')
    realized_pnl = Column(Numeric(18, 4), default=0, comment='已实现盈亏')
    unrealized_pnl = Column(Numeric(18, 4), default=0, comment='浮动盈亏')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class PortfolioConfig(Base):
    """持仓配置表"""
    __tablename__ = 'portfolio_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    initial_capital = Column(Numeric(18, 4), nullable=False, default=35000.0, comment='初始资金')
    commission_rate = Column(Numeric(18, 6), nullable=False, default=0.000235, comment='佣金费率')
    stamp_tax_rate = Column(Numeric(18, 6), nullable=False, default=0.0005, comment='印花税税率')
    transfer_rate = Column(Numeric(18, 6), nullable=False, default=0.00001, comment='过户费费率')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class MarketSentimentDaily(Base):
    """每日市场情绪统计表"""
    __tablename__ = 'market_sentiment_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, unique=True, index=True, comment='交易日期')
    total_stocks = Column(Integer, nullable=False, default=0, comment='当日参与统计的总股票数')
    up_count = Column(Integer, nullable=False, default=0, comment='上涨家数')
    down_count = Column(Integer, nullable=False, default=0, comment='下跌家数')
    flat_count = Column(Integer, nullable=False, default=0, comment='平盘家数')
    avg_pct_chg = Column(Numeric(18, 4), comment='平均涨跌幅')
    strong_count = Column(Integer, nullable=False, default=0, comment='涨幅>=阈值的家数')
    strong_threshold = Column(Numeric(18, 4), nullable=False, default=2.0, comment='强势阈值%')
    strong_percent = Column(Numeric(18, 4), comment='强势占比%')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }



class StockFinancialIndicator(Base):
    """股票财务指标表（仅保留最新一期）"""
    __tablename__ = "stock_financial_indicator"

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }

    symbol = Column(String(20), primary_key=True, comment='股票代码')
    name = Column(String(100), comment='股票名称')
    report_date = Column(Date, comment='报告期')
    net_profit = Column(Numeric(18, 4), comment='净利润')
    net_profit_yoy = Column(Numeric(18, 4), comment='净利润同比增长率(%)')
    deduct_net_profit = Column(Numeric(18, 4), comment='扣非净利润')
    total_revenue = Column(Numeric(18, 4), comment='营业总收入')
    revenue_yoy = Column(Numeric(18, 4), comment='营收同比增长率(%)')
    gross_profit_ratio = Column(Numeric(18, 4), comment='销售毛利率(%)')
    net_profit_ratio = Column(Numeric(18, 4), comment='销售净利率(%)')
    roe = Column(Numeric(18, 4), comment='净资产收益率(%)')
    roe_diluted = Column(Numeric(18, 4), comment='净资产收益率-摊薄(%)')
    eps = Column(Numeric(18, 4), comment='基本每股收益')
    bps = Column(Numeric(18, 4), comment='每股净资产')
    ops_cash_flow_per_share = Column(Numeric(18, 4), comment='每股经营现金流')
    current_ratio = Column(Numeric(18, 4), comment='流动比率')
    quick_ratio = Column(Numeric(18, 4), comment='速动比率')
    debt_ratio = Column(Numeric(18, 4), comment='资产负债率(%)')
    total_assets = Column(Numeric(18, 4), comment='资产总计(万元)')
    total_equity = Column(Numeric(18, 4), comment='所有者权益合计(万元)')
    operate_cash_flow = Column(Numeric(18, 4), comment='经营活动现金流净额')
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
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class IndexDaily(Base):
    """指数日线数据表"""
    __tablename__ = 'index_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment='指数代码')
    name = Column(String(50), comment='指数名称')
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    open = Column(Numeric(18, 4), comment='开盘价')
    high = Column(Numeric(18, 4), comment='最高价')
    low = Column(Numeric(18, 4), comment='最低价')
    close = Column(Numeric(18, 4), comment='收盘价')
    preclose = Column(Numeric(18, 4), comment='前收盘价')
    volume = Column(Numeric(18, 4), comment='成交量')
    amount = Column(Numeric(18, 4), comment='成交额')
    pct_chg = Column(Numeric(18, 4), comment='涨跌幅')

    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_index_daily_date_symbol'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
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
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class BoardInfo(Base):
    """板块/ETF基础信息表"""
    __tablename__ = 'board_info'

    code = Column(String(20), primary_key=True, comment='板块/ETF代码')
    name = Column(String(100), nullable=False, comment='板块/ETF名称')
    category = Column(String(20), nullable=False, comment='类型: industry/concept/etf')
    exchange = Column(String(10), comment='交易所')
    source = Column(String(20), comment='数据来源')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class BoardConstituent(Base):
    """板块/ETF成分股映射表"""
    __tablename__ = 'board_constituent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    board_code = Column(String(20), nullable=False, index=True, comment='板块/ETF代码')
    constituent_symbol = Column(String(20), nullable=False, index=True, comment='成分股代码')
    name = Column(String(100), comment='成分股名称')
    update_date = Column(Date, comment='更新日期')

    __table_args__ = (
        UniqueConstraint('board_code', 'constituent_symbol', name='uq_board_constituent'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class BoardDaily(Base):
    """板块/ETF日线数据表"""
    __tablename__ = 'board_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, index=True, comment='板块/ETF代码')
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    open = Column(Numeric(18, 4), comment='开盘价')
    high = Column(Numeric(18, 4), comment='最高价')
    low = Column(Numeric(18, 4), comment='最低价')
    close = Column(Numeric(18, 4), comment='收盘价')
    volume = Column(Numeric(18, 4), comment='成交量')
    amount = Column(Numeric(18, 4), comment='成交额')
    pct_chg = Column(Numeric(18, 4), comment='涨跌幅')

    __table_args__ = (
        UniqueConstraint('trade_date', 'code', name='uq_board_daily_date_code'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
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

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


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

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


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
        {'mysql_engine': 'InnoDB', 'mysql_collate': 'utf8mb4_unicode_ci', 'comment': '系统错误日志表'},
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
        {'mysql_engine': 'InnoDB', 'mysql_collate': 'utf8mb4_unicode_ci', 'comment': '系统操作日志表'},
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

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class StockCompanyProfile(Base):
    """股票公司概况表（来源：东方财富 F10）"""
    __tablename__ = 'stock_company_profile'

    symbol = Column(String(20), primary_key=True, comment='股票代码')
    company_full_name = Column(String(200), comment='公司全称')
    english_name = Column(String(200), comment='英文名称')
    chairman = Column(String(100), comment='董事长')
    general_manager = Column(String(100), comment='总经理')
    secretary = Column(String(100), comment='董事会秘书')
    legal_representative = Column(String(100), comment='法人代表')
    phone = Column(String(50), comment='联系电话')
    email = Column(String(100), comment='电子邮箱')
    fax = Column(String(50), comment='传真')
    website = Column(String(200), comment='公司网址')
    office_address = Column(String(500), comment='办公地址')
    reg_address = Column(String(500), comment='注册地址')
    postcode = Column(String(20), comment='邮政编码')
    reg_capital = Column(String(50), comment='注册资本')
    employees = Column(Integer, comment='员工人数')
    founded_date = Column(String(20), comment='成立日期')
    company_profile = Column(Text, comment='公司简介')
    business_scope = Column(Text, comment='经营范围')
    industry_detail = Column(String(100), comment='所属证监会行业')
    exchange = Column(String(50), comment='所属交易所')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class VisitorLog(Base):
    """访客日志表"""
    __tablename__ = 'visitor_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(64), nullable=False, index=True, comment='IP地址(匿名化网段)')
    user_agent = Column(String(1000), comment='浏览器User-Agent')
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

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class BacktestRun(Base):
    """回测运行表"""
    __tablename__ = 'backtest_run'

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(Date, nullable=False, comment='开始日期')
    end_date = Column(Date, nullable=True, comment='结束日期（自动运行用）')
    current_date = Column(Date, nullable=False, comment='当前已处理日期')
    initial_capital = Column(Numeric(18, 4), nullable=False, default=40000, comment='初始资金')
    cash = Column(Numeric(18, 4), nullable=False, default=40000, comment='剩余现金')
    status = Column(String(20), nullable=False, default='running', comment='状态 running/completed/failed')
    total_market_value = Column(Numeric(18, 4), nullable=False, default=0, comment='持仓总市值')
    total_return_pct = Column(Numeric(18, 4), nullable=False, default=0, comment='总收益率%')
    ai_model = Column(String(50), nullable=False, default='deepseek-v4-pro', comment='AI 模型')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class BacktestTrade(Base):
    """回测交易记录表"""
    __tablename__ = 'backtest_trade'

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey('backtest_run.id'), nullable=False, index=True, comment='回测ID')
    symbol = Column(String(20), nullable=False, comment='股票代码')
    name = Column(String(100), comment='股票名称')
    trade_type = Column(String(10), nullable=False, comment='交易类型 BUY/SELL')
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    price = Column(Numeric(18, 4), nullable=False, comment='成交价格')
    quantity = Column(Integer, nullable=False, comment='成交股数（100倍数）')
    amount = Column(Numeric(18, 4), nullable=False, comment='成交金额')
    fee = Column(Numeric(18, 4), default=0, comment='手续费')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class BacktestDailySnapshot(Base):
    """回测每日快照表"""
    __tablename__ = 'backtest_daily_snapshot'

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey('backtest_run.id'), nullable=False, index=True, comment='回测ID')
    trade_date = Column(Date, nullable=False, index=True, comment='交易日期')
    cash = Column(Numeric(18, 4), nullable=False, default=0, comment='现金')
    total_market_value = Column(Numeric(18, 4), nullable=False, default=0, comment='总市值')
    total_asset = Column(Numeric(18, 4), nullable=False, default=0, comment='总资产')
    daily_pnl = Column(Numeric(18, 4), nullable=False, default=0, comment='当日盈亏')
    cumulative_pnl = Column(Numeric(18, 4), nullable=False, default=0, comment='累计盈亏')
    unrealized_pnl = Column(Numeric(18, 4), nullable=False, default=0, comment='浮动盈亏')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')

    __table_args__ = (
        UniqueConstraint('run_id', 'trade_date', name='uq_backtest_snapshot_run_date'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class BacktestDecisionLog(Base):
    """回测 AI 决策日志表"""
    __tablename__ = 'backtest_decision_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey('backtest_run.id'), nullable=False, index=True, comment='回测ID')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    prompt_snapshot = Column(Text, comment='提示词快照')
    llm_raw_response = Column(Text, comment='LLM 原始响应')
    parsed_actions = Column(Text, comment='解析后的动作(JSON)')
    latency_ms = Column(Integer, comment='耗时(ms)')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')

    __table_args__ = {
        'mysql_collate': 'utf8mb4_unicode_ci',
    }


class BacktestTask(Base):
    """回测后台任务表（用于持久化任务状态、防并发、刷新后恢复轮询）"""
    __tablename__ = 'backtest_task'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True, comment='任务UUID')
    run_id = Column(Integer, ForeignKey('backtest_run.id'), nullable=True, index=True, comment='回测ID')
    status = Column(String(20), nullable=False, default='running', comment='状态 running/success/failed')
    result_json = Column(Text, nullable=True, comment='任务结果JSON')
    error = Column(Text, nullable=True, comment='错误信息')
    progress_current = Column(Integer, nullable=True, comment='进度当前值')
    progress_total = Column(Integer, nullable=True, comment='进度总数')
    started_at = Column(TIMESTAMP, server_default=func.now(), comment='开始时间')
    finished_at = Column(TIMESTAMP, nullable=True, comment='结束时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    __table_args__ = (
        Index('idx_backtest_task_run_status', 'run_id', 'status'),
        {'mysql_collate': 'utf8mb4_unicode_ci'},
    )
