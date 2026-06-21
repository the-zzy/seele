"""
股票日线数据路由

包含 CRUD、按日期/股票/范围查询等基础查询。
选股策略已拆分至 routes.pickers，市场情绪已拆分至 routes.market_sentiment。
"""

import concurrent.futures
import logging
import socket
import threading
from datetime import date, datetime
from typing import Dict, List, Optional

import akshare as ak
import baostock as bs
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.akshare_lock import akshare_lock
from app.database import get_db
from app.filters import apply_main_board_filter, get_baostock_code
from app.response import list_success, page_success, success
from app.schemas import StockDailyResponse

logger = logging.getLogger(__name__)

# akshare 全量实时行情缓存（30 秒 TTL）
_akshare_spot_cache: dict = {"df": None, "ts": 0}
_AKSHARE_CACHE_TTL = 30  # 秒
_akshare_cache_lock = threading.Lock()


def _refresh_live_price_cache():
    """强制刷新 akshare 全量实时行情缓存（用于启动预热）"""
    global _akshare_spot_cache
    with _akshare_cache_lock:
        _akshare_spot_cache = {"df": None, "ts": 0}
    import time
    now = time.time()
    try:
        with akshare_lock:
            df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            _akshare_spot_cache = {"df": df, "ts": now}
            logger.info('[WARMUP] 实时股价缓存已预热，共 %d 条', len(df))
            return True
    except Exception as exc:
        logger.warning('[WARMUP] 预热实时股价缓存失败: %s', exc)
    return False


router = APIRouter(prefix="/stock/daily", tags=["股票日线数据"])


def _build_daily_indicator_item(row) -> dict:
    """将 (StockDaily, indicator_fields...) 查询结果组装为统一字典"""
    daily = row[0]
    return {
        "id": daily.id,
        "trade_date": str(daily.trade_date),
        "symbol": daily.symbol,
        "open": daily.open,
        "high": daily.high,
        "low": daily.low,
        "close": daily.close,
        "volume": daily.volume,
        "amount": daily.amount,
        "amplitude": daily.amplitude,
        "pct_chg": daily.pct_chg,
        "price_change": daily.price_change,
        "turnover": daily.turnover,
        "ma5": row[1] if len(row) > 1 else None,
        "ma10": row[2] if len(row) > 2 else None,
        "ma20": row[3] if len(row) > 3 else None,
        "ma30": row[4] if len(row) > 4 else None,
        "ma60": row[5] if len(row) > 5 else None,
        "vol_ma5": row[6] if len(row) > 6 else None,
        "vol_ma10": row[7] if len(row) > 7 else None,
        "turnover_ma5": row[8] if len(row) > 8 else None,
        "turnover_ma10": row[9] if len(row) > 9 else None,
    }


