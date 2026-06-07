"""
主升浪选股评分服务 v2.0

基于现有数据实现，满分100分，60分及格可推荐，80分以上强烈推荐。

维度分配：
- 趋势形态：35分（均线偏离15 + K线质量12 + 距高点回落8）
- 板块强度：20分
- 业绩质量：15分（净利润同比 + ROE）
- 方向分散：15分
- 市值流动性：8分
- 大盘环境：7分
"""

from typing import List, Dict, Optional, Set
from datetime import datetime
from collections import defaultdict
from sqlalchemy.orm import Session, load_only
from sqlalchemy import distinct

from app import models


def _calc_ma_deviation(close: Optional[float], ma5: Optional[float]) -> int:
    """均线偏离评分（15分）

    偏离适中为佳。负偏离表示偏弱，过高偏离表示追高风险。
    """
    if not close or not ma5 or ma5 == 0:
        return 0
    deviate = (close - ma5) / ma5 * 100
    if deviate < -5 or deviate > 15:
        return 0
    if deviate <= 0:
        return 4
    if deviate <= 2:
        return 15
    if deviate <= 5:
        return 12
    if deviate <= 8:
        return 8
    if deviate <= 12:
        return 4
    return 1


def _calc_kline_quality(recent_dailies: List[models.StockDaily]) -> int:
    """K线质量评分（12分）

    综合近5日阳线数量、大阴线天数、上影线天数。
    """
    if not recent_dailies:
        return 0

    recent = recent_dailies[:5]
    pct_chgs = [d.pct_chg for d in recent if d.pct_chg is not None]
    up_count = sum(1 for p in pct_chgs if p > 0)

    # 阳线数量：0~5分
    up_score = min(up_count, 5)

    # 大阴线：阴线且跌幅>2%，0天=4分，1天=2分，2天+=0分
    big_drop_count = 0
    for d in recent:
        if d.close is not None and d.open is not None and d.pct_chg is not None:
            if d.close < d.open and d.pct_chg < -2:
                big_drop_count += 1
    if big_drop_count == 0:
        big_drop_score = 4
    elif big_drop_count == 1:
        big_drop_score = 2
    else:
        big_drop_score = 0

    # 上影线：上影线长度占收盘价比例超过1.5%，0天=3分，1天=1分，2天+=0分
    upper_shadow_count = 0
    for d in recent:
        if d.high is None or d.open is None or d.close is None:
            continue
        if d.high <= max(d.open, d.close):
            continue
        body_top = max(d.open, d.close)
        shadow_len = d.high - body_top
        if d.close == 0:
            continue
        if shadow_len / d.close > 0.015:
            upper_shadow_count += 1
    if upper_shadow_count == 0:
        shadow_score = 3
    elif upper_shadow_count == 1:
        shadow_score = 1
    else:
        shadow_score = 0

    return up_score + big_drop_score + shadow_score


def _calc_pullback(close: Optional[float], recent_highs: List[float]) -> int:
    """距高点回落评分（8分）"""
    if not close or not recent_highs:
        return 0
    max_high = max(recent_highs)
    if max_high == 0:
        return 0
    pullback = (max_high - close) / max_high * 100
    if pullback <= 2:
        return 8
    if pullback <= 4:
        return 5
    if pullback <= 7:
        return 2
    return 0


def _calc_adx(adx: Optional[float]) -> int:
    """ADX趋势强度评分（10分）

    ADX >= 40: 强趋势
    ADX >= 30: 确立趋势
    ADX >= 25: 趋势开始
    ADX >= 20: 弱势趋势
    """
    if adx is None:
        return 0
    if adx >= 40:
        return 10
    if adx >= 30:
        return 8
    if adx >= 25:
        return 5
    if adx >= 20:
        return 2
    return 0


def _calc_sector(industry: Optional[str], sector_sentiment_map: Dict[str, float]) -> int:
    """板块强度评分（20分）"""
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


def _calc_earnings(net_profit_yoy: Optional[float], roe: Optional[float]) -> int:
    """业绩质量评分（15分）

    综合净利润同比增长率和ROE。
    """
    if net_profit_yoy is None and roe is None:
        return 0

    # 综合评分逻辑
    if net_profit_yoy is not None and roe is not None:
        if net_profit_yoy > 50 and roe > 15:
            return 15
        if net_profit_yoy > 20 and roe > 10:
            return 12
        if net_profit_yoy > 0 and roe > 5:
            return 8

    # 单项兜底
    if net_profit_yoy is not None:
        if net_profit_yoy > 50:
            return 10
        if net_profit_yoy > 20:
            return 8
        if net_profit_yoy > 0:
            return 4

    if roe is not None:
        if roe > 15:
            return 8
        if roe > 10:
            return 5
        if roe > 5:
            return 3

    return 0


def _calc_direction(industry: Optional[str], holding_industries: Set[str]) -> int:
    """方向分散评分（15分）

    非持仓股与持仓同行业时降权，不再一票否决。
    """
    if not industry or not holding_industries:
        return 15
    if industry in holding_industries:
        return 5
    return 15


