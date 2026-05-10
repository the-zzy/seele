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


# 1.1 分页查询股票列表 (GET)
@router.get("/list")
def get_stock_basic_list(
    page_num: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页条数"),
    sort_field: str = Query(None, description="排序字段"),
    sort_order: str = Query("asc", description="排序方向"),
    symbol: str = Query(None, description="股票代码"),
    name: str = Query(None, description="股票名称"),
    industry: str = Query(None, description="行业"),
    area: str = Query(None, description="地区"),
    exclude_cyb: bool = Query(False, description="是否过滤创业板"),
    exclude_kcb: bool = Query(False, description="是否过滤科创板"),
    exclude_bse: bool = Query(False, description="是否过滤北交所"),
    db: Session = Depends(get_db),
):
    """分页查询股票列表 (GET) - 仅查询沪深主板且非ST股票"""
    query = schemas.StockBasicQuery(
        page_num=page_num,
        page_size=page_size,
        sort_field=sort_field,
        sort_order=sort_order,
        symbol=symbol,
        name=name,
        industry=industry,
        market="主板",
        area=area,
        exclude_st=True,
        exclude_cyb=exclude_cyb,
        exclude_kcb=exclude_kcb,
        exclude_bse=exclude_bse,
    )
    list_data, total = crud.stock_basic_crud.get_list(db, query)
    return page_success(
        items=[StockBasicWithFinancialResponse.model_validate(item) for item in list_data],
        total=total,
        page_num=page_num,
        page_size=page_size,
    )


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


# 1.3 根据股票代码查询
@router.get("/symbol/{symbol}")
def get_stock_basic_by_symbol(
    symbol: str,
    db: Session = Depends(get_db),
):
    """根据股票代码查询 - 仅查询沪深主板且非ST股票"""
    obj = crud.stock_basic_crud.get_by_symbol(db, symbol)
    if not is_main_board_non_st(obj):
        raise HTTPException(status_code=404, detail="股票不存在或非主板/ST股票")
    return success(StockBasicResponse.model_validate(obj))


# 1.4 批量查询股票
@router.post("/batch")
def post_stock_basic_batch(
    symbols: List[str],
    db: Session = Depends(get_db),
):
    """批量查询股票 - 仅查询沪深主板且非ST股票"""
    objs = filter_main_board_non_st(crud.stock_basic_crud.get_batch(db, symbols))
    return list_success([StockBasicResponse.model_validate(item) for item in objs])


# 1.5 根据行业查询
@router.get("/industry/{industry}")
def get_stock_basic_by_industry(
    industry: str,
    db: Session = Depends(get_db),
):
    """根据行业查询 - 仅查询沪深主板且非ST股票"""
    objs = filter_main_board_non_st(crud.stock_basic_crud.get_by_industry(db, industry))
    return list_success([StockBasicResponse.model_validate(item) for item in objs])


# 1.6 新增股票
@router.post("")
def post_stock_basic(
    obj_in: schemas.StockBasicCreate,
    db: Session = Depends(get_db),
):
    """新增股票"""
    obj = crud.stock_basic_crud.create(db, obj_in)
    return success(StockBasicResponse.model_validate(obj))


# 1.7 更新股票
@router.put("")
def put_stock_basic(
    obj_in: schemas.StockBasicUpdate,
    db: Session = Depends(get_db),
):
    """更新股票"""
    obj = crud.stock_basic_crud.update(db, obj_in)
    if not obj:
        raise HTTPException(status_code=404, detail="股票不存在")
    return success(StockBasicResponse.model_validate(obj))


# 1.2 根据ID查询 (放在后面避免路由冲突)
@router.get("/{id}")
def get_stock_basic_by_id(
    id: int,
    db: Session = Depends(get_db),
):
    """根据ID查询 - 仅查询沪深主板且非ST股票"""
    obj = crud.stock_basic_crud.get_by_id(db, id)
    if not is_main_board_non_st(obj):
        raise HTTPException(status_code=404, detail="股票不存在或非主板/ST股票")
    return success(StockBasicResponse.model_validate(obj))


# 1.8 删除股票
@router.delete("/{id}")
def delete_stock_basic(
    id: int,
    db: Session = Depends(get_db),
):
    """删除股票"""
    deleted = crud.stock_basic_crud.delete(db, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="股票不存在")
    return success(None)
