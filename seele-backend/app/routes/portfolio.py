"""
持仓管理路由
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import (
    portfolio_trade_crud,
    portfolio_closed_crud,
    portfolio_position_crud,
    stock_daily_crud,
    portfolio_config_crud,
    portfolio_daily_position_crud,
    portfolio_daily_summary_crud,
)
from app.database import get_db
from app.response import success, page_success, list_success

router = APIRouter(tags=['持仓管理'])


# ==================== 辅助函数 ====================


def _get_latest_close(db: Session, symbol: str, target_date: date = None) -> Optional[float]:
    """获取某股票最新收盘价"""
    query = db.query(models.StockDaily).filter(models.StockDaily.symbol == symbol)
    if target_date:
        query = query.filter(models.StockDaily.trade_date <= target_date)
    result = query.order_by(models.StockDaily.trade_date.desc()).first()
    return result.close if result else None


def _parse_trade_date_str(date_str: str) -> date:
    """解析交易日期字符串，兼容 YYYY-MM-DD 和 YYYY/MM/DD"""
    normalized = date_str.replace('/', '-')
    return datetime.strptime(normalized, '%Y-%m-%d').date()


def _validate_price_by_daily(db: Session, symbol: str, trade_date: date, price: float) -> Optional[str]:
    """根据当日日线最高价/最低价校验成交价格是否合理"""
    daily = (
        db.query(models.StockDaily)
        .filter(
            and_(
                models.StockDaily.symbol == symbol,
                models.StockDaily.trade_date == trade_date,
            )
        )
        .first()
    )
    if not daily:
        return None
    if daily.high is not None and price > daily.high:
        return f'成交价格 {price} 超过当日最高价 {daily.high}'
    if daily.low is not None and price < daily.low:
        return f'成交价格 {price} 低于当日最低价 {daily.low}'
    return None


def _get_latest_close_batch(db: Session, symbols: List[str]) -> dict[str, float]:
    """批量获取多只股票最新收盘价，返回 {symbol: close}

    使用每只股票各自的最新有数据日期，避免停牌股票因统一日期无数据而遗漏。
    """
    if not symbols:
        return {}

    from sqlalchemy import func

    subq = (
        db.query(
            models.StockDaily.symbol,
            func.max(models.StockDaily.trade_date).label('max_date')
        )
        .filter(models.StockDaily.symbol.in_(symbols))
        .group_by(models.StockDaily.symbol)
        .subquery()
    )

    results = (
        db.query(models.StockDaily.symbol, models.StockDaily.close)
        .join(
            subq,
            and_(
                models.StockDaily.symbol == subq.c.symbol,
                models.StockDaily.trade_date == subq.c.max_date
            )
        )
        .all()
    )

    return {r.symbol: r.close for r in results}


def _get_config(db: Session) -> models.PortfolioConfig:
    """获取持仓配置，不存在则创建默认"""
    return portfolio_config_crud.get_or_create(db)


def _calc_trade_fees(
    trade_type: str,
    amount: float,
    commission_rate: float,
    stamp_tax_rate: float,
    transfer_rate: float,
) -> dict:
    """根据交易类型和配置费率计算印花税、过户费及券商佣金

    券商佣金部分按不免五处理（最低 5 元）。
    返回: {'commission': ..., 'stamp_tax': ..., 'transfer_fee': ...}
    """
    amount = float(amount)
    commission = round(max(amount * commission_rate, 5.0), 2)
    stamp_tax = round(amount * stamp_tax_rate, 2) if trade_type == 'SELL' else 0.0
    transfer_fee = round(amount * transfer_rate, 2)
    return {
        'commission': commission,
        'stamp_tax': stamp_tax,
        'transfer_fee': transfer_fee,
    }


def _apply_trade_fees(data: dict, trade_type: str, config: models.PortfolioConfig) -> dict:
    """根据配置自动补齐交易费用

    规则：
    - 如果 commission / stamp_tax / transfer_fee 未传入，按默认费率自动计算。
    - 券商佣金部分始终按 amount * commission_rate 计算，不免五（最低 5 元）。
    """
    amount = float(data.get('amount', 0))
    commission_rate = float(config.commission_rate)
    stamp_tax_rate = float(config.stamp_tax_rate)
    transfer_rate = float(config.transfer_rate)

    auto_fees = _calc_trade_fees(trade_type, amount, commission_rate, stamp_tax_rate, transfer_rate)

    for key in ('commission', 'stamp_tax', 'transfer_fee'):
        if data.get(key) is None:
            data[key] = auto_fees[key]

    return data


def _calc_comprehensive_position(trades: List[models.PortfolioTrade]) -> tuple[int, float]:
    """综合成本（摊薄成本）计算当前持仓数量和剩余成本
    返回: (quantity, remaining_cost)
    """
    total_buy = sum(float(t.amount) for t in trades if t.trade_type == 'BUY')
    total_sell = sum(float(t.amount) for t in trades if t.trade_type == 'SELL')
    total_buy_qty = sum(t.quantity for t in trades if t.trade_type == 'BUY')
    total_sell_qty = sum(t.quantity for t in trades if t.trade_type == 'SELL')
    qty = total_buy_qty - total_sell_qty
    cost = total_buy - total_sell
    return qty, cost


def _calc_new_sell_comprehensive_cost(existing_trades: List[models.PortfolioTrade], sell_quantity: int) -> float:
    """基于已有交易记录，按综合成本计算新的一笔卖出对应的成本"""
    total_buy = sum(float(t.amount) for t in existing_trades if t.trade_type == 'BUY')
    total_sell = sum(float(t.amount) for t in existing_trades if t.trade_type == 'SELL')
    total_buy_qty = sum(t.quantity for t in existing_trades if t.trade_type == 'BUY')
    total_sell_qty = sum(t.quantity for t in existing_trades if t.trade_type == 'SELL')
    current_qty = total_buy_qty - total_sell_qty
    avg_cost = (total_buy - total_sell) / current_qty if current_qty > 0 else 0
    return sell_quantity * avg_cost


def _calc_closed_for_symbol(db: Session, symbol: str) -> Optional[dict]:
    """计算某股票的清仓盈亏，若未清仓返回 None"""
    trades = portfolio_trade_crud.get_by_symbol(db, symbol)
    if not trades:
        return None

    buys = [t for t in trades if t.trade_type == 'BUY']
    sells = [t for t in trades if t.trade_type == 'SELL']

    total_buy_qty = sum(b.quantity for b in buys)
    total_sell_qty = sum(s.quantity for s in sells)

    if total_sell_qty < total_buy_qty:
        return None

    total_buy_amount = sum(float(b.amount) for b in buys)
    total_sell_amount = sum(float(s.amount) for s in sells)
    total_fee = sum(
        float(t.commission or 0) + float(t.stamp_tax or 0) + float(t.transfer_fee or 0)
        for t in trades
    )
    total_dividend = sum(float(t.dividend or 0) for t in trades)
    total_quantity = total_buy_qty
    avg_buy = total_buy_amount / total_quantity if total_quantity > 0 else 0
    avg_sell = total_sell_amount / total_sell_qty if total_sell_qty > 0 else 0
    realized_pnl = total_sell_amount - total_buy_amount - total_fee + total_dividend
    pnl_pct = realized_pnl / total_buy_amount * 100 if total_buy_amount > 0 else 0

    return {
        'symbol': symbol,
        'name': trades[0].name,
        'total_buy_amount': round(total_buy_amount, 4),
        'total_sell_amount': round(total_sell_amount, 4),
        'total_quantity': total_quantity,
        'avg_buy_price': round(avg_buy, 4),
        'avg_sell_price': round(avg_sell, 4),
        'open_date': min(b.trade_date for b in buys),
        'close_date': max(s.trade_date for s in sells),
        'realized_pnl': round(realized_pnl, 4),
        'pnl_pct': round(pnl_pct, 4),
        'total_fee': round(total_fee, 4),
    }


def _calc_history_pnl(market_value: float, trades: List[models.PortfolioTrade]) -> float:
    """计算某只股票的历史盈亏（含已卖出部分、手续费和分红）"""
    total_buy = sum(float(t.amount) for t in trades if t.trade_type == 'BUY')
    total_sell = sum(float(t.amount) for t in trades if t.trade_type == 'SELL')
    total_fee = sum(
        float(t.commission or 0) + float(t.stamp_tax or 0) + float(t.transfer_fee or 0)
        for t in trades
    )
    total_dividend = sum(float(t.dividend or 0) for t in trades)
    return market_value + total_sell - total_buy - total_fee + total_dividend


def _calc_current_holding_start_date(trades: List[models.PortfolioTrade]) -> Optional[date]:
    """计算当前连续持仓周期的起始买入日期

    从今天往前推，找到最近一次持仓数量从 0 变为大于 0 的买入交易日。
    如果当前没有持仓，返回 None。
    """
    sorted_trades = sorted(trades, key=lambda t: (t.trade_date, t.id))
    current_qty = 0
    start_date = None
    for t in sorted_trades:
        if t.trade_type == 'BUY':
            if current_qty == 0:
                start_date = t.trade_date
            current_qty += t.quantity
        else:
            current_qty -= t.quantity
            if current_qty <= 0:
                current_qty = 0
                start_date = None
    return start_date


def _calc_current_pnl(market_value: float, trades: List[models.PortfolioTrade]) -> float:
    """计算当前连续持仓周期的盈亏（含本周期内已卖出部分、手续费和分红）"""
    start_date = _calc_current_holding_start_date(trades)
    if start_date is None:
        return 0.0
    period_trades = [t for t in trades if t.trade_date >= start_date]
    return _calc_history_pnl(market_value, period_trades)


def _sync_position_snapshot(db: Session, symbol: str) -> Optional[models.PortfolioPosition]:
    """同步单个股票的持仓快照"""
    trades = portfolio_trade_crud.get_by_symbol(db, symbol)
    if not trades:
        portfolio_position_crud.delete_by_symbol(db, symbol)
        return None

    qty, cost = _calc_comprehensive_position(trades)
    if qty <= 0:
        portfolio_position_crud.delete_by_symbol(db, symbol)
        return None

    avg_cost = cost / qty if qty > 0 else 0
    current_price = _get_latest_close(db, symbol)
    market_value = round(float(current_price) * qty, 4) if current_price else None
    unrealized_pnl = round(market_value - cost, 4) if market_value else None
    unrealized_pnl_pct = round(unrealized_pnl / cost * 100, 4) if unrealized_pnl and cost > 0 else None

    buys = [t for t in trades if t.trade_type == 'BUY']
    first_buy_date = min(b.trade_date for b in buys) if buys else None

    # 保留已有的止损止盈设置
    existing = portfolio_position_crud.get_by_symbol(db, symbol)
    stop_loss = existing.stop_loss_price if existing else None
    take_profit = existing.take_profit_price if existing else None
    group = existing.group if existing else 'default'
    remark = existing.remark if existing else None

    data = {
        'symbol': symbol,
        'name': trades[0].name,
        'quantity': qty,
        'avg_cost': round(avg_cost, 4),
        'current_price': current_price,
        'market_value': market_value,
        'unrealized_pnl': unrealized_pnl,
        'unrealized_pnl_pct': unrealized_pnl_pct,
        'stop_loss_price': stop_loss,
        'take_profit_price': take_profit,
        'alert_triggered': 0,
        'group': group,
        'remark': remark,
        'first_buy_date': first_buy_date,
    }

    return portfolio_position_crud.upsert(db, data)


def _sync_all_positions(db: Session) -> None:
    """同步所有持仓快照（批量优化版）"""
    all_trades = portfolio_trade_crud.get_all(db)
    symbols = sorted(set(t.symbol for t in all_trades))
    if not symbols:
        portfolio_position_crud.delete_all(db)
        return

    # 批量获取最新收盘价和现有持仓
    price_map = _get_latest_close_batch(db, symbols)
    existing_map = {
        p.symbol: p
        for p in portfolio_position_crud.get_list(db)
    }

    # 按 symbol 分组交易记录
    trades_by_symbol: dict[str, list] = {}
    for t in all_trades:
        trades_by_symbol.setdefault(t.symbol, []).append(t)

    upsert_items = []
    symbols_to_delete = []
    for symbol in symbols:
        trades = trades_by_symbol.get(symbol, [])
        if not trades:
            symbols_to_delete.append(symbol)
            continue
        qty, cost = _calc_comprehensive_position(trades)
        if qty <= 0:
            symbols_to_delete.append(symbol)
            continue

        avg_cost = cost / qty if qty > 0 else 0
        current_price = price_map.get(symbol)
        market_value = round(float(current_price) * qty, 4) if current_price else None
        unrealized_pnl = round(market_value - cost, 4) if market_value else None
        unrealized_pnl_pct = round(unrealized_pnl / cost * 100, 4) if unrealized_pnl and cost > 0 else None

        buys = [t for t in trades if t.trade_type == 'BUY']
        first_buy_date = min(b.trade_date for b in buys) if buys else None

        existing = existing_map.get(symbol)
        upsert_items.append({
            'symbol': symbol,
            'name': trades[0].name,
            'quantity': qty,
            'avg_cost': round(avg_cost, 4),
            'current_price': current_price,
            'market_value': market_value,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_pct': unrealized_pnl_pct,
            'stop_loss_price': existing.stop_loss_price if existing else None,
            'take_profit_price': existing.take_profit_price if existing else None,
            'group': existing.group if existing else 'default',
            'remark': existing.remark if existing else None,
            'first_buy_date': first_buy_date,
        })

    # 清理应删除的持仓快照：
    # 1. 当前无交易记录或已清仓的股票
    # 2. 交易记录被删除后残留的幽灵持仓
    keep_symbols = {symbol for symbol in symbols if symbol not in symbols_to_delete}
    for symbol in list(existing_map.keys()):
        if symbol not in keep_symbols:
            portfolio_position_crud.delete_by_symbol(db, symbol)

    portfolio_position_crud.upsert_batch(db, upsert_items)


def _sync_all_closed(db: Session) -> None:
    """全量重建所有清仓记录"""
    all_trades = portfolio_trade_crud.get_all(db)
    symbols = sorted(set(t.symbol for t in all_trades))

    # 先清空全部清仓记录
    portfolio_closed_crud.delete_all(db)

    # 按 symbol 分组并重新计算
    trades_by_symbol: dict[str, list] = {}
    for t in all_trades:
        trades_by_symbol.setdefault(t.symbol, []).append(t)

    for symbol in symbols:
        closed_data = _calc_closed_for_symbol(db, symbol)
        if closed_data:
            portfolio_closed_crud.create(db, closed_data)


def _rebuild_daily_data(db: Session) -> list[str]:
    """全量重建每日持仓明细和资产汇总实体表

    基于交易记录和日线数据，逐日计算每只股票的持仓状态，
    写入 portfolio_daily_position 和 portfolio_daily_summary。

    返回缺失日线数据的记录列表，格式: ['symbol@YYYY-MM-DD', ...]
    """
    all_trades = portfolio_trade_crud.get_all(db)
    if not all_trades:
        portfolio_daily_position_crud.delete_all(db)
        portfolio_daily_summary_crud.delete_all(db)
        db.commit()
        return []

    trade_dates = stock_daily_crud.get_trade_dates(db)
    trade_dates.sort()

    symbols = set(t.symbol for t in all_trades)
    all_dailies = stock_daily_crud.get_batch(db, list(symbols))
    symbol_dailies: dict[str, dict] = {}
    for d in all_dailies:
        symbol_dailies.setdefault(d.symbol, {})[d.trade_date] = d.close

    # 按 symbol + date 预计算每日手续费，用于准确的 daily_pnl
    fee_by_symbol_date: dict[str, dict] = {}
    for t in all_trades:
        fee_by_symbol_date.setdefault(t.symbol, {}).setdefault(t.trade_date, 0.0)
        fee_by_symbol_date[t.symbol][t.trade_date] += (
            float(t.commission or 0) + float(t.stamp_tax or 0) + float(t.transfer_fee or 0)
        )

    # 逐 symbol 重建每日持仓明细
    symbol_day_details = {s: {} for s in symbols}
    missing_data: list[str] = []
    for symbol in symbols:
        trades = sorted([t for t in all_trades if t.symbol == symbol], key=lambda x: (x.trade_date, x.id))
        daily_map = symbol_dailies.get(symbol, {})
        t_idx = 0
        for d in trade_dates:
            day_buy = 0.0
            day_sell = 0.0
            while t_idx < len(trades) and trades[t_idx].trade_date <= d:
                t = trades[t_idx]
                if t.trade_type == 'BUY':
                    day_buy += float(t.amount)
                else:
                    day_sell += float(t.amount)
                t_idx += 1

            past_trades = [tt for tt in trades if tt.trade_date <= d]
            qty, rem_cost = _calc_comprehensive_position(past_trades)
            avg_cost = rem_cost / qty if qty > 0 else 0
            close_price = daily_map.get(d)
            if qty > 0 and close_price is None:
                missing_data.append(f'{symbol}@{d}')
            market_value = qty * float(close_price) if close_price else 0
            unrealized_pnl = market_value - rem_cost if qty > 0 else 0
            symbol_day_details[symbol][d] = {
                'qty': qty,
                'avg_cost': avg_cost,
                'close_price': close_price,
                'market_value': market_value,
                'day_buy': day_buy,
                'day_sell': day_sell,
                'unrealized_pnl': unrealized_pnl,
            }

    # 汇总计算每日资产汇总
    position_items = []
    summary_items = []
    prev_mv = 0.0
    cumulative_pnl = 0.0

    for d in trade_dates:
        day_symbols = [s for s in symbols if symbol_day_details[s].get(d)]
        if not day_symbols:
            continue

        has_position = any(symbol_day_details[s][d]['qty'] > 0 for s in day_symbols)
        has_trade = any(symbol_day_details[s][d]['day_buy'] > 0 or symbol_day_details[s][d]['day_sell'] > 0 for s in day_symbols)

        if not has_position and not has_trade:
            continue

        today_mv = 0.0
        today_buy = 0.0
        today_sell = 0.0
        day_fee = 0.0
        total_invested = 0.0
        total_unrealized = 0.0

        for s in day_symbols:
            det = symbol_day_details[s][d]
            q = det['qty']
            cp = det['close_price']
            mv = q * float(cp) if q > 0 and cp else 0.0
            today_mv += mv
            today_buy += det['day_buy']
            today_sell += det['day_sell']
            day_fee += fee_by_symbol_date.get(s, {}).get(d, 0.0)
            if q > 0:
                total_invested += q * det['avg_cost']
                total_unrealized += det['unrealized_pnl']

            # 写入每日持仓明细
            trade = next((t for t in all_trades if t.symbol == s), None)
            if trade is None:
                continue
            position_items.append({
                'trade_date': d,
                'symbol': s,
                'name': trade.name,
                'quantity': q,
                'avg_cost': round(det['avg_cost'], 4),
                'close_price': cp,
                'market_value': round(mv, 4),
                'day_buy': round(det['day_buy'], 4),
                'day_sell': round(det['day_sell'], 4),
                'unrealized_pnl': round(det['unrealized_pnl'], 4),
            })

        daily_pnl = today_mv - prev_mv - today_buy + today_sell - day_fee
        cumulative_pnl += daily_pnl
        prev_mv = today_mv

        summary_items.append({
            'trade_date': d,
            'total_invested': round(total_invested, 4),
            'total_market_value': round(today_mv, 4),
            'daily_pnl': round(daily_pnl, 4),
            'cumulative_pnl': round(cumulative_pnl, 4),
            'realized_pnl': 0,
            'unrealized_pnl': round(total_unrealized, 4),
        })

    # 存在缺失数据时不写入，保留旧数据，由调用方报错
    if missing_data:
        return missing_data

    portfolio_daily_position_crud.delete_all(db)
    portfolio_daily_summary_crud.delete_all(db)

    if position_items:
        portfolio_daily_position_crud.create_batch(db, position_items)
    if summary_items:
        portfolio_daily_summary_crud.create_batch(db, summary_items)

    db.commit()
    return []


# ==================== 交易记录接口 ====================

@router.post('/portfolio/trades')
def create_trade(
    obj_in: schemas.PortfolioTradeCreate,
    db: Session = Depends(get_db),
):
    """录入交易记录（买入或卖出）"""
    if obj_in.trade_type not in ('BUY', 'SELL'):
        return {'code': 400, 'message': 'trade_type 必须为 BUY 或 SELL'}

    # 价格合理性校验
    trade_date_obj = _parse_trade_date_str(obj_in.trade_date)
    price_err = _validate_price_by_daily(db, obj_in.symbol, trade_date_obj, obj_in.price)
    if price_err:
        return {'code': 400, 'message': price_err}

    data = obj_in.model_dump()
    if data.get('amount') is None and data.get('price') and data.get('quantity'):
        data['amount'] = round(data['price'] * data['quantity'], 4)

    config = _get_config(db)
    data = _apply_trade_fees(data, obj_in.trade_type, config)

    trade = models.PortfolioTrade(**data)
    db.add(trade)
    db.flush()
    db.refresh(trade)

    # 同步该股票的持仓快照
    _sync_position_snapshot(db, obj_in.symbol)

    # 如果是卖出，检查是否清仓
    if obj_in.trade_type == 'SELL':
        closed_data = _calc_closed_for_symbol(db, obj_in.symbol)
        if closed_data:
            # 删除该 symbol 已有的清仓记录（若存在），然后重新写入
            db.query(models.PortfolioClosed).filter(
                models.PortfolioClosed.symbol == obj_in.symbol
            ).delete()
            portfolio_closed_crud.create(db, closed_data)

    db.commit()
    return success(schemas.PortfolioTradeResponse.model_validate(trade).model_dump(), message='录入成功')


@router.post('/portfolio/day-trades')
def create_day_trade(
    obj_in: schemas.PortfolioDayTradeCreate,
    db: Session = Depends(get_db),
):
    """录入做T交易：同一天同股票同股数的一买一卖，fee=0"""
    if obj_in.buy_price <= 0 or obj_in.sell_price <= 0:
        return {'code': 400, 'message': '买入价和卖出价必须大于0'}
    if obj_in.quantity <= 0 or obj_in.quantity % 100 != 0:
        return {'code': 400, 'message': '成交股数必须为100股的整数倍且大于0'}

    trade_date_obj = _parse_trade_date_str(obj_in.trade_date)

    buy_err = _validate_price_by_daily(db, obj_in.symbol, trade_date_obj, obj_in.buy_price)
    if buy_err:
        return {'code': 400, 'message': f'买入{buy_err}'}
    sell_err = _validate_price_by_daily(db, obj_in.symbol, trade_date_obj, obj_in.sell_price)
    if sell_err:
        return {'code': 400, 'message': f'卖出{sell_err}'}

    quantity = obj_in.quantity
    buy_amount = round(obj_in.buy_price * quantity, 4)
    sell_amount = round(obj_in.sell_price * quantity, 4)
    remark = '[做T]'

    buy_trade = models.PortfolioTrade(
        symbol=obj_in.symbol,
        name=obj_in.name,
        trade_type='BUY',
        trade_date=trade_date_obj,
        price=obj_in.buy_price,
        quantity=quantity,
        amount=buy_amount,
        stamp_tax=0,
        transfer_fee=0,
        commission=0,
        dividend=0,
        remark=remark,
    )
    sell_trade = models.PortfolioTrade(
        symbol=obj_in.symbol,
        name=obj_in.name,
        trade_type='SELL',
        trade_date=trade_date_obj,
        price=obj_in.sell_price,
        quantity=quantity,
        amount=sell_amount,
        stamp_tax=0,
        transfer_fee=0,
        commission=0,
        dividend=0,
        remark=remark,
    )

    db.add(buy_trade)
    db.add(sell_trade)
    db.flush()

    _sync_position_snapshot(db, obj_in.symbol)

    closed_data = _calc_closed_for_symbol(db, obj_in.symbol)
    if closed_data:
        db.query(models.PortfolioClosed).filter(
            models.PortfolioClosed.symbol == obj_in.symbol
        ).delete()
        portfolio_closed_crud.create(db, closed_data)

    db.commit()
    return success(message='做T录入成功')


@router.get('/portfolio/trades')
def get_trades(
    symbol: Optional[str] = None,
    trade_type: Optional[str] = None,
    page_num: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """查询交易记录列表"""
    query = schemas.PortfolioTradeQuery(
        page_num=page_num,
        page_size=page_size,
        symbol=symbol,
        trade_type=trade_type,
    )
    list_data, total = portfolio_trade_crud.get_list(db, query)
    items = [schemas.PortfolioTradeResponse.model_validate(i).model_dump() for i in list_data]
    return page_success(items, total, page_num, page_size)


@router.put('/portfolio/trades/{id}')
def update_trade(
    id: int,
    obj_in: schemas.PortfolioTradeUpdate,
    db: Session = Depends(get_db),
):
    """更新交易记录，并重新计算该股票的持仓与清仓状态"""
    trade = portfolio_trade_crud.get_by_id(db, id)
    if not trade:
        raise HTTPException(status_code=404, detail='交易记录不存在')

    update_data = obj_in.model_dump(exclude_unset=True)
    if update_data.get('amount') is None and update_data.get('price') and update_data.get('quantity'):
        update_data['amount'] = round(update_data['price'] * update_data['quantity'], 4)

    # 日期字段统一转为 date 对象，避免后续比较时出现 str vs date 的类型错误
    if 'trade_date' in update_data:
        update_data['trade_date'] = _parse_trade_date_str(update_data['trade_date'])

    # 价格合理性校验（修改了价格或日期时）
    if 'price' in update_data or 'trade_date' in update_data:
        check_date = update_data['trade_date'] if 'trade_date' in update_data else trade.trade_date
        check_price = update_data['price'] if 'price' in update_data else trade.price
        price_err = _validate_price_by_daily(db, trade.symbol, check_date, check_price)
        if price_err:
            return {'code': 400, 'message': price_err}

    config = _get_config(db)
    update_data = _apply_trade_fees(update_data, trade.trade_type, config)

    portfolio_trade_crud.update(db, id, update_data)

    symbol = trade.symbol
    # 重新同步持仓快照
    _sync_position_snapshot(db, symbol)

    # 重新计算清仓状态
    db.query(models.PortfolioClosed).filter(
        models.PortfolioClosed.symbol == symbol
    ).delete()

    closed_data = _calc_closed_for_symbol(db, symbol)
    if closed_data:
        portfolio_closed_crud.create(db, closed_data)

    # 重建每日持仓和资产数据（内部统一 commit）
    missing = _rebuild_daily_data(db)
    if missing:
        detail = f'持仓数据缺失日线收盘价: {", ".join(missing[:5])}' + (' 等' if len(missing) > 5 else '')
        return {'code': 400, 'message': detail, 'data': missing}
    return success(message='更新成功')


@router.delete('/portfolio/trades/{id}')
def delete_trade(id: int, db: Session = Depends(get_db)):
    """删除交易记录，并重新计算该股票的清仓状态"""
    trade = portfolio_trade_crud.get_by_id(db, id)
    if not trade:
        raise HTTPException(status_code=404, detail='交易记录不存在')

    symbol = trade.symbol
    portfolio_trade_crud.delete(db, id)

    # 重新同步持仓快照
    _sync_position_snapshot(db, symbol)

    # 重新计算清仓状态
    db.query(models.PortfolioClosed).filter(
        models.PortfolioClosed.symbol == symbol
    ).delete()

    closed_data = _calc_closed_for_symbol(db, symbol)
    if closed_data:
        portfolio_closed_crud.create(db, closed_data)

    # 重建每日持仓和资产数据（内部统一 commit）
    missing = _rebuild_daily_data(db)
    if missing:
        detail = f'持仓数据缺失日线收盘价: {", ".join(missing[:5])}' + (' 等' if len(missing) > 5 else '')
        return {'code': 400, 'message': detail, 'data': missing}
    return success(message='删除成功')


@router.post('/portfolio/sync')
def sync_positions(db: Session = Depends(get_db)):
    """手动触发全部持仓快照同步、清仓记录重建和每日数据重建"""
    _sync_all_positions(db)
    _sync_all_closed(db)
    missing = _rebuild_daily_data(db)
    if missing:
        detail = f'持仓数据缺失日线收盘价: {", ".join(missing[:5])}' + (' 等' if len(missing) > 5 else '')
        return {'code': 400, 'message': detail, 'data': missing}
    return success(message='同步完成')


# ==================== 持仓与清仓接口 ====================

@router.get('/portfolio/positions')
def get_positions(
    group: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取当前持仓及浮动盈亏（实时价格计算）"""
    positions = portfolio_position_crud.get_list(db, group)
    symbols = [p.symbol for p in positions]
    price_map = _get_latest_close_batch(db, symbols)

    # 批量获取交易记录，用于计算历史盈亏
    all_trades = (
        db.query(models.PortfolioTrade)
        .filter(models.PortfolioTrade.symbol.in_(symbols))
        .all()
    )
    trades_by_symbol: dict[str, list[models.PortfolioTrade]] = {}
    for t in all_trades:
        trades_by_symbol.setdefault(t.symbol, []).append(t)

    items = []
    for p in positions:
        data = schemas.PortfolioPositionResponse.model_validate(p).model_dump()
        latest_price = price_map.get(p.symbol)
        if latest_price is not None:
            latest_price = float(latest_price)
            data['current_price'] = round(latest_price, 4)
            data['market_value'] = round(latest_price * int(p.quantity), 4)
            data['unrealized_pnl'] = round(data['market_value'] - float(p.avg_cost) * int(p.quantity), 4)
            data['unrealized_pnl_pct'] = round(data['unrealized_pnl'] / (float(p.avg_cost) * int(p.quantity)) * 100, 4) if p.avg_cost > 0 else None

        # 计算历史盈亏（包含已卖出部分）
        symbol_trades = trades_by_symbol.get(p.symbol, [])
        mv = data.get('market_value') or float(p.market_value or 0)
        history_pnl = _calc_history_pnl(mv, symbol_trades)
        data['history_pnl'] = round(history_pnl, 4)
        current_cost = float(p.avg_cost) * int(p.quantity)
        data['history_pnl_pct'] = round(history_pnl / current_cost * 100, 4) if current_cost > 0 else None

        # 计算当前连续持仓周期的盈亏与起始日
        current_start = _calc_current_holding_start_date(symbol_trades)
        data['current_holding_start_date'] = current_start.strftime('%Y-%m-%d') if current_start else None
        current_pnl = _calc_current_pnl(mv, symbol_trades)
        data['current_pnl'] = round(current_pnl, 4)
        data['current_pnl_pct'] = round(current_pnl / current_cost * 100, 4) if current_cost > 0 else None

        items.append(data)

    return list_success(items)


