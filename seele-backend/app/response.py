"""
统一响应格式工具

后端所有路由统一返回 `{ code, message, data }` 结构，
通过 success / page_success 函数生成，避免在各路由手写 dict。
"""

from typing import Any, Iterable, Optional


def success(data: Any = None, message: str = "success") -> dict:
    """生成成功响应"""
    return {"code": 200, "message": message, "data": data}


def page_success(
    items: Iterable[Any],
    total: int,
    page_num: int,
    page_size: int,
    **extra: Any,
) -> dict:
    """生成分页响应

    extra 会被合并进 data，便于附加 trade_date、threshold 等附属字段。
    """
    payload = {
        "list": list(items),
        "total": total,
        "page_num": page_num,
        "page_size": page_size,
        **extra,
    }
    return success(payload)


def list_success(items: Iterable[Any], message: str = "success") -> dict:
    """生成纯列表响应（无分页字段）"""
    return success(list(items), message=message)
