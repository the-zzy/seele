"""
股票日线数据路由

包含 CRUD、按日期/股票/范围查询、分布统计、缩量榜等基础查询。
选股策略（倍量突破 / 趋势 / 震荡）已拆分至 routes.pickers。
"""

from collections import defaultdict
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.filters import apply_main_board_filter
from app.response import list_success, page_success, success
from app.schemas import StockDailyResponse

router = APIRouter(prefix="/stock/daily", tags=["股票日线数据"])


def _calc_consecutive_shrinking_days(volumes):
    """计算连续缩量天数（最近一天比前一天少算1天）"""
    if len(volumes) < 2:
        return 0
    consecutive = 0
    for i in range(len(volumes) - 1):
        if volumes[i] < volumes[i + 1]:
            consecutive += 1
        else:
            break
    return consecutive


def _parse_int(value, default: int) -> int:
    """容错地把 query 字符串转 int"""
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default


# 1.9 获取连续缩量的股票
@router.get("/shrinking-volume")
def get_shrinking_volume_stocks(
    min_days: Optional[str] = Query("1", description="最小连续缩量天数，默认 1"),
    max_days: Optional[str] = Query(None, description="最大连续缩量天数，默认不限制"),
    lookback: Optional[str] = Query("30", description="用于计算的历史交易日数量，默认 30"),
    page_num: Optional[str] = Query("1", description="页码，默认 1"),
    page_size: Optional[str] = Query("20", description="每页条数，默认 20"),
    db: Session = Depends(get_db),
):
    """获取最近连续缩量的股票列表（分页）"""
    min_days_val = max(_parse_int(min_days, 1), 1)
    max_days_val = _parse_int(max_days, 0) or None
    lookback_val = min(max(_parse_int(lookback, 30), 10), 120)
    page_num_val = max(_parse_int(page_num, 1), 1)
    page_size_val = min(max(_parse_int(page_size, 20), 1), 500)

    recent_dates = [
        d[0]
        for d in db.query(models.StockDaily.trade_date)
        .distinct()
        .order_by(models.StockDaily.trade_date.desc())
        .limit(lookback_val)
        .all()
    ]

    if len(recent_dates) < 2:
        return page_success(
            items=[],
            total=0,
            page_num=page_num_val,
            page_size=page_size_val,
            min_days=min_days_val,
            max_days=max_days_val,
        )

    recent_dates = sorted(recent_dates)

    raw_rows = (
        db.query(models.StockDaily)
        .filter(models.StockDaily.trade_date.in_(recent_dates))
        .all()
    )

    symbol_data = defaultdict(list)
    for row in raw_rows:
        symbol_data[row.symbol].append(row)

    symbols = list(symbol_data.keys())
    name_map = {
        row.symbol: row.name
        for row in db.query(models.StockBasic.symbol, models.StockBasic.name)
        .filter(models.StockBasic.symbol.in_(symbols))
        .all()
    }

    result_list = []
    for symbol, items in symbol_data.items():
        items_sorted = sorted(items, key=lambda x: x.trade_date, reverse=True)
        volumes = [item.volume for item in items_sorted if item.volume is not None]
        if len(volumes) < 2:
            continue

        consecutive_days = _calc_consecutive_shrinking_days(volumes)
        if consecutive_days < min_days_val:
            continue
        if max_days_val is not None and consecutive_days > max_days_val:
            continue

        latest = items_sorted[0]
        result_list.append({
            "symbol": latest.symbol,
            "stock_name": name_map.get(latest.symbol, ""),
            "trade_date": str(latest.trade_date),
            "open": latest.open,
            "high": latest.high,
            "low": latest.low,
            "close": latest.close,
            "price_change": latest.price_change,
            "pct_chg": latest.pct_chg,
            "amplitude": latest.amplitude,
            "volume": latest.volume,
            "amount": latest.amount,
            "turnover": latest.turnover,
            "consecutive_days": consecutive_days,
        })

    result_list.sort(key=lambda x: x["consecutive_days"], reverse=True)

    total = len(result_list)
    start = (page_num_val - 1) * page_size_val
    end = start + page_size_val

    return page_success(
        items=result_list[start:end],
        total=total,
        page_num=page_num_val,
        page_size=page_size_val,
        min_days=min_days_val,
        max_days=max_days_val,
    )


