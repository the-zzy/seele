"""
回测引擎

负责：交易日推进、主升浪池子计算、AI 决策调用、交易执行、快照持久化。
"""

import asyncio
import json
import logging
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.client import LlmClient
from app.crud import (
    backtest_decision_log_crud,
    backtest_run_crud,
    backtest_snapshot_crud,
    backtest_trade_crud,
    stock_basic_crud,
)
from app.services import mainwave_scorer

logger = logging.getLogger(__name__)

MAX_POSITIONS = 3
MIN_POSITION_RATIO = 0.20
BUY_POOL_TOP_N = 20
AI_KLINE_LIMIT = 15
AI_TIMEOUT_SECONDS = 900.0

# 与系统主升浪选股界面保持一致的默认筛选门槛
DEFAULT_POOL_FILTERS = {
    'float_market_cap_min': 200.0,  # 流通市值 ≥ 200 亿
    'close_max': 300.0,             # 股价 ≤ 300 元
    'avg_turnover_min': 2.0,        # 10 日平均换手率 ≥ 2%
    'avg_amount_min': 200000000.0,  # 10 日平均成交额 ≥ 2 亿元
    'ma_bull': True,                # 均线多头排列
}


def _fmt_date(d: date) -> str:
    return d.strftime('%Y-%m-%d')


def _parse_date(s: str) -> date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def _get_price_limit_rules(symbol: str, name: str = '') -> Tuple[float, float]:
    """根据股票代码和名称返回涨跌停幅度（上限度、下限度）。

    规则：
    - 创业板 300/301、科创板 688/689：±20%
    - 北交所 4/8 开头：±30%
    - 主板 ST/*ST：±5%
    - 主板其他：±10%
    """
    if symbol.startswith(('300', '301', '688', '689')):
        return 0.20, -0.20
    if symbol.startswith(('4', '8')):
        return 0.30, -0.30
    if name and re.search(r'^\*?ST', name):
        return 0.05, -0.05
    return 0.10, -0.10


def _calc_price_limits(
    prev_close: float,
    symbol: str,
    name: str = '',
) -> Tuple[Optional[float], Optional[float]]:
    """根据前收盘价计算涨停价和跌停价，返回 (limit_up, limit_down)。"""
    if prev_close is None or prev_close <= 0:
        return None, None
    up_pct, down_pct = _get_price_limit_rules(symbol, name)
    limit_up = round(prev_close * (1 + up_pct), 2)
    limit_down = round(prev_close * (1 + down_pct), 2)
    return limit_up, limit_down


def _is_limit_up(
    close: float,
    prev_close: float,
    symbol: str,
    name: str = '',
) -> bool:
    """判断是否涨停。"""
    limit_up, _ = _calc_price_limits(prev_close, symbol, name)
    if limit_up is None:
        return False
    return close >= limit_up - 1e-6


def _is_limit_down(
    close: float,
    prev_close: float,
    symbol: str,
    name: str = '',
) -> bool:
    """判断是否跌停。"""
    _, limit_down = _calc_price_limits(prev_close, symbol, name)
    if limit_down is None:
        return False
    return close <= limit_down + 1e-6


def _filter_pool_limit_up(
    pool: List[dict],
    close_map: Dict[str, float],
    klines: Dict[str, List[dict]],
) -> List[dict]:
    """剔除当日涨停股票，不推送给 AI 作为买入候选。"""
    filtered: List[dict] = []
    for s in pool:
        symbol = s['symbol']
        close = close_map.get(symbol)
        if close is None:
            continue
        prev_close = _get_prev_close_from_klines(klines, symbol)
        if prev_close is not None and _is_limit_up(
            close, prev_close, symbol, s.get('name') or symbol
        ):
            logger.info('[BACKTEST] %s 当日涨停，从 AI 买入池移除', symbol)
            continue
        filtered.append(s)
    return filtered


def _get_prev_close_from_klines(
    klines: Dict[str, List[dict]],
    symbol: str,
) -> Optional[float]:
    """从 K 线列表中取最近一根收盘价作为前收盘价。"""
    bars = klines.get(symbol, [])
    if not bars:
        return None
    return bars[-1].get('c')


