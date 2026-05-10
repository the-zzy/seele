"""
持仓管理路由
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
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


def _get_latest_close_batch(db: Session, symbols: List[str]) -> dict[str, float]:
    """批量获取多只股票最新收盘价，返回 {symbol: close}"""
    if not symbols:
        return {}
    from sqlalchemy import distinct
    latest_date_row = (
        db.query(models.StockDaily.trade_date)
        .filter(models.StockDaily.symbol.in_(symbols))
        .order_by(models.StockDaily.trade_date.desc())
        .first()
    )
    if not latest_date_row:
        return {}
    latest_date = latest_date_row[0]
    results = (
        db.query(models.StockDaily.symbol, models.StockDaily.close)
        .filter(
            models.StockDaily.symbol.in_(symbols),
            models.StockDaily.trade_date == latest_date,
        )
        .all()
    )
    return {r.symbol: r.close for r in results}


def _calc_fifo_position(trades: List[models.PortfolioTrade]) -> tuple[int, float]:
    """FIFO 计算当前持仓数量和剩余成本
    返回: (quantity, remaining_cost)
    """
    buys = sorted([t for t in trades if t.trade_type == 'BUY'], key=lambda x: x.trade_date)
    sells = sorted([t for t in trades if t.trade_type == 'SELL'], key=lambda x: x.trade_date)

    buy_queue = [(b.quantity, b.price) for b in buys]
    for s in sells:
        sq = s.quantity
        while sq > 0 and buy_queue:
            bq, bp = buy_queue[0]
            if bq <= sq:
                sq -= bq
                buy_queue.pop(0)
            else:
                buy_queue[0] = (bq - sq, bp)
                sq = 0

    remaining_qty = sum(q for q, p in buy_queue)
    remaining_cost = sum(q * p for q, p in buy_queue)
    return remaining_qty, remaining_cost


def _calc_new_sell_fifo_cost(existing_trades: List[models.PortfolioTrade], sell_quantity: int) -> float:
    """基于已有交易记录，计算新的一笔卖出对应的 FIFO 成本"""
    buys = sorted([t for t in existing_trades if t.trade_type == 'BUY'], key=lambda x: x.trade_date)
    sells = sorted([t for t in existing_trades if t.trade_type == 'SELL'], key=lambda x: x.trade_date)

    buy_queue = [(b.quantity, b.price) for b in buys]
    for s in sells:
        sq = s.quantity
        while sq > 0 and buy_queue:
            bq, bp = buy_queue[0]
            if bq <= sq:
                sq -= bq
                buy_queue.pop(0)
            else:
                buy_queue[0] = (bq - sq, bp)
                sq = 0

    remaining_sq = sell_quantity
    cost = 0.0
    while remaining_sq > 0 and buy_queue:
        bq, bp = buy_queue[0]
        if bq <= remaining_sq:
            cost += bq * bp
            remaining_sq -= bq
            buy_queue.pop(0)
        else:
            cost += remaining_sq * bp
            buy_queue[0] = (bq - remaining_sq, bp)
            remaining_sq = 0

    return cost


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

    total_buy_amount = sum(b.amount for b in buys)
    total_sell_amount = sum(s.amount for s in sells)
    total_fee = sum((t.fee or 0) for t in trades)
    total_quantity = total_buy_qty
    avg_buy = total_buy_amount / total_quantity if total_quantity > 0 else 0
    avg_sell = total_sell_amount / total_sell_qty if total_sell_qty > 0 else 0
    realized_pnl = total_sell_amount - total_buy_amount - total_fee
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


def _sync_position_snapshot(db: Session, symbol: str) -> Optional[models.PortfolioPosition]:
    """同步单个股票的持仓快照"""
    trades = portfolio_trade_crud.get_by_symbol(db, symbol)
    if not trades:
        portfolio_position_crud.delete_by_symbol(db, symbol)
        return None

    qty, cost = _calc_fifo_position(trades)
    if qty <= 0:
        portfolio_position_crud.delete_by_symbol(db, symbol)
        return None

    avg_cost = cost / qty if qty > 0 else 0
    current_price = _get_latest_close(db, symbol)
    market_value = round(current_price * qty, 4) if current_price else None
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
    """同步所有持仓快照"""
    all_trades = portfolio_trade_crud.get_all(db)
    symbols = sorted(set(t.symbol for t in all_trades))
    for symbol in symbols:
        _sync_position_snapshot(db, symbol)


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
        return []

    trade_dates = stock_daily_crud.get_trade_dates(db)
    trade_dates.sort()

    symbols = set(t.symbol for t in all_trades)
    symbol_dailies = {}
    for symbol in symbols:
        dailies = stock_daily_crud.get_by_symbol(db, symbol)
        symbol_dailies[symbol] = {d.trade_date: d.close for d in dailies}

    # 逐 symbol 重建每日持仓明细
    symbol_day_details = {s: {} for s in symbols}
    missing_data: list[str] = []
    for symbol in symbols:
        trades = sorted([t for t in all_trades if t.symbol == symbol], key=lambda x: x.trade_date)
        daily_map = symbol_dailies.get(symbol, {})
        qty = 0
        cost = 0.0
        t_idx = 0
        for d in trade_dates:
            day_buy = 0.0
            day_sell = 0.0
            while t_idx < len(trades) and trades[t_idx].trade_date <= d:
                t = trades[t_idx]
                if t.trade_type == 'BUY':
                    qty += t.quantity
                    cost += t.amount
                    day_buy += t.amount
                else:
                    qty -= t.quantity
                    cost -= t.quantity * (cost / qty if qty > t.quantity else t.price)
                    day_sell += t.amount
                t_idx += 1
            # FIFO 重新计算成本更精确
            past_trades = [tt for tt in trades if tt.trade_date <= d]
            qty, rem_cost = _calc_fifo_position(past_trades)
            avg_cost = rem_cost / qty if qty > 0 else 0
            close_price = daily_map.get(d)
            # 检测缺失数据：有持仓但无收盘价
            if qty > 0 and close_price is None:
                missing_data.append(f'{symbol}@{d}')
            market_value = qty * close_price if close_price else 0
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
        total_invested = 0.0
        total_unrealized = 0.0

        for s in day_symbols:
            det = symbol_day_details[s][d]
            q = det['qty']
            cp = det['close_price']
            mv = q * cp if q > 0 and cp else 0.0
            today_mv += mv
            today_buy += det['day_buy']
            today_sell += det['day_sell']
            if q > 0:
                total_invested += q * det['avg_cost']
                total_unrealized += det['unrealized_pnl']

            # 写入每日持仓明细
            trade = next(t for t in all_trades if t.symbol == s)
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

        daily_pnl = today_mv - prev_mv - today_buy + today_sell
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

    # 计算已实现盈亏：基于清仓记录，将清仓日的 realized_pnl 加到当天及之后的 cumulative
    closed_list = portfolio_closed_crud.get_all(db)
    closed_by_date = {}
    for c in closed_list:
        closed_by_date.setdefault(c.close_date, 0)
        closed_by_date[c.close_date] += c.realized_pnl

    running_realized = 0.0
    for item in summary_items:
        d = item['trade_date']
        running_realized += closed_by_date.get(d, 0)
        item['realized_pnl'] = round(running_realized, 4)

    if position_items:
        portfolio_daily_position_crud.create_batch(db, position_items)
    if summary_items:
        portfolio_daily_summary_crud.create_batch(db, summary_items)

    return missing_data


# ==================== 交易记录接口 ====================

@router.post('/portfolio/trades')
def create_trade(
    obj_in: schemas.PortfolioTradeCreate,
    db: Session = Depends(get_db),
):
    """录入交易记录（买入或卖出）"""
    if obj_in.trade_type not in ('BUY', 'SELL'):
        raise HTTPException(status_code=400, detail='trade_type 必须为 BUY 或 SELL')

    # 构建数据，排除 realized_pnl（模型无此字段）
    data = obj_in.model_dump(exclude={'realized_pnl'})
    if data.get('amount') is None and data.get('price') and data.get('quantity'):
        data['amount'] = round(data['price'] * data['quantity'], 4)

    # 卖出时若填写了实际盈亏，自动计算手续费
    if obj_in.trade_type == 'SELL' and obj_in.realized_pnl is not None:
        existing_trades = portfolio_trade_crud.get_by_symbol(db, obj_in.symbol)
        fifo_cost = _calc_new_sell_fifo_cost(existing_trades, obj_in.quantity)
        theoretical_pnl = data['amount'] - fifo_cost
        data['fee'] = round(theoretical_pnl - obj_in.realized_pnl, 4)

    trade = models.PortfolioTrade(**data)
    db.add(trade)
    db.commit()
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
            db.commit()
            portfolio_closed_crud.create(db, closed_data)

    # 重建每日持仓和资产数据
    missing = _rebuild_daily_data(db)
    msg = '录入成功'
    if missing:
        msg += f'（警告: {len(missing)} 条持仓数据缺失日线收盘价）'

    return success(schemas.PortfolioTradeResponse.model_validate(trade).model_dump(), message=msg)


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
    db.commit()

    closed_data = _calc_closed_for_symbol(db, symbol)
    if closed_data:
        portfolio_closed_crud.create(db, closed_data)

    # 重建每日持仓和资产数据
    missing = _rebuild_daily_data(db)
    msg = '删除成功'
    if missing:
        msg += f'（警告: {len(missing)} 条持仓数据缺失日线收盘价）'

    return success(message=msg)


@router.post('/portfolio/sync')
def sync_positions(db: Session = Depends(get_db)):
    """手动触发全部持仓快照同步，并重建每日数据"""
    _sync_all_positions(db)
    missing = _rebuild_daily_data(db)
    msg = '同步完成'
    if missing:
        msg += f'（警告: {len(missing)} 条持仓数据缺失日线收盘价）'
    return success(message=msg)


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

    items = []
    for p in positions:
        data = schemas.PortfolioPositionResponse.model_validate(p).model_dump()
        latest_price = price_map.get(p.symbol)
        if latest_price is not None:
            data['current_price'] = round(latest_price, 4)
            data['market_value'] = round(latest_price * p.quantity, 4)
            data['unrealized_pnl'] = round(data['market_value'] - p.avg_cost * p.quantity, 4)
            data['unrealized_pnl_pct'] = round(data['unrealized_pnl'] / (p.avg_cost * p.quantity) * 100, 4) if p.avg_cost > 0 else None
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
        live_price = price_map.get(p.symbol) or p.current_price
        if p.stop_loss_price and live_price <= p.stop_loss_price:
            alert_type = 'stop_loss'
            target_price = p.stop_loss_price
        else:
            alert_type = 'take_profit'
            target_price = p.take_profit_price

        pnl_pct = round((live_price - p.avg_cost) / p.avg_cost * 100, 2) if p.avg_cost > 0 else 0
        result.append({
            'symbol': p.symbol,
            'name': p.name,
            'current_price': live_price,
            'alert_type': alert_type,
            'target_price': target_price,
            'pnl_pct': pnl_pct,
        })
    return list_success(result)


@router.post('/portfolio/alerts/{id}/dismiss')
def dismiss_alert(id: int, db: Session = Depends(get_db)):
    """标记预警为已处理"""
    success_flag = portfolio_position_crud.mark_alert_triggered(db, id)
    if not success_flag:
        raise HTTPException(status_code=404, detail='持仓不存在')
    return success(message='已标记为已处理')


# ==================== 配置接口 ====================

@router.get('/portfolio/config')
def get_config(db: Session = Depends(get_db)):
    """获取持仓配置"""
    config = portfolio_config_crud.get_or_create(db)
    return success({
        'initial_capital': round(config.initial_capital, 4)
    })


@router.put('/portfolio/config')
def update_config(
    obj_in: schemas.PortfolioConfigUpdate,
    db: Session = Depends(get_db),
):
    """更新持仓配置"""
    config = portfolio_config_crud.update(db, obj_in.initial_capital)
    return success({
        'initial_capital': round(config.initial_capital, 4)
    })


# ==================== 统计与图表接口 ====================

@router.get('/portfolio/summary')
def get_summary(db: Session = Depends(get_db)):
    """获取资产总览统计"""
    positions = portfolio_position_crud.get_list(db)
    closed_data = portfolio_closed_crud.get_all(db)
    config = portfolio_config_crud.get_or_create(db)

    total_invested = sum(p.avg_cost * p.quantity for p in positions)

    # 批量获取最新价格
    symbols = [p.symbol for p in positions]
    price_map = _get_latest_close_batch(db, symbols)

    total_market_value = 0.0
    for p in positions:
        latest_price = price_map.get(p.symbol)
        total_market_value += latest_price * p.quantity if latest_price else (p.market_value or 0)
    unrealized_pnl = total_market_value - total_invested

    realized_pnl = sum(c.realized_pnl for c in closed_data)
    total_pnl = unrealized_pnl + realized_pnl

    total_pnl_pct = 0.0
    if total_invested > 0:
        total_pnl_pct = total_pnl / total_invested * 100
    elif realized_pnl != 0:
        total_pnl_pct = None

    total_return_pct = None
    if config.initial_capital > 0:
        total_return_pct = total_pnl / config.initial_capital * 100

    return success({
        'total_invested': round(total_invested, 4),
        'total_market_value': round(total_market_value, 4),
        'total_pnl': round(total_pnl, 4),
        'total_pnl_pct': round(total_pnl_pct, 4) if total_pnl_pct is not None else None,
        'realized_pnl': round(realized_pnl, 4),
        'unrealized_pnl': round(unrealized_pnl, 4),
        'position_count': len(positions),
        'initial_capital': round(config.initial_capital, 4),
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


@router.get('/portfolio/daily-pnl/debug')
def get_daily_pnl_debug(db: Session = Depends(get_db)):
    """每日盈亏调试接口：输出每天每只持仓股票的详细计算过程

    直接从 portfolio_daily_position 实体表读取。
    """
    positions = portfolio_daily_position_crud.get_list(db)
    summaries = portfolio_daily_summary_crud.get_list(db)

    if not positions or not summaries:
        return list_success([])

    summary_map = {s.trade_date: s for s in summaries}

    # 按日期分组持仓明细
    date_details = {}
    for p in positions:
        date_details.setdefault(p.trade_date, []).append({
            'symbol': p.symbol,
            'qty': p.quantity,
            'price': p.close_price,
            'market_value': round(p.market_value, 4),
            'day_buy': round(p.day_buy, 4),
            'day_sell': round(p.day_sell, 4),
        })

    result = []
    prev_mv = 0.0
    for s in summaries:
        d = s.trade_date
        breakdown = date_details.get(d, [])
        today_mv = s.total_market_value
        today_buy = sum(b['day_buy'] for b in breakdown)
        today_sell = sum(b['day_sell'] for b in breakdown)
        daily_pnl = s.daily_pnl
        prev_mv = today_mv - daily_pnl + today_buy - today_sell

        result.append({
            'date': d.strftime('%Y-%m-%d'),
            'prev_mv': round(prev_mv, 4),
            'today_mv': round(today_mv, 4),
            'today_buy': round(today_buy, 4),
            'today_sell': round(today_sell, 4),
            'daily_pnl': round(daily_pnl, 4),
            'cumulative_pnl': round(s.cumulative_pnl, 4),
            'breakdown': breakdown,
        })

    return list_success(result)


@router.get('/portfolio/distribution')
def get_distribution(db: Session = Depends(get_db)):
    """获取当前持仓占总资产分布（用于环形图）"""
    positions = portfolio_position_crud.get_list(db)
    closed_data = portfolio_closed_crud.get_all(db)
    config = portfolio_config_crud.get_or_create(db)

    total_invested = sum(p.avg_cost * p.quantity for p in positions)

    # 批量获取最新价格
    symbols = [p.symbol for p in positions]
    price_map = _get_latest_close_batch(db, symbols)

    total_market_value = 0.0
    position_mvs = []
    for p in positions:
        latest_price = price_map.get(p.symbol)
        mv = latest_price * p.quantity if latest_price else (p.market_value or 0)
        total_market_value += mv
        position_mvs.append((p, mv))
    unrealized_pnl = total_market_value - total_invested
    realized_pnl = sum(c.realized_pnl for c in closed_data)
    total_pnl = unrealized_pnl + realized_pnl
    total_asset = config.initial_capital + total_pnl

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