# 2.0 统计日期范围内每天涨幅超过阈值的股票占比（柱状图）
@router.get("/pct-chg-distribution")
def get_pct_chg_distribution(
    start_date: str = Query(..., description="开始日期，格式 2026-04-01 或 20260401"),
    end_date: str = Query(..., description="结束日期，格式 2026-04-30 或 20260430"),
    threshold: float = Query(2.0, description="涨幅阈值百分比，默认 2.0"),
    amount_ma5_min: Optional[float] = Query(200000000.0, description="5日平均成交额最小值，默认2亿"),
    amount_ma10_min: Optional[float] = Query(200000000.0, description="10日平均成交额最小值，默认2亿"),
    turnover_ma5_min: Optional[float] = Query(2.0, description="5日平均换手率最小值，默认2%"),
    turnover_ma10_min: Optional[float] = Query(2.0, description="10日平均换手率最小值，默认2%"),
    db: Session = Depends(get_db),
):
    """统计日期范围内每天最大涨幅超阈值的股票占比"""
    start = start_date.replace("-", "")
    end = end_date.replace("-", "")

    range_dates = [
        d[0]
        for d in db.query(models.StockDaily.trade_date)
        .filter(
            models.StockDaily.trade_date >= start,
            models.StockDaily.trade_date <= end,
        )
        .distinct()
        .order_by(models.StockDaily.trade_date.asc())
        .all()
    ]

    if not range_dates:
        return success({
            "start_date": start_date,
            "end_date": end_date,
            "threshold": threshold,
            "list": [],
        })

    extra_dates = [
        d[0]
        for d in db.query(models.StockDaily.trade_date)
        .filter(models.StockDaily.trade_date < start)
        .distinct()
        .order_by(models.StockDaily.trade_date.desc())
        .limit(10)
        .all()
    ]
    all_dates = sorted(set(extra_dates + range_dates))

    base_q = (
        db.query(
            models.StockDaily.symbol,
            models.StockDaily.trade_date,
            models.StockDaily.open,
            models.StockDaily.high,
        )
        .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
    )
    raw_rows = (
        apply_main_board_filter(base_q)
        .filter(
            models.StockDaily.trade_date.in_(all_dates),
            models.StockDaily.open > 0,
        )
        .all()
    )

    symbol_gains = defaultdict(dict)
    for symbol, trade_date, open_p, high in raw_rows:
        symbol_gains[symbol][trade_date] = (high - open_p) / open_p * 100

    # 按日期构建满足指标过滤条件的股票集合
    has_indicator_filter = any([
        amount_ma5_min is not None,
        amount_ma10_min is not None,
        turnover_ma5_min is not None,
        turnover_ma10_min is not None,
    ])
    valid_symbols_by_date = {}
    if has_indicator_filter:
        indicator_q = db.query(
            models.StockDailyIndicator.symbol,
            models.StockDailyIndicator.trade_date,
        ).filter(
            models.StockDailyIndicator.trade_date.in_(range_dates)
        )
        if amount_ma5_min is not None:
            indicator_q = indicator_q.filter(
                models.StockDailyIndicator.amount_ma5 >= amount_ma5_min
            )
        if amount_ma10_min is not None:
            indicator_q = indicator_q.filter(
                models.StockDailyIndicator.amount_ma10 >= amount_ma10_min
            )
        if turnover_ma5_min is not None:
            indicator_q = indicator_q.filter(
                models.StockDailyIndicator.turnover_ma5 >= turnover_ma5_min
            )
        if turnover_ma10_min is not None:
            indicator_q = indicator_q.filter(
                models.StockDailyIndicator.turnover_ma10 >= turnover_ma10_min
            )
        for symbol, trade_date in indicator_q.all():
            if trade_date not in valid_symbols_by_date:
                valid_symbols_by_date[trade_date] = set()
            valid_symbols_by_date[trade_date].add(symbol)

    exclude_by_date = defaultdict(set)
    date_index = {d: i for i, d in enumerate(all_dates)}
    for target_date in range_dates:
        idx = date_index[target_date]
        window_start = max(0, idx - 9)
        window_dates = all_dates[window_start:idx + 1]
        if len(window_dates) < 10:
            continue
        for symbol, gains in symbol_gains.items():
            if not all(d in gains for d in window_dates):
                continue
            if all(gains[d] < threshold for d in window_dates):
                exclude_by_date[target_date].add(symbol)

    data_list = []
    for target_date in range_dates:
        total = 0
        matched = 0
        excluded = exclude_by_date[target_date]
        valid_set = valid_symbols_by_date.get(target_date)
        for symbol, gains in symbol_gains.items():
            if target_date not in gains or symbol in excluded:
                continue
            if valid_set is not None and symbol not in valid_set:
                continue
            total += 1
            if gains[target_date] >= threshold:
                matched += 1
        matched_percent = round(matched / total * 100, 2) if total else 0.0
        data_list.append({
            "trade_date": str(target_date),
            "total_stocks": total,
            "matched_count": matched,
            "matched_percent": matched_percent,
        })

    return success({
        "start_date": start_date,
        "end_date": end_date,
        "threshold": threshold,
        "list": data_list,
    })


