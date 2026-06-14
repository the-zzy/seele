"""
主升浪选股评分服务 v2.1

评分体系全推翻后当前维度（后续可继续扩展）：
- 趋势分：启动日到最近交易日，收盘价与 MA5/MA10/MA20 的相对位置
- 强势分：启动日到最近交易日，每日涨跌幅区间累计
- 动量分：启动日到最近交易日，大涨/大跌日是否伴随换手率放大
"""

from typing import List, Dict, Optional, Set
from datetime import datetime
from collections import defaultdict
from sqlalchemy.orm import Session, load_only
from sqlalchemy import distinct, and_

from app import models


def _calc_trend_score(dailies: List[Dict]) -> float:
    """趋势分

    遍历启动日到最近交易日的每个交易日：
    - 收盘价 ≥ MA5：+3；跌破 MA5：-1
    - 收盘价 ≥ MA10：+2；跌破 MA10：-2
    - 收盘价 ≥ MA20：+1；跌破 MA20：-3
    """
    score = 0.0
    for d in dailies:
        close = d.get('close')
        ma5 = d.get('ma5')
        ma10 = d.get('ma10')
        ma20 = d.get('ma20')

        if close is not None and ma5 is not None and float(ma5) != 0:
            if float(close) >= float(ma5):
                score += 3
            else:
                score -= 1

        if close is not None and ma10 is not None and float(ma10) != 0:
            if float(close) >= float(ma10):
                score += 2
            else:
                score -= 2

        if close is not None and ma20 is not None and float(ma20) != 0:
            if float(close) >= float(ma20):
                score += 1
            else:
                score -= 3

    return round(score, 2)


def _calc_strength_score(dailies: List[Dict]) -> float:
    """强势分

    遍历启动日到最近交易日的每个交易日：
    - 涨幅 > 9%：+3
    - 5% ≤ 涨幅 ≤ 9%：+2
    - 0% ≤ 涨幅 < 5%：+1
    - 涨幅 < -9%：-3
    - -9% ≤ 涨幅 ≤ -5%：-2
    - -5% < 涨幅 < 0%：-1
    """
    score = 0.0
    for d in dailies:
        pct = d.get('pct_chg')
        if pct is None:
            continue
        pct = float(pct)

        if pct > 9:
            score += 3
        elif pct >= 5:
            score += 2
        elif pct >= 0:
            score += 1
        elif pct < -9:
            score -= 3
        elif pct <= -5:
            score -= 2
        else:
            score -= 1

    return round(score, 2)


def _calc_momentum_score(dailies: List[Dict]) -> float:
    """动量分

    遍历启动日到最近交易日的每个交易日：
    - 涨幅 > 5% 且 换手率 > 五日平均换手率：+5 * (换手率 / 五日平均换手率)
    - 涨幅 < -5% 且 换手率 > 五日平均换手率：-5 * (换手率 / 五日平均换手率)
    """
    score = 0.0
    for d in dailies:
        pct = d.get('pct_chg')
        turnover = d.get('turnover')
        turnover_ma5 = d.get('turnover_ma5')

        if pct is None or turnover is None or turnover_ma5 is None:
            continue
        pct = float(pct)
        turnover = float(turnover)
        turnover_ma5 = float(turnover_ma5)

        if turnover_ma5 <= 0:
            continue

        if pct > 5 and turnover > turnover_ma5:
            score += 5 * (turnover / turnover_ma5)
        elif pct < -5 and turnover > turnover_ma5:
            score -= 5 * (turnover / turnover_ma5)

    return round(score, 2)


def _records_to_dailies(recs, launch_date_str: Optional[str]) -> List[Dict]:
    """将查询记录转换为评分所需的日线字典，并按日期由旧到新排序。

    recs 元素：按日期 desc 排列的 tuple，格式为
    (trade_date, close, pct_chg, turnover, ma5, ma10, ma20, turnover_ma5)
    """
    dailies = []
    for r in recs:
        trade_date = str(r[0])
        if launch_date_str and trade_date < launch_date_str:
            continue
        dailies.append({
            'trade_date': trade_date,
            'close': r[1],
            'pct_chg': r[2],
            'turnover': r[3],
            'ma5': r[4],
            'ma10': r[5],
            'ma20': r[6],
            'turnover_ma5': r[7],
        })
    # 转为由旧到新，保证遍历顺序与"启动日到最近"一致
    dailies.reverse()
    return dailies


