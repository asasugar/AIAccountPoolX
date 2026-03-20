import httpx
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_config, save_config
from ..token_manager import token_manager
from ..database import db, Token

router = APIRouter(prefix="/api/newapi", tags=["newapi"])
# 57是openai oauth的类型
NEWAPI_TYPE_OPENAI = 57
DEFAULT_MODELS = "gpt-5.3,gpt-5,gpt-5-codex,gpt-5-codex-mini,gpt-5.1,gpt-5.1-codex,gpt-5.1-codex-max,gpt-5.1-codex-mini,gpt-5.2,gpt-5.2-codex,gpt-5.3-codex,gpt-5-openai-compact,gpt-5-codex-openai-compact,gpt-5-codex-mini-openai-compact,gpt-5.1-openai-compact,gpt-5.1-codex-openai-compact,gpt-5.1-codex-max-openai-compact,gpt-5.1-codex-mini-openai-compact,gpt-5.2-openai-compact,gpt-5.2-codex-openai-compact,gpt-5.3-codex-openai-compact"
DEFAULT_BASE_URL = ""


def _get_sync_status(cfg: dict) -> dict:
    return {
        "last_sync_at": cfg.get("newapi_sync_last_at"),
        "status": cfg.get("newapi_sync_status", "idle"),
        "message": cfg.get("newapi_sync_message", ""),
        "success_count": cfg.get("newapi_sync_success_count", 0),
        "fail_count": cfg.get("newapi_sync_fail_count", 0),
    }


def _get_headers(cfg: dict) -> tuple:
    base_url = (cfg.get("newapi_base_url") or "").rstrip("/")
    token = cfg.get("newapi_token")
    user_id = (cfg.get("newapi_user_id") or "").strip()
    return base_url, token, user_id


async def fetch_channels() -> list:
    cfg = get_config()
    base_url, token, user_id = _get_headers(cfg)
    if not base_url or not token or not user_id:
        return []
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "New-Api-User": user_id,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{base_url}/api/channel/",
                params={"p": 1, "page_size": 999, "id_sort": "true", "tag_mode": "false"},
                headers=headers,
            )
        if not r.is_success:
            return []
        data = r.json()
        items = data.get("items")
        if items is None and isinstance(data.get("data"), dict):
            items = data["data"].get("items")
        return items if isinstance(items, list) else []
    except Exception:
        return []


@router.get("/channels")
async def get_channels():
    items = await fetch_channels()
    return {"items": items}


@router.get("/channel/test/{channel_id}")
async def test_channel(channel_id: int):
    cfg = get_config()
    base_url, token, user_id = _get_headers(cfg)
    if not base_url or not token or not user_id:
        raise HTTPException(status_code=400, detail="请先配置 newAPI")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "New-Api-User": user_id,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{base_url}/api/channel/test/{channel_id}?model=gpt-5.2-codex&stream=true",
            headers=headers,
        )
    if not r.is_success:
        return {"ok": False, "message": "请求失败"}
    try:
        body = r.json()
        if isinstance(body, bool):
            ok = body
            time_val = None
        elif isinstance(body, dict):
            ok = body.get("success", False)
            time_val = body.get("time")
        else:
            ok = False
            time_val = None
        out = {"ok": bool(ok)}
        if time_val is not None:
            out["time"] = time_val
        return out
    except Exception:
        return {"ok": False}


class BatchChannelRequest(BaseModel):
    ids: list[int] = []


async def batch_delete_channel_ids(ids: list[int]) -> None:
    if not ids:
        return
    cfg = get_config()
    base_url, token, user_id = _get_headers(cfg)
    if not base_url or not token or not user_id:
        raise HTTPException(status_code=400, detail="请先配置 newAPI")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "New-Api-User": user_id,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{base_url}/api/channel/batch",
            json={"ids": ids},
            headers=headers,
        )
    if not r.is_success:
        try:
            err = r.json()
            raise HTTPException(status_code=r.status_code, detail=err.get("message", r.text))
        except HTTPException:
            raise
        raise HTTPException(status_code=r.status_code, detail=r.text[:200])


@router.post("/channel/batch")
async def batch_delete_channels(body: BatchChannelRequest):
    if not body.ids:
        return {"ok": True, "deleted": 0}
    await batch_delete_channel_ids(body.ids)
    return {"ok": True, "deleted": len(body.ids)}


@router.delete("/channel/{channel_id}")
async def delete_channel(channel_id: int):
    cfg = get_config()
    base_url, token, user_id = _get_headers(cfg)
    if not base_url or not token or not user_id:
        raise HTTPException(status_code=400, detail="请先配置 newAPI")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "New-Api-User": user_id,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.delete(f"{base_url}/api/channel/{channel_id}", headers=headers)
    if not r.is_success:
        try:
            err = r.json()
            raise HTTPException(status_code=r.status_code, detail=err.get("message", r.text))
        except HTTPException:
            raise
        raise HTTPException(status_code=r.status_code, detail=r.text[:200])
    return {"ok": True}