# 2.1 分页查询日线数据
@router.post("/page")
def post_stock_daily_page(
    query: schemas.StockDailyQuery,
    db: Session = Depends(get_db),
):
    """分页查询日线数据 - 仅查询沪深主板且非ST股票"""
    q = db.query(models.StockDaily).join(
        models.StockBasic,
        models.StockDaily.symbol == models.StockBasic.symbol,
    )
    q = apply_main_board_filter(q)

    if query.symbol:
        q = q.filter(models.StockDaily.symbol == query.symbol)
    if query.start_date:
        q = q.filter(models.StockDaily.trade_date >= query.start_date)
    if query.end_date:
        q = q.filter(models.StockDaily.trade_date <= query.end_date)

    total = q.with_entities(func.count(models.StockDaily.id)).scalar()
    list_data = (
        q.order_by(models.StockDaily.trade_date.desc())
        .offset((query.page_num - 1) * query.page_size)
        .limit(query.page_size)
        .all()
    )

    return page_success(
        items=[StockDailyResponse.model_validate(item) for item in list_data],
        total=total,
        page_num=query.page_num,
        page_size=query.page_size,
    )


# 2.3 根据股票代码查询全部日线（含指标）
@router.get("/symbol/{symbol}")
def get_stock_daily_by_symbol(
    symbol: str,
    db: Session = Depends(get_db),
):
    """根据股票代码查询全部日线 - 仅查询沪深主板且非ST股票，联查指标表"""
    basic = (
        apply_main_board_filter(db.query(models.StockBasic))
        .filter(models.StockBasic.symbol == symbol)
        .first()
    )
    if not basic:
        raise HTTPException(status_code=404, detail="股票不存在或非主板/ST股票")

    results = (
        db.query(
            models.StockDaily,
            models.StockDailyIndicator.ma5,
            models.StockDailyIndicator.ma10,
            models.StockDailyIndicator.ma20,
            models.StockDailyIndicator.ma30,
            models.StockDailyIndicator.ma60,
            models.StockDailyIndicator.vol_ma5,
            models.StockDailyIndicator.vol_ma10,
            models.StockDailyIndicator.turnover_ma5,
            models.StockDailyIndicator.turnover_ma10,
        )
        .outerjoin(
            models.StockDailyIndicator,
            and_(
                models.StockDaily.symbol == models.StockDailyIndicator.symbol,
                models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
            ),
        )
        .filter(models.StockDaily.symbol == symbol)
        .order_by(models.StockDaily.trade_date.desc())
        .all()
    )

    data_list = []
    for row in results:
        daily = row[0]
        data_list.append({
            "id": daily.id,
            "trade_date": str(daily.trade_date),
            "symbol": daily.symbol,
            "open": daily.open,
            "high": daily.high,
            "low": daily.low,
            "close": daily.close,
            "volume": daily.volume,
            "amount": daily.amount,
            "amplitude": daily.amplitude,
            "pct_chg": daily.pct_chg,
            "price_change": daily.price_change,
            "turnover": daily.turnover,
            "ma5": row[1],
            "ma10": row[2],
            "ma20": row[3],
            "ma30": row[4],
            "ma60": row[5],
            "vol_ma5": row[6],
            "vol_ma10": row[7],
            "turnover_ma5": row[8],
            "turnover_ma10": row[9],
        })

    return list_success(data_list)


