"""
股票日线指标路由

提供指标计算、查询等功能。
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

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


def _build_indicator_for_symbol(
    db: Session,
    symbol: str,
    trade_date: date,
    lookback: int = 60,
) -> Optional[dict]:
    """为单只股票计算指定日期的指标"""
    # 获取该日期及之前 lookback 天的数据（按日期降序）
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
        return None

    closes = [r.close for r in rows if r.close is not None]
    volumes = [r.volume for r in rows if r.volume is not None]
    amounts = [r.amount for r in rows if r.amount is not None]
    turnovers = [r.turnover for r in rows if r.turnover is not None]

    if not closes:
        return None

    return {
        "ma5": _compute_ma(closes, 5),
        "ma10": _compute_ma(closes, 10),
        "ma20": _compute_ma(closes, 20),
        "ma30": _compute_ma(closes, 30),
        "ma60": _compute_ma(closes, 60),
        "vol_ma5": int(_compute_avg(volumes, 5)) if len(volumes) >= 5 else None,
        "vol_ma10": int(_compute_avg(volumes, 10)) if len(volumes) >= 10 else None,
        "amount_ma5": int(_compute_avg(amounts, 5)) if len(amounts) >= 5 else None,
        "amount_ma10": int(_compute_avg(amounts, 10)) if len(amounts) >= 10 else None,
        "turnover_ma5": _compute_avg(turnovers, 5) if len(turnovers) >= 5 else None,
        "turnover_ma10": _compute_avg(turnovers, 10) if len(turnovers) >= 10 else None,
    }


# 3.0 计算指定日期的指标数据
@router.post("/compute")
def compute_indicators(
    trade_date: str = Query(..., description="交易日期，格式 YYYY-MM-DD 或 YYYYMMDD"),
    db: Session = Depends(get_db),
):
    """计算指定交易日所有主板的日线指标并入库"""
    formatted_date = trade_date.replace("-", "")

    # 验证交易日期是否存在
    exists = (
        db.query(models.StockDaily)
        .filter(models.StockDaily.trade_date == formatted_date)
        .first()
    )
    if not exists:
        raise HTTPException(status_code=404, detail=f"交易日期 {trade_date} 无数据")

    # 获取该日期所有主板股票代码
    q = (
        db.query(models.StockDaily.symbol)
        .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
        .filter(models.StockDaily.trade_date == formatted_date)
    )
    symbols = [row[0] for row in apply_main_board_filter(q).distinct().all()]

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

    for symbol in symbols:
        indicator_data = _build_indicator_for_symbol(db, symbol, formatted_date)
        if indicator_data is None:
            failed_count += 1
            continue
        indicator_data["symbol"] = symbol
        indicator_data["trade_date"] = formatted_date
        items.append(indicator_data)
        success_count += 1

    # 批量写入（逐条 upsert，避免一次性事务过大）
    if items:
        result = crud.stock_daily_indicator_crud.create_or_update_batch(db, items)
        success_count = result["success"]
        failed_count = result["failed"]

    return success({
        "trade_date": trade_date,
        "total": total,
        "success": success_count,
        "failed": failed_count,
    })


# 3.1 根据股票代码查询指标
@router.get("/symbol/{symbol}")
def get_indicator_by_symbol(
    symbol: str,
    db: Session = Depends(get_db),
):
    """根据股票代码查询全部日线指标"""
    objs = crud.stock_daily_indicator_crud.get_by_symbol(db, symbol)
    return list_success([
        schemas.StockDailyIndicatorResponse.model_validate(item)
        for item in objs
    ])


# 3.2 根据交易日期查询指标
@router.get("/date/{trade_date}")
def get_indicator_by_date(
    trade_date: str,
    db: Session = Depends(get_db),
):
    """根据交易日期查询全部日线指标"""
    formatted_date = trade_date.replace("-", "")
    objs = crud.stock_daily_indicator_crud.get_by_date(db, formatted_date)
    return list_success([
        schemas.StockDailyIndicatorResponse.model_validate(item)
        for item in objs
    ])
