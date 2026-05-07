"""
Seele 股票数据管理后端 - 主应用入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.config import get_settings
from app.database import engine, Base
from app.response import success
from app.routes import financial, pickers, portfolio, stock_basic, stock_daily, stock_indicator, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)
    yield
    # 关闭时清理资源


# 创建应用
app = FastAPI(
    title="Seele 股票数据管理API",
    description="基于FastAPI的股票数据管理后端服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stock_basic.router, prefix="/api")
app.include_router(stock_daily.router, prefix="/api")
app.include_router(stock_indicator.router, prefix="/api")
app.include_router(pickers.router, prefix="/api")
app.include_router(financial.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(sync.router, prefix="/api")


@app.get("/")
def root():
    """根路径"""
    return success("Seele 股票数据管理API")


@app.get("/health")
def health():
    """健康检查"""
    return success("OK")


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
