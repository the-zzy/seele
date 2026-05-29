"""
股票基础数据路由
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.filters import filter_main_board_non_st, is_main_board_non_st
from app.response import list_success, page_success, success
from app.schemas import StockBasicResponse, StockBasicWithFinancialResponse

router = APIRouter(prefix="/stock/basic", tags=["股票基础数据"])


# 1.1 分页查询股票列表 (POST)
@router.post("/page")
def post_stock_basic_page(
    query: schemas.StockBasicQuery,
    db: Session = Depends(get_db),
):
    """分页查询股票列表 (POST) - 仅查询沪深主板且非ST股票"""
    query.market = "主板"
    query.exclude_st = True
    list_data, total = crud.stock_basic_crud.get_list(db, query)
    return page_success(
        items=[StockBasicWithFinancialResponse.model_validate(item) for item in list_data],
        total=total,
        page_num=query.page_num,
        page_size=query.page_size,
    )


