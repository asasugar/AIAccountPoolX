import asyncio
import json
import traceback
from datetime import datetime
from typing import Optional
from fastapi import WebSocket


class LogManager:
    def __init__(self):
        self._clients: list[WebSocket] = []
        self._history: list[dict] = []
        self._max_history = 2000
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._seq = 0

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)
        for entry in self._history[-200:]:
            try:
                await ws.send_text(json.dumps(entry, ensure_ascii=False))
            except:
                break

    def disconnect(self, ws: WebSocket):
        if ws in self._clients:
            self._clients.remove(ws)

    def _build_entry(self, level: str, message: str) -> dict:
        self._seq += 1
        return {
            "id": self._seq,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "message": message,
        }

    async def _broadcast(self, entry: dict):
        text = json.dumps(entry, ensure_ascii=False)
        dead = []
        for ws in self._clients:
            try:
                await ws.send_text(text)
            except:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def _store_and_broadcast(self, entry: dict):
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(entry), self._loop)

    def info(self, msg: str):
        print(f"[INFO] {msg}")
        self._store_and_broadcast(self._build_entry("info", msg))

    def success(self, msg: str):
        print(f"[SUCCESS] {msg}")
        self._store_and_broadcast(self._build_entry("success", msg))

    def warning(self, msg: str):
        print(f"[WARN] {msg}")
        self._store_and_broadcast(self._build_entry("warning", msg))

    def error(self, msg: str):
        print(f"[ERROR] {msg}")
        self._store_and_broadcast(self._build_entry("error", msg))

    def format_exception(self, exc: BaseException) -> str:
        return repr(exc)

    def exception(self, msg: str, exc: BaseException, include_traceback: bool = False):
        detail = f"{msg}: {self.format_exception(exc)}"
        if include_traceback:
            detail = f"{detail}\n{traceback.format_exc()}"
        self.error(detail)

    def step(self, msg: str):
        print(f"[STEP] {msg}")
        self._store_and_broadcast(self._build_entry("step", msg))


log_manager = LogManager()
