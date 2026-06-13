"""
市场情绪路由

提供每日市场情绪统计和板块情绪统计查询。
数据优先从实体表读取，缺失时回退到实时计算。
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.filters import apply_main_board_filter
from app.response import list_success, success

router = APIRouter(prefix="/market/sentiment", tags=["市场情绪"])


def _compute_market_sentiment(db: Session, trade_date: date, threshold: float = 2.0) -> dict:
    """计算单日市场情绪统计"""
    q = (
        db.query(
            func.count(models.StockDaily.id).label("total"),
            func.sum(func.if_(models.StockDaily.pct_chg > 0, 1, 0)).label("up"),
            func.sum(func.if_(models.StockDaily.pct_chg < 0, 1, 0)).label("down"),
            func.sum(func.if_(models.StockDaily.pct_chg == 0, 1, 0)).label("flat"),
            func.avg(models.StockDaily.pct_chg).label("avg_pct_chg"),
            func.sum(func.if_(models.StockDaily.pct_chg >= threshold, 1, 0)).label("strong"),
        )
        .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
        .filter(models.StockDaily.trade_date == trade_date)
    )
    q = apply_main_board_filter(q)
    row = q.first()
    total = row.total or 0
    strong = row.strong or 0
    return {
        "trade_date": str(trade_date),
        "total_stocks": total,
        "up_count": row.up or 0,
        "down_count": row.down or 0,
        "flat_count": row.flat or 0,
        "avg_pct_chg": round(row.avg_pct_chg, 4) if row.avg_pct_chg else 0.0,
        "strong_count": strong,
        "strong_threshold": threshold,
        "strong_percent": round(strong / total * 100, 2) if total else 0.0,
    }


def _persist_market_sentiment(db: Session, trade_date: date, threshold: float = 2.0):
    """计算并持久化单日市场情绪"""
    data = _compute_market_sentiment(db, trade_date, threshold)
    existing = (
        db.query(models.MarketSentimentDaily)
        .filter(models.MarketSentimentDaily.trade_date == trade_date)
        .first()
    )
    if existing:
        existing.total_stocks = data["total_stocks"]
        existing.up_count = data["up_count"]
        existing.down_count = data["down_count"]
        existing.flat_count = data["flat_count"]
        existing.avg_pct_chg = data["avg_pct_chg"]
        existing.strong_count = data["strong_count"]
        existing.strong_threshold = data["strong_threshold"]
        existing.strong_percent = data["strong_percent"]
    else:
        db.add(models.MarketSentimentDaily(
            trade_date=trade_date,
            total_stocks=data["total_stocks"],
            up_count=data["up_count"],
            down_count=data["down_count"],
            flat_count=data["flat_count"],
            avg_pct_chg=data["avg_pct_chg"],
            strong_count=data["strong_count"],
            strong_threshold=data["strong_threshold"],
            strong_percent=data["strong_percent"],
        ))
    db.commit()


@router.post("/compute")
def post_compute_sentiment(
    trade_date: str = Query(..., description="交易日期，格式 YYYY-MM-DD"),
    threshold: float = Query(2.0, description="强势阈值，默认 2.0"),
    db: Session = Depends(get_db),
):
    """计算并保存指定日期的市场情绪数据（用于手动补算）"""
    from datetime import date as _date
    date_obj = _date.fromisoformat(trade_date)
    _persist_market_sentiment(db, date_obj, threshold)
    return success({
        "trade_date": trade_date,
        "status": "computed",
        "threshold": threshold,
    })


@router.get("/daily")
def get_daily_sentiment(
    start_date: str = Query(..., description="开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式 YYYY-MM-DD"),
    threshold: float = Query(2.0, description="强势阈值，默认 2.0"),
    db: Session = Depends(get_db),
):
    """查询日期范围内的每日市场情绪统计"""
    from datetime import date as _date

    start_obj = _date.fromisoformat(start_date)
    end_obj = _date.fromisoformat(end_date)

    range_dates = [
        d[0]
        for d in db.query(models.TradeCalendar.trade_date)
        .filter(
            models.TradeCalendar.trade_date >= start_obj,
            models.TradeCalendar.trade_date <= end_obj,
            models.TradeCalendar.is_trading_day == 1,
        )
        .order_by(models.TradeCalendar.trade_date.asc())
        .all()
    ]

    if not range_dates:
        return success({"start_date": start_date, "end_date": end_date, "list": []})

    existing_rows = (
        db.query(models.MarketSentimentDaily)
        .filter(models.MarketSentimentDaily.trade_date.in_(range_dates))
        .all()
    )
    existing_map = {r.trade_date: r for r in existing_rows}

    result = []
    for td in range_dates:
        row = existing_map.get(td)
        if row and float(row.strong_threshold) == threshold:
            result.append({
                "trade_date": str(row.trade_date),
                "total_stocks": row.total_stocks,
                "up_count": row.up_count,
                "down_count": row.down_count,
                "flat_count": row.flat_count,
                "avg_pct_chg": float(row.avg_pct_chg) if row.avg_pct_chg else 0.0,
                "strong_count": row.strong_count,
                "strong_threshold": float(row.strong_threshold),
                "strong_percent": float(row.strong_percent) if row.strong_percent else 0.0,
            })
        elif row:
            # 阈值不匹配时实时重新计算，不持久化（避免覆盖默认缓存）
            result.append(_compute_market_sentiment(db, td, threshold))
        else:
            # 缺失数据时返回空值，不再实时计算（应在同步任务链中预计算）
            result.append({
                "trade_date": str(td),
                "total_stocks": 0,
                "up_count": 0,
                "down_count": 0,
                "flat_count": 0,
                "avg_pct_chg": 0.0,
                "strong_count": 0,
                "strong_threshold": threshold,
                "strong_percent": 0.0,
            })

    return success({
        "start_date": start_date,
        "end_date": end_date,
        "threshold": threshold,
        "list": result,
    })


