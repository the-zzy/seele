#!/usr/bin/env python3
"""
独立脚本：从同花顺（THS）拉取板块日线数据（行业 + 概念）

东方财富 EM API 在部分网络环境下被 IIS 阻断（TLS fingerprint + IP level），
而同花顺 q.10jqka.com.cn 可通过 requests 正常访问（需 JS 解 v_code）。

数据流：
  1. 通过 akshare 获取 THS 行业/概念名称↔代码映射
  2. upsert board_info 表
  3. 对概念板块构建 inner_code 映射（300xxx → 885xxx，缓存到 JSON）
  4. 多线程并发拉取 d.10jqka.com.cn 的 K 线 JS 数据
  5. 解析、计算涨跌幅、批量写入 board_daily

用法：
    cd seele-backend
    source .venv/Scripts/activate
    python scripts/sync_board_daily.py

可选参数：
    --start     开始日期 YYYYMMDD，默认 2025-01-01
    --workers   并发线程数，默认 8
    --category  industry|concept，默认同步全部
"""
import argparse
import concurrent.futures
import json
import logging
import os
import re
import sys
import threading
import time
from datetime import date, datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import py_mini_racer
import requests
from akshare.datasets import get_ths_js

os.environ.setdefault("DEPLOY_ENV", "dev")

from app import crud, models, schemas
from app.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ========== THS 通用 ==========

_CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
_CONCEPT_MAP_CACHE = os.path.join(_CACHE_DIR, ".ths_concept_code_map.json")
_V_CODE: Optional[str] = None
_V_CODE_LOCK = threading.Lock()


def _get_v_code() -> str:
    """生成 THS 反爬 v_code（JS 挑战），全局复用"""
    global _V_CODE
    if _V_CODE is not None:
        return _V_CODE
    with _V_CODE_LOCK:
        if _V_CODE is not None:
            return _V_CODE
        js_code = py_mini_racer.MiniRacer()
        js_content = open(get_ths_js("ths.js"), encoding="utf-8").read()
        js_code.eval(js_content)
        _V_CODE = js_code.call("v")
        return _V_CODE


