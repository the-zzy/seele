"""
访客日志路由
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.crud import visitor_log_crud
from app.database import get_db
from app.response import success

router = APIRouter(prefix='/visitor', tags=['访客日志'])
logger = logging.getLogger(__name__)


class TrackRequest(BaseModel):
    """访客信息上报请求"""
    path: Optional[str] = Field(None, description='访问路径')
    screen_resolution: Optional[str] = Field(None, description='屏幕分辨率')
    language: Optional[str] = Field(None, description='浏览器语言')
    timezone: Optional[str] = Field(None, description='时区')
    platform: Optional[str] = Field(None, description='操作系统平台')
    referrer: Optional[str] = Field(None, description='来源页面')


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP"""
    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()
    real_ip = request.headers.get('x-real-ip')
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return 'unknown'


def _persist_log(db: Session, data: dict):
    """持久化日志，异常静默处理避免影响主请求"""
    try:
        visitor_log_crud.create(db, data)
        db.commit()
    except Exception as exc:
        logger.warning('[VISITOR_LOG] 写入访客日志失败: %s', exc)
        db.rollback()


@router.post('/track')
def track_visitor(request: Request, body: TrackRequest, db: Session = Depends(get_db)):
    """前端上报访客信息"""
    data = {
        'ip_address': _get_client_ip(request),
        'user_agent': request.headers.get('user-agent'),
        'path': body.path or request.headers.get('referer', '/'),
        'method': 'TRACK',
        'referrer': body.referrer,
        'screen_resolution': body.screen_resolution,
        'language': body.language,
        'timezone': body.timezone,
        'platform': body.platform,
    }
    _persist_log(db, data)
    return success({'tracked': True})


@router.get('/logs')
def get_visitor_logs(
    page_num: int = 1,
    page_size: int = 20,
    ip_address: Optional[str] = None,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """查询访客日志（需认证）"""
    query = schemas.VisitorLogQuery(
        page_num=page_num,
        page_size=page_size,
        ip_address=ip_address,
        days=days,
    )
    list_data, total = visitor_log_crud.get_list(db, query)
    return success({
        'list': [schemas.VisitorLogResponse.model_validate(r).model_dump() for r in list_data],
        'total': total,
        'page_num': page_num,
        'page_size': page_size,
    })
