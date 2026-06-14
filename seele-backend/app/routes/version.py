"""
版本信息路由
"""

from fastapi import APIRouter

from app.config import APP_VERSION

router = APIRouter(prefix='/version', tags=['版本'])


@router.get('')
def get_version():
    """获取后端当前版本号"""
    return {'version': APP_VERSION}
