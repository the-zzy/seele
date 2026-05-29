import os
import sys
import time
import random
import akshare as ak
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

def get_akshare_turnover():
    # akshare 接口可能有频率限制，加随机延迟和重试
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(1, 3))
            df = ak.stock_zh_a_hist(
                symbol='000001',
                period='daily',
                start_date='20240101',
                end_date='20260528',
                adjust=''
            )
            df = df[['日期', '换手率']].copy()
            df.columns = ['trade_date', 'ak_turnover']
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            # akshare 返回的是百分比数值（如 0.53 表示 0.53%），需要转成小数
            df['ak_turnover'] = pd.to_numeric(df['ak_turnover'], errors='coerce') / 100
            return df
        except Exception as exc:
            print(f'akshare 请求失败 (尝试 {attempt + 1}/{max_retries}): {exc}')
            if attempt < max_retries - 1:
                time.sleep(random.uniform(3, 6))
            else:
                raise

def main():
    print('正在获取数据库数据...')
    db_df = get_db_turnover()
    print(f'数据库记录数: {len(db_df)}')

    print('正在获取 akshare 数据...')
    ak_df = get_akshare_turnover()
    print(f'akshare 记录数: {len(ak_df)}')

    merged = pd.merge(db_df, ak_df, on='trade_date', how='outer')
    merged = merged.sort_values('trade_date')

    # 找出差异显著的记录
    merged['diff'] = merged['db_turnover'] - merged['ak_turnover']
    merged['diff_pct'] = (merged['diff'] / merged['ak_turnover'] * 100).abs()

    # 异常定义：差异超过 10% 或 DB 为 0/None 但 akshare 有值，或 DB 有值但 akshare 为 0/None
    anomalies = merged[
        (merged['diff'].abs() > 0.005) |  # 绝对差值 > 0.5%
        ((merged['db_turnover'].isna() | (merged['db_turnover'] == 0)) & merged['ak_turnover'].notna() & (merged['ak_turnover'] != 0)) |
        (merged['db_turnover'].notna() & (merged['db_turnover'] > 0) & (merged['ak_turnover'].isna() | (merged['ak_turnover'] == 0)))
    ].copy()

    print(f'\n=== 异常记录 ({len(anomalies)} 条) ===')
    print(f"{'日期':<12} {'DB换手率':<12} {'AK换手率':<12} {'差值':<12} {'说明'}")
    print('-' * 70)

    for _, row in anomalies.iterrows():
        date_str = row['trade_date'].strftime('%Y-%m-%d')
        db_val = f"{row['db_turnover']:.4f}" if pd.notna(row['db_turnover']) else 'NULL'
        ak_val = f"{row['ak_turnover']:.4f}" if pd.notna(row['ak_turnover']) else 'NULL'
        diff_val = f"{row['diff']:.4f}" if pd.notna(row['diff']) else 'N/A'

        if pd.isna(row['db_turnover']) or row['db_turnover'] == 0:
            note = 'DB缺失/为0'
        elif pd.isna(row['ak_turnover']) or row['ak_turnover'] == 0:
            note = 'AK缺失/为0'
        elif row['db_turnover'] > 1:
            note = 'DB异常大(>1)'
        else:
            note = '数值偏差'

        print(f"{date_str:<12} {db_val:<12} {ak_val:<12} {diff_val:<12} {note}")

    # 特别关注 DB 为 0 但 akshare 有正常值的记录
    zero_anomalies = merged[
        ((merged['db_turnover'] == 0) | merged['db_turnover'].isna()) &
        merged['ak_turnover'].notna() & (merged['ak_turnover'] > 0.001)
    ].copy()

    print(f'\n=== DB为0但AK有值的记录 ({len(zero_anomalies)} 条) ===')
    for _, row in zero_anomalies.iterrows():
        date_str = row['trade_date'].strftime('%Y-%m-%d')
        ak_val = f"{row['ak_turnover']:.4f}" if pd.notna(row['ak_turnover']) else 'NULL'
        print(f"{date_str}: DB={row['db_turnover']}, AK={ak_val}")

    # 汇总统计
    total_db_zero = len(merged[(merged['db_turnover'] == 0) | merged['db_turnover'].isna()])
    total_db_gt1 = len(merged[merged['db_turnover'] > 1])
    print(f'\n=== 汇总 ===')
    print(f'总记录数: {len(merged)}')
    print(f'DB为0/NULL: {total_db_zero}')
    print(f'DB>1(异常大): {total_db_gt1}')
    print(f'差异显著: {len(anomalies)}')

if __name__ == '__main__':
    main()
