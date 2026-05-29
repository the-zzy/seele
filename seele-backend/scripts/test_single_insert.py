import os
import sys
import baostock as bs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app import models
from sqlalchemy.dialects.mysql import insert

def main():
    db = SessionLocal()
    try:
        # 删除 000001 2026-05-21 的数据
        db.query(models.StockDaily).filter(
            models.StockDaily.symbol == '000001',
            models.StockDaily.trade_date == '20260521'
        ).delete()
        db.commit()

        # 拉取单条数据
        bs.login()
        rs = bs.query_history_k_data_plus(
            'sz.000001',
            'date,code,open,high,low,close,preclose,volume,amount,turn,pctChg',
            start_date='2026-05-21', end_date='2026-05-21',
            frequency='d', adjustflag='3'
        )
        row = None
        while rs.next():
            row = rs.get_row_data()
        bs.logout()

        print('raw row:', row)
        raw_turn = row[9]
        turnover = float(raw_turn) / 100 if raw_turn else None
        print('calculated turnover:', turnover)

        record = {
            'trade_date': row[0].replace('-', ''),
            'symbol': '000001',
            'open': float(row[2]),
            'high': float(row[3]),
            'low': float(row[4]),
            'close': float(row[5]),
            'volume': int(float(row[7])),
            'amount': float(row[8]),
            'amplitude': 0.0,
            'pct_chg': float(row[10]),
            'price_change': 0.0,
            'turnover': turnover,
        }
        print('record turnover:', record['turnover'])

        # 插入
        upsert_stmt = insert(models.StockDaily).values([record])
        update_dict = {
            k: upsert_stmt.inserted[k]
            for k in upsert_stmt.inserted.keys()
            if k not in ('id', 'trade_date', 'symbol')
        }
        upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
        db.execute(upsert_stmt)
        db.commit()

        # 查询
        result = db.query(models.StockDaily.turnover).filter(
            models.StockDaily.symbol == '000001',
            models.StockDaily.trade_date == '20260521'
        ).scalar()
        print('db turnover:', result)
        print('db turnover repr:', repr(result))

    finally:
        db.close()

if __name__ == '__main__':
    main()