def _get_prev_trade_date(db: Session, d: date) -> Optional[date]:
    row = (
        db.query(models.TradeCalendar.trade_date)
        .filter(
            models.TradeCalendar.is_trading_day == 1,
            models.TradeCalendar.trade_date < d,
        )
        .order_by(models.TradeCalendar.trade_date.desc())
        .first()
    )
    return row[0] if row else None


def _get_next_trade_date(db: Session, d: date) -> Optional[date]:
    row = (
        db.query(models.TradeCalendar.trade_date)
        .filter(
            models.TradeCalendar.is_trading_day == 1,
            models.TradeCalendar.trade_date > d,
        )
        .order_by(models.TradeCalendar.trade_date.asc())
        .first()
    )
    return row[0] if row else None


def _validate_run_date(db: Session, d: date) -> Optional[str]:
    cal = (
        db.query(models.TradeCalendar)
        .filter(
            models.TradeCalendar.trade_date == d,
            models.TradeCalendar.is_trading_day == 1,
        )
        .first()
    )
    if not cal:
        return f'{d} 不是交易日'
    has_daily = (
        db.query(models.StockDaily)
        .filter(models.StockDaily.trade_date == d)
        .first()
    )
    if not has_daily:
        return f'{d} 无日线数据，请先同步'
    return None


def _get_candidate_stocks(db: Session, trade_date: date) -> List[dict]:
    """使用系统主升浪选股接口获取候选股票列表，应用与界面一致的默认筛选门槛。"""
    query = schemas.MainwavePickerQuery(
        trade_date=_fmt_date(trade_date),
        market='主板',
        exclude_st=True,
        exclude_cyb=True,
        exclude_kcb=True,
        exclude_bse=True,
        page_num=1,
        page_size=10000,
        **DEFAULT_POOL_FILTERS,
    )
    list_data, _total, _actual_date = stock_basic_crud.get_mainwave_list(db, query)
    stocks = []
    for r in list_data:
        stocks.append({
            'symbol': r['symbol'],
            'name': r['stock_name'],
            'market': r['market'],
        })
    return stocks


def _get_pool(db: Session, trade_date: date) -> Tuple[List[dict], Dict[str, List]]:
    """计算当日可买入池子（主升浪 5/10/20 层），先过滤涨停股再分配名额。"""
    stocks = _get_candidate_stocks(db, trade_date)
    if not stocks:
        return [], {}

    # 先剔除当日涨停股，避免它们占用买入池名额
    symbols = [s['symbol'] for s in stocks]
    close_map = _get_close_for_symbols(db, symbols, trade_date)
    klines = _get_klines(db, symbols, trade_date)
    filtered: List[dict] = []
    for s in stocks:
        symbol = s['symbol']
        close = close_map.get(symbol)
        if close is None:
            continue
        prev_close = _get_prev_close_from_klines(klines, symbol)
        if prev_close is not None and _is_limit_up(
            close, prev_close, symbol, s.get('name') or symbol
        ):
            logger.info('[BACKTEST] %s 当日涨停，不参与池子排名', symbol)
            continue
        filtered.append(s)
    stocks = filtered
    if not stocks:
        return [], {}

    records_by_symbol = mainwave_scorer.batch_calculate_mainwave_layers(
        db, stocks, _fmt_date(trade_date)
    )
    mainwave_scorer.batch_calculate_scores(
        db, stocks, _fmt_date(trade_date), records_by_symbol=records_by_symbol
    )

    # 按 layer 分组并组内按评分降序
    layer_groups: Dict[int, List[dict]] = {5: [], 10: [], 20: []}
    for s in stocks:
        layer = s.get('layer')
        if layer in layer_groups:
            layer_groups[layer].append(s)
    for layer in layer_groups:
        layer_groups[layer].sort(
            key=lambda s: s.get('score', {}).get('total', 0),
            reverse=True,
        )

    counts = {layer: len(group) for layer, group in layer_groups.items()}
    non_empty = [layer for layer, count in counts.items() if count > 0]
    if not non_empty:
        return [], records_by_symbol

    total = sum(counts[layer] for layer in non_empty)
    target = min(BUY_POOL_TOP_N, total)

    # 按比例分配，非空 layer 至少 1 个
    raw = {layer: target * counts[layer] / total for layer in non_empty}
    allocated = {layer: 0 for layer in (5, 10, 20)}
    for layer in non_empty:
        allocated[layer] = max(1, int(raw[layer]))

    # 用最大余数法调整至总和为 target
    remaining = target - sum(allocated[layer] for layer in non_empty)
    if remaining > 0:
        remainders = {layer: raw[layer] - int(raw[layer]) for layer in non_empty}
        sorted_layers = sorted(non_empty, key=lambda l: remainders[l], reverse=True)
        for i in range(remaining):
            allocated[sorted_layers[i % len(sorted_layers)]] += 1
    elif remaining < 0:
        sorted_layers = sorted(
            non_empty,
            key=lambda l: raw[l] - allocated[l],
        )
        for layer in sorted_layers:
            if remaining == 0:
                break
            if allocated[layer] > 1:
                allocated[layer] -= 1
                remaining += 1

    # 重新计算剩余，后续只处理封顶/再分配
    remaining = target - sum(allocated[layer] for layer in non_empty)

    # 不能超过该 layer 实际数量，余额再分配
    for layer in non_empty:
        if allocated[layer] > counts[layer]:
            remaining += allocated[layer] - counts[layer]
            allocated[layer] = counts[layer]
    if remaining > 0:
        expandable = [l for l in non_empty if allocated[l] < counts[l]]
        expandable.sort(key=lambda l: counts[l] - allocated[l], reverse=True)
        for i in range(remaining):
            allocated[expandable[i % len(expandable)]] += 1

    pool: List[dict] = []
    for layer in (5, 10, 20):
        pool.extend(layer_groups[layer][:allocated[layer]])

    # 补充当日 MA 数据及量价/回调/动能指标
    _calc_pool_metrics(pool, records_by_symbol, trade_date)

    # 按（良性回调 + 动能）综合评分排序，让更优候选排在前面
    pool.sort(
        key=lambda s: (s.get('pullback_score', 0) + s.get('momentum_score', 0)),
        reverse=True,
    )

    return pool, records_by_symbol


