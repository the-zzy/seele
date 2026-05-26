"""
主升浪选股评分服务

参考《推荐标的评分规则 v3.1》实现，基于现有数据做合理简化。
满分100分，60分及格可推荐，80分以上强烈推荐。
"""

from typing import List, Dict, Optional, Set
from datetime import datetime
from collections import defaultdict
from sqlalchemy.orm import Session, load_only
from sqlalchemy import distinct

from app import models


def _calc_deviate_ma5(close: Optional[float], ma5: Optional[float]) -> int:
    """偏离MA5（10分）"""
    if not close or not ma5 or ma5 == 0:
        return 0
    deviate = (close - ma5) / ma5 * 100
    if deviate > 7 or deviate <= 0:
        return 0
    if deviate <= 1:
        return 10
    if deviate <= 2:
        return 8
    if deviate <= 3:
        return 6
    if deviate <= 4:
        return 4
    if deviate <= 5:
        return 2
    return 1


def _calc_pullback(close: Optional[float], recent_highs: List[float]) -> int:
    """距高点回落（5分）"""
    if not close or not recent_highs:
        return 0
    max_high = max(recent_highs)
    if max_high == 0:
        return 0
    pullback = (max_high - close) / max_high * 100
    if pullback <= 2:
        return 5
    if pullback <= 3:
        return 4
    if pullback <= 4:
        return 3
    if pullback <= 5:
        return 2
    return 0


def _calc_k_ratio(recent_pct_chgs: List[Optional[float]]) -> int:
    """K线涨跌比（5分）"""
    up = sum(1 for p in recent_pct_chgs if p is not None and p > 0)
    down = sum(1 for p in recent_pct_chgs if p is not None and p < 0)
    if up > down:
        return 5
    if up == down:
        return 3
    if up < down and up > 0:
        return 1
    return 0


def _is_big_drop(d: models.StockDaily) -> bool:
    """大阴线：阴线（收盘<开盘）且跌幅超过2%"""
    if not d or d.close is None or d.open is None:
        return False
    return d.close < d.open and d.pct_chg is not None and d.pct_chg < -2


def _calc_big_drop(recent_dailies: List[models.StockDaily]) -> int:
    """大阴线天数评分（5分）"""
    count = sum(1 for d in recent_dailies if _is_big_drop(d))
    if count == 0:
        return 5
    if count == 1:
        return 3
    return 0


def _is_upper_shadow(d: models.StockDaily) -> bool:
    """有明显上影线：上影线长度占收盘价比例超过1.5%"""
    if not d or d.high is None or d.open is None or d.close is None:
        return False
    if d.high <= max(d.open, d.close):
        return False
    body_top = max(d.open, d.close)
    shadow_len = d.high - body_top
    if d.close == 0:
        return False
    return shadow_len / d.close > 0.015


def _calc_upper_shadow(recent_dailies: List[models.StockDaily]) -> int:
    """上影线天数评分（5分）"""
    count = sum(1 for d in recent_dailies if _is_upper_shadow(d))
    if count == 0:
        return 5
    if count == 1:
        return 3
    return 0


def _calc_direction(industry: Optional[str], holding_industries: Set[str]) -> int:
    """方向分散（20分）

    简化版：持仓中无同行业=20分，持仓中有同行业=0分。
    因 industry 字段本身已是细分行业，无进一步的大类细分数据。
    """
    if not industry or not holding_industries:
        return 20
    if industry in holding_industries:
        return 0
    return 20


def _calc_sector(industry: Optional[str], sector_sentiment_map: Dict[str, float]) -> int:
    """板块强度（20分）

    使用行业当日平均涨幅近似板块ETF强度（数据有限时的替代方案）。
    """
    if not industry:
        return 5
    avg_chg = sector_sentiment_map.get(industry)
    if avg_chg is None:
        return 5
    if avg_chg > 2:
        return 20
    if avg_chg > 1:
        return 15
    if avg_chg > 0:
        return 10
    if avg_chg > -1:
        return 5
    if avg_chg > -2:
        return 3
    return 0


def _calc_earnings(net_profit_yoy: Optional[float]) -> int:
    """业绩质量（15分）"""
    if net_profit_yoy is None:
        return 0
    if net_profit_yoy > 100:
        return 15
    if net_profit_yoy > 50:
        return 12
    if net_profit_yoy > 20:
        return 10
    if net_profit_yoy > 10:
        return 7
    if net_profit_yoy > 0:
        return 4
    if net_profit_yoy > -30:
        return 2
    return 0


def _calc_liquidity(float_market_cap: Optional[float], turnover_ma10: Optional[float]) -> int:
    """市值流动性（10分）——流通市值与10日换手率取平均"""
    cap_score = 0
    if float_market_cap is not None:
        if float_market_cap > 500:
            cap_score = 10
        elif float_market_cap >= 200:
            cap_score = 8
        elif float_market_cap >= 100:
            cap_score = 5
        elif float_market_cap >= 50:
            cap_score = 3

    turn_score = 0
    if turnover_ma10 is not None:
        if turnover_ma10 > 5:
            turn_score = 10
        elif turnover_ma10 >= 3:
            turn_score = 8
        elif turnover_ma10 >= 2:
            turn_score = 5
        elif turnover_ma10 >= 1:
            turn_score = 3

    return round((cap_score + turn_score) / 2)


