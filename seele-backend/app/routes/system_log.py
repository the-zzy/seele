"""
系统日志路由
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.response import success

router = APIRouter(prefix="/system/logs", tags=["系统日志"])


@router.get("/errors")
def get_error_logs(
    page_num: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=1000, description="每页条数"),
    level: Optional[str] = Query(None, description="级别过滤"),
    source: Optional[str] = Query(None, description="来源模块过滤"),
    days: Optional[int] = Query(7, description="最近N天"),
    db: Session = Depends(get_db),
):
    """分页查询系统错误日志"""
    query = schemas.SystemErrorLogQuery(
        page_num=page_num,
        page_size=page_size,
        level=level,
        source=source,
        days=days,
    )
    list_data, total = crud.system_error_log_crud.get_list(db, query)
    return success({
        "list": list_data,
        "total": total,
        "page_num": page_num,
        "page_size": page_size,
    })


@router.get("/operations")
def get_operation_logs(
    page_num: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=1000, description="每页条数"),
    operation_type: Optional[str] = Query(None, description="操作类型过滤"),
    days: Optional[int] = Query(7, description="最近N天"),
    db: Session = Depends(get_db),
):
    """分页查询系统操作日志"""
    query = schemas.SystemOperationLogQuery(
        page_num=page_num,
        page_size=page_size,
        operation_type=operation_type,
        days=days,
    )
    list_data, total = crud.system_operation_log_crud.get_list(db, query)
    return success({
        "list": list_data,
        "total": total,
        "page_num": page_num,
        "page_size": page_size,
    })


@router.get("/overview")
def get_log_overview(db: Session = Depends(get_db)):
    """获取系统日志概览：今日统计 + 各任务类型最新同步记录"""
    from sqlalchemy import func

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 今日错误数
    today_error_count = db.query(func.count(models.SystemErrorLog.id)).filter(
        models.SystemErrorLog.created_at >= today_start
    ).scalar() or 0

    # 今日操作数
    today_operation_count = db.query(func.count(models.SystemOperationLog.id)).filter(
        models.SystemOperationLog.created_at >= today_start
    ).scalar() or 0

    # 各任务类型最新同步记录
    job_types = ['stock_basic', 'daily', 'financial', 'indicator', 'board_list', 'board_daily', 'board_constituent', 'index_daily', 'index_constituents']
    latest_sync_logs = []
    for jt in job_types:
        log = db.query(models.SyncJobLog).filter(
            models.SyncJobLog.job_type == jt
        ).order_by(models.SyncJobLog.started_at.desc()).first()
        if log:
            latest_sync_logs.append(log)

    return success({
        "today_error_count": today_error_count,
        "today_operation_count": today_operation_count,
        "latest_sync_logs": latest_sync_logs,
    })
