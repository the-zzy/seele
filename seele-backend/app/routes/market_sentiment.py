"""
市场情绪路由

提供每日市场情绪统计和板块情绪统计查询。
数据优先从实体表读取，缺失时回退到实时计算。
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, text
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


def _compute_industry_sentiment(db: Session, trade_date: date, threshold: float = 2.0) -> List[dict]:
    """计算单日板块情绪统计"""
    rows = (
        db.query(
            models.StockBasic.industry,
            func.count(models.StockDaily.id).label("stock_count"),
            func.sum(func.if_(models.StockDaily.pct_chg > 0, 1, 0)).label("up"),
            func.sum(func.if_(models.StockDaily.pct_chg < 0, 1, 0)).label("down"),
            func.sum(func.if_(models.StockDaily.pct_chg == 0, 1, 0)).label("flat"),
            func.avg(models.StockDaily.pct_chg).label("avg_pct_chg"),
            func.max(models.StockDaily.pct_chg).label("max_pct_chg"),
            func.min(models.StockDaily.pct_chg).label("min_pct_chg"),
            func.sum(func.if_(models.StockDaily.pct_chg >= threshold, 1, 0)).label("strong"),
            func.sum(models.StockDaily.amount).label("amount_sum"),
        )
        .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
        .filter(
            models.StockDaily.trade_date == trade_date,
            models.StockBasic.industry.isnot(None),
        )
        .group_by(models.StockBasic.industry)
        .order_by(func.avg(models.StockDaily.pct_chg).desc())
        .all()
    )

    result = []
    for row in rows:
        result.append({
            "trade_date": str(trade_date),
            "industry": row.industry,
            "stock_count": row.stock_count,
            "up_count": row.up or 0,
            "down_count": row.down or 0,
            "flat_count": row.flat or 0,
            "avg_pct_chg": round(row.avg_pct_chg, 4) if row.avg_pct_chg else 0.0,
            "max_pct_chg": round(row.max_pct_chg, 4) if row.max_pct_chg else 0.0,
            "min_pct_chg": round(row.min_pct_chg, 4) if row.min_pct_chg else 0.0,
            "strong_count": row.strong or 0,
            "amount_sum": round(row.amount_sum, 2) if row.amount_sum else 0.0,
        })
    return result


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


def _persist_industry_sentiment(db: Session, trade_date: date, threshold: float = 2.0):
    """计算并持久化单日板块情绪"""
    db.query(models.IndustrySentimentDaily).filter(
        models.IndustrySentimentDaily.trade_date == trade_date
    ).delete(synchronize_session=False)

    data_list = _compute_industry_sentiment(db, trade_date, threshold)
    for data in data_list:
        db.add(models.IndustrySentimentDaily(
            trade_date=trade_date,
            industry=data["industry"],
            stock_count=data["stock_count"],
            up_count=data["up_count"],
            down_count=data["down_count"],
            flat_count=data["flat_count"],
            avg_pct_chg=data["avg_pct_chg"],
            max_pct_chg=data["max_pct_chg"],
            min_pct_chg=data["min_pct_chg"],
            strong_count=data["strong_count"],
            amount_sum=data["amount_sum"],
        ))
    db.commit()


@router.get("/daily")
def get_daily_sentiment(
    start_date: str = Query(..., description="开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式 YYYY-MM-DD"),
    threshold: float = Query(2.0, description="强势阈值，默认 2.0"),
    db: Session = Depends(get_db),
):
    """查询日期范围内的每日市场情绪统计"""
    start = start_date.replace("-", "")
    end = end_date.replace("-", "")

    range_dates = [
        d[0]
        for d in db.query(models.StockDaily.trade_date)
        .filter(
            models.StockDaily.trade_date >= start,
            models.StockDaily.trade_date <= end,
        )
        .distinct()
        .order_by(models.StockDaily.trade_date.asc())
        .all()
    ]

    if not range_dates:
        return success({"start_date": start_date, "end_date": end_date, "list": []})

    result = []
    for td in range_dates:
        row = (
            db.query(models.MarketSentimentDaily)
            .filter(models.MarketSentimentDaily.trade_date == td)
            .first()
        )
        if row:
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
        else:
            data = _compute_market_sentiment(db, td, threshold)
            _persist_market_sentiment(db, td, threshold)
            result.append(data)

    return success({
        "start_date": start_date,
        "end_date": end_date,
        "threshold": threshold,
        "list": result,
    })


@router.get("/industry")
def get_industry_sentiment(
    trade_date: str = Query(..., description="交易日期，格式 YYYY-MM-DD"),
    threshold: float = Query(2.0, description="强势阈值，默认 2.0"),
    db: Session = Depends(get_db),
):
    """查询某日的板块情绪统计"""
    formatted = trade_date.replace("-", "")

    rows = (
        db.query(models.IndustrySentimentDaily)
        .filter(models.IndustrySentimentDaily.trade_date == formatted)
        .order_by(models.IndustrySentimentDaily.avg_pct_chg.desc())
        .all()
    )

    if rows:
        result = []
        for row in rows:
            result.append({
                "trade_date": str(row.trade_date),
                "industry": row.industry,
                "stock_count": row.stock_count,
                "up_count": row.up_count,
                "down_count": row.down_count,
                "flat_count": row.flat_count,
                "avg_pct_chg": float(row.avg_pct_chg) if row.avg_pct_chg else 0.0,
                "max_pct_chg": float(row.max_pct_chg) if row.max_pct_chg else 0.0,
                "min_pct_chg": float(row.min_pct_chg) if row.min_pct_chg else 0.0,
                "strong_count": row.strong_count,
                "amount_sum": float(row.amount_sum) if row.amount_sum else 0.0,
            })
        return success({"trade_date": trade_date, "list": result})

    data = _compute_industry_sentiment(db, formatted, threshold)
    _persist_industry_sentiment(db, formatted, threshold)
    return success({"trade_date": trade_date, "list": data})


@router.post("/compute/{trade_date}")
def compute_sentiment(
    trade_date: str,
    threshold: float = Query(2.0, description="强势阈值，默认 2.0"),
    db: Session = Depends(get_db),
):
    """手动触发某日的市场情绪统计计算并持久化"""
    formatted = trade_date.replace("-", "")
    _persist_market_sentiment(db, formatted, threshold)
    _persist_industry_sentiment(db, formatted, threshold)
    return success({"trade_date": trade_date, "message": "市场情绪统计已更新"})