def calculate_mainwave_score(
    stock: dict,
    launch_dailies: List[Dict],
) -> dict:
    """计算单只股票的主升浪评分

    Returns:
        dict: 包含 total 总分及各维度分数的字典
    """
    trend_score = _calc_trend_score(launch_dailies)
    strength_score = _calc_strength_score(launch_dailies)
    momentum_score = _calc_momentum_score(launch_dailies)

    total = trend_score + strength_score + momentum_score

    return {
        'total': round(total, 2),
        'trend_score': trend_score,
        'strength_score': strength_score,
        'momentum_score': momentum_score,
        'hard_pass': total >= 60,
    }


def _get_date_list(db: Session, trade_date: str, limit: int = 30) -> List:
    """获取最近 N 个交易日的日期列表（datetime.date，按日期降序）"""
    if '-' in trade_date:
        dt = datetime.strptime(trade_date, '%Y-%m-%d').date()
    else:
        dt = datetime.strptime(trade_date, '%Y%m%d').date()

    recent_dates = (
        db.query(models.TradeCalendar.trade_date)
        .filter(
            models.TradeCalendar.trade_date <= dt,
            models.TradeCalendar.is_trading_day == 1,
        )
        .order_by(models.TradeCalendar.trade_date.desc())
        .limit(limit)
        .all()
    )
    return [d[0] for d in recent_dates]


def _fetch_recent_records(
    db: Session,
    symbols: List[str],
    date_list: List,
) -> Dict[str, List]:
    """统一查询最近日线+指标数据，按 symbol 分组返回。

    返回字典：symbol -> 记录列表，每条记录格式为
    (trade_date, close, pct_chg, turnover, ma5, ma10, ma20, turnover_ma5)
    按 trade_date desc 排列。
    """
    recent_records = (
        db.query(
            models.StockDaily.symbol,
            models.StockDaily.trade_date,
            models.StockDaily.close,
            models.StockDaily.pct_chg,
            models.StockDaily.turnover,
            models.StockDailyIndicator.ma5,
            models.StockDailyIndicator.ma10,
            models.StockDailyIndicator.ma20,
            models.StockDailyIndicator.turnover_ma5,
        )
        .outerjoin(
            models.StockDailyIndicator,
            and_(
                models.StockDaily.symbol == models.StockDailyIndicator.symbol,
                models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
            ),
        )
        .filter(
            models.StockDaily.symbol.in_(symbols),
            models.StockDaily.trade_date.in_(date_list),
        )
        .order_by(models.StockDaily.symbol, models.StockDaily.trade_date.desc())
        .all()
    )

    records_by_symbol: Dict[str, List] = defaultdict(list)
    for r in recent_records:
        records_by_symbol[r[0]].append(r[1:])
    return records_by_symbol


def batch_calculate_scores(
    db: Session,
    stocks: List[dict],
    trade_date: str,
    records_by_symbol: Optional[Dict[str, List]] = None,
) -> List[dict]:
    """批量计算主升浪评分并附加到股票数据中

    Args:
        db: 数据库 Session
        stocks: get_mainwave_list 返回的股票字典列表，需已包含 launch_date
        trade_date: 交易日期字符串（YYYY-MM-DD 或 YYYYMMDD）
        records_by_symbol: 可选，已查询好的日线数据（由 batch_calculate_mainwave_layers 提供）

    Returns:
        附加了 score 字段的 stocks 列表
    """
    if not stocks:
        return stocks

    symbols = [s['symbol'] for s in stocks]

    if records_by_symbol is None:
        date_list = _get_date_list(db, trade_date)
        records_by_symbol = _fetch_recent_records(db, symbols, date_list)

    for stock in stocks:
        symbol = stock['symbol']
        recs = records_by_symbol.get(symbol, [])
        launch_date = stock.get('launch_date')
        if not launch_date and recs:
            launch_date = str(recs[-1][0])

        launch_dailies = _records_to_dailies(recs, launch_date)
        score = calculate_mainwave_score(stock, launch_dailies)
        stock['score'] = score

    return stocks


