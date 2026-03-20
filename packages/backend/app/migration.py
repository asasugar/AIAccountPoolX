"""
数据库迁移工具
"""

from .database import db, Token
from .log_manager import log_manager as log


def _add_column_if_missing(session, table: str, column: str, col_def: str):
    """SQLite ALTER TABLE 兼容方式补列"""
    try:
        result = session.execute(__import__("sqlalchemy").text(f"PRAGMA table_info({table})")).fetchall()
        existing = [row[1] for row in result]
        if column not in existing:
            session.execute(__import__("sqlalchemy").text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))
            log.info(f"[Migration] 已添加列 {table}.{column}")
    except Exception as e:
        log.error(f"[Migration] 添加列失败 {table}.{column}: {e}")


def check_and_migrate():
    """
    检查并执行数据库结构迁移
    """
    db.init()

    with db.get_session() as session:
        _add_column_if_missing(session, "tokens", "synced_to_newapi", "BOOLEAN DEFAULT 0")

    with db.get_session() as session:
        count = session.query(Token).count()
        if count > 0:
            log.info(f"数据库已有 {count} 条 Token 记录")


if __name__ == "__main__":
    check_and_migrate()
