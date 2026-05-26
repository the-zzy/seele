"""
初始化交易日历表 (2024-2026)

用法: python scripts/init_trade_calendar.py
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import akshare as ak
from app.database import SessionLocal, engine
from app.database import Base
from app import crud


def main():
    print('[INIT] 创建表...')
    Base.metadata.create_all(bind=engine)
    print('[INIT] 表已创建')
    db = SessionLocal()
    try:
        # 1. 从 akshare 获取官方交易日历
        print('[INIT] 从 akshare 获取交易日历...')
        df = ak.tool_trade_date_hist_sina()
        trading_dates = set()
        for d in df['trade_date']:
            try:
                if isinstance(d, str):
                    trading_dates.add(date.fromisoformat(d))
                else:
                    trading_dates.add(d.date() if hasattr(d, 'date') else d)
            except Exception:
                pass

        print(f'[INIT] akshare 返回 {len(trading_dates)} 个交易日')

        # 2. 生成 2024-2026 所有日期
        start = date(2024, 1, 1)
        end = date(2026, 12, 31)
        items = []
        current = start
        while current <= end:
            weekday = current.weekday()  # 0=周一
            is_weekend = 1 if weekday >= 5 else 0
            is_trading = 1 if current in trading_dates else 0
            quarter = (current.month - 1) // 3 + 1
            week = current.isocalendar()[1]

            items.append({
                'trade_date': current,
                'is_trading_day': is_trading,
                'year': current.year,
                'quarter': quarter,
                'month': current.month,
                'week': week,
                'weekday': weekday,
                'is_weekend': is_weekend,
            })
            current += timedelta(days=1)

        # 3. 批量写入
        print(f'[INIT] 准备写入 {len(items)} 条记录...')
        count = crud.trade_calendar_crud.create_batch(db, items)
        print(f'[INIT] 成功写入 {count} 条')

    except Exception as exc:
        print(f'[INIT] 失败: {exc}')
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