def _calc_pool_metrics(
    pool: List[dict],
    records_by_symbol: Dict[str, List],
    trade_date: date,
) -> None:
    """为候选池计算良性回调评分、动能评分、量比等辅助指标。"""
    for s in pool:
        symbol = s['symbol']
        recs = records_by_symbol.get(symbol, [])
        if not recs:
            continue
        sorted_recs = sorted(recs, key=lambda r: r[0])
        current_idx = None
        for i, r in enumerate(sorted_recs):
            if r[0] == trade_date:
                current_idx = i
                break
        if current_idx is None:
            continue

        cur = sorted_recs[current_idx]
        close = float(cur[1]) if cur[1] is not None else None
        ma5 = float(cur[4]) if cur[4] is not None else None
        ma10 = float(cur[5]) if cur[5] is not None else None
        ma20 = float(cur[6]) if cur[6] is not None else None
        turnover = float(cur[3]) if cur[3] is not None else None
        turnover_ma5 = float(cur[7]) if cur[7] is not None else None

        if close is None or ma5 is None or ma10 is None or ma20 is None:
            continue

        recent_window = sorted_recs[max(0, current_idx - 4):current_idx + 1]
        recent_closes = [float(r[1]) for r in recent_window if r[1] is not None]
        recent_high = max(recent_closes) if recent_closes else close
        momentum_5d = sum(float(r[2]) for r in recent_window if r[2] is not None)

        longer_window = sorted_recs[max(0, current_idx - 9):current_idx + 1]
        momentum_10d = sum(float(r[2]) for r in longer_window if r[2] is not None)

        # 良性回调评分：回踩短期均线、均线多头排列、缩量、仍有正向动能
        pb_score = 0
        if close < ma5:
            pb_score += 1
        if close > ma10:
            pb_score += 1
        if ma5 > ma10 > ma20:
            pb_score += 1
        if momentum_5d > 0:
            pb_score += 1
        if (
            turnover is not None
            and turnover_ma5 is not None
            and turnover_ma5 > 0
            and turnover < turnover_ma5
        ):
            pb_score += 1
        if close >= recent_high * 0.95:
            pb_score += 1
        s['ma5'] = ma5
        s['ma10'] = ma10
        s['ma20'] = ma20
        s['pullback_score'] = round(pb_score / 6, 2)

        # 动能评分：短期/中期涨幅、趋势偏离、放量
        mom_score = 0.0
        if momentum_5d > 0:
            mom_score += 0.3
        if momentum_10d > 0:
            mom_score += 0.2
        if ma20 > 0 and (close - ma20) / ma20 > 0:
            mom_score += 0.2
        if (
            turnover is not None
            and turnover_ma5 is not None
            and turnover_ma5 > 0
            and turnover / turnover_ma5 > 1
        ):
            mom_score += 0.3
        s['momentum_score'] = round(min(mom_score, 1.0), 2)

        if turnover is not None and turnover_ma5 is not None and turnover_ma5 > 0:
            s['volume_momentum'] = round(turnover / turnover_ma5, 2)


