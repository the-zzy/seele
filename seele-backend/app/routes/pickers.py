"""
选股策略路由 — 仅保留主升浪选股（关联日线及指标表）
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.response import page_success

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
