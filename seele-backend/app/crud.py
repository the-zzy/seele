"""
数据库CRUD操作模块
"""

from typing import List, Optional
from datetime import date
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app import models, schemas


# ==================== 股票基础数据 ====================


class StockBasicCRUD:
    """股票基础数据CRUD"""

    def get_by_id(self, db: Session, id: int) -> Optional[models.StockBasic]:
        """根据ID查询"""
        return db.query(models.StockBasic).filter(models.StockBasic.id == id).first()

    def get_by_symbol(self, db: Session, symbol: str) -> Optional[models.StockBasic]:
        """根据股票代码查询"""
        return db.query(models.StockBasic).filter(models.StockBasic.symbol == symbol).first()

    def get_by_industry(self, db: Session, industry: str) -> List[models.StockBasic]:
        """根据行业查询"""
        return db.query(models.StockBasic).filter(models.StockBasic.industry == industry).all()

    def get_list(
        self,
        db: Session,
        query: schemas.StockBasicQuery,
    ) -> tuple[List[models.StockBasic], int]:
        """分页查询"""
        # 构建查询条件
        filters = []
        if query.symbol and query.name:
            # symbol 与 name 同时传时，使用 OR 匹配（模糊搜索场景）
            filters.append(or_(
                models.StockBasic.symbol.like(f"%{query.symbol}%"),
                models.StockBasic.name.like(f"%{query.name}%")
            ))
        else:
            if query.symbol:
                filters.append(models.StockBasic.symbol.like(f"%{query.symbol}%"))
            if query.name:
                filters.append(models.StockBasic.name.like(f"%{query.name}%"))
        if query.industry:
            filters.append(models.StockBasic.industry == query.industry)
        if query.market:
            filters.append(models.StockBasic.market == query.market)
        if query.area:
            filters.append(models.StockBasic.area == query.area)
        if query.exclude_st:
            filters.append(models.StockBasic.name.notlike('%ST%'))
        if query.exclude_cyb:
            filters.append(models.StockBasic.symbol.notlike('300%'))
            filters.append(models.StockBasic.symbol.notlike('301%'))
        if query.exclude_kcb:
            filters.append(models.StockBasic.symbol.notlike('688%'))
        if query.exclude_bse:
            filters.append(models.StockBasic.symbol.notlike('4%'))
            filters.append(models.StockBasic.symbol.notlike('8%'))

        # 构建排序
        order_column = models.StockBasic.symbol
        if query.sort_field:
            field_map = {
                "symbol": models.StockBasic.symbol,
                "name": models.StockBasic.name,
                "industry": models.StockBasic.industry,
                "market": models.StockBasic.market,
                "area": models.StockBasic.area,
                "listDate": models.StockBasic.list_date,
            }
            order_column = field_map.get(query.sort_field, models.StockBasic.symbol)

        order = order_column.asc() if query.sort_order == "asc" else order_column.desc()

        # 查询总数
        total = db.query(func.count(models.StockBasic.id))
        if filters:
            total = total.filter(and_(*filters))
        total = total.scalar()

        # 查询列表
        stmt = db.query(models.StockBasic)
        if filters:
            stmt = stmt.filter(and_(*filters))
        stmt = stmt.order_by(order).offset((query.page_num - 1) * query.page_size).limit(query.page_size)
        list_data = stmt.all()

        return list_data, total

    def get_batch(self, db: Session, symbols: List[str]) -> List[models.StockBasic]:
        """批量查询"""
        return db.query(models.StockBasic).filter(models.StockBasic.symbol.in_(symbols)).all()

    def create(self, db: Session, obj_in: schemas.StockBasicCreate) -> models.StockBasic:
        """创建"""
        db_obj = models.StockBasic(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, obj_in: schemas.StockBasicUpdate) -> Optional[models.StockBasic]:
        """更新"""
        db_obj = self.get_by_id(db, obj_in.id)
        if db_obj:
            update_data = obj_in.model_dump(exclude={"id"})
            for key, value in update_data.items():
                if value is not None:
                    setattr(db_obj, key, value)
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def upsert(self, db: Session, obj_in: schemas.StockBasicCreate) -> models.StockBasic:
        """存在则更新，不存在则插入"""
        existing = self.get_by_symbol(db, obj_in.symbol)
        if existing:
            update_data = obj_in.model_dump(exclude={"symbol"})
            for key, value in update_data.items():
                if value is not None:
                    setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            return self.create(db, obj_in)

    def upsert_batch(self, db: Session, obj_list: list[schemas.StockBasicCreate]) -> dict:
        """批量 upsert"""
        created = 0
        updated = 0
        for obj in obj_list:
            existing = self.get_by_symbol(db, obj.symbol)
            if existing:
                update_data = obj.model_dump(exclude={"symbol"})
                for key, value in update_data.items():
                    if value is not None:
                        setattr(existing, key, value)
                updated += 1
            else:
                db_obj = models.StockBasic(**obj.model_dump())
                db.add(db_obj)
                created += 1
        db.commit()
        return {"created": created, "updated": updated}

    def delete(self, db: Session, id: int) -> bool:
        """删除"""
        db_obj = self.get_by_id(db, id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False


stock_basic_crud = StockBasicCRUD()


# ==================== 股票日线数据 ====================


class StockDailyCRUD:
    """股票日线数据CRUD"""

    def get_by_id(self, db: Session, id: int) -> Optional[models.StockDaily]:
        """根据ID查询"""
        return db.query(models.StockDaily).filter(models.StockDaily.id == id).first()

    def get_by_symbol(self, db: Session, symbol: str) -> List[models.StockDaily]:
        """根据股票代码查询"""
        return db.query(models.StockDaily).filter(models.StockDaily.symbol == symbol).all()

    def get_by_date(self, db: Session, trade_date: str) -> List[models.StockDaily]:
        """根据交易日期查询"""
        return db.query(models.StockDaily).filter(models.StockDaily.trade_date == trade_date).all()

    def get_list(
        self,
        db: Session,
        query: schemas.StockDailyQuery,
    ) -> tuple[List[models.StockDaily], int]:
        """分页查询"""
        # 构建查询条件
        filters = []
        if query.symbol:
            filters.append(models.StockDaily.symbol == query.symbol)
        if query.start_date:
            filters.append(models.StockDaily.trade_date >= query.start_date)
        if query.end_date:
            filters.append(models.StockDaily.trade_date <= query.end_date)

        # 查询总数
        total = db.query(func.count(models.StockDaily.id))
        if filters:
            total = total.filter(and_(*filters))
        total = total.scalar()

        # 查询列表
        stmt = db.query(models.StockDaily)
        if filters:
            stmt = stmt.filter(and_(*filters))
        stmt = stmt.order_by(models.StockDaily.trade_date.desc()).offset((query.page_num - 1) * query.page_size).limit(query.page_size)
        list_data = stmt.all()

        return list_data, total

    def get_by_symbol_date_range(
        self,
        db: Session,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> List[models.StockDaily]:
        """根据股票代码和日期范围查询"""
        return (
            db.query(models.StockDaily)
            .filter(
                and_(
                    models.StockDaily.symbol == symbol,
                    models.StockDaily.trade_date >= start_date,
                    models.StockDaily.trade_date <= end_date,
                )
            )
            .order_by(models.StockDaily.trade_date.asc())
            .all()
        )

    def get_batch(self, db: Session, symbols: List[str]) -> List[models.StockDaily]:
        """批量查询"""
        return db.query(models.StockDaily).filter(models.StockDaily.symbol.in_(symbols)).all()

    def get_trade_dates(self, db: Session) -> List[date]:
        """获取所有交易日（查询所有不重复的交易日期）"""
        from sqlalchemy import distinct
        results = (
            db.query(distinct(models.StockDaily.trade_date))
            .order_by(models.StockDaily.trade_date.desc())
            .all()
        )
        return [r[0] for r in results]

    def _get_pre_close(self, db: Session, symbol: str, trade_date) -> Optional[float]:
        """获取前一日收盘价"""
        prev = (
            db.query(models.StockDaily)
            .filter(
                and_(
                    models.StockDaily.symbol == symbol,
                    models.StockDaily.trade_date < trade_date,
                )
            )
            .order_by(models.StockDaily.trade_date.desc())
            .first()
        )
        return prev.close if prev else None

    def _fill_calculated_fields(self, db: Session, data: dict) -> dict:
        """自动计算涨跌额、涨跌幅、振幅（仅当字段为空且存在必要价格数据时）"""
        close = data.get("close")
        high = data.get("high")
        low = data.get("low")
        symbol = data.get("symbol")
        trade_date = data.get("trade_date")

        if close is None or high is None or low is None or symbol is None or trade_date is None:
            return data

        # 若三个字段都已提供，无需计算
        if (
            data.get("price_change") is not None
            and data.get("pct_chg") is not None
            and data.get("amplitude") is not None
        ):
            return data

        pre_close = self._get_pre_close(db, symbol, trade_date)
        if pre_close:
            if data.get("price_change") is None:
                data["price_change"] = round(close - pre_close, 4)
            if data.get("pct_chg") is None:
                data["pct_chg"] = round((close - pre_close) / pre_close * 100, 4)
            if data.get("amplitude") is None:
                data["amplitude"] = round((high - low) / pre_close * 100, 4)
        else:
            if data.get("price_change") is None:
                data["price_change"] = 0.0
            if data.get("pct_chg") is None:
                data["pct_chg"] = 0.0
            if data.get("amplitude") is None:
                data["amplitude"] = 0.0
        return data

    def create(self, db: Session, obj_in: schemas.StockDailyCreate) -> models.StockDaily:
        """创建"""
        data = self._fill_calculated_fields(db, obj_in.model_dump())
        db_obj = models.StockDaily(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_batch(self, db: Session, obj_list: List[schemas.StockDailyCreate]) -> int:
        """批量创建"""
        db_objs = []
        for obj in obj_list:
            data = self._fill_calculated_fields(db, obj.model_dump())
            db_objs.append(models.StockDaily(**data))
        db.add_all(db_objs)
        db.commit()
        return len(db_objs)

    def upsert(self, db: Session, obj_in: schemas.StockDailyCreate) -> models.StockDaily:
        """存在则更新，不存在则插入"""
        existing = (
            db.query(models.StockDaily)
            .filter(
                and_(
                    models.StockDaily.trade_date == obj_in.trade_date,
                    models.StockDaily.symbol == obj_in.symbol,
                )
            )
            .first()
        )
        if existing:
            update_data = obj_in.model_dump(exclude={"id", "trade_date", "symbol"})

            # 若更新时未提供计算字段，但提供了价格数据，则自动计算
            close = update_data.get("close") if update_data.get("close") is not None else existing.close
            high = update_data.get("high") if update_data.get("high") is not None else existing.high
            low = update_data.get("low") if update_data.get("low") is not None else existing.low

            if close is not None and high is not None and low is not None and (
                update_data.get("price_change") is None
                or update_data.get("pct_chg") is None
                or update_data.get("amplitude") is None
            ):
                pre_close = self._get_pre_close(db, existing.symbol, existing.trade_date)
                if pre_close:
                    if update_data.get("price_change") is None:
                        update_data["price_change"] = round(close - pre_close, 4)
                    if update_data.get("pct_chg") is None:
                        update_data["pct_chg"] = round((close - pre_close) / pre_close * 100, 4)
                    if update_data.get("amplitude") is None:
                        update_data["amplitude"] = round((high - low) / pre_close * 100, 4)
                else:
                    if update_data.get("price_change") is None:
                        update_data["price_change"] = 0.0
                    if update_data.get("pct_chg") is None:
                        update_data["pct_chg"] = 0.0
                    if update_data.get("amplitude") is None:
                        update_data["amplitude"] = 0.0

            for key, value in update_data.items():
                if value is not None:
                    setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            data = self._fill_calculated_fields(db, obj_in.model_dump())
            db_obj = models.StockDaily(**data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj

    def update(self, db: Session, obj_in: schemas.StockDailyUpdate) -> Optional[models.StockDaily]:
        """更新"""
        db_obj = self.get_by_id(db, obj_in.id)
        if db_obj:
            update_data = obj_in.model_dump(exclude={"id"})
            for key, value in update_data.items():
                if value is not None:
                    setattr(db_obj, key, value)
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> bool:
        """删除"""
        db_obj = self.get_by_id(db, id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False


stock_daily_crud = StockDailyCRUD()


# ==================== 股票日线指标 ====================


class StockDailyIndicatorCRUD:
    """股票日线指标CRUD"""

    def get_by_symbol_date(
        self, db: Session, symbol: str, trade_date: date
    ) -> Optional[models.StockDailyIndicator]:
        """根据股票代码和交易日期查询"""
        return (
            db.query(models.StockDailyIndicator)
            .filter(
                and_(
                    models.StockDailyIndicator.symbol == symbol,
                    models.StockDailyIndicator.trade_date == trade_date,
                )
            )
            .first()
        )

    def get_by_symbol(self, db: Session, symbol: str) -> List[models.StockDailyIndicator]:
        """根据股票代码查询"""
        return (
            db.query(models.StockDailyIndicator)
            .filter(models.StockDailyIndicator.symbol == symbol)
            .order_by(models.StockDailyIndicator.trade_date.desc())
            .all()
        )

    def get_by_date(self, db: Session, trade_date: date) -> List[models.StockDailyIndicator]:
        """根据交易日期查询"""
        return (
            db.query(models.StockDailyIndicator)
            .filter(models.StockDailyIndicator.trade_date == trade_date)
            .all()
        )

    def create_or_update(
        self, db: Session, symbol: str, trade_date: date, indicator_data: dict
    ) -> models.StockDailyIndicator:
        """存在则更新，不存在则插入"""
        existing = self.get_by_symbol_date(db, symbol, trade_date)
        if existing:
            for key, value in indicator_data.items():
                if value is not None:
                    setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            db_obj = models.StockDailyIndicator(
                symbol=symbol,
                trade_date=trade_date,
                **indicator_data
            )
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj

    def create_or_update_batch(
        self, db: Session, items: List[dict]
    ) -> dict:
        """批量创建或更新"""
        success = 0
        failed = 0
        for item in items:
            try:
                symbol = item.pop("symbol")
                trade_date = item.pop("trade_date")
                self.create_or_update(db, symbol, trade_date, item)
                success += 1
            except Exception:
                failed += 1
        return {"success": success, "failed": failed}


stock_daily_indicator_crud = StockDailyIndicatorCRUD()


# ==================== 持仓交易记录 ====================


class PortfolioTradeCRUD:
    """持仓交易记录 CRUD"""

    def get_by_id(self, db: Session, id: int) -> Optional[models.PortfolioTrade]:
        """根据 ID 查询"""
        return db.query(models.PortfolioTrade).filter(models.PortfolioTrade.id == id).first()

    def get_list(
        self,
        db: Session,
        query: schemas.PortfolioTradeQuery,
    ) -> tuple[List[models.PortfolioTrade], int]:
        """分页查询"""
        filters = []
        if query.symbol:
            filters.append(models.PortfolioTrade.symbol == query.symbol)
        if query.trade_type:
            filters.append(models.PortfolioTrade.trade_type == query.trade_type)

        total = db.query(func.count(models.PortfolioTrade.id))
        if filters:
            total = total.filter(and_(*filters))
        total = total.scalar()

        stmt = db.query(models.PortfolioTrade)
        if filters:
            stmt = stmt.filter(and_(*filters))
        stmt = (
            stmt.order_by(models.PortfolioTrade.trade_date.desc())
            .offset((query.page_num - 1) * query.page_size)
            .limit(query.page_size)
        )
        list_data = stmt.all()
        return list_data, total

    def get_all(self, db: Session) -> List[models.PortfolioTrade]:
        """查询全部交易记录"""
        return db.query(models.PortfolioTrade).order_by(models.PortfolioTrade.trade_date.asc()).all()

    def get_by_symbol(self, db: Session, symbol: str) -> List[models.PortfolioTrade]:
        """根据股票代码查询交易记录"""
        return (
            db.query(models.PortfolioTrade)
            .filter(models.PortfolioTrade.symbol == symbol)
            .order_by(models.PortfolioTrade.trade_date.asc())
            .all()
        )

    def create(self, db: Session, obj_in: schemas.PortfolioTradeCreate) -> models.PortfolioTrade:
        """创建交易记录"""
        data = obj_in.model_dump()
        if data.get('amount') is None and data.get('price') and data.get('quantity'):
            data['amount'] = round(data['price'] * data['quantity'], 4)
        db_obj = models.PortfolioTrade(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> bool:
        """删除交易记录"""
        db_obj = self.get_by_id(db, id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False


portfolio_trade_crud = PortfolioTradeCRUD()


# ==================== 清仓盈亏记录 ====================


class PortfolioClosedCRUD:
    """清仓盈亏记录 CRUD"""

    def get_list(
        self,
        db: Session,
        page_num: int = 1,
        page_size: int = 20,
    ) -> tuple[List[models.PortfolioClosed], int]:
        """分页查询"""
        total = db.query(func.count(models.PortfolioClosed.id)).scalar()
        stmt = (
            db.query(models.PortfolioClosed)
            .order_by(models.PortfolioClosed.close_date.desc())
            .offset((page_num - 1) * page_size)
            .limit(page_size)
        )
        list_data = stmt.all()
        return list_data, total

    def get_all(self, db: Session) -> List[models.PortfolioClosed]:
        """查询全部清仓记录"""
        return db.query(models.PortfolioClosed).order_by(models.PortfolioClosed.close_date.desc()).all()

    def create(self, db: Session, data: dict) -> models.PortfolioClosed:
        """创建清仓记录"""
        db_obj = models.PortfolioClosed(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_by_symbol(self, db: Session, symbol: str) -> bool:
        """根据股票代码删除清仓记录（用于重新计算时清理）"""
        db.query(models.PortfolioClosed).filter(models.PortfolioClosed.symbol == symbol).delete()
        db.commit()
        return True


portfolio_closed_crud = PortfolioClosedCRUD()


# ==================== 持仓快照 ====================


class PortfolioPositionCRUD:
    """持仓快照 CRUD"""

    def get_by_symbol(self, db: Session, symbol: str, group: str = 'default') -> Optional[models.PortfolioPosition]:
        """根据股票代码和分组查询持仓快照"""
        return (
            db.query(models.PortfolioPosition)
            .filter(models.PortfolioPosition.symbol == symbol, models.PortfolioPosition.group == group)
            .first()
        )

    def get_list(self, db: Session, group: Optional[str] = None) -> List[models.PortfolioPosition]:
        """查询持仓快照列表"""
        stmt = db.query(models.PortfolioPosition)
        if group:
            stmt = stmt.filter(models.PortfolioPosition.group == group)
        return stmt.order_by(models.PortfolioPosition.unrealized_pnl.desc()).all()

    def upsert(self, db: Session, data: dict) -> models.PortfolioPosition:
        """更新或插入持仓快照"""
        symbol = data['symbol']
        group = data.get('group', 'default')
        db_obj = self.get_by_symbol(db, symbol, group)
        if db_obj:
            for key, value in data.items():
                setattr(db_obj, key, value)
        else:
            db_obj = models.PortfolioPosition(**data)
            db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_by_symbol(self, db: Session, symbol: str, group: str = 'default') -> bool:
        """根据股票代码和分组删除持仓快照"""
        db.query(models.PortfolioPosition).filter(
            models.PortfolioPosition.symbol == symbol,
            models.PortfolioPosition.group == group
        ).delete()
        db.commit()
        return True

    def get_alerts(self, db: Session) -> List[models.PortfolioPosition]:
        """获取触发止损/止盈预警的持仓"""
        return (
            db.query(models.PortfolioPosition)
            .filter(
                models.PortfolioPosition.quantity > 0,
                models.PortfolioPosition.alert_triggered == 0,
                models.PortfolioPosition.current_price.isnot(None),
                or_(
                    and_(
                        models.PortfolioPosition.stop_loss_price.isnot(None),
                        models.PortfolioPosition.current_price <= models.PortfolioPosition.stop_loss_price
                    ),
                    and_(
                        models.PortfolioPosition.take_profit_price.isnot(None),
                        models.PortfolioPosition.current_price >= models.PortfolioPosition.take_profit_price
                    )
                )
            )
            .all()
        )

    def mark_alert_triggered(self, db: Session, id: int) -> bool:
        """标记预警已触发"""
        db_obj = db.query(models.PortfolioPosition).filter(models.PortfolioPosition.id == id).first()
        if db_obj:
            db_obj.alert_triggered = 1
            db.commit()
            return True
        return False


portfolio_position_crud = PortfolioPositionCRUD()


# ==================== 持仓配置 ====================


class PortfolioConfigCRUD:
    """持仓配置 CRUD"""

    def get_or_create(self, db: Session) -> models.PortfolioConfig:
        """获取配置，不存在则创建默认值"""
        config = db.query(models.PortfolioConfig).first()
        if not config:
            config = models.PortfolioConfig(initial_capital=35000.0)
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    def update(self, db: Session, initial_capital: float) -> models.PortfolioConfig:
        """更新初始资金"""
        config = self.get_or_create(db)
        config.initial_capital = initial_capital
        db.commit()
        db.refresh(config)
        return config


portfolio_config_crud = PortfolioConfigCRUD()