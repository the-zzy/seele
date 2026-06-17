"""
数据同步路由
"""

import asyncio
import concurrent.futures
import logging
import os
import socket
import threading
import time
import traceback
import uuid
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional

import baostock as bs
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session, load_only
from app import crud, models, schemas
from app.akshare_lock import akshare_lock
from app.config import get_settings
from app.database import SessionLocal, get_db
from app.response import success
from app.routes.stock_indicator import _build_indicator_for_symbol, _calc_indicator_stats, INDICATOR_FIELDS
from app.sync_worker import _fetch_akshare_batch, _fetch_baostock_chunk, _fetch_akshare_single

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["数据同步"])

# 后台任务状态存储
_task_lock = threading.Lock()
_task_registry: dict[str, dict] = {}

# 任务链状态存储
_pipeline_lock = threading.Lock()
_pipeline_registry: dict[str, dict] = {}

# 数据源可用性探测缓存（避免每次同步都重复探测）
_source_test_cache: dict[str, tuple[bool, float]] = {}
_SOURCE_TEST_CACHE_TTL = 300  # 5 分钟

# 流通市值缓存（避免每次同步 stock_basic 都重复拉取）
_cap_map_cache: dict[str, tuple[dict[str, float], float]] = {}
_CAP_MAP_CACHE_TTL = 300  # 5 分钟

PIPELINE_TIMEOUT_MINUTES = 60


def _register_pipeline(pipeline_id: str, chain_type: str, trade_date: str | None, steps: list[dict]) -> None:
    with _pipeline_lock:
        _pipeline_registry[pipeline_id] = {
            "pipeline_id": pipeline_id,
            "chain_type": chain_type,
            "trade_date": trade_date,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "error": None,
            "steps": [
                {
                    "name": s["name"],
                    "job_type": s["job_type"],
                    "status": "pending",
                    "trade_date": s.get("trade_date"),
                    "task_id": None,
                    "log_id": None,
                    "result": None,
                    "error": None,
                    "started_at": None,
                    "finished_at": None,
                    "skip_on_fail": s.get("skip_on_fail", False),
                }
                for s in steps
            ],
        }


def _update_pipeline_step(pipeline_id: str, step_index: int, **kwargs) -> None:
    with _pipeline_lock:
        pipeline = _pipeline_registry.get(pipeline_id)
        if pipeline and 0 <= step_index < len(pipeline["steps"]):
            pipeline["steps"][step_index].update(kwargs)


def _finish_pipeline(pipeline_id: str, status: str, error: str | None = None) -> None:
    with _pipeline_lock:
        pipeline = _pipeline_registry.get(pipeline_id)
        if pipeline:
            pipeline["status"] = status
            pipeline["finished_at"] = datetime.now().isoformat()
            if error:
                pipeline["error"] = error


def _cleanup_timeout_pipelines():
    """自动清理超时的 running pipeline"""
    cutoff = datetime.now() - timedelta(minutes=PIPELINE_TIMEOUT_MINUTES)
    with _pipeline_lock:
        for pipeline_id, pipeline in list(_pipeline_registry.items()):
            if pipeline["status"] == "running":
                started_at = datetime.fromisoformat(pipeline["started_at"])
                if started_at < cutoff:
                    pipeline["status"] = "failed"
                    pipeline["finished_at"] = datetime.now().isoformat()
                    pipeline["error"] = f"任务链超时（超过 {PIPELINE_TIMEOUT_MINUTES} 分钟）"
                    for step in pipeline["steps"]:
                        if step["status"] in ("pending", "running"):
                            step["status"] = "failed"
                            step["finished_at"] = datetime.now().isoformat()


def _register_task(task_id: str, trade_date: str, job_type: str = 'unknown', log_id: int | None = None) -> None:
    with _task_lock:
        _task_registry[task_id] = {
            "task_id": task_id,
            "trade_date": trade_date,
            "job_type": job_type,
            "log_id": log_id,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "result": None,
            "error": None,
            "progress": None,
        }


def _update_task_progress(task_id: str, current: int, total: int) -> None:
    with _task_lock:
        if task_id in _task_registry:
            _task_registry[task_id]["progress"] = {
                "current": current,
                "total": total,
                "percent": round(current / total * 100, 1) if total else 0,
            }


def _finish_task(task_id: str, result: Optional[dict] = None, error: Optional[str] = None) -> None:
    with _task_lock:
        if task_id in _task_registry:
            _task_registry[task_id]["status"] = "success" if error is None else "failed"
            _task_registry[task_id]["finished_at"] = datetime.now().isoformat()
            _task_registry[task_id]["result"] = result
            _task_registry[task_id]["error"] = error


TASK_TIMEOUT_MINUTES = 30


def _cleanup_timeout_tasks():
    """自动清理超时的 running 任务（内存 + 数据库）"""
    cutoff = datetime.now() - timedelta(minutes=TASK_TIMEOUT_MINUTES)
    with _task_lock:
        for task_id, task in list(_task_registry.items()):
            if task["status"] == "running":
                started_at = datetime.fromisoformat(task["started_at"])
                if started_at < cutoff:
                    task["status"] = "failed"
                    task["finished_at"] = datetime.now().isoformat()
                    task["error"] = f"任务超时（超过 {TASK_TIMEOUT_MINUTES} 分钟）"


def _cleanup_db_timeout_tasks(db: Session):
    """自动清理数据库中超时的 running 记录"""
    cutoff = datetime.now() - timedelta(minutes=TASK_TIMEOUT_MINUTES)
    db.query(models.SyncJobLog).filter(
        models.SyncJobLog.status == 'running',
        models.SyncJobLog.started_at < cutoff
    ).update({
        'status': 'failed',
        'ended_at': datetime.now(),
        'error_message': f'任务超时（超过 {TASK_TIMEOUT_MINUTES} 分钟）'
    }, synchronize_session=False)
    db.commit()


def format_date(d: date) -> str:
    """格式化日期"""
    return d.strftime("%Y-%m-%d")


def _test_baostock() -> bool:
    """测试 Baostock 是否可用（带 10 秒超时，结果缓存 5 分钟）"""
    now = time.time()
    cached = _source_test_cache.get('baostock')
    if cached and now - cached[1] < _SOURCE_TEST_CACHE_TTL:
        return cached[0]

    def _do_login():
        try:
            lg = bs.login()
            ok = lg.error_code == '0'
            if ok:
                bs.logout()
            return ok
        except Exception as exc:
            print(f'[SYNC] Baostock test failed: {exc}')
            return False
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_login)
            ok = future.result(timeout=10)
    except concurrent.futures.TimeoutError:
        print('[SYNC] Baostock test timeout (10s)')
        ok = False
    except Exception as exc:
        print(f'[SYNC] Baostock test failed: {exc}')
        ok = False
    _source_test_cache['baostock'] = (ok, now)
    return ok


def _test_akshare() -> bool:
    """测试 AkShare 新浪源是否可用（只拉当天数据，结果缓存 5 分钟）"""
    now = time.time()
    cached = _source_test_cache.get('akshare')
    if cached and now - cached[1] < _SOURCE_TEST_CACHE_TTL:
        return cached[0]

    try:
        import akshare as ak
        today = datetime.now().strftime('%Y%m%d')
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(10)
        try:
            with akshare_lock:
                df = ak.stock_zh_a_daily(symbol='sz000001', start_date=today, end_date=today, adjust='qfq')
        finally:
            socket.setdefaulttimeout(old_timeout)
        ok = df is not None and not df.empty
    except Exception as exc:
        print(f'[SYNC] AkShare test failed: {exc}')
        ok = False
    _source_test_cache['akshare'] = (ok, now)
    return ok


def _write_failed_log(trade_date: str, skipped: List[str], failed: List[dict]):
    """写入失败股票日志"""
    total = len(skipped) + len(failed)
    if total == 0:
        return
    lines = [f"# 失败股票代码列表", f"# 总计: {total}"]
    now = datetime.now().isoformat()
    for symbol in skipped:
        lines.append(f"{symbol}\t无数据\t{now}")
    for item in failed:
        lines.append(f"{item['symbol']}\t异常: {item['reason']}\t{now}")
    with open("failed_symbols.log", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def chunk_list(lst: List, n: int) -> List[List]:
    """将列表平均分成 n 份"""
    avg = len(lst) // n
    remainder = len(lst) % n
    chunks = []
    start = 0
    for i in range(n):
        size = avg + (1 if i < remainder else 0)
        chunks.append(lst[start:start + size])
        start += size
    return chunks


def _sync_daily_bulk(trade_date: str, source: str = 'akshare', task_id: str | None = None, on_progress: Callable | None = None, progress_queue: asyncio.Queue | None = None, only_missing: bool = False) -> dict:
    """按日期同步全部A股日线数据的内部实现（多进程版）"""
    db = SessionLocal()
    try:
        all_stocks = crud.stock_basic_crud.get_list(
            db,
            schemas.StockBasicQuery(page_num=1, page_size=10000)
        )[0]
        # 过滤北交所（baostock/akshare 数据源均不支持）
        all_stocks = [s for s in all_stocks if s.market != '北交所']
        if only_missing:
            formatted = trade_date.replace("-", "")
            trade_date_obj = datetime.strptime(formatted, "%Y%m%d").date()

            # 查询当日停牌股，与 get_detailed_status 口径一致
            suspended_symbols = db.query(models.StockSuspension.symbol).filter(
                models.StockSuspension.suspend_date <= trade_date_obj,
                or_(
                    models.StockSuspension.resume_date.is_(None),
                    models.StockSuspension.resume_date > trade_date_obj,
                ),
            ).all()
            suspended_set = set(s[0] for s in suspended_symbols)

            # 过滤退市、未上市、停牌
            # 兼容 list_date 为字符串的情况（某些驱动返回 str 而非 date）
            def _as_date(val):
                if isinstance(val, date):
                    return val
                if isinstance(val, str):
                    for fmt in ('%Y-%m-%d', '%Y%m%d'):
                        try:
                            return datetime.strptime(val, fmt).date()
                        except ValueError:
                            continue
                return None

            all_stocks = [
                s for s in all_stocks
                if _as_date(s.list_date) is not None
                and _as_date(s.list_date) <= trade_date_obj
                and '退' not in s.name
                and s.symbol not in suspended_set
            ]

            # 查询已有数据（join stock_basic 并做同样过滤）
            existing_rows = db.query(models.StockDaily.symbol).join(
                models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol
            ).filter(
                models.StockDaily.trade_date == trade_date_obj,
                models.StockBasic.market != '北交所',
                models.StockBasic.list_date.isnot(None),
                models.StockBasic.list_date <= trade_date_obj,
                ~models.StockBasic.name.like('%退%'),
            ).all()
            existing = set(row[0] for row in existing_rows)
            if suspended_set:
                existing = existing - suspended_set

            all_stocks = [s for s in all_stocks if s.symbol not in existing]
    finally:
        db.close()

    if source not in ('akshare', 'baostock'):
        raise ValueError(f"Unknown source: {source}")

    _skipped: List[str] = []
    _failed: List[dict] = []
    _results: List[dict] = []
    _total_stocks = len(all_stocks)
    _lock = threading.Lock()
    _counter = [0]
    _upserted_total = [0]

    # 预加载所有股票的前一日收盘价，避免每只股都查一次 DB
    preclose_map: dict[str, float] = {}
    if all_stocks:
        symbols = [s.symbol for s in all_stocks]
        target_date_obj = datetime.strptime(trade_date, '%Y%m%d').date()
        db_pre = SessionLocal()
        try:
            from sqlalchemy import func
            subq = db_pre.query(
                models.StockDaily.symbol,
                func.max(models.StockDaily.trade_date).label('max_date')
            ).filter(
                models.StockDaily.symbol.in_(symbols),
                models.StockDaily.trade_date < target_date_obj
            ).group_by(models.StockDaily.symbol).subquery()

            prev_rows = db_pre.query(
                models.StockDaily.symbol,
                models.StockDaily.close
            ).join(subq,
                (models.StockDaily.symbol == subq.c.symbol) &
                (models.StockDaily.trade_date == subq.c.max_date)
            ).all()
            preclose_map = {row[0]: float(row[1]) for row in prev_rows if row[1] is not None}
        except Exception as exc:
            logger.warning('[SYNC_DAILY_BULK] 预加载前收盘价失败: %s', exc)
        finally:
            db_pre.close()

    def _push_progress(current: int, status: str, extra: dict | None = None):
        payload = {"current": current, "total": _total_stocks, "status": status}
        if extra:
            payload.update(extra)
        if task_id and current % 10 == 0:
            _update_task_progress(task_id, current, _total_stocks)
        if on_progress:
            on_progress(current, _total_stocks, status)
        if progress_queue is not None:
            try:
                progress_queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def _flush_results():
        nonlocal _results
        if not _results:
            return
        batch = _results[:]
        db_write = SessionLocal()
        try:
            upsert_stmt = insert(models.StockDaily).values(batch)
            update_dict = {
                k: upsert_stmt.inserted[k]
                for k in upsert_stmt.inserted.keys()
                if k not in ("id", "trade_date", "symbol")
            }
            upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
            db_write.execute(upsert_stmt)
            db_write.commit()
            _upserted_total[0] += len(batch)
            _results = []
        except Exception as exc:
            logger.error('[SYNC_DAILY_BULK] 批量写入失败，批次大小 %s，错误: %s', len(batch), exc)
            try:
                db_err = SessionLocal()
                crud.system_error_log_crud.create(
                    db_err,
                    schemas.SystemErrorLogCreate(
                        level='error',
                        source='sync_daily_bulk',
                        trace_id=task_id if task_id else None,
                        message=str(exc)[:1000],
                        detail=traceback.format_exc()[:4000],
                    )
                )
                db_err.commit()
            except Exception as exc:
                logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc)
            finally:
                db_err.close()
            # 失败时不清空 _results，保留数据供最后重试
        finally:
            db_write.close()

    try:
        _push_progress(0, "running", {"message": f"开始同步（数据源: {source}）"})

        if not all_stocks:
            return {
                "trade_date": trade_date,
                "total_stocks": 0,
                "upserted": 0,
                "skipped": 0,
                "failed": 0,
                "failed_symbols": [],
                "summary": "无需要同步的股票",
            }

        # 多进程并行拉取（baostock / akshare 均走 ProcessPoolExecutor）
        # baostock：每个子进程独立登录，互不干扰
        # akshare：绕过 py_mini_racer 全局锁
        cpu_count = os.cpu_count() or 4
        workers = min(cpu_count, 6)
        if _total_stocks < 200:
            workers = 1
        elif _total_stocks < 1000:
            workers = min(cpu_count, 4)

        symbol_list = [s.symbol for s in all_stocks]
        chunk_size = 25
        chunks = [symbol_list[i:i + chunk_size] for i in range(0, len(symbol_list), chunk_size)]
        workers = min(workers, len(chunks))
        chunk_timeout = 60

        def _consume_batch(records, skipped, failed):
            with _lock:
                _results.extend(records)
                _skipped.extend(skipped)
                _failed.extend(failed)
                _counter[0] += len(records) + len(skipped)

                if len(_results) >= 1500:
                    _flush_results()

                _push_progress(_counter[0], "running", {
                    "symbol": "",
                    "success": _upserted_total[0] + len(_results),
                    "skipped": len(_skipped),
                    "failed": len(_failed)
                })

        def _run_parallel(fetch_fn, extra_args):
            """通用并行分片调度器，捕获 _consume_batch 等外部闭包"""
            nonlocal _failed
            executor = concurrent.futures.ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=1)
            try:
                future_meta = {}
                next_chunk_idx = 0

                def _submit_next_chunk():
                    nonlocal next_chunk_idx
                    if next_chunk_idx >= len(chunks):
                        return None
                    chunk = chunks[next_chunk_idx]
                    next_chunk_idx += 1
                    future = executor.submit(fetch_fn, chunk, *extra_args)
                    future_meta[future] = {
                        "symbols": chunk,
                        "started_at": time.monotonic(),
                    }
                    return future

                pending = set()
                for _ in range(workers):
                    future = _submit_next_chunk()
                    if future is not None:
                        pending.add(future)

                while pending:
                    done, pending = concurrent.futures.wait(
                        pending,
                        timeout=5,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )

                    for future in done:
                        meta = future_meta[future]
                        try:
                            records, skipped, failed = future.result()
                        except Exception as exc:
                            symbols = meta["symbols"]
                            logger.error(
                                '[SYNC_DAILY_BULK] 子进程批次异常，股票 %s~%s，数量 %s，错误: %s',
                                symbols[0], symbols[-1], len(symbols), exc
                            )
                            failed = [
                                {"symbol": symbol, "reason": f"batch exception: {exc}"}
                                for symbol in symbols
                            ]
                            _consume_batch([], [], failed)
                            next_future = _submit_next_chunk()
                            if next_future is not None:
                                pending.add(next_future)
                            continue

                        _consume_batch(records, skipped, failed)
                        next_future = _submit_next_chunk()
                        if next_future is not None:
                            pending.add(next_future)

                    now = time.monotonic()
                    timed_out = [
                        future for future in pending
                        if now - future_meta[future]["started_at"] > chunk_timeout
                    ]
                    for future in timed_out:
                        pending.remove(future)
                        meta = future_meta[future]
                        symbols = meta["symbols"]
                        cancelled = future.cancel()
                        if not cancelled:
                            logger.error(
                                '[SYNC_DAILY_BULK] 子进程批次超时(%ss)且无法取消，股票 %s~%s，数量 %s，可能是子进程卡死',
                                chunk_timeout, symbols[0], symbols[-1], len(symbols)
                            )
                        else:
                            logger.error(
                                '[SYNC_DAILY_BULK] 子进程批次超时(%ss)，股票 %s~%s，数量 %s，cancelled=%s',
                                chunk_timeout, symbols[0], symbols[-1], len(symbols), cancelled
                            )
                        failed = [
                            {"symbol": symbol, "reason": f"batch timeout ({chunk_timeout}s)"}
                            for symbol in symbols
                        ]
                        _consume_batch([], [], failed)
                        # 如果子进程无法取消，说明有进程卡死，不再提交新 chunk，等待 shutdown 清理
                        if not cancelled:
                            logger.warning('[SYNC_DAILY_BULK] 检测到卡死子进程，停止提交新 chunk')
                            next_chunk_idx = len(chunks)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

        # ----- 主数据源拉取 -----
        if source == 'baostock':
            _run_parallel(_fetch_baostock_chunk, (trade_date,))
        else:
            _run_parallel(_fetch_akshare_batch, (trade_date, preclose_map))

        # ----- akshare 兜底：重试 baostock 失败的个股 -----
        if source == 'baostock' and _failed:
            fallback_symbols = [f['symbol'] for f in _failed]
            _failed.clear()
            logger.info(
                '[SYNC_DAILY_BULK] Baostock 失败 %d 只，尝试 akshare 兜底',
                len(fallback_symbols)
            )
            for symbol in fallback_symbols:
                try:
                    records, skipped, failed = _fetch_akshare_single(
                        symbol, trade_date, preclose_map
                    )
                    _consume_batch(records, skipped, failed)
                except Exception as exc:
                    logger.warning(
                        '[SYNC_DAILY_BULK] akshare 兜底失败 %s: %s', symbol, exc
                    )
                    _consume_batch(
                        [], [],
                        [{'symbol': symbol, 'reason': f'akshare fallback error: {exc}'}]
                    )

    finally:
        pass

    with _lock:
        _flush_results()

    _write_failed_log(trade_date, _skipped, _failed)

    if task_id:
        _update_task_progress(task_id, _total_stocks, _total_stocks)

    with _lock:
        return {
            "trade_date": trade_date,
            "total_stocks": _total_stocks,
            "upserted": _upserted_total[0],
            "skipped": len(_skipped),
            "failed": len(_failed),
            "failed_symbols": [item["symbol"] for item in _failed[:50]],
            "summary": (
                f"日期 {trade_date} 同步完成（{source}），"
                f"写入/更新: {_upserted_total[0]}, "
                f"停牌/无数据: {len(_skipped)}, "
                f"异常: {len(_failed)}"
            ),
        }


