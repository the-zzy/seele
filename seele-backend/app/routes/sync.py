"""
数据同步路由
"""

import asyncio
import concurrent.futures
import json
import logging
import threading
import time
import traceback
import uuid
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional

import baostock as bs
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app import crud, models, schemas
from app.database import SessionLocal, get_db
from app.filters import get_baostock_code
from app.response import success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["数据同步"])

# 后台任务状态存储
_task_lock = threading.Lock()
_task_registry: dict[str, dict] = {}


def _register_task(task_id: str, trade_date: str) -> None:
    with _task_lock:
        _task_registry[task_id] = {
            "task_id": task_id,
            "trade_date": trade_date,
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


def format_date(d: date) -> str:
    """格式化日期"""
    return d.strftime("%Y-%m-%d")


def _sync_daily_for_symbol(db: Session, symbol: str, start_date: str, end_date: str) -> int:
    """同步单只股票的日线数据，返回成功处理的记录数（Baostock）"""
    try:
        code = get_baostock_code(symbol)
        start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

        lg = bs.login()
        if lg.error_code != '0':
            return 0

        try:
            fields = 'date,code,open,high,low,close,preclose,volume,amount,turn,pctChg'
            rs = bs.query_history_k_data_plus(
                code, fields, start_date=start, end_date=end,
                frequency='d', adjustflag='3'
            )
            rows = []
            while (rs.error_code == '0') and rs.next():
                rows.append(rs.get_row_data())

            if not rows:
                return 0

            count = 0
            for row in rows:
                preclose = float(row[6]) if row[6] else 0
                close = float(row[5]) if row[5] else None
                high = float(row[3]) if row[3] else None
                low = float(row[4]) if row[4] else None

                record = {
                    'trade_date': row[0],
                    'symbol': symbol,
                    'open': float(row[2]) if row[2] else None,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': int(float(row[7])) if row[7] else None,
                    'amount': float(row[8]) if row[8] else None,
                    'amplitude': round((high - low) / preclose * 100, 4) if preclose and high is not None and low is not None else 0.0,
                    'pct_chg': float(row[10]) if row[10] else None,
                    'price_change': round(close - preclose, 4) if close is not None and preclose else 0.0,
                    'turnover': float(row[9]) if row[9] else None,
                }
                obj_in = schemas.StockDailyCreate(**record)
                crud.stock_daily_crud.upsert(db, obj_in)
                count += 1
            return count
        finally:
            bs.logout()
    except Exception:
        return 0


def _test_baostock() -> bool:
    """测试 Baostock 是否可用（带 10 秒超时）"""
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
            return future.result(timeout=10)
    except concurrent.futures.TimeoutError:
        print('[SYNC] Baostock test timeout (10s)')
        return False
    except Exception as exc:
        print(f'[SYNC] Baostock test failed: {exc}')
        return False


def _test_akshare() -> bool:
    """测试 AkShare 东方财富源是否可用"""
    try:
        import akshare as ak
        # 使用最近一个交易日进行测试，避免节假日无数据
        today = datetime.today()
        # 向前查找最近一个交易日（最多回溯 10 天）
        for i in range(10):
            test_date = (today - timedelta(days=i)).strftime('%Y%m%d')
            try:
                df = ak.stock_zh_a_hist(symbol='000001', period='daily', start_date=test_date, end_date=test_date, adjust='')
                if not df.empty:
                    return True
            except Exception:
                continue
        return False
    except Exception as exc:
        print(f'[SYNC] AkShare test failed: {exc}')
        return False


def _fetch_baostock_record(symbol: str, trade_date: str, fields: str):
    """获取 Baostock 单只股票数据。返回 (record, skip_reason, fail_reason)"""
    code = get_baostock_code(symbol)

    try:
        rs = bs.query_history_k_data_plus(
            code, fields,
            start_date=trade_date, end_date=trade_date,
            frequency='d', adjustflag='3'
        )
        rows = []
        count = 0
        while (rs.error_code == '0') and rs.next():
            rows.append(rs.get_row_data())
            count += 1
            if count >= 10:
                break
    except Exception as e:
        return None, None, str(e)

    if rs.error_code != '0':
        return None, None, rs.error_msg
    if not rows:
        return None, 'no_data', None
    row = rows[0]
    if not row[5] or float(row[5]) == 0:
        return None, 'zero_close', None

    preclose = float(row[6]) if row[6] else 0
    close = float(row[5])
    high = float(row[3]) if row[3] else None
    low = float(row[4]) if row[4] else None

    record = {
        'trade_date': row[0],
        'symbol': symbol,
        'open': float(row[2]) if row[2] else None,
        'high': high,
        'low': low,
        'close': close,
        'volume': int(float(row[7])) if row[7] else None,
        'amount': float(row[8]) if row[8] else None,
        'amplitude': round((high - low) / preclose * 100, 4) if preclose and high is not None and low is not None else 0.0,
        'pct_chg': float(row[10]) if row[10] else None,
        'price_change': round(close - preclose, 4) if preclose else 0.0,
        'turnover': float(row[9]) if row[9] else None,
    }
    return record, None, None


def _fetch_akshare_record(symbol: str, trade_date: str):
    """获取 AkShare 东方财富源单只股票数据。返回 (record, skip_reason, fail_reason)"""
    end = datetime.strptime(trade_date, '%Y%m%d')
    start = (end - timedelta(days=7)).strftime('%Y%m%d')
    end_str = end.strftime('%Y%m%d')

    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=symbol, period='daily', start_date=start, end_date=end_str, adjust='')
    except Exception as e:
        return None, None, str(e)

    if df.empty:
        return None, 'no_data', None

    target_date_fmt = f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}'
    target_rows = df[df['日期'] == target_date_fmt]

    if target_rows.empty:
        return None, 'no_data', None

    row = target_rows.iloc[-1]

    close = row['收盘']
    if not pd.notna(close) or float(close) == 0:
        return None, 'zero_close', None

    change = row['涨跌额']
    preclose = float(close) - float(change) if pd.notna(change) else 0

    high = row['最高']
    low = row['最低']

    def _parse_pct(val):
        if pd.notna(val) and isinstance(val, str) and val.endswith('%'):
            return float(val.replace('%', ''))
        return float(val) if pd.notna(val) else 0.0

    record = {
        'trade_date': target_date_fmt,
        'symbol': symbol,
        'open': float(row['开盘']) if pd.notna(row['开盘']) else None,
        'high': float(high) if pd.notna(high) else None,
        'low': float(low) if pd.notna(low) else None,
        'close': float(close),
        'volume': int(float(row['成交量']) * 100) if pd.notna(row['成交量']) else None,
        'amount': float(row['成交额']) if pd.notna(row['成交额']) else None,
        'amplitude': _parse_pct(row['振幅']),
        'pct_chg': _parse_pct(row['涨跌幅']),
        'price_change': round(float(change), 4) if pd.notna(change) else 0.0,
        'turnover': _parse_pct(row['换手率']) if pd.notna(row['换手率']) else None,
    }
    return record, None, None


