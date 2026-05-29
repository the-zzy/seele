import os
import sys
import concurrent.futures
import logging
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app import models, crud
from app.routes.stock_indicator import _build_indicator_for_symbol

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


def recalc_for_date(db, trade_date: date):
    formatted = trade_date.strftime('%Y%m%d')
    logger.info('[%s] 开始查询股票列表...', formatted)

    symbols = [
        row[0] for row in
        db.query(models.StockDaily.symbol)
        .filter(models.StockDaily.trade_date == formatted)
        .distinct()
        .all()
    ]
    total = len(symbols)
    logger.info('[%s] 共 %d 只股票需要计算', formatted, total)

    if not symbols:
        return

    # 批量预查询历史数据（每个 symbol 最多 60 条）
    logger.info('[%s] 批量预查询历史数据...', formatted)
    all_rows = (
        db.query(models.StockDaily)
        .filter(
            models.StockDaily.symbol.in_(symbols),
            models.StockDaily.trade_date <= formatted,
        )
        .order_by(models.StockDaily.symbol, models.StockDaily.trade_date.desc())
        .all()
    )
    rows_by_symbol: dict[str, list] = {}
    for row in all_rows:
        symbol_rows = rows_by_symbol.setdefault(row.symbol, [])
        if len(symbol_rows) < 60:
            symbol_rows.append(row)

    logger.info('[%s] 开始并行计算指标...', formatted)

    items = []
    success_count = 0
    failed_count = 0

    def _calc(symbol):
        indicator_data = _build_indicator_for_symbol(
            db=None, symbol=symbol, trade_date=trade_date,
            rows=rows_by_symbol.get(symbol)
        )
        if indicator_data is None:
            return None
        indicator_data['symbol'] = symbol
        indicator_data['trade_date'] = formatted
        return indicator_data

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_calc, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(futures):
            sym = futures[future]
            try:
                result = future.result()
                if result is not None:
                    items.append(result)
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as exc:
                logger.error('[%s] %s 计算失败: %s', formatted, sym, exc)
                failed_count += 1

    logger.info('[%s] 计算完成: 成功=%d, 失败=%d, 开始批量写入...',
                formatted, success_count, failed_count)

    if items:
        result = crud.stock_daily_indicator_crud.create_or_update_batch(db, items)
        db.commit()
        logger.info('[%s] 写入完成: 成功=%d, 失败=%d',
                    formatted, result['success'], result['failed'])
    else:
        logger.warning('[%s] 无指标数据需要写入', formatted)


def main():
    trade_dates = [
        date(2026, 5, 12), date(2026, 5, 13), date(2026, 5, 14),
        date(2026, 5, 15), date(2026, 5, 18), date(2026, 5, 19),
        date(2026, 5, 20), date(2026, 5, 21), date(2026, 5, 22),
        date(2026, 5, 25), date(2026, 5, 26), date(2026, 5, 27),
        date(2026, 5, 28),
    ]

    db = SessionLocal()
    try:
        for td in trade_dates:
            recalc_for_date(db, td)
    finally:
        db.close()

    logger.info('全部完成')


if __name__ == '__main__':
    main()
