"""
Agent 工具注册表与实现
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Any, Optional

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import (
    stock_basic_crud,
    stock_daily_crud,
    stock_daily_indicator_crud,
    stock_financial_indicator_crud,
    portfolio_trade_crud,
    portfolio_position_crud,
    portfolio_closed_crud,
    portfolio_daily_summary_crud,
    portfolio_config_crud,
    sync_job_log_crud,
)


@dataclass
class ToolMeta:
    name: str
    description: str
    parameters: dict
    category: str
    func: Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolMeta] = {}

    def register(self, name: str, description: str, parameters: dict, category: str = 'read'):
        def decorator(func: Callable):
            self._tools[name] = ToolMeta(
                name=name,
                description=description,
                parameters=parameters,
                category=category,
                func=func,
            )
            return func
        return decorator

    def get_openai_tools(self, allowed_categories: set[str] | None = None) -> list[dict]:
        result = []
        for meta in self._tools.values():
            if allowed_categories and meta.category not in allowed_categories:
                continue
            result.append({
                'type': 'function',
                'function': {
                    'name': meta.name,
                    'description': meta.description,
                    'parameters': meta.parameters,
                },
            })
        return result

    async def execute(self, name: str, arguments: dict, db: Session) -> Any:
        meta = self._tools.get(name)
        if not meta:
            raise ValueError(f'未知工具: {name}')
        return await meta.func(db, **arguments)


registry = ToolRegistry()


# ==================== 读工具 ====================


@registry.register(
    name='query_stock_basic',
    description='查询股票基础信息，支持按代码精确查询或按名称模糊查询',
    parameters={
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': '股票代码，如 000001'},
            'name': {'type': 'string', 'description': '股票名称模糊匹配'},
            'industry': {'type': 'string', 'description': '行业过滤'},
            'limit': {'type': 'integer', 'description': '返回条数上限，默认 10'},
        },
    },
    category='read',
)
async def query_stock_basic(db: Session, symbol: Optional[str] = None, name: Optional[str] = None, industry: Optional[str] = None, limit: int = 10):
    if symbol and not name:
        item = stock_basic_crud.get_by_symbol(db, symbol)
        if item:
            return _stock_basic_to_dict(item)
        return {'error': f'未找到股票 {symbol}'}

    query = schemas.StockBasicQuery(page_num=1, page_size=limit, symbol=symbol, name=name, industry=industry)
    items, total = stock_basic_crud.get_list(db, query)
    return {'total': total, 'list': [_stock_basic_to_dict(i) for i in items[:limit]]}


def _stock_basic_to_dict(item: models.StockBasic) -> dict:
    return {
        'symbol': item.symbol,
        'name': item.name,
        'area': item.area,
        'industry': item.industry,
        'market': item.market,
        'float_market_cap': item.float_market_cap,
        'list_date': str(item.list_date) if item.list_date else None,
        'roe': getattr(item, 'roe', None),
        'gross_profit_ratio': getattr(item, 'gross_profit_ratio', None),
        'net_profit_ratio': getattr(item, 'net_profit_ratio', None),
    }


@registry.register(
    name='query_stock_daily',
    description='查询股票日线 OHLCV 数据',
    parameters={
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': '股票代码'},
            'start_date': {'type': 'string', 'description': '开始日期 YYYY-MM-DD'},
            'end_date': {'type': 'string', 'description': '结束日期 YYYY-MM-DD'},
            'limit': {'type': 'integer', 'description': '返回条数上限，默认 30'},
        },
        'required': ['symbol'],
    },
    category='read',
)
async def query_stock_daily(db: Session, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 30):
    if start_date or end_date:
        query = schemas.StockDailyQuery(page_num=1, page_size=limit, symbol=symbol, start_date=start_date, end_date=end_date)
        items, total = stock_daily_crud.get_list(db, query)
    else:
        items = stock_daily_crud.get_by_symbol(db, symbol)
        items = items[-limit:] if len(items) > limit else items
        total = len(items)
    return {'total': total, 'list': [_stock_daily_to_dict(i) for i in items]}


def _stock_daily_to_dict(item: models.StockDaily) -> dict:
    return {
        'trade_date': str(item.trade_date),
        'symbol': item.symbol,
        'open': item.open,
        'high': item.high,
        'low': item.low,
        'close': item.close,
        'volume': item.volume,
        'amount': item.amount,
        'amplitude': item.amplitude,
        'pct_chg': item.pct_chg,
        'price_change': item.price_change,
        'turnover': item.turnover,
    }


@registry.register(
    name='query_stock_indicator',
    description='查询股票技术指标（均线、MACD、RSI、KDJ、布林带等）',
    parameters={
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': '股票代码'},
            'trade_date': {'type': 'string', 'description': '特定交易日 YYYY-MM-DD'},
            'limit': {'type': 'integer', 'description': '返回条数上限，默认 10'},
        },
        'required': ['symbol'],
    },
    category='read',
)
async def query_stock_indicator(db: Session, symbol: str, trade_date: Optional[str] = None, limit: int = 10):
    if trade_date:
        d = datetime.strptime(trade_date, '%Y-%m-%d').date()
        item = stock_daily_indicator_crud.get_by_symbol_date(db, symbol, d)
        if item:
            return _stock_indicator_to_dict(item)
        return {'error': f'未找到 {symbol} 在 {trade_date} 的指标数据'}

    items = stock_daily_indicator_crud.get_by_symbol(db, symbol)
    items = items[:limit]
    return {'total': len(items), 'list': [_stock_indicator_to_dict(i) for i in items]}


def _stock_indicator_to_dict(item: models.StockDailyIndicator) -> dict:
    return {
        'trade_date': str(item.trade_date),
        'symbol': item.symbol,
        'ma5': item.ma5,
        'ma10': item.ma10,
        'ma20': item.ma20,
        'ma30': item.ma30,
        'ma60': item.ma60,
        'chg_5d': item.chg_5d,
        'chg_10d': item.chg_10d,
        'macd_dif': item.macd_dif,
        'macd_dea': item.macd_dea,
        'macd_hist': item.macd_hist,
        'rsi_6': item.rsi_6,
        'rsi_12': item.rsi_12,
        'rsi_24': item.rsi_24,
        'kdj_k': item.kdj_k,
        'kdj_d': item.kdj_d,
        'kdj_j': item.kdj_j,
        'boll_upper': item.boll_upper,
        'boll_middle': item.boll_middle,
        'boll_lower': item.boll_lower,
        'turnover_ma5': item.turnover_ma5,
        'turnover_ma10': item.turnover_ma10,
    }


@registry.register(
    name='query_financial_indicator',
    description='查询股票财务指标（ROE、毛利率、净利率、营收增长等）',
    parameters={
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': '股票代码'},
        },
        'required': ['symbol'],
    },
    category='read',
)
async def query_financial_indicator(db: Session, symbol: str):
    item = stock_financial_indicator_crud.get_by_symbol(db, symbol)
    if not item:
        return {'error': f'未找到 {symbol} 的财务指标'}
    return {
        'symbol': item.symbol,
        'name': item.name,
        'report_date': str(item.report_date) if item.report_date else None,
        'net_profit': item.net_profit,
        'net_profit_yoy': item.net_profit_yoy,
        'deduct_net_profit': item.deduct_net_profit,
        'total_revenue': item.total_revenue,
        'revenue_yoy': item.revenue_yoy,
        'gross_profit_ratio': item.gross_profit_ratio,
        'net_profit_ratio': item.net_profit_ratio,
        'roe': item.roe,
        'roe_diluted': item.roe_diluted,
        'eps': item.eps,
        'bps': item.bps,
        'debt_ratio': item.debt_ratio,
        'total_assets': item.total_assets,
        'total_equity': item.total_equity,
    }


@registry.register(
    name='run_mainwave_picker',
    description='运行主升浪选股策略，返回符合条件的股票列表',
    parameters={
        'type': 'object',
        'properties': {
            'trade_date': {'type': 'string', 'description': '交易日期 YYYY-MM-DD，默认最新'},
            'float_market_cap_min': {'type': 'number', 'description': '流通市值最小值（亿元）'},
            'close_max': {'type': 'number', 'description': '收盘价最大值'},
            'avg_turnover_min': {'type': 'number', 'description': '10日平均换手率最小值(%)'},
            'avg_amount_min': {'type': 'number', 'description': '10日平均成交额最小值'},
            'ma_bull': {'type': 'boolean', 'description': '是否要求均线多头排列'},
            'limit': {'type': 'integer', 'description': '返回条数上限，默认 20'},
        },
    },
    category='read',
)
async def run_mainwave_picker(
    db: Session,
    trade_date: Optional[str] = None,
    float_market_cap_min: Optional[float] = None,
    close_max: Optional[float] = None,
    avg_turnover_min: Optional[float] = None,
    avg_amount_min: Optional[float] = None,
    ma_bull: Optional[bool] = None,
    limit: int = 20,
):
    query = schemas.MainwavePickerQuery(
        page_num=1,
        page_size=limit,
        trade_date=trade_date,
        float_market_cap_min=float_market_cap_min,
        close_max=close_max,
        avg_turnover_min=avg_turnover_min,
        avg_amount_min=avg_amount_min,
        ma_bull=ma_bull,
    )
    items, total, actual_date = stock_basic_crud.get_mainwave_list(db, query)
    return {'trade_date': actual_date, 'total': total, 'list': items[:limit]}


@registry.register(
    name='query_portfolio_positions',
    description='查询当前持仓列表及浮动盈亏',
    parameters={
        'type': 'object',
        'properties': {
            'group': {'type': 'string', 'description': '持仓分组过滤'},
        },
    },
    category='read',
)
async def query_portfolio_positions(db: Session, group: Optional[str] = None):
    positions = portfolio_position_crud.get_list(db, group)
    symbols = [p.symbol for p in positions]
    price_map = _get_latest_close_batch(db, symbols)

    items = []
    for p in positions:
        latest_price = price_map.get(p.symbol)
        avg_cost = float(p.avg_cost)
        mv = round(latest_price * int(p.quantity), 4) if latest_price else float(p.market_value or 0)
        upnl = round(mv - avg_cost * int(p.quantity), 4) if latest_price else float(p.unrealized_pnl or 0)
        upnl_pct = round(upnl / (avg_cost * int(p.quantity)) * 100, 4) if avg_cost > 0 else None
        items.append({
            'symbol': p.symbol,
            'name': p.name,
            'quantity': p.quantity,
            'avg_cost': avg_cost,
            'current_price': latest_price or p.current_price,
            'market_value': mv,
            'unrealized_pnl': upnl,
            'unrealized_pnl_pct': upnl_pct,
            'stop_loss_price': p.stop_loss_price,
            'take_profit_price': p.take_profit_price,
            'group': p.group,
            'remark': p.remark,
        })
    return {'total': len(items), 'list': items}


def _get_latest_close_batch(db: Session, symbols: list[str]) -> dict[str, float]:
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
    results = (
        db.query(models.StockDaily.symbol, models.StockDaily.close)
        .filter(
            models.StockDaily.symbol.in_(symbols),
            models.StockDaily.trade_date == latest_date_row[0],
        )
        .all()
    )
    return {r.symbol: r.close for r in results}


@registry.register(
    name='query_portfolio_trades',
    description='查询交易记录',
    parameters={
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': '股票代码过滤'},
            'trade_type': {'type': 'string', 'description': 'BUY 或 SELL'},
            'limit': {'type': 'integer', 'description': '返回条数上限，默认 20'},
        },
    },
    category='read',
)
async def query_portfolio_trades(db: Session, symbol: Optional[str] = None, trade_type: Optional[str] = None, limit: int = 20):
    query = schemas.PortfolioTradeQuery(page_num=1, page_size=limit, symbol=symbol, trade_type=trade_type)
    items, total = portfolio_trade_crud.get_list(db, query)
    return {
        'total': total,
        'list': [
            {
                'id': i.id,
                'symbol': i.symbol,
                'name': i.name,
                'trade_type': i.trade_type,
                'trade_date': str(i.trade_date),
                'price': i.price,
                'quantity': i.quantity,
                'amount': i.amount,
                'fee': i.fee,
                'remark': i.remark,
            }
            for i in items
        ],
    }


@registry.register(
    name='query_portfolio_summary',
    description='查询资产总览（总投入、总市值、盈亏、收益率等）',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
async def query_portfolio_summary(db: Session):
    positions = portfolio_position_crud.get_list(db)
    closed_data = portfolio_closed_crud.get_all(db)
    config = portfolio_config_crud.get_or_create(db)

    symbols = [p.symbol for p in positions]
    price_map = _get_latest_close_batch(db, symbols)

    total_invested = sum(float(p.avg_cost) * int(p.quantity) for p in positions)
    total_market_value = 0.0
    for p in positions:
        lp = price_map.get(p.symbol)
        total_market_value += lp * int(p.quantity) if lp else float(p.market_value or 0)
    unrealized_pnl = total_market_value - total_invested
    realized_pnl = sum(float(c.realized_pnl) for c in closed_data)
    total_pnl = unrealized_pnl + realized_pnl

    total_pnl_pct = total_pnl / total_invested * 100 if total_invested > 0 else 0
    total_return_pct = total_pnl / config.initial_capital * 100 if config.initial_capital > 0 else None

    return {
        'initial_capital': round(config.initial_capital, 4),
        'total_invested': round(total_invested, 4),
        'total_market_value': round(total_market_value, 4),
        'realized_pnl': round(realized_pnl, 4),
        'unrealized_pnl': round(unrealized_pnl, 4),
        'total_pnl': round(total_pnl, 4),
        'total_pnl_pct': round(total_pnl_pct, 4),
        'total_return_pct': round(total_return_pct, 4) if total_return_pct is not None else None,
        'position_count': len(positions),
    }


@registry.register(
    name='query_portfolio_daily_pnl',
    description='查询每日盈亏时间序列',
    parameters={
        'type': 'object',
        'properties': {
            'limit': {'type': 'integer', 'description': '返回最近N天，默认 30'},
        },
    },
    category='read',
)
async def query_portfolio_daily_pnl(db: Session, limit: int = 30):
    rows = portfolio_daily_summary_crud.get_list(db)
    rows = rows[-limit:] if len(rows) > limit else rows
    return {
        'total': len(rows),
        'list': [
            {
                'date': str(r.trade_date),
                'total_invested': round(r.total_invested, 4),
                'total_market_value': round(r.total_market_value, 4),
                'daily_pnl': round(r.daily_pnl, 4),
                'cumulative_pnl': round(r.cumulative_pnl, 4),
                'realized_pnl': round(r.realized_pnl, 4),
                'unrealized_pnl': round(r.unrealized_pnl, 4),
            }
            for r in rows
        ],
    }


@registry.register(
    name='query_portfolio_closed',
    description='查询已清仓记录及盈亏',
    parameters={
        'type': 'object',
        'properties': {
            'limit': {'type': 'integer', 'description': '返回条数上限，默认 20'},
        },
    },
    category='read',
)
async def query_portfolio_closed(db: Session, limit: int = 20):
    items, total = portfolio_closed_crud.get_list(db, page_num=1, page_size=limit)
    return {
        'total': total,
        'list': [
            {
                'symbol': i.symbol,
                'name': i.name,
                'avg_buy_price': i.avg_buy_price,
                'avg_sell_price': i.avg_sell_price,
                'total_quantity': i.total_quantity,
                'realized_pnl': i.realized_pnl,
                'pnl_pct': i.pnl_pct,
                'open_date': str(i.open_date),
                'close_date': str(i.close_date),
            }
            for i in items
        ],
    }


@registry.register(
    name='query_portfolio_alerts',
    description='查询触发止损或止盈预警的持仓',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
async def query_portfolio_alerts(db: Session):
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
    return {'total': len(result), 'list': result}


@registry.register(
    name='query_sync_job_logs',
    description='查询同步任务执行日志',
    parameters={
        'type': 'object',
        'properties': {
            'days': {'type': 'integer', 'description': '最近N天'},
            'job_type': {'type': 'string', 'description': '任务类型: stock_basic/daily/financial/indicator'},
            'limit': {'type': 'integer', 'description': '返回条数上限，默认 20'},
        },
    },
    category='read',
)
async def query_sync_job_logs(db: Session, days: Optional[int] = None, job_type: Optional[str] = None, limit: int = 20):
    query = schemas.SyncJobLogQuery(page_num=1, page_size=limit, days=days, job_type=job_type)
    items, total = sync_job_log_crud.get_list(db, query)
    return {
        'total': total,
        'list': [
            {
                'id': i.id,
                'job_type': i.job_type,
                'trigger_type': i.trigger_type,
                'status': i.status,
                'started_at': str(i.started_at),
                'ended_at': str(i.ended_at) if i.ended_at else None,
                'duration_seconds': i.duration_seconds,
                'success_count': i.success_count,
                'failed_count': i.failed_count,
            }
            for i in items
        ],
    }


@registry.register(
    name='query_db_status',
    description='查询数据库各表的数据概况',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
async def query_db_status(db: Session):
    tables = [
        ('stock_basic', models.StockBasic),
        ('stock_daily', models.StockDaily),
        ('stock_daily_indicator', models.StockDailyIndicator),
        ('portfolio_trade', models.PortfolioTrade),
        ('portfolio_position', models.PortfolioPosition),
        ('portfolio_closed', models.PortfolioClosed),
        ('portfolio_daily_summary', models.PortfolioDailySummary),
        ('market_sentiment_daily', models.MarketSentimentDaily),
        ('stock_financial_indicator', models.StockFinancialIndicator),
        ('sync_job_log', models.SyncJobLog),
    ]
    result = {}
    for name, model in tables:
        count = db.query(func.count('*')).select_from(model).scalar()
        result[name] = count

    latest_daily = db.query(models.StockDaily.trade_date).order_by(models.StockDaily.trade_date.desc()).first()
    latest_indicator = db.query(models.StockDailyIndicator.trade_date).order_by(models.StockDailyIndicator.trade_date.desc()).first()

    return {
        'table_counts': result,
        'latest_trade_date': str(latest_daily[0]) if latest_daily else None,
        'latest_indicator_date': str(latest_indicator[0]) if latest_indicator else None,
    }


@registry.register(
    name='query_market_sentiment',
    description='查询市场每日情绪统计（上涨/下跌家数、平均涨幅等）。如果不传日期，默认查询最近5个交易日。',
    parameters={
        'type': 'object',
        'properties': {
            'start_date': {'type': 'string', 'description': '开始日期 YYYY-MM-DD，可选'},
            'end_date': {'type': 'string', 'description': '结束日期 YYYY-MM-DD，可选'},
        },
    },
    category='read',
)
async def query_market_sentiment(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None):
    if start_date and end_date:
        sd = datetime.strptime(start_date, '%Y-%m-%d').date()
        ed = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        # 默认查最近5个交易日
        from sqlalchemy import func
        latest = db.query(func.max(models.MarketSentimentDaily.trade_date)).scalar()
        if not latest:
            return {'total': 0, 'list': []}
        ed = latest
        sd = ed - timedelta(days=10)
    rows = (
        db.query(models.MarketSentimentDaily)
        .filter(
            models.MarketSentimentDaily.trade_date >= sd,
            models.MarketSentimentDaily.trade_date <= ed,
        )
        .order_by(models.MarketSentimentDaily.trade_date.asc())
        .all()
    )
    return {
        'total': len(rows),
        'list': [
            {
                'trade_date': str(r.trade_date),
                'total_stocks': r.total_stocks,
                'up_count': r.up_count,
                'down_count': r.down_count,
                'flat_count': r.flat_count,
                'avg_pct_chg': r.avg_pct_chg,
                'strong_count': r.strong_count,
                'strong_percent': r.strong_percent,
            }
            for r in rows
        ],
    }


# ==================== 写工具 ====================


@registry.register(
    name='create_trade',
    description='录入一笔买入或卖出交易记录。录入后会自动同步持仓快照并重建每日资产数据。',
    parameters={
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': '股票代码'},
            'name': {'type': 'string', 'description': '股票名称'},
            'trade_type': {'type': 'string', 'description': 'BUY 或 SELL'},
            'trade_date': {'type': 'string', 'description': '交易日期 YYYY-MM-DD'},
            'price': {'type': 'number', 'description': '成交价格'},
            'quantity': {'type': 'integer', 'description': '成交股数'},
            'amount': {'type': 'number', 'description': '成交金额（可选，不传则自动计算 price*quantity）'},
            'fee': {'type': 'number', 'description': '手续费'},
            'remark': {'type': 'string', 'description': '备注'},
        },
        'required': ['symbol', 'name', 'trade_type', 'trade_date', 'price', 'quantity'],
    },
    category='write',
)
async def create_trade(db: Session, symbol: str, name: str, trade_type: str, trade_date: str, price: float, quantity: int, amount: Optional[float] = None, fee: Optional[float] = None, remark: Optional[str] = None):
    from app.routes.portfolio import _sync_position_snapshot, _calc_closed_for_symbol, _rebuild_daily_data

    if trade_type not in ('BUY', 'SELL'):
        return {'error': 'trade_type 必须为 BUY 或 SELL'}

    data = {
        'symbol': symbol,
        'name': name,
        'trade_type': trade_type,
        'trade_date': trade_date,
        'price': price,
        'quantity': quantity,
        'amount': amount if amount is not None else round(price * quantity, 4),
        'fee': fee if fee is not None else 0,
        'remark': remark,
    }
    db_obj = models.PortfolioTrade(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    _sync_position_snapshot(db, symbol)

    if trade_type == 'SELL':
        closed_data = _calc_closed_for_symbol(db, symbol)
        if closed_data:
            db.query(models.PortfolioClosed).filter(models.PortfolioClosed.symbol == symbol).delete()
            db.commit()
            portfolio_closed_crud.create(db, closed_data)

    missing = _rebuild_daily_data(db)
    result = {
        'id': db_obj.id,
        'symbol': db_obj.symbol,
        'trade_type': db_obj.trade_type,
        'price': db_obj.price,
        'quantity': db_obj.quantity,
        'amount': db_obj.amount,
    }
    if missing:
        result['warning'] = f'{len(missing)} 条持仓数据缺失日线收盘价'
    return result


@registry.register(
    name='update_position',
    description='更新持仓的止损价、止盈价、分组或备注',
    parameters={
        'type': 'object',
        'properties': {
            'symbol': {'type': 'string', 'description': '股票代码'},
            'stop_loss_price': {'type': 'number', 'description': '止损价格'},
            'take_profit_price': {'type': 'number', 'description': '止盈价格'},
            'group': {'type': 'string', 'description': '分组名称'},
            'remark': {'type': 'string', 'description': '备注'},
        },
        'required': ['symbol'],
    },
    category='write',
)
async def update_position(db: Session, symbol: str, stop_loss_price: Optional[float] = None, take_profit_price: Optional[float] = None, group: Optional[str] = None, remark: Optional[str] = None):
    position = portfolio_position_crud.get_by_symbol(db, symbol)
    if not position:
        return {'error': f'持仓不存在: {symbol}'}

    if stop_loss_price is not None:
        position.stop_loss_price = stop_loss_price
        position.alert_triggered = 0
    if take_profit_price is not None:
        position.take_profit_price = take_profit_price
        position.alert_triggered = 0
    if group is not None:
        position.group = group
    if remark is not None:
        position.remark = remark

    db.commit()
    db.refresh(position)
    return {
        'symbol': position.symbol,
        'name': position.name,
        'stop_loss_price': position.stop_loss_price,
        'take_profit_price': position.take_profit_price,
        'group': position.group,
        'remark': position.remark,
    }


@registry.register(
    name='update_portfolio_config',
    description='更新投资组合的初始资金配置',
    parameters={
        'type': 'object',
        'properties': {
            'initial_capital': {'type': 'number', 'description': '初始资金金额'},
        },
        'required': ['initial_capital'],
    },
    category='write',
)
async def update_portfolio_config(db: Session, initial_capital: float):
    config = portfolio_config_crud.update(db, initial_capital)
    return {'initial_capital': round(config.initial_capital, 4)}


@registry.register(
    name='sync_positions',
    description='手动触发全部持仓快照同步，并重建每日持仓和资产汇总数据',
    parameters={'type': 'object', 'properties': {}},
    category='write',
)
async def sync_positions(db: Session):
    from app.routes.portfolio import _sync_all_positions, _rebuild_daily_data

    _sync_all_positions(db)
    missing = _rebuild_daily_data(db)
    result = {'message': '同步完成'}
    if missing:
        result['warning'] = f'{len(missing)} 条持仓数据缺失日线收盘价'
    return result


@registry.register(
    name='dismiss_alert',
    description='标记某条持仓预警为已处理',
    parameters={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': '持仓快照 ID'},
        },
        'required': ['id'],
    },
    category='write',
)
async def dismiss_alert(db: Session, id: int):
    success_flag = portfolio_position_crud.mark_alert_triggered(db, id)
    if not success_flag:
        return {'error': '持仓不存在'}
    return {'message': '已标记为已处理'}
