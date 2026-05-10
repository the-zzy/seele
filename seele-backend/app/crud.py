"""
数据库CRUD操作模块
"""

from typing import List, Optional
from datetime import date, datetime
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
        """分页查询（关联财务指标）"""
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
                "roe": models.StockFinancialIndicator.roe,
                "gross_profit_ratio": models.StockFinancialIndicator.gross_profit_ratio,
                "grossProfitRatio": models.StockFinancialIndicator.gross_profit_ratio,
                "net_profit_ratio": models.StockFinancialIndicator.net_profit_ratio,
                "netProfitRatio": models.StockFinancialIndicator.net_profit_ratio,
                "net_profit_yoy": models.StockFinancialIndicator.net_profit_yoy,
                "netProfitYoy": models.StockFinancialIndicator.net_profit_yoy,
                "revenue_yoy": models.StockFinancialIndicator.revenue_yoy,
                "revenueYoy": models.StockFinancialIndicator.revenue_yoy,
                "eps": models.StockFinancialIndicator.eps,
                "debt_ratio": models.StockFinancialIndicator.debt_ratio,
            }
            order_column = field_map.get(query.sort_field, models.StockBasic.symbol)

        order = order_column.asc() if query.sort_order == "asc" else order_column.desc()

        # JOIN 财务指标表
        stmt = db.query(models.StockBasic, models.StockFinancialIndicator).outerjoin(
            models.StockFinancialIndicator,
            models.StockBasic.symbol == models.StockFinancialIndicator.symbol,
        )

        # 查询总数
        total = db.query(func.count(models.StockBasic.id))
        if filters:
            total = total.filter(and_(*filters))
        total = total.scalar()

        # 查询列表
        if filters:
            stmt = stmt.filter(and_(*filters))
        stmt = stmt.order_by(order).offset((query.page_num - 1) * query.page_size).limit(query.page_size)
        results = stmt.all()

        # 组装结果
        list_data = []
        for basic, financial in results:
            basic.roe = financial.roe if financial else None
            basic.gross_profit_ratio = financial.gross_profit_ratio if financial else None
            basic.net_profit_ratio = financial.net_profit_ratio if financial else None
            basic.net_profit_yoy = financial.net_profit_yoy if financial else None
            basic.revenue_yoy = financial.revenue_yoy if financial else None
            basic.eps = financial.eps if financial else None
            basic.debt_ratio = financial.debt_ratio if financial else None
            list_data.append(basic)

        return list_data, total

    def get_mainwave_list(
        self,
        db: Session,
        query: schemas.MainwavePickerQuery,
    ) -> tuple[List[dict], int, str]:
        """主升浪选股查询（关联日线及指标表）

        返回: (数据列表, 总数, 实际使用的交易日期)
        """
        # 确定交易日期：优先使用传入的日期，否则取 indicator 表最新有数据的交易日
        trade_date = query.trade_date
        if not trade_date:
            from sqlalchemy import distinct
            latest_indicator_date = (
                db.query(distinct(models.StockDailyIndicator.trade_date))
                .order_by(models.StockDailyIndicator.trade_date.desc())
                .first()
            )
            if latest_indicator_date:
                trade_date = str(latest_indicator_date[0])
            else:
                latest_dates = stock_daily_crud.get_trade_dates(db)
                if latest_dates:
                    trade_date = str(latest_dates[0])
                else:
                    trade_date = date.today().strftime("%Y-%m-%d")
        else:
            # 检查传入的日期是否有 indicator 数据，如果没有则 fallback
            formatted_check = trade_date.replace("-", "")
            has_indicator = (
                db.query(models.StockDailyIndicator)
                .filter(models.StockDailyIndicator.trade_date == formatted_check)
                .first()
            )
            if not has_indicator:
                from sqlalchemy import distinct
                latest_indicator_date = (
                    db.query(distinct(models.StockDailyIndicator.trade_date))
                    .order_by(models.StockDailyIndicator.trade_date.desc())
                    .first()
                )
                if latest_indicator_date:
                    trade_date = str(latest_indicator_date[0])
        formatted_date = trade_date.replace("-", "")

        # 基础查询：StockDaily JOIN StockBasic LEFT JOIN StockDailyIndicator
        q = (
            db.query(
                models.StockDaily,
                models.StockBasic.name.label("stock_name"),
                models.StockBasic.industry,
                models.StockBasic.market,
                models.StockBasic.area,
                models.StockBasic.float_market_cap,
                models.StockDailyIndicator.ma5,
                models.StockDailyIndicator.ma10,
                models.StockDailyIndicator.ma20,
                models.StockDailyIndicator.ma30,
                models.StockDailyIndicator.ma60,
                models.StockDailyIndicator.vol_ma5,
                models.StockDailyIndicator.vol_ma10,
                models.StockDailyIndicator.amount_ma5,
                models.StockDailyIndicator.amount_ma10,
                models.StockDailyIndicator.turnover_ma5,
                models.StockDailyIndicator.turnover_ma10,
            )
            .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
            .outerjoin(
                models.StockDailyIndicator,
                and_(
                    models.StockDaily.symbol == models.StockDailyIndicator.symbol,
                    models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
                ),
            )
        )

        # 强制条件1：主板、非ST、非创业板、非科创板
        q = q.filter(
            models.StockBasic.market == "主板",
            models.StockBasic.name.notlike("%ST%"),
            models.StockDaily.trade_date == formatted_date,
        )
        q = q.filter(
            models.StockBasic.symbol.notlike("300%"),
            models.StockBasic.symbol.notlike("301%"),
            models.StockBasic.symbol.notlike("688%"),
            models.StockBasic.symbol.notlike("689%"),
        )

        # 文本筛选
        if query.symbol and query.name:
            q = q.filter(
                or_(
                    models.StockBasic.symbol.like(f"%{query.symbol}%"),
                    models.StockBasic.name.like(f"%{query.name}%"),
                )
            )
        else:
            if query.symbol:
                q = q.filter(models.StockBasic.symbol.like(f"%{query.symbol}%"))
            if query.name:
                q = q.filter(models.StockBasic.name.like(f"%{query.name}%"))
        # 数值筛选（条件2-5）
        if query.float_market_cap_min is not None:
            q = q.filter(models.StockBasic.float_market_cap >= query.float_market_cap_min)
        if query.close_max is not None:
            q = q.filter(models.StockDaily.close <= query.close_max)
        if query.avg_turnover_min is not None:
            q = q.filter(models.StockDailyIndicator.turnover_ma10 >= query.avg_turnover_min)
        if query.avg_amount_min is not None:
            q = q.filter(models.StockDailyIndicator.amount_ma10 >= query.avg_amount_min)

        # 排序映射
        sort_column_map = {
            "symbol": models.StockDaily.symbol,
            "stock_name": models.StockBasic.name,
            "name": models.StockBasic.name,
            "open": models.StockDaily.open,
            "high": models.StockDaily.high,
            "low": models.StockDaily.low,
            "close": models.StockDaily.close,
            "volume": models.StockDaily.volume,
            "amount": models.StockDaily.amount,
            "amplitude": models.StockDaily.amplitude,
            "pct_chg": models.StockDaily.pct_chg,
            "pctChg": models.StockDaily.pct_chg,
            "price_change": models.StockDaily.price_change,
            "priceChange": models.StockDaily.price_change,
            "turnover": models.StockDaily.turnover,
            "ma5": models.StockDailyIndicator.ma5,
            "ma10": models.StockDailyIndicator.ma10,
            "ma20": models.StockDailyIndicator.ma20,
            "ma30": models.StockDailyIndicator.ma30,
            "ma60": models.StockDailyIndicator.ma60,
            "vol_ma5": models.StockDailyIndicator.vol_ma5,
            "volMa5": models.StockDailyIndicator.vol_ma5,
            "vol_ma10": models.StockDailyIndicator.vol_ma10,
            "volMa10": models.StockDailyIndicator.vol_ma10,
            "turnover_ma5": models.StockDailyIndicator.turnover_ma5,
            "turnoverMa5": models.StockDailyIndicator.turnover_ma5,
            "turnover_ma10": models.StockDailyIndicator.turnover_ma10,
            "turnoverMa10": models.StockDailyIndicator.turnover_ma10,
            "float_market_cap": models.StockBasic.float_market_cap,
        }
        sort_column = sort_column_map.get(query.sort_field, models.StockDaily.symbol)
        if query.sort_order == "desc":
            q = q.order_by(sort_column.desc())
        else:
            q = q.order_by(sort_column.asc())

        # 总数
        total = q.with_entities(func.count(models.StockDaily.id)).scalar() or 0

        # 分页
        results = (
            q.offset((query.page_num - 1) * query.page_size)
            .limit(query.page_size)
            .all()
        )

        data_list = []
        for (
            daily,
            stock_name,
            industry,
            market,
            area,
            float_market_cap,
            ma5,
            ma10,
            ma20,
            ma30,
            ma60,
            vol_ma5,
            vol_ma10,
            amount_ma5,
            amount_ma10,
            turnover_ma5,
            turnover_ma10,
        ) in results:
            data_list.append({
                "id": daily.id,
                "trade_date": str(daily.trade_date),
                "symbol": daily.symbol,
                "stock_name": stock_name or "",
                "name": stock_name or "",
                "industry": industry or "",
                "market": market or "",
                "area": area or "",
                "float_market_cap": float_market_cap,
                "open": daily.open,
                "high": daily.high,
                "low": daily.low,
                "close": daily.close,
                "volume": daily.volume,
                "amount": daily.amount,
                "amplitude": daily.amplitude,
                "pct_chg": daily.pct_chg,
                "price_change": daily.price_change,
                "turnover": daily.turnover,
                "ma5": ma5,
                "ma10": ma10,
                "ma20": ma20,
                "ma30": ma30,
                "ma60": ma60,
                "vol_ma5": vol_ma5,
                "vol_ma10": vol_ma10,
                "amount_ma5": amount_ma5,
                "amount_ma10": amount_ma10,
                "turnover_ma5": turnover_ma5,
                "turnover_ma10": turnover_ma10,
            })

        return data_list, total, trade_date

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
        self, db: Session, items: List[dict], batch_size: int = 500
    ) -> dict:
        """批量创建或更新（使用 INSERT ... ON DUPLICATE KEY UPDATE，分批写入）"""
        if not items:
            return {"success": 0, "failed": 0}

        from sqlalchemy.dialects.mysql import insert

        records = []
        for item in items:
            record = {
                "symbol": item.pop("symbol"),
                "trade_date": item.pop("trade_date"),
                **item,
            }
            records.append(record)

        total = len(records)
        success = 0
        failed = 0

        for i in range(0, total, batch_size):
            chunk = records[i:i + batch_size]
            try:
                upsert_stmt = insert(models.StockDailyIndicator).values(chunk)
                update_dict = {
                    k: upsert_stmt.inserted[k]
                    for k in upsert_stmt.inserted.keys()
                    if k not in ("id", "symbol", "trade_date", "created_at", "updated_at")
                }
                upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
                db.execute(upsert_stmt)
                db.commit()
                success += len(chunk)
            except Exception as exc:
                import logging, traceback
                logging.getLogger(__name__).error(
                    '[INDICATOR_BATCH] 批量写入失败 (batch %d-%d): %s', i, i + len(chunk), exc
                )
                logging.getLogger(__name__).error(traceback.format_exc())
                db.rollback()
                failed += len(chunk)

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
        page_size: int = 10,
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


