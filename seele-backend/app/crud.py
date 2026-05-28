"""
数据库CRUD操作模块
"""

from typing import List, Optional
from datetime import date, datetime
from collections import defaultdict
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, load_only

from app import models, schemas
from app.services import mainwave_scorer


# ==================== 持仓查询辅助 ====================

def _get_holding_symbols(db: Session) -> set:
    """获取当前持仓的所有股票代码集合"""
    rows = db.query(models.PortfolioPosition.symbol).all()
    return {r[0] for r in rows}


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

        # stock_basic 去重子查询（按 symbol 取最大 id，保留最新记录）
        subq = db.query(
            models.StockBasic.symbol,
            func.max(models.StockBasic.id).label('max_id')
        ).group_by(models.StockBasic.symbol)
        if filters:
            subq = subq.filter(and_(*filters))
        subq = subq.subquery()

        # 从去重后的 stock_basic 出发 JOIN 财务指标表
        stmt = db.query(models.StockBasic, models.StockFinancialIndicator).join(
            subq, models.StockBasic.id == subq.c.max_id
        ).outerjoin(
            models.StockFinancialIndicator,
            models.StockBasic.symbol == models.StockFinancialIndicator.symbol,
        )

        # 查询总数
        total = db.query(func.count(subq.c.max_id)).scalar()

        # 查询列表
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
                latest_date = trade_calendar_crud.get_latest(db)
                if latest_date:
                    trade_date = str(latest_date)
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
        holding_symbols = _get_holding_symbols(db)

        def _build_base_query():
            """构建基础查询（含所有 JOIN 和 trade_date 过滤）"""
            return (
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
                    models.StockDailyIndicator.chg_5d,
                    models.StockDailyIndicator.chg_10d,
                    models.StockDailyIndicator.adx,
                    models.StockFinancialIndicator.net_profit,
                    models.StockFinancialIndicator.net_profit_yoy,
                    models.StockFinancialIndicator.roe,
                )
                .join(models.StockBasic, models.StockDaily.symbol == models.StockBasic.symbol)
                .outerjoin(
                    models.StockDailyIndicator,
                    and_(
                        models.StockDaily.symbol == models.StockDailyIndicator.symbol,
                        models.StockDaily.trade_date == models.StockDailyIndicator.trade_date,
                    ),
                )
                .outerjoin(
                    models.StockFinancialIndicator,
                    models.StockDaily.symbol == models.StockFinancialIndicator.symbol,
                )
                .filter(models.StockDaily.trade_date == formatted_date)
                .options(load_only(
                    models.StockDaily.id,
                    models.StockDaily.trade_date,
                    models.StockDaily.symbol,
                    models.StockDaily.open,
                    models.StockDaily.high,
                    models.StockDaily.low,
                    models.StockDaily.close,
                    models.StockDaily.volume,
                    models.StockDaily.amount,
                    models.StockDaily.amplitude,
                    models.StockDaily.pct_chg,
                    models.StockDaily.price_change,
                    models.StockDaily.turnover,
                ))
            )

        def _apply_text_filters(q):
            """应用文本筛选条件"""
            if query.symbol and query.name:
                return q.filter(
                    or_(
                        models.StockBasic.symbol.like(f"%{query.symbol}%"),
                        models.StockBasic.name.like(f"%{query.name}%"),
                    )
                )
            if query.symbol:
                q = q.filter(models.StockBasic.symbol.like(f"%{query.symbol}%"))
            if query.name:
                q = q.filter(models.StockBasic.name.like(f"%{query.name}%"))
            return q

        def _apply_picker_filters(q):
            """应用选股特有的硬性门槛（不包含 trade_date）"""
            q = q.filter(
                models.StockBasic.market == "主板",
                models.StockBasic.name.notlike("%ST%"),
                models.StockBasic.symbol.notlike("300%"),
                models.StockBasic.symbol.notlike("301%"),
                models.StockBasic.symbol.notlike("688%"),
                models.StockBasic.symbol.notlike("689%"),
            )
            # 市值过滤已移除：float_market_cap 数据缺失且换手率+成交额过滤已足够
            if query.close_max is not None:
                q = q.filter(models.StockDaily.close <= query.close_max)
            if query.avg_turnover_min is not None:
                q = q.filter(models.StockDailyIndicator.turnover_ma10 >= query.avg_turnover_min)
            # 前端传入单位为亿元，数据库 amount_ma10 单位为元，需转换
            if query.avg_amount_min is not None:
                q = q.filter(models.StockDailyIndicator.amount_ma10 >= query.avg_amount_min * 1e8)
            if query.ma_bull:
                q = q.filter(
                    models.StockDaily.close > models.StockDailyIndicator.ma5,
                    models.StockDailyIndicator.ma5 > models.StockDailyIndicator.ma10,
                    models.StockDailyIndicator.ma10 > models.StockDailyIndicator.ma20,
                    models.StockDailyIndicator.ma20 > models.StockDailyIndicator.ma30,
                    models.StockDailyIndicator.ma30 > models.StockDailyIndicator.ma60,
                )
            # 财务数据过滤：允许缺失（NULL），有数据则要求盈利
            q = q.filter(
                or_(
                    models.StockFinancialIndicator.net_profit.is_(None),
                    models.StockFinancialIndicator.net_profit > 0,
                ),
                or_(
                    models.StockFinancialIndicator.total_revenue.is_(None),
                    models.StockFinancialIndicator.total_revenue > 0,
                ),
            )
            # MA5偏离不再在SQL层硬性过滤，由Python评分层处理
            # 保留ma5非空检查以确保指标数据存在
            q = q.filter(
                models.StockDailyIndicator.ma5.isnot(None),
                models.StockDailyIndicator.ma5 > 0,
            )
            return q

        # 1. 选股结果（带所有选股条件）
        picker_q = _apply_picker_filters(_apply_text_filters(_build_base_query()))
        picker_results = picker_q.all()
        picker_symbols = {row[0].symbol for row in picker_results}

        # 2. 补充持仓股（不满足选股条件但用户持有）
        missing_symbols = holding_symbols - picker_symbols
        holding_results = []
        if missing_symbols:
            holding_q = _apply_text_filters(_build_base_query())
            holding_q = holding_q.filter(models.StockDaily.symbol.in_(list(missing_symbols)))
            holding_results = holding_q.all()

        all_results = picker_results + holding_results

        def _build_item(row):
            """将查询结果行组装为字典"""
            (
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
                chg_5d,
                chg_10d,
                adx,
                net_profit,
                net_profit_yoy,
                roe,
            ) = row
            return {
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
                "chg_5d": chg_5d,
                "chg_10d": chg_10d,
                "adx": adx,
                "net_profit": net_profit,
                "net_profit_yoy": net_profit_yoy,
                "roe": roe,
                "is_holding": daily.symbol in holding_symbols,
            }

        all_data = [_build_item(row) for row in all_results]
        mainwave_scorer.batch_calculate_scores(db, all_data, trade_date)

        # 统一内存排序
        sort_key_map = {
            "symbol": lambda x: x.get("symbol", ""),
            "stock_name": lambda x: x.get("stock_name", ""),
            "name": lambda x: x.get("name", ""),
            "open": lambda x: x.get("open") or 0,
            "high": lambda x: x.get("high") or 0,
            "low": lambda x: x.get("low") or 0,
            "close": lambda x: x.get("close") or 0,
            "volume": lambda x: x.get("volume") or 0,
            "amount": lambda x: x.get("amount") or 0,
            "amplitude": lambda x: x.get("amplitude") or 0,
            "pct_chg": lambda x: x.get("pct_chg") or 0,
            "pctChg": lambda x: x.get("pct_chg") or 0,
            "price_change": lambda x: x.get("price_change") or 0,
            "priceChange": lambda x: x.get("price_change") or 0,
            "turnover": lambda x: x.get("turnover") or 0,
            "ma5": lambda x: x.get("ma5") or 0,
            "ma10": lambda x: x.get("ma10") or 0,
            "ma20": lambda x: x.get("ma20") or 0,
            "ma30": lambda x: x.get("ma30") or 0,
            "ma60": lambda x: x.get("ma60") or 0,
            "vol_ma5": lambda x: x.get("vol_ma5") or 0,
            "volMa5": lambda x: x.get("vol_ma5") or 0,
            "vol_ma10": lambda x: x.get("vol_ma10") or 0,
            "volMa10": lambda x: x.get("vol_ma10") or 0,
            "turnover_ma5": lambda x: x.get("turnover_ma5") or 0,
            "turnoverMa5": lambda x: x.get("turnover_ma5") or 0,
            "turnover_ma10": lambda x: x.get("turnover_ma10") or 0,
            "turnoverMa10": lambda x: x.get("turnover_ma10") or 0,
            "float_market_cap": lambda x: x.get("float_market_cap") or 0,
            "score": lambda x: x.get("score", {}).get("total", 0),
        }
        sort_key = sort_key_map.get(query.sort_field, sort_key_map["symbol"])
        reverse = query.sort_order == "desc"
        all_data.sort(key=sort_key, reverse=reverse)

        total = len(all_data)
        start = (query.page_num - 1) * query.page_size
        end = start + query.page_size
        data_list = all_data[start:end]

        return data_list, total, trade_date

    def get_batch(self, db: Session, symbols: List[str]) -> List[models.StockBasic]:
        """批量查询"""
        return db.query(models.StockBasic).filter(models.StockBasic.symbol.in_(symbols)).all()

    def create(self, db: Session, obj_in: schemas.StockBasicCreate) -> models.StockBasic:
        """创建（不自动 commit，由调用方统一提交）"""
        db_obj = models.StockBasic(**obj_in.model_dump())
        db.add(db_obj)
        return db_obj

    def update(self, db: Session, obj_in: schemas.StockBasicUpdate) -> Optional[models.StockBasic]:
        """更新（不自动 commit，由调用方统一提交）"""
        db_obj = self.get_by_id(db, obj_in.id)
        if db_obj:
            update_data = obj_in.model_dump(exclude={"id"})
            for key, value in update_data.items():
                if value is not None:
                    setattr(db_obj, key, value)
        return db_obj

    def upsert(self, db: Session, obj_in: schemas.StockBasicCreate) -> models.StockBasic:
        """存在则更新，不存在则插入（不自动 commit，由调用方统一提交）"""
        existing = self.get_by_symbol(db, obj_in.symbol)
        if existing:
            update_data = obj_in.model_dump(exclude={"symbol"})
            for key, value in update_data.items():
                if value is not None:
                    setattr(existing, key, value)
            return existing
        else:
            return self.create(db, obj_in)

    def upsert_batch(self, db: Session, obj_list: list[schemas.StockBasicCreate]) -> dict:
        """批量 upsert（使用 INSERT ... ON DUPLICATE KEY UPDATE，不自动 commit）"""
        if not obj_list:
            return {"success": 0, "failed": 0}

        from sqlalchemy.dialects.mysql import insert

        records = [obj.model_dump() for obj in obj_list]
        total = len(records)
        success = 0
        failed = 0
        batch_size = 500

        for i in range(0, total, batch_size):
            chunk = records[i:i + batch_size]
            try:
                upsert_stmt = insert(models.StockBasic).values(chunk)
                update_dict = {
                    k: upsert_stmt.inserted[k]
                    for k in upsert_stmt.inserted.keys()
                    if k not in ("id", "symbol")
                }
                upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
                db.execute(upsert_stmt)
                success += len(chunk)
            except Exception as exc:
                import logging, traceback
                logging.getLogger(__name__).error(
                    '[STOCK_BASIC_BATCH] 批量写入失败 (batch %d-%d): %s', i, i + len(chunk), exc
                )
                logging.getLogger(__name__).error(traceback.format_exc())
                db.rollback()
                failed += len(chunk)

        return {"success": success, "failed": failed}

    def delete(self, db: Session, id: int) -> bool:
        """删除（不自动 commit，由调用方统一提交）"""
        db_obj = self.get_by_id(db, id)
        if db_obj:
            db.delete(db_obj)
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


    def get_batch(self, db: Session, symbols: List[str]) -> List[models.StockDaily]:
        """批量查询"""
        return db.query(models.StockDaily).filter(models.StockDaily.symbol.in_(symbols)).all()

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
        """创建（不自动 commit，由调用方统一提交）"""
        data = self._fill_calculated_fields(db, obj_in.model_dump())
        db_obj = models.StockDaily(**data)
        db.add(db_obj)
        return db_obj

    def create_batch(self, db: Session, obj_list: List[schemas.StockDailyCreate]) -> int:
        """批量创建（不自动 commit，由调用方统一提交）"""
        db_objs = []
        for obj in obj_list:
            data = self._fill_calculated_fields(db, obj.model_dump())
            db_objs.append(models.StockDaily(**data))
        db.add_all(db_objs)
        return len(db_objs)

    def upsert(self, db: Session, obj_in: schemas.StockDailyCreate) -> models.StockDaily:
        """存在则更新，不存在则插入（不自动 commit，由调用方统一提交）"""
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
            return existing
        else:
            data = self._fill_calculated_fields(db, obj_in.model_dump())
            db_obj = models.StockDaily(**data)
            db.add(db_obj)
            return db_obj

    def update(self, db: Session, obj_in: schemas.StockDailyUpdate) -> Optional[models.StockDaily]:
        """更新（不自动 commit，由调用方统一提交）"""
        db_obj = self.get_by_id(db, obj_in.id)
        if db_obj:
            update_data = obj_in.model_dump(exclude={"id"})
            for key, value in update_data.items():
                if value is not None:
                    setattr(db_obj, key, value)
        return db_obj

    def delete(self, db: Session, id: int) -> bool:
        """删除（不自动 commit，由调用方统一提交）"""
        db_obj = self.get_by_id(db, id)
        if db_obj:
            db.delete(db_obj)
            return True
        return False

    def get_trade_dates(self, db: Session) -> list:
        """获取所有交易日期列表（升序）"""
        rows = (
            db.query(models.StockDaily.trade_date)
            .distinct()
            .order_by(models.StockDaily.trade_date.asc())
            .all()
        )
        return [r[0] for r in rows]


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
        """存在则更新，不存在则插入（不自动 commit，由调用方统一提交）"""
        existing = self.get_by_symbol_date(db, symbol, trade_date)
        if existing:
            for key, value in indicator_data.items():
                if value is not None:
                    setattr(existing, key, value)
            return existing
        else:
            db_obj = models.StockDailyIndicator(
                symbol=symbol,
                trade_date=trade_date,
                **indicator_data
            )
            db.add(db_obj)
            return db_obj

    def create_or_update_batch(
        self, db: Session, items: List[dict], batch_size: int = 500
    ) -> dict:
        """批量创建或更新（使用 INSERT ... ON DUPLICATE KEY UPDATE，不自动 commit）"""
        if not items:
            return {"success": 0, "failed": 0}

        from sqlalchemy.dialects.mysql import insert

        records = []
        for item in items:
            record = dict(item)
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
                success += len(chunk)
            except Exception as exc:
                import logging, traceback
                logging.getLogger(__name__).error(
                    '[INDICATOR_BATCH] 批量写入失败 (batch %d-%d): %s', i, i + len(chunk), exc
                )
                logging.getLogger(__name__).error(traceback.format_exc())
                try:
                    db_err = SessionLocal()
                    crud.system_error_log_crud.create(
                        db_err,
                        schemas.SystemErrorLogCreate(
                            level='error', source='indicator_batch', trace_id=None,
                            message=f'批量写入失败 (batch {i}-{i + len(chunk)}): {exc}'[:1000],
                            detail=traceback.format_exc()[:4000],
                        )
                    )
                    db_err.commit()
                    db_err.close()
                except Exception as exc:
                    logger.warning('[CRUD] 写入 system_error_log 失败: %s', exc)
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
            .order_by(models.PortfolioTrade.trade_date.asc(), models.PortfolioTrade.id.asc())
            .all()
        )

    def create(self, db: Session, obj_in: schemas.PortfolioTradeCreate) -> models.PortfolioTrade:
        """创建交易记录（不自动 commit，由调用方统一提交）"""
        data = obj_in.model_dump()
        if data.get('amount') is None and data.get('price') and data.get('quantity'):
            data['amount'] = round(data['price'] * data['quantity'], 4)
        db_obj = models.PortfolioTrade(**data)
        db.add(db_obj)
        return db_obj

    def update(self, db: Session, id: int, data: dict) -> Optional[models.PortfolioTrade]:
        """更新交易记录（不自动 commit，由调用方统一提交）"""
        db_obj = self.get_by_id(db, id)
        if not db_obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(db_obj, k, v)
        return db_obj

    def delete(self, db: Session, id: int) -> bool:
        """删除交易记录（不自动 commit，由调用方统一提交）"""
        db_obj = self.get_by_id(db, id)
        if db_obj:
            db.delete(db_obj)
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
        """创建清仓记录（不自动 commit，由调用方统一提交）"""
        db_obj = models.PortfolioClosed(**data)
        db.add(db_obj)
        return db_obj

    def delete_by_symbol(self, db: Session, symbol: str) -> bool:
        """根据股票代码删除清仓记录（不自动 commit，由调用方统一提交）"""
        db.query(models.PortfolioClosed).filter(models.PortfolioClosed.symbol == symbol).delete()
        return True

    def delete_all(self, db: Session) -> bool:
        """清空全部清仓记录（调用方需在同一事务中统一 commit）"""
        db.query(models.PortfolioClosed).delete()
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
        """批量插入（调用方需先清空表，并在同一事务中统一 commit）"""
        db_objs = [models.PortfolioDailyPosition(**item) for item in items]
        db.add_all(db_objs)
        return len(db_objs)

    def delete_all(self, db: Session) -> bool:
        """清空全部记录（调用方需在同一事务中统一 commit）"""
        db.query(models.PortfolioDailyPosition).delete()
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
        """批量插入（调用方需先清空表，并在同一事务中统一 commit）"""
        db_objs = [models.PortfolioDailySummary(**item) for item in items]
        db.add_all(db_objs)
        return len(db_objs)

    def delete_all(self, db: Session) -> bool:
        """清空全部记录（调用方需在同一事务中统一 commit）"""
        db.query(models.PortfolioDailySummary).delete()
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
        """更新或插入持仓快照（不自动 commit，由调用方统一提交）"""
        symbol = data['symbol']
        group = data.get('group', 'default')
        db_obj = self.get_by_symbol(db, symbol, group)
        if db_obj:
            for key, value in data.items():
                setattr(db_obj, key, value)
        else:
            db_obj = models.PortfolioPosition(**data)
            db.add(db_obj)
        db.flush()
        return db_obj

    def upsert_batch(self, db: Session, items: List[dict]) -> None:
        """批量 upsert 持仓快照（不自动 commit，由调用方统一提交）"""
        if not items:
            return
        symbols = [d['symbol'] for d in items]
        existing = {
            r.symbol: r
            for r in db.query(models.PortfolioPosition)
            .filter(models.PortfolioPosition.symbol.in_(symbols))
            .all()
        }
        for data in items:
            symbol = data['symbol']
            db_obj = existing.get(symbol)
            if db_obj:
                for key, value in data.items():
                    setattr(db_obj, key, value)
            else:
                db.add(models.PortfolioPosition(**data))
        db.flush()

    def delete_by_symbol(self, db: Session, symbol: str, group: str = None) -> bool:
        """根据股票代码删除持仓快照（group 为 None 时不限分组，不自动 commit）"""
        query = db.query(models.PortfolioPosition).filter(models.PortfolioPosition.symbol == symbol)
        if group:
            query = query.filter(models.PortfolioPosition.group == group)
        query.delete()
        return True

    def delete_all(self, db: Session) -> int:
        """清空所有持仓快照（不自动 commit，由调用方统一提交）"""
        return db.query(models.PortfolioPosition).delete()

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
        """标记预警已触发（不自动 commit，由调用方统一提交）"""
        db_obj = db.query(models.PortfolioPosition).filter(models.PortfolioPosition.id == id).first()
        if db_obj:
            db_obj.alert_triggered = 1
            return True
        return False