# 3.1 同步所有股票日线数据
@router.post("/daily")
def post_sync_daily(
    db: Session = Depends(get_db),
):
    """同步所有股票日线数据"""
    # 获取所有股票代码（仅沪深主板且非ST）
    all_stocks = crud.stock_basic_crud.get_list(
        db,
        schemas.StockBasicQuery(page_num=1, page_size=10000, market="主板", exclude_st=True)
    )[0]

    success_count = 0
    failed_count = 0
    start_date = "20240101"
    end_date = datetime.today().strftime("%Y%m%d")

    for stock in all_stocks:
        symbol = stock.symbol
        count = _sync_daily_for_symbol(db, symbol, start_date, end_date)
        if count > 0:
            success_count += count
        else:
            failed_count += 1
        time.sleep(0.03)

    return success(f"同步完成，成功: {success_count}, 失败: {failed_count}")


# 3.2 同步单只股票日线数据
@router.post("/daily/{symbol}")
def post_sync_daily_by_symbol(
    symbol: str,
    db: Session = Depends(get_db),
):
    """同步单只股票日线数据"""
    start_date = "20240101"
    end_date = datetime.today().strftime("%Y%m%d")
    count = _sync_daily_for_symbol(db, symbol, start_date, end_date)

    return success(f"同步完成: {symbol}, 更新 {count} 条")


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


