"""
同步任务子进程工作模块

与主路由模块完全隔离，确保 ProcessPoolExecutor 子进程启动时不触发
FastAPI 路由注册、数据库引擎创建等副作用。

每个子进程函数都是自包含的（import 在函数内部），可独立被 pickle 序列化。
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


def _fetch_baostock_chunk(symbols: list, trade_date: str) -> tuple:
    """子进程：单进程内串行拉取 baostock，带每只股的硬超时保护。

    每个进程持有独立的 baostock 登录态，不会与其他进程冲突。
    返回 (records, skipped, failed)
    """
    import concurrent.futures
    import baostock as bs

    date_fmt = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}" if len(trade_date) == 8 else trade_date

    records = []
    skipped = []
    failed = []

    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(10)

    def _login():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as te:
            ft = te.submit(bs.login)
            try:
                lg = ft.result(timeout=10)
                return lg.error_code == '0', lg.error_msg
            except concurrent.futures.TimeoutError:
                return False, 'baostock login timeout (10s)'

    def _fetch_one(symbol: str) -> tuple:
        """返回 (record_dict | None, skip_symbol | None, fail_dict | None)"""
        if symbol.startswith('6'):
            prefix = 'sh'
        elif symbol.startswith(('0', '2', '3')):
            prefix = 'sz'
        else:
            prefix = 'bj'
        code = f'{prefix}.{symbol}'

        rows = []
        rs = None
        for attempt in range(2):
            try:
                rs = bs.query_history_k_data_plus(
                    code,
                    'date,code,open,high,low,close,preclose,volume,amount,turn,pctChg',
                    start_date=date_fmt, end_date=date_fmt,
                    frequency='d', adjustflag='2',
                )
                rows = []
                count = 0
                while (rs.error_code == '0') and rs.next():
                    rows.append(rs.get_row_data())
                    count += 1
                    if count >= 10:
                        break
                if rs.error_code == '0':
                    break

                if '用户未登录' in (rs.error_msg or '') and attempt == 0:
                    try:
                        bs.logout()
                    except Exception:
                        pass
                    ok, msg = _login()
                    if not ok:
                        return None, None, {'symbol': symbol, 'reason': f'Baostock relogin failed: {msg}'}
                    continue
                break
            except socket.timeout:
                return None, None, {'symbol': symbol, 'reason': 'baostock request timeout (10s)'}
            except Exception as e:
                return None, None, {'symbol': symbol, 'reason': str(e)}

        if rs is None:
            return None, None, None
        if rs.error_code != '0':
            return None, None, {'symbol': symbol, 'reason': rs.error_msg}
        if not rows:
            return None, symbol, None

        row = rows[0]
        if not row[5] or float(row[5]) == 0:
            return None, symbol, None

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
        return record, None, None

    try:
        ok, msg = _login()
        if not ok:
            return [], [], [{'symbol': s, 'reason': f'Baostock login failed: {msg}'} for s in symbols]

        for symbol in symbols:
            # 每只股用独立线程执行，带 10s 硬超时
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as te:
                ft = te.submit(_fetch_one, symbol)
                try:
                    record, skip, fail = ft.result(timeout=10)
                except concurrent.futures.TimeoutError:
                    failed.append({'symbol': symbol, 'reason': 'timeout (10s)'})
                    continue
                except Exception as exc:
                    failed.append({'symbol': symbol, 'reason': str(exc)})
                    continue

            if record:
                records.append(record)
            elif skip:
                skipped.append(skip)
            elif fail:
                failed.append(fail)
    finally:
        socket.setdefaulttimeout(old_timeout)
        try:
            bs.logout()
        except Exception:
            pass

    return records, skipped, failed


def _fetch_akshare_single(symbol: str, trade_date: str, preclose_map: dict) -> tuple:
    """单只股 akshare 回退获取。返回 (records列表, skipped列表, failed列表)"""
    import akshare as ak
    import pandas as pd
    from datetime import datetime

    target_dt = datetime.strptime(trade_date, '%Y%m%d')
    target_date_obj = target_dt.date()

    prefix = 'sh' if symbol.startswith('6') else 'sz'
    ak_symbol = f'{prefix}{symbol}'

    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(15)
    try:
        df = ak.stock_zh_a_daily(symbol=ak_symbol, start_date=trade_date, end_date=trade_date, adjust='qfq')
    except Exception as e:
        return [], [], [{'symbol': symbol, 'reason': f'akshare fallback: {e}'}]
    finally:
        socket.setdefaulttimeout(old_timeout)

    if df.empty:
        return [], [symbol], []

    target_rows = df[df['date'] == target_date_obj]
    if target_rows.empty:
        return [], [symbol], []

    row = target_rows.iloc[-1]
    close = row['close']
    if not pd.notna(close) or float(close) == 0:
        return [], [symbol], []

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
        'price_change': round(close - preclose, 4) if preclose else 0.0,
        'turnover': float(row['turnover']) * 100 if pd.notna(row['turnover']) else None,
    }
    return [record], [], []
