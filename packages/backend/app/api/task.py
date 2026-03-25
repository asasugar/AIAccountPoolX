from fastapi import APIRouter, HTTPException

from ..platforms.registry import registry
from ..proxy_pool import proxy_pool
from ..schemas import TaskStartRequest, TaskStatusResponse, RegisterOnceRequest, RegisterOnceResponse, ProxyPoolStats

router = APIRouter(prefix="/api/task", tags=["task"])


def _get_engine(platform: str = "openai"):
    """获取平台引擎"""
    eng = registry.get(platform)
    if not eng:
        raise HTTPException(status_code=404, detail=f"平台不存在: {platform}")
    return eng


@router.post("/start")
async def start_task(req: TaskStartRequest, platform: str = "openai"):
    eng = _get_engine(platform)
    await eng.start(
        count=req.count,
        interval=req.interval,
        concurrency=req.concurrency,
        mode=req.mode,
        interval_min=req.interval_min,
        interval_max=req.interval_max,
    )
    return {"ok": True, "message": f"[{eng.platform_name}] 任务已启动"}


@router.post("/stop")
async def stop_task(platform: str = "openai"):
    eng = _get_engine(platform)
    await eng.stop()
    return {"ok": True, "message": f"[{eng.platform_name}] 任务已停止"}


@router.get("/status", response_model=TaskStatusResponse)
async def get_status(platform: str = "openai"):
    eng = _get_engine(platform)
    return eng.get_status()


@router.post("/reset")
async def reset_stats(platform: str = "openai"):
    eng = _get_engine(platform)
    eng.reset_stats()
    return {"ok": True, "message": "统计已重置"}


@router.post("/register-once", response_model=RegisterOnceResponse)
async def register_once(req: RegisterOnceRequest):
    """
    单次注册 API

    通过 API 调用触发单次账号注册，每次调用使用动态 IP。

    - 如果指定了 proxy，则使用指定的代理
    - 如果未指定 proxy，则从代理池自动获取
    - 可以指定邮箱和密码，也可以留空自动生成
    """
    eng = _get_engine(req.platform)

    # 检查引擎是否支持单次注册
    if not hasattr(eng, "register_once"):
        raise HTTPException(status_code=400, detail=f"平台 {req.platform} 不支持单次注册 API")

    result = await eng.register_once(
        proxy=req.proxy,
        email=req.email,
        password=req.password,
    )

    return RegisterOnceResponse(
        success=result["success"],
        email=result.get("email"),
        proxy_used=result.get("proxy_used"),
        message=result.get("message", ""),
    )


@router.get("/proxy-pool/stats", response_model=ProxyPoolStats)
async def get_proxy_pool_stats():
    """获取代理池统计信息"""
    return proxy_pool.get_stats()


@router.post("/proxy-pool/add")
async def add_proxy(proxy: str):
    """动态添加代理"""
    proxy_pool.add_proxy(proxy)
    return {"ok": True, "message": f"代理已添加: {proxy}"}


@router.post("/proxy-pool/remove")
async def remove_proxy(proxy: str):
    """移除代理"""
    proxy_pool.remove_proxy(proxy)
    return {"ok": True, "message": f"代理已移除: {proxy}"}