def _sync_daily_bulk(trade_date: str, source: str = 'baostock', task_id: str | None = None, on_progress: Callable | None = None, progress_queue: asyncio.Queue | None = None) -> dict:
    """按日期同步全部A股日线数据的内部实现（单线程版）"""
    db = SessionLocal()
    try:
        all_stocks = crud.stock_basic_crud.get_list(
            db,
            schemas.StockBasicQuery(page_num=1, page_size=10000, market="主板", exclude_st=True)
        )[0]
    finally:
        db.close()

    if source == 'baostock':
        lg = bs.login()
        if lg.error_code != '0':
            raise RuntimeError(f"Baostock login failed: {lg.error_msg}")
        fields = 'date,code,open,high,low,close,preclose,volume,amount,turn,pctChg'
    elif source != 'akshare':
        raise ValueError(f"Unknown source: {source}")

    _skipped: List[str] = []
    _failed: List[dict] = []
    results: List[dict] = []
    total_stocks = len(all_stocks)

    def _push_progress(current: int, status: str, extra: dict | None = None):
        payload = {"current": current, "total": total_stocks, "status": status}
        if extra:
            payload.update(extra)
        if task_id and current % 10 == 0:
            _update_task_progress(task_id, current, total_stocks)
        if on_progress:
            on_progress(current, total_stocks, status)
        if progress_queue is not None:
            try:
                progress_queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def _flush_results():
        nonlocal results
        if not results:
            return
        db_write = SessionLocal()
        try:
            upsert_stmt = insert(models.StockDaily).values(results)
            update_dict = {
                k: upsert_stmt.inserted[k]
                for k in upsert_stmt.inserted.keys()
                if k not in ("id", "trade_date", "symbol")
            }
            upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
            db_write.execute(upsert_stmt)
            db_write.commit()
        finally:
            db_write.close()
        results = []

    try:
        _push_progress(0, "running", {"message": f"开始同步（数据源: {source}）"})
        for i, stock in enumerate(all_stocks, 1):
            symbol = stock.symbol

            if source == 'baostock':
                record, skip_reason, fail_reason = _fetch_baostock_record(symbol, trade_date, fields)
            else:
                record, skip_reason, fail_reason = _fetch_akshare_record(symbol, trade_date)

            if fail_reason:
                _failed.append({"symbol": symbol, "reason": fail_reason})
            elif skip_reason:
                _skipped.append(symbol)
            else:
                results.append(record)

            _push_progress(i, "running", {"symbol": symbol, "success": len(results), "skipped": len(_skipped), "failed": len(_failed)})

            if i % 100 == 0:
                _flush_results()

            if i % 100 == 0 or i == total_stocks:
                time.sleep(0.5)
            else:
                time.sleep(0.03)
    finally:
        if source == 'baostock':
            bs.logout()

    _flush_results()

    _write_failed_log(trade_date, _skipped, _failed)

    return {
        "trade_date": trade_date,
        "total_stocks": total_stocks,
        "upserted": len(results),
        "skipped": len(_skipped),
        "failed": len(_failed),
        "failed_symbols": [item["symbol"] for item in _failed[:50]],
        "summary": (
            f"日期 {trade_date} 同步完成（{source}），"
            f"写入/更新: {len(results)}, "
            f"停牌/无数据: {len(_skipped)}, "
            f"异常: {len(_failed)}"
        ),
    }


def _run_sync_bg(task_id: str, trade_date: str) -> None:
    """后台执行同步任务"""
    try:
        result = _sync_daily_bulk(trade_date, task_id=task_id)
        _finish_task(task_id, result=result)
    except Exception as exc:
        _finish_task(task_id, error=str(exc))