class UpdateChannelRequest(BaseModel):
    channel_id: int
    token_id: str
    platform: str = "openai"


@router.put("/channel")
async def update_channel(body: UpdateChannelRequest):
    cfg = get_config()
    base_url, token, user_id = _get_headers(cfg)
    if not base_url or not token or not user_id:
        raise HTTPException(status_code=400, detail="请先配置 newAPI")
    t = token_manager.get_token(body.token_id, body.platform or "")
    if not t:
        raise HTTPException(status_code=404, detail="Token 不存在")
    if t.get("synced_to_newapi"):
        raise HTTPException(status_code=400, detail="仅当状态为 Token刷新，待同步 时可更新渠道")
    account_name = t.get("first_name") or t.get("email", "")
    channel = {
        "id": body.channel_id,
        "auto_ban": 1,
        "name": t.get("email") or "",
        "type": NEWAPI_TYPE_OPENAI,
        "key": json.dumps({"access_token": t.get("access_token", ""), "account_id": account_name}, ensure_ascii=False),
        "base_url": DEFAULT_BASE_URL,
        "models": DEFAULT_MODELS,
        "multi_key_mode": "random",
        "group": "default",
        "groups": ["default"],
        "priority": 0,
        "weight": 0,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "New-Api-User": user_id,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.put(
            f"{base_url}/api/channel/",
            json=channel,
            headers=headers,
        )
    if not r.is_success:
        try:
            err = r.json()
            raise HTTPException(status_code=r.status_code, detail=err.get("message", r.text))
        except HTTPException:
            raise
        raise HTTPException(status_code=r.status_code, detail=r.text[:200])
    with db.get_session() as session:
        row = session.query(Token).filter(Token.token_id == body.token_id).first()
        if row:
            row.synced_to_newapi = True
    return {"ok": True, "message": "渠道已更新"}


@router.get("/sync-status")
async def get_sync_status():
    cfg = get_config()
    return _get_sync_status(cfg)


@router.post("/sync")
async def sync_to_newapi():
    cfg = get_config()
    base_url = (cfg.get("newapi_base_url") or "").rstrip("/")
    token = cfg.get("newapi_token")
    user_id = (cfg.get("newapi_user_id") or "").strip()
    if not base_url or not token:
        raise HTTPException(
            status_code=400,
            detail="请先在系统配置中填写 newAPI 地址和鉴权 Token",
        )
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="请填写 newAPI 用户 ID（New-Api-User，需与当前登录用户一致）",
        )
    tokens, _ = token_manager.list_tokens(platform="openai", page=1, page_size=10000, status="active")
    unsynced = [t for t in tokens if not t.get("synced_to_newapi")]
    success_count = 0
    fail_count = 0
    errors = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for t in unsynced:
            account_name = t.get("first_name") or t.get("email", "")
            now_str = datetime.now().strftime("%Y%m%d-%H:%M")
            channel = {
                "auto_ban": 1,
                "name": t.get("email") or f"{now_str}-auto",
                "type": NEWAPI_TYPE_OPENAI,
                "key": json.dumps({"access_token": t.get("access_token", ""), "account_id": account_name}, ensure_ascii=False),
                "base_url": DEFAULT_BASE_URL,
                "models": DEFAULT_MODELS,
                "multi_key_mode": "random",
                "group": "default",
                "groups": ["default"],
                "priority": 0,
                "weight": 0,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "New-Api-User": user_id,
            }
            try:
                r = await client.post(
                    f"{base_url}/api/channel/",
                    json={"mode": "single", "channel": channel},
                    headers=headers,
                )
                if r.is_success:
                    success_count += 1
                    with db.get_session() as session:
                        row = session.query(Token).filter(Token.token_id == t["id"]).first()
                        if row:
                            row.synced_to_newapi = True
                else:
                    fail_count += 1
                    try:
                        err = r.json()
                        errors.append(err.get("message", r.text)[:80])
                    except Exception:
                        errors.append(r.text[:80])
            except Exception as e:
                fail_count += 1
                errors.append(str(e)[:80])
    message = ""
    if errors:
        message = "; ".join(errors[:3])
        if len(errors) > 3:
            message += f" …共{len(errors)}条"
    cfg = get_config()
    cfg["newapi_sync_last_at"] = datetime.utcnow().isoformat() + "Z"
    cfg["newapi_sync_status"] = "success" if fail_count == 0 else "partial" if success_count else "error"
    cfg["newapi_sync_message"] = message
    cfg["newapi_sync_success_count"] = success_count
    cfg["newapi_sync_fail_count"] = fail_count
    save_config(cfg)
    return {
        "ok": True,
        "success_count": success_count,
        "fail_count": fail_count,
        "message": message,
        **_get_sync_status(cfg),
    }
