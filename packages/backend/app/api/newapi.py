from fastapi import APIRouter
from pydantic import BaseModel

from ..config import get_config
from ..services import newapi_service

router = APIRouter(prefix="/api/newapi", tags=["newapi"])


async def fetch_channels() -> list:
    return await newapi_service.fetch_channels()


async def batch_delete_channel_ids(ids: list[int]) -> None:
    await newapi_service.batch_delete_channel_ids(ids)


@router.get("/channels")
async def get_channels():
    items = await fetch_channels()
    return {"items": items}


@router.get("/channel/test/{channel_id}")
async def test_channel(channel_id: int):
    return await newapi_service.test_channel(channel_id)


class BatchChannelRequest(BaseModel):
    ids: list[int] = []


@router.post("/channel/batch")
async def batch_delete_channels(body: BatchChannelRequest):
    if not body.ids:
        return {"ok": True, "deleted": 0}
    await batch_delete_channel_ids(body.ids)
    return {"ok": True, "deleted": len(body.ids)}


@router.delete("/channel/{channel_id}")
async def delete_channel(channel_id: int):
    await newapi_service.delete_channel(channel_id)
    return {"ok": True}


class UpdateChannelRequest(BaseModel):
    channel_id: int
    token_id: str
    platform: str = "openai"


@router.put("/channel")
async def update_channel(body: UpdateChannelRequest):
    return await newapi_service.update_channel(
        channel_id=body.channel_id,
        token_id=body.token_id,
        platform=body.platform,
    )


@router.get("/sync-status")
async def get_sync_status():
    cfg = get_config()
    return newapi_service.get_sync_status(cfg)


@router.post("/sync")
async def sync_to_newapi():
    return await newapi_service.sync_to_newapi()
