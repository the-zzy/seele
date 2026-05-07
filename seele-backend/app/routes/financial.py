"""
财务指标路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.filters import build_exclude_sql
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


@router.post("/picker")
def post_financial_picker(
    query: schemas.FinancialPickerQuery,
    db: Session = Depends(get_db),
):
    """财务选股 - 基于盈利能力与成长性指标筛选"""
    page_size = min(query.page_size, 100)
    exclude_sql = build_exclude_sql(query)

    count_sql = f"""
    SELECT COUNT(*)
    FROM stock_financial_indicator fi
    JOIN stock_basic sb ON fi.symbol = sb.symbol
    WHERE fi.roe >= :roe_min
        AND fi.gross_profit_ratio >= :gross_profit_ratio_min
        AND fi.net_profit_yoy >= :net_profit_yoy_min
        AND fi.revenue_yoy >= :revenue_yoy_min
        AND fi.debt_ratio <= :debt_ratio_max
        {exclude_sql}
        {("AND fi.net_profit_ratio >= :net_profit_ratio_min" if query.net_profit_ratio_min is not None else "")}
    """

    list_sql = f"""
    SELECT
        fi.symbol,
        fi.name,
        sb.industry,
        sb.market,
        fi.report_date,
        fi.net_profit,
        fi.net_profit_yoy,
        fi.total_revenue,
        fi.revenue_yoy,
        fi.gross_profit_ratio,
        fi.net_profit_ratio,
        fi.roe,
        fi.roe_diluted,
        fi.eps,
        fi.bps,
        fi.debt_ratio,
        fi.operate_cash_flow
    FROM stock_financial_indicator fi
    JOIN stock_basic sb ON fi.symbol = sb.symbol
    WHERE fi.roe >= :roe_min
        AND fi.gross_profit_ratio >= :gross_profit_ratio_min
        AND fi.net_profit_yoy >= :net_profit_yoy_min
        AND fi.revenue_yoy >= :revenue_yoy_min
        AND fi.debt_ratio <= :debt_ratio_max
        {exclude_sql}
        {("AND fi.net_profit_ratio >= :net_profit_ratio_min" if query.net_profit_ratio_min is not None else "")}
    ORDER BY {query.sort_field} {query.sort_order.upper()}
    LIMIT :limit OFFSET :offset
    """

    params = {
        "roe_min": query.roe_min,
        "gross_profit_ratio_min": query.gross_profit_ratio_min,
        "net_profit_yoy_min": query.net_profit_yoy_min,
        "revenue_yoy_min": query.revenue_yoy_min,
        "debt_ratio_max": query.debt_ratio_max,
        "limit": page_size,
        "offset": (query.page_num - 1) * page_size,
    }
    if query.net_profit_ratio_min is not None:
        params["net_profit_ratio_min"] = query.net_profit_ratio_min

    total_result = db.execute(text(count_sql), params).scalar() or 0
    rows = db.execute(text(list_sql), params).all()

    result_list = []
    for row in rows:
        result_list.append({
            "symbol": row.symbol,
            "name": row.name,
            "industry": row.industry,
            "market": row.market,
            "report_date": row.report_date.strftime("%Y-%m-%d") if row.report_date else None,
            "net_profit": row.net_profit,
            "net_profit_yoy": row.net_profit_yoy,
            "total_revenue": row.total_revenue,
            "revenue_yoy": row.revenue_yoy,
            "gross_profit_ratio": row.gross_profit_ratio,
            "net_profit_ratio": row.net_profit_ratio,
            "roe": row.roe,
            "roe_diluted": row.roe_diluted,
            "eps": row.eps,
            "bps": row.bps,
            "debt_ratio": row.debt_ratio,
            "operate_cash_flow": row.operate_cash_flow,
        })

    return success({
        "total": total_result,
        "page_num": query.page_num,
        "page_size": page_size,
        "list": result_list,
    })
