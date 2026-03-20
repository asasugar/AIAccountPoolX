from fastapi import APIRouter

from ..config import get_config, save_config, load_config
from ..schemas import ConfigModel

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def get_current_config():
    return get_config()


@router.put("")
async def update_config(cfg: ConfigModel):
    current = get_config()
    for k, v in cfg.model_dump().items():
        current[k] = v
    save_config(current)
    load_config()
    return {"ok": True, "message": "配置已更新"}
