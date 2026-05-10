"""
财务指标路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.response import success

router = APIRouter(prefix="/financial", tags=["财务指标"])


# 字段映射：查询参数 -> 模型字段
_FINANCIAL_FIELD_MAP = {
    "roe": models.StockFinancialIndicator.roe,
    "gross_profit_ratio": models.StockFinancialIndicator.gross_profit_ratio,
    "net_profit_ratio": models.StockFinancialIndicator.net_profit_ratio,
    "net_profit_yoy": models.StockFinancialIndicator.net_profit_yoy,
    "revenue_yoy": models.StockFinancialIndicator.revenue_yoy,
    "debt_ratio": models.StockFinancialIndicator.debt_ratio,
    "eps": models.StockFinancialIndicator.eps,
    "bps": models.StockFinancialIndicator.bps,
    "symbol": models.StockFinancialIndicator.symbol,
    "name": models.StockFinancialIndicator.name,
}


@router.get("")
def get_financial_list(
    query: schemas.StockFinancialIndicatorQuery = Depends(),
    db: Session = Depends(get_db),
):
    """财务指标列表查询，支持按指标范围过滤和排序"""
    list_data, total = crud.stock_financial_indicator_crud.get_list(db, query)

    result_list = []
    for item in list_data:
        result_list.append({
            "symbol": item.symbol,
            "name": item.name,
            "industry": getattr(item, "industry", None),
            "market": getattr(item, "market", None),
            "report_date": item.report_date.strftime("%Y-%m-%d") if item.report_date else None,
            "net_profit": item.net_profit,
            "net_profit_yoy": item.net_profit_yoy,
            "deduct_net_profit": item.deduct_net_profit,
            "total_revenue": item.total_revenue,
            "revenue_yoy": item.revenue_yoy,
            "gross_profit_ratio": item.gross_profit_ratio,
            "net_profit_ratio": item.net_profit_ratio,
            "roe": item.roe,
            "roe_diluted": item.roe_diluted,
            "eps": item.eps,
            "bps": item.bps,
            "ops_cash_flow_per_share": item.ops_cash_flow_per_share,
            "current_ratio": item.current_ratio,
            "quick_ratio": item.quick_ratio,
            "debt_ratio": item.debt_ratio,
        })

    return success({
        "total": total,
        "page_num": query.page_num,
        "page_size": query.page_size,
        "list": result_list,
    })


@router.get("/{symbol}")
def get_financial_by_symbol(
    symbol: str,
    db: Session = Depends(get_db),
):
    """单只股票财务指标详情"""
    item = crud.stock_financial_indicator_crud.get_by_symbol(db, symbol)
    if not item:
        raise HTTPException(status_code=404, detail="未找到该股票的财务指标数据")

    return success({
        "symbol": item.symbol,
        "name": item.name,
        "report_date": item.report_date.strftime("%Y-%m-%d") if item.report_date else None,
        "net_profit": item.net_profit,
        "net_profit_yoy": item.net_profit_yoy,
        "deduct_net_profit": item.deduct_net_profit,
        "total_revenue": item.total_revenue,
        "revenue_yoy": item.revenue_yoy,
        "gross_profit_ratio": item.gross_profit_ratio,
        "net_profit_ratio": item.net_profit_ratio,
        "roe": item.roe,
        "roe_diluted": item.roe_diluted,
        "eps": item.eps,
        "bps": item.bps,
        "ops_cash_flow_per_share": item.ops_cash_flow_per_share,
        "current_ratio": item.current_ratio,
        "quick_ratio": item.quick_ratio,
        "debt_ratio": item.debt_ratio,
        "total_assets": item.total_assets,
        "total_equity": item.total_equity,
        "operate_cash_flow": item.operate_cash_flow,
    })


