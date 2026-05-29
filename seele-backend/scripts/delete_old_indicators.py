#!/usr/bin/env python3
"""
独立脚本：删除最近 20 个交易日之前的旧指标数据

与项目代码完全解耦，可直接运行：
    .venv/Scripts/python scripts/delete_old_indicators.py
"""

import logging
import os
import sys

from sqlalchemy import Column, Date, Integer, String, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker

# ==================== 配置区 ====================

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '20020228')
DB_NAME = os.environ.get('DB_NAME', 'seele')

DATABASE_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

Base = declarative_base()


# ==================== 数据库模型 ====================


class StockDaily(Base):
    __tablename__ = 'stock_daily'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)


class StockDailyIndicator(Base):
    __tablename__ = 'stock_daily_indicator'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)


# ==================== 主逻辑 ====================


def main():
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=5,
        echo=False,
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. 获取最近 20 个交易日
        rows = (
            session.query(StockDaily.trade_date)
            .distinct()
            .order_by(StockDaily.trade_date.desc())
            .limit(20)
            .all()
        )
        if len(rows) < 20:
            logger.warning('stock_daily 表数据不足 20 个交易日，无法确定 cutoff')
            return

        # 第 20 个交易日（更早的数据要删除）
        cutoff_date = rows[-1][0]
        logger.info('最近 20 个交易日截止到: %s', cutoff_date.strftime('%Y%m%d'))
        logger.info('将删除 %s 之前的所有指标数据', cutoff_date.strftime('%Y%m%d'))

        # 2. 查询待删除数量
        count_before = (
            session.query(StockDailyIndicator)
            .filter(StockDailyIndicator.trade_date < cutoff_date)
            .count()
        )
        logger.info('待删除记录数: %d', count_before)

        if count_before == 0:
            logger.info('没有需要删除的旧指标数据')
            return

        # 3. 执行删除
        deleted = (
            session.query(StockDailyIndicator)
            .filter(StockDailyIndicator.trade_date < cutoff_date)
            .delete(synchronize_session=False)
        )
        session.commit()
        logger.info('已删除 %d 条旧指标记录', deleted)

        # 4. 验证
        remaining = session.query(StockDailyIndicator).count()
        logger.info('stock_daily_indicator 表剩余记录: %d', remaining)

    finally:
        session.close()


if __name__ == '__main__':
    main()