# ==================== 每日持仓明细 ====================


class PortfolioDailyPositionCRUD:
    """每日持仓明细 CRUD"""

    def get_list(self, db: Session) -> List[models.PortfolioDailyPosition]:
        """查询全部，按日期和代码排序"""
        return (
            db.query(models.PortfolioDailyPosition)
            .order_by(
                models.PortfolioDailyPosition.trade_date.asc(),
                models.PortfolioDailyPosition.symbol.asc(),
            )
            .all()
        )

    def get_by_date(self, db: Session, trade_date: date) -> List[models.PortfolioDailyPosition]:
        """根据日期查询当日所有持仓"""
        return (
            db.query(models.PortfolioDailyPosition)
            .filter(models.PortfolioDailyPosition.trade_date == trade_date)
            .all()
        )

    def get_latest_date(self, db: Session) -> Optional[date]:
        """获取最新记录的日期"""
        row = (
            db.query(models.PortfolioDailyPosition.trade_date)
            .order_by(models.PortfolioDailyPosition.trade_date.desc())
            .first()
        )
        return row[0] if row else None

    def create_batch(self, db: Session, items: List[dict]) -> int:
        """批量创建，先清空再插入"""
        db.query(models.PortfolioDailyPosition).delete()
        db_objs = [models.PortfolioDailyPosition(**item) for item in items]
        db.add_all(db_objs)
        db.commit()
        return len(db_objs)

    def delete_all(self, db: Session) -> bool:
        """清空全部记录"""
        db.query(models.PortfolioDailyPosition).delete()
        db.commit()
        return True


