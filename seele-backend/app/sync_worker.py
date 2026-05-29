"""
同步任务子进程工作模块

与主路由模块完全隔离，确保 ProcessPoolExecutor 子进程启动时不触发
FastAPI 路由注册、数据库引擎创建等副作用。
"""

import socket


def _fetch_akshare_batch(symbols: list, trade_date: str, preclose_map: dict) -> tuple:
    """子进程：批量获取 akshare 数据。返回 (records, skipped, failed)"""
    import akshare as ak
    import pandas as pd
    from datetime import datetime

    target_dt = datetime.strptime(trade_date, '%Y%m%d')
    target_date_obj = target_dt.date()

    records = []
    skipped = []
    failed = []

    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        for symbol in symbols:
            prefix = 'sh' if symbol.startswith('6') else 'sz'
            ak_symbol = f'{prefix}{symbol}'
            try:
                df = ak.stock_zh_a_daily(symbol=ak_symbol, start_date=trade_date, end_date=trade_date, adjust='qfq')
            except Exception as e:
                failed.append({'symbol': symbol, 'reason': str(e)})
                continue

            if df.empty:
                skipped.append(symbol)
                continue

            target_rows = df[df['date'] == target_date_obj]
            if target_rows.empty:
                skipped.append(symbol)
                continue

            row = target_rows.iloc[-1]
            close = row['close']
            if not pd.notna(close) or float(close) == 0:
                skipped.append(symbol)
                continue

            preclose = preclose_map.get(symbol)
            pct_chg = None
            if preclose is not None:
                pct_chg = round((float(close) - preclose) / preclose * 100, 4)

            high = row['high']
            low = row['low']

            record = {
                'trade_date': target_date_obj,
                'symbol': symbol,
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(high) if pd.notna(high) else None,
                'low': float(low) if pd.notna(low) else None,
                'close': float(close),
                'volume': int(float(row['volume'])) if pd.notna(row['volume']) else None,
                'amount': float(row['amount']) if pd.notna(row['amount']) else None,
                'amplitude': round((float(high) - float(low)) / preclose * 100, 4) if preclose and high is not None and low is not None else 0.0,
                'pct_chg': pct_chg,
                'price_change': round(float(close) - preclose, 4) if preclose else 0.0,
                'turnover': float(row['turnover']) * 100 if pd.notna(row['turnover']) else None,
            }
            records.append(record)
    finally:
        socket.setdefaulttimeout(old_timeout)

    return records, skipped, failed


def _fetch_baostock_batch(symbols: list, trade_date: str) -> tuple:
    """子进程：批量获取 baostock 数据。返回 (records, skipped, failed)"""
    import baostock as bs

    fields = 'date,code,open,high,low,close,preclose,volume,amount,turn,pctChg'
    date_fmt = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}" if len(trade_date) == 8 else trade_date

    lg = bs.login()
    if lg.error_code != '0':
        return [], [], [{'symbol': 'ALL', 'reason': f'Baostock login failed: {lg.error_msg}'}]

    records = []
    skipped = []
    failed = []

    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(30)
    try:
        for symbol in symbols:
            if symbol.startswith('6'):
                prefix = 'sh'
            elif symbol.startswith(('0', '2', '3')):
                prefix = 'sz'
            else:
                prefix = 'bj'
            code = f'{prefix}.{symbol}'

            try:
                rs = bs.query_history_k_data_plus(
                    code, fields,
                    start_date=date_fmt, end_date=date_fmt,
                    frequency='d', adjustflag='2'
                )
                rows = []
                count = 0
                while (rs.error_code == '0') and rs.next():
                    rows.append(rs.get_row_data())
                    count += 1
                    if count >= 10:
                        break
            except socket.timeout:
                failed.append({'symbol': symbol, 'reason': 'baostock request timeout (30s)'})
                continue
            except Exception as e:
                failed.append({'symbol': symbol, 'reason': str(e)})
                continue

            if rs.error_code != '0':
                failed.append({'symbol': symbol, 'reason': rs.error_msg})
                continue
            if not rows:
                skipped.append(symbol)
                continue

            row = rows[0]
            if not row[5] or float(row[5]) == 0:
                skipped.append(symbol)
                continue

            preclose = float(row[6]) if row[6] else 0
            close = float(row[5])
            high = float(row[3]) if row[3] else None
            low = float(row[4]) if row[4] else None

            record = {
                'trade_date': row[0],
                'symbol': symbol,
                'open': float(row[2]) if row[2] else None,
                'high': high,
                'low': low,
                'close': close,
                'volume': int(float(row[7])) if row[7] else None,
                'amount': float(row[8]) if row[8] else None,
                'amplitude': round((high - low) / preclose * 100, 4) if preclose and high is not None and low is not None else 0.0,
                'pct_chg': float(row[10]) if row[10] else None,
                'price_change': round(close - preclose, 4) if preclose else 0.0,
                'turnover': float(row[9]) if row[9] else None,
            }
            records.append(record)
    finally:
        socket.setdefaulttimeout(old_timeout)
        bs.logout()

    return records, skipped, failed