# 2.4 批量查询日线数据
@router.post("/symbols")
def post_stock_daily_symbols(
    symbols: List[str],
    db: Session = Depends(get_db),
):
    """批量查询日线数据 - 仅查询沪深主板且非ST股票"""
    basics = (
        apply_main_board_filter(db.query(models.StockBasic.symbol))
        .filter(models.StockBasic.symbol.in_(symbols))
        .all()
    )
    valid_symbols = [b[0] for b in basics]
    objs = crud.stock_daily_crud.get_batch(db, valid_symbols)
    return list_success([StockDailyResponse.model_validate(item) for item in objs])


# 2.5 根据日期范围查询（含指标）
@router.get("/symbol/{symbol}/range")
def get_stock_daily_by_symbol_range(
    symbol: str,
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: Session = Depends(get_db),
):
    """根据日期范围查询 - 仅查询沪深主板且非ST股票，联查指标表"""
    basic = (
        apply_main_board_filter(db.query(models.StockBasic))
        .filter(models.StockBasic.symbol == symbol)
        .first()
    )
    if not basic:
        raise HTTPException(status_code=404, detail="股票不存在或非主板/ST股票")

    results = (
        db.query(
            models.StockDaily,
            models.StockDailyIndicator.ma5,
            models.StockDailyIndicator.ma10,
            models.StockDailyIndicator.ma20,
            models.StockDailyIndicator.ma30,
            models.StockDailyIndicator.ma60,
            models.StockDailyIndicator.vol_ma5,
            models.StockDailyIndicator.vol_ma10,
            models.StockDailyIndicator.turnover_ma5,
            models.StockDailyIndicator.turnover_ma10,
        )
        .outerjoin(
            models.StockDailyIndicator,
            and_(
                models.StockDaily.symbol == models.StockDailyIndicator.symbol,
                models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
            ),
        )
        .filter(
            and_(
                models.StockDaily.symbol == symbol,
                models.StockDaily.trade_date >= start_date,
                models.StockDaily.trade_date <= end_date,
            )
        )
        .order_by(models.StockDaily.trade_date.asc())
        .all()
    )

    data_list = []
    for row in results:
        daily = row[0]
        data_list.append({
            "id": daily.id,
            "trade_date": str(daily.trade_date),
            "symbol": daily.symbol,
            "open": daily.open,
            "high": daily.high,
            "low": daily.low,
            "close": daily.close,
            "volume": daily.volume,
            "amount": daily.amount,
            "amplitude": daily.amplitude,
            "pct_chg": daily.pct_chg,
            "price_change": daily.price_change,
            "turnover": daily.turnover,
            "ma5": row[1],
            "ma10": row[2],
            "ma20": row[3],
            "ma30": row[4],
            "ma60": row[5],
            "vol_ma5": row[6],
            "vol_ma10": row[7],
            "turnover_ma5": row[8],
            "turnover_ma10": row[9],
        })

    return list_success(data_list)


# 2.6 根据交易日期查询
@router.get("/date/{trade_date}")
def get_stock_daily_by_date(
    trade_date: str,
    db: Session = Depends(get_db),
):
    """根据交易日期查询 - 仅查询沪深主板且非ST股票"""
    formatted_date = trade_date.replace("-", "")
    q = db.query(models.StockDaily).join(
        models.StockBasic,
        models.StockDaily.symbol == models.StockBasic.symbol,
    )
    objs = (
        apply_main_board_filter(q)
        .filter(models.StockDaily.trade_date == formatted_date)
        .all()
    )
    return list_success([StockDailyResponse.model_validate(item) for item in objs])


