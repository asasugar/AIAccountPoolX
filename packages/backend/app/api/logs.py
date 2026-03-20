"""
任务日志 API
"""
from fastapi import APIRouter
from typing import Optional

from ..task_log_service import task_log_service

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
async def get_task_logs(
    platform: str = "",
    task_type: str = "",
    success: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
):
    """获取任务日志列表"""
    items, total = task_log_service.get_logs(
        platform=platform,
        task_type=task_type,
        success=success,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/stats")
async def get_task_stats(platform: str = "", days: int = 7):
    """获取任务统计"""
    return task_log_service.get_stats(platform=platform, days=days)


@router.get("/today")
async def get_today_stats(platform: str = ""):
    """获取今日统计"""
    return task_log_service.get_today_stats(platform=platform)
