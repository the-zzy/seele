"""
更新 2026-05-11 的 5日涨幅和10日涨幅指标
"""

import pymysql
from datetime import date

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '20020228',
    'database': 'seele',
    'charset': 'utf8mb4',
}

TRADE_DATE = '20260511'

def main():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 获取该交易日所有有数据的股票代码
    cursor.execute(
        "SELECT DISTINCT symbol FROM stock_daily WHERE trade_date = %s",
        (TRADE_DATE,)
    )
    symbols = [row['symbol'] for row in cursor.fetchall()]
    print(f'共 {len(symbols)} 只股票待处理')

    success = 0
    failed = 0

    for i, symbol in enumerate(symbols, 1):
        # 获取最近 10 天的数据（包含当日）
        cursor.execute(
            """
            SELECT trade_date, close FROM stock_daily
            WHERE symbol = %s AND trade_date <= %s
            ORDER BY trade_date DESC
            LIMIT 10
            """,
            (symbol, TRADE_DATE)
        )
        rows = cursor.fetchall()
        closes = [r['close'] for r in rows if r['close'] is not None]

        if len(closes) < 5:
            failed += 1
            continue

        chg_5d = round((closes[0] - closes[4]) / closes[4] * 100, 2) if closes[4] != 0 else None
        chg_10d = round((closes[0] - closes[9]) / closes[9] * 100, 2) if len(closes) >= 10 and closes[9] != 0 else None

        cursor.execute(
            """
            UPDATE stock_daily_indicator
            SET chg_5d = %s, chg_10d = %s
            WHERE symbol = %s AND trade_date = %s
            """,
            (chg_5d, chg_10d, symbol, TRADE_DATE)
        )
        success += 1

        if i % 100 == 0:
            conn.commit()
            print(f'  已处理 {i}/{len(symbols)}...')

    conn.commit()
    cursor.close()
    conn.close()
    print(f'完成: 成功 {success}, 失败 {failed}')


if __name__ == '__main__':
    main()