@router.get('/portfolio/closed')
def get_closed(
    page_num: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """获取已清仓记录"""
    list_data, total = portfolio_closed_crud.get_list(db, page_num, page_size)
    items = [schemas.PortfolioClosedResponse.model_validate(i).model_dump() for i in list_data]
    return page_success(items, total, page_num, page_size)


# ==================== 持仓快照管理接口 ====================

@router.put('/portfolio/positions/{symbol}')
def update_position(
    symbol: str,
    obj_in: schemas.PortfolioPositionUpdate,
    db: Session = Depends(get_db),
):
    """更新持仓的止损止盈、分组、备注"""
    position = portfolio_position_crud.get_by_symbol(db, symbol)
    if not position:
        raise HTTPException(status_code=404, detail='持仓不存在')

    update_data = obj_in.model_dump(exclude_unset=True)
    if update_data.get('stop_loss_price') or update_data.get('take_profit_price'):
        update_data['alert_triggered'] = 0

    for key, value in update_data.items():
        setattr(position, key, value)
    db.commit()
    db.refresh(position)

    return success(schemas.PortfolioPositionResponse.model_validate(position).model_dump())


@router.get('/portfolio/alerts')
def get_alerts(db: Session = Depends(get_db)):
    """获取触发止损/止盈预警的持仓"""
    alerts = portfolio_position_crud.get_alerts(db)
    symbols = [p.symbol for p in alerts]
    price_map = _get_latest_close_batch(db, symbols)

    result = []
    for p in alerts:
        live_price = float(price_map.get(p.symbol) or p.current_price)
        if p.stop_loss_price and live_price <= float(p.stop_loss_price):
            alert_type = 'stop_loss'
            target_price = p.stop_loss_price
        else:
            alert_type = 'take_profit'
            target_price = p.take_profit_price

        avg_cost = float(p.avg_cost)
        pnl_pct = round((live_price - avg_cost) / avg_cost * 100, 2) if avg_cost > 0 else 0
        result.append({
            'symbol': p.symbol,
            'name': p.name,
            'current_price': live_price,
            'alert_type': alert_type,
            'target_price': target_price,
            'pnl_pct': pnl_pct,
        })
    return list_success(result)


# ==================== 配置接口 ====================

@router.get('/portfolio/config')
def get_config(db: Session = Depends(get_db)):
    """获取持仓配置"""
    config = portfolio_config_crud.get_or_create(db)
    return success({
        'initial_capital': round(float(config.initial_capital), 4),
        'commission_rate': round(float(config.commission_rate), 6),
        'stamp_tax_rate': round(float(config.stamp_tax_rate), 6),
        'transfer_rate': round(float(config.transfer_rate), 6),
    })


@router.put('/portfolio/config')
def update_config(
    obj_in: schemas.PortfolioConfigUpdate,
    db: Session = Depends(get_db),
):
    """更新持仓配置"""
    config = portfolio_config_crud.update(
        db,
        obj_in.initial_capital,
        commission_rate=obj_in.commission_rate,
        stamp_tax_rate=obj_in.stamp_tax_rate,
        transfer_rate=obj_in.transfer_rate,
    )
    db.commit()
    return success({
        'initial_capital': round(float(config.initial_capital), 4),
        'commission_rate': round(float(config.commission_rate), 6),
        'stamp_tax_rate': round(float(config.stamp_tax_rate), 6),
        'transfer_rate': round(float(config.transfer_rate), 6),
    })


# ==================== 统计与图表接口 ====================

@router.get('/portfolio/summary')
def get_summary(db: Session = Depends(get_db)):
    """获取资产总览统计"""
    positions = portfolio_position_crud.get_list(db)
    closed_data = portfolio_closed_crud.get_all(db)
    config = db.query(models.PortfolioConfig).first()
    initial_capital = float(config.initial_capital) if config else 35000.0

    total_invested = sum(float(p.avg_cost) * int(p.quantity) for p in positions)

    # 批量获取最新价格
    symbols = [p.symbol for p in positions]
    price_map = _get_latest_close_batch(db, symbols)

    # 获取持仓股票的所有交易记录，用于计算历史盈亏（含部分卖出和手续费）
    all_trades = (
        db.query(models.PortfolioTrade)
        .filter(models.PortfolioTrade.symbol.in_(symbols))
        .all()
    )
    trades_by_symbol: dict[str, list[models.PortfolioTrade]] = {}
    for t in all_trades:
        trades_by_symbol.setdefault(t.symbol, []).append(t)

    total_market_value = 0.0
    total_unrealized = 0.0
    for p in positions:
        latest_price = price_map.get(p.symbol)
        mv = float(latest_price) * int(p.quantity) if latest_price else float(p.market_value or 0)
        total_market_value += mv

        symbol_trades = trades_by_symbol.get(p.symbol, [])
        history_pnl = _calc_history_pnl(mv, symbol_trades)
        total_unrealized += history_pnl

    realized_pnl = sum(float(c.realized_pnl) for c in closed_data)
    total_pnl = total_unrealized + realized_pnl

    total_pnl_pct = 0.0
    if total_invested > 0:
        total_pnl_pct = total_pnl / total_invested * 100
    elif realized_pnl != 0:
        total_pnl_pct = None

    total_return_pct = None
    if initial_capital > 0:
        total_return_pct = total_pnl / initial_capital * 100

    return success({
        'total_invested': round(total_invested, 4),
        'total_market_value': round(total_market_value, 4),
        'total_pnl': round(total_pnl, 4),
        'total_pnl_pct': round(total_pnl_pct, 4) if total_pnl_pct is not None else None,
        'realized_pnl': round(realized_pnl, 4),
        'unrealized_pnl': round(total_unrealized, 4),
        'position_count': len(positions),
        'initial_capital': round(initial_capital, 4),
        'total_return_pct': round(total_return_pct, 4) if total_return_pct is not None else None,
    })


@router.get('/portfolio/daily-pnl')
def get_daily_pnl(db: Session = Depends(get_db)):
    """获取每日盈亏时间序列（用于折线图和柱状图）

    直接从 portfolio_daily_summary 实体表读取。
    """
    rows = portfolio_daily_summary_crud.get_list(db)
    items = [
        {
            'date': r.trade_date.strftime('%Y-%m-%d'),
            'market_value': round(r.total_market_value, 4),
            'daily_pnl': round(r.daily_pnl, 4),
            'cumulative_pnl': round(r.cumulative_pnl, 4),
        }
        for r in rows
    ]
    return list_success(items)


@router.get('/portfolio/distribution')
def get_distribution(db: Session = Depends(get_db)):
    """获取当前持仓占总资产分布（用于环形图）"""
    positions = portfolio_position_crud.get_list(db)
    closed_data = portfolio_closed_crud.get_all(db)
    config = db.query(models.PortfolioConfig).first()
    initial_capital = float(config.initial_capital) if config else 35000.0

    total_invested = sum(float(p.avg_cost) * int(p.quantity) for p in positions)

    # 批量获取最新价格
    symbols = [p.symbol for p in positions]
    price_map = _get_latest_close_batch(db, symbols)

    total_market_value = 0.0
    position_mvs = []
    for p in positions:
        latest_price = price_map.get(p.symbol)
        mv = float(latest_price) * int(p.quantity) if latest_price else float(p.market_value or 0)
        total_market_value += mv
        position_mvs.append((p, mv))
    unrealized_pnl = total_market_value - total_invested
    realized_pnl = sum(float(c.realized_pnl) for c in closed_data)
    total_pnl = unrealized_pnl + realized_pnl
    total_asset = initial_capital + total_pnl

    items = []
    for p, mv in position_mvs:
        ratio = mv / total_asset * 100 if total_asset > 0 else 0
        items.append({
            'symbol': p.symbol,
            'name': p.name,
            'market_value': round(mv, 4),
            'ratio': round(ratio, 4),
        })

    return list_success(items)


@router.post('/portfolio/rebuild-daily')
def rebuild_daily_data(db: Session = Depends(get_db)):
    """手动重建 portfolio 每日资产数据（修复历史日线补齐后资产趋势断层）"""
    missing = _rebuild_daily_data(db)
    if missing:
        detail = f'持仓数据缺失日线收盘价: {", ".join(missing[:5])}' + (' 等' if len(missing) > 5 else '')
        return {'code': 400, 'message': detail, 'data': missing}
    db.commit()
    return success(message='资产数据重建成功')