def _calc_liquidity(float_market_cap: Optional[float], turnover_ma10: Optional[float]) -> int:
    """市值流动性评分（8分）"""
    cap_score = 0
    if float_market_cap is not None:
        if float_market_cap > 500:
            cap_score = 4
        elif float_market_cap >= 200:
            cap_score = 3
        elif float_market_cap >= 100:
            cap_score = 2
        elif float_market_cap >= 50:
            cap_score = 1

    turn_score = 0
    if turnover_ma10 is not None:
        if turnover_ma10 > 0.05:
            turn_score = 4
        elif turnover_ma10 >= 0.03:
            turn_score = 3
        elif turnover_ma10 >= 0.02:
            turn_score = 2
        elif turnover_ma10 >= 0.01:
            turn_score = 1

    return cap_score + turn_score


def _calc_market_env(index_pct_chg: Optional[float]) -> int:
    """大盘环境评分（7分）

    基于沪深300或上证指数当日涨跌幅。
    """
    if index_pct_chg is None:
        return 3
    if index_pct_chg > 1.5:
        return 7
    if index_pct_chg > 0.5:
        return 5
    if index_pct_chg > -0.5:
        return 3
    if index_pct_chg > -1.5:
        return 1
    return 0


def calculate_mainwave_score(
    stock: dict,
    recent_dailies: List[models.StockDaily],
    holding_industries: Set[str],
    sector_sentiment_map: Dict[str, float],
    market_index_pct_chg: Optional[float],
) -> dict:
    """计算单只股票的主升浪评分

    Returns:
        dict: 包含 total 总分及各维度分数的字典
    """
    close = stock.get('close')
    ma5 = stock.get('ma5')
    industry = stock.get('industry')
    net_profit_yoy = stock.get('net_profit_yoy')
    roe = stock.get('roe')
    float_market_cap = stock.get('float_market_cap')
    turnover_ma10 = stock.get('turnover_ma10')

    # 各维度评分
    ma_deviation = _calc_ma_deviation(close, ma5)
    kline_quality = _calc_kline_quality(recent_dailies)

    recent_highs = [d.high for d in recent_dailies if d.high is not None]
    pullback = _calc_pullback(close, recent_highs)

    adx_val = stock.get('adx')
    adx_score = _calc_adx(adx_val)

    trend_shape = ma_deviation + kline_quality + pullback + adx_score

    sector = _calc_sector(industry, sector_sentiment_map)
    earnings = _calc_earnings(net_profit_yoy, roe)
    direction = _calc_direction(industry, holding_industries)
    liquidity = _calc_liquidity(float_market_cap, turnover_ma10)
    market_env = _calc_market_env(market_index_pct_chg)

    total = trend_shape + sector + earnings + direction + liquidity + market_env

    return {
        'total': total,
        'trend_shape': trend_shape,
        'ma_deviation': ma_deviation,
        'kline_quality': kline_quality,
        'pullback': pullback,
        'adx': adx_score,
        'sector': sector,
        'earnings': earnings,
        'direction': direction,
        'liquidity': liquidity,
        'market_env': market_env,
        'hard_pass': total >= 60,
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

    # 1. 批量获取近20个交易日K线数据（取30个交易日内最多20条，应对停牌）
    recent_dates = (
        db.query(models.TradeCalendar.trade_date)
        .filter(
            models.TradeCalendar.trade_date <= dt,
            models.TradeCalendar.is_trading_day == 1,
        )
        .order_by(models.TradeCalendar.trade_date.desc())
        .limit(30)
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
        if len(dailies_by_symbol[d.symbol]) < 20:
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

    # 3. 获取板块指数涨跌幅（同花顺行业板块指数）
    sentiments = (
        db.query(models.BoardInfo.name, models.BoardDaily.pct_chg)
        .join(models.BoardDaily, models.BoardInfo.code == models.BoardDaily.code)
        .filter(
            models.BoardInfo.category == 'industry',
            models.BoardDaily.trade_date == dt,
        )
        .all()
    )
    sector_sentiment_map: Dict[str, float] = {
        name: float(pct_chg) for name, pct_chg in sentiments if pct_chg is not None
    }

    # 4. 获取大盘环境数据（沪深300优先，fallback 上证指数）
    market_index_pct_chg: Optional[float] = None
    index_symbols = ['000300.SH', 'sh000300', '000001.SH', 'sh000001']
    for idx_sym in index_symbols:
        idx_record = (
            db.query(models.IndexDaily)
            .filter(
                models.IndexDaily.symbol == idx_sym,
                models.IndexDaily.trade_date == dt,
            )
            .first()
        )
        if idx_record and idx_record.pct_chg is not None:
            market_index_pct_chg = idx_record.pct_chg
            break

    # 5. 逐只计算评分
    for stock in stocks:
        symbol = stock['symbol']
        dailies = dailies_by_symbol.get(symbol, [])
        score = calculate_mainwave_score(
            stock, dailies, holding_industries, sector_sentiment_map,
            market_index_pct_chg,
        )
        stock['score'] = score

    return stocks
