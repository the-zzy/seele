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


def _get_position_with_live_price(db: Session, p: models.PortfolioPosition) -> dict:
    """基于持仓快照，实时查询最新价格并计算返回数据"""
    data = schemas.PortfolioPositionResponse.model_validate(p).model_dump()
    latest_price = _get_latest_close(db, p.symbol)
    if latest_price is not None:
        data['current_price'] = round(latest_price, 4)
        data['market_value'] = round(latest_price * p.quantity, 4)
        data['unrealized_pnl'] = round(data['market_value'] - p.avg_cost * p.quantity, 4)
        data['unrealized_pnl_pct'] = round(data['unrealized_pnl'] / (p.avg_cost * p.quantity) * 100, 4) if p.avg_cost > 0 else None
    return data


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

    return success(schemas.PortfolioTradeResponse.model_validate(trade).model_dump())


@router.get('/portfolio/trades')
def get_trades(
    symbol: Optional[str] = None,
    trade_type: Optional[str] = None,
    page_num: int = 1,
    page_size: int = 20,
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

    return success(message='删除成功')


@router.post('/portfolio/sync')
def sync_positions(db: Session = Depends(get_db)):
    """手动触发全部持仓快照同步"""
    _sync_all_positions(db)
    return success(message='同步完成')


# ==================== 持仓与清仓接口 ====================

@router.get('/portfolio/positions')
def get_positions(
    group: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取当前持仓及浮动盈亏（实时价格计算）"""
    positions = portfolio_position_crud.get_list(db, group)
    items = [_get_position_with_live_price(db, p) for p in positions]
    return list_success(items)


@router.get('/portfolio/closed')
def get_closed(
    page_num: int = 1,
    page_size: int = 20,
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
    result = []
    for p in alerts:
        live_price = _get_latest_close(db, p.symbol) or p.current_price
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
    total_market_value = 0.0
    for p in positions:
        latest_price = _get_latest_close(db, p.symbol)
        total_market_value += latest_price * p.quantity if latest_price else (p.market_value or 0)
    unrealized_pnl = total_market_value - total_invested

    realized_pnl = sum(c.realized_pnl for c in closed_data)
    total_pnl = unrealized_pnl + realized_pnl

    # 历史总投入（含已清仓股票的买入成本）
    total_historical_invested = total_invested + sum(c.total_buy_amount for c in closed_data)
    total_pnl_pct = total_pnl / total_historical_invested * 100 if total_historical_invested > 0 else None

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
        'total_historical_invested': round(total_historical_invested, 4),
    })


@router.get('/portfolio/daily-pnl')
def get_daily_pnl(db: Session = Depends(get_db)):
    """获取每日盈亏时间序列（用于折线图和柱状图）

    计算逻辑：每日盈亏 = (当天收盘持仓市值 + 当天卖出金额 - 当天买入金额) - 前一天收盘持仓市值
    这等价于「当天结束总资产 - 前一天结束总资产」，已自然包含卖出已实现盈亏。
    """
    all_trades = portfolio_trade_crud.get_all(db)
    if not all_trades:
        return list_success([])

    trade_dates = stock_daily_crud.get_trade_dates(db)
    trade_dates.sort()

    symbols = set(t.symbol for t in all_trades)
    symbol_dailies = {}
    for symbol in symbols:
        dailies = stock_daily_crud.get_by_symbol(db, symbol)
        symbol_dailies[symbol] = {d.trade_date: d.close for d in dailies}

    # 构建每日持仓及当日买卖金额、手续费
    date_positions = {}
    date_buys = {}
    date_sells = {}
    date_fees = {}

    for symbol in symbols:
        trades = sorted([t for t in all_trades if t.symbol == symbol], key=lambda x: x.trade_date)
        daily_map = symbol_dailies.get(symbol, {})
        qty = 0
        t_idx = 0
        for d in trade_dates:
            day_buy = 0.0
            day_sell = 0.0
            day_fee = 0.0
            while t_idx < len(trades) and trades[t_idx].trade_date <= d:
                t = trades[t_idx]
                if t.trade_type == 'BUY':
                    qty += t.quantity
                    day_buy += t.amount
                else:
                    qty -= t.quantity
                    day_sell += t.amount
                day_fee += t.fee or 0
                t_idx += 1
            if qty > 0 and d in daily_map:
                date_positions.setdefault(d, {})[symbol] = (qty, daily_map[d])
            if day_buy:
                date_buys[d] = date_buys.get(d, 0) + day_buy
            if day_sell:
                date_sells[d] = date_sells.get(d, 0) + day_sell
            if day_fee:
                date_fees[d] = date_fees.get(d, 0) + day_fee

    # 按总资产变化计算每日盈亏
    result = []
    prev_mv = 0.0
    cumulative_pnl = 0.0
    config = portfolio_config_crud.get_or_create(db)

    for d in trade_dates:
        if d not in date_positions and d not in date_buys and d not in date_sells:
            continue

        today_mv = sum(q * p for q, p in date_positions.get(d, {}).values())
        today_buy = date_buys.get(d, 0)
        today_sell = date_sells.get(d, 0)
        today_fee = date_fees.get(d, 0)

        # 当天盈亏 = 当天收盘总资产 - 前一天收盘总资产
        # 其中：当天收盘总资产 = today_mv + today_sell - today_buy - today_fee（现金变动已内化）
        # 前一天收盘总资产 = prev_mv（前一天的持仓按前一天收盘价估值 + 对应现金）
        daily_pnl = today_mv - prev_mv - today_buy + today_sell - today_fee
        cumulative_pnl += daily_pnl
        prev_mv = today_mv

        result.append({
            'date': d.strftime('%Y-%m-%d'),
            'market_value': round(today_mv, 4),
            'daily_pnl': round(daily_pnl, 4),
            'cumulative_pnl': round(cumulative_pnl, 4),
            'total_asset': round(config.initial_capital + cumulative_pnl, 4),
        })

    return list_success(result)


@router.get('/portfolio/distribution')
def get_distribution(db: Session = Depends(get_db)):
    """获取当前持仓占总资产分布（用于环形图）"""
    positions = portfolio_position_crud.get_list(db)
    closed_data = portfolio_closed_crud.get_all(db)
    config = portfolio_config_crud.get_or_create(db)

    total_invested = sum(p.avg_cost * p.quantity for p in positions)
    total_market_value = 0.0
    position_mvs = []
    for p in positions:
        latest_price = _get_latest_close(db, p.symbol)
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
