"""
技术指标计算模块

为选股策略提供可组合的 SQL CTE 构建函数。所有 CTE 共享同一个
`pre_filter` 子查询，调用方按需拼接需要的指标 CTE，再写
WHERE / ORDER BY 完成筛选。

所有 CTE 期望的绑定参数：
- :trade_date       目标交易日
- :start_date       预筛选起始日（pre_filter 用）
- :min_amount       预筛选最低成交额均值（pre_filter 用）

调用方可按需补充其他参数（min_pct_chg、rsi_min 等），它们会通过
`db.execute(text(sql), params)` 一并传入。
"""

from typing import Iterable, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


# ==================== 预筛选 / 当日数据 ====================

def build_pre_filter_cte(
    exclude_sql: str = "",
    min_count: int = 8,
    extra_having: Optional[str] = None,
) -> str:
    """构建 pre_filter CTE：沪深主板非ST，最近若干日数据完整。

    需要绑定的参数：trade_date / start_date / min_amount。

    :param exclude_sql: 由 filters.build_exclude_sql 产生的额外排除条件
        SQL 片段（每行已带 `    AND ...` 前缀）
    :param min_count: 至少多少条日线数据才纳入预筛
    :param extra_having: 额外的 HAVING 子句（不带 AND 前缀），
        用于震荡选股等需要叠加均值上限条件的场景
    """
    extra_having_sql = f"\n            AND {extra_having}" if extra_having else ""
    return f"""pre_filter AS (
        SELECT
            sd.symbol,
            sb.name,
            sb.industry,
            AVG(ABS(sd.pct_chg)) AS avg_abs_pct,
            AVG(sd.turnover) AS avg_turnover,
            AVG(sd.amount) AS avg_amount
        FROM stock_daily sd
        JOIN stock_basic sb ON sd.symbol = sb.symbol
        WHERE sd.trade_date <= :trade_date
            AND sd.trade_date >= :start_date
            AND sb.market = '主板'
{exclude_sql}
        GROUP BY sd.symbol, sb.name, sb.industry
        HAVING COUNT(*) >= {min_count}
            AND AVG(ABS(sd.pct_chg)) > 2
            AND AVG(sd.turnover) > 2
            AND AVG(sd.amount) > :min_amount{extra_having_sql}
    )"""


def build_latest_data_cte() -> str:
    """构建 latest_data CTE：从 pre_filter 中筛选 :trade_date 当日的盘口数据"""
    return """latest_data AS (
        SELECT
            symbol,
            close,
            open,
            high,
            low,
            volume,
            amount,
            turnover,
            pct_chg,
            trade_date
        FROM stock_daily
        WHERE trade_date = :trade_date
            AND symbol IN (SELECT symbol FROM pre_filter)
    )"""


# ==================== 技术指标 CTE ====================

def build_ma_cte(periods: Iterable[int] = (5, 10, 20, 60)) -> str:
    """构建多周期均线 CTE，从 stock_daily_indicator 预计算表读取。"""
    periods = tuple(periods)
    col_lines = ',\n            '.join(
        f"ma{p}" for p in periods
    )
    return f"""ma_calc AS (
        SELECT
            symbol COLLATE utf8mb4_unicode_ci AS symbol,
            {col_lines}
        FROM stock_daily_indicator
        WHERE trade_date = :trade_date
            AND symbol COLLATE utf8mb4_unicode_ci IN (SELECT symbol FROM pre_filter)
    )"""


def build_macd_cte() -> str:
    """构建近似 MACD CTE，输出 dif / dif_prev（用于判断金叉）。"""
    return """macd_calc AS (
        SELECT
            symbol,
            AVG(CASE WHEN rn <= 12 THEN close END) -
            AVG(CASE WHEN rn <= 26 THEN close END) AS dif,
            AVG(CASE WHEN rn <= 13 AND rn > 1 THEN close END) -
            AVG(CASE WHEN rn <= 27 AND rn > 1 THEN close END) AS dif_prev
        FROM (
            SELECT
                symbol,
                close,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
            FROM stock_daily
            WHERE symbol IN (SELECT symbol FROM pre_filter)
                AND trade_date <= :trade_date
        ) t
        WHERE rn <= 27
        GROUP BY symbol
    )"""


