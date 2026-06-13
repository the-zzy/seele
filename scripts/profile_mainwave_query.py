#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 mainwave-picker 基础查询耗时"""

import sys
import time
sys.path.insert(0, 'd:/seele/seele-backend')

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import load_only
from app.database import SessionLocal
from app import models

db = SessionLocal()
formatted_date = '20260612'

# 最新财务指标子查询
financial_subq = (
    db.query(
        models.StockFinancialIndicator.symbol,
        func.max(models.StockFinancialIndicator.report_date).label('max_report_date'),
    )
    .group_by(models.StockFinancialIndicator.symbol)
    .subquery()
)
financial_q = (
    db.query(
        models.StockFinancialIndicator.symbol,
        models.StockFinancialIndicator.net_profit,
        models.StockFinancialIndicator.net_profit_yoy,
        models.StockFinancialIndicator.roe,
    )
    .join(
        financial_subq,
        and_(
            models.StockFinancialIndicator.symbol == financial_subq.c.symbol,
            models.StockFinancialIndicator.report_date == financial_subq.c.max_report_date,
        ),
    )
    .subquery()
)

t0 = time.time()
base_q = (
    db.query(
        models.StockDaily,
        models.StockBasic.name.label('stock_name'),
        models.StockBasic.industry,
        models.StockBasic.market,
        models.StockBasic.area,
        models.StockBasic.float_market_cap,
        models.StockDailyIndicator.ma5,
        models.StockDailyIndicator.ma10,
        models.StockDailyIndicator.ma20,
        models.StockDailyIndicator.ma30,
        models.StockDailyIndicator.ma60,
        models.StockDailyIndicator.vol_ma5,
        models.StockDailyIndicator.vol_ma10,
        models.StockDailyIndicator.amount_ma5,
        models.StockDailyIndicator.amount_ma10,
        models.StockDailyIndicator.turnover_ma5,
        models.StockDailyIndicator.turnover_ma10,
        models.StockDailyIndicator.chg_5d,
        models.StockDailyIndicator.chg_10d,
        models.StockDailyIndicator.adx,
        financial_q.c.net_profit,
        financial_q.c.net_profit_yoy,
        financial_q.c.roe,
    )
    .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
    .outerjoin(
        models.StockDailyIndicator,
        and_(
            models.StockDaily.symbol == models.StockDailyIndicator.symbol,
            models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
        ),
    )
    .outerjoin(financial_q, models.StockDaily.symbol == financial_q.c.symbol)
    .filter(models.StockDaily.trade_date == formatted_date)
    .options(load_only(
        models.StockDaily.id,
        models.StockDaily.trade_date,
        models.StockDaily.symbol,
        models.StockDaily.open,
        models.StockDaily.high,
        models.StockDaily.low,
        models.StockDaily.close,
        models.StockDaily.volume,
        models.StockDaily.amount,
        models.StockDaily.amplitude,
        models.StockDaily.pct_chg,
        models.StockDaily.price_change,
        models.StockDaily.turnover,
    ))
)
rows = base_q.all()
t1 = time.time()
print(f'base query rows: {len(rows)}, elapsed: {t1-t0:.3f}s')

# 应用筛选
t0 = time.time()
picker_q = base_q.filter(
    models.StockBasic.market == '主板',
    models.StockBasic.name.notlike('%ST%'),
    models.StockBasic.symbol.notlike('300%'),
    models.StockBasic.symbol.notlike('301%'),
    models.StockBasic.symbol.notlike('688%'),
    models.StockBasic.symbol.notlike('689%'),
    or_(
        financial_q.c.net_profit.is_(None),
        financial_q.c.net_profit > 0,
    ),
    or_(
        models.StockFinancialIndicator.total_revenue.is_(None),
        models.StockFinancialIndicator.total_revenue > 0,
    ),
    models.StockDailyIndicator.ma5.isnot(None),
    models.StockDailyIndicator.ma5 > 0,
)
rows2 = picker_q.all()
t1 = time.time()
print(f'picker query rows: {len(rows2)}, elapsed: {t1-t0:.3f}s')

db.close()
