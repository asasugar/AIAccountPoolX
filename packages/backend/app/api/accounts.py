"""
账号管理 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..database import db, Account, Token

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    platform: str = "openai"
    email: str
    password: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_year: Optional[int] = None
    birth_month: Optional[int] = None
    birth_day: Optional[int] = None
    register_ip: Optional[str] = None


class AccountUpdate(BaseModel):
    password: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_year: Optional[int] = None
    birth_month: Optional[int] = None
    birth_day: Optional[int] = None
    status: Optional[str] = None
    verified: Optional[bool] = None


@router.get("")
async def list_accounts(
    platform: str = "",
    search: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 50,
    include_password: bool = False,
):
    """获取账号列表"""
    with db.get_session() as session:
        query = session.query(Account)

        if platform:
            query = query.filter(Account.platform == platform)
        if status:
            query = query.filter(Account.status == status)
        if search:
            query = query.filter(Account.email.ilike(f"%{search}%"))

        total = query.count()

        accounts = query.order_by(Account.created_at.desc()) \
                       .offset((page - 1) * page_size) \
                       .limit(page_size) \
                       .all()

        return {
            "items": [a.to_dict(include_password=include_password) for a in accounts],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@router.get("/{account_id}")
async def get_account(account_id: int, include_password: bool = False):
    """获取单个账号详情"""
    with db.get_session() as session:
        account = session.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        return account.to_dict(include_password=include_password)


@router.get("/{account_id}/token")
async def get_account_token(account_id: int):
    """获取账号关联的 Token"""
    with db.get_session() as session:
        account = session.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")

        # 查找关联的 Token
        token = session.query(Token).filter(
            Token.platform == account.platform,
            Token.email == account.email
        ).first()

        if not token:
            return {"has_token": False, "token": None}

        return {
            "has_token": True,
            "token": token.to_dict()
        }


@router.post("")
async def create_account(data: AccountCreate):
    """创建账号"""
    with db.get_session() as session:
        # 检查是否已存在
        existing = session.query(Account).filter(
            Account.platform == data.platform,
            Account.email == data.email
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="账号已存在")

        account = Account(
            platform=data.platform,
            email=data.email,
            password=data.password,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            birth_year=data.birth_year,
            birth_month=data.birth_month,
            birth_day=data.birth_day,
            register_ip=data.register_ip,
            status="active",
            verified=True,
        )
        session.add(account)
        session.flush()

        return {"ok": True, "id": account.id, "message": "账号已创建"}


@router.put("/{account_id}")
async def update_account(account_id: int, data: AccountUpdate):
    """更新账号"""
    with db.get_session() as session:
        account = session.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")

        # 更新字段
        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(account, field, value)

        return {"ok": True, "message": "账号已更新"}


@router.delete("/{account_id}")
async def delete_account(account_id: int):
    """删除账号"""
    with db.get_session() as session:
        account = session.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")

        session.delete(account)
        return {"ok": True, "message": "账号已删除"}


@router.get("/stats/summary")
async def get_accounts_stats(platform: str = ""):
    """获取账号统计"""
    with db.get_session() as session:
        query = session.query(Account)
        if platform:
            query = query.filter(Account.platform == platform)

        total = query.count()
        active = query.filter(Account.status == "active").count()
        verified = query.filter(Account.verified == True).count()
        banned = query.filter(Account.status == "banned").count()

        return {
            "total": total,
            "active": active,
            "verified": verified,
            "banned": banned,
        }


@router.post("/seed")
async def seed_test_data():
    """预置测试数据"""
    from ..seed_data import seed_test_data as do_seed
    accounts, tokens = do_seed()
    return {
        "ok": True,
        "message": f"已创建 {accounts} 个账号, {tokens} 个 Token",
        "accounts_created": accounts,
        "tokens_created": tokens,
    }
