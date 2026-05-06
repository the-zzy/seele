#!/usr/bin/env python3
"""
独立脚本：同步全部 A 股历史日线数据（2020-01-01 至今）
多进程并行版本，目标 1 小时内完成

使用方法：
    .venv/Scripts/python sync_history_data.py

说明：
    - 数据源：Baostock
    - 股票范围：沪深主板且非 ST
    - 写入策略：全量覆盖（ON DUPLICATE KEY UPDATE）
    - 每个 worker 进程复用 Baostock 连接，只登录一次
"""

import time
import sys
from datetime import datetime, timedelta
from typing import List, Dict
from multiprocessing import Pool, Manager

import baostock as bs
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

# 并行进程数
NUM_WORKERS = 16
# Baostock 查询间隔（秒），避免触发限流
QUERY_INTERVAL = 2

# 数据库配置
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = '20020228'
DB_NAME = 'seele'

DATABASE_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

Base = declarative_base()


class StockBasic(Base):
    __tablename__ = 'stock_basic'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    area = Column(String(50))
    industry = Column(String(50))
    market = Column(String(20))
    list_date = Column(Date)


class StockDaily(Base):
    __tablename__ = 'stock_daily'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    amplitude = Column(Float)
    pct_chg = Column(Float)
    price_change = Column(Float)
    turnover = Column(Float)

    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_trade_date_symbol'),
    )


def get_stock_list() -> List[str]:
    """获取沪深主板且非 ST 的股票代码列表"""
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=5,
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        stocks = (
            db.query(StockBasic)
            .filter(StockBasic.market == '主板')
            .filter(StockBasic.name.notlike('%ST%'))
            .all()
        )
        return [s.symbol for s in stocks]
    finally:
        db.close()


def _sync_symbol(db, symbol: str, start_date: str, end_date: str) -> Dict:
    """同步单只股票（worker 内部调用，不复用 Baostock 连接）"""
    if symbol.startswith('6'):
        prefix = 'sh'
    elif symbol.startswith(('0', '2', '3')):
        prefix = 'sz'
    else:
        prefix = 'bj'
    code = f'{prefix}.{symbol}'

    start = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
    end = f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'

    fields = 'date,code,open,high,low,close,preclose,volume,amount,turn,pctChg'
    rs = bs.query_history_k_data_plus(
        code, fields, start_date=start, end_date=end,
        frequency='d', adjustflag='3'
    )
    rows = []
    while (rs.error_code == '0') and rs.next():
        rows.append(rs.get_row_data())

    if not rows:
        return {'symbol': symbol, 'count': 0, 'error': None}

    records = []
    for row in rows:
        preclose = float(row[6]) if row[6] else 0
        close = float(row[5]) if row[5] else None
        high = float(row[3]) if row[3] else None
        low = float(row[4]) if row[4] else None

        records.append({
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
            'price_change': round(close - preclose, 4) if close is not None and preclose else 0.0,
            'turnover': float(row[9]) if row[9] else None,
        })

    if records:
        upsert_stmt = insert(StockDaily).values(records)
        update_dict = {
            k: upsert_stmt.inserted[k]
            for k in upsert_stmt.inserted.keys()
            if k not in ('id', 'trade_date', 'symbol')
        }
        upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
        db.execute(upsert_stmt)
        db.commit()

    return {'symbol': symbol, 'count': len(records), 'error': None}


def _sync_symbol_akshare(db, symbol: str, start_date: str, end_date: str) -> Dict:
    """AkShare 新浪源同步单只股票（Baostock 备用）"""
    if symbol.startswith('6'):
        prefix = 'sh'
    elif symbol.startswith(('0', '2', '3')):
        prefix = 'sz'
    else:
        prefix = 'bj'
    code = f'{prefix}.{symbol}'

    # 多查几天用于计算 preclose（避开节假日）
    s = datetime.strptime(start_date, '%Y%m%d')
    pre_start = (s - timedelta(days=5)).strftime('%Y%m%d')

    try:
        import akshare as ak
        df = ak.stock_zh_a_daily(symbol=code, start_date=pre_start, end_date=end_date, adjust='qfq')
    except Exception as exc:
        return {'symbol': symbol, 'count': 0, 'error': f'AkShare 失败: {exc}'}

    if df.empty:
        return {'symbol': symbol, 'count': 0, 'error': None}

    df = df.sort_values('date').reset_index(drop=True)
    df['preclose'] = df['close'].shift(1)

    target_start = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
    df = df[df['date'] >= target_start]

    records = []
    for _, row in df.iterrows():
        preclose = row['preclose'] if pd.notna(row['preclose']) else 0
        close = row['close']
        high = row['high']
        low = row['low']

        records.append({
            'trade_date': row['date'],
            'symbol': symbol,
            'open': float(row['open']) if pd.notna(row['open']) else None,
            'high': float(high) if pd.notna(high) else None,
            'low': float(low) if pd.notna(low) else None,
            'close': float(close) if pd.notna(close) else None,
            'volume': int(float(row['volume'])) if pd.notna(row['volume']) else None,
            'amount': float(row['amount']) if pd.notna(row['amount']) else None,
            'amplitude': round((high - low) / preclose * 100, 4) if preclose and pd.notna(high) and pd.notna(low) else 0.0,
            'pct_chg': float((close - preclose) / preclose * 100) if preclose and pd.notna(close) else 0.0,
            'price_change': round(close - preclose, 4) if pd.notna(close) and preclose else 0.0,
            'turnover': float(row['turnover']) * 100 if pd.notna(row['turnover']) else None,
        })

    if records:
        upsert_stmt = insert(StockDaily).values(records)
        update_dict = {
            k: upsert_stmt.inserted[k]
            for k in upsert_stmt.inserted.keys()
            if k not in ('id', 'trade_date', 'symbol')
        }
        upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
        db.execute(upsert_stmt)
        db.commit()

    return {'symbol': symbol, 'count': len(records), 'error': None}