def _run_sync_bg(task_id: str, trade_date: str, log_id: int, only_missing: bool = False) -> None:
    """后台执行同步任务（仅使用 baostock）"""
    db = SessionLocal()
    try:
        source = 'baostock'
        if not _test_baostock():
            raise RuntimeError('Baostock 探测不可用，已按配置禁止回退 AkShare')
        result = _sync_daily_bulk(trade_date, source=source, task_id=task_id, only_missing=only_missing)
        upserted = result.get('upserted', 0)
        failed = result.get('failed', 0)
        skipped = result.get('skipped', 0)
        total = result.get('total_stocks', 0)

        # 如果全部失败且没有任何写入或跳过，标记为 failed
        status = 'failed' if (upserted == 0 and skipped == 0 and failed > 0) else 'success'

        # 日线同步成功后自动预计算市场情绪
        if status == 'success':
            try:
                from app.routes.market_sentiment import _persist_market_sentiment
                trade_date_obj = datetime.strptime(trade_date, '%Y%m%d').date()
                _persist_market_sentiment(db, trade_date_obj)
                logger.info('[SYNC_DAILY_BG] 市场情绪预计算完成: %s', trade_date)
            except Exception as exc:
                logger.warning('[SYNC_DAILY_BG] 市场情绪预计算失败: %s', exc)

            # 日线同步成功后自动重建 portfolio 资产数据（修复历史日线补齐后资产趋势断层）
            try:
                from app.routes.portfolio import _rebuild_daily_data
                db_portfolio = SessionLocal()
                missing = _rebuild_daily_data(db_portfolio)
                if missing:
                    logger.warning('[SYNC_DAILY_BG] portfolio 重建发现缺失日线: %s', missing[:5])
                else:
                    db_portfolio.commit()
                    logger.info('[SYNC_DAILY_BG] portfolio 资产数据重建完成')
            except Exception as exc:
                logger.warning('[SYNC_DAILY_BG] portfolio 重建失败: %s', exc)
            finally:
                db_portfolio.close()

        _finish_task(task_id, result=result)
        crud.sync_job_log_crud.finish(
            db, log_id, status,
            success_count=upserted,
            failed_count=failed,
            skipped_count=skipped,
            total_count=total,
            trade_date=trade_date,
            extra_info=result.get('summary', ''),
        )
        db.commit()
    except Exception as exc:
        logger.error('[SYNC_DAILY_BG] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        _finish_task(task_id, error=str(exc))
        crud.sync_job_log_crud.finish(
            db, log_id, 'failed', error_message=str(exc)[:2000]
        )
        db.commit()
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_daily_bg',
                    trace_id=str(log_id),
                    message=f'日线同步任务异常: {exc}'[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc2:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc2)
        finally:
            db_err.close()
    finally:
        db.close()


def _run_sync_single_stock_bg(task_id: str, symbol: str, trade_date: str, log_id: int) -> None:
    """后台执行单只股票日线+指标同步任务"""
    db = SessionLocal()
    try:
        formatted_date = trade_date.replace("-", "")
        trade_date_obj = datetime.strptime(formatted_date, "%Y%m%d").date()
        date_str = trade_date_obj.strftime("%Y-%m-%d")

        _update_task_progress(task_id, 1, 3)

        # 1. 拉取日线数据：先 baostock，失败则回退 akshare
        records = []
        failed = []
        source = "baostock"
        try:
            if _test_baostock():
                baostock_records, _, baostock_failed = _fetch_baostock_chunk([symbol], formatted_date)
                records = baostock_records
                failed = baostock_failed
        except Exception as exc:
            logger.warning('[SYNC_SINGLE] baostock 拉取失败: %s', exc)

        if not records:
            source = "akshare"
            try:
                ak_records, _, ak_failed = _fetch_akshare_single(symbol, formatted_date, {})
                records = ak_records
                if not failed:
                    failed = ak_failed
            except Exception as exc:
                logger.warning('[SYNC_SINGLE] akshare 拉取失败: %s', exc)

        if not records:
            msg = f"未获取到 {symbol} 在 {date_str} 的日线数据"
            crud.sync_job_log_crud.finish(db, log_id, 'failed', error_message=msg)
            db.commit()
            _finish_task(task_id, error=msg)
            return

        # 2. 写入/更新日线记录
        daily_record = records[0]
        daily_record['trade_date'] = date_str
        crud.stock_daily_crud.upsert(db, schemas.StockDailyCreate(**daily_record))
        db.commit()

        _update_task_progress(task_id, 2, 3)

        # 3. 计算并写入指标
        indicator_data = _build_indicator_for_symbol(db, symbol, trade_date_obj, lookback=60)
        if indicator_data is None:
            indicator_data = {field: -1 for field in INDICATOR_FIELDS}
        indicator_data.pop('symbol', None)
        indicator_data.pop('trade_date', None)
        crud.stock_daily_indicator_crud.create_or_update(db, symbol, trade_date_obj, indicator_data)
        db.commit()

        indicator_stats = _calc_indicator_stats([indicator_data])

        _update_task_progress(task_id, 3, 3)
        result = {
            'symbol': symbol,
            'trade_date': formatted_date,
            'source': source,
            'daily_upserted': 1,
            'indicator_upserted': 1,
            'failed': failed,
            'indicator_stats': indicator_stats,
        }
        crud.sync_job_log_crud.finish(
            db, log_id, 'success',
            success_count=1,
            failed_count=len(failed),
            total_count=1,
            trade_date=formatted_date,
            extra_info=f'single stock sync {symbol} {date_str}, source={source}',
        )
        db.commit()
        _finish_task(task_id, result=result)
    except Exception as exc:
        logger.error('[SYNC_SINGLE] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        _finish_task(task_id, error=str(exc))
        crud.sync_job_log_crud.finish(db, log_id, 'failed', error_message=str(exc)[:2000])
        db.commit()
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_single_stock_bg',
                    trace_id=str(log_id),
                    message=f'单股同步异常: {exc}'[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc2:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc2)
        finally:
            if 'db_err' in locals():
                db_err.close()
    finally:
        db.close()


# 3.2.1 按日期同步全部A股日线数据（后台异步版）
@router.post("/daily/date/{trade_date}")
def post_sync_daily_by_date(
    trade_date: str,
    only_missing: bool = Query(False, description="仅同步缺失数据"),
    db: Session = Depends(get_db),
):
    """
    按日期同步全部A股日线数据（后台异步版）
    - 仅使用 Baostock 获取日线数据
    - 更新到数据库（存在则更新，不存在则插入）
    """
    formatted_date = trade_date.replace("-", "")
    log = crud.sync_job_log_crud.create(
        db, schemas.SyncJobLogCreate(job_type='daily', trigger_type='manual', trade_date=formatted_date)
    )
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='sync_manual',
            target_type='job',
            target_id=str(log.id),
            detail=f'手动触发日线同步，日期={formatted_date}, 仅缺失={only_missing}',
            result='success',
        )
    )
    db.commit()
    task_id = str(uuid.uuid4())
    _register_task(task_id, formatted_date, job_type='daily', log_id=log.id)
    t = threading.Thread(target=_run_sync_bg, args=(task_id, formatted_date, log.id, only_missing), daemon=True)
    t.start()
    logger.info('[SYNC_DAILY_API] 已提交后台任务, log_id=%s, trade_date=%s, only_missing=%s', log.id, formatted_date, only_missing)
    return success({
        "task_id": task_id,
        "log_id": log.id,
        "trade_date": formatted_date,
        "status": "running",
        "hint": "同步任务已提交后台执行，约需 5-10 秒，请稍后刷新页面查看",
    })


# 3.2.2 按股票+日期同步单股日线数据及指标（后台异步版）
@router.post("/daily/stock/{symbol}/date/{trade_date}")
def post_sync_daily_single_stock(
    symbol: str,
    trade_date: str,
    db: Session = Depends(get_db),
):
    """
    同步单只股票指定日期的日线数据及指标（后台异步版）
    - 先尝试 Baostock，失败回退 AkShare
    - 日线写入后自动计算并写入指标
    """
    formatted_date = trade_date.replace("-", "")
    log = crud.sync_job_log_crud.create(
        db, schemas.SyncJobLogCreate(job_type='daily_single', trigger_type='manual', trade_date=formatted_date)
    )
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='sync_manual',
            target_type='job',
            target_id=str(log.id),
            detail=f'手动触发单股同步，股票={symbol}, 日期={formatted_date}',
            result='success',
        )
    )
    db.commit()
    task_id = str(uuid.uuid4())
    _register_task(task_id, formatted_date, job_type='daily_single', log_id=log.id)
    with _task_lock:
        _task_registry[task_id]['symbol'] = symbol
    t = threading.Thread(target=_run_sync_single_stock_bg, args=(task_id, symbol, formatted_date, log.id), daemon=True)
    t.start()
    logger.info('[SYNC_SINGLE_API] 已提交后台任务, log_id=%s, symbol=%s, trade_date=%s', log.id, symbol, formatted_date)
    return success({
        "task_id": task_id,
        "log_id": log.id,
        "symbol": symbol,
        "trade_date": formatted_date,
        "status": "running",
        "hint": "单股同步任务已提交后台执行，约需 3-5 秒，请稍后刷新页面查看",
    })


