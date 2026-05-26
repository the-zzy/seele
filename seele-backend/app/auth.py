"""
认证模块
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token"""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm='HS256')


def decode_token(token: str) -> Optional[dict]:
    """解码并验证 JWT token"""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=['HS256'])
    except jwt.PyJWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """FastAPI 依赖：验证 Bearer token，返回用户名"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='缺少认证凭据',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='无效的认证凭据',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    username: str = payload.get('sub')
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='无效的认证凭据',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return username
