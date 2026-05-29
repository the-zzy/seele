import os
import sys
import baostock as bs
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app import models

def get_db_turnover():
    db = SessionLocal()
    try:
        rows = (
            db.query(models.StockDaily.trade_date, models.StockDaily.turnover)
            .filter(
                models.StockDaily.symbol == '000001',
                models.StockDaily.trade_date >= '20240101',
            )
            .order_by(models.StockDaily.trade_date)
            .all()
        )
        df = pd.DataFrame(rows, columns=['trade_date', 'db_turnover'])
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        return df
    finally:
        db.close()

def get_baostock_turnover():
    lg = bs.login()
    if lg.error_code != '0':
        print(f'baostock 登录失败: {lg.error_msg}')
        sys.exit(1)
    try:
        rs = bs.query_history_k_data_plus(
            'sz.000001',
            'date,turn',
            start_date='2024-01-01',
            end_date='2026-05-28',
            frequency='d',
            adjustflag='3'
        )
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        df = pd.DataFrame(data_list, columns=['trade_date', 'bs_turnover'])
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        # baostock 返回的是百分比数值字符串，如 "12.05" 表示 12.05%
        # 数据库存的是小数，如 0.1205，需要除以 100
        df['bs_turnover'] = pd.to_numeric(df['bs_turnover'], errors='coerce') / 100
        return df
    finally:
        bs.logout()

def main():
    print('正在获取数据库数据...')
    db_df = get_db_turnover()
    print(f'数据库记录数: {len(db_df)}')

    print('正在获取 baostock 数据...')
    bs_df = get_baostock_turnover()
    print(f'baostock 记录数: {len(bs_df)}')

    merged = pd.merge(db_df, bs_df, on='trade_date', how='outer')
    merged = merged.sort_values('trade_date')

    merged['diff'] = merged['db_turnover'] - merged['bs_turnover']
    merged['diff_pct'] = (merged['diff'] / merged['bs_turnover'] * 100).abs()

    anomalies = merged[
        (merged['diff'].abs() > 0.005) |
        ((merged['db_turnover'].isna() | (merged['db_turnover'] == 0)) & merged['bs_turnover'].notna() & (merged['bs_turnover'] > 0.001)) |
        (merged['db_turnover'].notna() & (merged['db_turnover'] > 0) & (merged['bs_turnover'].isna() | (merged['bs_turnover'] == 0)))
    ].copy()

    print(f'\n=== 异常记录 ({len(anomalies)} 条) ===')
    print(f"{'日期':<12} {'DB换手率':<14} {'BS换手率':<14} {'差值':<14} {'说明'}")
    print('-' * 80)

    for _, row in anomalies.iterrows():
        date_str = row['trade_date'].strftime('%Y-%m-%d')
        db_val = f"{row['db_turnover']:.6f}" if pd.notna(row['db_turnover']) else 'NULL'
        bs_val = f"{row['bs_turnover']:.6f}" if pd.notna(row['bs_turnover']) else 'NULL'
        diff_val = f"{row['diff']:.6f}" if pd.notna(row['diff']) else 'N/A'

        if pd.isna(row['db_turnover']) or row['db_turnover'] == 0:
            note = 'DB缺失/为0'
        elif pd.isna(row['bs_turnover']) or row['bs_turnover'] == 0:
            note = 'BS缺失/为0'
        elif row['db_turnover'] > 1:
            note = 'DB异常大(>1)'
        else:
            note = '数值偏差'

        print(f"{date_str:<12} {db_val:<14} {bs_val:<14} {diff_val:<14} {note}")

    zero_anomalies = merged[
        ((merged['db_turnover'] == 0) | merged['db_turnover'].isna()) &
        merged['bs_turnover'].notna() & (merged['bs_turnover'] > 0.001)
    ].copy()

    print(f'\n=== DB为0但BS有值的记录 ({len(zero_anomalies)} 条) ===')
    for _, row in zero_anomalies.iterrows():
        date_str = row['trade_date'].strftime('%Y-%m-%d')
        bs_val = f"{row['bs_turnover']:.6f}" if pd.notna(row['bs_turnover']) else 'NULL'
        print(f"{date_str}: DB={row['db_turnover']}, BS={bs_val}")

    total_db_zero = len(merged[(merged['db_turnover'] == 0) | merged['db_turnover'].isna()])
    total_db_gt1 = len(merged[merged['db_turnover'] > 1])
    print(f'\n=== 汇总 ===')
    print(f'总记录数: {len(merged)}')
    print(f'DB为0/NULL: {total_db_zero}')
    print(f'DB>1(异常大): {total_db_gt1}')
    print(f'差异显著: {len(anomalies)}')

if __name__ == '__main__':
    main()
