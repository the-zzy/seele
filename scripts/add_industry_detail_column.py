#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用应用配置连接数据库添加缺失字段"""

import sys
sys.path.insert(0, 'd:/seele/seele-backend')

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE stock_basic ADD COLUMN industry_detail VARCHAR(255) DEFAULT NULL AFTER industry;"))
    conn.commit()
    print('industry_detail 字段已添加')

    result = conn.execute(text("SHOW COLUMNS FROM stock_basic LIKE 'industry_detail';"))
    row = result.fetchone()
    print(row)
