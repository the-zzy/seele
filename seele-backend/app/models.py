"""
数据库模型模块
"""

from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint, BigInteger, TIMESTAMP
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

    # 复合唯一索引
    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_trade_date_symbol'),
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


class PortfolioConfig(Base):
    """持仓配置表"""
    __tablename__ = 'portfolio_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    initial_capital = Column(Float, nullable=False, default=35000.0, comment='初始资金')
    created_at = Column(TIMESTAMP, server_default=func.now(), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class StockFinancialIndicator(Base):
    """股票财务指标表（仅保留最新一期）"""
    __tablename__ = 'stock_financial_indicator'

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