def _ths_get(url: str, timeout: int = 15, referer: str = "http://q.10jqka.com.cn") -> requests.Response:
    """带 v_code 和浏览器 UA 的 THS GET 请求"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": referer,
        "Cookie": f"v={_get_v_code()}",
    }
    return requests.get(url, headers=headers, timeout=timeout)


# ========== 板块列表同步 ==========


def _fetch_ths_boards(category: str) -> List[dict]:
    """从 akshare 获取 THS 板块名称→代码映射"""
    import akshare as ak

    if category == "industry":
        df = ak.stock_board_industry_name_ths()
    else:
        df = ak.stock_board_concept_name_ths()

    records = []
    # 注意 akshare 返回的列名可能是乱码（终端编码问题），用位置索引
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip()
        code = str(row.iloc[1]).strip()
        if name and code:
            # THS 行业代码以 88 开头，概念以 30 开头
            records.append(
                schemas.BoardInfoCreate(
                    code=code, name=name, category=category, source="ths"
                )
            )
    return records


def sync_board_list() -> tuple[Dict[str, str], Dict[str, str]]:
    """同步板块列表到 DB，返回 {code: name} 映射"""
    print("\n========== 第一步：同步板块列表 ==========")

    all_records: List[schemas.BoardInfoCreate] = []
    industry_map: Dict[str, str] = {}
    concept_map: Dict[str, str] = {}

    for cat in ("industry", "concept"):
        try:
            records = _fetch_ths_boards(cat)
            all_records.extend(records)
            m = {r.code: r.name for r in records}
            if cat == "industry":
                industry_map = m
            else:
                concept_map = m
            print(f"  [OK] THS {cat}: {len(records)} 个")
        except Exception as e:
            print(f"  [ERR] 获取{cat}失败: {e}")
            logger.warning("获取%s失败", cat, exc_info=True)

    if not all_records:
        print("  [WARN] 未获取到任何板块列表，退出")
        sys.exit(1)

    db = SessionLocal()
    try:
        result = crud.board_info_crud.upsert_batch(db, all_records)
        db.commit()
        print(f'  [OK] 写入 DB: 新增 {result["created"]}, 更新 {result["updated"]}')
    except Exception as e:
        db.rollback()
        print(f"  [ERR] 写入板块列表失败: {e}")
        raise
    finally:
        db.close()

    print(f"  [OK] 行业 {len(industry_map)} 个, 概念 {len(concept_map)} 个")
    return industry_map, concept_map


# ========== 概念 inner_code 映射 ==========


def _scrape_concept_inner_code(ths_code: str) -> Optional[str]:
    """从概念详情页抓取 inner_code（如 300008 → 885431）"""
    url = f"https://q.10jqka.com.cn/gn/detail/code/{ths_code}/"
    try:
        r = _ths_get(url, timeout=10)
        m = re.search(r'id="clid"[^>]*value\s*=\s*["\'](\d+)["\']', r.text)
        if m:
            return m.group(1)
    except Exception as e:
        logger.warning("抓取概念 %s inner_code 失败: %s", ths_code, e)
    return None


def build_concept_code_map(
    concept_map: Dict[str, str], force: bool = False
) -> Dict[str, str]:
    """构建 THS 概念代码 → inner_code 映射（300xxx → 885xxx）

    优先从本地缓存加载，缺失的远程抓取后更新缓存。
    """
    print("\n========== 第二步：构建概念 inner_code 映射 ==========")

    cached: Dict[str, str] = {}
    if not force and os.path.exists(_CONCEPT_MAP_CACHE):
        try:
            with open(_CONCEPT_MAP_CACHE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            print(f"  [OK] 加载缓存 {len(cached)} 个概念映射")
        except Exception as e:
            print(f"  [WARN] 缓存读取失败: {e}")

    ths_codes = set(concept_map.keys())
    missing = ths_codes - set(cached.keys())

    if not missing:
        print(f"  [OK] 全部 {len(ths_codes)} 个概念已在缓存中")
        return cached

    print(f"  需抓取 {len(missing)} / {len(ths_codes)} 个概念的 inner_code")

    from tqdm import tqdm

    results: Dict[str, Optional[str]] = {}
    lock = threading.Lock()

    def _scrape_one(code: str):
        inner = _scrape_concept_inner_code(code)
        with lock:
            results[code] = inner

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futs = {executor.submit(_scrape_one, code): code for code in missing}
        for fut in tqdm(
            concurrent.futures.as_completed(futs),
            total=len(missing),
            desc="抓取 inner_code",
            unit="个",
            ncols=80,
        ):
            fut.result()

    ok = 0
    for code, inner in results.items():
        if inner:
            cached[code] = inner
            ok += 1
        else:
            logger.warning("概念 %s(%s) 获取 inner_code 失败", code, concept_map.get(code, "?"))

    print(f"  [OK] 本次成功 {ok}, 失败 {len(missing) - ok}")
    print(f"  [OK] 缓存总计 {len(cached)} 个")

    try:
        with open(_CONCEPT_MAP_CACHE, "w", encoding="utf-8") as f:
            json.dump(cached, f, ensure_ascii=False, indent=2)
        print(f"  [OK] 缓存已保存: {_CONCEPT_MAP_CACHE}")
    except Exception as e:
        print(f"  [WARN] 缓存写入失败: {e}")

    return cached


# ========== 拉取日线数据 ==========


def _parse_ths_js_response(text: str) -> list[dict]:
    """解析 THS K 线 JS 响应

    格式: quotebridge_v4_line_bk_XXXX_01_YYYY({"data":"csv;data"})
    返回 [{trade_date, open, high, low, close, volume, amount}]
    """
    # 提取 JSON 部分
    m = re.search(r"\{.*\}", text)
    if not m:
        return []
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        return []

    csv_str = data.get("data", "")
    if not csv_str:
        return []

    records = []
    for line in csv_str.split(";"):
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 7:
            continue
        try:
            td = parts[0].strip()
            o = float(parts[1]) if parts[1] else None
            h = float(parts[2]) if parts[2] else None
            l = float(parts[3]) if parts[3] else None
            c = float(parts[4]) if parts[4] else None
            v = float(parts[5]) if parts[5] else None
            a = float(parts[6]) if parts[6] else None
            records.append(
                {
                    "trade_date": td,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": v,
                    "amount": a,
                }
            )
        except (ValueError, IndexError):
            continue

    return records


def _fetch_board_yearly(code: str, inner_code: str, year: int) -> list[dict]:
    """拉取单板块单年度 K 线数据"""
    url = f"https://d.10jqka.com.cn/v4/line/bk_{inner_code}/01/{year}.js"
    try:
        r = _ths_get(url, timeout=15, referer="http://q.10jqka.com.cn")
        if r.status_code != 200:
            return []
        return _parse_ths_js_response(r.text)
    except Exception as e:
        logger.warning("[%s] 拉取 %d 年失败: %s", code, year, e)
        return []


def _calc_pct_chg(records: list[dict]) -> list[dict]:
    """计算涨跌幅（基于前一天的收盘价）"""
    records_sorted = sorted(records, key=lambda x: x["trade_date"])
    prev_close = None
    for rec in records_sorted:
        if prev_close is not None and rec.get("close") is not None and prev_close != 0:
            rec["pct_chg"] = round((rec["close"] - prev_close) / prev_close * 100, 4)
        else:
            rec["pct_chg"] = None
        prev_close = rec.get("close")
    return records_sorted


def sync_board_daily(
    start_date: str,
    workers: int,
    industry_map: Dict[str, str],
    concept_map: Dict[str, str],
    concept_inner_map: Dict[str, str],
    category: str = None,
):
    """多线程同步板块日线"""
    db = SessionLocal()
    try:
        query = db.query(models.BoardInfo).filter(models.BoardInfo.source == "ths")
        if category == "industry":
            query = query.filter(models.BoardInfo.category == "industry")
        elif category == "concept":
            query = query.filter(models.BoardInfo.category == "concept")
        else:
            query = query.filter(models.BoardInfo.category.in_(["industry", "concept"]))
        boards = query.order_by(models.BoardInfo.category, models.BoardInfo.code).all()
    finally:
        db.close()

    if not boards:
        print("\n[ERR] DB 中没有找到 THS 板块数据，退出")
        return

    start_year = int(start_date[:4])
    current_year = date.today().year
    years = list(range(start_year, current_year + 1))

    print(f"\n========== 第三步：拉取日线数据 ==========")
    print(f"  板块数: {len(boards)} ({sum(1 for b in boards if b.category=='industry')} 行业 + {sum(1 for b in boards if b.category=='concept')} 概念)")
    print(f"  日期范围: {start_date} ~ {date.today().strftime('%Y%m%d')}")
    print(f"  并发数: {workers}")
    print(f"  年度: {years}")
    print()

    success = failed = total_records = 0
    results: List[dict] = []
    start_time = time.time()
    lock = threading.Lock()

    def flush_batch(batch):
        db_w = SessionLocal()
        try:
            crud.board_daily_crud.upsert_batch(db_w, batch)
            db_w.commit()
        except Exception as e:
            db_w.rollback()
            logger.error("批量写入 %d 条失败: %s", len(batch), e)
        finally:
            db_w.close()

    def process_board(board) -> int:
        nonlocal success, failed, total_records
        board_records = []

        # Determine inner_code for URL
        if board.category == "industry":
            inner = board.code  # 行业: 881xxx 直接使用
        else:
            inner = concept_inner_map.get(board.code)  # 概念: 300xxx → 885xxx
            if not inner:
                logger.warning("[%s] %s 无 inner_code，跳过", board.code, board.name)
                with lock:
                    failed += 1
                return 0

        for year in years:
            recs = _fetch_board_yearly(board.code, inner, year)
            board_records.extend(recs)

        if not board_records:
            with lock:
                failed += 1
            return 0

        # Calculate pct_chg from close prices (sorted by date)
        board_records = _calc_pct_chg(board_records)

        # Filter by start_date
        if start_date:
            board_records = [r for r in board_records if r["trade_date"] >= start_date]

        if not board_records:
            with lock:
                failed += 1
            return 0

        # Add code field
        for rec in board_records:
            rec["code"] = board.code

        with lock:
            results.extend(board_records)
            success += 1
            total_records += len(board_records)
            if len(results) >= 500:
                batch = results[:]
                results.clear()
                t = threading.Thread(target=flush_batch, args=(batch,), daemon=True)
                t.start()

        return len(board_records)

    from tqdm import tqdm

    pbar = tqdm(total=len(boards), desc="拉取板块", unit="个", ncols=80)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_board, b): b for b in boards}
        for future in concurrent.futures.as_completed(futures):
            future.result()
            pbar.update(1)
            with lock:
                pbar.set_postfix(success=success, failed=failed, records=total_records)

    pbar.close()

    # Final flush
    if results:
        flush_batch(results[:])
        results.clear()

    elapsed = time.time() - start_time
    print(f"\n========== 完成 ==========")
    print(f"  耗时: {elapsed:.1f} 秒")
    print(f"  成功: {success} 个板块")
    print(f"  失败: {failed} 个板块")
    print(f"  总记录数: {total_records} 条")
    if elapsed > 0 and total_records > 0:
        print(f"  平均: {total_records / elapsed:.0f} 条/秒")


# ========== 主流程 ==========


def main():
    parser = argparse.ArgumentParser(description="同步同花顺板块日线数据")
    parser.add_argument("--start", default="20250101", help="开始日期 (YYYYMMDD)，默认 20250101")
    parser.add_argument("--workers", type=int, default=8, help="并发线程数，默认 8")
    parser.add_argument("--category", choices=["industry", "concept"], default=None, help="板块类型，默认同步全部")
    parser.add_argument("--force-map", action="store_true", help="强制重新抓取概念 inner_code 映射")
    args = parser.parse_args()

    print(f"=== 同花顺板块日线同步脚本 ===")
    print(f"   启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   开始日期: {args.start}")
    print(f"   并发数:  {args.workers}")

    # Step 1: sync board list
    industry_map, concept_map = sync_board_list()

    # Step 2: build concept inner_code mapping
    concept_inner_map = build_concept_code_map(concept_map, force=args.force_map)

    # Step 3: sync daily data
    sync_board_daily(
        args.start,
        args.workers,
        industry_map,
        concept_map,
        concept_inner_map,
        args.category,
    )

    print("\n全部完成\n")


if __name__ == "__main__":
    main()
