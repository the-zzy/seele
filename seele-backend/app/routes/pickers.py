"""
选股策略路由

将三种选股策略 endpoint（倍量突破 / 趋势 / 震荡）从 stock_daily.py
拆分到这里，并复用 indicators.py 中的可参数化 CTE 构建函数。
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import indicators, schemas
from app.database import get_db
from app.filters import build_exclude_sql
from app.response import success

router = APIRouter(prefix="/stock/daily", tags=["股票选股策略"])


def _get_start_date(trade_date: str, days: int = 15) -> str:
    """计算预筛选起始日期（trade_date 前 days 天）"""
    trade_date_obj = datetime.strptime(trade_date.replace("-", ""), "%Y%m%d")
    start_date_obj = trade_date_obj - timedelta(days=days)
    return start_date_obj.strftime("%Y%m%d")


# 2.12 倍量突破选股
@router.post("/breakout-picker")
def post_breakout_picker(
    query: schemas.BreakoutPickerQuery,
    db: Session = Depends(get_db),
):
    """倍量突破选股 - 数据库层完成 MA250、平台突破、倍量计算"""
    trade_date = query.trade_date.replace("-", "")
    page_size = min(query.page_size, 100)
    exclude_sql = build_exclude_sql(query)

    base_cte = f"""
    target_stocks AS (
        SELECT sd.symbol
        FROM stock_daily sd
        JOIN stock_basic sb ON sd.symbol = sb.symbol
        WHERE sd.trade_date = :trade_date
            AND sd.close > sd.open
            AND sd.pct_chg >= :min_pct_chg
            AND sd.pct_chg <= :max_pct_chg
            AND sd.turnover >= :min_turnover
            AND sd.amount >= :min_amount
            AND sb.market = '主板'
{exclude_sql}
    ),
    history AS (
        SELECT
            symbol,
            close,
            high,
            volume,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
        FROM stock_daily
        WHERE symbol IN (SELECT symbol FROM target_stocks)
            AND trade_date < :trade_date
    ),
    stats AS (
        SELECT
            symbol,
            AVG(CASE WHEN rn <= 250 THEN close END) AS ma250,
            MAX(CASE WHEN rn <= 60 THEN high END) AS high_60,
            AVG(CASE WHEN rn <= 20 THEN volume END) AS avg_volume_20
        FROM history
        WHERE rn <= 250
        GROUP BY symbol
        HAVING COUNT(*) >= 250
    )"""

    count_sql = f"""
    WITH {base_cte}
    SELECT COUNT(*)
    FROM target_stocks ts
    JOIN stats s ON ts.symbol = s.symbol
    JOIN stock_daily sd ON sd.symbol = ts.symbol AND sd.trade_date = :trade_date
    WHERE sd.close > s.ma250
        AND sd.close >= s.high_60
        AND sd.volume >= s.avg_volume_20 * 2
    """

    list_sql = f"""
    WITH target_stocks AS (
        SELECT
            sd.symbol,
            sb.name,
            sd.open,
            sd.close,
            sd.high,
            sd.low,
            sd.volume,
            sd.amount,
            sd.turnover,
            sd.pct_chg
        FROM stock_daily sd
        JOIN stock_basic sb ON sd.symbol = sb.symbol
        WHERE sd.trade_date = :trade_date
            AND sd.close > sd.open
            AND sd.pct_chg >= :min_pct_chg
            AND sd.pct_chg <= :max_pct_chg
            AND sd.turnover >= :min_turnover
            AND sd.amount >= :min_amount
            AND sb.market = '主板'
{exclude_sql}
    ),
    history AS (
        SELECT
            symbol,
            close,
            high,
            volume,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
        FROM stock_daily
        WHERE symbol IN (SELECT symbol FROM target_stocks)
            AND trade_date < :trade_date
    ),
    stats AS (
        SELECT
            symbol,
            AVG(CASE WHEN rn <= 250 THEN close END) AS ma250,
            MAX(CASE WHEN rn <= 60 THEN high END) AS high_60,
            AVG(CASE WHEN rn <= 20 THEN volume END) AS avg_volume_20
        FROM history
        WHERE rn <= 250
        GROUP BY symbol
        HAVING COUNT(*) >= 250
    ),
    post_signal AS (
        SELECT
            symbol,
            close AS latest_close,
            trade_date AS latest_date,
            MAX(high) OVER (PARTITION BY symbol) AS max_high_since,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
        FROM stock_daily
        WHERE symbol IN (SELECT symbol FROM target_stocks)
            AND trade_date > :trade_date
    )
    SELECT
        ts.symbol,
        ts.name,
        ts.open,
        ts.close,
        ts.high,
        ts.low,
        ts.volume,
        ts.amount,
        ts.turnover,
        ts.pct_chg,
        s.ma250,
        s.high_60,
        s.avg_volume_20,
        ts.close > s.ma250 AS above_ma250,
        ts.close >= s.high_60 AS is_breakout,
        ts.volume >= s.avg_volume_20 * 2 AS is_double_volume,
        (ps.latest_close - ts.close) / ts.close * 100 AS current_return,
        (ps.max_high_since - ts.close) / ts.close * 100 AS max_return,
        ps.latest_date
    FROM target_stocks ts
    JOIN stats s ON ts.symbol = s.symbol
    LEFT JOIN post_signal ps ON ts.symbol = ps.symbol AND ps.rn = 1
    WHERE ts.close > s.ma250
        AND ts.close >= s.high_60
        AND ts.volume >= s.avg_volume_20 * 2
    ORDER BY ts.pct_chg DESC
    LIMIT :limit OFFSET :offset
    """

    params = {
        "trade_date": trade_date,
        "min_pct_chg": query.min_pct_chg,
        "max_pct_chg": query.max_pct_chg,
        "min_turnover": query.min_turnover,
        "min_amount": query.min_amount,
        "limit": page_size,
        "offset": (query.page_num - 1) * page_size,
    }

    total_result = db.execute(text(count_sql), params).scalar() or 0
    rows = db.execute(text(list_sql), params).all()

    result_list = []
    for row in rows:
        signals = []
        if row.above_ma250:
            signals.append("站上年线")
        if row.is_breakout:
            signals.append("突破平台")
        if row.is_double_volume:
            signals.append("倍量")

        result_list.append({
            "symbol": row.symbol,
            "name": row.name,
            "trade_date": query.trade_date,
            "open": row.open,
            "close": row.close,
            "high": row.high,
            "low": row.low,
            "volume": row.volume,
            "amount": row.amount,
            "turnover": row.turnover,
            "pct_chg": row.pct_chg,
            "ma250": round(row.ma250, 4) if row.ma250 is not None else None,
            "high_60": round(row.high_60, 4) if row.high_60 is not None else None,
            "avg_volume_20": round(row.avg_volume_20, 2) if row.avg_volume_20 is not None else None,
            "above_ma250": bool(row.above_ma250),
            "is_breakout": bool(row.is_breakout),
            "is_double_volume": bool(row.is_double_volume),
            "current_return": round(row.current_return, 2) if row.current_return is not None else None,
            "max_return": round(row.max_return, 2) if row.max_return is not None else None,
            "latest_date": row.latest_date,
            "signals": " | ".join(signals),
        })

    return success({
        "trade_date": query.trade_date,
        "total": total_result,
        "page_num": query.page_num,
        "page_size": page_size,
        "list": result_list,
    })


# 2.13 趋势选股
@router.post("/trend-picker")
def post_trend_picker(
    query: schemas.TrendPickerQuery,
    db: Session = Depends(get_db),
):
    """趋势选股 - 均线多头 / MACD金叉 / RSI健康 / 放量上涨"""
    trade_date = query.trade_date.replace("-", "")
    page_size = min(query.page_size, 100)
    start_date = _get_start_date(trade_date)
    exclude_sql = build_exclude_sql(query)

    with_clause = indicators.assemble_with(
        indicators.build_pre_filter_cte(exclude_sql=exclude_sql),
        indicators.build_latest_data_cte(),
        indicators.build_ma_cte(periods=(5, 10, 20, 60)),
        indicators.build_macd_cte(),
        indicators.build_rsi_cte(period=14),
        indicators.build_volume_avg_cte(period=20),
    )

    where_conditions = [
        "ld.pct_chg >= :min_pct_chg",
        "ld.pct_chg <= :max_pct_chg",
        "ld.turnover >= :min_turnover",
        "rc.rsi_14 >= :rsi_min",
        "rc.rsi_14 <= :rsi_max",
        "ld.volume / vc.avg_volume_20 >= :volume_ratio",
    ]
    if query.ma_alignment:
        where_conditions.append("mc.ma5 > mc.ma10 AND mc.ma10 > mc.ma20 AND mc.ma20 > mc.ma60")
    if query.macd_golden_cross:
        where_conditions.append("mc2.dif > 0 AND mc2.dif_prev <= 0")

    where_sql = "\n        AND ".join(where_conditions)

    sort_field = query.sort_field if query.sort_field in {
        "pct_chg", "volume_ratio", "rsi_14", "ma5", "ma10", "ma20", "ma60",
        "turnover", "amount", "symbol", "name",
    } else "pct_chg"
    sort_order = "DESC" if query.sort_order.lower() == "desc" else "ASC"

    count_sql = f"""
    {with_clause}
    SELECT COUNT(*)
    FROM latest_data ld
    JOIN pre_filter pf ON ld.symbol = pf.symbol
    JOIN ma_calc mc ON ld.symbol = mc.symbol
    JOIN macd_calc mc2 ON ld.symbol = mc2.symbol
    LEFT JOIN rsi_calc rc ON ld.symbol = rc.symbol
    LEFT JOIN volume_calc vc ON ld.symbol = vc.symbol
    WHERE {where_sql}
    """

    params = {
        "trade_date": trade_date,
        "start_date": start_date,
        "min_amount": query.min_amount,
        "min_pct_chg": query.min_pct_chg,
        "max_pct_chg": query.max_pct_chg,
        "min_turnover": query.min_turnover,
        "rsi_min": query.rsi_min,
        "rsi_max": query.rsi_max,
        "volume_ratio": query.volume_ratio,
    }

    total_result = db.execute(text(count_sql), params).scalar() or 0

    select_columns = """
        ld.symbol,
        pf.name,
        pf.industry,
        ld.trade_date,
        ld.open,
        ld.close,
        ld.high,
        ld.low,
        ld.volume,
        ld.amount,
        ld.turnover,
        ld.pct_chg,
        mc.ma5,
        mc.ma10,
        mc.ma20,
        mc.ma60,
        mc2.dif AS macd_dif,
        mc2.dif * 0.8 AS macd_dea,
        rc.rsi_14,
        vc.avg_volume_20,
        ld.volume / vc.avg_volume_20 AS volume_ratio
    """

    if sort_field == "score":
        list_sql = f"""
        {with_clause}
        SELECT {select_columns}
        FROM latest_data ld
        JOIN pre_filter pf ON ld.symbol = pf.symbol
        JOIN ma_calc mc ON ld.symbol = mc.symbol
        JOIN macd_calc mc2 ON ld.symbol = mc2.symbol
        LEFT JOIN rsi_calc rc ON ld.symbol = rc.symbol
        LEFT JOIN volume_calc vc ON ld.symbol = vc.symbol
        WHERE {where_sql}
        """
    else:
        list_sql = f"""
        {with_clause}
        SELECT {select_columns}
        FROM latest_data ld
        JOIN pre_filter pf ON ld.symbol = pf.symbol
        JOIN ma_calc mc ON ld.symbol = mc.symbol
        JOIN macd_calc mc2 ON ld.symbol = mc2.symbol
        LEFT JOIN rsi_calc rc ON ld.symbol = rc.symbol
        LEFT JOIN volume_calc vc ON ld.symbol = vc.symbol
        WHERE {where_sql}
        ORDER BY {sort_field} {sort_order}
        LIMIT :limit OFFSET :offset
        """
        params["limit"] = page_size
        params["offset"] = (query.page_num - 1) * page_size

    rows = db.execute(text(list_sql), params).all()

    result_list = []
    for row in rows:
        score, signals = indicators.calculate_trend_score(
            row.ma5 or 0, row.ma10 or 0, row.ma20 or 0, row.ma60 or 0,
            row.macd_dif or 0, row.macd_dea or 0,
            row.rsi_14 or 50, row.volume_ratio or 1,
        )
        result_list.append({
            "symbol": row.symbol,
            "name": row.name,
            "industry": row.industry,
            "trade_date": query.trade_date,
            "open": row.open,
            "close": row.close,
            "high": row.high,
            "low": row.low,
            "volume": row.volume,
            "amount": row.amount,
            "turnover": row.turnover,
            "pct_chg": row.pct_chg,
            "ma5": round(row.ma5, 4) if row.ma5 else None,
            "ma10": round(row.ma10, 4) if row.ma10 else None,
            "ma20": round(row.ma20, 4) if row.ma20 else None,
            "ma60": round(row.ma60, 4) if row.ma60 else None,
            "macd_dif": round(row.macd_dif, 4) if row.macd_dif else None,
            "macd_dea": round(row.macd_dea, 4) if row.macd_dea else None,
            "rsi_14": round(row.rsi_14, 2) if row.rsi_14 else None,
            "volume_ratio": round(row.volume_ratio, 2) if row.volume_ratio else None,
            "trend_score": score,
            "signals": " | ".join(signals),
        })

    if sort_field == "score":
        result_list.sort(key=lambda x: x["trend_score"], reverse=True)
        offset = (query.page_num - 1) * page_size
        result_list = result_list[offset:offset + page_size]

    return success({
        "trade_date": query.trade_date,
        "total": total_result,
        "page_num": query.page_num,
        "page_size": page_size,
        "list": result_list,
    })


# 2.14 震荡选股
@router.post("/range-picker")
def post_range_picker(
    query: schemas.RangePickerQuery,
    db: Session = Depends(get_db),
):
    """震荡选股 - 布林带收口 / RSI中性 / 均线缠绕 / 缩量"""
    trade_date = query.trade_date.replace("-", "")
    page_size = min(query.page_size, 100)
    start_date = _get_start_date(trade_date)
    exclude_sql = build_exclude_sql(query)

    with_clause = indicators.assemble_with(
        indicators.build_pre_filter_cte(
            exclude_sql=exclude_sql,
            extra_having="AVG(ABS(sd.pct_chg)) <= :max_pct_chg_20d",
        ),
        indicators.build_latest_data_cte(),
        indicators.build_bollinger_cte(period=20, std_multiplier=2.0),
        indicators.build_ma_cte(periods=(5, 10, 20)),
        indicators.build_rsi_cte(period=14),
        indicators.build_amplitude_avg_cte(period=20),
        indicators.build_volume_avg_cte(period=20),
    )

    where_conditions = [
        "br.bb_width <= :bb_width_max",
        "rc.rsi_14 >= :rsi_min",
        "rc.rsi_14 <= :rsi_max",
        "ac.avg_amplitude_20 >= :min_amplitude_20d",
    ]
    if query.volume_shrink:
        where_conditions.append("ld.volume / vc.avg_volume_20 <= 0.9")
    if query.near_ma20:
        where_conditions.append("ABS(ld.close - mc.ma20) / mc.ma20 <= 0.03")

    where_sql = "\n        AND ".join(where_conditions)

    sort_field = query.sort_field if query.sort_field in {
        "bb_width", "rsi_14", "ma5", "ma10", "ma20", "pct_chg",
        "turnover", "amount", "symbol", "name",
    } else "bb_width"
    sort_order = "ASC" if query.sort_order.lower() == "asc" else "DESC"

    count_sql = f"""
    {with_clause}
    SELECT COUNT(*)
    FROM latest_data ld
    JOIN pre_filter pf ON ld.symbol = pf.symbol
    JOIN bb_result br ON ld.symbol = br.symbol
    JOIN ma_calc mc ON ld.symbol = mc.symbol
    LEFT JOIN rsi_calc rc ON ld.symbol = rc.symbol
    LEFT JOIN amplitude_calc ac ON ld.symbol = ac.symbol
    LEFT JOIN volume_calc vc ON ld.symbol = vc.symbol
    WHERE {where_sql}
    """

    params = {
        "trade_date": trade_date,
        "start_date": start_date,
        "min_amount": query.min_amount,
        "max_pct_chg_20d": query.max_pct_chg_20d,
        "bb_width_max": query.bb_width_max,
        "rsi_min": query.rsi_min,
        "rsi_max": query.rsi_max,
        "min_amplitude_20d": query.min_amplitude_20d,
    }

    total_result = db.execute(text(count_sql), params).scalar() or 0

    select_columns = """
        ld.symbol,
        pf.name,
        pf.industry,
        ld.trade_date,
        ld.open,
        ld.close,
        ld.high,
        ld.low,
        ld.volume,
        ld.amount,
        ld.turnover,
        ld.pct_chg,
        br.bb_lower,
        br.bb_middle,
        br.bb_upper,
        br.bb_width,
        mc.ma5,
        mc.ma10,
        mc.ma20,
        rc.rsi_14,
        ac.avg_amplitude_20,
        vc.avg_volume_20,
        ld.volume / vc.avg_volume_20 AS volume_ratio
    """

    if sort_field == "score":
        list_sql = f"""
        {with_clause}
        SELECT {select_columns}
        FROM latest_data ld
        JOIN pre_filter pf ON ld.symbol = pf.symbol
        JOIN bb_result br ON ld.symbol = br.symbol
        JOIN ma_calc mc ON ld.symbol = mc.symbol
        LEFT JOIN rsi_calc rc ON ld.symbol = rc.symbol
        LEFT JOIN amplitude_calc ac ON ld.symbol = ac.symbol
        LEFT JOIN volume_calc vc ON ld.symbol = vc.symbol
        WHERE {where_sql}
        """
    else:
        list_sql = f"""
        {with_clause}
        SELECT {select_columns}
        FROM latest_data ld
        JOIN pre_filter pf ON ld.symbol = pf.symbol
        JOIN bb_result br ON ld.symbol = br.symbol
        JOIN ma_calc mc ON ld.symbol = mc.symbol
        LEFT JOIN rsi_calc rc ON ld.symbol = rc.symbol
        LEFT JOIN amplitude_calc ac ON ld.symbol = ac.symbol
        LEFT JOIN volume_calc vc ON ld.symbol = vc.symbol
        WHERE {where_sql}
        ORDER BY {sort_field} {sort_order}
        LIMIT :limit OFFSET :offset
        """
        params["limit"] = page_size
        params["offset"] = (query.page_num - 1) * page_size

    rows = db.execute(text(list_sql), params).all()

    result_list = []
    for row in rows:
        score, signals = indicators.calculate_range_score(
            row.bb_width or 0.1,
            row.rsi_14 or 50,
            row.ma5 or 0, row.ma10 or 0, row.ma20 or 0,
            row.volume_ratio or 1,
            row.avg_amplitude_20 or 0,
        )
        result_list.append({
            "symbol": row.symbol,
            "name": row.name,
            "industry": row.industry,
            "trade_date": query.trade_date,
            "open": row.open,
            "close": row.close,
            "high": row.high,
            "low": row.low,
            "volume": row.volume,
            "amount": row.amount,
            "turnover": row.turnover,
            "pct_chg": row.pct_chg,
            "bb_lower": round(row.bb_lower, 4) if row.bb_lower else None,
            "bb_middle": round(row.bb_middle, 4) if row.bb_middle else None,
            "bb_upper": round(row.bb_upper, 4) if row.bb_upper else None,
            "bb_width": round(row.bb_width, 4) if row.bb_width else None,
            "ma5": round(row.ma5, 4) if row.ma5 else None,
            "ma10": round(row.ma10, 4) if row.ma10 else None,
            "ma20": round(row.ma20, 4) if row.ma20 else None,
            "rsi_14": round(row.rsi_14, 2) if row.rsi_14 else None,
            "avg_amplitude_20": round(row.avg_amplitude_20, 2) if row.avg_amplitude_20 else None,
            "volume_ratio": round(row.volume_ratio, 2) if row.volume_ratio else None,
            "range_score": score,
            "signals": " | ".join(signals),
        })

    if sort_field == "score":
        result_list.sort(key=lambda x: x["range_score"], reverse=True)
        offset = (query.page_num - 1) * page_size
        result_list = result_list[offset:offset + page_size]

    return success({
        "trade_date": query.trade_date,
        "total": total_result,
        "page_num": query.page_num,
        "page_size": page_size,
        "list": result_list,
    })