def _get_klines(db: Session, symbols: List[str], trade_date: date) -> Dict[str, List[dict]]:
    """获取 symbols 在操作日之前的最近 AI_KLINE_LIMIT 根日 K 线（收盘/涨跌幅/换手率，已压缩）"""
    if not symbols:
        return {}
    date_list = mainwave_scorer._get_date_list(
        db, _fmt_date(trade_date), limit=AI_KLINE_LIMIT + 1
    )
    records = mainwave_scorer._fetch_recent_records(db, symbols, date_list)
    result: Dict[str, List[dict]] = {}
    for symbol, recs in records.items():
        bars = []
        for r in recs:
            bar_date = r[0]
            if bar_date >= trade_date:
                continue
            bars.append({
                'd': str(bar_date),
                'c': float(r[1]) if r[1] is not None else None,
                'p': float(r[2]) if r[2] is not None else None,
                't': float(r[3]) if r[3] is not None else None,
            })
        bars.sort(key=lambda b: b['d'])
        result[symbol] = bars
    # 未来数据保护断言
    op_str = _fmt_date(trade_date)
    for symbol, bars in result.items():
        if bars:
            max_date = max(b['d'] for b in bars)
            assert max_date < op_str, f'future data leaked for {symbol}: {max_date}'
    return result


def _get_close_for_symbols(db: Session, symbols: List[str], trade_date: date) -> Dict[str, float]:
    if not symbols:
        return {}
    rows = (
        db.query(models.StockDaily.symbol, models.StockDaily.close)
        .filter(
            models.StockDaily.symbol.in_(symbols),
            models.StockDaily.trade_date == trade_date,
        )
        .all()
    )
    return {r.symbol: float(r.close) for r in rows if r.close is not None}


def _calc_positions(trades: List[models.BacktestTrade]) -> Dict[str, dict]:
    """基于交易记录计算当前持仓（综合成本法）"""
    pos: Dict[str, dict] = {}
    for t in trades:
        symbol = t.symbol
        if symbol not in pos:
            pos[symbol] = {
                'symbol': symbol,
                'name': t.name,
                'quantity': 0,
                'cost': 0.0,
            }
        p = pos[symbol]
        qty = int(t.quantity)
        amount = float(t.amount)
        if t.trade_type == 'BUY':
            p['quantity'] += qty
            p['cost'] += amount
        else:
            old_qty = p['quantity']
            p['quantity'] -= qty
            if old_qty > 0:
                p['cost'] -= p['cost'] * (qty / old_qty)
            if p['quantity'] <= 0:
                del pos[symbol]
    for p in pos.values():
        p['avg_cost'] = p['cost'] / p['quantity'] if p['quantity'] > 0 else 0
    return pos