def _worker_task(args):
    """进程 worker：登录一次 Baostock，批量处理股票"""
    symbols, start_date, end_date, progress_queue, worker_id = args

    # 数据库连接
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=2,
        max_overflow=2,
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Baostock 登录（每个 worker 只登录一次）
    lg = bs.login()
    use_akshare = lg.error_code != '0'
    if use_akshare:
        print(f'[worker {worker_id}] Baostock 登录失败: {lg.error_msg}，切换 AkShare 备用源')

    try:
        for symbol in symbols:
            t0 = time.time()
            try:
                if use_akshare:
                    result = _sync_symbol_akshare(db, symbol, start_date, end_date)
                else:
                    result = _sync_symbol(db, symbol, start_date, end_date)
            except Exception as exc:
                result = {'symbol': symbol, 'count': 0, 'error': str(exc)}

            elapsed = time.time() - t0
            result['elapsed'] = elapsed
            result['worker_id'] = worker_id
            progress_queue.put(result)

            # Baostock 需要请求频率控制，AkShare 不需要
            if not use_akshare:
                time.sleep(QUERY_INTERVAL)
    finally:
        if not use_akshare:
            bs.logout()
        db.close()

    return worker_id


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f'{seconds:.1f}秒'
    elif seconds < 3600:
        return f'{seconds / 60:.1f}分钟'
    else:
        return f'{seconds / 3600:.1f}小时'


def chunk_list(lst: List, n: int) -> List[List]:
    """将列表平均分成 n 份"""
    avg = len(lst) // n
    remainder = len(lst) % n
    chunks = []
    start = 0
    for i in range(n):
        size = avg + (1 if i < remainder else 0)
        chunks.append(lst[start:start + size])
        start += size
    return chunks


def main():
    start_date = '20200101'
    end_date = datetime.today().strftime('%Y%m%d')

    print('=' * 60)
    print('开始同步 A 股历史日线数据（多进程并行）')
    print(f'日期范围: {start_date} ~ {end_date}')
    print(f'并行进程数: {NUM_WORKERS}')
    print(f'查询间隔: {QUERY_INTERVAL}s')
    print('=' * 60)

    all_symbols = get_stock_list()
    total = len(all_symbols)
    print(f'共 {total} 只股票待同步（沪深主板且非 ST）')
    print()

    # 分片
    chunks = chunk_list(all_symbols, NUM_WORKERS)
    chunks = [c for c in chunks if c]
    actual_workers = len(chunks)

    manager = Manager()
    progress_queue = manager.Queue()

    tasks = [
        (chunks[i], start_date, end_date, progress_queue, i)
        for i in range(actual_workers)
    ]

    overall_start = time.time()
    success_records = 0
    failed_stocks = 0
    skipped_stocks = 0
    processed = 0

    with Pool(processes=actual_workers) as pool:
        async_results = [pool.apply_async(_worker_task, (task,)) for task in tasks]

        last_summary_time = time.time()
        while processed < total:
            try:
                result = progress_queue.get(timeout=60)
            except Exception:
                # queue 超时，打印提示继续等待
                print('  [提示] 进度队列等待中...')
                sys.stdout.flush()
                continue

            processed += 1
            symbol = result['symbol']
            count = result['count']
            error = result['error']
            elapsed = result.get('elapsed', 0)
            worker_id = result.get('worker_id', 0)

            if error:
                failed_stocks += 1
            elif count > 0:
                success_records += count
            else:
                skipped_stocks += 1

            now = time.time()
            elapsed_total = now - overall_start
            speed = processed / elapsed_total if elapsed_total > 0 else 0
            eta = (total - processed) / speed if speed > 0 else 0
            pct = processed / total * 100

            status_icon = 'OK' if count > 0 else ('SKIP' if not error else 'ERR')
            msg = (
                f'[{processed:>5}/{total} {pct:5.1f}%] {symbol} w{worker_id:>2} | '
                f'{status_icon} {count:>4}条 {elapsed:5.2f}s | '
                f'ETA {format_duration(eta)} ({speed:.1f}只/s)'
            )
            print(msg)
            sys.stdout.flush()

            if now - last_summary_time >= 30:
                last_summary_time = now
                print(
                    f'\n  >>> 汇总: 成功记录 {success_records:,} | '
                    f'跳过 {skipped_stocks} | 异常 {failed_stocks} | '
                    f'速度 {speed:.1f}只/s | ETA {format_duration(eta)}\n'
                )
                sys.stdout.flush()

        # 等待所有进程结束
        for r in async_results:
            try:
                r.get(timeout=300)
            except Exception as exc:
                print(f'  [警告] worker 异常: {exc}')

    total_time = time.time() - overall_start

    print()
    print('=' * 60)
    print('同步完成')
    print(f'总耗时: {format_duration(total_time)}')
    print(f'成功记录: {success_records}')
    print(f'跳过/无数据: {skipped_stocks}')
    print(f'异常: {failed_stocks}')
    print('=' * 60)


if __name__ == '__main__':
    main()
