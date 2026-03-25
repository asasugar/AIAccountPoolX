"""
Token 管理器 - 基于 SQLite 数据库
"""
from datetime import datetime
from typing import Optional
from threading import Lock

from sqlalchemy import func, and_, Integer

from .database import db, Token, Account
from .log_manager import log_manager as log
from .token_manager_helpers import (
    apply_token_update,
    attach_account_fields,
    build_token_entity,
    build_token_id,
)


class TokenManager:
    def __init__(self):
        self._lock = Lock()
        # 确保数据库已初始化
        db.init()

    def list_tokens(
        self,
        platform: str = "",
        search: str = "",
        page: int = 1,
        page_size: int = 50,
        status: str = "",
        synced_to_newapi: str = "",
    ) -> tuple[list[dict], int]:
        """
        获取 Token 列表（支持分页和搜索），关联 Account 表补充账号信息
        返回: (tokens, total_count)
        """
        with db.get_session() as session:
            base = session.query(Token, Account).outerjoin(
                Account,
                (Token.email == Account.email) & (Token.platform == Account.platform)
            )

            if platform:
                base = base.filter(Token.platform == platform)
            if status:
                base = base.filter(Token.status == status)
            if synced_to_newapi != "":
                synced_flag = str(synced_to_newapi).lower() in ("1", "true", "yes")
                base = base.filter(Token.synced_to_newapi == synced_flag)
            if search:
                base = base.filter(Token.email.ilike(f"%{search}%"))

            total = base.count()

            rows = base.order_by(Token.created_at.desc()) \
                       .offset((page - 1) * page_size) \
                       .limit(page_size) \
                       .all()

            results = []
            for token, acc in rows:
                d = token.to_dict()
                results.append(attach_account_fields(d, acc))

            return results, total

    def get_token(self, token_id: str, platform: str = "") -> Optional[dict]:
        """获取单个 Token"""
        with db.get_session() as session:
            query = session.query(Token).filter(Token.token_id == token_id)
            if platform:
                query = query.filter(Token.platform == platform)
            token = query.first()
            return token.to_dict() if token else None

    def delete_token(self, token_id: str, platform: str = "") -> bool:
        """删除 Token"""
        with db.get_session() as session:
            query = session.query(Token).filter(Token.token_id == token_id)
            if platform:
                query = query.filter(Token.platform == platform)
            token = query.first()
            if token:
                email = token.email
                session.delete(token)
                log.info(f"已删除 Token: {email} (ID: {token_id})")
                return True
            return False

    def batch_delete_tokens(self, token_ids: list[str], platform: str = "") -> int:
        """批量删除 Token，返回实际删除数量"""
        if not token_ids:
            return 0
        deleted = 0
        with db.get_session() as session:
            for token_id in token_ids:
                query = session.query(Token).filter(Token.token_id == token_id)
                if platform:
                    query = query.filter(Token.platform == platform)
                token = query.first()
                if token:
                    session.delete(token)
                    deleted += 1
        return deleted

    def save_token(self, email: str, token_data: dict, platform: str = "openai") -> str:
        """
        保存 Token
        如果已存在则更新，否则创建
        """
        token_id = build_token_id(email, platform)

        with db.get_session() as session:
            # 查找现有记录
            existing = session.query(Token).filter(Token.token_id == token_id).first()

            if existing:
                # 更新现有记录（如刷新 Token 后需重新同步 newAPI）
                apply_token_update(existing, token_data)
                log.info(f"Token 已更新: {email}")
            else:
                # 创建新记录
                new_token = build_token_entity(token_id, platform, email, token_data)
                session.add(new_token)
                log.success(f"Token 已保存: {email}")

            return token_id

    def acquire_token(self, platform: str = "openai") -> Optional[dict]:
        """
        获取一个可用的 Token (用于分发)
        自动标记为使用中，更新使用次数和最后使用时间
        """
        with self._lock:
            with db.get_session() as session:
                # 查找可用的 Token：状态为 active 且不在使用中
                token = session.query(Token).filter(
                    and_(
                        Token.platform == platform,
                        Token.status == "active",
                        Token.in_use == False
                    )
                ).order_by(Token.used_count.asc()).first()

                if not token:
                    log.warning(f"[平台:{platform}] 无可用 Token")
                    return None

                # 标记为使用中
                token.in_use = True
                token.used_count += 1
                token.last_used = datetime.utcnow()

                result = token.to_dict()
                log.info(f"[平台:{platform}] Token 已分发: {token.email}")
                return result

    def release_token(self, token_id: str, success: bool = True, platform: str = "") -> bool:
        """
        释放 Token，标记为不再使用
        """
        with self._lock:
            with db.get_session() as session:
                query = session.query(Token).filter(Token.token_id == token_id)
                if platform:
                    query = query.filter(Token.platform == platform)
                token = query.first()

                if token and token.in_use:
                    token.in_use = False
                    if not success:
                        # 如果使用失败，可以考虑标记为 invalid
                        pass
                    log.info(f"Token 已释放: {token.email}, 成功: {success}")
                    return True
                return False

    def update_token_status(self, token_id: str, status: str, platform: str = "") -> bool:
        """更新 Token 状态"""
        with db.get_session() as session:
            query = session.query(Token).filter(Token.token_id == token_id)
            if platform:
                query = query.filter(Token.platform == platform)
            token = query.first()
            if token:
                token.status = status
                token.updated_at = datetime.utcnow()
                return True
            return False

    def get_usage_stats(self, platform: str = "") -> dict:
        """获取 Token 使用统计"""
        with db.get_session() as session:
            query = session.query(Token)
            if platform:
                query = query.filter(Token.platform == platform)

            total = query.count()
            active = query.filter(Token.status == "active").count()
            in_use = query.filter(Token.in_use == True).count()
            available = query.filter(
                and_(Token.status == "active", Token.in_use == False)
            ).count()

            # 总使用次数
            total_used = session.query(func.sum(Token.used_count)).filter(
                Token.platform == platform if platform else True
            ).scalar() or 0

            return {
                "total": total,
                "active": active,
                "in_use": in_use,
                "available": available,
                "total_used_count": total_used,
            }

    def get_platform_stats(self) -> list[dict]:
        """获取各平台统计"""
        with db.get_session() as session:
            platforms = session.query(
                Token.platform,
                func.count(Token.id).label("total"),
                func.sum(func.cast(Token.status == "active", Integer)).label("active"),
            ).group_by(Token.platform).all()

            return [
                {
                    "platform": p.platform,
                    "total": p.total,
                    "active": p.active or 0,
                }
                for p in platforms
            ]

    def export_tokens(self, platform: str = "") -> list[dict]:
        """导出所有 Token"""
        tokens, _ = self.list_tokens(platform=platform, page_size=10000)
        return tokens

    def batch_import(self, tokens_data: list[dict], platform: str = "openai") -> int:
        """
        批量导入 Token
        返回导入数量
        """
        count = 0
        for data in tokens_data:
            email = data.get("email", "")
            if not email:
                continue
            self.save_token(email, data, platform)
            count += 1
        return count

# 全局实例
token_manager = TokenManager()


# 兼容旧的 list_tokens 调用方式
def _compat_list_tokens(self, platform: str = "") -> list[dict]:
    """ 兼容旧版本的 list_tokens 调用 """
    tokens, _ = self.list_tokens(platform=platform, page_size=10000)
    return tokens
