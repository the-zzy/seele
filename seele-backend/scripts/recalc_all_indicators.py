#!/usr/bin/env python3
"""
独立脚本：全量重算所有历史日线指标（多进程向量化版，基础指标）

只计算 20 日内可完成的基础指标：
    MA5/10/20, vol_ma5/10, amount_ma5/10, turnover_ma5/10, chg_5d/10d

与项目代码完全解耦，可直接运行：
    .venv/Scripts/python scripts/recalc_all_indicators.py

前置：
    如需清空旧指标数据，先执行：
        TRUNCATE TABLE stock_daily_indicator;
"""

import logging
import math
import os
import sys
import time
from multiprocessing import cpu_count

import pandas as pd
from sqlalchemy import (
    BigInteger, Column, Date, Float, Integer, String, UniqueConstraint,
    create_engine
)
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import declarative_base, sessionmaker

# ==================== 配置区 ====================

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '20020228')
DB_NAME = os.environ.get('DB_NAME', 'seele')

NUM_WORKERS = int(os.environ.get('MAX_WORKERS', min(cpu_count() or 4, 16)))
BATCH_WRITE_SIZE = 5000

DATABASE_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

Base = declarative_base()


# ==================== 数据库模型 ====================


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
    turnover = Column(Float)


class StockDailyIndicator(Base):
    __tablename__ = 'stock_daily_indicator'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma30 = Column(Float)
    ma60 = Column(Float)
    vol_ma5 = Column(BigInteger)
    vol_ma10 = Column(BigInteger)
    amount_ma5 = Column(BigInteger)
    amount_ma10 = Column(BigInteger)
    turnover_ma5 = Column(Float)
    turnover_ma10 = Column(Float)
    chg_5d = Column(Float)
    chg_10d = Column(Float)
    macd_dif = Column(Float)
    macd_dea = Column(Float)
    macd_hist = Column(Float)
    rsi_6 = Column(Float)
    rsi_12 = Column(Float)
    rsi_24 = Column(Float)
    kdj_k = Column(Float)
    kdj_d = Column(Float)
    kdj_j = Column(Float)
    boll_upper = Column(Float)
    boll_middle = Column(Float)
    boll_lower = Column(Float)
    adx = Column(Float)

    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', name='uq_indicator_trade_date_symbol'),
    )


# ==================== 计算函数 ====================


def _calc_symbol(args):
    """进程 worker：计算单只股票完整历史（基础指标，向量化）"""
    symbol, = args

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=2,
        max_overflow=2,
        echo=False,
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        rows = (
            session.query(StockDaily)
            .filter(StockDaily.symbol == symbol)
            .order_by(StockDaily.trade_date.asc())
            .all()
        )
    finally:
        session.close()

    if len(rows) < 5:
        return []

    df = pd.DataFrame([
        {
            'trade_date': r.trade_date,
            'close': r.close,
            'volume': r.volume,
            'amount': r.amount,
            'turnover': r.turnover,
        }
        for r in rows
    ])

    # 基础指标（向量化，只用 20 日内可算的）
    df['ma5'] = df['close'].rolling(window=5).mean().round(2)
    df['ma10'] = df['close'].rolling(window=10).mean().round(2)
    df['ma20'] = df['close'].rolling(window=20).mean().round(2)

    df['vol_ma5'] = df['volume'].rolling(window=5).mean().round(0)
    df['vol_ma10'] = df['volume'].rolling(window=10).mean().round(0)
    df['amount_ma5'] = df['amount'].rolling(window=5).mean().round(0)
    df['amount_ma10'] = df['amount'].rolling(window=10).mean().round(0)
    df['turnover_ma5'] = df['turnover'].rolling(window=5).mean().round(2)
    df['turnover_ma10'] = df['turnover'].rolling(window=10).mean().round(2)

    df['chg_5d'] = ((df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100).round(2)
    df['chg_10d'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100).round(2)

    output_cols = [
        'trade_date',
        'ma5', 'ma10', 'ma20',
        'vol_ma5', 'vol_ma10',
        'amount_ma5', 'amount_ma10',
        'turnover_ma5', 'turnover_ma10',
        'chg_5d', 'chg_10d',
    ]

    results = []
    for _, row in df.iterrows():
        record = {'symbol': symbol}
        for col in output_cols:
            val = row.get(col)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                record[col] = None
            elif hasattr(val, 'item'):
                record[col] = val.item()
            else:
                record[col] = val
        results.append(record)

    return results


# ==================== 主进程 ====================


def _upsert_batch(session, records):
    if not records:
        return
    stmt = insert(StockDailyIndicator).values(records)
    update_dict = {
        k: stmt.inserted[k]
        for k in stmt.inserted.keys()
        if k not in ('id', 'trade_date', 'symbol')
    }
    stmt = stmt.on_duplicate_key_update(**update_dict)
    session.execute(stmt)
    session.commit()


def main():
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=10,
        echo=False,
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        symbol_rows = session.query(StockDaily.symbol).distinct().all()
        all_symbols = sorted([r[0] for r in symbol_rows])
        total = len(all_symbols)

        logger.info('=' * 60)
        logger.info('开始全量指标重算（基础指标，多进程向量化）')
        logger.info('进程数: %d', NUM_WORKERS)
        logger.info('股票数: %d', total)
        logger.info('=' * 60)

        if total == 0:
            logger.info('stock_daily 表无数据')
            return

        overall_start = time.time()
        all_items = []
        processed = [0]
        success_count = [0]

        import concurrent.futures

        def _on_done(future):
            try:
                results = future.result()
                if results:
                    all_items.extend(results)
                    success_count[0] += len(results)
            except Exception as exc:
                logger.error('worker 异常: %s', exc)
            finally:
                processed[0] += 1
                current = processed[0]
                if current % 50 == 0 or current == total:
                    elapsed = time.time() - overall_start
                    speed = current / elapsed if elapsed > 0 else 0
                    eta = (total - current) / speed if speed > 0 else 0
                    pct = current / total * 100
                    logger.info(
                        '[%5d/%d %5.1f%%] 速度 %.1f只/s ETA %.0fs | 成功记录 %d',
                        current, total, pct, speed, eta, success_count[0]
                    )
                    sys.stdout.flush()

        with concurrent.futures.ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
            for symbol in all_symbols:
                future = executor.submit(_calc_symbol, (symbol,))
                future.add_done_callback(_on_done)
            executor.shutdown(wait=True)

        if all_items:
            logger.info('开始批量写入 %d 条指标数据...', len(all_items))
            t_write = time.time()
            batch = []
            for item in all_items:
                batch.append(item)
                if len(batch) >= BATCH_WRITE_SIZE:
                    _upsert_batch(session, batch)
                    batch = []
            if batch:
                _upsert_batch(session, batch)
            logger.info('写入完成，耗时 %.2fs', time.time() - t_write)

        total_time = time.time() - overall_start
        logger.info('=' * 60)
        logger.info('全部完成')
        logger.info('总耗时: %.1fs (%.1f分钟)', total_time, total_time / 60)
        logger.info('成功记录: %d', success_count[0])
        logger.info('=' * 60)

    finally:
        session.close()


if __name__ == '__main__':
    main()
