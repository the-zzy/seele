#!/usr/bin/env python3
"""
独立脚本：全量同步 A 股历史日线数据（akshare 源，多进程版）

与项目代码完全解耦，可直接运行：
    .venv/Scripts/python scripts/sync_history_full_akshare.py

特性：
    - 数据源：akshare stock_zh_a_daily（前复权）
    - 股票范围：从 stock_basic 表读取，排除北交所
    - 换手率存储为百分位（akshare 返回小数，脚本内部 *100）
    - 多进程并发（multiprocessing.Pool），每个进程独立 akshare 环境，真正并行
    - 每个 worker 内批量写入，主进程负责进度汇总
    - 进度实时输出到控制台
"""

import os
import sys
import socket
import time
from datetime import datetime
from multiprocessing import Pool, Manager

import akshare as ak
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, UniqueConstraint
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import declarative_base, sessionmaker

# ==================== 配置区 ====================

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '20020228')
DB_NAME = os.environ.get('DB_NAME', 'seele')

START_DATE = os.environ.get('START_DATE', '20200101')
END_DATE = os.environ.get('END_DATE', datetime.now().strftime('%Y%m%d'))

# 股票代码范围（可选，默认不限制，仅排除北交所）
SYMBOL_MIN = os.environ.get('SYMBOL_MIN', '')
SYMBOL_MAX = os.environ.get('SYMBOL_MAX', '')

# 进程数：akshare 新浪源限流严格，建议 2-4 进程，太多会触发 IP 封禁
NUM_WORKERS = int(os.environ.get('MAX_WORKERS', 4))

# 每个 worker 内部批量写入阈值
WORKER_BATCH_SIZE = 3000

DATABASE_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

Base = declarative_base()

# ==================== 数据库模型 ====================


class StockBasic(Base):
    __tablename__ = 'stock_basic'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    market = Column(String(20))


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


# ==================== 工具函数 ====================


def _upsert(session, records: list[dict]) -> None:
    """批量 upsert"""
    if not records:
        return
    stmt = insert(StockDaily).values(records)
    update_dict = {
        k: stmt.inserted[k]
        for k in stmt.inserted.keys()
        if k not in ('id', 'trade_date', 'symbol')
    }
    stmt = stmt.on_duplicate_key_update(**update_dict)
    session.execute(stmt)
    session.commit()


def _fetch_symbol_history(symbol: str, start_date: str, end_date: str) -> tuple[list[dict], str | None]:
    """获取单只股票历史日线，返回 (records, error)"""
    if symbol.startswith('6'):
        prefix = 'sh'
    elif symbol.startswith(('0', '2', '3')):
        prefix = 'sz'
    else:
        prefix = 'bj'
    code = f'{prefix}{symbol}'

    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)
        try:
            df = ak.stock_zh_a_daily(symbol=code, start_date=start_date, end_date=end_date, adjust='qfq')
        finally:
            socket.setdefaulttimeout(old_timeout)
    except Exception as exc:
        return [], str(exc)

    if df is None or df.empty:
        return [], None

    df = df.sort_values('date').reset_index(drop=True)
    df['preclose'] = df['close'].shift(1)

    records = []
    for _, row in df.iterrows():
        preclose = float(row['preclose']) if pd.notna(row['preclose']) else 0
        close = float(row['close']) if pd.notna(row['close']) else None
        high = float(row['high']) if pd.notna(row['high']) else None
        low = float(row['low']) if pd.notna(row['low']) else None

        records.append({
            'trade_date': str(pd.to_datetime(row['date']).date()),
            'symbol': symbol,
            'open': float(row['open']) if pd.notna(row['open']) else None,
            'high': high,
            'low': low,
            'close': close,
            'volume': int(float(row['volume'])) if pd.notna(row['volume']) else None,
            'amount': float(row['amount']) if pd.notna(row['amount']) else None,
            'amplitude': round((high - low) / preclose * 100, 4) if preclose and high is not None and low is not None else 0.0,
            'pct_chg': round((close - preclose) / preclose * 100, 4) if preclose and close is not None else 0.0,
            'price_change': round(close - preclose, 4) if close is not None and preclose else 0.0,
            'turnover': float(row['turnover']) * 100 if pd.notna(row['turnover']) else None,
        })

    return records, None


