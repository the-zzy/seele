#!/usr/bin/env python3
"""
独立脚本：从东方财富（EM）拉取板块成分股（行业 + 概念）

数据流：
  1. 从 DB 读取 board_info 中的行业/概念板块列表
  2. 通过 akshare 并发拉取每个板块的成分股
  3. 先清空旧数据再批量写入 board_constituent

用法：
    cd seele-backend
    source .venv/Scripts/activate
    python scripts/sync_board_constituent.py

可选参数：
    --workers  并发线程数，默认 2（东方财富源限流较严）
    --category industry|concept，默认同步全部
"""
import argparse
import concurrent.futures
import logging
import os
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DEPLOY_ENV", "dev")

import akshare as ak
from sqlalchemy import and_

from app import crud, models, schemas
from app.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

akshare_lock = threading.Lock()


def _get_boards(category: str = None) -> list:
    """从 DB 读取板块列表"""
    db = SessionLocal()
    try:
        query = db.query(models.BoardInfo).filter(
            models.BoardInfo.category.in_(['industry', 'concept'])
        )
        if category == 'industry':
            query = query.filter(models.BoardInfo.category == 'industry')
        elif category == 'concept':
            query = query.filter(models.BoardInfo.category == 'concept')
        return query.order_by(models.BoardInfo.category, models.BoardInfo.code).all()
    finally:
        db.close()


def _process_board(board) -> list[dict]:
    """拉取单板块成分股，返回 records"""
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
        logger.debug('[%s] %s 成分股拉取失败: %s', board.code, board.name, exc)

    return records


def sync_board_constituent(workers: int, category: str = None):
    """同步板块成分股主流程"""
    boards = _get_boards(category)
    if not boards:
        print('\n[ERR] DB 中没有找到板块数据，退出')
        return

    total = len(boards)
    industry_count = sum(1 for b in boards if b.category == 'industry')
    concept_count = sum(1 for b in boards if b.category == 'concept')

    print(f'\n========== 同步板块成分股 ==========')
    print(f'  板块总数: {total} ({industry_count} 行业 + {concept_count} 概念)')
    print(f'  并发数:   {workers}')
    print()

    _success = [0]
    _failed = [0]
    _total_records = [0]
    _lock = threading.Lock()
    start_time = time.time()

    def _handle_board(board):
        records = _process_board(board)
        with _lock:
            if records:
                db_write = SessionLocal()
                try:
                    crud.board_constituent_crud.delete_by_board(db_write, board.code)
                    for r in records:
                        crud.board_constituent_crud.upsert_batch(db_write, [
                            schemas.BoardConstituentCreate(**r)
                        ])
                    db_write.commit()
                    _success[0] += 1
                    _total_records[0] += len(records)
                except Exception as exc:
                    db_write.rollback()
                    logger.warning('[%s] %s 写入失败: %s', board.code, board.name, exc)
                    _failed[0] += 1
                finally:
                    db_write.close()
            else:
                _failed[0] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_handle_board, b) for b in boards]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                logger.error('单板块处理超时(30s)')
            except Exception as exc:
                logger.error('处理板块异常: %s', exc)
            # 每完成一个板块打印一次进度
            with _lock:
                done = _success[0] + _failed[0]
                pct = done / total * 100
                print(f'  [{done}/{total}] {pct:.0f}%  成功={_success[0]}  失败={_failed[0]}  成分股={_total_records[0]}')

    elapsed = time.time() - start_time
    print(f'\n========== 完成 ==========')
    print(f'  耗时:     {elapsed:.1f} 秒')
    print(f'  成功:     {_success[0]} 个板块')
    print(f'  失败:     {_failed[0]} 个板块')
    print(f'  总记录数: {_total_records[0]} 条')
    if elapsed > 0 and _total_records[0] > 0:
        print(f'  平均:     {_total_records[0] / elapsed:.0f} 条/秒')


def main():
    parser = argparse.ArgumentParser(description='同步东方财富板块成分股')
    parser.add_argument('--workers', type=int, default=2, help='并发线程数，默认 2')
    parser.add_argument(
        '--category', choices=['industry', 'concept'], default=None,
        help='板块类型，默认同步全部',
    )
    args = parser.parse_args()

    print(f'=== 东方财富板块成分股同步脚本 ===')
    print(f'   启动时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'   并发数:   {args.workers}')

    sync_board_constituent(args.workers, args.category)

    print('\n全部完成\n')


if __name__ == '__main__':
    main()