# 2.6.1 根据交易日期获取全部A股数据（关联basic表及指标表）— 服务端分页
@router.get("/date/{trade_date}/all")
def get_stock_daily_all_by_date(
    trade_date: str,
    exclude_st: bool = Query(False, description="是否过滤ST股票"),
    exclude_cyb: bool = Query(False, description="是否过滤创业板"),
    exclude_kcb: bool = Query(False, description="是否过滤科创板"),
    exclude_bse: bool = Query(False, description="是否过滤北交所"),
    symbol: Optional[str] = Query(None, description="代码或名称模糊搜索"),
    min_pct_chg: Optional[float] = Query(None, description="最小涨幅百分比过滤"),
    sort_field: str = Query("symbol", description="排序字段"),
    sort_order: str = Query("asc", description="排序方向 asc/desc"),
    page_num: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页条数"),
    db: Session = Depends(get_db),
):
    """根据交易日期分页获取A股数据（关联 stock_basic 及 stock_daily_indicator）"""
    formatted_date = trade_date.replace("-", "")

    q = (
        db.query(
            models.StockDaily,
            models.StockBasic.name.label("stock_name"),
            models.StockBasic.industry,
            models.StockBasic.market,
            models.StockBasic.area,
            models.StockDailyIndicator.ma5,
            models.StockDailyIndicator.ma10,
            models.StockDailyIndicator.ma20,
            models.StockDailyIndicator.ma30,
            models.StockDailyIndicator.ma60,
            models.StockDailyIndicator.vol_ma5,
            models.StockDailyIndicator.vol_ma10,
            models.StockDailyIndicator.turnover_ma5,
            models.StockDailyIndicator.turnover_ma10,
        )
        .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
        .outerjoin(
            models.StockDailyIndicator,
            and_(
                models.StockDaily.symbol == models.StockDailyIndicator.symbol,
                models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
            ),
        )
    )
    q = apply_main_board_filter(q).filter(
        models.StockDaily.trade_date == formatted_date,
    )

    if exclude_st:
        q = q.filter(~models.StockBasic.name.like('%ST%'))
    if exclude_cyb:
        q = q.filter(
            models.StockBasic.symbol.notlike("300%"),
            models.StockBasic.symbol.notlike("301%"),
        )
    if exclude_kcb:
        q = q.filter(
            models.StockBasic.symbol.notlike("688%"),
            models.StockBasic.symbol.notlike("689%"),
        )
    if exclude_bse:
        q = q.filter(
            models.StockBasic.symbol.notlike("4%"),
            models.StockBasic.symbol.notlike("8%"),
        )
    if symbol:
        like_pattern = f"%{symbol}%"
        q = q.filter(
            or_(
                models.StockDaily.symbol.like(like_pattern),
                models.StockBasic.name.like(like_pattern),
            )
        )
    if min_pct_chg is not None:
        q = q.filter(models.StockDaily.pct_chg > min_pct_chg)

    # 排序映射
    sort_column_map = {
        'symbol': models.StockDaily.symbol,
        'stock_name': models.StockBasic.name,
        'open': models.StockDaily.open,
        'high': models.StockDaily.high,
        'low': models.StockDaily.low,
        'close': models.StockDaily.close,
        'volume': models.StockDaily.volume,
        'amount': models.StockDaily.amount,
        'amplitude': models.StockDaily.amplitude,
        'pct_chg': models.StockDaily.pct_chg,
        'price_change': models.StockDaily.price_change,
        'turnover': models.StockDaily.turnover,
        'ma5': models.StockDailyIndicator.ma5,
        'ma10': models.StockDailyIndicator.ma10,
        'ma20': models.StockDailyIndicator.ma20,
        'ma30': models.StockDailyIndicator.ma30,
        'ma60': models.StockDailyIndicator.ma60,
        'vol_ma5': models.StockDailyIndicator.vol_ma5,
        'vol_ma10': models.StockDailyIndicator.vol_ma10,
        'turnover_ma5': models.StockDailyIndicator.turnover_ma5,
        'turnover_ma10': models.StockDailyIndicator.turnover_ma10,
    }
    sort_column = sort_column_map.get(sort_field, models.StockDaily.symbol)
    if sort_order == 'desc':
        q = q.order_by(sort_column.desc())
    else:
        q = q.order_by(sort_column.asc())

    # 总数
    total = q.with_entities(func.count(models.StockDaily.id)).scalar() or 0

    # 分页
    results = (
        q.offset((page_num - 1) * page_size)
        .limit(page_size)
        .all()
    )

    data_list = []
    for (
        daily,
        stock_name,
        industry,
        market,
        area,
        ma5,
        ma10,
        ma20,
        ma30,
        ma60,
        vol_ma5,
        vol_ma10,
        turnover_ma5,
        turnover_ma10,
    ) in results:
        data_list.append({
            'id': daily.id,
            'trade_date': str(daily.trade_date),
            'symbol': daily.symbol,
            'stock_name': stock_name or '',
            'industry': industry or '',
            'market': market or '',
            'area': area or '',
            'open': daily.open,
            'high': daily.high,
            'low': daily.low,
            'close': daily.close,
            'volume': daily.volume,
            'amount': daily.amount,
            'amplitude': daily.amplitude,
            'pct_chg': daily.pct_chg,
            'price_change': daily.price_change,
            'turnover': daily.turnover,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma30': ma30,
            'ma60': ma60,
            'vol_ma5': vol_ma5,
            'vol_ma10': vol_ma10,
            'turnover_ma5': turnover_ma5,
            'turnover_ma10': turnover_ma10,
        })

    return page_success(
        items=data_list,
        total=total,
        page_num=page_num,
        page_size=page_size,
        trade_date=trade_date,
    )