# 3.2.1 按日期同步全部A股日线数据（后台异步版）
@router.post("/daily/date/{trade_date}")
def post_sync_daily_by_date(
    trade_date: str,
    db: Session = Depends(get_db),
):
    """
    按日期同步全部A股日线数据（后台异步版）
    - 从 Baostock API 获取指定日期的所有A股数据
    - 更新到数据库（存在则更新，不存在则插入）
    """
    task_id = str(uuid.uuid4())
    _register_task(task_id, trade_date)
    t = threading.Thread(target=_run_sync_bg, args=(task_id, trade_date), daemon=True)
    t.start()
    return success({
        "task_id": task_id,
        "trade_date": trade_date,
        "status": "running",
        "hint": "同步任务已提交后台执行，约需 5-10 秒，请稍后刷新页面查看",
    })


# 3.2.3 查询同步任务状态
@router.get("/task/{task_id}")
def get_sync_task_status(task_id: str):
    """查询同步任务状态"""
    with _task_lock:
        task = _task_registry.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return success(task)


# 3.3 对比数据库与stock_basic表数据
@router.get("/compare")
def get_sync_compare(
    trade_date: date = Query(..., description="交易日期"),
    db: Session = Depends(get_db),
):
    """对比数据库与stock_basic表数据 - 仅对比沪深主板且非ST股票"""
    # 获取沪深主板且非ST的股票代码列表
    all_stocks = crud.stock_basic_crud.get_list(
        db,
        schemas.StockBasicQuery(page_num=1, page_size=10000, market="主板", exclude_st=True)
    )[0]
    all_symbols = {s.symbol for s in all_stocks}

    # 获取数据库数据（仅保留主板非ST）
    db_data = crud.stock_daily_crud.get_by_date(db, trade_date)
    db_data = [d for d in db_data if d.symbol in all_symbols]
    db_count = len(db_data)

    # 获取当日有数据的股票代码
    db_symbols = {d.symbol for d in db_data}

    # 计算差异
    only_in_basic = list(all_symbols - db_symbols)
    only_in_db = []  # 理论上不存在basic中没有但db中有的情况
    differences = []

    summary = (
        f"对比日期: {format_date(trade_date)} | "
        f"数据库: {db_count}条 | "
        f"基础表: {len(all_symbols)}条 | "
        f"缺失: {len(only_in_basic)}条"
    )

    return success({
        "trade_date": trade_date,
        "db_count": db_count,
        "basic_count": len(all_symbols),
        "only_in_basic": only_in_basic,
        "only_in_db": only_in_db,
        "differences": differences,
        "summary": summary,
    })