# 3.2.3 查询同步任务状态
@router.get("/task/{task_id}")
def get_sync_task_status(task_id: str):
    """查询同步任务状态"""
    _cleanup_timeout_tasks()
    with _task_lock:
        task = _task_registry.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return success(task)


# 3.2.4 查询当前活跃任务列表
@router.get("/active-tasks")
def get_active_tasks():
    """查询当前正在运行的同步任务列表"""
    _cleanup_timeout_tasks()
    with _task_lock:
        tasks = [
            {
                "task_id": t["task_id"],
                "trade_date": t["trade_date"],
                "job_type": t.get("job_type", "unknown"),
                "log_id": t.get("log_id"),
                "status": t["status"],
                "started_at": t["started_at"],
                "progress": t.get("progress"),
            }
            for t in _task_registry.values()
            if t["status"] == "running"
        ]
    return success({"tasks": tasks, "count": len(tasks)})


# 3.2.5 取消正在运行的同步任务
@router.post("/task/{task_id}/cancel")
def post_cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    """取消正在运行的同步任务，并同步标记对应 job log 为 failed"""
    with _task_lock:
        task = _task_registry.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] != "running":
        raise HTTPException(status_code=400, detail="任务未在运行中")

    task["status"] = "failed"
    task["finished_at"] = datetime.now().isoformat()
    task["error"] = "手动取消"

    log_id = task.get("log_id")
    if log_id:
        db_obj = crud.sync_job_log_crud.get_by_id(db, log_id)
        if db_obj and db_obj.status == 'running':
            crud.sync_job_log_crud.finish(
                db, log_id, 'failed',
                success_count=db_obj.success_count or 0,
                failed_count=db_obj.failed_count or 0,
                skipped_count=db_obj.skipped_count or 0,
                total_count=db_obj.total_count or 0,
                error_message='手动取消',
            )
            db.commit()

    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='task_cancel',
            target_type='task',
            target_id=task_id,
            detail=f'手动取消同步任务，job_type={task.get("job_type")}, log_id={log_id}',
            result='success',
        )
    )
    db.commit()
    return success({"task_id": task_id, "status": "cancelled"})


def _infer_market(symbol: str) -> str:
    """根据股票代码前缀推断市场板块"""
    if symbol.startswith(('600', '601', '603', '605', '000', '001', '002', '003')):
        return '主板'
    elif symbol.startswith(('300', '301')):
        return '创业板'
    elif symbol.startswith('688'):
        return '科创板'
    elif symbol.startswith(('4', '8', '43', '83', '87', '88', '920')):
        return '北交所'
    return '其他'


def _parse_list_date(val) -> Optional[date]:
    """解析上市日期"""
    if pd.isna(val) or val == '' or val is None:
        return None
    try:
        return pd.to_datetime(val).date()
    except (ValueError, TypeError):
        return None


def _sync_stock_basic_from_akshare(db: Session, task_id: str | None = None, total_estimate: int = 5500) -> dict:
    """从 AkShare 同步股票基础信息（上交所 + 深交所 + 北交所）"""
    import akshare as ak

    records_map: dict[str, dict] = {}

    # 获取流通市值（亿元），带 5 分钟缓存
    cap_map: dict[str, float] = {}
    now = time.time()
    cached_cap = _cap_map_cache.get('spot')
    if cached_cap and now - cached_cap[1] < _CAP_MAP_CACHE_TTL:
        cap_map = cached_cap[0]
        logger.info('[SYNC_STOCK_BASIC] 使用缓存流通市值 (%d 只)', len(cap_map))
    else:
        try:
            with akshare_lock:
                df_spot = ak.stock_zh_a_spot_em()
            for _, row in df_spot.iterrows():
                symbol = str(row['代码']).strip().zfill(6)
                cap = row.get('流通市值')
                if pd.notna(cap) and cap:
                    cap_map[symbol] = round(float(cap) / 1e8, 4)
            _cap_map_cache['spot'] = (cap_map, now)
            logger.info('[SYNC_STOCK_BASIC] 刷新流通市值缓存 (%d 只)', len(cap_map))
        except Exception as exc:
            logger.warning('[SYNC_STOCK_BASIC] 获取流通市值失败: %s', exc)

    # 1. 上海
    with akshare_lock:
        df_sh = ak.stock_info_sh_name_code()
    for _, row in df_sh.iterrows():
        symbol = str(row['证券代码']).strip().zfill(6)
        if not symbol.isdigit():
            continue
        records_map[symbol] = {
            'symbol': symbol,
            'name': str(row['证券简称']).strip(),
            'list_date': _parse_list_date(row['上市日期']),
            'market': _infer_market(symbol),
            'industry': None,
            'area': None,
            'float_market_cap': cap_map.get(symbol),
        }

    # 2. 深圳
    with akshare_lock:
        df_sz = ak.stock_info_sz_name_code()
    for _, row in df_sz.iterrows():
        symbol = str(row['A股代码']).strip().zfill(6)
        if not symbol.isdigit():
            continue
        records_map[symbol] = {
            'symbol': symbol,
            'name': str(row['A股简称']).strip(),
            'list_date': _parse_list_date(row['A股上市日期']),
            'market': _infer_market(symbol),
            'industry': str(row['所属行业']).strip() if pd.notna(row['所属行业']) else None,
            'area': None,
            'float_market_cap': cap_map.get(symbol),
        }

    # 3. 北京
    with akshare_lock:
        df_bj = ak.stock_info_bj_name_code()
    for _, row in df_bj.iterrows():
        symbol = str(row['证券代码']).strip().zfill(6)
        if not symbol.isdigit():
            continue
        records_map[symbol] = {
            'symbol': symbol,
            'name': str(row['证券简称']).strip(),
            'list_date': _parse_list_date(row['上市日期']),
            'market': _infer_market(symbol),
            'industry': str(row['所属行业']).strip() if pd.notna(row['所属行业']) else None,
            'area': str(row['地区']).strip() if pd.notna(row['地区']) else None,
            'float_market_cap': cap_map.get(symbol),
        }

    records = [schemas.StockBasicCreate(**d) for d in records_map.values()]
    result = crud.stock_basic_crud.upsert_batch(db, records)
    if task_id:
        _update_task_progress(task_id, total_estimate, total_estimate)
    return {
        'total': len(records),
        'success': result['success'],
        'failed': result['failed'],
    }


def _sync_stock_basic_from_baostock(db: Session, task_id: str | None = None, total_estimate: int = 5500) -> dict:
    """从 Baostock 同步股票基础信息"""
    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"Baostock login failed: {lg.error_msg}")

    try:
        # 1. 获取基础信息
        rs_basic = bs.query_stock_basic()
        basic_map: dict[str, dict] = {}
        while rs_basic.error_code == '0' and rs_basic.next():
            row = rs_basic.get_row_data()
            code = row[0]
            symbol = code.split('.')[1]
            basic_map[symbol] = {
                'symbol': symbol,
                'name': row[1],
                'ipo_date': row[2] if row[2] else None,
                'out_date': row[3] if row[3] else None,
                'type': row[4],
                'status': row[5],
            }

        # 2. 获取行业信息
        rs_industry = bs.query_stock_industry()
        industry_map: dict[str, str] = {}
        while rs_industry.error_code == '0' and rs_industry.next():
            row = rs_industry.get_row_data()
            code = row[1]
            symbol = code.split('.')[1]
            industry = row[3].strip() if row[3] else None
            if industry:
                industry_map[symbol] = industry

        # 3. 过滤并组装数据（仅保留 A 股且正常上市）
        records: list[schemas.StockBasicCreate] = []
        for symbol, basic in basic_map.items():
            if basic['type'] != '1' or basic['status'] != '1':
                continue
            if basic['out_date']:
                continue

            list_date = _parse_list_date(basic['ipo_date'])

            records.append(schemas.StockBasicCreate(
                symbol=symbol,
                name=basic['name'],
                industry=industry_map.get(symbol),
                market=_infer_market(symbol),
                list_date=list_date,
            ))

        # 4. 批量写入
        result = crud.stock_basic_crud.upsert_batch(db, records)
        if task_id:
            _update_task_progress(task_id, total_estimate, total_estimate)
        return {
            'total': len(records),
            'success': result['success'],
            'failed': result['failed'],
        }
    finally:
        bs.logout()


def _sync_stock_suspension(db: Session) -> dict:
    """从 akshare 同步停牌信息"""
    import akshare as ak
    from datetime import datetime

    today = datetime.now().strftime('%Y%m%d')
    try:
        with akshare_lock:
            df = ak.stock_tfp_em(date=today)
    except Exception as exc:
        logger.warning('[SYNC_SUSPENSION] 获取停牌数据失败: %s', exc)
        return {'total': 0, 'upserted': 0}

    if df is None or df.empty:
        return {'total': 0, 'upserted': 0}

    records = []
    for _, row in df.iterrows():
        symbol = str(row.get('代码', '')).strip().zfill(6)
        if not symbol.isdigit():
            continue
        name = str(row.get('名称', '')).strip()
        suspend_date_str = row.get('停牌时间', '')
        resume_date_str = row.get('预计复牌时间', '')
        reason = str(row.get('停牌原因', '')).strip() if pd.notna(row.get('停牌原因')) else None

        suspend_date = _parse_list_date(suspend_date_str)
        resume_date = _parse_list_date(resume_date_str)

        records.append(schemas.StockSuspensionCreate(
            symbol=symbol,
            name=name,
            suspend_date=suspend_date,
            resume_date=resume_date,
            reason=reason,
        ))

    result = crud.stock_suspension_crud.upsert_batch(db, records)
    return {'total': len(records), 'upserted': result['success']}


def _run_sync_stock_basic_bg(task_id: str, log_id: int) -> None:
    """后台执行股票基础信息同步任务"""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        total_estimate = db.query(func.count(models.StockBasic.id)).scalar() or 5500
        _update_task_progress(task_id, 0, total_estimate)
        try:
            result = _sync_stock_basic_from_akshare(db, task_id=task_id, total_estimate=total_estimate)
            source = 'akshare'
            extra = f'source={source}'
        except Exception as exc:
            result = _sync_stock_basic_from_baostock(db, task_id=task_id, total_estimate=total_estimate)
            source = 'baostock'
            extra = f'source={source}, fallback_reason={str(exc)[:200]}'

        # 同步停牌信息
        suspension_result = _sync_stock_suspension(db)
        extra += f', suspension={suspension_result["upserted"]}/{suspension_result["total"]}'

        crud.sync_job_log_crud.finish(
            db, log_id, 'success',
            success_count=result.get('success', 0),
            total_count=result.get('total', 0),
            extra_info=extra,
        )
        db.commit()
        _update_task_progress(task_id, total_estimate, total_estimate)
        _finish_task(task_id, result={
            'summary': f"同步完成（{source}），共 {result['total']} 条，成功 {result['success']} 条，失败 {result['failed']} 条，停牌 {suspension_result['upserted']} 条",
            **result,
            'log_id': log_id,
        })
    except Exception as exc:
        logger.error('[SYNC_STOCK_BASIC_BG] 任务异常, log_id=%s, error=%s', log_id, exc)
        logger.error(traceback.format_exc())
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_stock_basic_bg',
                    trace_id=str(log_id),
                    message=str(exc)[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc)
        finally:
            db_err.close()
        crud.sync_job_log_crud.finish(
            db, log_id, 'failed', error_message=str(exc)[:2000]
        )
        db.commit()
        _finish_task(task_id, error=str(exc))
    finally:
        db.close()


# 3.5 同步股票基础信息（后台异步版）
@router.post("/stock-basic")
def post_sync_stock_basic(
    db: Session = Depends(get_db),
):
    """同步股票基础信息（优先 akshare，失败回退 baostock）"""
    log = crud.sync_job_log_crud.create(
        db, schemas.SyncJobLogCreate(job_type='stock_basic', trigger_type='manual')
    )
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='sync_manual',
            target_type='job',
            target_id=str(log.id),
            detail='手动触发股票基础信息同步',
            result='success',
        )
    )
    db.commit()
    task_id = str(uuid.uuid4())
    _register_task(task_id, "stock_basic", job_type='stock_basic', log_id=log.id)
    t = threading.Thread(target=_run_sync_stock_basic_bg, args=(task_id, log.id), daemon=True)
    t.start()
    logger.info('[SYNC_STOCK_BASIC_API] 已提交后台任务, log_id=%s', log.id)
    return success({
        "task_id": task_id,
        "log_id": log.id,
        "status": "running",
        "hint": "股票基础信息同步任务已提交后台执行，约需 10-30 秒，请稍后刷新页面查看",
    })


# ==================== 财务指标同步 ====================


def _parse_financial_value(val):
    """解析财务指标值，处理 '--'、空值、False、中文单位、百分比等"""
    if val is None or val == '' or val == '--' or val is False:
        return None
    val_str = str(val).strip()
    if val_str == '--' or val_str == 'False':
        return None
    # 移除百分比符号
    if val_str.endswith('%'):
        val_str = val_str[:-1]
    # 移除中文单位（亿、万）并转换
    multiplier = 1
    if val_str.endswith('亿'):
        multiplier = 1
        val_str = val_str[:-1]
    elif val_str.endswith('万'):
        multiplier = 1
        val_str = val_str[:-1]
    try:
        return float(val_str) * multiplier
    except (ValueError, TypeError):
        return None


def _sync_financial_for_symbol(symbol: str, name: str) -> Optional[dict]:
    """同步单只股票财务指标，返回解析后的数据字典（带 15 秒超时）"""
    def _fetch():
        import akshare as ak
        with akshare_lock:
            df = ak.stock_financial_abstract_ths(symbol, indicator='按报告期')
        if df is None or df.empty:
            return None
        row = df.iloc[-1]
        return {
            'symbol': symbol,
            'name': name,
            'report_date': _parse_list_date(row.get('报告期')),
            'net_profit': _parse_financial_value(row.get('净利润')),
            'net_profit_yoy': _parse_financial_value(row.get('净利润同比增长率')),
            'deduct_net_profit': _parse_financial_value(row.get('扣非净利润')),
            'total_revenue': _parse_financial_value(row.get('营业总收入')),
            'revenue_yoy': _parse_financial_value(row.get('营业总收入同比增长率')),
            'gross_profit_ratio': _parse_financial_value(row.get('销售毛利率')),
            'net_profit_ratio': _parse_financial_value(row.get('销售净利率')),
            'roe': _parse_financial_value(row.get('净资产收益率')),
            'roe_diluted': _parse_financial_value(row.get('净资产收益率-摊薄')),
            'eps': _parse_financial_value(row.get('基本每股收益')),
            'bps': _parse_financial_value(row.get('每股净资产')),
            'ops_cash_flow_per_share': _parse_financial_value(row.get('每股经营现金流')),
            'current_ratio': _parse_financial_value(row.get('流动比率')),
            'quick_ratio': _parse_financial_value(row.get('速动比率')),
            'debt_ratio': _parse_financial_value(row.get('资产负债率')),
            'total_assets': _parse_financial_value(row.get('资产总计')),
            'total_equity': _parse_financial_value(row.get('所有者权益（或股东权益）合计')),
            'operate_cash_flow': _parse_financial_value(row.get('经营活动产生的现金流量净额')),
        }

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch)
            return future.result(timeout=10)
    except concurrent.futures.TimeoutError:
        logger.warning('[SYNC_FINANCIAL] 获取 %s 财务数据超时', symbol)
        return None
    except (ValueError, TypeError):
        return None


