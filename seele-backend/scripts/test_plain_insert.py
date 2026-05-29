import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app import models

def main():
    db = SessionLocal()
    try:
        # 删除
        db.query(models.StockDaily).filter(
            models.StockDaily.symbol == '000001',
            models.StockDaily.trade_date == '20260521'
        ).delete()
        db.commit()

        # 直接 ORM 插入
        item = models.StockDaily(
            trade_date='20260521',
            symbol='000001',
            open=10.78,
            high=10.80,
            low=10.69,
            close=10.70,
            volume=111021108,
            amount=1194144111.5,
            amplitude=0.0,
            pct_chg=-0.65,
            price_change=0.0,
            turnover=0.005721,
        )
        db.add(item)
        db.commit()

        # 查询
        result = db.query(models.StockDaily.turnover).filter(
            models.StockDaily.symbol == '000001',
            models.StockDaily.trade_date == '20260521'
        ).scalar()
        print('db turnover after plain insert:', result)
        print('repr:', repr(result))

    finally:
        db.close()

if __name__ == '__main__':
    main()
