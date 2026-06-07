"""
定时任务定义
"""

import logging
import time
from datetime import datetime

from app import crud, models, schemas
from app.database import SessionLocal
from app.routes.market_sentiment import _persist_market_sentiment
from app.routes.stock_indicator import _build_indicator_for_symbol
from app.routes.sync import (
    _sync_board_daily_em,
    _sync_daily_bulk,
    _sync_etf_daily_em,
    _sync_financial_bulk,
    _sync_stock_basic_from_akshare,
    _sync_stock_basic_from_baostock,
    _test_akshare,
    _test_baostock,
)
from app.scheduler import _with_job_log, get_last_trade_date, is_trading_day

logger = logging.getLogger(__name__)


@_with_job_log('stock_basic')
def scheduled_sync_stock_basic(db, log_id: int) -> None:
    """定时同步股票基础信息"""
    try:
        result = _sync_stock_basic_from_akshare(db)
        source = 'akshare'
        extra = f'source={source}'
    except Exception as exc:
        logger.warning('[SCHEDULER] AkShare 失败，回退 Baostock: %s', exc)
        result = _sync_stock_basic_from_baostock(db)
        source = 'baostock'
        extra = f'source={source}, fallback_reason={str(exc)[:200]}'

    crud.sync_job_log_crud.finish(
        db,
        log_id,
        status='success',
        success_count=result.get('success', 0),
        failed_count=0,
        total_count=result.get('total', 0),
        extra_info=extra,
    )
    db.commit()


@_with_job_log('daily')
def scheduled_sync_daily(db, log_id: int) -> None:
    """定时同步最近交易日日线数据"""
    today = datetime.now()
    if not is_trading_day(today):
        logger.info('[SCHEDULER] 今日 %s 非交易日，跳过日线同步', today.strftime('%Y-%m-%d'))
        crud.sync_job_log_crud.finish(
            db, log_id, 'skipped', extra_info='non-trading day'
        )
        db.commit()
        return

    trade_date = get_last_trade_date()

    existing = db.query(models.SyncJobLog).filter(
        models.SyncJobLog.job_type == 'daily',
        models.SyncJobLog.status == 'success',
        models.SyncJobLog.trade_date == trade_date,
    ).first()

    if existing:
        logger.info('[SCHEDULER] 交易日 %s 的日线数据已同步，跳过', trade_date)
        crud.sync_job_log_crud.finish(
            db, log_id, 'skipped', extra_info=f'trade_date={trade_date} already synced'
        )
        db.commit()
        return

    source = 'baostock'
    if not _test_baostock():
        if _test_akshare():
            source = 'akshare'
        else:
            raise RuntimeError('Baostock 和 AkShare 均不可用')

    log = crud.sync_job_log_crud.get_by_id(db, log_id)
    if log:
        log.trade_date = trade_date
        db.commit()

    result = _sync_daily_bulk(trade_date, source=source)

    # 日线同步完成后自动预计算市场情绪
    from datetime import datetime as _datetime
    trade_date_obj = _datetime.strptime(trade_date, '%Y%m%d').date()
    try:
        _persist_market_sentiment(db, trade_date_obj)
        logger.info('[SCHEDULER] 交易日 %s 市场情绪预计算完成', trade_date)
    except Exception as exc:
        logger.warning('[SCHEDULER] 市场情绪预计算失败: %s', exc)

    crud.sync_job_log_crud.finish(
        db,
        log_id,
        status='success',
        success_count=result.get('upserted', 0),
        failed_count=result.get('failed', 0),
        skipped_count=result.get('skipped', 0),
        total_count=result.get('total_stocks', 0),
        trade_date=trade_date,
        extra_info=f'source={source}',
    )
    db.commit()


@_with_job_log('financial')
def scheduled_sync_financial(db, log_id: int) -> None:
    """定时同步财务指标"""
    result = _sync_financial_bulk(only_missing=True)

    crud.sync_job_log_crud.finish(
        db,
        log_id,
        status='success',
        success_count=result.get('upserted', 0),
        failed_count=result.get('failed', 0),
        total_count=result.get('total_stocks', 0),
        extra_info='source=akshare_ths',
    )
    db.commit()


@_with_job_log('indicator')
def scheduled_compute_indicators(db, log_id: int) -> None:
    """定时计算日线指标（MACD/RSI/KDJ/BOLL等）"""
    today = datetime.now()
    if not is_trading_day(today):
        logger.info('[SCHEDULER] 今日 %s 非交易日，跳过指标计算', today.strftime('%Y-%m-%d'))
        crud.sync_job_log_crud.finish(
            db, log_id, 'skipped', extra_info='non-trading day'
        )
        db.commit()
        return

    trade_date = get_last_trade_date()
    formatted_date = f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}'

    exists = db.query(models.StockDaily).filter(
        models.StockDaily.trade_date == trade_date
    ).first()
    if not exists:
        logger.warning('[SCHEDULER] 交易日期 %s 无日线数据，跳过指标计算', trade_date)
        crud.sync_job_log_crud.finish(
            db, log_id, 'skipped', extra_info=f'no daily data for {trade_date}'
        )
        db.commit()
        return

    symbols = [
        row[0] for row in
        db.query(models.StockDaily.symbol).filter(
            models.StockDaily.trade_date == trade_date
        ).distinct().all()
    ]

    total = len(symbols)
    success_count = 0
    failed_count = 0
    items = []

    for symbol in symbols:
        indicator_data = _build_indicator_for_symbol(db, symbol, trade_date)
        if indicator_data is None:
            failed_count += 1
            continue
        indicator_data['symbol'] = symbol
        indicator_data['trade_date'] = trade_date
        items.append(indicator_data)
        success_count += 1

    if items:
        result = crud.stock_daily_indicator_crud.create_or_update_batch(db, items)
        success_count = result['success']
        failed_count = result['failed']

    crud.sync_job_log_crud.finish(
        db,
        log_id,
        status='success',
        success_count=success_count,
        failed_count=failed_count,
        total_count=total,
        trade_date=trade_date,
        extra_info=f'indicators for {formatted_date}',
    )
    db.commit()


@_with_job_log('board_daily')
def scheduled_sync_board_daily(db, log_id: int) -> None:
    """定时同步板块/ETF日线数据"""
    trade_date = get_last_trade_date()

    existing = db.query(models.SyncJobLog).filter(
        models.SyncJobLog.job_type == 'board_daily',
        models.SyncJobLog.status == 'success',
        models.SyncJobLog.trade_date == trade_date,
    ).first()

    if existing:
        logger.info('[SCHEDULER] 交易日 %s 的板块日线已同步，跳过', trade_date)
        crud.sync_job_log_crud.finish(
            db, log_id, 'skipped', extra_info=f'trade_date={trade_date} already synced'
        )
        db.commit()
        return

    log = crud.sync_job_log_crud.get_by_id(db, log_id)
    if log:
        log.trade_date = trade_date
        db.commit()

    board_result = _sync_board_daily_em()
    etf_result = _sync_etf_daily_em()
    total_records = board_result.get('records', 0) + etf_result.get('records', 0)

    crud.sync_job_log_crud.finish(
        db,
        log_id,
        status='success',
        success_count=total_records,
        total_count=board_result.get('total_boards', 0) + etf_result.get('total_etfs', 0),
        trade_date=trade_date,
        extra_info=f'board_records={board_result.get("records",0)}, etf_records={etf_result.get("records",0)}',
    )
    db.commit()