def build_rsi_cte(period: int = 14) -> str:
    """构建 RSI CTE，输出 rsi_{period} 列。"""
    return f"""rsi_calc AS (
        SELECT
            symbol,
            CASE
                WHEN avg_loss = 0 THEN 100
                ELSE 100 - (100 / (1 + avg_gain / avg_loss))
            END AS rsi_{period}
        FROM (
            SELECT
                symbol,
                AVG(CASE WHEN close > prev_close THEN close - prev_close ELSE 0 END) AS avg_gain,
                AVG(CASE WHEN close < prev_close THEN prev_close - close ELSE 0 END) AS avg_loss
            FROM (
                SELECT
                    symbol,
                    close,
                    LAG(close) OVER (PARTITION BY symbol ORDER BY trade_date) AS prev_close,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
                FROM stock_daily
                WHERE symbol IN (SELECT symbol FROM pre_filter)
                    AND trade_date <= :trade_date
            ) t
            WHERE rn <= {period} AND prev_close IS NOT NULL
            GROUP BY symbol
            HAVING COUNT(*) >= {period}
        ) t2
    )"""


def build_bollinger_cte(period: int = 20, std_multiplier: float = 2.0) -> str:
    """构建布林带 CTE，输出 bb_lower / bb_middle / bb_upper / bb_width。"""
    return f"""bb_calc AS (
        SELECT
            symbol,
            AVG(CASE WHEN rn <= {period} THEN close END) AS bb_middle,
            STDDEV(CASE WHEN rn <= {period} THEN close END) AS bb_std
        FROM (
            SELECT
                symbol,
                close,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
            FROM stock_daily
            WHERE symbol IN (SELECT symbol FROM pre_filter)
                AND trade_date <= :trade_date
        ) t
        WHERE rn <= {period}
        GROUP BY symbol
        HAVING COUNT(*) >= {period}
    ),
    bb_result AS (
        SELECT
            symbol,
            bb_middle - {std_multiplier} * bb_std AS bb_lower,
            bb_middle,
            bb_middle + {std_multiplier} * bb_std AS bb_upper,
            ({std_multiplier} * 2 * bb_std) / bb_middle AS bb_width
        FROM bb_calc
        WHERE bb_middle > 0
    )"""


def build_volume_avg_cte(period: int = 20) -> str:
    """构建 N 日均量 CTE（不包含当日，用于计算量比）。"""
    return f"""volume_calc AS (
        SELECT
            symbol,
            AVG(CASE WHEN rn <= {period} THEN volume END) AS avg_volume_{period}
        FROM (
            SELECT
                symbol,
                volume,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
            FROM stock_daily
            WHERE symbol IN (SELECT symbol FROM pre_filter)
                AND trade_date < :trade_date
        ) t
        WHERE rn <= {period}
        GROUP BY symbol
    )"""


def build_amplitude_avg_cte(period: int = 20) -> str:
    """构建 N 日振幅均值 CTE。"""
    return f"""amplitude_calc AS (
        SELECT
            symbol,
            AVG(amplitude) AS avg_amplitude_{period}
        FROM (
            SELECT
                symbol,
                amplitude,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
            FROM stock_daily
            WHERE symbol IN (SELECT symbol FROM pre_filter)
                AND trade_date <= :trade_date
        ) t
        WHERE rn <= {period}
        GROUP BY symbol
    )"""


def assemble_with(*ctes: str) -> str:
    """将多个 CTE 字符串拼接成单个 WITH 子句（包含 WITH 关键字）。"""
    body = ",\n    ".join(c.strip() for c in ctes if c)
    return f"WITH {body}"


# ==================== 辅助函数 ====================

def get_recent_trade_dates(db: Session, n: int = 10) -> List[str]:
    """获取最近 N 个交易日"""
    result = db.execute(text("""
        SELECT DISTINCT trade_date
        FROM stock_daily
        ORDER BY trade_date DESC
        LIMIT :limit
    """), {"limit": n}).fetchall()
    return [str(r[0]) for r in result]


def validate_trade_date(db: Session, trade_date: str) -> Optional[str]:
    """验证交易日期是否存在，返回标准化日期或 None"""
    normalized = trade_date.replace("-", "")
    result = db.execute(text("""
        SELECT 1 FROM stock_daily
        WHERE trade_date = :date
        LIMIT 1
    """), {"date": normalized}).fetchone()
    return normalized if result else None
