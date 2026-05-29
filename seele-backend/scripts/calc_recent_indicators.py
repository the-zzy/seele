#!/usr/bin/env python3
"""
独立脚本：计算最近 20 个交易日的日线指标（多进程优化版）

与项目代码完全解耦，可直接运行：
    .venv/Scripts/python scripts/calc_recent_indicators.py

优化点：
    - 一次大查询加载全部所需数据，避免 N+1
    - 多进程并行（ProcessPoolExecutor），绕过 GIL，CPU 计算真正并行
    - 按 symbol 分组计算，减少数据重复准备
    - 批量写入，减少 commit 次数
"""

import concurrent.futures
import logging
import math
import os
import sys
import time
from datetime import date, timedelta
from multiprocessing import cpu_count

import pandas as pd
from sqlalchemy import (
    BigInteger, Column, Date, Float, Integer, String, UniqueConstraint,
    create_engine
)
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import declarative_base, sessionmaker

# ta 库
try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, ADXIndicator
    from ta.volatility import BollingerBands
except ImportError:
    print('请先安装 ta 库: pip install ta')
    sys.exit(1)

# ==================== 配置区 ====================

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '20020228')
DB_NAME = os.environ.get('DB_NAME', 'seele')

NUM_WORKERS = int(os.environ.get('MAX_WORKERS', min(cpu_count() or 4, 16)))
LOOKBACK = 60
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


# ==================== 计算函数（worker 内调用，纯函数） ====================


def _compute_ma(values, period):
    if len(values) < period:
        return None
    return round(sum(values[:period]) / period, 2)


def _compute_avg(values, period):
    if len(values) < period:
        return None
    return round(sum(values[:period]) / period, 2)


def _build_indicator(records):
    """records 为纯 dict 列表，按 trade_date desc 排序"""
    if not records:
        return None

    closes = [r['close'] for r in records if r['close'] is not None]
    volumes = [r['volume'] for r in records if r['volume'] is not None]
    amounts = [r['amount'] for r in records if r['amount'] is not None]
    turnovers = [r['turnover'] for r in records if r['turnover'] is not None]

    if not closes:
        return None

    result = {
        'ma5': _compute_ma(closes, 5),
        'ma10': _compute_ma(closes, 10),
        'ma20': _compute_ma(closes, 20),
        'ma30': _compute_ma(closes, 30),
        'ma60': _compute_ma(closes, 60),
        'vol_ma5': int(_compute_avg(volumes, 5)) if len(volumes) >= 5 else None,
        'vol_ma10': int(_compute_avg(volumes, 10)) if len(volumes) >= 10 else None,
        'amount_ma5': int(_compute_avg(amounts, 5)) if len(amounts) >= 5 else None,
        'amount_ma10': int(_compute_avg(amounts, 10)) if len(amounts) >= 10 else None,
        'turnover_ma5': _compute_avg(turnovers, 5) if len(turnovers) >= 5 else None,
        'turnover_ma10': _compute_avg(turnovers, 10) if len(turnovers) >= 10 else None,
        'chg_5d': round((closes[0] - closes[4]) / closes[4] * 100, 2) if len(closes) >= 5 and closes[4] != 0 else None,
        'chg_10d': round((closes[0] - closes[9]) / closes[9] * 100, 2) if len(closes) >= 10 and closes[9] != 0 else None,
        'macd_dif': None,
        'macd_dea': None,
        'macd_hist': None,
        'rsi_6': None,
        'rsi_12': None,
        'rsi_24': None,
        'kdj_k': None,
        'kdj_d': None,
        'kdj_j': None,
        'boll_upper': None,
        'boll_middle': None,
        'boll_lower': None,
        'adx': None,
    }

    if len(closes) >= 26:
        df = pd.DataFrame({
            'close': closes[::-1],
            'high': [r['high'] for r in records[::-1] if r['high'] is not None],
            'low': [r['low'] for r in records[::-1] if r['low'] is not None],
        })

        if len(df) >= 26 and df['close'].notna().all():
            try:
                macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
                result['macd_dif'] = float(round(macd.macd().iloc[-1], 4))
                result['macd_dea'] = float(round(macd.macd_signal().iloc[-1], 4))
                result['macd_hist'] = float(round(macd.macd_diff().iloc[-1], 4))
            except Exception:
                pass

            try:
                rsi_6 = RSIIndicator(close=df['close'], window=6)
                rsi_12 = RSIIndicator(close=df['close'], window=12)
                rsi_24 = RSIIndicator(close=df['close'], window=24)
                result['rsi_6'] = float(round(rsi_6.rsi().iloc[-1], 2))
                result['rsi_12'] = float(round(rsi_12.rsi().iloc[-1], 2))
                result['rsi_24'] = float(round(rsi_24.rsi().iloc[-1], 2))
            except Exception:
                pass

            try:
                bb = BollingerBands(close=df['close'], window=20, window_dev=2)
                result['boll_upper'] = float(round(bb.bollinger_hband().iloc[-1], 2))
                result['boll_middle'] = float(round(bb.bollinger_mavg().iloc[-1], 2))
                result['boll_lower'] = float(round(bb.bollinger_lband().iloc[-1], 2))
            except Exception:
                pass

            try:
                if len(df) >= 9 and df['high'].notna().all() and df['low'].notna().all():
                    low_list = df['low'].rolling(window=9, min_periods=9).min()
                    high_list = df['high'].rolling(window=9, min_periods=9).max()
                    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
                    k = rsv.ewm(com=2, adjust=False).mean()
                    d = k.ewm(com=2, adjust=False).mean()
                    j = 3 * k - 2 * d
                    result['kdj_k'] = float(round(k.iloc[-1], 2))
                    result['kdj_d'] = float(round(d.iloc[-1], 2))
                    result['kdj_j'] = float(round(j.iloc[-1], 2))
            except Exception:
                pass

            try:
                if (len(df) >= 30 and df['high'].notna().all() and df['low'].notna().all()
                        and len(df[df['high'] > df['low']]) >= 20):
                    adx_ind = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
                    adx_val = adx_ind.adx().iloc[-1]
                    if pd.notna(adx_val):
                        result['adx'] = float(round(adx_val, 2))
            except Exception:
                pass

    for key in list(result.keys()):
        val = result[key]
        if val is not None and isinstance(val, float) and not math.isfinite(val):
            result[key] = None

    return result


