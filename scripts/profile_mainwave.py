#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 mainwave-picker 各阶段耗时"""

import sys
import time
sys.path.insert(0, 'd:/seele/seele-backend')

from app.database import SessionLocal
from app import crud, schemas

db = SessionLocal()
query = schemas.MainwavePickerQuery(page_num=1, page_size=10)
query.market = '主板'
query.exclude_st = True
query.exclude_cyb = True
query.exclude_kcb = True

t0 = time.time()
list_data, total, trade_date = crud.stock_basic_crud.get_mainwave_list(db, query)
t1 = time.time()
print(f'total: {total}, trade_date: {trade_date}, elapsed: {t1-t0:.3f}s')
db.close()