portfolio_daily_position_crud = PortfolioDailyPositionCRUD()


# ==================== 每日资产汇总 ====================


class PortfolioDailySummaryCRUD:
    """每日资产汇总 CRUD"""

    def get_list(self, db: Session) -> List[models.PortfolioDailySummary]:
        """查询全部，按日期升序"""
        return (
            db.query(models.PortfolioDailySummary)
            .order_by(models.PortfolioDailySummary.trade_date.asc())
            .all()
        )

    def get_by_date(self, db: Session, trade_date: date) -> Optional[models.PortfolioDailySummary]:
        """根据日期查询"""
        return (
            db.query(models.PortfolioDailySummary)
            .filter(models.PortfolioDailySummary.trade_date == trade_date)
            .first()
        )

    def get_latest(self, db: Session) -> Optional[models.PortfolioDailySummary]:
        """获取最新一天的汇总"""
        return (
            db.query(models.PortfolioDailySummary)
            .order_by(models.PortfolioDailySummary.trade_date.desc())
            .first()
        )

    def create_batch(self, db: Session, items: List[dict]) -> int:
        """批量创建，先清空再插入"""
        db.query(models.PortfolioDailySummary).delete()
        db_objs = [models.PortfolioDailySummary(**item) for item in items]
        db.add_all(db_objs)
        db.commit()
        return len(db_objs)

    def delete_all(self, db: Session) -> bool:
        """清空全部记录"""
        db.query(models.PortfolioDailySummary).delete()
        db.commit()
        return True


