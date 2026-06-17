"""
股票日线指标路由

提供指标计算、查询等功能。
"""

import logging
import math
from datetime import date, datetime
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session
from ta.momentum import RSIIndicator
from ta.trend import MACD, ADXIndicator
from ta.volatility import BollingerBands

from app import crud, models, schemas
from app.database import get_db
from app.filters import apply_main_board_filter
from app.response import list_success, page_success, success

router = APIRouter(prefix="/stock/indicator", tags=["股票日线指标"])


def _compute_ma(values: List[float], period: int) -> Optional[float]:
    """计算简单移动平均"""
    if len(values) < period:
        return None
    return round(sum(values[:period]) / period, 2)


def _compute_avg(values: List[float], period: int) -> Optional[float]:
    """计算平均值"""
    if len(values) < period:
        return None
    return round(sum(values[:period]) / period, 2)


MISSING_VALUE = -1

INDICATOR_FIELDS = [
    'ma5', 'ma10', 'ma20', 'ma30', 'ma60',
    'vol_ma5', 'vol_ma10', 'amount_ma5', 'amount_ma10',
    'turnover_ma5', 'turnover_ma10', 'chg_5d', 'chg_10d',
    'macd_dif', 'macd_dea', 'macd_hist',
    'rsi_6', 'rsi_12', 'rsi_24',
    'kdj_k', 'kdj_d', 'kdj_j',
    'boll_upper', 'boll_middle', 'boll_lower', 'adx',
]


def _calc_indicator_stats(items: list[dict]) -> dict:
    """统计指标字段有效/缺失数量（MISSING_VALUE 或 None 视为缺失）"""
    stats = {}
    total = len(items)
    for field in INDICATOR_FIELDS:
        valid = sum(1 for item in items if item.get(field) not in (None, MISSING_VALUE))
        missing = total - valid
        stats[field] = {'total': total, 'valid': valid, 'missing': missing}
    return stats


def _build_indicator_for_symbol(
    db: Session,
    symbol: str,
    trade_date: date,
    lookback: int = 30,
    rows: list | None = None,
) -> Optional[dict]:
    """为单只股票计算指定日期的指标。如果传入 rows 则直接使用，否则查询数据库。

    数据不足无法计算时，对应指标写入 MISSING_VALUE（-1），保证每条日线都有一条记录。
    """
    if rows is None:
        rows = (
            db.query(models.StockDaily)
            .filter(
                and_(
                    models.StockDaily.symbol == symbol,
                    models.StockDaily.trade_date <= trade_date,
                )
            )
            .order_by(models.StockDaily.trade_date.desc())
            .limit(lookback)
            .all()
        )

    if not rows:
        logger.debug('[_build_indicator] %s rows empty, trade_date=%s', symbol, trade_date)
        return None

    closes = [r.close for r in rows if r.close is not None]
    volumes = [r.volume for r in rows if r.volume is not None]
    amounts = [r.amount for r in rows if r.amount is not None]
    turnovers = [r.turnover for r in rows if r.turnover is not None]

    # 默认全部填充缺失标记，能算的再覆盖
    result = {
        "ma5": MISSING_VALUE,
        "ma10": MISSING_VALUE,
        "ma20": MISSING_VALUE,
        "ma30": MISSING_VALUE,
        "ma60": MISSING_VALUE,
        "vol_ma5": MISSING_VALUE,
        "vol_ma10": MISSING_VALUE,
        "amount_ma5": MISSING_VALUE,
        "amount_ma10": MISSING_VALUE,
        "turnover_ma5": MISSING_VALUE,
        "turnover_ma10": MISSING_VALUE,
        "chg_5d": MISSING_VALUE,
        "chg_10d": MISSING_VALUE,
        "macd_dif": MISSING_VALUE,
        "macd_dea": MISSING_VALUE,
        "macd_hist": MISSING_VALUE,
        "rsi_6": MISSING_VALUE,
        "rsi_12": MISSING_VALUE,
        "rsi_24": MISSING_VALUE,
        "kdj_k": MISSING_VALUE,
        "kdj_d": MISSING_VALUE,
        "kdj_j": MISSING_VALUE,
        "boll_upper": MISSING_VALUE,
        "boll_middle": MISSING_VALUE,
        "boll_lower": MISSING_VALUE,
        "adx": MISSING_VALUE,
    }

    if not closes:
        logger.debug('[_build_indicator] %s closes empty, rows=%s, write placeholder', symbol, len(rows))
        return result

    # 均线
    result['ma5'] = _compute_ma(closes, 5)
    result['ma10'] = _compute_ma(closes, 10)
    result['ma20'] = _compute_ma(closes, 20)
    result['ma30'] = _compute_ma(closes, 30)
    result['ma60'] = _compute_ma(closes, 60)

    # 成交量/成交额/换手率均线
    if len(volumes) >= 5:
        result['vol_ma5'] = int(_compute_avg(volumes, 5))
    if len(volumes) >= 10:
        result['vol_ma10'] = int(_compute_avg(volumes, 10))
    if len(amounts) >= 5:
        result['amount_ma5'] = int(_compute_avg(amounts, 5))
    if len(amounts) >= 10:
        result['amount_ma10'] = int(_compute_avg(amounts, 10))
    if len(turnovers) >= 5:
        result['turnover_ma5'] = _compute_avg(turnovers, 5)
    if len(turnovers) >= 10:
        result['turnover_ma10'] = _compute_avg(turnovers, 10)

    # 涨跌幅
    if len(closes) >= 5 and closes[4] != 0:
        result['chg_5d'] = round((closes[0] - closes[4]) / closes[4] * 100, 2)
    if len(closes) >= 10 and closes[9] != 0:
        result['chg_10d'] = round((closes[0] - closes[9]) / closes[9] * 100, 2)

    # 使用 ta 库计算高级指标（需要至少 26 条数据）
    valid_rows = [r for r in rows if r.close is not None]
    if len(valid_rows) >= 26:
        rows_asc = valid_rows[::-1]  # 转为升序
        df = pd.DataFrame({
            'close': [r.close for r in rows_asc],
            'high': [r.high if r.high is not None else r.close for r in rows_asc],
            'low': [r.low if r.low is not None else r.close for r in rows_asc],
        })

        if len(df) >= 26 and df['close'].notna().all():
            # MACD
            try:
                macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
                result['macd_dif'] = float(round(macd.macd().iloc[-1], 4))
                result['macd_dea'] = float(round(macd.macd_signal().iloc[-1], 4))
                result['macd_hist'] = float(round(macd.macd_diff().iloc[-1], 4))
            except Exception as exc:
                logger.debug('[INDICATOR] MACD 计算失败 %s: %s', symbol, exc)

            # RSI
            try:
                rsi_6 = RSIIndicator(close=df['close'], window=6)
                rsi_12 = RSIIndicator(close=df['close'], window=12)
                rsi_24 = RSIIndicator(close=df['close'], window=24)
                result['rsi_6'] = float(round(rsi_6.rsi().iloc[-1], 2))
                result['rsi_12'] = float(round(rsi_12.rsi().iloc[-1], 2))
                result['rsi_24'] = float(round(rsi_24.rsi().iloc[-1], 2))
            except Exception as exc:
                logger.debug('[INDICATOR] RSI 计算失败 %s: %s', symbol, exc)

            # BOLL
            try:
                bb = BollingerBands(close=df['close'], window=20, window_dev=2)
                result['boll_upper'] = float(round(bb.bollinger_hband().iloc[-1], 2))
                result['boll_middle'] = float(round(bb.bollinger_mavg().iloc[-1], 2))
                result['boll_lower'] = float(round(bb.bollinger_lband().iloc[-1], 2))
            except Exception as exc:
                logger.debug('[INDICATOR] BOLL 计算失败 %s: %s', symbol, exc)

            # KDJ
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
            except Exception as exc:
                logger.debug('[INDICATOR] KDJ 计算失败 %s: %s', symbol, exc)

            # ADX
            try:
                if (len(df) >= 30 and df['high'].notna().all() and df['low'].notna().all()
                        and len(df[df['high'] > df['low']]) >= 20):
                    adx_ind = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
                    adx_val = adx_ind.adx().iloc[-1]
                    if pd.notna(adx_val):
                        result['adx'] = float(round(adx_val, 2))
            except Exception as exc:
                logger.debug('[INDICATOR] ADX 计算失败 %s: %s', symbol, exc)

    # 将 NaN / inf 替换为 None，避免 MySQL 写入失败
    for key in list(result.keys()):
        val = result[key]
        if val is not None and isinstance(val, float) and not math.isfinite(val):
            result[key] = None

    return result


