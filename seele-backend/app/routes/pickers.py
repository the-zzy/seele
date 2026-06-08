"""
选股策略路由 — 仅保留主升浪选股（关联日线及指标表）
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.response import list_success, page_success, success
from app.services.mainwave_detector import detect_mainwave_phases, batch_detect_mainwaves

router = APIRouter(prefix="/stock/daily", tags=["股票选股策略"])


# 2.16 主升浪选股
@router.post("/mainwave-picker")
def post_mainwave_picker(
    query: schemas.MainwavePickerQuery,
    db: Session = Depends(get_db),
):
    """主升浪选股 - 关联日线及指标表，支持市值/股价/换手率/成交额筛选"""
    query.market = "主板"
    query.exclude_st = True
    query.exclude_cyb = True
    query.exclude_kcb = True
    list_data, total, actual_trade_date = crud.stock_basic_crud.get_mainwave_list(db, query)
    return page_success(
        items=list_data,
        total=total,
        page_num=query.page_num,
        page_size=query.page_size,
        trade_date=actual_trade_date,
    )


# 2.17 主升浪阶段检测（单只股票）
@router.get("/mainwave-detect/{symbol}")
def get_mainwave_detect(
    symbol: str,
    min_gain_pct: float = Query(180.0, description="最小涨幅阈值(%)"),
    window_days: int = Query(30, description="窗口交易日数"),
    start_date: Optional[str] = Query(None, description="查询起始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="查询结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """检测单只股票历史上的主升浪阶段（30 个交易日涨幅 >= 180%）"""
    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    result = detect_mainwave_phases(
        db, symbol, min_gain_pct, window_days, start_dt, end_dt
    )
    return success(result)


# 2.18 主升浪阶段检测（批量）
@router.post("/mainwave-detect/batch")
def post_mainwave_detect_batch(
    query: schemas.MainwaveBatchDetectQuery,
    db: Session = Depends(get_db),
):
    """批量检测多只股票的主升浪阶段，仅返回识别到主升浪的股票"""
    start_dt = None
    end_dt = None
    if query.start_date:
        start_dt = datetime.strptime(query.start_date, '%Y-%m-%d').date()
    if query.end_date:
        end_dt = datetime.strptime(query.end_date, '%Y-%m-%d').date()

    results = batch_detect_mainwaves(
        db, query.symbols, query.min_gain_pct, query.window_days, start_dt, end_dt
    )
    return list_success(results)
