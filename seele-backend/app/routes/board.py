"""
板块/ETF 数据查询路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.response import page_success, success

router = APIRouter(prefix='/board', tags=['板块/ETF'])


@router.post('/list')
def query_board_list(query: schemas.BoardInfoQuery, db: Session = Depends(get_db)):
    """分页查询板块/ETF 列表，含指定交易日（或最新）的涨跌幅"""
    items, total = crud.board_info_crud.get_list(db, query)
    return page_success(items, total, query.page_num, query.page_size)


@router.post('/daily')
def query_board_daily(query: schemas.BoardDailyQuery, db: Session = Depends(get_db)):
    """分页查询单板块/ETF 的日线数据"""
    items, total = crud.board_daily_crud.get_by_code(
        db, query.code, query.start_date, query.end_date, query.page_num, query.page_size
    )
    return page_success(
        [{
            'trade_date': str(r.trade_date),
            'open': float(r.open) if r.open else None,
            'high': float(r.high) if r.high else None,
            'low': float(r.low) if r.low else None,
            'close': float(r.close) if r.close else None,
            'volume': float(r.volume) if r.volume else None,
            'amount': float(r.amount) if r.amount else None,
            'pct_chg': float(r.pct_chg) if r.pct_chg else None,
        } for r in items],
        total, query.page_num, query.page_size,
    )


@router.get('/constituents/{code}')
def query_board_constituents(code: str, db: Session = Depends(get_db)):
    """查询板块/ETF 的成分股列表，含最新行情"""
    items = crud.board_constituent_crud.get_by_board(db, code)
    return success([{
        'symbol': c.constituent_symbol,
        'name': c.name or '',
        'trade_date': str(c.trade_date) if c.trade_date else None,
        'open': float(c.open) if c.open is not None else None,
        'high': float(c.high) if c.high is not None else None,
        'low': float(c.low) if c.low is not None else None,
        'close': float(c.close) if c.close is not None else None,
        'pct_chg': float(c.pct_chg) if c.pct_chg is not None else None,
        'volume': float(c.volume) if c.volume is not None else None,
        'amount': float(c.amount) if c.amount is not None else None,
        'update_date': str(c.update_date) if c.update_date else None,
    } for c in items])


@router.post('/constituents/save')
def save_board_constituent(data: schemas.BoardConstituentCreate, db: Session = Depends(get_db)):
    """保存板块-个股关联关系（存在则更新，不存在则新增）"""
    board = crud.board_info_crud.get_by_code(db, data.board_code)
    if not board:
        return success({'saved': False, 'reason': f'板块代码 {data.board_code} 不存在'})

    stock = crud.stock_basic_crud.get_by_symbol(db, data.constituent_symbol)
    if not stock:
        return success({'saved': False, 'reason': f'股票代码 {data.constituent_symbol} 不存在'})

    db_obj, is_created = crud.board_constituent_crud.upsert(db, data)
    db.commit()
    db.refresh(db_obj)
    return success({
        'saved': True,
        'is_created': is_created,
        'id': db_obj.id,
        'board_code': db_obj.board_code,
        'constituent_symbol': db_obj.constituent_symbol,
        'name': db_obj.name,
        'update_date': str(db_obj.update_date) if db_obj.update_date else None,
    })