# 3.0 计算指定日期的指标数据
@router.post("/compute")
def compute_indicators(
    trade_date: str = Query(..., description="交易日期，格式 YYYY-MM-DD 或 YYYYMMDD"),
    db: Session = Depends(get_db),
):
    """计算指定交易日所有主板的日线指标并入库"""
    formatted_date = trade_date.replace("-", "")
    trade_date_obj = datetime.strptime(formatted_date, '%Y%m%d').date()

    # 验证交易日期是否存在
    exists = (
        db.query(models.StockDaily)
        .filter(models.StockDaily.trade_date == trade_date_obj)
        .first()
    )
    if not exists:
        raise HTTPException(status_code=404, detail=f"交易日期 {trade_date} 无数据")

    # 获取该日期所有股票代码
    symbols = [
        row[0] for row in
        db.query(models.StockDaily.symbol)
        .filter(models.StockDaily.trade_date == trade_date_obj)
        .distinct()
        .all()
    ]

    if not symbols:
        return success({
            "trade_date": trade_date,
            "total": 0,
            "success": 0,
            "failed": 0,
        })

    total = len(symbols)
    success_count = 0
    failed_count = 0
    items = []

    # 批量预查询所有股票的历史数据，避免 N+1
    all_rows = (
        db.query(models.StockDaily)
        .filter(
            models.StockDaily.symbol.in_(symbols),
            models.StockDaily.trade_date <= trade_date_obj,
        )
        .order_by(models.StockDaily.symbol, models.StockDaily.trade_date.desc())
        .all()
    )
    rows_by_symbol: dict[str, list] = {}
    for row in all_rows:
        symbol_rows = rows_by_symbol.setdefault(row.symbol, [])
        if len(symbol_rows) < 60:
            symbol_rows.append(row)

    for symbol in symbols:
        indicator_data = _build_indicator_for_symbol(
            db, symbol, trade_date_obj, rows=rows_by_symbol.get(symbol)
        )
        if indicator_data is None:
            failed_count += 1
            continue
        indicator_data["symbol"] = symbol
        indicator_data["trade_date"] = trade_date_obj
        items.append(indicator_data)
        success_count += 1

    # 批量写入（逐条 upsert，避免一次性事务过大）
    indicator_stats = {}
    if items:
        result = crud.stock_daily_indicator_crud.create_or_update_batch(db, items)
        success_count = result["success"]
        failed_count = result["failed"]
        indicator_stats = _calc_indicator_stats(items)

    db.commit()
    return success({
        "trade_date": trade_date,
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "indicator_stats": indicator_stats,
    })