def _sync_financial_bulk(
    task_id: str | None = None,
    on_progress: Callable | None = None,
    progress_queue: asyncio.Queue | None = None,
    only_missing: bool = False,
) -> dict:
    """批量同步全部股票财务指标（多线程版）"""
    logger.info('[SYNC_FINANCIAL] 开始批量同步财务指标, only_missing=%s', only_missing)
    db = SessionLocal()
    try:
        all_stocks = crud.stock_basic_crud.get_list(
            db,
            schemas.StockBasicQuery(page_num=1, page_size=10000)
        )[0]
        if only_missing:
            existing_symbols = set(
                row[0] for row in db.query(models.StockFinancialIndicator.symbol).all()
            )
            all_stocks = [s for s in all_stocks if s.symbol not in existing_symbols]
            logger.info('[SYNC_FINANCIAL] 增量模式：过滤后剩 %d 只待同步', len(all_stocks))
    except Exception as exc:
        logger.error('[SYNC_FINANCIAL] 获取股票列表失败: %s', exc)
        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()

    _failed: List[str] = []
    _records: List[dict] = []
    _total_stocks = len(all_stocks)
    _lock = threading.Lock()
    _counter = [0]
    logger.info('[SYNC_FINANCIAL] 共 %d 只股票待同步', _total_stocks)

    def _push_progress(current: int, status: str, extra: dict | None = None):
        payload = {"current": current, "total": _total_stocks, "status": status}
        if extra:
            payload.update(extra)
        if task_id and current % 10 == 0:
            _update_task_progress(task_id, current, _total_stocks)
        if on_progress:
            on_progress(current, _total_stocks, status)
        if progress_queue is not None:
            try:
                progress_queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def _process_stock(stock):
        data = _sync_financial_for_symbol(stock.symbol, stock.name)
        with _lock:
            if data:
                _records.append(data)
            else:
                _failed.append(stock.symbol)
            _counter[0] += 1
            current = _counter[0]
            _push_progress(current, "running", {
                "symbol": stock.symbol,
                "success": len(_records),
                "failed": len(_failed),
            })

    _push_progress(0, "running", {"message": "开始同步财务指标"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=get_settings().sync_max_workers) as executor:
        futures = [executor.submit(_process_stock, stock) for stock in all_stocks]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                logger.error('处理股票异常: %s', exc)

    # 批量写入
    db_write = SessionLocal()
    try:
        from sqlalchemy.dialects.mysql import insert
        if _records:
            logger.info('[SYNC_FINANCIAL] 准备写入 %d 条记录', len(_records))
            upsert_stmt = insert(models.StockFinancialIndicator).values(_records)
            update_dict = {
                k: upsert_stmt.inserted[k]
                for k in upsert_stmt.inserted.keys()
                if k not in ("symbol", "updated_at")
            }
            upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
            db_write.execute(upsert_stmt)
            db_write.commit()
            logger.info('[SYNC_FINANCIAL] 写入完成')
        else:
            logger.warning('[SYNC_FINANCIAL] 没有记录需要写入')
    except Exception as exc:
        logger.error('[SYNC_FINANCIAL] 批量写入失败: %s', exc)
        logger.error(traceback.format_exc())
        raise
    finally:
        db_write.close()

    return {
        "total_stocks": _total_stocks,
        "upserted": len(_records),
        "failed": len(_failed),
        "failed_symbols": _failed[:50],
        "summary": (
            f"财务指标同步完成，"
            f"写入/更新: {len(_records)}, "
            f"异常: {len(_failed)}"
        ),
    }


def _run_sync_financial_bg(task_id: str, only_missing: bool = False) -> None:
    """后台执行财务指标同步任务"""
    logger.info('[SYNC_FINANCIAL_BG] 后台任务启动, task_id=%s, only_missing=%s', task_id, only_missing)
    try:
        result = _sync_financial_bulk(task_id=task_id, only_missing=only_missing)
        _finish_task(task_id, result=result)
        logger.info('[SYNC_FINANCIAL_BG] 任务完成, task_id=%s', task_id)
    except Exception as exc:
        logger.error('[SYNC_FINANCIAL_BG] 任务异常, task_id=%s, error=%s', task_id, exc)
        logger.error(traceback.format_exc())
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_financial_bg',
                    trace_id=task_id,
                    message=str(exc)[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc)
        finally:
            db_err.close()
        _finish_task(task_id, error=str(exc))


# 3.6 同步全部股票财务指标（后台异步版）
@router.post("/financial")
def post_sync_financial(
    only_missing: bool = Query(False, description="仅同步缺失数据"),
    db: Session = Depends(get_db),
):
    """同步全部股票财务指标（后台异步版）"""
    log = crud.sync_job_log_crud.create(
        db, schemas.SyncJobLogCreate(job_type='financial', trigger_type='manual')
    )
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='sync_manual',
            target_type='job',
            target_id=str(log.id),
            detail='手动触发财务指标同步',
            result='success',
        )
    )
    db.commit()
    try:
        task_id = str(uuid.uuid4())
        _register_task(task_id, "financial", job_type='financial', log_id=log.id)
        # 在后台线程中执行，但需要把 log_id 传进去以便更新
        def _run_with_log():
            db2 = SessionLocal()
            try:
                result = _sync_financial_bulk(only_missing=only_missing)
                crud.sync_job_log_crud.finish(
                    db2, log.id, 'success',
                    success_count=result.get('upserted', 0),
                    failed_count=result.get('failed', 0),
                    total_count=result.get('total_stocks', 0),
                    extra_info='source=akshare_ths',
                )
                db2.commit()
                _finish_task(task_id, result=result)
            except Exception as exc:
                logger.error('[SYNC_FINANCIAL_BG] 任务异常, log_id=%s, error=%s', log.id, exc)
                logger.error(traceback.format_exc())
                try:
                    db_err = SessionLocal()
                    crud.system_error_log_crud.create(
                        db_err,
                        schemas.SystemErrorLogCreate(
                            level='error',
                            source='sync_financial_bg',
                            trace_id=str(log.id),
                            message=str(exc)[:1000],
                            detail=traceback.format_exc()[:4000],
                        )
                    )
                except Exception as exc:
                    logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc)
                finally:
                    db_err.close()
                crud.sync_job_log_crud.finish(
                    db2, log.id, 'failed', error_message=str(exc)[:2000]
                )
                db2.commit()
                _finish_task(task_id, error=str(exc))
            finally:
                db2.close()

        t = threading.Thread(target=_run_with_log, daemon=True)
        t.start()
        logger.info('[SYNC_FINANCIAL_API] 已提交后台任务, log_id=%s', log.id)
        return success({
            "task_id": task_id,
            "log_id": log.id,
            "status": "running",
            "hint": "财务指标同步任务已提交后台执行，约需 3-5 分钟，请稍后刷新页面查看",
        })
    except Exception as exc:
        logger.error('[SYNC_FINANCIAL_API] 提交任务失败: %s', exc)
        logger.error(traceback.format_exc())
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_financial_api',
                    trace_id=str(log.id),
                    message=str(exc)[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc)
        finally:
            db_err.close()
        crud.sync_job_log_crud.finish(db, log.id, 'failed', error_message=str(exc)[:2000])
        db.commit()
        raise


@router.get("/job-logs")
def get_sync_job_logs(
    days: int = Query(5, description="最近N天"),
    job_type: Optional[str] = Query(None, description="任务类型过滤"),
    page_num: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """查询同步任务执行日志（自动清理超时任务）"""
    _cleanup_db_timeout_tasks(db)
    query = schemas.SyncJobLogQuery(
        page_num=page_num,
        page_size=page_size,
        days=days,
        job_type=job_type,
    )
    list_data, total = crud.sync_job_log_crud.get_list(db, query)
    return success({
        "list": list_data,
        "total": total,
        "page_num": page_num,
        "page_size": page_size,
    })


@router.post("/job-log/{log_id}/cancel")
def post_cancel_job_log(
    log_id: int,
    db: Session = Depends(get_db),
):
    """取消/终止同步任务（将 running 状态标记为 failed）"""
    db_obj = crud.sync_job_log_crud.get_by_id(db, log_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="任务不存在")
    if db_obj.status != 'running':
        raise HTTPException(status_code=400, detail="任务未在运行中")
    crud.sync_job_log_crud.finish(
        db, log_id, 'failed',
        success_count=db_obj.success_count or 0,
        failed_count=db_obj.failed_count or 0,
        skipped_count=db_obj.skipped_count or 0,
        total_count=db_obj.total_count or 0,
        error_message='手动取消',
    )
    db.commit()
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='job_cancel',
            target_type='job',
            target_id=str(log_id),
            detail='手动取消同步任务',
            result='success',
        )
    )
    db.commit()
    return success({"log_id": log_id, "status": "cancelled"})


# 3.7.1 后台执行指标计算任务
def _run_sync_indicator_bg(task_id: str, trade_date: str, log_id: int, only_missing: bool = True) -> None:
    """后台执行日线指标计算任务（基于全A股股票列表，多线程版）"""
    db = SessionLocal()
    try:
        formatted_date = trade_date.replace("-", "")
        trade_date_obj = datetime.strptime(formatted_date, '%Y%m%d').date()

        # 验证交易日期是否存在
        exists = (
            db.query(models.StockDaily)
            .filter(models.StockDaily.trade_date == trade_date_obj)
            .first()
        )
        if not exists:
            msg = f"交易日期 {trade_date} 无数据"
            crud.sync_job_log_crud.finish(db, log_id, 'failed', error_message=msg)
            db.commit()
            _finish_task(task_id, error=msg)
            return

        # 只基于当天有日线数据的股票计算指标，避免用历史数据张冠李戴
        symbols = [
            row[0] for row in
            db.query(models.StockDaily.symbol).filter(
                models.StockDaily.trade_date == trade_date_obj
            ).distinct().all()
        ]

        if only_missing:
            existing = set(
                row[0] for row in db.query(models.StockDailyIndicator.symbol)
                .filter(models.StockDailyIndicator.trade_date == trade_date_obj)
                .all()
            )
            symbols = [s for s in symbols if s not in existing]

        total = len(symbols)

        if total == 0:
            crud.sync_job_log_crud.finish(
                db, log_id, 'success',
                success_count=0, failed_count=0, total_count=0,
                trade_date=formatted_date,
                extra_info=f'no symbols for {trade_date}',
            )
            db.commit()
            _finish_task(task_id, result={"trade_date": trade_date, "total": 0, "success": 0, "failed": 0})
            return

        _update_task_progress(task_id, 0, total)
        _items: List[dict] = []
        _success_count = 0
        _failed_count = 0

        # 批量预查询所有股票的历史数据，避免 N+1
        start_date_obj = trade_date_obj - timedelta(days=90)

        all_rows = (
            db.query(models.StockDaily)
            .filter(
                models.StockDaily.symbol.in_(symbols),
                models.StockDaily.trade_date >= start_date_obj,
                models.StockDaily.trade_date <= trade_date_obj,
            )
            .order_by(models.StockDaily.symbol, models.StockDaily.trade_date.desc())
            .options(load_only(
                models.StockDaily.symbol,
                models.StockDaily.trade_date,
                models.StockDaily.close,
                models.StockDaily.high,
                models.StockDaily.low,
                models.StockDaily.volume,
                models.StockDaily.amount,
                models.StockDaily.turnover,
            ))
            .all()
        )
        rows_by_symbol: dict[str, list] = {}
        for row in all_rows:
            symbol_rows = rows_by_symbol.setdefault(row.symbol, [])
            if len(symbol_rows) < 60:
                symbol_rows.append(row)

        for idx, symbol in enumerate(symbols):
            try:
                rows = rows_by_symbol.get(symbol, [])
                if not rows:
                    _failed_count += 1
                    continue

                indicator_data = _build_indicator_for_symbol(None, symbol, trade_date_obj, rows=rows)
                if indicator_data is None:
                    _failed_count += 1
                else:
                    indicator_data["symbol"] = symbol
                    indicator_data["trade_date"] = trade_date_obj
                    _items.append(indicator_data)
                    _success_count += 1

                if (idx + 1) % 50 == 0:
                    _update_task_progress(task_id, idx + 1, total)
                    # 每 50 只批量写入一次，避免内存堆积
                    if _items:
                        crud.stock_daily_indicator_crud.create_or_update_batch(db, _items)
                        db.commit()
                        _items = []
            except Exception as exc:
                logger.error('[SYNC_INDICATOR] 处理 %s 指标异常: %s', symbol, exc)
                _failed_count += 1

        if _items:
            crud.stock_daily_indicator_crud.create_or_update_batch(db, _items)
            db.commit()

        _update_task_progress(task_id, total, total)
        indicator_stats = _calc_indicator_stats(_items) if _items else {}
        crud.sync_job_log_crud.finish(
            db, log_id, 'success',
            success_count=_success_count,
            failed_count=_failed_count,
            total_count=total,
            trade_date=formatted_date,
            extra_info=f'indicators for {trade_date}, stats={indicator_stats}',
        )
        db.commit()
        _finish_task(task_id, result={
            "trade_date": trade_date,
            "total": total,
            "success": _success_count,
            "failed": _failed_count,
            "indicator_stats": indicator_stats,
        })
    except Exception as exc:
        logger.error('[SYNC_INDICATOR_BG] 任务异常, log_id=%s, error=%s', log_id, exc)
        logger.error(traceback.format_exc())
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_indicator_bg',
                    trace_id=str(log_id),
                    message=str(exc)[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc)
        finally:
            db_err.close()
        crud.sync_job_log_crud.finish(
            db, log_id, 'failed', error_message=str(exc)[:2000]
        )
        db.commit()
        _finish_task(task_id, error=str(exc))
    finally:
        db.close()