def _build_prompt(
    trade_date: date,
    cash: float,
    total_asset: float,
    positions: Dict[str, dict],
    close_map: Dict[str, float],
    pool: List[dict],
    klines: Dict[str, List[dict]],
    records_by_symbol: Dict[str, List],
) -> List[dict]:
    holdings = []
    for symbol, p in positions.items():
        close = close_map.get(symbol)
        mv = close * p['quantity'] if close else 0
        unrealized = mv - p['cost'] if close else 0
        unrealized_pct = unrealized / p['cost'] * 100 if p['cost'] > 0 else 0
        ma5 = ma10 = ma20 = None
        recs = records_by_symbol.get(symbol, [])
        for r in recs:
            if r[0] == trade_date:
                ma5 = float(r[4]) if r[4] is not None else None
                ma10 = float(r[5]) if r[5] is not None else None
                ma20 = float(r[6]) if r[6] is not None else None
                break
        bars = klines.get(symbol, [])[-AI_KLINE_LIMIT:]
        holdings.append({
            's': symbol,
            'n': p['name'],
            'q': p['quantity'],
            'ac': round(p['avg_cost'], 4),
            'c': close,
            'mv': round(mv, 2),
            'up': round(unrealized_pct, 2),
            'm5': ma5,
            'm10': ma10,
            'm20': ma20,
            'ld': (
                close is not None
                and bars
                and bars[-1].get('c') is not None
                and _is_limit_down(close, bars[-1]['c'], symbol, p['name'] or symbol)
            ),
            'k': bars,
        })

    buyable = []
    for s in pool:
        symbol = s['symbol']
        bars = klines.get(symbol, [])[-AI_KLINE_LIMIT:]
        buyable.append({
            's': symbol,
            'n': s.get('name'),
            'l': s.get('layer'),
            'c': s.get('close'),
            'm5': s.get('ma5'),
            'm10': s.get('ma10'),
            'm20': s.get('ma20'),
            'pb': s.get('pullback_score'),
            'mom': s.get('momentum_score'),
            'vm': s.get('volume_momentum'),
            'k': bars,
        })

    system_msg = (
        '你是量化回测交易助手。请严格基于提供的历史数据做决策，绝不可使用未来价格。'
        '你必须只输出合法 JSON，不要包含 Markdown 代码块或其他解释。'
        'JSON 格式：{"sell": [{"symbol": "代码", "quantity": 股数}], "buy": [...], "reasoning": "理由"}。'
        '所有股数必须是 100 的整数倍。reasoning 控制在 80 字以内。'
        '你的定位是短期和中期趋势选手，基于 K 线形态、均线排列、换手率变化、量价关系与动能做综合判断。'
        '目标是在控制风险的前提下尽量满仓运作，避免大量现金闲置；'
        '单只个股仓位建议不低于总资产的 20%，持仓数量尽量接近上限 3 只。'
        '买入时必须基于当前可用现金计算股数。若计划先卖出持仓再买入，需确保卖出后到账的现金足够支付买入金额，'
        '且单只股票买入金额不得超过卖出后预计可用现金。避免提出超出资金能力的买入数量。'
        '买入时从候选池中做综合分析，构建最优组合，尽量避免买入同方向或同板块的个股以分散风险。'
        '候选池已剔除当日涨停的股票，不要试图买入不在候选池中的股票。'
        '买入决策请重点关注以下信号，优先级：良性回调（pb 高） > 量价动能强劲（mom 高、vm>1） > 均线多头排列。'
        'pb 衡量良性回调：股价回踩 MA5/MA10、均线多头排列、回调缩量、近期仍保持正向动能。'
        'mom/vm 衡量量价动能：mom 高表示短期/中期涨幅、趋势、放量均强；vm>1 表示当日换手高于 5 日均值，资金活跃。'
        '避免买入已大幅冲高、放量滞涨、缩量阴跌或 pb/mom 双低的标的。'
        '当某只持仓股的短期或中期上涨趋势不再成立、出现放量滞涨或跌破关键均线时，可果断卖出；'
        '若持仓的 ld 字段为 true，表示该股票当日跌停，不允许卖出，请勿对其发起卖出。'
        '字段缩写：K线 d=日期,c=收盘,p=涨跌幅,t=换手率; '
        '持仓/池子 s=代码,n=名称,q=股数,ac=均价,c=收盘价,mv=市值,up=浮动盈亏%,l=层,m5/m10/m20=均线,ld=跌停,k=K线列表;'
        '池子额外字段 pb=良性回调评分(0-1),mom=动能评分(0-1),vm=量比(对5日均值)。'
    )
    user_msg = {
        'od': _fmt_date(trade_date),
        'cash': round(cash, 2),
        'ta': round(total_asset, 2),
        'cons': {
            'max_positions': MAX_POSITIONS,
            'min_single_position_ratio': MIN_POSITION_RATIO,
            'buy_only_from_pool': True,
            'quantity_multiple_of': 100,
            'cannot_exceed_cash': True,
            'sell_before_buy': True,
        },
        'hold': holdings,
        'pool': buyable,
    }
    return [
        {'role': 'system', 'content': system_msg},
        {'role': 'user', 'content': json.dumps(user_msg, ensure_ascii=False, default=str)},
    ]


