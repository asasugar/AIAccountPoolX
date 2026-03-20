from fastapi import APIRouter

from ..platforms.registry import registry

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.get("")
async def list_platforms():
    return registry.list_platforms()


@router.get("/{platform_id}")
async def get_platform(platform_id: str):
    eng = registry.get(platform_id)
    if not eng:
        return {"error": "平台不存在"}
    return eng.get_status()


@router.get("/{platform_id}/config-fields")
async def get_config_fields(platform_id: str):
    eng = registry.get(platform_id)
    if not eng:
        return {"error": "平台不存在"}
    return eng.get_config_fields()