# 3.7.2 计算指定交易日指标（后台异步版）
@router.post("/indicator")
def post_sync_indicator(
    trade_date: str = Query(..., description="交易日期，格式 YYYY-MM-DD"),
    only_missing: bool = Query(True, description="仅计算缺失数据"),
    db: Session = Depends(get_db),
):
    """计算指定交易日所有主板的日线指标（后台异步版）"""
    log = crud.sync_job_log_crud.create(
        db, schemas.SyncJobLogCreate(job_type='indicator', trigger_type='manual', trade_date=trade_date.replace("-", ""))
    )
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='sync_manual',
            target_type='job',
            target_id=str(log.id),
            detail=f'手动触发指标计算，日期={trade_date}',
            result='success',
        )
    )
    db.commit()
    task_id = str(uuid.uuid4())
    _register_task(task_id, trade_date, job_type='indicator', log_id=log.id)
    t = threading.Thread(target=_run_sync_indicator_bg, args=(task_id, trade_date, log.id, only_missing), daemon=True)
    t.start()
    logger.info('[SYNC_INDICATOR_API] 已提交后台任务, log_id=%s, trade_date=%s, only_missing=%s', log.id, trade_date, only_missing)
    return success({
        "task_id": task_id,
        "log_id": log.id,
        "status": "running",
        "hint": "指标计算任务已提交后台执行，约需 1-3 分钟，请稍后刷新页面查看",
    })


# 3.10 查询详细同步状态
@router.get("/detailed-status")
def get_detailed_status(
    daily_page_num: int = Query(1, ge=1, description="交易日状态页码"),
    daily_page_size: int = Query(5, ge=1, le=30, description="每页交易日数量"),
    db: Session = Depends(get_db),
):
    """查询同步任务详细数据库状态"""
    from sqlalchemy import func

    # 1. 股票基本信息统计（排除北交所，数据源不支持）
    # 合并 COUNT：一次查询拿到 total / st_count / delisted_count
    basic_stats = db.query(
        func.count(models.StockBasic.id).label('total'),
        func.sum(func.if_(models.StockBasic.name.like('%ST%'), 1, 0)).label('st_count'),
        func.sum(func.if_(models.StockBasic.name.like('%退%'), 1, 0)).label('delisted_count'),
    ).filter(
        models.StockBasic.market != '北交所'
    ).first()
    total_basic = basic_stats.total or 0
    st_count = basic_stats.st_count or 0
    delisted_count = basic_stats.delisted_count or 0
    last_basic_sync = (
        db.query(
            models.SyncJobLog.started_at,
            models.SyncJobLog.success_count,
            models.SyncJobLog.total_count,
        )
        .filter(models.SyncJobLog.job_type == 'stock_basic')
        .order_by(models.SyncJobLog.started_at.desc())
        .first()
    )
    market_dist = (
        db.query(models.StockBasic.market, func.count(models.StockBasic.id))
        .filter(models.StockBasic.market != '北交所')
        .group_by(models.StockBasic.market)
        .all()
    )

    # 2. 交易日的日线/指标状态（从交易日历取，避免大表 DISTINCT）
    today = date.today()
    daily_total = (
        db.query(func.count(models.TradeCalendar.trade_date))
        .filter(
            models.TradeCalendar.is_trading_day == 1,
            models.TradeCalendar.trade_date <= today,
        )
        .scalar()
    ) or 0
    trade_dates = (
        db.query(models.TradeCalendar.trade_date)
        .filter(
            models.TradeCalendar.is_trading_day == 1,
            models.TradeCalendar.trade_date <= today,
        )
        .order_by(models.TradeCalendar.trade_date.desc())
        .offset((daily_page_num - 1) * daily_page_size)
        .limit(daily_page_size)
        .all()
    )
    if not trade_dates:
        trade_dates = []
    date_objs = [td for (td,) in trade_dates]
    date_strs = [td.strftime('%Y%m%d') for td in date_objs]
    oldest_date = min(date_objs) if date_objs else None

    # 批量获取日线/指标计数（用 date 对象过滤和匹配，trade_date 是 Date 类型）
    daily_counts = {
        r[0]: r[1]
        for r in db.query(models.StockDaily.trade_date, func.count(models.StockDaily.id))
        .filter(models.StockDaily.trade_date.in_(date_objs))
        .group_by(models.StockDaily.trade_date)
        .all()
    }
    indicator_counts = {
        r[0]: r[1]
        for r in db.query(models.StockDailyIndicator.trade_date, func.count(models.StockDailyIndicator.id))
        .filter(models.StockDailyIndicator.trade_date.in_(date_objs))
        .group_by(models.StockDailyIndicator.trade_date)
        .all()
    }

    # 批量获取最新日志（按日期取最新一条，合并 daily + indicator）
    # SyncJobLog.trade_date 是 String(8)，用 date_strs 过滤
    logs_raw = (
        db.query(
            models.SyncJobLog.id,
            models.SyncJobLog.trade_date,
            models.SyncJobLog.job_type,
            models.SyncJobLog.status,
            models.SyncJobLog.success_count,
            models.SyncJobLog.failed_count,
            models.SyncJobLog.total_count,
            models.SyncJobLog.started_at,
        )
        .filter(
            models.SyncJobLog.job_type.in_(['daily', 'indicator']),
            models.SyncJobLog.trade_date.in_(date_strs),
        )
        .order_by(models.SyncJobLog.trade_date, models.SyncJobLog.job_type, models.SyncJobLog.started_at.desc())
        .all()
    )
    daily_log_map: dict[str, tuple] = {}
    indicator_log_map: dict[str, tuple] = {}
    for row in logs_raw:
        log_id, ds, jt = row[0], row[1], row[2]
        if jt == 'daily' and ds not in daily_log_map:
            daily_log_map[ds] = (log_id, *row[3:])
        elif jt == 'indicator' and ds not in indicator_log_map:
            indicator_log_map[ds] = (log_id, *row[3:])

    # 一次性拉取有效股票和停牌记录，在 Python 中计算每日预期（避免 N+1 查询）
    all_basics = db.query(
        models.StockBasic.symbol,
        models.StockBasic.list_date
    ).filter(
        models.StockBasic.market != '北交所',
        models.StockBasic.list_date.isnot(None),
        ~models.StockBasic.name.like('%退%'),
    ).all()

    suspended_map: dict[str, set[str]] = {ds: set() for ds in date_strs}
    if oldest_date:
        all_suspensions = db.query(
            models.StockSuspension.symbol,
            models.StockSuspension.suspend_date,
            models.StockSuspension.resume_date
        ).filter(
            models.StockSuspension.suspend_date <= max(date_objs),
            or_(
                models.StockSuspension.resume_date.is_(None),
                models.StockSuspension.resume_date >= min(date_objs),
            ),
        ).all()
        for sym, s_date, r_date in all_suspensions:
            for td, ds in zip(date_objs, date_strs):
                if s_date <= td and (r_date is None or r_date > td):
                    suspended_map[ds].add(sym)

    basic_by_date: dict[str, set[str]] = {ds: set() for ds in date_strs}
    for sym, list_date in all_basics:
        if isinstance(list_date, str):
            list_date = date.fromisoformat(list_date)
        for td, ds in zip(date_objs, date_strs):
            if list_date <= td:
                basic_by_date[ds].add(sym)

    daily_status = []
    for td in date_objs:
        ds = td.strftime('%Y%m%d')
        expected = len(basic_by_date.get(ds, set()) - suspended_map.get(ds, set()))
        daily_cnt = daily_counts.get(td, 0)
        indicator_cnt = indicator_counts.get(td, 0)
        daily_log = daily_log_map.get(ds)
        indicator_log = indicator_log_map.get(ds)

        daily_status.append({
            'date': td.isoformat(),
            'total_stock_count': expected,
            'daily_count': daily_cnt,
            'indicator_count': indicator_cnt,
            'missing_daily': max(0, expected - daily_cnt),
            'missing_indicator': max(0, expected - indicator_cnt),
            'daily_log': {
                'log_id': daily_log[0],
                'status': daily_log[1],
                'success': daily_log[2],
                'failed': daily_log[3],
                'total': daily_log[4],
                'started_at': daily_log[5].isoformat() if daily_log[5] else None,
            } if daily_log else None,
            'indicator_log': {
                'log_id': indicator_log[0],
                'status': indicator_log[1],
                'success': indicator_log[2],
                'failed': indicator_log[3],
                'total': indicator_log[4],
                'started_at': indicator_log[5].isoformat() if indicator_log[5] else None,
            } if indicator_log else None,
        })

    # 3. 财报指标统计
    financial_total = db.query(func.count(models.StockFinancialIndicator.symbol)).scalar() or 0
    last_financial_sync = (
        db.query(models.SyncJobLog.started_at)
        .filter(models.SyncJobLog.job_type == 'financial')
        .order_by(models.SyncJobLog.started_at.desc())
        .first()
    )
    report_dist = (
        db.query(
            models.StockFinancialIndicator.report_date,
            func.count(models.StockFinancialIndicator.symbol),
        )
        .filter(models.StockFinancialIndicator.report_date.isnot(None))
        .group_by(models.StockFinancialIndicator.report_date)
        .order_by(models.StockFinancialIndicator.report_date.desc())
        .all()
    )

    # 3.5 日线指标覆盖度统计（取最新交易日）
    latest_indicator_date = db.query(func.max(models.StockDailyIndicator.trade_date)).scalar()
    indicator_stats = {}
    if latest_indicator_date:
        indicator_total = db.query(func.count(models.StockDailyIndicator.symbol)).filter(
            models.StockDailyIndicator.trade_date == latest_indicator_date
        ).scalar() or 0
        for field in INDICATOR_FIELDS:
            col = getattr(models.StockDailyIndicator, field)
            valid = db.query(func.count(models.StockDailyIndicator.id)).filter(
                models.StockDailyIndicator.trade_date == latest_indicator_date,
                col.isnot(None),
                col != -1,
            ).scalar() or 0
            indicator_stats[field] = {
                'total': indicator_total,
                'valid': valid,
                'missing': indicator_total - valid,
            }
    last_indicator_sync = (
        db.query(models.SyncJobLog.started_at)
        .filter(models.SyncJobLog.job_type == 'indicator')
        .order_by(models.SyncJobLog.started_at.desc())
        .first()
    )

    # 4. 板块/ETF统计
    board_category_counts = (
        db.query(
            models.BoardInfo.category,
            func.count(models.BoardInfo.code),
        )
        .group_by(models.BoardInfo.category)
        .all()
    )
    board_counts = {c: n for c, n in board_category_counts}
    last_board_list_sync = (
        db.query(
            models.SyncJobLog.started_at,
            models.SyncJobLog.success_count,
            models.SyncJobLog.total_count,
        )
        .filter(models.SyncJobLog.job_type == 'board_list')
        .order_by(models.SyncJobLog.started_at.desc())
        .first()
    )
    last_board_daily_sync = (
        db.query(models.SyncJobLog.started_at)
        .filter(models.SyncJobLog.job_type == 'board_daily')
        .order_by(models.SyncJobLog.started_at.desc())
        .first()
    )
    # 板块日线最新交易日
    latest_board_daily = (
        db.query(func.max(models.BoardDaily.trade_date))
        .scalar()
    )
    # 成分股总数
    constituent_total = (
        db.query(func.count(models.BoardConstituent.id))
        .scalar()
    ) or 0

    return success({
        'stock_basic': {
            'total': total_basic,
            'st_count': st_count,
            'delisted_count': delisted_count,
            'valid_count': total_basic - st_count - delisted_count,
            'last_sync': last_basic_sync[0].isoformat() if last_basic_sync else None,
            'total_count': (last_basic_sync[2] or 0) if last_basic_sync else 0,
            'success_count': (last_basic_sync[1] or 0) if last_basic_sync else 0,
            'market_distribution': {m: c for m, c in market_dist},
        },
        'daily': daily_status,
        'daily_total': daily_total,
        'daily_page_num': daily_page_num,
        'daily_page_size': daily_page_size,
        'financial': {
            'total': financial_total,
            'expected': total_basic,
            'missing': total_basic - financial_total,
            'last_sync': last_financial_sync[0].isoformat() if last_financial_sync else None,
            'report_distribution': [
                {'date': d.isoformat() if d else None, 'count': c}
                for d, c in report_dist
            ],
        },
        'indicator': {
            'latest_date': latest_indicator_date.isoformat() if latest_indicator_date else None,
            'last_sync': last_indicator_sync[0].isoformat() if last_indicator_sync else None,
            'field_stats': indicator_stats,
        },
        'board': {
            'total': sum(board_counts.values()),
            'industry_count': board_counts.get('industry', 0),
            'concept_count': board_counts.get('concept', 0),
            'etf_count': board_counts.get('etf', 0),
            'last_sync': last_board_daily_sync[0].isoformat() if last_board_daily_sync else None,
            'last_list_sync': last_board_list_sync[0].isoformat() if last_board_list_sync else None,
            'total_count': (last_board_list_sync[2] or 0) if last_board_list_sync else 0,
            'success_count': (last_board_list_sync[1] or 0) if last_board_list_sync else 0,
            'latest_daily_date': latest_board_daily.isoformat() if latest_board_daily else None,
            'constituent_count': constituent_total,
        },
    })


# ==================== 4. 指数数据同步 ====================

INDEX_CONFIG = {
    'sh.000001': '上证指数',
    'sz.399001': '深证成指',
    'sz.399006': '创业板指',
    'sh.000300': '沪深300',
    'sh.000016': '上证50',
    'sh.000905': '中证500',
}


def _sync_index_daily(trade_date: str) -> dict:
    """同步指定交易日的主要指数日线数据（baostock）"""
    from datetime import date as _date

    start = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}" if len(trade_date) == 8 else trade_date
    end = start
    trade_date_obj = datetime.strptime(start, "%Y-%m-%d").date()

    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"Baostock login failed: {lg.error_msg}")

    fields = 'date,code,open,high,low,close,preclose,volume,amount,pctChg'
    results: List[dict] = []
    failed: List[str] = []

    try:
        for code, name in INDEX_CONFIG.items():
            rs = bs.query_history_k_data_plus(
                code, fields, start_date=start, end_date=end,
                frequency='d', adjustflag='3'
            )
            if rs.error_code == '0' and rs.next():
                row = rs.get_row_data()
                results.append({
                    'symbol': code,
                    'name': name,
                    'trade_date': trade_date_obj,
                    'open': float(row[2]) if row[2] else None,
                    'high': float(row[3]) if row[3] else None,
                    'low': float(row[4]) if row[4] else None,
                    'close': float(row[5]) if row[5] else None,
                    'preclose': float(row[6]) if row[6] else None,
                    'volume': float(row[7]) if row[7] else None,
                    'amount': float(row[8]) if row[8] else None,
                    'pct_chg': float(row[9]) if row[9] else None,
                })
            else:
                failed.append(code)
            time.sleep(0.5)
    finally:
        bs.logout()

    if results:
        db = SessionLocal()
        try:
            upsert_stmt = insert(models.IndexDaily).values(results)
            update_dict = {
                k: upsert_stmt.inserted[k]
                for k in upsert_stmt.inserted.keys()
                if k not in ("id", "trade_date", "symbol")
            }
            upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
            db.execute(upsert_stmt)
            db.commit()
        except Exception as exc:
            logger.error('[SYNC_INDEX_DAILY] 批量写入失败: %s', exc)
            try:
                db_err = SessionLocal()
                crud.system_error_log_crud.create(
                    db_err,
                    schemas.SystemErrorLogCreate(
                        level='error',
                        source='sync_index_daily',
                        trace_id=None,
                        message=str(exc)[:1000],
                        detail=traceback.format_exc()[:4000],
                    )
                )
                db_err.commit()
            except Exception as exc:
                logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc)
            finally:
                db_err.close()
            db.rollback()
        finally:
            db.close()

    return {
        "trade_date": start,
        "total": len(INDEX_CONFIG),
        "success": len(results),
        "failed": len(failed),
        "failed_codes": failed,
    }