def _is_ma_bull(ma5, ma10, ma20):
    """判断当日是否满足 MA5 > MA10 > MA20"""
    if ma5 is None or ma10 is None or ma20 is None:
        return False
    return float(ma5) > float(ma10) > float(ma20)


def _find_launch_date(records, window_size):
    """从考察区间最远日往前找启动日

    records: 按日期降序排列的记录列表，元素格式为
    (trade_date, close, pct_chg, turnover, ma5, ma10, ma20, turnover_ma5)

    返回: (launch_date_str, launch_close)
    """
    if len(records) < window_size:
        return None, None

    # 从考察区间最远日（索引 window_size-1）往前遍历
    for i in range(window_size - 1, len(records) - 1):
        curr = records[i]
        prev = records[i + 1]
        curr_pct = curr[2] if curr[2] is not None else 0
        prev_pct = prev[2] if prev[2] is not None else 0

        # 单日跌幅 < -2%
        if curr_pct < -2:
            return str(curr[0]), float(curr[1]) if curr[1] is not None else None

        # 连续两天涨幅 < 1%
        if curr_pct < 1 and prev_pct < 1:
            return str(curr[0]), float(curr[1]) if curr[1] is not None else None

    # 未触发条件，取最早有数据的日期
    last = records[-1]
    return str(last[0]), float(last[1]) if last[1] is not None else None


def batch_calculate_mainwave_layers(
    db: Session,
    stocks: List[dict],
    trade_date: str,
) -> Dict[str, List]:
    """批量计算主升浪分层数据：多头排列天数、启动日、启动日至今涨幅

    直接修改 stocks 列表，附加以下字段：
    - bull_days_5:  最近5日多头排列天数
    - bull_days_10: 最近10日多头排列天数
    - bull_days_20: 最近20日多头排列天数
    - layer:        分层结果 'MAX' / 20 / 10 / 5 / 'OFF'
    - launch_date:  启动日（YYYY-MM-DD）
    - launch_pct_chg: 启动日至今涨幅(%)

    返回按 symbol 分组的日线记录（与 _fetch_recent_records 格式一致），
    可供 batch_calculate_scores 复用，避免重复查询。
    """
    if not stocks:
        return {}

    symbols = [s['symbol'] for s in stocks]
    date_list = _get_date_list(db, trade_date, limit=30)
    records_by_symbol = _fetch_recent_records(db, symbols, date_list)

    for stock in stocks:
        symbol = stock['symbol']
        recs = records_by_symbol.get(symbol, [])

        # 计算最近 N 日多头排列天数
        bull_flags = [_is_ma_bull(r[4], r[5], r[6]) for r in recs]
        bull_days_5 = sum(bull_flags[:5])
        bull_days_10 = sum(bull_flags[:10])
        bull_days_20 = sum(bull_flags[:20])

        stock['bull_days_5'] = bull_days_5
        stock['bull_days_10'] = bull_days_10
        stock['bull_days_20'] = bull_days_20

        # 分层判断（优先级从高到低）
        # 二十日分组：最近20天中 >= 16 天多头排列（80%）
        # 十日分组：最近10天中 >= 7 天多头排列（70%）
        # 五日分组：最近5天中 >= 4 天多头排列（80%）
        if bull_days_20 >= 16:
            layer = 20
            window = 20
        elif bull_days_10 >= 7:
            layer = 10
            window = 10
        elif bull_days_5 >= 4:
            layer = 5
            window = 5
        else:
            layer = 'OFF'
            window = 5  # 兜底也用5日区间找启动日

        stock['layer'] = layer

        # 计算启动日和启动日至今涨幅
        launch_date, launch_close = _find_launch_date(recs, window)
        stock['launch_date'] = launch_date

        if launch_date and launch_close and launch_close > 0:
            current_close = stock.get('close')
            if current_close is not None:
                stock['launch_pct_chg'] = round(
                    (float(current_close) - launch_close) / launch_close * 100, 2
                )
            else:
                stock['launch_pct_chg'] = None
        else:
            stock['launch_pct_chg'] = None

    return records_by_symbol
