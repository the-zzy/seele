"""
定时任务调度模块
"""

import logging
import threading
import traceback
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

from app.akshare_lock import akshare_lock
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """获取全局 scheduler 实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            timezone='Asia/Shanghai',
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 3600,
            },
        )
    return _scheduler


def _get_trade_dates() -> set[str]:
    """获取所有交易日（缓存到模块级变量）"""
    global _trade_dates_cache, _trade_dates_cache_time
    with _trade_dates_lock:
        if _trade_dates_cache is not None and _trade_dates_cache_time is not None:
            if datetime.now() - _trade_dates_cache_time < timedelta(hours=6):
                return _trade_dates_cache

        try:
            import akshare as ak
            with akshare_lock:
                df = ak.tool_trade_date_hist_sina()
            if df is not None and not df.empty:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                _trade_dates_cache = set(df['trade_date'].dt.strftime('%Y-%m-%d'))
                _trade_dates_cache_time = datetime.now()
                return _trade_dates_cache
        except Exception as exc:
            logger.warning('[SCHEDULER] 获取交易日历失败: %s', exc)

        return set()


def is_trading_day(check_date: datetime | None = None) -> bool:
    """判断是否为A股交易日"""
    if check_date is None:
        check_date = datetime.now()
    if check_date.weekday() >= 5:
        return False
    date_str = check_date.strftime('%Y-%m-%d')
    trade_dates = _get_trade_dates()
    if trade_dates:
        return date_str in trade_dates
    return True


def get_last_trade_date() -> str:
    """获取最近一个交易日（YYYYMMDD）"""
    trade_dates = _get_trade_dates()
    today = datetime.now().strftime('%Y-%m-%d')
    if trade_dates:
        past_dates = [d for d in trade_dates if d <= today]
        if past_dates:
            return max(past_dates).replace('-', '')
    d = datetime.now()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime('%Y%m%d')


def _with_job_log(job_type: str):
    """装饰器：自动记录 SyncJobLog"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app import crud, schemas

            db = SessionLocal()
            log = None
            try:
                log = crud.sync_job_log_crud.create(
                    db,
                    schemas.SyncJobLogCreate(job_type=job_type, trigger_type='scheduled')
                )
                db.commit()
                log_id = log.id
            except Exception as exc:
                logger.error('[SCHEDULER] 创建 job log 失败: %s', exc, exc_info=True)
                try:
                    from app import crud as _crud, schemas as _schemas
                    _db_err = SessionLocal()
                    _crud.system_error_log_crud.create(
                        _db_err,
                        _schemas.SystemErrorLogCreate(
                            level='error', source='scheduler', trace_id=None,
                            message=f'创建 job log 失败: {exc}'[:1000],
                            detail=traceback.format_exc()[:4000],
                        )
                    )
                    _db_err.commit()
                    _db_err.close()
                except Exception as exc:
                    logger.warning('[SCHEDULER] 写入 system_error_log 失败: %s', exc)
                db.close()
                raise
            finally:
                if log is None:
                    db.close()

            db2 = SessionLocal()
            try:
                result = func(db2, log_id, *args, **kwargs)
                return result
            except Exception as exc:
                logger.error('[SCHEDULER] 任务执行异常: %s', exc, exc_info=True)
                try:
                    from app import crud as _crud, schemas as _schemas
                    _db_err = SessionLocal()
                    _crud.system_error_log_crud.create(
                        _db_err,
                        _schemas.SystemErrorLogCreate(
                            level='error', source='scheduler', trace_id=str(log_id),
                            message=f'任务执行异常: {exc}'[:1000],
                            detail=traceback.format_exc()[:4000],
                        )
                    )
                    _db_err.commit()
                    _db_err.close()
                except Exception as exc:
                    logger.warning('[SCHEDULER] 写入 system_error_log 失败: %s', exc)
                try:
                    crud.sync_job_log_crud.finish(
                        db2, log_id, 'failed', error_message=str(exc)[:2000]
                    )
                    db2.commit()
                except Exception as exc:
                    logger.warning('[SCHEDULER] 更新 sync_job_log 失败状态失败: %s', exc)
                raise
            finally:
                db2.close()
        return wrapper
    return decorator


_trade_dates_cache: set[str] | None = None
_trade_dates_cache_time: datetime | None = None
_trade_dates_lock = threading.Lock()
