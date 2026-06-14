"""
认证路由
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.auth import create_access_token, get_current_user
from app.config import APP_VERSION, get_settings
from app.response import success

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
def login(payload: dict, x_client_version: str | None = Header(None, alias='X-Client-Version')):
    """管理员登录"""
    if x_client_version != APP_VERSION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={'code': 'VERSION_MISMATCH', 'server_version': APP_VERSION},
        )

    settings = get_settings()
    if not settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='管理员密码未配置，请在环境变量中设置 ADMIN_PASSWORD',
        )

    password = payload.get('password', '')
    if password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='密码错误',
        )

    token = create_access_token(data={'sub': 'admin'})
    return success({'token': token})


@router.get("/me")
def me(current_user: str = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return success({'username': current_user})
