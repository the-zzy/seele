"""
Seele 股票数据管理后端 - 主应用入口
"""

from contextlib import asynccontextmanager

from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.config import get_settings
from app.database import engine, Base
from app.response import success
from app.routes import financial, market_sentiment, pickers, portfolio, stock_basic, stock_daily, stock_indicator, sync
from app.scheduler import get_scheduler
from app.scheduler_jobs import (
    scheduled_compute_indicators,
    scheduled_sync_daily,
    scheduled_sync_financial,
    scheduled_sync_stock_basic,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)

    # 启动定时任务调度器
    scheduler = get_scheduler()
    scheduler.add_job(
        scheduled_sync_stock_basic,
        trigger=CronTrigger(hour=1, minute=0, day_of_week='mon-fri'),
        id='sync_stock_basic',
        name='股票基础信息同步',
        replace_existing=True,
    )
    scheduler.add_job(
        scheduled_sync_daily,
        trigger=CronTrigger(hour=17, minute=0, day_of_week='mon-fri'),
        id='sync_daily',
        name='股票日线数据同步',
        replace_existing=True,
    )
    scheduler.add_job(
        scheduled_sync_financial,
        trigger=CronTrigger(hour=2, minute=0, day_of_week='mon'),
        id='sync_financial',
        name='财务指标同步',
        replace_existing=True,
    )
    scheduler.add_job(
        scheduled_compute_indicators,
        trigger=CronTrigger(hour=17, minute=30, day_of_week='mon-fri'),
        id='sync_indicator',
        name='日线指标计算',
        replace_existing=True,
    )
    scheduler.start()
    print('[SCHEDULER] 定时任务调度器已启动')

    yield

    # 关闭时清理资源
    scheduler.shutdown(wait=False)
    print('[SCHEDULER] 定时任务调度器已关闭')


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
app.include_router(market_sentiment.router, prefix="/api")
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