def _sync_index_constituents(index_symbol: str) -> dict:
    """同步指定指数的成分股列表（baostock）"""
    func_map = {
        'sh.000300': bs.query_hs300_stocks,
        'sh.000016': bs.query_sz50_stocks,
        'sh.000905': bs.query_zz500_stocks,
    }
    query_func = func_map.get(index_symbol)
    if not query_func:
        raise ValueError(f"不支持的指数代码: {index_symbol}")

    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"Baostock login failed: {lg.error_msg}")

    results: List[dict] = []
    update_date = datetime.now().date()

    try:
        rs = query_func()
        if rs.error_code == '0':
            while rs.next():
                row = rs.get_row_data()
                # row format: ['updateDate', 'code', 'code_name']
                code = row[1] if len(row) > 1 else None
                if code:
                    # code is like 'sh.600519', extract 600519
                    constituent = code.split('.')[-1] if '.' in code else code
                    results.append({
                        'index_symbol': index_symbol,
                        'constituent_symbol': constituent,
                        'update_date': update_date,
                    })
                    if row[0] and not update_date:
                        update_date = datetime.strptime(row[0], "%Y-%m-%d").date()
        else:
            raise RuntimeError(f"查询成分股失败: {rs.error_msg}")
    finally:
        bs.logout()

    if results:
        db = SessionLocal()
        try:
            # 先清空旧数据再写入
            db.query(models.IndexConstituent).filter(
                models.IndexConstituent.index_symbol == index_symbol
            ).delete(synchronize_session=False)
            db.bulk_insert_mappings(models.IndexConstituent, results)
            db.commit()
        except Exception as exc:
            logger.error('[SYNC_INDEX_CONSTITUENTS] 写入失败: %s', exc)
            try:
                db_err = SessionLocal()
                crud.system_error_log_crud.create(
                    db_err,
                    schemas.SystemErrorLogCreate(
                        level='error',
                        source='sync_index_constituents',
                        trace_id=None,
                        message=str(exc)[:1000],
                        detail=traceback.format_exc()[:4000],
                    )
                )
                db_err.commit()
            except Exception as exc:
                logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc)
            finally:
                db_err.close()
            db.rollback()
        finally:
            db.close()

    return {
        "index_symbol": index_symbol,
        "count": len(results),
        "update_date": update_date.isoformat(),
    }


# ==================== 板块/ETF数据同步 ====================


def _sync_board_list_em(db: Session) -> dict:
    """从东方财富同步行业/概念板块列表"""
    import akshare as ak

    records = []
    industry_count = 0
    concept_count = 0

    try:
        with akshare_lock:
            df_industry = ak.stock_board_industry_name_em()
        for _, row in df_industry.iterrows():
            records.append(schemas.BoardInfoCreate(
                code=str(row['板块代码']).strip(),
                name=str(row['板块名称']).strip(),
                category='industry',
                source='em',
            ))
        industry_count = len(df_industry)
    except Exception as exc:
        logger.warning('[SYNC_BOARD_LIST] 获取东方财富行业板块失败: %s', exc)

    try:
        with akshare_lock:
            df_concept = ak.stock_board_concept_name_em()
        for _, row in df_concept.iterrows():
            records.append(schemas.BoardInfoCreate(
                code=str(row['板块代码']).strip(),
                name=str(row['板块名称']).strip(),
                category='concept',
                source='em',
            ))
        concept_count = len(df_concept)
    except Exception as exc:
        logger.warning('[SYNC_BOARD_LIST] 获取东方财富概念板块失败: %s', exc)

    result = crud.board_info_crud.upsert_batch(db, records)
    return {
        'total': len(records),
        'industry_count': industry_count,
        'concept_count': concept_count,
        'created': result['created'],
        'updated': result['updated'],
    }


def _sync_etf_list_sina(db: Session) -> dict:
    """从新浪同步ETF列表"""
    import akshare as ak

    try:
        with akshare_lock:
            df = ak.fund_etf_category_sina(symbol='ETF基金')
    except Exception as exc:
        logger.warning('[SYNC_ETF_LIST] 获取新浪ETF列表失败: %s', exc)
        return {'total': 0, 'created': 0, 'updated': 0}

    records = []
    for _, row in df.iterrows():
        raw_code = str(row.get('代码', '')).strip()
        if not raw_code:
            continue
        # 提取纯数字代码，如 sz159998 -> 159998
        symbol = raw_code.replace('sh', '').replace('sz', '').replace('bj', '')
        name = str(row.get('名称', '')).strip()
        exchange = 'SH' if raw_code.startswith('sh') else ('SZ' if raw_code.startswith('sz') else 'BJ')
        records.append(schemas.BoardInfoCreate(
            code=symbol,
            name=name,
            category='etf',
            exchange=exchange,
            source='sina',
        ))

    result = crud.board_info_crud.upsert_batch(db, records)
    return {
        'total': len(records),
        'created': result['created'],
        'updated': result['updated'],
    }


def _parse_board_daily_em(df, board_code: str) -> List[dict]:
    """解析东方财富板块日线 DataFrame 为记录列表（自带涨跌幅）"""
    if df is None or df.empty:
        return []

    records = []
    for _, row in df.iterrows():
        trade_date = str(row['日期']).strip()
        close = float(row['收盘']) if pd.notna(row['收盘']) else None
        open_price = float(row['开盘']) if pd.notna(row['开盘']) else None
        high = float(row['最高']) if pd.notna(row['最高']) else None
        low = float(row['最低']) if pd.notna(row['最低']) else None
        volume = float(row['成交量']) if pd.notna(row['成交量']) else None
        amount = float(row['成交额']) if pd.notna(row['成交额']) else None
        pct_chg = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None

        records.append({
            'code': board_code,
            'trade_date': trade_date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'amount': amount,
            'pct_chg': pct_chg,
        })

    return records


def _sync_board_daily_em(
    task_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    only_industry: bool = False,
    only_concept: bool = False,
) -> dict:
    """同步板块日线（东方财富源，多线程版）"""
    import akshare as ak

    db = SessionLocal()
    try:
        boards = db.query(models.BoardInfo)
        if only_industry:
            boards = boards.filter(models.BoardInfo.category == 'industry')
        elif only_concept:
            boards = boards.filter(models.BoardInfo.category == 'concept')
        else:
            boards = boards.filter(models.BoardInfo.category.in_(['industry', 'concept']))
        boards = boards.all()
    finally:
        db.close()

    if not boards:
        return {'total_boards': 0, 'success': 0, 'failed': 0, 'records': 0}

    em_start = start_date or '20000101'
    em_end = end_date or '20500101'

    _counter = [0]
    _success = [0]
    _failed = [0]
    _records_total = [0]
    _lock = threading.Lock()
    _results: List[dict] = []

    def _process_board(board):
        try:
            if board.category == 'industry':
                with akshare_lock:
                    df = ak.stock_board_industry_hist_em(
                        symbol=board.code,
                        start_date=em_start,
                        end_date=em_end,
                        period='日k',
                        adjust='',
                    )
            else:
                with akshare_lock:
                    df = ak.stock_board_concept_hist_em(
                        symbol=board.code,
                        period='daily',
                        start_date=em_start,
                        end_date=em_end,
                        adjust='',
                    )

            records = _parse_board_daily_em(df, board.code)

            # 日期过滤
            if start_date or end_date:
                filtered = []
                for r in records:
                    if start_date and r['trade_date'] < start_date:
                        continue
                    if end_date and r['trade_date'] > end_date:
                        continue
                    filtered.append(r)
                records = filtered

            with _lock:
                _results.extend(records)
                _success[0] += 1
                _records_total[0] += len(records)
                if len(_results) >= 500:
                    batch = _results[:]
                    _results.clear()
                    db_write = SessionLocal()
                    try:
                        crud.board_daily_crud.upsert_batch(db_write, batch)
                        db_write.commit()
                    finally:
                        db_write.close()
        except Exception as exc:
            logger.warning('[SYNC_BOARD_DAILY] %s(%s) 失败: %s', board.name, board.code, exc)
            with _lock:
                _failed[0] += 1
        finally:
            with _lock:
                _counter[0] += 1
                current = _counter[0]
                if task_id and current % 10 == 0:
                    _update_task_progress(task_id, current, len(boards))

    workers = 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_process_board, b) for b in boards]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result(timeout=60)
            except concurrent.futures.TimeoutError:
                logger.error('[SYNC_BOARD_DAILY] 单板块处理超时(60s)')
            except Exception as exc:
                logger.error('[SYNC_BOARD_DAILY] 处理板块异常: %s', exc)

    # 写入剩余数据
    with _lock:
        if _results:
            batch = _results[:]
            _results.clear()
            db_write = SessionLocal()
            try:
                crud.board_daily_crud.upsert_batch(db_write, batch)
            finally:
                db_write.close()

    return {
        'total_boards': len(boards),
        'success': _success[0],
        'failed': _failed[0],
        'records': _records_total[0],
    }


def _sync_etf_daily_em(
    task_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """同步ETF日线（东方财富源，多线程版）"""
    import akshare as ak

    db = SessionLocal()
    try:
        etfs = db.query(models.BoardInfo).filter(models.BoardInfo.category == 'etf').all()
    finally:
        db.close()

    if not etfs:
        return {'total_etfs': 0, 'success': 0, 'failed': 0, 'records': 0}

    _counter = [0]
    _success = [0]
    _failed = [0]
    _records_total = [0]
    _lock = threading.Lock()
    _results: List[dict] = []

    def _process_etf(etf):
        try:
            with akshare_lock:
                df = ak.fund_etf_hist_em(symbol=etf.code, period='daily', start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                with _lock:
                    _success[0] += 1
                return

            records = []
            prev_close = None
            for _, row in df.iterrows():
                trade_date = str(row['日期']).strip()
                close = float(row['收盘']) if pd.notna(row['收盘']) else None
                open_price = float(row['开盘']) if pd.notna(row['开盘']) else None
                high = float(row['最高']) if pd.notna(row['最高']) else None
                low = float(row['最低']) if pd.notna(row['最低']) else None
                volume = float(row['成交量']) if pd.notna(row['成交量']) else None
                amount = float(row['成交额']) if pd.notna(row['成交额']) else None
                pct_chg = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None

                records.append({
                    'code': etf.code,
                    'trade_date': trade_date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume,
                    'amount': amount,
                    'pct_chg': pct_chg,
                })
                if close is not None:
                    prev_close = close

            with _lock:
                _results.extend(records)
                _success[0] += 1
                _records_total[0] += len(records)
                if len(_results) >= 500:
                    batch = _results[:]
                    _results.clear()
                    db_write = SessionLocal()
                    try:
                        crud.board_daily_crud.upsert_batch(db_write, batch)
                        db_write.commit()
                    finally:
                        db_write.close()
        except Exception as exc:
            logger.warning('[SYNC_ETF_DAILY] %s(%s) 失败: %s', etf.name, etf.code, exc)
            with _lock:
                _failed[0] += 1
        finally:
            with _lock:
                _counter[0] += 1
                current = _counter[0]
                if task_id and current % 50 == 0:
                    _update_task_progress(task_id, current, len(etfs))

    workers = 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_process_etf, e) for e in etfs]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                logger.error('[SYNC_ETF_DAILY] 单ETF处理超时(30s)')
            except Exception as exc:
                logger.error('[SYNC_ETF_DAILY] 处理ETF异常: %s', exc)

    with _lock:
        if _results:
            batch = _results[:]
            _results.clear()
            db_write = SessionLocal()
            try:
                crud.board_daily_crud.upsert_batch(db_write, batch)
            finally:
                db_write.close()

    return {
        'total_etfs': len(etfs),
        'success': _success[0],
        'failed': _failed[0],
        'records': _records_total[0],
    }


def _sync_board_constituent_em(task_id: str | None = None) -> dict:
    """同步板块成分股（东方财富源），失败时 fallback 到 stock_basic.industry 聚合"""
    import akshare as ak

    db = SessionLocal()
    try:
        boards = db.query(models.BoardInfo).filter(
            models.BoardInfo.category.in_(['industry', 'concept'])
        ).all()
    finally:
        db.close()

    _counter = [0]
    _success = [0]
    _failed = [0]
    _lock = threading.Lock()

    def _process_board(board):
        records = []
        try:
            if board.category == 'industry':
                with akshare_lock:
                    df = ak.stock_board_industry_cons_em(symbol=board.name)
            else:
                with akshare_lock:
                    df = ak.stock_board_concept_cons_em(symbol=board.name)

            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    symbol = str(row.get('代码', '')).strip().zfill(6)
                    name = str(row.get('名称', '')).strip()
                    if symbol.isdigit():
                        records.append({
                            'board_code': board.code,
                            'constituent_symbol': symbol,
                            'name': name or None,
                            'update_date': datetime.now().date(),
                        })
        except Exception as exc:
            # 东方财富源失败，网络可能不通或接口变更
            logger.debug('[SYNC] 板块 %s 成分股同步失败: %s', board.code, exc)

        with _lock:
            if records:
                db_write = SessionLocal()
                try:
                    # 先清空再写入
                    crud.board_constituent_crud.delete_by_board(db_write, board.code)
                    for r in records:
                        crud.board_constituent_crud.upsert_batch(db_write, [
                            schemas.BoardConstituentCreate(**r)
                        ])
                    db_write.commit()
                    _success[0] += 1
                except Exception as exc:
                    logger.warning('[SYNC_CONSTITUENT] %s 写入失败: %s', board.code, exc)
                    _failed[0] += 1
                finally:
                    db_write.close()
            else:
                _failed[0] += 1

            _counter[0] += 1
            current = _counter[0]
            if task_id and current % 10 == 0:
                _update_task_progress(task_id, current, len(boards))

    workers = 2  # 东方财富源限流较严，用较少线程
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_process_board, b) for b in boards]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                logger.error('[SYNC_CONSTITUENT] 单板块处理超时(30s)')
            except Exception as exc:
                logger.error('[SYNC_CONSTITUENT] 处理板块异常: %s', exc)

    # EM 接口自带成分股数据，无需兜底
    return {
        'total_boards': len(boards),
        'success': _success[0],
        'failed': _failed[0],
    }


