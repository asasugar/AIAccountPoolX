import asyncio
import httpx
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_config, save_config
from ..token_manager import token_manager
from ..database import db, Token

router = APIRouter(prefix="/api/newapi", tags=["newapi"])
DEFAULT_NEWAPI_TYPE_OPENAI = 57
DEFAULT_NEWAPI_MODELS = "gpt-5.4,gpt-5.3,gpt-5,gpt-5-codex,gpt-5-codex-mini,gpt-5.1,gpt-5.1-codex,gpt-5.1-codex-max,gpt-5.1-codex-mini,gpt-5.2,gpt-5.2-codex,gpt-5.3-codex,gpt-5-openai-compact,gpt-5-codex-openai-compact,gpt-5-codex-mini-openai-compact,gpt-5.1-openai-compact,gpt-5.1-codex-openai-compact,gpt-5.1-codex-max-openai-compact,gpt-5.1-codex-mini-openai-compact,gpt-5.2-openai-compact,gpt-5.2-codex-openai-compact,gpt-5.3-codex-openai-compact"
DEFAULT_NEWAPI_CHANNEL_BASE_URL = ""


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


def _get_channel_sync_settings(cfg: dict) -> tuple[int, str, str]:
    type_val = cfg.get("newapi_type_openai", DEFAULT_NEWAPI_TYPE_OPENAI)
    try:
        channel_type = int(type_val)
    except Exception:
        channel_type = DEFAULT_NEWAPI_TYPE_OPENAI
    models = (cfg.get("newapi_models") or DEFAULT_NEWAPI_MODELS).strip() or DEFAULT_NEWAPI_MODELS
    channel_base_url = (cfg.get("newapi_channel_base_url") or DEFAULT_NEWAPI_CHANNEL_BASE_URL).strip()
    return channel_type, models, channel_base_url


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
    page_size = 100
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{base_url}/api/channel/",
                params={"p": 1, "page_size": page_size, "id_sort": "true", "tag_mode": "false"},
                headers=headers,
            )
            if not r.is_success:
                return []
            data = r.json()
            wrapper = data.get("data") if isinstance(data.get("data"), dict) else data
            items = wrapper.get("items")
            if not isinstance(items, list):
                return []
            total = wrapper.get("total", len(items))
            all_items = list(items)
            total_pages = (total + page_size - 1) // page_size
            for page in range(2, total_pages + 1):
                r = await client.get(
                    f"{base_url}/api/channel/",
                    params={"p": page, "page_size": page_size, "id_sort": "true", "tag_mode": "false"},
                    headers=headers,
                )
                if not r.is_success:
                    break
                pd = r.json()
                pw = pd.get("data") if isinstance(pd.get("data"), dict) else pd
                page_items = pw.get("items")
                if not isinstance(page_items, list) or not page_items:
                    break
                all_items.extend(page_items)
    except Exception:
        return []
    return all_items


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
    channel_type, models, channel_base_url = _get_channel_sync_settings(cfg)
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
        "type": channel_type,
        "key": json.dumps({"access_token": t.get("access_token", ""), "account_id": account_name}, ensure_ascii=False),
        "base_url": channel_base_url,
        "models": models,
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
    channel_type, models, channel_base_url = _get_channel_sync_settings(cfg)
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
    channels = await fetch_channels()
    email_to_channel: dict[str, dict] = {}
    for channel_item in channels:
        name = str(channel_item.get("name", "")).strip()
        if not name:
            continue
        email_to_channel[name] = {
            "id": channel_item.get("id"),
            "status": channel_item.get("status"),
        }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "New-Api-User": user_id,
    }
    semaphore = asyncio.Semaphore(10)
    success_ids: list[str] = []
    errors: list[str] = []

    async def sync_one(client: httpx.AsyncClient, t: dict) -> tuple[bool, str, str]:
        account_name = t.get("first_name") or t.get("email", "")
        now_str = datetime.now().strftime("%Y%m%d-%H:%M")
        email = (t.get("email") or "").strip()
        matched_channel = email_to_channel.get(email) or {}
        matched_channel_id = matched_channel.get("id")
        matched_channel_status = matched_channel.get("status")
        channel = {
            "auto_ban": 1,
            "name": t.get("email") or f"{now_str}-auto",
            "type": channel_type,
            "key": json.dumps({"access_token": t.get("access_token", ""), "account_id": account_name}, ensure_ascii=False),
            "base_url": channel_base_url,
            "models": models,
            "multi_key_mode": "random",
            "group": "default",
            "groups": ["default"],
            "priority": 0,
            "weight": 0,
        }
        token_id = t.get("id", "")
        last_error = ""
        async with semaphore:
            for attempt in range(3):
                try:
                    if matched_channel_id is not None and matched_channel_status is not None:
                        channel["id"] = matched_channel_id
                        r = await client.put(
                            f"{base_url}/api/channel/",
                            json=channel,
                            headers=headers,
                        )
                    else:
                        r = await client.post(
                            f"{base_url}/api/channel/",
                            json={"mode": "single", "channel": channel},
                            headers=headers,
                        )
                    if r.is_success:
                        return True, token_id, ""
                    try:
                        err = r.json()
                        last_error = (err.get("message", r.text) or "")[:120]
                    except Exception:
                        last_error = (r.text or "")[:120]
                    if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    return False, token_id, last_error
                except Exception as e:
                    last_error = str(e)[:120]
                    if attempt < 2:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    return False, token_id, last_error
        return False, token_id, last_error

    timeout = httpx.Timeout(60.0, connect=10.0)
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        batch_size = 200
        for i in range(0, len(unsynced), batch_size):
            batch = unsynced[i:i + batch_size]
            results = await asyncio.gather(*(sync_one(client, t) for t in batch))
            for ok, token_id, err_msg in results:
                if ok:
                    success_ids.append(token_id)
                else:
                    errors.append(err_msg or "同步失败")

    if success_ids:
        with db.get_session() as session:
            rows = session.query(Token).filter(Token.token_id.in_(success_ids)).all()
            for row in rows:
                row.synced_to_newapi = True

    success_count = len(success_ids)
    fail_count = len(unsynced) - success_count
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
