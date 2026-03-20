from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..log_manager import log_manager

router = APIRouter()


@router.websocket("/api/ws/logs")
async def ws_logs(ws: WebSocket):
    await log_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(ws)
    except:
        log_manager.disconnect(ws)
