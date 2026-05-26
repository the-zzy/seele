"""
交易日历路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.response import success

router = APIRouter(prefix='/trade-calendar', tags=['交易日历'])


@router.get('/latest')
def get_latest_trade_date(db: Session = Depends(get_db)):
    """获取最近一个交易日"""
    latest = crud.trade_calendar_crud.get_latest(db)
    if not latest:
        return success(None)
    return success(str(latest))