# 2.1 根据交易日期获取全部A股数据（关联basic表及指标表）— 服务端分页
@router.get("/date/{trade_date}/all")
def get_stock_daily_all_by_date(
    trade_date: str,
    exclude_st: bool = Query(False, description="是否过滤ST股票"),
    exclude_cyb: bool = Query(False, description="是否过滤创业板"),
    exclude_kcb: bool = Query(False, description="是否过滤科创板"),
    exclude_bse: bool = Query(False, description="是否过滤北交所"),
    symbol: Optional[str] = Query(None, description="代码或名称模糊搜索"),
    min_pct_chg: Optional[float] = Query(None, description="最小涨幅百分比过滤"),
    sort_field: str = Query("symbol", description="排序字段"),
    sort_order: str = Query("asc", description="排序方向 asc/desc"),
    page_num: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=500, description="每页条数"),
    db: Session = Depends(get_db),
):
    """根据交易日期分页获取A股数据（关联 stock_basic 及 stock_daily_indicator）"""
    formatted_date = trade_date.replace("-", "")

    # 使用 STRAIGHT_JOIN 强制 MySQL 按 FROM 子句顺序执行 JOIN，
    # 避免优化器误选 stock_basic 作为驱动表导致全表扫描。
    q = (
        db.query(
            models.StockDaily,
            models.StockDailyIndicator.ma5,
            models.StockDailyIndicator.ma10,
            models.StockDailyIndicator.ma20,
            models.StockDailyIndicator.ma30,
            models.StockDailyIndicator.ma60,
            models.StockDailyIndicator.vol_ma5,
            models.StockDailyIndicator.vol_ma10,
            models.StockDailyIndicator.turnover_ma5,
            models.StockDailyIndicator.turnover_ma10,
            models.StockBasic.name.label("stock_name"),
            models.StockBasic.industry,
            models.StockBasic.market,
            models.StockBasic.area,
        )
        .prefix_with('STRAIGHT_JOIN')
        .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
        .outerjoin(
            models.StockDailyIndicator,
            and_(
                models.StockDaily.symbol == models.StockDailyIndicator.symbol,
                models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
            ),
        )
    )
    q = apply_main_board_filter(q).filter(
        models.StockDaily.trade_date == formatted_date,
    )

    if exclude_st:
        q = q.filter(~models.StockBasic.name.like('%ST%'))
    if exclude_cyb:
        q = q.filter(
            models.StockBasic.symbol.notlike("300%"),
            models.StockBasic.symbol.notlike("301%"),
        )
    if exclude_kcb:
        q = q.filter(
            models.StockBasic.symbol.notlike("688%"),
            models.StockBasic.symbol.notlike("689%"),
        )
    if exclude_bse:
        q = q.filter(
            models.StockBasic.symbol.notlike("4%"),
            models.StockBasic.symbol.notlike("8%"),
        )
    if symbol:
        like_pattern = f"%{symbol}%"
        q = q.filter(
            or_(
                models.StockDaily.symbol.like(like_pattern),
                models.StockBasic.name.like(like_pattern),
            )
        )
    if min_pct_chg is not None:
        q = q.filter(models.StockDaily.pct_chg > min_pct_chg)

    # 优化 COUNT：用子查询替代 JOIN，避免大表 JOIN 开销
    basic_subq = db.query(models.StockBasic.symbol).filter(
        models.StockBasic.market == "主板",
        ~models.StockBasic.name.like('%ST%'),
    )
    if exclude_cyb:
        basic_subq = basic_subq.filter(
            models.StockBasic.symbol.notlike("300%"),
            models.StockBasic.symbol.notlike("301%"),
        )
    if exclude_kcb:
        basic_subq = basic_subq.filter(
            models.StockBasic.symbol.notlike("688%"),
            models.StockBasic.symbol.notlike("689%"),
        )
    if exclude_bse:
        basic_subq = basic_subq.filter(
            models.StockBasic.symbol.notlike("4%"),
            models.StockBasic.symbol.notlike("8%"),
        )
    if symbol:
        like_pattern = f"%{symbol}%"
        basic_subq = basic_subq.filter(
            or_(
                models.StockBasic.symbol.like(like_pattern),
                models.StockBasic.name.like(like_pattern),
            )
        )

    count_q = db.query(models.StockDaily).filter(
        models.StockDaily.trade_date == formatted_date,
        models.StockDaily.symbol.in_(basic_subq),
    )
    if min_pct_chg is not None:
        count_q = count_q.filter(models.StockDaily.pct_chg > min_pct_chg)
    total = count_q.with_entities(func.count(models.StockDaily.id)).scalar() or 0

    # 排序映射
    sort_column_map = {
        'symbol': models.StockDaily.symbol,
        'stock_name': models.StockBasic.name,
        'open': models.StockDaily.open,
        'high': models.StockDaily.high,
        'low': models.StockDaily.low,
        'close': models.StockDaily.close,
        'volume': models.StockDaily.volume,
        'amount': models.StockDaily.amount,
        'amplitude': models.StockDaily.amplitude,
        'pct_chg': models.StockDaily.pct_chg,
        'price_change': models.StockDaily.price_change,
        'turnover': models.StockDaily.turnover,
        'ma5': models.StockDailyIndicator.ma5,
        'ma10': models.StockDailyIndicator.ma10,
        'ma20': models.StockDailyIndicator.ma20,
        'ma30': models.StockDailyIndicator.ma30,
        'ma60': models.StockDailyIndicator.ma60,
        'vol_ma5': models.StockDailyIndicator.vol_ma5,
        'vol_ma10': models.StockDailyIndicator.vol_ma10,
        'turnover_ma5': models.StockDailyIndicator.turnover_ma5,
        'turnover_ma10': models.StockDailyIndicator.turnover_ma10,
    }
    sort_column = sort_column_map.get(sort_field, models.StockDaily.symbol)
    if sort_order == 'desc':
        q = q.order_by(sort_column.desc())
    else:
        q = q.order_by(sort_column.asc())

    # 分页
    results = (
        q.offset((page_num - 1) * page_size)
        .limit(page_size)
        .all()
    )

    data_list = []
    for row in results:
        item = _build_daily_indicator_item(row)
        item.update({
            'stock_name': row[10] if len(row) > 10 else '',
            'industry': row[11] if len(row) > 11 else '',
            'market': row[12] if len(row) > 12 else '',
            'area': row[13] if len(row) > 13 else '',
        })
        data_list.append(item)

    return page_success(
        items=data_list,
        total=total,
        page_num=page_num,
        page_size=page_size,
        trade_date=trade_date,
    )