portfolio_position_crud = PortfolioPositionCRUD()


# ==================== 持仓配置 ====================


class PortfolioConfigCRUD:
    """持仓配置 CRUD"""

    def get_or_create(self, db: Session) -> models.PortfolioConfig:
        """获取配置，不存在则创建默认值（不自动 commit，由调用方统一提交）"""
        config = db.query(models.PortfolioConfig).first()
        if not config:
            config = models.PortfolioConfig(initial_capital=35000.0)
            db.add(config)
        return config

    def update(self, db: Session, initial_capital: float) -> models.PortfolioConfig:
        """更新初始资金（不自动 commit，由调用方统一提交）"""
        config = self.get_or_create(db)
        config.initial_capital = initial_capital
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
        stmt = db.query(models.StockFinancialIndicator, models.StockBasic).outerjoin(
            models.StockBasic,
            models.StockFinancialIndicator.symbol == models.StockBasic.symbol
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
        """创建（不自动 commit，由调用方统一提交）"""
        db_obj = models.StockFinancialIndicator(**obj_in.model_dump())
        db.add(db_obj)
        return db_obj

    def upsert(self, db: Session, obj_in: schemas.StockFinancialIndicatorCreate) -> models.StockFinancialIndicator:
        """存在则更新，不存在则插入（不自动 commit，由调用方统一提交）"""
        existing = self.get_by_symbol(db, obj_in.symbol)
        if existing:
            update_data = obj_in.model_dump(exclude={"symbol"})
            for key, value in update_data.items():
                if value is not None:
                    setattr(existing, key, value)
            return existing
        else:
            return self.create(db, obj_in)

    def upsert_batch(self, db: Session, obj_list: list[schemas.StockFinancialIndicatorCreate]) -> dict:
        """批量 upsert（使用 INSERT ... ON DUPLICATE KEY UPDATE，不自动 commit）"""
        if not obj_list:
            return {"success": 0, "failed": 0}

        from sqlalchemy.dialects.mysql import insert

        records = [obj.model_dump() for obj in obj_list]
        total = len(records)
        success = 0
        failed = 0
        batch_size = 500

        for i in range(0, total, batch_size):
            chunk = records[i:i + batch_size]
            try:
                upsert_stmt = insert(models.StockFinancialIndicator).values(chunk)
                update_dict = {
                    k: upsert_stmt.inserted[k]
                    for k in upsert_stmt.inserted.keys()
                    if k not in ("id", "symbol")
                }
                upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
                db.execute(upsert_stmt)
                success += len(chunk)
            except Exception as exc:
                import logging, traceback
                logging.getLogger(__name__).error(
                    '[FINANCIAL_INDICATOR_BATCH] 批量写入失败 (batch %d-%d): %s', i, i + len(chunk), exc
                )
                logging.getLogger(__name__).error(traceback.format_exc())
                db.rollback()
                failed += len(chunk)

        return {"success": success, "failed": failed}


stock_financial_indicator_crud = StockFinancialIndicatorCRUD()


# ==================== 同步任务日志 ====================


class SyncJobLogCRUD:
    """同步任务日志 CRUD"""

    def create(self, db: Session, obj_in: schemas.SyncJobLogCreate) -> models.SyncJobLog:
        """创建同步任务日志（不自动 commit，由调用方统一提交）"""
        db_obj = models.SyncJobLog(
            job_type=obj_in.job_type,
            trigger_type=obj_in.trigger_type,
            status='running',
            trade_date=obj_in.trade_date,
        )
        db.add(db_obj)
        db.flush()
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
        """更新同步任务日志状态（不自动 commit，由调用方统一提交）"""
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
        return db_obj


sync_job_log_crud = SyncJobLogCRUD()


# ==================== 系统日志 ====================


class SystemErrorLogCRUD:
    """系统错误日志 CRUD"""

    def create(self, db: Session, obj_in: schemas.SystemErrorLogCreate) -> models.SystemErrorLog:
        """创建系统错误日志（不自动 commit，由调用方统一提交）"""
        db_obj = models.SystemErrorLog(
            level=obj_in.level,
            source=obj_in.source,
            trace_id=obj_in.trace_id,
            message=obj_in.message,
            detail=obj_in.detail,
        )
        db.add(db_obj)
        return db_obj

    def get_list(
        self,
        db: Session,
        query: schemas.SystemErrorLogQuery,
    ) -> tuple[List[models.SystemErrorLog], int]:
        from datetime import timedelta

        filters = []
        if query.level:
            filters.append(models.SystemErrorLog.level == query.level)
        if query.source:
            filters.append(models.SystemErrorLog.source == query.source)
        if query.days:
            cutoff = datetime.now() - timedelta(days=query.days)
            filters.append(models.SystemErrorLog.created_at >= cutoff)

        total = db.query(func.count(models.SystemErrorLog.id))
        if filters:
            total = total.filter(and_(*filters))
        total = total.scalar()

        stmt = db.query(models.SystemErrorLog)
        if filters:
            stmt = stmt.filter(and_(*filters))
        stmt = stmt.order_by(models.SystemErrorLog.created_at.desc()).offset(
            (query.page_num - 1) * query.page_size
        ).limit(query.page_size)
        return stmt.all(), total


class SystemOperationLogCRUD:
    """系统操作日志 CRUD"""

    def create(self, db: Session, obj_in: schemas.SystemOperationLogCreate) -> models.SystemOperationLog:
        """创建系统操作日志（不自动 commit，由调用方统一提交）"""
        db_obj = models.SystemOperationLog(
            operation_type=obj_in.operation_type,
            operator=obj_in.operator,
            target_type=obj_in.target_type,
            target_id=obj_in.target_id,
            detail=obj_in.detail,
            result=obj_in.result,
        )
        db.add(db_obj)
        return db_obj

    def get_list(
        self,
        db: Session,
        query: schemas.SystemOperationLogQuery,
    ) -> tuple[List[models.SystemOperationLog], int]:
        from datetime import timedelta

        filters = []
        if query.operation_type:
            filters.append(models.SystemOperationLog.operation_type == query.operation_type)
        if query.days:
            cutoff = datetime.now() - timedelta(days=query.days)
            filters.append(models.SystemOperationLog.created_at >= cutoff)

        total = db.query(func.count(models.SystemOperationLog.id))
        if filters:
            total = total.filter(and_(*filters))
        total = total.scalar()

        stmt = db.query(models.SystemOperationLog)
        if filters:
            stmt = stmt.filter(and_(*filters))
        stmt = stmt.order_by(models.SystemOperationLog.created_at.desc()).offset(
            (query.page_num - 1) * query.page_size
        ).limit(query.page_size)
        return stmt.all(), total


system_error_log_crud = SystemErrorLogCRUD()
system_operation_log_crud = SystemOperationLogCRUD()


# ==================== 股票停牌信息 ====================


class StockSuspensionCRUD:
    """股票停牌信息CRUD"""

    def create(self, db: Session, obj_in: schemas.StockSuspensionCreate) -> models.StockSuspension:
        """创建停牌记录（不自动 commit，由调用方统一提交）"""
        db_obj = models.StockSuspension(
            symbol=obj_in.symbol,
            name=obj_in.name,
            suspend_date=obj_in.suspend_date,
            resume_date=obj_in.resume_date,
            reason=obj_in.reason,
        )
        db.add(db_obj)
        return db_obj

    def get_by_symbol_and_date(self, db: Session, symbol: str, suspend_date: date) -> Optional[models.StockSuspension]:
        """根据股票代码和停牌日期查询"""
        return db.query(models.StockSuspension).filter(
            models.StockSuspension.symbol == symbol,
            models.StockSuspension.suspend_date == suspend_date,
        ).first()

    def get_active_suspensions(self, db: Session, trade_date: date) -> List[models.StockSuspension]:
        """获取指定日期仍在停牌中的记录（suspend_date <= trade_date 且 resume_date 为空或 > trade_date）"""
        return db.query(models.StockSuspension).filter(
            models.StockSuspension.suspend_date <= trade_date,
            or_(
                models.StockSuspension.resume_date.is_(None),
                models.StockSuspension.resume_date > trade_date,
            ),
        ).all()

    def get_active_symbols(self, db: Session, trade_date: date) -> List[str]:
        """获取指定日期仍在停牌中的股票代码列表"""
        rows = db.query(models.StockSuspension.symbol).filter(
            models.StockSuspension.suspend_date <= trade_date,
            or_(
                models.StockSuspension.resume_date.is_(None),
                models.StockSuspension.resume_date > trade_date,
            ),
        ).distinct().all()
        return [r[0] for r in rows]

    def upsert(self, db: Session, obj_in: schemas.StockSuspensionCreate) -> models.StockSuspension:
        """存在则更新，不存在则创建（不自动 commit，由调用方统一提交）"""
        existing = self.get_by_symbol_and_date(db, obj_in.symbol, obj_in.suspend_date)
        if existing:
            existing.name = obj_in.name or existing.name
            existing.resume_date = obj_in.resume_date or existing.resume_date
            existing.reason = obj_in.reason or existing.reason
            return existing
        return self.create(db, obj_in)

    def upsert_batch(self, db: Session, items: List[schemas.StockSuspensionCreate]) -> dict:
        """批量 upsert 停牌记录（不自动 commit，由调用方统一提交）"""
        if not items:
            return {'success': 0, 'failed': 0}
        from sqlalchemy.dialects.mysql import insert
        stmt = insert(models.StockSuspension).values([
            {
                'symbol': item.symbol,
                'name': item.name,
                'suspend_date': item.suspend_date,
                'resume_date': item.resume_date,
                'reason': item.reason,
            }
            for item in items
        ])
        upsert_stmt = stmt.on_duplicate_key_update(
            name=stmt.inserted.name,
            resume_date=stmt.inserted.resume_date,
            reason=stmt.inserted.reason,
        )
        try:
            db.execute(upsert_stmt)
            return {'success': len(items), 'failed': 0}
        except Exception as exc:
            logger.error('[CRUD] 批量 upsert 停牌记录失败: %s', exc)
            db_err = SessionLocal()
            try:
                db_err.add(models.SystemErrorLog(
                    level='error', source='suspension_upsert_batch', trace_id=None,
                    message=f'批量 upsert 停牌记录失败: {exc}'[:1000],
                    detail=traceback.format_exc()[:4000],
                ))
                db_err.commit()
            except Exception as err_exc:
                logger.warning('[CRUD] 写入 system_error_log 失败: %s', err_exc)
            finally:
                db_err.close()
            return {'success': 0, 'failed': len(items)}

    def delete_all(self, db: Session) -> int:
        """清空所有停牌记录（不自动 commit，由调用方统一提交）"""
        count = db.query(models.StockSuspension).delete()
        return count


stock_suspension_crud = StockSuspensionCRUD()


# ==================== 板块/ETF信息 ====================


class BoardInfoCRUD:
    """板块/ETF信息 CRUD"""

    def get_by_code(self, db: Session, code: str) -> Optional[models.BoardInfo]:
        """根据代码查询"""
        return db.query(models.BoardInfo).filter(models.BoardInfo.code == code).first()

    def get_list(
        self,
        db: Session,
        query: schemas.BoardInfoQuery,
    ) -> tuple[List[dict], int]:
        """分页查询，支持 category 过滤和名称模糊搜索

        返回每个板块的最新涨幅、5日涨幅、10日涨幅（基于 board_daily）。
        """
        stmt = db.query(models.BoardInfo)
        filters = []
        if query.category:
            filters.append(models.BoardInfo.category == query.category)
        if query.keyword:
            filters.append(models.BoardInfo.name.like(f'%{query.keyword}%'))
        if filters:
            stmt = stmt.filter(and_(*filters))

        total = stmt.with_entities(func.count(models.BoardInfo.code)).scalar() or 0
        board_list = (
            stmt.order_by(models.BoardInfo.category, models.BoardInfo.code)
            .offset((query.page_num - 1) * query.page_size)
            .limit(query.page_size)
            .all()
        )

        if not board_list:
            return [], total

        codes = [b.code for b in board_list]
        all_dailies = (
            db.query(models.BoardDaily)
            .filter(models.BoardDaily.code.in_(codes))
            .order_by(models.BoardDaily.code, models.BoardDaily.trade_date.desc())
            .all()
        )

        daily_by_code = defaultdict(list)
        for d in all_dailies:
            if len(daily_by_code[d.code]) < 10:
                daily_by_code[d.code].append(d)

        result = []
        for b in board_list:
            dailies = daily_by_code.get(b.code, [])
            latest = dailies[0] if dailies else None
            stats = {
                'latest_close': latest.close if latest else None,
                'latest_pct_chg': latest.pct_chg if latest else None,
                'latest_trade_date': str(latest.trade_date) if latest else None,
                'chg_5d': None,
                'chg_10d': None,
            }
            if len(dailies) >= 5 and dailies[4].close:
                stats['chg_5d'] = round(
                    (dailies[0].close - dailies[4].close) / dailies[4].close * 100, 2
                )
            if len(dailies) >= 10 and dailies[9].close:
                stats['chg_10d'] = round(
                    (dailies[0].close - dailies[9].close) / dailies[9].close * 100, 2
                )

            result.append({
                'code': b.code,
                'name': b.name,
                'category': b.category,
                'exchange': b.exchange,
                'source': b.source,
                **stats,
            })

        return result, total

    def get_by_category(self, db: Session, category: str) -> List[models.BoardInfo]:
        """根据类型查询全部"""
        return db.query(models.BoardInfo).filter(models.BoardInfo.category == category).all()

    def upsert_batch(self, db: Session, obj_list: List[schemas.BoardInfoCreate]) -> dict:
        """批量 upsert（以 code 为唯一键，不自动 commit，由调用方统一提交）"""
        created = 0
        updated = 0
        for obj in obj_list:
            existing = self.get_by_code(db, obj.code)
            if existing:
                update_data = obj.model_dump(exclude={'code'})
                for key, value in update_data.items():
                    if value is not None:
                        setattr(existing, key, value)
                updated += 1
            else:
                db_obj = models.BoardInfo(**obj.model_dump())
                db.add(db_obj)
                created += 1
        return {'created': created, 'updated': updated}


board_info_crud = BoardInfoCRUD()


# ==================== 板块/ETF成分股 ====================


class BoardConstituentCRUD:
    """板块/ETF成分股 CRUD"""

    def get_by_board(self, db: Session, board_code: str) -> List[models.BoardConstituent]:
        """根据板块代码查询成分股"""
        return (
            db.query(models.BoardConstituent)
            .filter(models.BoardConstituent.board_code == board_code)
            .all()
        )

    def get_boards_by_symbol(self, db: Session, symbol: str) -> List[models.BoardInfo]:
        """根据个股代码查询所属板块信息（JOIN board_info）"""
        return (
            db.query(models.BoardInfo)
            .join(
                models.BoardConstituent,
                models.BoardInfo.code == models.BoardConstituent.board_code,
            )
            .filter(models.BoardConstituent.constituent_symbol == symbol)
            .all()
        )

    def upsert_batch(self, db: Session, obj_list: List[schemas.BoardConstituentCreate]) -> dict:
        """批量 upsert（不自动 commit，由调用方统一提交）"""
        created = 0
        updated = 0
        for obj in obj_list:
            existing = (
                db.query(models.BoardConstituent)
                .filter(
                    and_(
                        models.BoardConstituent.board_code == obj.board_code,
                        models.BoardConstituent.constituent_symbol == obj.constituent_symbol,
                    )
                )
                .first()
            )
            if existing:
                if obj.update_date is not None:
                    existing.update_date = obj.update_date
                updated += 1
            else:
                db_obj = models.BoardConstituent(**obj.model_dump())
                db.add(db_obj)
                created += 1
        return {'created': created, 'updated': updated}

    def delete_by_board(self, db: Session, board_code: str) -> int:
        """删除指定板块的所有成分股（全量更新前清空，不自动 commit，由调用方统一提交）"""
        count = (
            db.query(models.BoardConstituent)
            .filter(models.BoardConstituent.board_code == board_code)
            .delete()
        )
        return count


board_constituent_crud = BoardConstituentCRUD()


# ==================== 板块/ETF日线 ====================


class BoardDailyCRUD:
    """板块/ETF日线 CRUD"""

    def get_by_code(
        self,
        db: Session,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_num: int = 1,
        page_size: int = 100,
    ) -> tuple[List[models.BoardDaily], int]:
        """根据代码查询日线，支持日期范围"""
        stmt = db.query(models.BoardDaily).filter(models.BoardDaily.code == code)
        if start_date:
            stmt = stmt.filter(models.BoardDaily.trade_date >= start_date)
        if end_date:
            stmt = stmt.filter(models.BoardDaily.trade_date <= end_date)

        total = stmt.with_entities(func.count(models.BoardDaily.id)).scalar() or 0
        list_data = (
            stmt.order_by(models.BoardDaily.trade_date.desc())
            .offset((page_num - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return list_data, total

    def get_by_date(self, db: Session, trade_date: str) -> List[models.BoardDaily]:
        """根据交易日期查询全部板块日线"""
        return (
            db.query(models.BoardDaily)
            .filter(models.BoardDaily.trade_date == trade_date)
            .all()
        )

    def get_latest_by_code(self, db: Session, code: str) -> Optional[models.BoardDaily]:
        """获取某板块最新一天的日线"""
        return (
            db.query(models.BoardDaily)
            .filter(models.BoardDaily.code == code)
            .order_by(models.BoardDaily.trade_date.desc())
            .first()
        )

    def upsert_batch(self, db: Session, records: List[dict], batch_size: int = 500) -> dict:
        """批量 upsert（INSERT ... ON DUPLICATE KEY UPDATE，不自动 commit，由调用方统一提交）"""
        if not records:
            return {'success': 0, 'failed': 0}

        from sqlalchemy.dialects.mysql import insert

        total = len(records)
        success = 0
        failed = 0

        for i in range(0, total, batch_size):
            chunk = records[i:i + batch_size]
            try:
                upsert_stmt = insert(models.BoardDaily).values(chunk)
                update_dict = {
                    k: upsert_stmt.inserted[k]
                    for k in upsert_stmt.inserted.keys()
                    if k not in ('id', 'trade_date', 'code')
                }
                upsert_stmt = upsert_stmt.on_duplicate_key_update(**update_dict)
                db.execute(upsert_stmt)
                success += len(chunk)
            except Exception as exc:
                import logging, traceback
                logging.getLogger(__name__).error(
                    '[BOARD_DAILY_BATCH] 批量写入失败 (batch %d-%d): %s', i, i + len(chunk), exc
                )
                logging.getLogger(__name__).error(traceback.format_exc())
                try:
                    db_err = SessionLocal()
                    crud.system_error_log_crud.create(
                        db_err,
                        schemas.SystemErrorLogCreate(
                            level='error', source='board_daily_batch', trace_id=None,
                            message=f'批量写入失败 (batch {i}-{i + len(chunk)}): {exc}'[:1000],
                            detail=traceback.format_exc()[:4000],
                        )
                    )
                    db_err.commit()
                    db_err.close()
                except Exception as exc:
                    logger.warning('[CRUD] 写入 system_error_log 失败: %s', exc)
                db.rollback()
                failed += len(chunk)

        return {'success': success, 'failed': failed}


board_daily_crud = BoardDailyCRUD()


# ==================== 交易日历 ====================


class TradeCalendarCRUD:
    """交易日历 CRUD"""

    def get_latest(self, db: Session) -> Optional[date]:
        """获取最近一个交易日（不超过今天）"""
        row = (
            db.query(models.TradeCalendar)
            .filter(
                models.TradeCalendar.is_trading_day == 1,
                models.TradeCalendar.trade_date <= date.today(),
            )
            .order_by(models.TradeCalendar.trade_date.desc())
            .first()
        )
        return row.trade_date if row else None

    def get_by_year(self, db: Session, year: int) -> List[models.TradeCalendar]:
        """获取某年的交易日历"""
        return (
            db.query(models.TradeCalendar)
            .filter(models.TradeCalendar.year == year)
            .order_by(models.TradeCalendar.trade_date.asc())
            .all()
        )

    def create_batch(self, db: Session, items: List[dict]) -> int:
        """批量插入（ON DUPLICATE KEY UPDATE）"""
        from sqlalchemy.dialects.mysql import insert
        if not items:
            return 0
        stmt = insert(models.TradeCalendar).values(items)
        stmt = stmt.on_duplicate_key_update(
            is_trading_day=stmt.inserted.is_trading_day,
            year=stmt.inserted.year,
            quarter=stmt.inserted.quarter,
            month=stmt.inserted.month,
            week=stmt.inserted.week,
            weekday=stmt.inserted.weekday,
            is_weekend=stmt.inserted.is_weekend,
        )
        db.execute(stmt)
        db.commit()
        return len(items)


trade_calendar_crud = TradeCalendarCRUD()