# 3.4 SSE 实时进度推送同步接口
@router.get("/daily/date/{trade_date}/stream")
async def get_sync_daily_stream(trade_date: str):
    """
    SSE 实时推送同步进度
    收到请求后自动探测 Baostock / AkShare，优先使用 Baostock
    前端使用 EventSource('/api/sync/daily/date/2025-04-18/stream') 连接
    """
    # 探测数据源
    source = None
    if _test_baostock():
        source = 'baostock'
    elif _test_akshare():
        source = 'akshare'

    progress_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=100)

    def run_sync_in_thread():
        try:
            if source is None:
                progress_queue.put_nowait({
                    "status": "failed",
                    "error": "Baostock 和 AkShare 均不可用",
                })
                return
            result = _sync_daily_bulk(trade_date, source=source, progress_queue=progress_queue)
            try:
                progress_queue.put_nowait({"status": "completed", "result": result})
            except asyncio.QueueFull:
                pass
        except Exception as exc:
            try:
                progress_queue.put_nowait({"status": "failed", "error": str(exc)})
            except asyncio.QueueFull:
                pass

    thread = threading.Thread(target=run_sync_in_thread, daemon=True)
    thread.start()

    async def event_generator():
        # 先推送数据源信息
        if source:
            yield f"data: {json.dumps({'status': 'running', 'source': source, 'message': f'使用数据源: {source}'})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'failed', 'error': 'Baostock 和 AkShare 均不可用'})}\n\n"
            return

        while True:
            try:
                payload = await asyncio.wait_for(progress_queue.get(), timeout=300)
            except asyncio.TimeoutError:
                yield f"event: timeout\ndata: {json.dumps({'message': '同步超时'})}\n\n"
                break

            yield f"data: {json.dumps(payload)}\n\n"

            if payload.get("status") in ("completed", "failed"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
    except Exception:
        return None


def _sync_stock_basic_from_akshare(db: Session) -> dict:
    """从 AkShare 同步股票基础信息（上交所 + 深交所 + 北交所）"""
    import akshare as ak

    records_map: dict[str, dict] = {}

    # 获取流通市值（亿元）
    cap_map: dict[str, float] = {}
    try:
        df_spot = ak.stock_zh_a_spot_em()
        for _, row in df_spot.iterrows():
            symbol = str(row['代码']).strip().zfill(6)
            cap = row.get('流通市值')
            if pd.notna(cap) and cap:
                cap_map[symbol] = round(float(cap) / 1e8, 4)
    except Exception as exc:
        logger.warning('[SYNC_STOCK_BASIC] 获取流通市值失败: %s', exc)

    # 1. 上海
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
    return {
        'total': len(records),
        'created': result['created'],
        'updated': result['updated'],
    }


def _sync_stock_basic_from_baostock(db: Session) -> dict:
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
        return {
            'total': len(records),
            'created': result['created'],
            'updated': result['updated'],
        }
    finally:
        bs.logout()


# 3.5 同步股票基础信息
@router.post("/stock-basic")
def post_sync_stock_basic(
    db: Session = Depends(get_db),
):
    """同步股票基础信息（优先 akshare，失败回退 baostock）"""
    try:
        result = _sync_stock_basic_from_akshare(db)
        result['source'] = 'akshare'
    except Exception as exc:
        result = _sync_stock_basic_from_baostock(db)
        result['source'] = 'baostock'
        result['fallback_reason'] = str(exc)

    return success({
        'summary': f"同步完成（{result['source']}），共 {result['total']} 条，新增 {result['created']} 条，更新 {result['updated']} 条",
        **result,
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
    """同步单只股票财务指标，返回解析后的数据字典"""
    try:
        import akshare as ak
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
    except Exception:
        return None


def _sync_financial_bulk(
    task_id: str | None = None,
    on_progress: Callable | None = None,
    progress_queue: asyncio.Queue | None = None,
) -> dict:
    """批量同步全部股票财务指标"""
    logger.info('[SYNC_FINANCIAL] 开始批量同步财务指标')
    db = SessionLocal()
    try:
        all_stocks = crud.stock_basic_crud.get_list(
            db,
            schemas.StockBasicQuery(page_num=1, page_size=10000)
        )[0]
    except Exception as exc:
        logger.error('[SYNC_FINANCIAL] 获取股票列表失败: %s', exc)
        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()

    _failed: List[str] = []
    records: List[dict] = []
    total_stocks = len(all_stocks)
    logger.info('[SYNC_FINANCIAL] 共 %d 只股票待同步', total_stocks)

    def _push_progress(current: int, status: str, extra: dict | None = None):
        payload = {"current": current, "total": total_stocks, "status": status}
        if extra:
            payload.update(extra)
        if task_id and current % 10 == 0:
            _update_task_progress(task_id, current, total_stocks)
        if on_progress:
            on_progress(current, total_stocks, status)
        if progress_queue is not None:
            try:
                progress_queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    _push_progress(0, "running", {"message": "开始同步财务指标"})

    for i, stock in enumerate(all_stocks, 1):
        data = _sync_financial_for_symbol(stock.symbol, stock.name)
        if data:
            records.append(data)
        else:
            _failed.append(stock.symbol)

        _push_progress(i, "running", {
            "symbol": stock.symbol,
            "success": len(records),
            "failed": len(_failed),
        })

        if i % 50 == 0:
            time.sleep(0.5)

    # 批量写入
    db_write = SessionLocal()
    try:
        from sqlalchemy.dialects.mysql import insert
        if records:
            logger.info('[SYNC_FINANCIAL] 准备写入 %d 条记录', len(records))
            upsert_stmt = insert(models.StockFinancialIndicator).values(records)
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
        "total_stocks": total_stocks,
        "upserted": len(records),
        "failed": len(_failed),
        "failed_symbols": _failed[:50],
        "summary": (
            f"财务指标同步完成，"
            f"写入/更新: {len(records)}, "
            f"异常: {len(_failed)}"
        ),
    }


def _run_sync_financial_bg(task_id: str) -> None:
    """后台执行财务指标同步任务"""
    logger.info('[SYNC_FINANCIAL_BG] 后台任务启动, task_id=%s', task_id)
    try:
        result = _sync_financial_bulk(task_id=task_id)
        _finish_task(task_id, result=result)
        logger.info('[SYNC_FINANCIAL_BG] 任务完成, task_id=%s', task_id)
    except Exception as exc:
        logger.error('[SYNC_FINANCIAL_BG] 任务异常, task_id=%s, error=%s', task_id, exc)
        logger.error(traceback.format_exc())
        _finish_task(task_id, error=str(exc))


# 3.6 同步全部股票财务指标（后台异步版）
@router.post("/financial")
def post_sync_financial(
    db: Session = Depends(get_db),
):
    """同步全部股票财务指标（后台异步版）"""
    try:
        task_id = str(uuid.uuid4())
        _register_task(task_id, "financial")
        t = threading.Thread(target=_run_sync_financial_bg, args=(task_id,), daemon=True)
        t.start()
        logger.info('[SYNC_FINANCIAL_API] 已提交后台任务, task_id=%s', task_id)
        return success({
            "task_id": task_id,
            "status": "running",
            "hint": "财务指标同步任务已提交后台执行，约需 3-5 分钟，请稍后刷新页面查看",
        })
    except Exception as exc:
        logger.error('[SYNC_FINANCIAL_API] 提交任务失败: %s', exc)
        logger.error(traceback.format_exc())
        raise


# 3.6.1 SSE 实时推送财务指标同步进度
@router.get("/financial/stream")
async def get_sync_financial_stream():
    """
    SSE 实时推送财务指标同步进度
    前端使用 EventSource('/api/sync/financial/stream') 连接
    """
    progress_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=100)

    def run_sync_in_thread():
        try:
            result = _sync_financial_bulk(progress_queue=progress_queue)
            try:
                progress_queue.put_nowait({"status": "completed", "result": result})
            except asyncio.QueueFull:
                pass
        except Exception as exc:
            try:
                progress_queue.put_nowait({"status": "failed", "error": str(exc)})
            except asyncio.QueueFull:
                pass

    thread = threading.Thread(target=run_sync_in_thread, daemon=True)
    thread.start()

    async def event_generator():
        yield f"data: {json.dumps({'status': 'running', 'message': '开始同步财务指标'})}\n\n"

        while True:
            try:
                payload = await asyncio.wait_for(progress_queue.get(), timeout=300)
            except asyncio.TimeoutError:
                yield f"event: timeout\ndata: {json.dumps({'message': '同步超时'})}\n\n"
                break

            yield f"data: {json.dumps(payload)}\n\n"

            if payload.get("status") in ("completed", "failed"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 3.7 同步单只股票财务指标
@router.post("/financial/{symbol}")
def post_sync_financial_by_symbol(
    symbol: str,
    db: Session = Depends(get_db),
):
    """同步单只股票财务指标"""
    stock = crud.stock_basic_crud.get_by_symbol(db, symbol)
    name = stock.name if stock else symbol
    data = _sync_financial_for_symbol(symbol, name)
    if not data:
        raise HTTPException(status_code=404, detail=f"未获取到 {symbol} 的财务指标数据")

    obj_in = schemas.StockFinancialIndicatorCreate(**data)
    result = crud.stock_financial_indicator_crud.upsert(db, obj_in)
    return success({
        "symbol": symbol,
        "report_date": data.get("report_date").isoformat() if data.get("report_date") else None,
        "summary": f"同步完成: {symbol}",
    })