def _run_sync_board_list_bg(task_id: str, log_id: int) -> None:
    """后台执行板块/ETF列表同步"""
    db = SessionLocal()
    try:
        board_result = _sync_board_list_em(db)
        etf_result = _sync_etf_list_sina(db)
        total = board_result.get('total', 0) + etf_result.get('total', 0)
        created = board_result.get('created', 0) + etf_result.get('created', 0)
        updated = board_result.get('updated', 0) + etf_result.get('updated', 0)
        crud.sync_job_log_crud.finish(
            db, log_id, 'success',
            success_count=created + updated,
            total_count=total,
            extra_info=f'boards={board_result}, etfs={etf_result}',
        )
        db.commit()
        _finish_task(task_id, result={
            'boards': board_result,
            'etfs': etf_result,
            'summary': f"板块列表同步完成，行业 {board_result.get('industry_count', 0)} 个，概念 {board_result.get('concept_count', 0)} 个，ETF {etf_result.get('total', 0)} 个",
        })
    except Exception as exc:
        logger.error('[SYNC_BOARD_LIST_BG] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        crud.sync_job_log_crud.finish(db, log_id, 'failed', error_message=str(exc)[:2000])
        db.commit()
        _finish_task(task_id, error=str(exc))
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_board_list_bg',
                    trace_id=str(log_id),
                    message=f'板块列表同步任务异常: {exc}'[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc2:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc2)
        finally:
            db_err.close()
    finally:
        db.close()


def _run_sync_board_daily_bg(
    task_id: str,
    log_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """后台执行板块/ETF日线同步"""
    db = SessionLocal()
    try:
        board_result = _sync_board_daily_em(task_id=task_id, start_date=start_date, end_date=end_date)
        etf_result = _sync_etf_daily_em(task_id=task_id, start_date=start_date, end_date=end_date)
        total_records = board_result.get('records', 0) + etf_result.get('records', 0)
        crud.sync_job_log_crud.finish(
            db, log_id, 'success',
            success_count=total_records,
            total_count=board_result.get('total_boards', 0) + etf_result.get('total_etfs', 0),
            extra_info=f'board_records={board_result.get("records",0)}, etf_records={etf_result.get("records",0)}',
        )
        db.commit()
        _finish_task(task_id, result={
            'boards': board_result,
            'etfs': etf_result,
            'summary': f"日线同步完成，板块记录 {board_result.get('records', 0)} 条，ETF记录 {etf_result.get('records', 0)} 条",
        })
    except Exception as exc:
        logger.error('[SYNC_BOARD_DAILY_BG] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        crud.sync_job_log_crud.finish(db, log_id, 'failed', error_message=str(exc)[:2000])
        db.commit()
        _finish_task(task_id, error=str(exc))
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_board_daily_bg',
                    trace_id=str(log_id),
                    message=f'板块日线同步任务异常: {exc}'[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc2:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc2)
        finally:
            db_err.close()
    finally:
        db.close()


def _run_sync_board_constituent_bg(task_id: str, log_id: int) -> None:
    """后台执行板块成分股同步"""
    db = SessionLocal()
    try:
        result = _sync_board_constituent_em(task_id=task_id)
        crud.sync_job_log_crud.finish(
            db, log_id, 'success',
            success_count=result.get('success', 0),
            total_count=result.get('total_boards', 0),
            extra_info=f'fallback={result.get("industry_fallback", {})}',
        )
        db.commit()
        _finish_task(task_id, result=result)
    except Exception as exc:
        logger.error('[SYNC_BOARD_CONSTITUENT_BG] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        crud.sync_job_log_crud.finish(db, log_id, 'failed', error_message=str(exc)[:2000])
        db.commit()
        _finish_task(task_id, error=str(exc))
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_board_constituent_bg',
                    trace_id=str(log_id),
                    message=f'板块成分股同步任务异常: {exc}'[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc2:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc2)
        finally:
            db_err.close()
    finally:
        db.close()


# ==================== 5. 同步任务链（Pipeline）====================


def _run_sync_index_daily_bg(task_id: str, trade_date: str, log_id: int) -> None:
    """后台执行指数日线同步任务"""
    db = SessionLocal()
    try:
        result = _sync_index_daily(trade_date.replace("-", ""))
        crud.sync_job_log_crud.finish(
            db, log_id, 'success',
            success_count=result.get('success', 0),
            total_count=result.get('total', 0),
            trade_date=trade_date.replace("-", ""),
            extra_info=f"index_daily for {trade_date}",
        )
        db.commit()
        _finish_task(task_id, result=result)
    except Exception as exc:
        logger.error('[SYNC_INDEX_DAILY_BG] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        crud.sync_job_log_crud.finish(db, log_id, 'failed', error_message=str(exc)[:2000])
        db.commit()
        _finish_task(task_id, error=str(exc))
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_index_daily_bg',
                    trace_id=str(log_id),
                    message=f'指数日线同步任务异常: {exc}'[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc2:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc2)
        finally:
            db_err.close()
    finally:
        db.close()


def _run_sync_index_constituents_bg(task_id: str, index_code: str, log_id: int) -> None:
    """后台执行指数成分股同步任务"""
    db = SessionLocal()
    try:
        result = _sync_index_constituents(index_code)
        crud.sync_job_log_crud.finish(
            db, log_id, 'success',
            success_count=result.get('count', 0),
            total_count=result.get('count', 0),
            extra_info=f"index={index_code}",
        )
        db.commit()
        _finish_task(task_id, result=result)
    except Exception as exc:
        logger.error('[SYNC_INDEX_CONSTITUENTS_BG] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        crud.sync_job_log_crud.finish(db, log_id, 'failed', error_message=str(exc)[:2000])
        db.commit()
        _finish_task(task_id, error=str(exc))
        try:
            db_err = SessionLocal()
            crud.system_error_log_crud.create(
                db_err,
                schemas.SystemErrorLogCreate(
                    level='error',
                    source='sync_index_constituents_bg',
                    trace_id=str(log_id),
                    message=f'指数成分股同步任务异常: {exc}'[:1000],
                    detail=traceback.format_exc()[:4000],
                )
            )
            db_err.commit()
        except Exception as exc2:
            logger.warning('[SYNC] 写入 system_error_log 失败: %s', exc2)
        finally:
            db_err.close()
    finally:
        db.close()


# 预设任务链定义
CHAIN_DEFINITIONS: dict[str, list[dict]] = {
    "daily": [
        {"name": "股票基础信息", "job_type": "stock_basic", "skip_on_fail": False},
        {"name": "日线数据", "job_type": "daily", "skip_on_fail": False},
        {"name": "指标计算", "job_type": "indicator", "skip_on_fail": False},
    ],
    "full": [
        {"name": "股票基础信息", "job_type": "stock_basic", "skip_on_fail": False},
        {"name": "日线数据", "job_type": "daily", "skip_on_fail": False},
        {"name": "指标计算", "job_type": "indicator", "skip_on_fail": False},
        {"name": "财务指标", "job_type": "financial", "skip_on_fail": True},
        {"name": "板块/ETF列表", "job_type": "board_list", "skip_on_fail": False},
        {"name": "板块/ETF日线", "job_type": "board_daily", "skip_on_fail": True},
        {"name": "板块成分股", "job_type": "board_constituent", "skip_on_fail": True},
        {"name": "指数日线", "job_type": "index_daily", "skip_on_fail": True},
        {"name": "指数成分股", "job_type": "index_constituents", "skip_on_fail": True},
    ],
    "board": [
        {"name": "板块/ETF列表", "job_type": "board_list", "skip_on_fail": False},
        {"name": "板块/ETF日线", "job_type": "board_daily", "skip_on_fail": True},
        {"name": "板块成分股", "job_type": "board_constituent", "skip_on_fail": True},
    ],
}


def _resolve_trade_date(db: Session, trade_date: str | None) -> str:
    """解析交易日：如果未提供，取数据库最新交易日，否则今天"""
    if trade_date:
        return trade_date.replace("-", "")
    dates = crud.stock_daily_crud.get_trade_dates(db)
    if dates:
        return dates[0].strftime("%Y%m%d")
    return datetime.today().strftime("%Y%m%d")


def _launch_single_task(db: Session, job_type: str, trade_date: str | None) -> tuple[str, int]:
    """启动单个后台任务，返回 (task_id, log_id)"""
    task_id = str(uuid.uuid4())

    if job_type == "stock_basic":
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='stock_basic', trigger_type='manual')
        )
        _register_task(task_id, "stock_basic", job_type='stock_basic', log_id=log.id)
        t = threading.Thread(target=_run_sync_stock_basic_bg, args=(task_id, log.id), daemon=True)
        t.start()
    elif job_type == "daily":
        formatted = trade_date or datetime.today().strftime("%Y%m%d")
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='daily', trigger_type='manual', trade_date=formatted)
        )
        _register_task(task_id, formatted, job_type='daily', log_id=log.id)
        t = threading.Thread(target=_run_sync_bg, args=(task_id, formatted, log.id, False), daemon=True)
        t.start()
    elif job_type == "indicator":
        date_fmt = trade_date or datetime.today().strftime("%Y-%m-%d")
        formatted = date_fmt.replace("-", "")
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='indicator', trigger_type='manual', trade_date=formatted)
        )
        _register_task(task_id, date_fmt, job_type='indicator', log_id=log.id)
        t = threading.Thread(target=_run_sync_indicator_bg, args=(task_id, date_fmt, log.id, True), daemon=True)
        t.start()
    elif job_type == "financial":
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='financial', trigger_type='manual')
        )
        _register_task(task_id, "financial", job_type='financial', log_id=log.id)
        def _run_with_log():
            db2 = SessionLocal()
            try:
                result = _sync_financial_bulk(only_missing=False)
                crud.sync_job_log_crud.finish(
                    db2, log.id, 'success',
                    success_count=result.get('upserted', 0),
                    failed_count=result.get('failed', 0),
                    total_count=result.get('total_stocks', 0),
                    extra_info='source=akshare_ths',
                )
                db2.commit()
                _finish_task(task_id, result=result)
            except Exception as exc:
                logger.error('[SYNC_FINANCIAL_BG] 任务异常, log_id=%s, error=%s', log.id, exc)
                logger.error(traceback.format_exc())
                crud.sync_job_log_crud.finish(
                    db2, log.id, 'failed', error_message=str(exc)[:2000]
                )
                db2.commit()
                _finish_task(task_id, error=str(exc))
            finally:
                db2.close()
        t = threading.Thread(target=_run_with_log, daemon=True)
        t.start()
    elif job_type == "board_list":
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='board_list', trigger_type='manual')
        )
        _register_task(task_id, "board_list", job_type='board_list', log_id=log.id)
        t = threading.Thread(target=_run_sync_board_list_bg, args=(task_id, log.id), daemon=True)
        t.start()
    elif job_type == "board_daily":
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='board_daily', trigger_type='manual')
        )
        _register_task(task_id, "board_daily", job_type='board_daily', log_id=log.id)
        t = threading.Thread(
            target=_run_sync_board_daily_bg,
            args=(task_id, log.id, None, None),
            daemon=True,
        )
        t.start()
    elif job_type == "board_constituent":
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='board_constituent', trigger_type='manual')
        )
        _register_task(task_id, "board_constituent", job_type='board_constituent', log_id=log.id)
        t = threading.Thread(target=_run_sync_board_constituent_bg, args=(task_id, log.id), daemon=True)
        t.start()
    elif job_type == "index_daily":
        date_fmt = trade_date or datetime.today().strftime("%Y-%m-%d")
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='index_daily', trigger_type='manual', trade_date=date_fmt.replace("-", ""))
        )
        _register_task(task_id, date_fmt, job_type='index_daily', log_id=log.id)
        t = threading.Thread(target=_run_sync_index_daily_bg, args=(task_id, date_fmt, log.id), daemon=True)
        t.start()
    elif job_type == "index_constituents":
        log = crud.sync_job_log_crud.create(
            db, schemas.SyncJobLogCreate(job_type='index_constituents', trigger_type='manual')
        )
        _register_task(task_id, "index_constituents", job_type='index_constituents', log_id=log.id)
        t = threading.Thread(target=_run_sync_index_constituents_bg, args=(task_id, "sh.000300", log.id), daemon=True)
        t.start()
    else:
        raise ValueError(f"Unknown job_type: {job_type}")

    return task_id, log.id


def _wait_for_task(task_id: str, timeout_seconds: float = 3600, poll_interval: float = 2.0) -> dict:
    """等待单个后台任务完成，返回最终状态"""
    start = time.time()
    while True:
        with _task_lock:
            task = _task_registry.get(task_id)
        if not task:
            return {"status": "failed", "error": "任务不存在"}
        if task["status"] in ("success", "failed"):
            return task
        if time.time() - start > timeout_seconds:
            return {"status": "failed", "error": f"等待超时（{timeout_seconds}秒）"}
        time.sleep(poll_interval)


def _run_pipeline_bg(pipeline_id: str, steps: list[dict], trade_date: str | None) -> None:
    """后台执行任务链：顺序执行每一步，等待完成后再执行下一步"""
    db = SessionLocal()
    try:
        resolved_date = _resolve_trade_date(db, trade_date)
    except (ValueError, SQLAlchemyError) as exc:
        logger.warning('[SYNC] 解析交易日期失败，使用当天: %s', exc)
        resolved_date = datetime.today().strftime("%Y%m%d")
    finally:
        db.close()

    for i, step in enumerate(steps):
        job_type = step["job_type"]
        skip_on_fail = step.get("skip_on_fail", False)

        _update_pipeline_step(
            pipeline_id, i,
            status="running",
            started_at=datetime.now().isoformat(),
        )

        db2 = SessionLocal()
        try:
            step_trade_date = resolved_date if job_type in ("daily", "indicator") else (
                trade_date if job_type == "index_daily" else None
            )
            task_id, log_id = _launch_single_task(db2, job_type, step_trade_date)
            _update_pipeline_step(pipeline_id, i, task_id=task_id, log_id=log_id)
        except Exception as exc:
            logger.error('[PIPELINE] 启动步骤 %s 失败: %s', job_type, exc)
            _update_pipeline_step(
                pipeline_id, i,
                status="failed",
                error=str(exc),
                finished_at=datetime.now().isoformat(),
            )
            if not skip_on_fail:
                _finish_pipeline(pipeline_id, "failed", error=f"步骤 {step['name']} 启动失败: {exc}")
                return
            continue
        finally:
            db2.close()

        # 等待任务完成
        task_result = _wait_for_task(task_id)

        if task_result["status"] == "success":
            _update_pipeline_step(
                pipeline_id, i,
                status="success",
                result=task_result.get("result"),
                finished_at=datetime.now().isoformat(),
            )
        else:
            error_msg = task_result.get("error", "未知错误")
            _update_pipeline_step(
                pipeline_id, i,
                status="failed",
                error=error_msg,
                finished_at=datetime.now().isoformat(),
            )
            if not skip_on_fail:
                _finish_pipeline(
                    pipeline_id, "failed",
                    error=f"步骤 {step['name']} 失败: {error_msg}"
                )
                return

    _finish_pipeline(pipeline_id, "success")