# 2.2 批量获取指定日期收盘价（轻量接口）
# 注意：必须放在 /symbol/{symbol} 动态路由之前，否则会被后者匹配为 symbol="close"。
@router.get('/close')
def get_stock_daily_close(
    symbols: str = Query(..., description='股票代码，逗号分隔'),
    trade_date: str = Query(..., description='交易日期 YYYY-MM-DD'),
    db: Session = Depends(get_db),
):
    """批量获取指定股票在指定日期的收盘价，仅返回 close 和 trade_date"""
    symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail='symbols 不能为空')

    formatted_date = trade_date.replace('-', '')
    rows = (
        db.query(models.StockDaily.symbol, models.StockDaily.close, models.StockDaily.trade_date)
        .filter(
            models.StockDaily.symbol.in_(symbol_list),
            models.StockDaily.trade_date == formatted_date,
        )
        .all()
    )
    return success({
        row[0]: {
            'close': float(row[1]) if row[1] is not None else None,
            'trade_date': str(row[2]),
        }
        for row in rows
    })


# 2.3 根据股票代码查询全部日线数据（关联指标表）
@router.get("/symbol/{symbol}")
def get_stock_daily_by_symbol(
    symbol: str,
    db: Session = Depends(get_db),
):
    """根据股票代码查询全部历史日线数据（关联 stock_daily_indicator）"""
    results = (
        db.query(
            models.StockDaily,
            models.StockDailyIndicator.ma5,
            models.StockDailyIndicator.ma10,
            models.StockDailyIndicator.ma20,
            models.StockDailyIndicator.ma30,
            models.StockDailyIndicator.ma60,
            models.StockDailyIndicator.vol_ma5,
            models.StockDailyIndicator.vol_ma10,
            models.StockDailyIndicator.turnover_ma5,
            models.StockDailyIndicator.turnover_ma10,
        )
        .outerjoin(
            models.StockDailyIndicator,
            and_(
                models.StockDaily.symbol == models.StockDailyIndicator.symbol,
                models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
            ),
        )
        .filter(models.StockDaily.symbol == symbol)
        .order_by(models.StockDaily.trade_date.asc())
        .all()
    )

    data_list = [_build_daily_indicator_item(row) for row in results]
    return list_success(data_list)

