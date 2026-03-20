"""
SQLite 数据库模块
使用 SQLAlchemy ORM 管理数据
"""
import os
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Index, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .config import get_config

Base = declarative_base()


class Token(Base):
    """Token 模型"""
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_id = Column(String(128), unique=True, nullable=False, index=True)  # 唯一标识符
    platform = Column(String(32), nullable=False, default="openai", index=True)
    email = Column(String(256), nullable=False, index=True)

    # Token 数据
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    id_token = Column(Text, nullable=True)
    token_type = Column(String(32), default="Bearer")
    expires_in = Column(Integer, default=0)

    # 状态
    status = Column(String(16), default="active", index=True)  # active, invalid, expired
    in_use = Column(Boolean, default=False)
    synced_to_newapi = Column(Boolean, default=False)

    # 统计
    used_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 复合索引
    __table_args__ = (
        Index('idx_platform_status', 'platform', 'status'),
        Index('idx_platform_email', 'platform', 'email'),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.token_id,
            "platform": self.platform,
            "email": self.email,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "id_token": self.id_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "status": self.status,
            "in_use": self.in_use,
            "synced_to_newapi": self.synced_to_newapi or False,
            "used_count": self.used_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "saved_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Account(Base):
    """账号模型 - 存储注册的账号信息"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(32), nullable=False, index=True)

    # 基本信息
    email = Column(String(256), nullable=False)
    password = Column(String(256), nullable=True)
    username = Column(String(128), nullable=True)  # 用户名

    # 个人信息
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    birth_year = Column(Integer, nullable=True)  # 出生年
    birth_month = Column(Integer, nullable=True)  # 出生月
    birth_day = Column(Integer, nullable=True)  # 出生日

    # 状态
    status = Column(String(16), default="active")  # active, banned, unverified
    verified = Column(Boolean, default=False)

    # 元数据
    register_ip = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON 格式存储额外数据

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_account_platform_email', 'platform', 'email', unique=True),
    )

    def to_dict(self, include_password: bool = False) -> dict:
        result = {
            "id": self.id,
            "platform": self.platform,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birth_year": self.birth_year,
            "birth_month": self.birth_month,
            "birth_day": self.birth_day,
            "status": self.status,
            "verified": self.verified,
            "register_ip": self.register_ip,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_password:
            result["password"] = self.password
        return result


class TaskLog(Base):
    """任务日志模型"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(32), nullable=False, index=True)
    task_type = Column(String(32), default="register")  # register, refresh, validate

    # 结果
    success = Column(Boolean, default=False)
    email = Column(String(256), nullable=True)
    message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    # 代理信息
    proxy_used = Column(String(256), nullable=True)

    # 耗时
    duration_ms = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "platform": self.platform,
            "task_type": self.task_type,
            "success": self.success,
            "email": self.email,
            "message": self.message,
            "error": self.error,
            "proxy_used": self.proxy_used,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProxyRecord(Base):
    """代理使用记录"""
    __tablename__ = "proxy_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proxy_url = Column(String(512), nullable=False, index=True)

    # 统计
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)

    # 状态
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_fail = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "proxy_url": self.proxy_url,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "total_count": self.total_count,
            "success_rate": round(self.success_count / max(self.total_count, 1) * 100, 2),
            "is_active": self.is_active,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


class Database:
    """数据库管理类"""

    _instance: Optional["Database"] = None
    _engine = None
    _SessionLocal = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self, db_path: Optional[str] = None):
        """初始化数据库连接"""
        if self._engine is not None:
            return

        if db_path is None:
            cfg = get_config()
            data_dir = cfg.get("data_dir", "./data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "aiaccountpool.db")

        # SQLite 连接字符串
        db_url = f"sqlite:///{db_path}"

        self._engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,  # 生产环境关闭 SQL 日志
        )

        self._SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine
        )

        # 创建所有表
        Base.metadata.create_all(bind=self._engine)

        print(f"[Database] 数据库已初始化: {db_path}")

    @contextmanager
    def get_session(self):
        """获取数据库会话（上下文管理器）"""
        if self._SessionLocal is None:
            self.init()

        session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_direct(self) -> Session:
        """获取数据库会话（直接返回，需手动管理）"""
        if self._SessionLocal is None:
            self.init()
        return self._SessionLocal()


# 全局数据库实例
db = Database()


def get_db():
    """依赖注入用：获取数据库会话"""
    with db.get_session() as session:
        yield session
