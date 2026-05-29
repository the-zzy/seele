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
        # 1. 删除 000001 的所有历史数据
        deleted = db.query(models.StockDaily).filter(models.StockDaily.symbol == '000001').delete()
        db.commit()
        print(f'已删除 000001 的 {deleted} 条旧记录')

        # 2. 用 baostock 拉取 2020-01-01 至今的数据
        lg = bs.login()
        if lg.error_code != '0':
            print(f'baostock 登录失败: {lg.error_msg}')
            return

        try:
            rs = bs.query_history_k_data_plus(
                'sz.000001',
                'date,code,open,high,low,close,preclose,volume,amount,turn,pctChg',
                start_date='2020-01-01',
                end_date='2026-05-28',
                frequency='d',
                adjustflag='3'
            )
            rows = []
            while rs.error_code == '0' and rs.next():
                rows.append(rs.get_row_data())
            print(f'baostock 返回 {len(rows)} 条记录')
        finally:
            bs.logout()

        # 3. 构建记录，正确处理 turnover
        records = []
        for row in rows:
            if not row[5] or float(row[5]) == 0:
                continue
            preclose = float(row[6]) if row[6] else 0
            close = float(row[5])
            high = float(row[3]) if row[3] else None
            low = float(row[4]) if row[4] else None

            # baostock 返回的 turn 是百分比数值，直接存入 DECIMAL(10,2)
            raw_turn = row[9]
            turnover = float(raw_turn) if raw_turn else None

            records.append({
                'trade_date': row[0].replace('-', ''),
                'symbol': '000001',
                'open': float(row[2]) if row[2] else None,
                'high': high,
                'low': low,
                'close': close,
                'volume': int(float(row[7])) if row[7] else None,
                'amount': float(row[8]) if row[8] else None,
                'amplitude': round((high - low) / preclose * 100, 4) if preclose and high is not None and low is not None else 0.0,
                'pct_chg': float(row[10]) if row[10] else None,
                'price_change': round(close - preclose, 4) if preclose else 0.0,
                'turnover': turnover,
            })

        print(f'构建完成，{len(records)} 条有效记录')

        # 4. 批量写入
        if records:
            upsert_stmt = insert(models.StockDaily).values(records)
            update_dict = {
                k: upsert_stmt.inserted[k]
                for k in upsert_stmt.inserted.keys()
                if k not in ('id', 'trade_date', 'symbol')
            }
            upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
            db.execute(upsert_stmt)
            db.commit()
            print(f'写入完成')

        # 5. 验证最近几天
        verify_rows = (
            db.query(models.StockDaily.trade_date, models.StockDaily.turnover)
            .filter(models.StockDaily.symbol == '000001')
            .filter(models.StockDaily.trade_date >= '20260520')
            .order_by(models.StockDaily.trade_date)
            .all()
        )
        print('\n=== 验证 000001 最近数据 ===')
        print(f"{'日期':<12} {'turnover'}")
        for td, to in verify_rows:
            print(f'{td:<12} {to}')

        # 6. 统计全表 000001 的 turnover 分布
        all_rows = (
            db.query(models.StockDaily.turnover)
            .filter(models.StockDaily.symbol == '000001')
            .all()
        )
        vals = [r[0] for r in all_rows if r[0] is not None]
        print(f'\n=== 000001 turnover 统计 ===')
        print(f'总记录: {len(all_rows)}')
        print(f'有值记录: {len(vals)}')
        if vals:
            print(f'最小值: {min(vals)}')
            print(f'最大值: {max(vals)}')
            print(f'均值: {sum(vals)/len(vals):.6f}')
            gt1 = len([v for v in vals if v > 1])
            print(f'>1 的异常值: {gt1}')

    finally:
        db.close()

if __name__ == '__main__':
    main()