def calculate_mainwave_score(
    stock: dict,
    recent_dailies: List[models.StockDaily],
    holding_industries: Set[str],
    sector_sentiment_map: Dict[str, float],
    is_holding: bool = False,
) -> dict:
    """计算单只股票的主升浪评分

    Returns:
        dict: 包含 total 总分及各子项分数的字典
    """
    close = stock.get('close')
    ma5 = stock.get('ma5')
    industry = stock.get('industry')
    net_profit_yoy = stock.get('net_profit_yoy')
    float_market_cap = stock.get('float_market_cap')
    turnover_ma10 = stock.get('turnover_ma10')

    # ---- 硬性门槛 ----
    hard_pass = True
    if close and ma5 and ma5 > 0:
        deviate = (close - ma5) / ma5 * 100
        if deviate > 7 or deviate <= 0:
            hard_pass = False
    else:
        hard_pass = False

    # 持仓股本身不因为"与持仓同行业"被一票否决
    if industry and industry in holding_industries and not is_holding:
        hard_pass = False

    if not hard_pass:
        return {
            'total': 0,
            'deviate_ma5': 0,
            'pullback': 0,
            'k_ratio': 0,
            'big_drop': 0,
            'upper_shadow': 0,
            'direction': 0,
            'sector': 0,
            'earnings': 0,
            'liquidity': 0,
            'catalyst': 0,
            'hard_pass': False,
        }

    # ---- 各维度评分 ----
    deviate_ma5 = _calc_deviate_ma5(close, ma5)
    recent_highs = [d.high for d in recent_dailies if d.high is not None]
    pullback = _calc_pullback(close, recent_highs)
    recent_pct_chgs = [d.pct_chg for d in recent_dailies]
    k_ratio = _calc_k_ratio(recent_pct_chgs)
    big_drop = _calc_big_drop(recent_dailies)
    upper_shadow = _calc_upper_shadow(recent_dailies)
    direction = _calc_direction(industry, holding_industries)
    sector = _calc_sector(industry, sector_sentiment_map)
    earnings = _calc_earnings(net_profit_yoy)
    liquidity = _calc_liquidity(float_market_cap, turnover_ma10)
    catalyst = 0  # 暂无催化事件数据

    total = (
        deviate_ma5 + pullback + k_ratio + big_drop + upper_shadow +
        direction + sector + earnings + liquidity + catalyst
    )

    return {
        'total': total,
        'deviate_ma5': deviate_ma5,
        'pullback': pullback,
        'k_ratio': k_ratio,
        'big_drop': big_drop,
        'upper_shadow': upper_shadow,
        'direction': direction,
        'sector': sector,
        'earnings': earnings,
        'liquidity': liquidity,
        'catalyst': catalyst,
        'hard_pass': True,
    }


def batch_calculate_scores(
    db: Session,
    stocks: List[dict],
    trade_date: str,
) -> List[dict]:
    """批量计算主升浪评分并附加到股票数据中

    Args:
        db: 数据库 Session
        stocks: get_mainwave_list 返回的股票字典列表
        trade_date: 交易日期字符串（YYYY-MM-DD 或 YYYYMMDD）

    Returns:
        附加了 score 字段的 stocks 列表
    """
    if not stocks:
        return stocks

    symbols = [s['symbol'] for s in stocks]

    # 统一日期格式为 datetime.date
    if '-' in trade_date:
        dt = datetime.strptime(trade_date, '%Y-%m-%d').date()
    else:
        dt = datetime.strptime(trade_date, '%Y%m%d').date()

    # 1. 批量获取近5个交易日K线数据
    # 先获取最近10个交易日期（从交易日历取，避免大表 DISTINCT）
    recent_dates = (
        db.query(models.TradeCalendar.trade_date)
        .filter(
            models.TradeCalendar.trade_date <= dt,
            models.TradeCalendar.is_trading_day == 1,
        )
        .order_by(models.TradeCalendar.trade_date.desc())
        .limit(10)
        .all()
    )
    date_list = [d[0] for d in recent_dates]

    recent_dailies = (
        db.query(models.StockDaily)
        .options(load_only(
            models.StockDaily.symbol,
            models.StockDaily.trade_date,
            models.StockDaily.high,
            models.StockDaily.open,
            models.StockDaily.close,
            models.StockDaily.pct_chg,
        ))
        .filter(
            models.StockDaily.symbol.in_(symbols),
            models.StockDaily.trade_date.in_(date_list),
        )
        .order_by(models.StockDaily.symbol, models.StockDaily.trade_date.desc())
        .all()
    )

    dailies_by_symbol: Dict[str, List[models.StockDaily]] = defaultdict(list)
    for d in recent_dailies:
        if len(dailies_by_symbol[d.symbol]) < 5:
            dailies_by_symbol[d.symbol].append(d)

    # 2. 获取当前持仓行业（quantity > 0 的持仓）
    holdings = (
        db.query(models.PortfolioPosition, models.StockBasic.industry)
        .join(
            models.StockBasic,
            models.PortfolioPosition.symbol == models.StockBasic.symbol,
        )
        .filter(models.PortfolioPosition.quantity > 0)
        .all()
    )
    holding_industries: Set[str] = set()
    for pos, ind in holdings:
        if ind:
            holding_industries.add(ind)

    # 3. 获取行业情绪数据（当日板块平均涨跌幅）
    sentiments = (
        db.query(models.IndustrySentimentDaily)
        .filter(models.IndustrySentimentDaily.trade_date == dt)
        .all()
    )
    sector_sentiment_map: Dict[str, float] = {
        s.industry: s.avg_pct_chg for s in sentiments if s.avg_pct_chg is not None
    }

    # 4. 逐只计算评分
    for stock in stocks:
        symbol = stock['symbol']
        dailies = dailies_by_symbol.get(symbol, [])
        score = calculate_mainwave_score(
            stock, dailies, holding_industries, sector_sentiment_map,
            is_holding=stock.get('is_holding', False)
        )
        stock['score'] = score

    return stocks
