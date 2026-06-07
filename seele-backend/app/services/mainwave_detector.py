"""
主升浪阶段识别服务

给定一只股票，找出历史上所有 30 个交易日涨幅 >= 180% 的主升浪阶段。
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Dict

from sqlalchemy.orm import Session

from app import models


@dataclass
class MainwavePhase:
    """主升浪阶段"""
    start_date: date
    end_date: date
    days: int
    start_close: float
    end_close: float
    total_gain_pct: float
    max_daily_gain_pct: float
    max_daily_drop_pct: float
    avg_turnover: Optional[float]
    max_high: float
    min_low: float


def _fetch_daily_data(
    db: Session,
    symbol: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[models.StockDaily]:
    """获取单只股票日线数据，按日期升序排列"""
    q = (
        db.query(models.StockDaily)
        .filter(models.StockDaily.symbol == symbol)
        .order_by(models.StockDaily.trade_date.asc())
    )
    if start_date:
        q = q.filter(models.StockDaily.trade_date >= start_date)
    if end_date:
        q = q.filter(models.StockDaily.trade_date <= end_date)
    return q.all()


def _calc_window_gain(
    dailies: List[models.StockDaily],
    start_idx: int,
    window_days: int = 30,
    min_gain_pct: float = 180.0,
) -> Optional[MainwavePhase]:
    """计算从 start_idx 开始、window_days 个交易日的窗口涨幅"""
    end_idx = start_idx + window_days - 1
    if end_idx >= len(dailies):
        return None

    window = dailies[start_idx:end_idx + 1]
    start_close = float(window[0].close) if window[0].close else None
    end_close = float(window[-1].close) if window[-1].close else None
    if start_close is None or end_close is None or start_close == 0:
        return None

    total_gain_pct = (end_close - start_close) / start_close * 100
    if total_gain_pct < min_gain_pct:
        return None

    # 统计窗口内指标
    pct_chgs = []
    turnovers = []
    highs = []
    lows = []
    for d in window:
        if d.pct_chg is not None:
            pct_chgs.append(float(d.pct_chg))
        if d.turnover is not None:
            turnovers.append(float(d.turnover))
        if d.high is not None:
            highs.append(float(d.high))
        if d.low is not None:
            lows.append(float(d.low))

    max_daily_gain = max(pct_chgs) if pct_chgs else 0
    max_daily_drop = min(pct_chgs) if pct_chgs else 0
    avg_turnover = sum(turnovers) / len(turnovers) if turnovers else None
    max_high = max(highs) if highs else 0
    min_low = min(lows) if lows else 0

    return MainwavePhase(
        start_date=window[0].trade_date,
        end_date=window[-1].trade_date,
        days=window_days,
        start_close=round(start_close, 4),
        end_close=round(end_close, 4),
        total_gain_pct=round(total_gain_pct, 2),
        max_daily_gain_pct=round(max_daily_gain, 2),
        max_daily_drop_pct=round(max_daily_drop, 2),
        avg_turnover=round(avg_turnover, 4) if avg_turnover else None,
        max_high=round(max_high, 4),
        min_low=round(min_low, 4),
    )


def _deduplicate_overlapping_phases(phases: List[MainwavePhase]) -> List[MainwavePhase]:
    """对重叠的主升浪窗口去重，保留每段主升浪中涨幅最大的代表窗口

    策略：
    1. 按开始日期排序
    2. 遍历窗口，如果当前窗口与上一个已选窗口重叠，比较涨幅保留更大的
    3. 不重叠则直接加入结果

    这样可以避免一段持续 40~60 天的主升浪被多个 30 天窗口重复报告。
    """
    if not phases:
        return []

    sorted_phases = sorted(phases, key=lambda p: p.start_date)
    result: List[MainwavePhase] = []

    for p in sorted_phases:
        if not result:
            result.append(p)
            continue

        last = result[-1]
        # 判断是否重叠（开始日期在上一窗口结束日期之前或当天）
        if p.start_date <= last.end_date:
            # 重叠：保留涨幅更大的窗口
            if p.total_gain_pct > last.total_gain_pct:
                result[-1] = p
        else:
            result.append(p)

    return result


def detect_mainwave_phases(
    db: Session,
    symbol: str,
    min_gain_pct: float = 180.0,
    window_days: int = 30,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict:
    """识别单只股票的主升浪阶段

    Args:
        db: 数据库 Session
        symbol: 股票代码
        min_gain_pct: 最小涨幅阈值（默认 180%）
        window_days: 窗口交易日数（默认 30）
        start_date: 查询起始日期
        end_date: 查询结束日期

    Returns:
        dict: {
            'symbol': str,
            'name': str,
            'total_days': int,
            'phase_count': int,
            'phases': List[dict]
        }
    """
    # 获取股票名称
    stock_basic = (
        db.query(models.StockBasic)
        .filter(models.StockBasic.symbol == symbol)
        .first()
    )
    name = stock_basic.name if stock_basic else ''

    dailies = _fetch_daily_data(db, symbol, start_date, end_date)
    if len(dailies) < window_days:
        return {
            'symbol': symbol,
            'name': name,
            'total_days': len(dailies),
            'phase_count': 0,
            'phases': [],
        }

    # 滑动窗口扫描
    raw_phases: List[MainwavePhase] = []
    for i in range(len(dailies) - window_days + 1):
        phase = _calc_window_gain(dailies, i, window_days, min_gain_pct)
        if phase and phase.total_gain_pct >= min_gain_pct:
            raw_phases.append(phase)

    # 对重叠窗口去重，保留每段主升浪涨幅最大的 30 天代表窗口
    phases = _deduplicate_overlapping_phases(raw_phases)

    return {
        'symbol': symbol,
        'name': name,
        'total_days': len(dailies),
        'phase_count': len(phases),
        'phases': [
            {
                'start_date': str(p.start_date),
                'end_date': str(p.end_date),
                'days': p.days,
                'start_close': p.start_close,
                'end_close': p.end_close,
                'total_gain_pct': p.total_gain_pct,
                'max_daily_gain_pct': p.max_daily_gain_pct,
                'max_daily_drop_pct': p.max_daily_drop_pct,
                'avg_turnover': p.avg_turnover,
                'max_high': p.max_high,
                'min_low': p.min_low,
            }
            for p in phases
        ],
    }


def batch_detect_mainwaves(
    db: Session,
    symbols: List[str],
    min_gain_pct: float = 180.0,
    window_days: int = 30,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict]:
    """批量识别多只股票的主升浪阶段

    Returns:
        仅返回至少识别到一个主升浪阶段的股票结果
    """
    results = []
    for symbol in symbols:
        result = detect_mainwave_phases(
            db, symbol, min_gain_pct, window_days, start_date, end_date
        )
        if result['phase_count'] > 0:
            results.append(result)
    return results