# 2.7 获取交易日列表
@router.get("/trade-dates")
def get_stock_daily_trade_dates(
    db: Session = Depends(get_db),
):
    """获取交易日列表"""
    dates = crud.stock_daily_crud.get_trade_dates(db)
    return list_success([str(d) for d in dates])


# 2.8 新增日线数据
@router.post("")
def post_stock_daily(
    obj_in: schemas.StockDailyCreate,
    db: Session = Depends(get_db),
):
    """新增日线数据"""
    obj = crud.stock_daily_crud.upsert(db, obj_in)
    return success(StockDailyResponse.model_validate(obj))


# 2.9 批量新增
@router.post("/batch")
def post_stock_daily_batch(
    obj_list: List[schemas.StockDailyCreate],
    db: Session = Depends(get_db),
):
    """批量新增"""
    count = crud.stock_daily_crud.create_batch(db, obj_list)
    return success(f"成功创建 {count} 条数据")


# 2.10 更新日线数据
@router.put("")
def put_stock_daily(
    obj_in: schemas.StockDailyUpdate,
    db: Session = Depends(get_db),
):
    """更新日线数据"""
    obj = crud.stock_daily_crud.update(db, obj_in)
    if not obj:
        raise HTTPException(status_code=404, detail="日线数据不存在")
    return success(StockDailyResponse.model_validate(obj))


# 2.11 根据日期和涨幅筛选股票
@router.get("/top-pct-chg")
def get_stock_daily_top_pct_chg(
    trade_date: str = Query(..., description="交易日期，格式 2026-04-14 或 20260412"),
    min_pct_chg: float = Query(5.0, description="最小涨幅百分比"),
    db: Session = Depends(get_db),
):
    """获取指定日期涨幅超过固定百分比的股票数据"""
    formatted_date = trade_date.replace("-", "")

    total_stocks = (
        apply_main_board_filter(db.query(func.count(models.StockBasic.id))).scalar() or 0
    )

    q = (
        db.query(
            models.StockDaily,
            models.StockBasic.name.label("stock_name"),
            models.StockBasic.industry,
            models.StockBasic.market,
            models.StockBasic.area,
        )
        .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
    )
    results = (
        apply_main_board_filter(q)
        .filter(
            models.StockDaily.trade_date == formatted_date,
            models.StockDaily.pct_chg >= min_pct_chg,
        )
        .order_by(models.StockDaily.pct_chg.desc())
        .all()
    )

    matched_count = len(results)
    matched_percent = round(matched_count / total_stocks * 100, 2) if total_stocks else 0.0

    data_list = [
        {
            "id": daily.id,
            "trade_date": str(daily.trade_date),
            "symbol": daily.symbol,
            "stock_name": stock_name or "",
            "industry": industry or "",
            "market": market or "",
            "area": area or "",
            "open": daily.open,
            "high": daily.high,
            "low": daily.low,
            "close": daily.close,
            "volume": daily.volume,
            "amount": daily.amount,
            "amplitude": daily.amplitude,
            "pct_chg": daily.pct_chg,
            "price_change": daily.price_change,
            "turnover": daily.turnover,
        }
        for daily, stock_name, industry, market, area in results
    ]

    return success({
        "trade_date": trade_date,
        "min_pct_chg": min_pct_chg,
        "total_stocks": total_stocks,
        "matched_count": matched_count,
        "matched_percent": matched_percent,
        "list": data_list,
    })


# 2.2 根据ID查询 (放在后面避免路由冲突)
@router.get("/{id}")
def get_stock_daily_by_id(
    id: int,
    db: Session = Depends(get_db),
):
    """根据ID查询"""
    obj = crud.stock_daily_crud.get_by_id(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="日线数据不存在")
    return success(StockDailyResponse.model_validate(obj))


# 2.11 删除日线数据
@router.delete("/{id}")
def delete_stock_daily(
    id: int,
    db: Session = Depends(get_db),
):
    """删除日线数据"""
    deleted = crud.stock_daily_crud.delete(db, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="日线数据不存在")
    return success(None)