def _worker_calc(args):
    """进程 worker：计算单个 symbol 在最近多个交易日的指标"""
    symbol, trade_dates, all_records = args

    results = []
    for td in trade_dates:
        # 过滤出 <= td 的数据，降序，取前 LOOKBACK 条
        records = [r for r in all_records if r['trade_date'] <= td]
        records.sort(key=lambda r: r['trade_date'], reverse=True)
        records = records[:LOOKBACK]

        indicator_data = _build_indicator(records)
        if indicator_data is None:
            continue
        indicator_data['symbol'] = symbol
        indicator_data['trade_date'] = td
        results.append(indicator_data)

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
        # 1. 获取最近 20 个交易日
        trade_date_rows = (
            session.query(StockDaily.trade_date)
            .distinct()
            .order_by(StockDaily.trade_date.desc())
            .limit(20)
            .all()
        )
        trade_dates = sorted([r[0] for r in trade_date_rows])
        if not trade_dates:
            logger.info('stock_daily 表无数据')
            return

        logger.info('最近 20 个交易日: %s', [d.strftime('%Y%m%d') for d in trade_dates])

        # 2. 一次性加载全部所需原始数据（最近 20 日 + 前面 90 天历史用于指标计算）
        oldest_date = trade_dates[0] - timedelta(days=90)
        latest_date = trade_dates[-1]

        logger.info('开始加载原始数据 %s ~ %s ...', oldest_date.strftime('%Y%m%d'), latest_date.strftime('%Y%m%d'))
        t0 = time.time()

        all_rows = (
            session.query(StockDaily)
            .filter(
                StockDaily.trade_date >= oldest_date,
                StockDaily.trade_date <= latest_date,
            )
            .all()
        )

        # 3. 按 symbol 分组，截断到 LOOKBACK 条，并序列化为纯 dict（可 pickle）
        raw_by_symbol = {}
        for row in all_rows:
            raw_by_symbol.setdefault(row.symbol, []).append(row)

        records_by_symbol = {}
        trade_dates_by_symbol = {}
        trade_dates_set = set(trade_dates)

        for symbol, rows in raw_by_symbol.items():
            rows.sort(key=lambda r: r.trade_date, reverse=True)
            rows = rows[:LOOKBACK + 20]  # 多留一点，worker 内再精确过滤

            records_by_symbol[symbol] = [
                {
                    'trade_date': r.trade_date,
                    'open': r.open,
                    'high': r.high,
                    'low': r.low,
                    'close': r.close,
                    'volume': r.volume,
                    'amount': r.amount,
                    'turnover': r.turnover,
                }
                for r in rows
            ]

            # 该 symbol 在最近 20 个交易日中有数据的日期
            tds = sorted({r.trade_date for r in rows if r.trade_date in trade_dates_set})
            if tds:
                trade_dates_by_symbol[symbol] = tds

        load_time = time.time() - t0
        total_symbols = len(trade_dates_by_symbol)
        logger.info('数据加载完成: %d 只, 耗时 %.2fs', total_symbols, load_time)

        if total_symbols == 0:
            logger.info('没有需要计算的股票')
            return

        # 4. 组装任务列表
        tasks = [
            (symbol, trade_dates_by_symbol[symbol], records_by_symbol[symbol])
            for symbol in trade_dates_by_symbol
        ]

        # 5. 多进程计算
        logger.info('开始计算指标，进程数: %d ...', NUM_WORKERS)
        overall_start = time.time()
        all_items = []
        processed = [0]
        success_count = [0]
        failed_count = [0]

        def _on_done(future):
            try:
                results = future.result()
                if results:
                    all_items.extend(results)
                    success_count[0] += len(results)
                else:
                    failed_count[0] += 1
            except Exception as exc:
                logger.error('worker 异常: %s', exc)
                failed_count[0] += 1
            finally:
                processed[0] += 1
                current = processed[0]
                if current % 50 == 0 or current == total_symbols:
                    elapsed = time.time() - overall_start
                    speed = current / elapsed if elapsed > 0 else 0
                    eta = (total_symbols - current) / speed if speed > 0 else 0
                    pct = current / total_symbols * 100
                    logger.info(
                        '[%5d/%d %5.1f%%] 速度 %.1f只/s ETA %.0fs | '
                        '成功记录 %d',
                        current, total_symbols, pct, speed, eta, success_count[0]
                    )
                    sys.stdout.flush()

        with concurrent.futures.ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
            for task in tasks:
                future = executor.submit(_worker_calc, task)
                future.add_done_callback(_on_done)

            # 等待全部完成
            executor.shutdown(wait=True)

        # 6. 批量写入
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
        logger.info('失败: %d', failed_count[0])
        logger.info('=' * 60)

    finally:
        session.close()


if __name__ == '__main__':
    main()