async def _call_ai(messages: List[dict], ai_model: str) -> Tuple[Optional[schemas.BacktestDecisionOutput], Optional[str], Optional[str]]:
    client = LlmClient(model=ai_model, timeout=AI_TIMEOUT_SECONDS, max_retries=0)
    raw_response = None
    try:
        resp = await client.chat(messages, temperature=0.5)
        raw_response = resp.choices[0].message.content or ''
        content = raw_response.strip()
        if content.startswith('```'):
            lines = content.splitlines()
            if lines and lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].startswith('```'):
                lines = lines[:-1]
            content = '\n'.join(lines).strip()
        data = json.loads(content)
        decision = schemas.BacktestDecisionOutput(**data)
        return decision, raw_response, None
    except Exception as exc:
        logger.warning('[BACKTEST_AI] AI 调用或解析失败: %s', exc)
        return None, raw_response, str(exc)


def _run_async(coro):
    """在同步上下文中运行异步协程"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


def _normalize_quantity(qty: int) -> int:
    return (qty // 100) * 100


def create_run(db: Session, obj_in: schemas.BacktestCreate) -> dict:
    """创建回测并自动执行开始日交易，返回 run 与首日执行结果"""
    start_date = _parse_date(obj_in.start_date)

    date_error = _validate_run_date(db, start_date)
    if date_error:
        adjusted = _get_next_trade_date(db, start_date)
        if not adjusted:
            raise ValueError(f'{start_date} 不是交易日，且之后无可用交易日')
        logger.info('[BACKTEST] 开始日 %s 非交易日，自动调整为 %s', start_date, adjusted)
        start_date = adjusted

    if obj_in.end_date:
        end_date = _parse_date(obj_in.end_date)
        if end_date < start_date:
            raise ValueError('结束日期不能早于开始日期')
        obj_in.end_date = _fmt_date(end_date)

    obj_in.start_date = _fmt_date(start_date)
    run = backtest_run_crud.create(db, obj_in)

    # 创建后立即执行开始日的买入决策
    try:
        result = _execute_step(db, run, start_date)
    except Exception:
        # AI 决策失败时回滚：删除已创建的 run，不保留空回测
        db.rollback()
        backtest_run_crud.delete(db, run.id)
        db.commit()
        raise

    return {
        'run': run,
        'snapshot': result['snapshot'],
        'trades': result['trades'],
        'reasoning': result['reasoning'],
        'pool': result['pool'],
    }


def step(db: Session, run_id: int) -> dict:
    """手动执行下一天"""
    run = backtest_run_crud.get_by_id(db, run_id)
    if not run:
        raise ValueError('回测不存在')
    if run.status not in ('running',):
        raise ValueError(f'回测状态为 {run.status}，无法继续')
    next_date = _get_next_trade_date(db, run.current_date)
    if not next_date:
        raise ValueError('没有更多交易日')
    if run.end_date and next_date > run.end_date:
        raise ValueError('已到达结束日期')
    return _execute_step(db, run, next_date)


def _execute_step(db: Session, run: models.BacktestRun, next_date: date) -> dict:
    error = _validate_run_date(db, next_date)
    if error:
        raise ValueError(error)

    trades_all = sorted(
        backtest_trade_crud.get_by_run_id(db, run.id, page_num=1, page_size=10000)[0],
        key=lambda t: (t.trade_date, t.id),
    )
    positions = _calc_positions(trades_all)
    symbols = list(positions.keys())

    pool, records_by_symbol = _get_pool(db, next_date)
    pool_symbols = [s['symbol'] for s in pool]
    all_symbols = list(set(symbols + pool_symbols))
    close_map = _get_close_for_symbols(db, all_symbols, next_date)

    for s in pool:
        s['close'] = close_map.get(s['symbol'])

    kline_symbols = list(set(symbols + pool_symbols))
    klines = _get_klines(db, kline_symbols, next_date)

    # 涨停股票不推送给 AI
    pool = _filter_pool_limit_up(pool, close_map, klines)
    pool_symbols = [s['symbol'] for s in pool]

    total_asset = float(run.cash) + sum(
        close_map.get(s, 0) * p['quantity'] for s, p in positions.items()
    )

    messages = _build_prompt(
        next_date, float(run.cash), total_asset, positions, close_map, pool, klines,
        records_by_symbol,
    )

    start_ms = int(time.time() * 1000)
    decision, raw_response, ai_error = _run_async(_call_ai(messages, run.ai_model))
    latency_ms = int(time.time() * 1000) - start_ms

    executed_trades: List[models.BacktestTrade] = []
    reasoning = decision.reasoning if decision else ''
    all_trades = list(trades_all)

    if decision:
        # 先卖
        for sell in decision.sell:
            symbol = sell.symbol
            qty = _normalize_quantity(sell.quantity)
            if qty <= 0:
                continue
            current_qty = sum(
                p['quantity'] for p in _calc_positions(all_trades).values() if p['symbol'] == symbol
            )
            if current_qty < qty:
                logger.warning('[BACKTEST] AI 卖出超持仓或无效: %s %s', symbol, qty)
                continue
            close = close_map.get(symbol)
            if close is None:
                logger.warning('[BACKTEST] AI 卖出无收盘价: %s', symbol)
                continue
            name = next((t.name for t in all_trades if t.symbol == symbol), symbol)
            prev_close = _get_prev_close_from_klines(klines, symbol)
            if prev_close is not None and _is_limit_down(close, prev_close, symbol, name):
                logger.warning('[BACKTEST] %s 当日跌停，无法卖出', symbol)
                continue
            amount = round(close * qty, 4)
            trade = backtest_trade_crud.create(db, run.id, {
                'symbol': symbol,
                'name': name,
                'trade_type': 'SELL',
                'trade_date': next_date,
                'price': close,
                'quantity': qty,
                'amount': amount,
                'fee': 0,
            })
            executed_trades.append(trade)
            all_trades.append(trade)

        # 后买
        for buy in decision.buy:
            symbol = buy.symbol
            qty = _normalize_quantity(buy.quantity)
            if qty <= 0:
                continue
            if symbol not in pool_symbols:
                logger.warning('[BACKTEST] AI 买入非池子股票: %s', symbol)
                continue
            close = close_map.get(symbol)
            if close is None:
                continue
            pool_item = next((s for s in pool if s['symbol'] == symbol), None)
            if not pool_item:
                continue
            prev_close = _get_prev_close_from_klines(klines, symbol)
            if prev_close is not None and _is_limit_up(close, prev_close, symbol, pool_item.get('name') or symbol):
                logger.warning('[BACKTEST] %s 当日涨停，无法买入', symbol)
                continue

            current_positions = _calc_positions(all_trades)
            executed_sell_total = sum(float(t.amount) for t in executed_trades if t.trade_type == 'SELL')
            executed_buy_total = sum(float(t.amount) for t in executed_trades if t.trade_type == 'BUY')
            current_cash = float(run.cash) + executed_sell_total - executed_buy_total
            current_total_asset = current_cash + sum(
                close_map.get(s, 0) * p['quantity'] for s, p in current_positions.items()
            )

            if len(current_positions) >= MAX_POSITIONS and symbol not in current_positions:
                logger.warning('[BACKTEST] AI 买入时持仓已达上限')
                continue

            # 若 AI 建议数量超现金，按比例缩至可用现金内，而非直接跳过
            if close * qty > current_cash:
                qty = int(current_cash / close // 100 * 100)
                if qty <= 0:
                    logger.warning('[BACKTEST] AI 买入金额超现金且无法缩放: %s', symbol)
                    continue

            position_value = close * qty
            if position_value < current_total_asset * MIN_POSITION_RATIO:
                min_qty = int((current_total_asset * MIN_POSITION_RATIO / close) // 100 * 100) + 100
                if min_qty * close <= current_cash and (len(current_positions) < MAX_POSITIONS or symbol in current_positions):
                    qty = min_qty
                else:
                    logger.warning('[BACKTEST] AI 买入仓位低于%s%%且无法补足: %s', int(MIN_POSITION_RATIO * 100), symbol)
                    continue

            amount = round(close * qty, 4)
            if amount > current_cash:
                logger.warning('[BACKTEST] AI 买入金额超现金: %s', symbol)
                continue

            trade = backtest_trade_crud.create(db, run.id, {
                'symbol': symbol,
                'name': pool_item.get('name') or symbol,
                'trade_type': 'BUY',
                'trade_date': next_date,
                'price': close,
                'quantity': qty,
                'amount': amount,
                'fee': 0,
            })
            executed_trades.append(trade)
            all_trades.append(trade)
    else:
        # AI 调用失败或超时，当日不交易，不推进日期
        raise ValueError(f'AI 调用失败（{ai_error or "无响应"}），决策未生效，当日不交易')

    # 计算当日快照
    final_positions = _calc_positions(all_trades)
    total_market_value = 0.0
    total_cost = 0.0
    for symbol, p in final_positions.items():
        close = close_map.get(symbol, 0)
        total_market_value += close * p['quantity']
        total_cost += p['cost']

    executed_sells = [t for t in executed_trades if t.trade_type == 'SELL']
    executed_buys = [t for t in executed_trades if t.trade_type == 'BUY']
    cash = float(run.cash) + sum(float(t.amount) for t in executed_sells) - sum(float(t.amount) for t in executed_buys)
    total_asset = cash + total_market_value

    prev_snapshot = (
        db.query(models.BacktestDailySnapshot)
        .filter(
            models.BacktestDailySnapshot.run_id == run.id,
            models.BacktestDailySnapshot.trade_date < next_date,
        )
        .order_by(models.BacktestDailySnapshot.trade_date.desc())
        .first()
    )
    prev_total_asset = float(prev_snapshot.total_asset) if prev_snapshot else float(run.initial_capital)
    daily_pnl = total_asset - prev_total_asset
    cumulative_pnl = total_asset - float(run.initial_capital)
    unrealized_pnl = total_market_value - total_cost

    snapshot = backtest_snapshot_crud.create(db, run.id, {
        'trade_date': next_date,
        'cash': round(cash, 4),
        'total_market_value': round(total_market_value, 4),
        'total_asset': round(total_asset, 4),
        'daily_pnl': round(daily_pnl, 4),
        'cumulative_pnl': round(cumulative_pnl, 4),
        'unrealized_pnl': round(unrealized_pnl, 4),
    })

    backtest_run_crud.update_state(
        db, run.id, next_date, round(cash, 4), round(total_market_value, 4)
    )

    backtest_decision_log_crud.create(db, run.id, {
        'trade_date': next_date,
        'prompt_snapshot': json.dumps(messages, ensure_ascii=False, default=str)[:8000],
        'llm_raw_response': (raw_response or '')[:4000],
        'parsed_actions': json.dumps(
            decision.model_dump() if decision else {'error': ai_error},
            ensure_ascii=False
        ),
        'latency_ms': latency_ms,
    })

    db.commit()

    return {
        'snapshot': snapshot,
        'trades': executed_trades,
        'reasoning': reasoning,
        'pool': pool,
    }


def run_until_end(db: Session, run_id: int, task_id: str, on_progress=None) -> dict:
    """自动运行回测直到结束日期，供后台线程调用"""
    from app.routes.backtest import _update_task_progress, _finish_task
    run = backtest_run_crud.get_by_id(db, run_id)
    if not run:
        raise ValueError('回测不存在')
    if not run.end_date:
        raise ValueError('未设置结束日期')

    total_steps = 0
    cursor = run.current_date
    while True:
        nxt = _get_next_trade_date(db, cursor)
        if not nxt or nxt > run.end_date:
            break
        total_steps += 1
        cursor = nxt
    if total_steps == 0:
        backtest_run_crud.update_state(db, run_id, run.current_date, float(run.cash), float(run.total_market_value), status='completed')
        db.commit()
        _finish_task(db, task_id, result={'run_id': run_id, 'steps': 0})
        return {'run_id': run_id, 'steps': 0}

    cursor = run.current_date
    step_idx = 0
    while True:
        nxt = _get_next_trade_date(db, cursor)
        if not nxt or nxt > run.end_date:
            break
        try:
            _execute_step(db, run, nxt)
        except Exception as exc:
            logger.error('[BACKTEST_AUTO] 执行步骤 %s 失败: %s', nxt, exc)
            backtest_run_crud.update_state(db, run_id, run.current_date, float(run.cash), float(run.total_market_value), status='failed')
            db.commit()
            _finish_task(db, task_id, error=str(exc))
            return {'run_id': run_id, 'error': str(exc)}
        cursor = nxt
        step_idx += 1
        if on_progress:
            on_progress(step_idx, total_steps)
        _update_task_progress(db, task_id, step_idx, total_steps)
        # 重新加载 run 以获取最新 current_date
        db.refresh(run)

    backtest_run_crud.update_state(db, run_id, run.current_date, float(run.cash), float(run.total_market_value), status='completed')
    db.commit()
    _finish_task(db, task_id, result={'run_id': run_id, 'steps': step_idx})
    return {'run_id': run_id, 'steps': step_idx}
