#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印 mainwave-picker 生成的 SQL"""

import sys
sys.path.insert(0, 'd:/seele/seele-backend')

from app.database import SessionLocal
from app import crud, schemas

db = SessionLocal()
query = schemas.MainwavePickerQuery(page_num=1, page_size=10)
query.market = '主板'
query.exclude_st = True
query.exclude_cyb = True
query.exclude_kcb = True

# 直接调用内部函数生成查询
from datetime import date
trade_date = query.trade_date or date.today().strftime('%Y-%m-%d')
formatted_date = trade_date.replace('-', '')

from sqlalchemy import func, and_, or_
from app import models
from sqlalchemy.orm import load_only

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

q = (
    db.query(
        models.StockDaily,
        models.StockBasic.name.label('stock_name'),
        financial_q.c.net_profit,
    )
    .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
    .outerjoin(financial_q, models.StockDaily.symbol == financial_q.c.symbol)
    .filter(models.StockDaily.trade_date == formatted_date)
)

print(q.statement.compile(compile_kwargs={'literal_binds': True}))
db.close()
