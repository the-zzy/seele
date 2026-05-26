"""
Seele 股票数据管理后端 - 主应用入口
"""

import asyncio
from contextlib import asynccontextmanager

from apscheduler.triggers.cron import CronTrigger
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import get_current_user
from app.config import get_settings
from app.database import engine, Base
from app.response import success
from app.routes import auth, financial, index, market_sentiment, pickers, portfolio, stock_basic, stock_daily, stock_indicator, sync, system_log, trade_calendar
from app.agent.router import router as agent_router
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
    # 启动时异步创建数据库表，避免阻塞 lifespan
    await asyncio.to_thread(Base.metadata.create_all, bind=engine)

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
    # 定时清理内存中超期的异步任务和 pipeline，防止无人查询时持续累积
    from app.routes.sync import _cleanup_timeout_tasks, _cleanup_timeout_pipelines
    scheduler.add_job(
        lambda: (_cleanup_timeout_tasks(), _cleanup_timeout_pipelines()),
        trigger='interval',
        minutes=10,
        id='cleanup_timeout_tasks',
        name='清理超时异步任务',
        replace_existing=True,
    )

    scheduler.start()
    print('[SCHEDULER] 定时任务调度器已启动')

    # 启动时后台预热 akshare 实时数据缓存（不阻塞启动）
    def _warmup_cache():
        import time
        time.sleep(3)
        try:
            from app.routes.index import _refresh_index_spot_cache
            _refresh_index_spot_cache()
            print('[WARMUP] 指数实时数据缓存已预热')
        except Exception as exc:
            print(f'[WARMUP] 指数缓存预热失败: {exc}')
        try:
            from app.routes.stock_daily import _refresh_live_price_cache
            _refresh_live_price_cache()
        except Exception as exc:
            print(f'[WARMUP] 股价缓存预热失败: {exc}')

    import threading
    threading.Thread(target=_warmup_cache, daemon=True).start()

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

# 全局异常处理器
logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理异常，避免返回 HTML 500 页面"""
    logger.error('未捕获异常 [%s %s]: %s', request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={'code': 500, 'message': '服务器内部错误', 'data': None}
    )

# 配置CORS
settings = get_settings()
origins = ["http://localhost:8000", "http://127.0.0.1:8000"]
if settings.deploy_env == "dev":
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（认证路由除外，其他全部需要 Bearer token）
auth_dep = [Depends(get_current_user)]

app.include_router(auth.router, prefix="/api")
app.include_router(stock_basic.router, prefix="/api", dependencies=auth_dep)
app.include_router(stock_daily.router, prefix="/api", dependencies=auth_dep)
app.include_router(stock_indicator.router, prefix="/api", dependencies=auth_dep)
app.include_router(pickers.router, prefix="/api", dependencies=auth_dep)
app.include_router(financial.router, prefix="/api", dependencies=auth_dep)
app.include_router(portfolio.router, prefix="/api", dependencies=auth_dep)
app.include_router(market_sentiment.router, prefix="/api", dependencies=auth_dep)
app.include_router(sync.router, prefix="/api", dependencies=auth_dep)
app.include_router(index.router, prefix="/api", dependencies=auth_dep)
app.include_router(system_log.router, prefix="/api", dependencies=auth_dep)
app.include_router(trade_calendar.router, prefix="/api", dependencies=auth_dep)
app.include_router(agent_router, prefix="/api", dependencies=auth_dep)


@app.get("/")
def root():
    """根路径"""
    return success("Seele 股票数据管理API (cache-fix-v1)")


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
        reload=settings.uvicorn_reload,
        workers=settings.uvicorn_workers,
    )

