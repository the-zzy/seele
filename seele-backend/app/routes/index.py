"""
指数数据路由
"""

import logging
import threading
import time
from typing import Optional

import akshare as ak

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app import models, schemas
from app.akshare_lock import akshare_lock
from app.database import get_db
from app.response import page_success, success

# 指数实时数据缓存（30 秒 TTL）
_index_spot_cache: dict = {"df": None, "ts": 0}
_INDEX_CACHE_TTL = 30  # 秒
_index_cache_lock = threading.Lock()


def _fetch_index_spot_df():
    """获取 akshare 指数实时 DataFrame，带 30 秒缓存（失败也缓存 None，避免反复重试）"""
    global _index_spot_cache
    now = time.time()
    with _index_cache_lock:
        if (now - _index_spot_cache.get("ts", 0)) < _INDEX_CACHE_TTL:
            return _index_spot_cache.get("df")

    try:
        with akshare_lock:
            df = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
        with _index_cache_lock:
            _index_spot_cache = {"df": df, "ts": now}
        return df
    except Exception as exc:
        logger.warning('[INDEX] 获取指数实时数据失败: %s', exc)
        with _index_cache_lock:
            _index_spot_cache = {"df": None, "ts": now}
        return None


def _refresh_index_spot_cache():
    """强制刷新指数实时数据缓存（用于启动预热）"""
    global _index_spot_cache
    with _index_cache_lock:
        _index_spot_cache["df"] = None
        _index_spot_cache["ts"] = 0
    return _fetch_index_spot_df()


router = APIRouter(prefix="/index", tags=["指数数据"])

# 指数名称到 akshare 名称的映射
INDEX_NAME_MAP = {
    'sh.000001': '上证指数',
    'sz.399001': '深证成指',
    'sz.399006': '创业板指',
    'sh.000300': '沪深300',
    'sh.000016': '上证50',
    'sh.000905': '中证500',
}


@router.get("/list")
def get_index_list(db: Session = Depends(get_db)):
    """返回支持的主要指数列表及最新实时数据"""
    result = []
    spot_df = None

    # 优先尝试 akshare 实时数据（带 30 秒缓存）
    spot_df = _fetch_index_spot_df()

    # 2. 无实时数据时 fallback 数据库：一次性批量查询所有指数最新数据
    symbol_list = list(INDEX_NAME_MAP.keys())
    latest_map = {}
    if spot_df is None or spot_df.empty:
        subq = (
            db.query(
                models.IndexDaily.symbol,
                func.max(models.IndexDaily.trade_date).label('max_date')
            )
            .filter(models.IndexDaily.symbol.in_(symbol_list))
            .group_by(models.IndexDaily.symbol)
            .subquery()
        )
        latest_rows = (
            db.query(
                models.IndexDaily.symbol,
                models.IndexDaily.trade_date,
                models.IndexDaily.close,
                models.IndexDaily.pct_chg
            )
            .join(subq, and_(
                models.IndexDaily.symbol == subq.c.symbol,
                models.IndexDaily.trade_date == subq.c.max_date
            ))
            .all()
        )
        latest_map = {r.symbol: r for r in latest_rows}

    for code, name in INDEX_NAME_MAP.items():
        latest_trade_date = None
        latest_close = None
        latest_pct_chg = None
        data_source = 'db'

        # 1. 优先用 akshare 实时数据
        if spot_df is not None and not spot_df.empty:
            ak_name = INDEX_NAME_MAP.get(code)
            row = spot_df[spot_df['名称'] == ak_name]
            if not row.empty:
                latest_close = row['最新价'].values[0]
                latest_pct_chg = row['涨跌幅'].values[0]
                data_source = 'akshare_spot'
                latest_trade_date = 'realtime'

        # 2. 无实时数据时 fallback 数据库
        if latest_close is None:
            row = latest_map.get(code)
            if row:
                latest_trade_date = row.trade_date.isoformat()
                latest_close = row.close
                latest_pct_chg = row.pct_chg

        result.append({
            "symbol": code,
            "name": name,
            "latest_trade_date": latest_trade_date,
            "latest_close": round(float(latest_close), 2) if latest_close is not None else None,
            "latest_pct_chg": round(float(latest_pct_chg), 2) if latest_pct_chg is not None else None,
            "data_source": data_source,
        })

    return success(result)
