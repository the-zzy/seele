#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""添加 stock_financial_indicator 复合索引优化 mainwave-picker 查询"""

import sys
sys.path.insert(0, 'd:/seele/seele-backend')

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    existing = conn.execute(text(
        "SELECT 1 FROM information_schema.STATISTICS "
        "WHERE table_schema = DATABASE() "
        "AND table_name = 'stock_financial_indicator' "
        "AND index_name = 'idx_financial_symbol_report_date';"
    )).fetchone()

    if existing:
        print('idx_financial_symbol_report_date 索引已存在')
    else:
        conn.execute(text(
            "CREATE INDEX idx_financial_symbol_report_date "
            "ON stock_financial_indicator(symbol, report_date);"
        ))
        conn.commit()
        print('idx_financial_symbol_report_date 索引已添加')

    result = conn.execute(text(
        "SHOW INDEX FROM stock_financial_indicator WHERE Key_name = 'idx_financial_symbol_report_date';"
    ))
    rows = result.fetchall()
    for row in rows:
        print(row)