portfolio_daily_summary_crud = PortfolioDailySummaryCRUD()


# ==================== 持仓快照 ====================


class PortfolioPositionCRUD:
    """持仓快照 CRUD"""

    def get_by_symbol(self, db: Session, symbol: str, group: str = None) -> Optional[models.PortfolioPosition]:
        """根据股票代码查询持仓快照（group 为 None 时不限分组）"""
        query = db.query(models.PortfolioPosition).filter(models.PortfolioPosition.symbol == symbol)
        if group:
            query = query.filter(models.PortfolioPosition.group == group)
        return query.first()

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

    def delete_by_symbol(self, db: Session, symbol: str, group: str = None) -> bool:
        """根据股票代码删除持仓快照（group 为 None 时不限分组）"""
        query = db.query(models.PortfolioPosition).filter(models.PortfolioPosition.symbol == symbol)
        if group:
            query = query.filter(models.PortfolioPosition.group == group)
        query.delete()
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


# ==================== 财务指标 ====================


class StockFinancialIndicatorCRUD:
    """财务指标 CRUD（仅保留最新一期，以 symbol 为唯一键）"""

    def get_by_symbol(self, db: Session, symbol: str) -> Optional[models.StockFinancialIndicator]:
        """根据股票代码查询"""
        return (
            db.query(models.StockFinancialIndicator)
            .filter(models.StockFinancialIndicator.symbol == symbol)
            .first()
        )

    def get_list(
        self,
        db: Session,
        query: schemas.StockFinancialIndicatorQuery,
    ) -> tuple[List[models.StockFinancialIndicator], int]:
        """分页查询，支持指标范围过滤"""
        from sqlalchemy import distinct

        # JOIN stock_basic 以支持 industry / market 过滤
        stmt = db.query(models.StockFinancialIndicator, models.StockBasic).join(
            models.StockBasic,
            models.StockFinancialIndicator.symbol == models.StockBasic.symbol,
            isouter=True,
        )

        filters = []
        if query.symbol:
            filters.append(models.StockFinancialIndicator.symbol.like(f"%{query.symbol}%"))
        if query.name:
            filters.append(models.StockFinancialIndicator.name.like(f"%{query.name}%"))
        if query.industry:
            filters.append(models.StockBasic.industry == query.industry)
        if query.market:
            filters.append(models.StockBasic.market == query.market)

        # 指标范围过滤
        field_map = {
            "roe": models.StockFinancialIndicator.roe,
            "gross_profit_ratio": models.StockFinancialIndicator.gross_profit_ratio,
            "net_profit_ratio": models.StockFinancialIndicator.net_profit_ratio,
            "net_profit_yoy": models.StockFinancialIndicator.net_profit_yoy,
            "revenue_yoy": models.StockFinancialIndicator.revenue_yoy,
            "debt_ratio": models.StockFinancialIndicator.debt_ratio,
        }
        range_filters = {
            "roe": (query.roe_min, query.roe_max),
            "gross_profit_ratio": (query.gross_profit_ratio_min, query.gross_profit_ratio_max),
            "net_profit_ratio": (query.net_profit_ratio_min, query.net_profit_ratio_max),
            "net_profit_yoy": (query.net_profit_yoy_min, query.net_profit_yoy_max),
            "revenue_yoy": (query.revenue_yoy_min, query.revenue_yoy_max),
            "debt_ratio": (query.debt_ratio_min, query.debt_ratio_max),
        }
        for field, (min_val, max_val) in range_filters.items():
            col = field_map[field]
            if min_val is not None:
                filters.append(col >= min_val)
            if max_val is not None:
                filters.append(col <= max_val)

        if filters:
            stmt = stmt.filter(and_(*filters))

        # 排序
        sort_col = field_map.get(query.sort_field, models.StockFinancialIndicator.roe)
        if query.sort_order == "asc":
            stmt = stmt.order_by(sort_col.asc())
        else:
            stmt = stmt.order_by(sort_col.desc())

        total = stmt.with_entities(func.count(distinct(models.StockFinancialIndicator.symbol))).scalar()

        results = (
            stmt.offset((query.page_num - 1) * query.page_size)
            .limit(query.page_size)
            .all()
        )

        list_data = []
        for fin, basic in results:
            fin.industry = basic.industry if basic else None
            fin.market = basic.market if basic else None
            list_data.append(fin)

        return list_data, total

    def create(self, db: Session, obj_in: schemas.StockFinancialIndicatorCreate) -> models.StockFinancialIndicator:
        """创建"""
        db_obj = models.StockFinancialIndicator(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def upsert(self, db: Session, obj_in: schemas.StockFinancialIndicatorCreate) -> models.StockFinancialIndicator:
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

    def upsert_batch(self, db: Session, obj_list: list[schemas.StockFinancialIndicatorCreate]) -> dict:
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
                db_obj = models.StockFinancialIndicator(**obj.model_dump())
                db.add(db_obj)
                created += 1
        db.commit()
        return {"created": created, "updated": updated}


stock_financial_indicator_crud = StockFinancialIndicatorCRUD()


# ==================== 同步任务日志 ====================


class SyncJobLogCRUD:
    """同步任务日志 CRUD"""

    def create(self, db: Session, obj_in: schemas.SyncJobLogCreate) -> models.SyncJobLog:
        db_obj = models.SyncJobLog(
            job_type=obj_in.job_type,
            trigger_type=obj_in.trigger_type,
            status='running',
            trade_date=obj_in.trade_date,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_id(self, db: Session, id: int) -> Optional[models.SyncJobLog]:
        return db.query(models.SyncJobLog).filter(models.SyncJobLog.id == id).first()

    def get_list(
        self,
        db: Session,
        query: schemas.SyncJobLogQuery,
    ) -> tuple[List[models.SyncJobLog], int]:
        from datetime import timedelta
        from sqlalchemy import and_

        filters = []
        if query.job_type:
            filters.append(models.SyncJobLog.job_type == query.job_type)
        if query.status:
            filters.append(models.SyncJobLog.status == query.status)
        if query.trigger_type:
            filters.append(models.SyncJobLog.trigger_type == query.trigger_type)
        if query.days:
            cutoff = datetime.now() - timedelta(days=query.days)
            filters.append(models.SyncJobLog.started_at >= cutoff)

        total = db.query(func.count(models.SyncJobLog.id))
        if filters:
            total = total.filter(and_(*filters))
        total = total.scalar()

        stmt = db.query(models.SyncJobLog)
        if filters:
            stmt = stmt.filter(and_(*filters))
        stmt = stmt.order_by(models.SyncJobLog.started_at.desc()).offset(
            (query.page_num - 1) * query.page_size
        ).limit(query.page_size)
        return stmt.all(), total

    def update(self, db: Session, obj_in: schemas.SyncJobLogUpdate) -> Optional[models.SyncJobLog]:
        db_obj = self.get_by_id(db, obj_in.id)
        if not db_obj:
            return None
        update_data = obj_in.model_dump(exclude={'id'}, exclude_none=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def finish(
        self,
        db: Session,
        log_id: int,
        status: str,
        success_count: int = 0,
        failed_count: int = 0,
        skipped_count: int = 0,
        total_count: int = 0,
        trade_date: Optional[str] = None,
        error_message: Optional[str] = None,
        extra_info: Optional[str] = None,
    ) -> Optional[models.SyncJobLog]:
        db_obj = self.get_by_id(db, log_id)
        if not db_obj:
            return None
        db_obj.status = status
        db_obj.ended_at = datetime.now()
        if db_obj.started_at:
            db_obj.duration_seconds = int((db_obj.ended_at - db_obj.started_at).total_seconds())
        db_obj.success_count = success_count
        db_obj.failed_count = failed_count
        db_obj.skipped_count = skipped_count
        db_obj.total_count = total_count
        if trade_date is not None:
            db_obj.trade_date = trade_date
        if error_message is not None:
            db_obj.error_message = error_message
        if extra_info is not None:
            db_obj.extra_info = extra_info
        db.commit()
        db.refresh(db_obj)
        return db_obj


sync_job_log_crud = SyncJobLogCRUD()