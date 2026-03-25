from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_id = Column(String(128), unique=True, nullable=False, index=True)
    platform = Column(String(32), nullable=False, default="openai", index=True)
    email = Column(String(256), nullable=False, index=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    id_token = Column(Text, nullable=True)
    token_type = Column(String(32), default="Bearer")
    expires_in = Column(Integer, default=0)
    status = Column(String(16), default="active", index=True)
    in_use = Column(Boolean, default=False)
    synced_to_newapi = Column(Boolean, default=False)
    used_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_platform_status", "platform", "status"),
        Index("idx_platform_email", "platform", "email"),
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
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(32), nullable=False, index=True)
    email = Column(String(256), nullable=False)
    password = Column(String(256), nullable=True)
    username = Column(String(128), nullable=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    birth_year = Column(Integer, nullable=True)
    birth_month = Column(Integer, nullable=True)
    birth_day = Column(Integer, nullable=True)
    status = Column(String(16), default="active")
    verified = Column(Boolean, default=False)
    register_ip = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    extra_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_account_platform_email", "platform", "email", unique=True),
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
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(32), nullable=False, index=True)
    task_type = Column(String(32), default="register")
    success = Column(Boolean, default=False)
    email = Column(String(256), nullable=True)
    message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    proxy_used = Column(String(256), nullable=True)
    duration_ms = Column(Integer, default=0)
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
    __tablename__ = "proxy_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proxy_url = Column(String(512), nullable=False, index=True)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_fail = Column(DateTime, nullable=True)
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