def _worker_task(args):
    """进程 worker：处理一批股票，独立写入数据库"""
    symbols, start_date, end_date, progress_queue, worker_id = args

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=2,
        max_overflow=2,
        echo=False,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    buffer = []
    try:
        for idx, symbol in enumerate(symbols):
            t0 = time.time()
            try:
                records, error = _fetch_symbol_history(symbol, start_date, end_date)
            except Exception as exc:
                records, error = [], str(exc)

            # akshare 新浪源限流保护：每请求间隔 0.5 秒
            if idx < len(symbols) - 1:
                time.sleep(0.5)

            if records:
                buffer.extend(records)
                if len(buffer) >= WORKER_BATCH_SIZE:
                    _upsert(session, buffer)
                    buffer = []

            elapsed = time.time() - t0
            progress_queue.put({
                'symbol': symbol,
                'count': len(records),
                'error': error,
                'worker_id': worker_id,
                'elapsed': elapsed,
            })

        if buffer:
            _upsert(session, buffer)
    finally:
        session.close()

    return worker_id


# ==================== 主进程 ====================


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f'{seconds:.0f}秒'
    elif seconds < 3600:
        return f'{seconds / 60:.1f}分钟'
    else:
        return f'{seconds / 3600:.1f}小时'


def main():
    # 1. 获取股票列表
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=5,
        echo=False,
    )
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        rows = session.query(StockBasic.symbol, StockBasic.market).all()
        all_symbols = [r[0] for r in rows if r[1] != '北交所']
        if SYMBOL_MIN or SYMBOL_MAX:
            all_symbols = [
                s for s in all_symbols
                if (not SYMBOL_MIN or s >= SYMBOL_MIN)
                and (not SYMBOL_MAX or s <= SYMBOL_MAX)
            ]

        # 过滤已存在的股票（断点续传）
        existing_symbols = {
            r[0] for r in session.query(StockDaily.symbol).distinct().all()
        }
        skipped_existing = [s for s in all_symbols if s in existing_symbols]
        all_symbols = [s for s in all_symbols if s not in existing_symbols]
    finally:
        session.close()

    total = len(all_symbols)
    skipped_count = len(skipped_existing)

    print('=' * 70)
    print('开始全量历史同步（akshare 多进程版）')
    print(f'日期范围: {START_DATE} ~ {END_DATE}')
    if SYMBOL_MIN or SYMBOL_MAX:
        print(f'代码范围: {SYMBOL_MIN or "*"} ~ {SYMBOL_MAX or "*"}')
    else:
        print('代码范围: 全部（排除北交所）')
    print(f'进程数: {NUM_WORKERS}')
    if skipped_count > 0:
        print(f'已存在（跳过）: {skipped_count} 只')
    print(f'待同步: {total} 只')
    print('=' * 70)
    sys.stdout.flush()

    if total == 0:
        print('没有需要同步的股票，全部已存在。')
        return

    # 2. 分片
    chunk_size = max(1, total // NUM_WORKERS)
    chunks = [all_symbols[i:i + chunk_size] for i in range(0, len(all_symbols), chunk_size)]
    actual_workers = len(chunks)

    manager = Manager()
    progress_queue = manager.Queue()

    tasks = [
        (chunks[i], START_DATE, END_DATE, progress_queue, i)
        for i in range(actual_workers)
    ]

    # 3. 启动进程池并消费进度
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
                print('  [提示] 进度队列等待中...')
                sys.stdout.flush()
                continue

            processed += 1
            symbol = result['symbol']
            count = result['count']
            error = result['error']
            worker_id = result.get('worker_id', 0)
            elapsed = result.get('elapsed', 0)

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
                f'ETA {_format_duration(eta)} ({speed:.1f}只/s)'
            )
            print(msg)
            sys.stdout.flush()

            if now - last_summary_time >= 30:
                last_summary_time = now
                print(
                    f'\n  >>> 汇总: 成功记录 {success_records:,} | '
                    f'跳过 {skipped_stocks} | 异常 {failed_stocks} | '
                    f'速度 {speed:.1f}只/s | ETA {_format_duration(eta)}\n'
                )
                sys.stdout.flush()

        # 4. 等待所有进程结束
        for r in async_results:
            try:
                r.get(timeout=300)
            except Exception as exc:
                print(f'  [警告] worker 异常: {exc}')

    total_time = time.time() - overall_start

    print()
    print('=' * 70)
    print('同步完成')
    print(f'总耗时: {_format_duration(total_time)}')
    print(f'成功记录: {success_records:,}')
    print(f'跳过/无数据: {skipped_stocks}')
    print(f'异常: {failed_stocks}')
    print('=' * 70)


if __name__ == '__main__':
    main()
