import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from .config import load_config
from .database import db
from .migration import check_and_migrate
from . import engine  # 确保引擎被注册
from .log_manager import log_manager
from .proxy_pool import proxy_pool
from .platforms.registry import registry
from .api import task, tokens, config_api, stats, ws, platforms, logs, accounts, newapi
from .aws_gateway import shutdown_gateway

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = load_config()
    # 初始化数据库
    db.init()
    # 检查并执行数据迁移
    check_and_migrate()
    # 初始化代理池
    proxy_pool.configure(cfg)
    log_manager.set_loop(asyncio.get_event_loop())
    log_manager.info("AIAccountPoolX 后端已启动")
    platform_names = [p["name"] for p in registry.list_platforms()]
    log_manager.info(f"已注册平台: {', '.join(platform_names)}")
    yield
    for eng in registry.all_engines():
        if eng.running:
            await eng.stop()
    await shutdown_gateway()
    log_manager.info("AIAccountPoolX 后端已关闭")


app = FastAPI(title="AIAccountPoolX", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(platforms.router)
app.include_router(task.router)
app.include_router(tokens.router)
app.include_router(accounts.router)
app.include_router(config_api.router)
app.include_router(stats.router)
app.include_router(logs.router)
app.include_router(ws.router)
app.include_router(newapi.router)


@app.get("/auth/callback")
async def oauth_callback(request: Request):
    """
    OAuth 回调端点 (纯 HTTP 模式下不再使用，保留以兼容旧流程)
    """
    params = dict(request.query_params)
    code = params.get("code")
    state_param = params.get("state")
    error_param = params.get("error")

    if error_param:
        log_manager.error(f"OAuth 回调错误: {error_param}")
        return HTMLResponse(f"<h1>授权失败: {error_param}</h1>", status_code=400)

    if not code:
        log_manager.error("回调中缺少 code")
        return HTMLResponse("<h1>Missing authorization code</h1>", status_code=400)

    log_manager.success(f"OAuth 回调收到 code (前8位: {code[:8]}...)")
    return RedirectResponse("/auth/success")


@app.get("/auth/success")
async def oauth_success():
    return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>授权成功</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;
       display: flex; justify-content: center; align-items: center;
       height: 100vh; margin: 0;
       background: linear-gradient(135deg, #28a745 0%, #20c997 100%); }
.container { text-align: center; color: white; }
h1 { font-size: 2.5rem; margin-bottom: 1rem; }
p { font-size: 1.2rem; opacity: 0.9; }
</style></head><body>
<div class="container">
  <h1>授权成功</h1>
  <p>您可以关闭此窗口</p>
</div></body></html>""")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=1455, reload=True)