@router.post("/pipeline")
def post_sync_pipeline(
    body: schemas.PipelineCreate,
    db: Session = Depends(get_db),
):
    """创建并启动同步任务链（Pipeline）"""
    chain_type = body.chain_type
    trade_date = body.trade_date

    if body.steps:
        steps = [s.model_dump() for s in body.steps]
    elif chain_type in CHAIN_DEFINITIONS:
        steps = [dict(s) for s in CHAIN_DEFINITIONS[chain_type]]
    else:
        raise HTTPException(status_code=400, detail=f"未知的任务链类型: {chain_type}")

    pipeline_id = str(uuid.uuid4())
    _register_pipeline(pipeline_id, chain_type, trade_date, steps)

    t = threading.Thread(
        target=_run_pipeline_bg,
        args=(pipeline_id, steps, trade_date),
        daemon=True,
    )
    t.start()
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='pipeline_start',
            target_type='pipeline',
            target_id=pipeline_id,
            detail=f'启动任务链，类型={chain_type}, 交易日={trade_date}',
            result='success',
        )
    )
    db.commit()
    logger.info('[PIPELINE_API] 已启动任务链, pipeline_id=%s, chain_type=%s', pipeline_id, chain_type)

    with _pipeline_lock:
        pipeline = _pipeline_registry[pipeline_id]

    return success({
        "pipeline_id": pipeline_id,
        "chain_type": chain_type,
        "status": "running",
        "trade_date": trade_date,
        "steps": pipeline["steps"],
        "started_at": pipeline["started_at"],
    })


@router.get("/pipeline/{pipeline_id}")
def get_sync_pipeline(pipeline_id: str):
    """查询任务链状态"""
    _cleanup_timeout_pipelines()
    with _pipeline_lock:
        pipeline = _pipeline_registry.get(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="任务链不存在")
    return success(pipeline)


@router.get("/pipelines")
def get_sync_pipelines():
    """查询所有活跃/近期任务链"""
    _cleanup_timeout_pipelines()
    with _pipeline_lock:
        pipelines = [
            {
                "pipeline_id": p["pipeline_id"],
                "chain_type": p["chain_type"],
                "status": p["status"],
                "started_at": p["started_at"],
                "finished_at": p.get("finished_at"),
                "step_summary": [
                    {"name": s["name"], "status": s["status"]} for s in p["steps"]
                ],
            }
            for p in _pipeline_registry.values()
        ]
    return success({"pipelines": pipelines, "count": len(pipelines)})


@router.post("/pipeline/{pipeline_id}/cancel")
def post_cancel_pipeline(pipeline_id: str):
    """取消任务链"""
    with _pipeline_lock:
        pipeline = _pipeline_registry.get(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="任务链不存在")
        if pipeline["status"] != "running":
            raise HTTPException(status_code=400, detail="任务链未在运行中")
        pipeline["status"] = "failed"
        pipeline["finished_at"] = datetime.now().isoformat()
        pipeline["error"] = "手动取消"
        for step in pipeline["steps"]:
            if step["status"] in ("pending", "running"):
                step["status"] = "failed"
                step["finished_at"] = datetime.now().isoformat()
    db_pipeline = SessionLocal()
    try:
        crud.system_operation_log_crud.create(
            db_pipeline,
            schemas.SystemOperationLogCreate(
                operation_type='pipeline_cancel',
                target_type='pipeline',
                target_id=pipeline_id,
                detail='手动取消任务链',
                result='success',
            )
        )
        db_pipeline.commit()
    except Exception as exc:
        logger.warning('[SYNC] 记录 pipeline 取消日志失败: %s', exc)
    finally:
        db_pipeline.close()
    return success({"pipeline_id": pipeline_id, "status": "cancelled"})


# ==================== 全量历史日线数据同步 ====================


def _fetch_symbol_history_akshare(symbol: str, start_date: str, end_date: str) -> tuple:
    """获取单只股票历史日线数据（akshare），返回 (records, error)"""
    import akshare as ak

    if symbol.startswith('6'):
        prefix = 'sh'
    elif symbol.startswith(('0', '2', '3')):
        prefix = 'sz'
    else:
        prefix = 'bj'
    code = f'{prefix}{symbol}'

    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)
        try:
            with akshare_lock:
                df = ak.stock_zh_a_daily(symbol=code, start_date=start_date, end_date=end_date, adjust='qfq')
        finally:
            socket.setdefaulttimeout(old_timeout)
    except Exception as exc:
        return [], str(exc)

    if df is None or df.empty:
        return [], None

    df = df.sort_values('date').reset_index(drop=True)
    df['preclose'] = df['close'].shift(1)

    records = []
    for _, row in df.iterrows():
        preclose = float(row['preclose']) if pd.notna(row['preclose']) else 0
        close = float(row['close']) if pd.notna(row['close']) else None
        high = float(row['high']) if pd.notna(row['high']) else None
        low = float(row['low']) if pd.notna(row['low']) else None

        _trade_date = pd.to_datetime(row['date']).date()

        records.append({
            'trade_date': _trade_date,
            'symbol': symbol,
            'open': float(row['open']) if pd.notna(row['open']) else None,
            'high': high,
            'low': low,
            'close': close,
            'volume': int(float(row['volume'])) if pd.notna(row['volume']) else None,
            'amount': float(row['amount']) if pd.notna(row['amount']) else None,
            'amplitude': round((high - low) / preclose * 100, 4) if preclose and high is not None and low is not None else 0.0,
            'pct_chg': round((close - preclose) / preclose * 100, 4) if preclose and close is not None else 0.0,
            'price_change': round(close - preclose, 4) if close is not None and preclose else 0.0,
            'turnover': float(row['turnover']) * 100 if pd.notna(row['turnover']) else None,
        })

    return records, None


def _sync_history_full_bulk(
    task_id: str | None = None,
    start_date: str = '20200101',
    end_date: str | None = None,
) -> dict:
    """全量历史日线数据同步（akshare，多线程），换手率存百分位"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    db = SessionLocal()
    try:
        all_stocks = crud.stock_basic_crud.get_list(
            db,
            schemas.StockBasicQuery(page_num=1, page_size=10000)
        )[0]
        all_stocks = [s for s in all_stocks if s.market != '北交所']
    finally:
        db.close()

    _total = len(all_stocks)
    _counter = [0]
    _success_records = [0]
    _failed_symbols: list[str] = []
    _skipped_symbols: list[str] = []
    _records_buffer: list[dict] = []
    _lock = threading.Lock()

    def _flush_buffer():
        if not _records_buffer:
            return
        batch = _records_buffer[:]
        db_write = SessionLocal()
        try:
            upsert_stmt = insert(models.StockDaily).values(batch)
            update_dict = {
                k: upsert_stmt.inserted[k]
                for k in upsert_stmt.inserted.keys()
                if k not in ('id', 'trade_date', 'symbol')
            }
            upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
            db_write.execute(upsert_stmt)
            db_write.commit()
            _success_records[0] += len(batch)
        except Exception as exc:
            logger.error('[SYNC_HISTORY_FULL] 批量写入失败，批次 %s 条: %s', len(batch), exc)
            try:
                db_write.rollback()
            except Exception:
                pass
        finally:
            db_write.close()
        _records_buffer.clear()

    def _process_stock(stock):
        records, error = _fetch_symbol_history_akshare(stock.symbol, start_date, end_date)
        with _lock:
            _counter[0] += 1
            current = _counter[0]
            if error:
                _failed_symbols.append(stock.symbol)
                status = 'ERR'
            elif not records:
                _skipped_symbols.append(stock.symbol)
                status = 'SKIP'
            else:
                _records_buffer.extend(records)
                status = 'OK'
                if len(_records_buffer) >= 5000:
                    _flush_buffer()

            if task_id and (current % 10 == 0 or current == _total):
                _update_task_progress(task_id, current, _total)

            logger.info(
                '[SYNC_HISTORY_FULL] [%s/%s] %s %s records=%s',
                current, _total, stock.symbol, status, len(records)
            )

    logger.info('[SYNC_HISTORY_FULL] 开始全量同步，共 %s 只，日期 %s ~ %s', _total, start_date, end_date)
    _update_task_progress(task_id, 0, _total)

    workers = get_settings().sync_max_workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_process_stock, s) for s in all_stocks]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                logger.error('[SYNC_HISTORY_FULL] 处理异常: %s', exc)

    _flush_buffer()

    return {
        'total_stocks': _total,
        'success_records': _success_records[0],
        'failed': len(_failed_symbols),
        'skipped': len(_skipped_symbols),
        'failed_symbols': _failed_symbols[:50],
        'summary': (
            f'全量同步完成，股票 {_total} 只，'
            f'成功记录 {_success_records[0]} 条，'
            f'失败 {len(_failed_symbols)} 只，'
            f'跳过 {len(_skipped_symbols)} 只'
        ),
    }


def _run_sync_history_full_bg(task_id: str, start_date: str, end_date: str, log_id: int) -> None:
    """后台执行全量历史数据同步任务"""
    logger.info('[SYNC_HISTORY_FULL_BG] 后台任务启动 task_id=%s', task_id)
    try:
        result = _sync_history_full_bulk(task_id=task_id, start_date=start_date, end_date=end_date)
        _finish_task(task_id, result=result)
        status = 'success'
    except Exception as exc:
        logger.error('[SYNC_HISTORY_FULL_BG] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        _finish_task(task_id, error=str(exc))
        result = {
            'total_stocks': 0,
            'success_records': 0,
            'failed': 0,
            'skipped': 0,
            'summary': f'异常: {exc}',
        }
        status = 'failed'

    db = SessionLocal()
    try:
        crud.sync_job_log_crud.finish(
            db, log_id, status,
            success_count=result.get('success_records', 0),
            failed_count=result.get('failed', 0),
            total_count=result.get('total_stocks', 0),
            extra_info=result.get('summary', ''),
        )
        db.commit()
    except Exception as exc:
        logger.warning('[SYNC_HISTORY_FULL_BG] 更新日志失败: %s', exc)
    finally:
        db.close()


@router.post("/history-full")
def post_sync_history_full(
    start_date: str = Query('20200101', description="起始日期，格式 YYYYMMDD"),
    end_date: str = Query(None, description="结束日期，格式 YYYYMMDD，默认今天"),
    db: Session = Depends(get_db),
):
    """全量历史日线数据同步（akshare，多线程，后台异步）

    换手率存储为百分位（如 0.57 表示 0.57%）。
    股票代码从 stock_basic 表获取，排除北交所。
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    log = crud.sync_job_log_crud.create(
        db,
        schemas.SyncJobLogCreate(
            job_type='history_full',
            trigger_type='manual',
            trade_date=start_date,
        )
    )
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='sync_manual',
            target_type='job',
            target_id=str(log.id),
            detail=f'手动触发全量历史同步，{start_date} ~ {end_date}',
            result='success',
        )
    )
    db.commit()
    task_id = str(uuid.uuid4())
    _register_task(task_id, start_date, job_type='history_full', log_id=log.id)
    t = threading.Thread(
        target=_run_sync_history_full_bg,
        args=(task_id, start_date, end_date, log.id),
        daemon=True,
    )
    t.start()
    logger.info('[SYNC_HISTORY_FULL_API] 已提交后台任务 log_id=%s', log.id)
    return success({
        "task_id": task_id,
        "log_id": log.id,
        "status": "running",
        "hint": "全量历史同步任务已提交后台执行，约需 30-60 分钟，请稍后刷新页面查看",
    })


# ==================== 细分行业批量同步 ====================


def _run_sync_industry_detail_bg(task_id: str, log_id: int) -> None:
    """后台执行细分行业批量同步"""
    from app.services.industry_detail_sync import sync_all_industry_detail

    logger.info('[SYNC_INDUSTRY_DETAIL_BG] 后台任务启动 task_id=%s', task_id)
    try:
        def _on_progress(current: int, total: int, status: str):
            _update_task_progress(task_id, current, total)

        result = sync_all_industry_detail(max_workers=10, on_progress=_on_progress)
        _finish_task(task_id, result=result)

        db = SessionLocal()
        try:
            crud.sync_job_log_crud.finish(
                db, log_id, 'success',
                success_count=result.get('db_success', 0),
                failed_count=result.get('failed', 0),
                total_count=result.get('total', 0),
                extra_info=f"industry_detail_sync, db_success={result.get('db_success',0)}",
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.error('[SYNC_INDUSTRY_DETAIL_BG] 任务异常: %s', exc)
        logger.error(traceback.format_exc())
        _finish_task(task_id, error=str(exc))
        db = SessionLocal()
        try:
            crud.sync_job_log_crud.finish(
                db, log_id, 'failed', error_message=str(exc)[:2000]
            )
            db.commit()
        finally:
            db.close()


@router.post("/industry-detail")
def post_sync_industry_detail(
    db: Session = Depends(get_db),
):
    """批量同步全部股票的细分行业（后台异步版，来源：东方财富 F10）"""
    log = crud.sync_job_log_crud.create(
        db, schemas.SyncJobLogCreate(job_type='industry_detail', trigger_type='manual')
    )
    crud.system_operation_log_crud.create(
        db,
        schemas.SystemOperationLogCreate(
            operation_type='sync_manual',
            target_type='job',
            target_id=str(log.id),
            detail='手动触发细分行业批量同步',
            result='success',
        )
    )
    db.commit()
    task_id = str(uuid.uuid4())
    _register_task(task_id, "industry_detail", job_type='industry_detail', log_id=log.id)
    t = threading.Thread(
        target=_run_sync_industry_detail_bg,
        args=(task_id, log.id),
        daemon=True,
    )
    t.start()
    logger.info('[SYNC_INDUSTRY_DETAIL_API] 已提交后台任务 log_id=%s', log.id)
    return success({
        "task_id": task_id,
        "log_id": log.id,
        "status": "running",
        "hint": "细分行业同步任务已提交后台执行，约需 5-10 分钟，请稍后刷新页面查看",
    })
