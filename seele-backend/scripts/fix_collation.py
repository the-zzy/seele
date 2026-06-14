"""
统一数据库表及字段 collation 为 utf8mb4_unicode_ci，修复跨表 JOIN 1267 错误。

用法（在项目根目录执行）：
    cd seele-backend
    python scripts/fix_collation.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymysql
from app.config import get_settings

TARGET_COLLATION = 'utf8mb4_unicode_ci'


def get_connection():
    settings = get_settings()
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset='utf8mb4',
    )


def main():
    settings = get_settings()
    print(f'[{settings.db_name}] 开始检查并修正 collation...')

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 修正数据库默认 collation
            cur.execute(
                f'ALTER DATABASE `{settings.db_name}` '
                f'CHARACTER SET utf8mb4 COLLATE {TARGET_COLLATION};'
            )
            print(f'  数据库默认 collation 已设为 {TARGET_COLLATION}')

            # 2. 找出所有 collation 不一致的表
            cur.execute("""
                SELECT TABLE_NAME, TABLE_COLLATION
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_TYPE = 'BASE TABLE'
            """, (settings.db_name,))
            tables = cur.fetchall()

            fixed_tables = []
            for table_name, table_collation in tables:
                if table_collation != TARGET_COLLATION:
                    sql = (
                        f'ALTER TABLE `{table_name}` '
                        f'CONVERT TO CHARACTER SET utf8mb4 COLLATE {TARGET_COLLATION};'
                    )
                    cur.execute(sql)
                    fixed_tables.append((table_name, table_collation))
                    print(f'  修正表 {table_name}: {table_collation} -> {TARGET_COLLATION}')

            # 3. 检查是否还有不一致的字段
            cur.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND COLLATION_NAME IS NOT NULL
                  AND COLLATION_NAME != %s
            """, (settings.db_name, TARGET_COLLATION))
            columns = cur.fetchall()

            fixed_columns = []
            for table_name, column_name, charset, collation in columns:
                cur.execute(
                    f'ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` '
                    f'{_rebuild_column_def(cur, table_name, column_name)} '
                    f'CHARACTER SET utf8mb4 COLLATE {TARGET_COLLATION};'
                )
                fixed_columns.append((table_name, column_name, collation))
                print(f'  修正字段 {table_name}.{column_name}: {collation} -> {TARGET_COLLATION}')

        conn.commit()

    if fixed_tables or fixed_columns:
        print(f'\n完成：修正 {len(fixed_tables)} 张表，{len(fixed_columns)} 个字段。')
    else:
        print('\n无需修正：所有表和字段 collation 已统一。')


def _rebuild_column_def(cur, table_name, column_name):
    """重建列定义（保留类型、长度、可空、默认值等），只改 collation。"""
    cur.execute("""
        SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
    """, (table_name, column_name))
    row = cur.fetchone()
    column_type, is_nullable, column_default, extra = row

    parts = [column_type]
    if is_nullable == 'NO':
        parts.append('NOT NULL')
    if column_default is not None:
        default_upper = str(column_default).upper()
        # 保留时间戳关键字和无引号数字，其余加单引号
        if default_upper in ('CURRENT_TIMESTAMP', 'NULL'):
            parts.append(f'DEFAULT {default_upper}')
        elif default_upper.isdigit() or _is_float(default_upper):
            parts.append(f'DEFAULT {column_default}')
        else:
            parts.append(f'DEFAULT {column_default!r}')
    elif is_nullable == 'YES':
        parts.append('DEFAULT NULL')
    if extra:
        parts.append(extra)

    return ' '.join(parts)


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


if __name__ == '__main__':
    main()
