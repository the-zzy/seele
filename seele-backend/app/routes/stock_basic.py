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
from app.services.company_survey import fetch_company_survey
from app.services.industry_detail_sync import fetch_industry_detail

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


@router.get('/{symbol}/survey')
def get_stock_company_survey(symbol: str, db: Session = Depends(get_db)):
    """查询股票公司概况（来源：东方财富 F10）"""
    item = crud.stock_company_profile_crud.get_by_symbol(db, symbol)
    if not item:
        return success(None, message='暂无数据，请先调用同步接口')
    return success(schemas.StockCompanyProfileResponse.model_validate(item))


@router.post('/{symbol}/sync-survey')
def sync_stock_company_survey(symbol: str, db: Session = Depends(get_db)):
    """从东方财富 F10 同步单只股票的公司概况"""
    stock = crud.stock_basic_crud.get_by_symbol(db, symbol)
    if not stock:
        return success({'synced': False, 'reason': f'股票代码 {symbol} 不存在'})

    profile = fetch_company_survey(symbol)
    if not profile:
        return success({'synced': False, 'reason': f'从东方财富抓取 {symbol} 数据失败'})

    db_obj = crud.stock_company_profile_crud.create_or_update(db, profile)
    db.commit()
    db.refresh(db_obj)
    return success({
        'synced': True,
        'symbol': db_obj.symbol,
        'company_full_name': db_obj.company_full_name,
        'updated_at': str(db_obj.updated_at) if db_obj.updated_at else None,
    })


@router.post('/{symbol}/sync-industry-detail')
def sync_stock_industry_detail(symbol: str, db: Session = Depends(get_db)):
    """从东方财富 F10 同步单只股票的细分行业"""
    stock = crud.stock_basic_crud.get_by_symbol(db, symbol)
    if not stock:
        return success({'synced': False, 'reason': f'股票代码 {symbol} 不存在'})

    industry_detail = fetch_industry_detail(symbol)
    if not industry_detail:
        return success({'synced': False, 'reason': f'从东方财富抓取 {symbol} 细分行业失败'})

    crud.stock_basic_crud.update_industry_detail(db, symbol, industry_detail)
    db.commit()
    return success({
        'synced': True,
        'symbol': symbol,
        'industry_detail': industry_detail,
    })

