from fastapi import APIRouter

from ..platforms.registry import registry
from ..token_manager import token_manager

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats(platform: str = ""):
    tokens, total_tokens = token_manager.list_tokens(platform, page_size=10000)
    active_count = sum(1 for t in tokens if t.get("status") == "active")

    total_success = 0
    total_fail = 0
    running = False

    if platform:
        eng = registry.get(platform)
        if eng:
            total_success = eng.success_count
            total_fail = eng.fail_count
            running = eng.running
    else:
        for eng in registry.all_engines():
            total_success += eng.success_count
            total_fail += eng.fail_count
            if eng.running:
                running = True

    return {
        "success_count": total_success,
        "fail_count": total_fail,
        "total_count": total_success + total_fail,
        "token_count": total_tokens,
        "active_token_count": active_count,
        "running": running,
        "platforms": registry.list_platforms(),
    }
