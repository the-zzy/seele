"""
回测路由
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.crud import (
    backtest_decision_log_crud,
    backtest_run_crud,
    backtest_snapshot_crud,
    backtest_trade_crud,
)
from app.database import SessionLocal, get_db
from app.response import list_success, page_success, success
from app.services import backtest_engine

router = APIRouter(prefix='/backtest', tags=['回测'])

logger = logging.getLogger(__name__)

TASK_TIMEOUT_MINUTES = 30


def _register_task_db(
    db: Session,
    task_id: str,
    run_id: Optional[int] = None,
) -> models.BacktestTask:
    """在数据库中注册后台任务"""
    task = models.BacktestTask(
        task_id=task_id,
        run_id=run_id,
        status='running',
        progress_current=0,
        progress_total=0,
    )
    db.add(task)
    db.flush()
    return task


def _acquire_run_lock(
    db: Session,
    run_id: int,
    task_id: str,
) -> bool:
    """用 SELECT FOR UPDATE 锁住 run 行，并检查是否已有进行中的任务。"""
    run = (
        db.query(models.BacktestRun)
        .filter(models.BacktestRun.id == run_id)
        .with_for_update()
        .first()
    )
    if not run:
        return False
    existing = (
        db.query(models.BacktestTask)
        .filter(
            models.BacktestTask.run_id == run_id,
            models.BacktestTask.status == 'running',
        )
        .first()
    )
    if existing:
        return False
    _register_task_db(db, task_id, run_id)
    return True


def _update_task_progress(
    db: Session,
    task_id: str,
    current: int,
    total: int,
) -> None:
    task = db.query(models.BacktestTask).filter(models.BacktestTask.task_id == task_id).first()
    if not task:
        return
    task.progress_current = current
    task.progress_total = total
    db.commit()


def _finish_task(
    db: Session,
    task_id: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:
    task = db.query(models.BacktestTask).filter(models.BacktestTask.task_id == task_id).first()
    if not task:
        return
    task.status = 'success' if error is None else 'failed'
    task.result_json = (
        json.dumps(result, ensure_ascii=False, default=str) if result is not None else None
    )
    task.error = error
    task.finished_at = datetime.now()
    db.commit()


def _cleanup_timeout_tasks(db: Session) -> None:
    cutoff = datetime.now() - timedelta(minutes=TASK_TIMEOUT_MINUTES)
    db.query(models.BacktestTask).filter(
        models.BacktestTask.status == 'running',
        models.BacktestTask.started_at < cutoff,
    ).update(
        {
            'status': 'failed',
            'error': f'任务超时（超过 {TASK_TIMEOUT_MINUTES} 分钟）',
            'finished_at': datetime.now(),
        },
        synchronize_session=False,
    )
    db.commit()


def _has_running_task_for_run(db: Session, run_id: int) -> bool:
    """检查指定 run 是否已有正在执行的后台任务"""
    _cleanup_timeout_tasks(db)
    return (
        db.query(models.BacktestTask)
        .filter(
            models.BacktestTask.run_id == run_id,
            models.BacktestTask.status == 'running',
        )
        .first()
        is not None
    )


def _get_running_task_for_run(db: Session, run_id: int) -> Optional[dict]:
    """获取指定 run 正在执行的后台任务信息"""
    _cleanup_timeout_tasks(db)
    task = (
        db.query(models.BacktestTask)
        .filter(
            models.BacktestTask.run_id == run_id,
            models.BacktestTask.status == 'running',
        )
        .first()
    )
    if not task:
        return None
    return {
        'task_id': task.task_id,
        'status': task.status,
        'progress': {
            'current': task.progress_current or 0,
            'total': task.progress_total or 0,
            'percent': (
                round(task.progress_current / task.progress_total * 100, 1)
                if task.progress_total
                else 0
            ),
        },
        'started_at': task.started_at.isoformat() if task.started_at else None,
    }


def _task_to_dict(task: models.BacktestTask) -> dict:
    """把 BacktestTask ORM 对象转成接口返回字典"""
    result = None
    if task.result_json:
        try:
            result = json.loads(task.result_json)
        except Exception:
            result = task.result_json
    return {
        'task_id': task.task_id,
        'run_id': task.run_id,
        'status': task.status,
        'result': result,
        'error': task.error,
        'progress': {
            'current': task.progress_current or 0,
            'total': task.progress_total or 0,
            'percent': (
                round(task.progress_current / task.progress_total * 100, 1)
                if task.progress_total
                else 0
            ),
        },
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'finished_at': task.finished_at.isoformat() if task.finished_at else None,
    }


@router.get('/{run_id}/running-task')
def get_running_task(run_id: int, db: Session = Depends(get_db)):
    """查询指定回测是否有正在执行的后台任务（用于刷新页面后恢复轮询）"""
    task = _get_running_task_for_run(db, run_id)
    return success(task)


def _run_auto_bg(task_id: str, run_id: int) -> None:
    db = SessionLocal()
    try:
        backtest_engine.run_until_end(db, run_id, task_id)
    finally:
        db.close()


def _create_and_run_first_day(task_id: str, obj_in: schemas.BacktestCreate) -> None:
    """后台任务：创建回测并执行首日交易"""
    db = SessionLocal()
    try:
        result = backtest_engine.create_run(db, obj_in)
        # 把 run_id 回填到任务记录
        task = db.query(models.BacktestTask).filter(models.BacktestTask.task_id == task_id).first()
        if task:
            task.run_id = result['run'].id
        _finish_task(
            db,
            task_id,
            result={
                'run_id': result['run'].id,
                'run': schemas.BacktestResponse.model_validate(result['run']).model_dump(),
                'snapshot': schemas.BacktestSnapshotResponse.model_validate(result['snapshot']).model_dump(),
                'trades': [schemas.BacktestTradeResponse.model_validate(t).model_dump() for t in result['trades']],
                'reasoning': result['reasoning'],
                'pool': result['pool'],
            },
        )
    except Exception as exc:
        logger.error('[BACKTEST_CREATE] 创建回测失败: %s', exc)
        _finish_task(db, task_id, error=str(exc))
    finally:
        db.close()


def _run_step_bg(task_id: str, run_id: int) -> None:
    """后台任务：执行下一天交易"""
    db = SessionLocal()
    try:
        result = backtest_engine.step(db, run_id)
        run = backtest_run_crud.get_by_id(db, run_id)
        _finish_task(
            db,
            task_id,
            result={
                'run_id': run.id,
                'run': schemas.BacktestResponse.model_validate(run).model_dump(),
                'snapshot': schemas.BacktestSnapshotResponse.model_validate(result['snapshot']).model_dump(),
                'trades': [schemas.BacktestTradeResponse.model_validate(t).model_dump() for t in result['trades']],
                'reasoning': result['reasoning'],
                'pool': result['pool'],
            },
        )
    except Exception as exc:
        logger.error('[BACKTEST_STEP] 执行步骤失败: %s', exc)
        _finish_task(db, task_id, error=str(exc))
    finally:
        db.close()


@router.post('')
def create_backtest(
    obj_in: schemas.BacktestCreate,
    db: Session = Depends(get_db),
):
    """创建回测（异步执行首日交易，避免 AI 调用超时）"""
    try:
        backtest_engine._parse_date(obj_in.start_date)
        if obj_in.end_date:
            backtest_engine._parse_date(obj_in.end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f'日期格式错误: {exc}')

    task_id = str(uuid.uuid4())
    _register_task_db(db, task_id, run_id=None)
    db.commit()
    t = threading.Thread(target=_create_and_run_first_day, args=(task_id, obj_in), daemon=True)
    t.start()
    return success({
        'task_id': task_id,
        'status': 'running',
        'hint': '回测创建中，正在执行首日交易',
    })


@router.get('')
def list_backtests(
    status: Optional[str] = Query(None, description='状态过滤'),
    page_num: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """回测列表"""
    query = schemas.BacktestQuery(status=status, page_num=page_num, page_size=page_size)
    list_data, total = backtest_run_crud.get_list(db, query)
    return page_success(
        [schemas.BacktestResponse.model_validate(r).model_dump() for r in list_data],
        total=total,
        page_num=page_num,
        page_size=page_size,
    )


@router.get('/task/{task_id}')
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """查询后台任务状态（必须放在 /{run_id} 之前，避免路由被 shadow）"""
    _cleanup_timeout_tasks(db)
    task = db.query(models.BacktestTask).filter(models.BacktestTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail='任务不存在')
    return success(_task_to_dict(task))


@router.get('/{run_id}')
def get_backtest(
    run_id: int,
    db: Session = Depends(get_db),
):
    """获取回测详情及最新快照"""
    run = backtest_run_crud.get_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='回测不存在')
    latest_snapshot = (
        db.query(models.BacktestDailySnapshot)
        .filter(models.BacktestDailySnapshot.run_id == run_id)
        .order_by(models.BacktestDailySnapshot.trade_date.desc())
        .first()
    )
    data = schemas.BacktestResponse.model_validate(run).model_dump()
    data['latest_snapshot'] = schemas.BacktestSnapshotResponse.model_validate(latest_snapshot).model_dump() if latest_snapshot else None
    return success(data)


@router.post('/{run_id}/step')
def step_backtest(
    run_id: int,
    db: Session = Depends(get_db),
):
    """手动执行下一天"""
    try:
        result = backtest_engine.step(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    run = backtest_run_crud.get_by_id(db, run_id)
    return success({
        'run': schemas.BacktestResponse.model_validate(run).model_dump(),
        'snapshot': schemas.BacktestSnapshotResponse.model_validate(result['snapshot']).model_dump(),
        'trades': [schemas.BacktestTradeResponse.model_validate(t).model_dump() for t in result['trades']],
        'reasoning': result['reasoning'],
        'pool': result['pool'],
    })


@router.post('/{run_id}/step-async')
def step_backtest_async(
    run_id: int,
    db: Session = Depends(get_db),
):
    """异步执行下一天（避免 AI 调用超时）"""
    run = backtest_run_crud.get_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='回测不存在')
    if run.status != 'running':
        raise HTTPException(status_code=400, detail=f'回测状态为 {run.status}，无法继续')

    task_id = str(uuid.uuid4())
    if not _acquire_run_lock(db, run_id, task_id):
        raise HTTPException(status_code=409, detail='当前回测有进行中的任务，请等待完成')
    db.commit()

    t = threading.Thread(target=_run_step_bg, args=(task_id, run_id), daemon=True)
    t.start()
    return success({
        'task_id': task_id,
        'status': 'running',
        'hint': '下一天执行中',
    })


@router.post('/{run_id}/auto')
def auto_backtest(
    run_id: int,
    end_date: Optional[str] = Query(None, description='结束日期 YYYY-MM-DD，优先使用该参数'),
    db: Session = Depends(get_db),
):
    """自动运行回测到结束日期"""
    run = backtest_run_crud.get_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='回测不存在')

    task_id = str(uuid.uuid4())
    if not _acquire_run_lock(db, run_id, task_id):
        raise HTTPException(status_code=409, detail='当前回测有进行中的任务，请等待完成')

    if end_date:
        run.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if not run.end_date:
        raise HTTPException(status_code=400, detail='未设置结束日期')
    db.commit()

    t = threading.Thread(target=_run_auto_bg, args=(task_id, run_id), daemon=True)
    t.start()
    return success({
        'task_id': task_id,
        'run_id': run_id,
        'status': 'running',
        'hint': '回测任务已提交后台执行',
    })


@router.get('/{run_id}/trades')
def get_backtest_trades(
    run_id: int,
    page_num: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """回测交易记录"""
    if not backtest_run_crud.get_by_id(db, run_id):
        raise HTTPException(status_code=404, detail='回测不存在')
    list_data, total = backtest_trade_crud.get_by_run_id(db, run_id, page_num=page_num, page_size=page_size)
    return page_success(
        [schemas.BacktestTradeResponse.model_validate(r).model_dump() for r in list_data],
        total=total,
        page_num=page_num,
        page_size=page_size,
    )


@router.get('/{run_id}/snapshots')
def get_backtest_snapshots(
    run_id: int,
    page_num: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """回测每日快照"""
    if not backtest_run_crud.get_by_id(db, run_id):
        raise HTTPException(status_code=404, detail='回测不存在')
    list_data, total = backtest_snapshot_crud.get_by_run_id(db, run_id, page_num=page_num, page_size=page_size)
    return page_success(
        [schemas.BacktestSnapshotResponse.model_validate(r).model_dump() for r in list_data],
        total=total,
        page_num=page_num,
        page_size=page_size,
    )


@router.get('/{run_id}/decisions')
def get_backtest_decisions(
    run_id: int,
    page_num: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """回测 AI 决策日志"""
    if not backtest_run_crud.get_by_id(db, run_id):
        raise HTTPException(status_code=404, detail='回测不存在')
    list_data, total = backtest_decision_log_crud.get_by_run_id(db, run_id, page_num=page_num, page_size=page_size)
    return page_success(
        [schemas.BacktestDecisionLogResponse.model_validate(r).model_dump() for r in list_data],
        total=total,
        page_num=page_num,
        page_size=page_size,
    )


@router.delete('/{run_id}')
def delete_backtest(
    run_id: int,
    db: Session = Depends(get_db),
):
    """删除回测及关联数据"""
    run = backtest_run_crud.get_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='回测不存在')
    backtest_run_crud.delete(db, run_id)
    db.commit()
    return success({'run_id': run_id, 'status': 'deleted'})


@router.post('/{run_id}/revert')
def revert_backtest(
    run_id: int,
    db: Session = Depends(get_db),
):
    """撤回一天：删除当前日期的交易、快照、决策日志，回退到前一天状态"""
    run = backtest_run_crud.get_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='回测不存在')
    if run.current_date <= run.start_date:
        raise HTTPException(status_code=400, detail='已经是最早日期，无法撤回')

    # 获取前一天快照
    prev_snapshot = (
        db.query(models.BacktestDailySnapshot)
        .filter(
            models.BacktestDailySnapshot.run_id == run_id,
            models.BacktestDailySnapshot.trade_date < run.current_date,
        )
        .order_by(models.BacktestDailySnapshot.trade_date.desc())
        .first()
    )

    # 删除当前日期的交易、快照、决策日志
    db.query(models.BacktestTrade).filter(
        models.BacktestTrade.run_id == run_id,
        models.BacktestTrade.trade_date == run.current_date,
    ).delete()
    db.query(models.BacktestDailySnapshot).filter(
        models.BacktestDailySnapshot.run_id == run_id,
        models.BacktestDailySnapshot.trade_date == run.current_date,
    ).delete()
    db.query(models.BacktestDecisionLog).filter(
        models.BacktestDecisionLog.run_id == run_id,
        models.BacktestDecisionLog.trade_date == run.current_date,
    ).delete()

    if prev_snapshot:
        backtest_run_crud.update_state(
            db,
            run_id,
            prev_snapshot.trade_date,
            float(prev_snapshot.cash),
            float(prev_snapshot.total_market_value),
            status='running',
        )
    else:
        backtest_run_crud.update_state(
            db,
            run_id,
            run.start_date,
            float(run.initial_capital),
            0.0,
            status='running',
        )
    db.commit()

    run = backtest_run_crud.get_by_id(db, run_id)
    return success(schemas.BacktestResponse.model_validate(run).model_dump())


@router.post('/batch-delete')
def batch_delete_backtests(
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
):
    """批量删除回测。

    - 传入 {run_ids: [...]} 时只删除指定回测
    - 不传 run_ids 时清空全部回测数据
    """
    run_ids = (payload or {}).get('run_ids')
    if run_ids:
        run_ids = [int(rid) for rid in run_ids if isinstance(rid, (int, float, str))]
        db.query(models.BacktestTrade).filter(models.BacktestTrade.run_id.in_(run_ids)).delete()
        db.query(models.BacktestDailySnapshot).filter(models.BacktestDailySnapshot.run_id.in_(run_ids)).delete()
        db.query(models.BacktestDecisionLog).filter(models.BacktestDecisionLog.run_id.in_(run_ids)).delete()
        db.query(models.BacktestTask).filter(models.BacktestTask.run_id.in_(run_ids)).delete()
        db.query(models.BacktestRun).filter(models.BacktestRun.id.in_(run_ids)).delete()
    else:
        db.query(models.BacktestTrade).delete()
        db.query(models.BacktestDailySnapshot).delete()
        db.query(models.BacktestDecisionLog).delete()
        db.query(models.BacktestTask).delete()
        db.query(models.BacktestRun).delete()
    db.commit()
    return success({'status': 'deleted'})
