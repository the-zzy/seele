"""
东方财富 F10 细分行业批量同步服务
"""

import json
import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, Optional

from app.database import SessionLocal
from app import crud, models

logger = logging.getLogger(__name__)

SURVEY_API_URL = 'http://f10.eastmoney.com/CompanySurvey/CompanySurveyAjax?code={code}'


def _infer_market_prefix(symbol: str) -> str:
    """根据股票代码推断交易所前缀"""
    if symbol.startswith('6'):
        return 'SH'
    if symbol.startswith(('82', '83', '87', '88', '89', '92', '93')):
        return 'BJ'
    if symbol.startswith(('4', '8')):
        return 'BJ'
    return 'SZ'


def fetch_industry_detail(symbol: str) -> Optional[str]:
    """从东方财富 F10 抓取单只股票的细分行业（sszjhhy）

    Returns:
        细分行业字符串，抓取失败返回 None
    """
    prefix = _infer_market_prefix(symbol)
    url = SURVEY_API_URL.format(code=f'{prefix}{symbol}')

    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ),
                'Referer': 'http://f10.eastmoney.com/',
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8')
    except Exception as exc:
        logger.warning('[INDUSTRY_DETAIL] 请求失败 %s: %s', symbol, exc)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning('[INDUSTRY_DETAIL] JSON 解析失败 %s: %s', symbol, exc)
        return None

    jbzl = data.get('jbzl') or {}
    industry_detail = jbzl.get('sszjhhy')
    if not industry_detail:
        # fallback 到 sshy（所属行业）
        industry_detail = jbzl.get('sshy')

    return industry_detail.strip() if industry_detail else None


def sync_all_industry_detail(
    max_workers: int = 10,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """批量同步所有股票的细分行业

    Args:
        max_workers: 并发线程数
        on_progress: 进度回调 (current, total, status)

    Returns:
        {"total": int, "success": int, "failed": int}
    """
    db = SessionLocal()
    try:
        symbols = [r[0] for r in db.query(models.StockBasic.symbol).all()]
    finally:
        db.close()

    total = len(symbols)
    if total == 0:
        return {"total": 0, "success": 0, "failed": 0}

    logger.info('[INDUSTRY_DETAIL] 开始批量同步，共 %d 只，并发 %d', total, max_workers)

    results = []
    success_count = 0
    failed_count = 0

    def _process(sym: str) -> dict:
        detail = fetch_industry_detail(sym)
        return {"symbol": sym, "industry_detail": detail}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process, sym): sym for sym in symbols}
        for idx, future in enumerate(as_completed(futures), 1):
            try:
                res = future.result()
                results.append(res)
                if res["industry_detail"]:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as exc:
                logger.error('[INDUSTRY_DETAIL] 处理异常: %s', exc)
                failed_count += 1

            if on_progress and idx % 50 == 0:
                on_progress(idx, total, 'running')

    # 批量写入数据库
    db_write = SessionLocal()
    try:
        batch_result = crud.stock_basic_crud.update_industry_detail_batch(
            db_write, [r for r in results if r["industry_detail"]]
        )
        db_write.commit()
        logger.info(
            '[INDUSTRY_DETAIL] 批量同步完成，total=%d, fetched=%d, db_success=%d',
            total, success_count, batch_result.get('success', 0)
        )
    except Exception as exc:
        db_write.rollback()
        logger.error('[INDUSTRY_DETAIL] 批量写入失败: %s', exc)
        raise
    finally:
        db_write.close()

    return {
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "db_success": batch_result.get('success', 0),
        "db_failed": batch_result.get('failed', 0),
    }
