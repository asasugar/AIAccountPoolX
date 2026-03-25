from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..token_manager import token_manager
from ..oauth import refresh_access_token as oauth_refresh
from . import newapi as newapi_module

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


class ReleaseTokenRequest(BaseModel):
    token_id: str
    success: bool = True
    platform: str = ""


class BatchDeleteRequest(BaseModel):
    ids: list[str] = []


def _build_email_channel_map(channels: list[dict]) -> dict[str, dict]:
    email_to_channel: dict[str, dict] = {}
    for channel in channels:
        name = str(channel.get("name", "")).strip()
        if not name:
            continue
        email_to_channel[name] = {
            "id": channel.get("id"),
            "status": channel.get("status"),
            "other_info": channel.get("other_info"),
        }
    return email_to_channel


@router.get("")
async def list_tokens(
    platform: str = "",
    search: str = "",
    page: int = 1,
    page_size: int = 50,
    include_newapi_channel_id: bool = True,
    newApiChannelStatus: str = "",
    syncedToNewapi: str = "",
):
    if newApiChannelStatus:
        all_items, _ = token_manager.list_tokens(
            platform=platform,
            search=search,
            page=1,
            page_size=100000,
            synced_to_newapi=syncedToNewapi,
        )
        items = all_items
        total = len(all_items)
    else:
        items, total = token_manager.list_tokens(
            platform=platform,
            search=search,
            page=page,
            page_size=page_size,
            synced_to_newapi=syncedToNewapi,
        )
    need_newapi_channel_info = include_newapi_channel_id or bool(newApiChannelStatus)
    if need_newapi_channel_info and items:
        channels = await newapi_module.fetch_channels()
        email_to_channel = _build_email_channel_map(channels)
        for it in items:
            channel = email_to_channel.get((it.get("email") or "").strip()) or {}
            it["newApiChannelId"] = channel.get("id")
            it["newApiChannelStatus"] = channel.get("status")
            it["newApiChannelOtherInfo"] = channel.get("other_info")
        if newApiChannelStatus:
            items = [it for it in items if str(it.get("newApiChannelStatus")) == str(newApiChannelStatus)]
            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            items = items[start:end]
    else:
        for it in items:
            it.setdefault("newApiChannelId", None)
            it.setdefault("newApiChannelStatus", None)
            it.setdefault("newApiChannelOtherInfo", None)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/batch-delete")
async def batch_delete_tokens(body: BatchDeleteRequest, platform: str = ""):
    if not body.ids:
        return {"ok": True, "deleted_tokens": 0, "deleted_channels": 0}
    channels = await newapi_module.fetch_channels()
    email_to_channel = _build_email_channel_map(channels)
    channel_ids = []
    for token_id in body.ids:
        token = token_manager.get_token(token_id, platform)
        if token:
            cid = (email_to_channel.get((token.get("email") or "").strip()) or {}).get("id")
            if cid is not None:
                channel_ids.append(cid)
    if channel_ids:
        await newapi_module.batch_delete_channel_ids(channel_ids)
    deleted = token_manager.batch_delete_tokens(body.ids, platform)
    return {"ok": True, "deleted_tokens": deleted, "deleted_channels": len(channel_ids)}


@router.delete("/{token_id}")
async def delete_token(token_id: str, platform: str = ""):
    ok = token_manager.delete_token(token_id, platform)
    if not ok:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"ok": True}


@router.get("/export")
async def export_tokens(platform: str = ""):
    tokens = token_manager.export_tokens(platform)
    return JSONResponse(content=tokens)


@router.post("/acquire")
async def acquire_token(platform: str = "openai"):
    """
    获取一个可用的 Token

    自动标记为使用中，使用完毕后请调用 /release 释放
    """
    token = token_manager.acquire_token(platform)
    if not token:
        raise HTTPException(status_code=404, detail="无可用 Token")
    return {
        "ok": True,
        "token": {
            "id": token["id"],
            "email": token.get("email", ""),
            "platform": token.get("platform", platform),
            "access_token": token.get("access_token", ""),
            "refresh_token": token.get("refresh_token", ""),
            "used_count": token.get("used_count", 0),
        }
    }


@router.post("/release")
async def release_token(req: ReleaseTokenRequest):
    """
    释放 Token，标记为不再使用
    """
    ok = token_manager.release_token(req.token_id, req.success, req.platform)
    if not ok:
        return {"ok": False, "message": "Token 未在使用中或不存在"}
    return {"ok": True, "message": "Token 已释放"}


@router.get("/stats")
async def get_token_stats(platform: str = ""):
    """
    获取 Token 使用统计
    """
    stats = token_manager.get_usage_stats(platform)
    return stats


@router.post("/{token_id}/refresh")
async def refresh_token_route(token_id: str, platform: str = ""):
    token = token_manager.get_token(token_id, platform)
    if not token:
        raise HTTPException(status_code=404, detail="Token 不存在")
    rt = token.get("refresh_token") or ""
    if not rt:
        raise HTTPException(status_code=400, detail="无 refresh_token")
    new_data = await oauth_refresh(rt)
    if not new_data:
        raise HTTPException(status_code=502, detail="刷新 Token 失败")
    email = token.get("email", "")
    token_manager.save_token(email, new_data, platform=token.get("platform") or platform or "openai")
    return {"success": True, "message": "Token 已刷新"}
