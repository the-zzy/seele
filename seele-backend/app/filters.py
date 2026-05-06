"""
通用查询过滤工具

封装"沪深主板 + 非ST"等高频过滤条件，避免在路由层重复书写。
所有应用 `apply_main_board_filter` 的查询都会被收敛到主板非ST，
便于将来策略调整时只需修改一个地方。
"""

from typing import Any

from app import models


def apply_main_board_filter(query: Any) -> Any:
    """限定 query 仅匹配沪深主板且名称不含 ST 的股票（基于 StockBasic）"""
    return query.filter(
        models.StockBasic.market == "主板",
        models.StockBasic.name.notlike("%ST%"),
    )


def is_main_board_non_st(stock: models.StockBasic) -> bool:
    """判断单个 StockBasic 对象是否属于沪深主板且非 ST"""
    if not stock or stock.market != "主板":
        return False
    if stock.name and "ST" in stock.name:
        return False
    return True


def filter_main_board_non_st(stocks):
    """从 StockBasic 列表中筛选沪深主板非 ST 的对象"""
    return [s for s in stocks if is_main_board_non_st(s)]


def build_exclude_sql(query: Any) -> str:
    """根据查询对象构建 SQL 排除条件片段（用于 raw SQL CTE）。

    支持字段：exclude_st、exclude_cyb、exclude_kcb、exclude_bse。
    返回的字符串中各行已自带前缀 `    AND ...`。
    """
    conditions = []
    if getattr(query, "exclude_st", False):
        conditions.append("    AND sb.name NOT LIKE '%ST%'")
    if getattr(query, "exclude_cyb", False):
        conditions.append("    AND sb.symbol NOT LIKE '300%'")
        conditions.append("    AND sb.symbol NOT LIKE '301%'")
    if getattr(query, "exclude_kcb", False):
        conditions.append("    AND sb.symbol NOT LIKE '688%'")
        conditions.append("    AND sb.symbol NOT LIKE '689%'")
    if getattr(query, "exclude_bse", False):
        conditions.append("    AND sb.symbol NOT LIKE '4%'")
        conditions.append("    AND sb.symbol NOT LIKE '8%'")
    return "\n".join(conditions)


def get_baostock_code(symbol: str) -> str:
    """将 6 位股票代码转换为 Baostock 格式（如 600000 → sh.600000）"""
    if symbol.startswith("6"):
        prefix = "sh"
    elif symbol.startswith(("0", "2", "3")):
        prefix = "sz"
    else:
        prefix = "bj"
    return f"{prefix}.{symbol}"
