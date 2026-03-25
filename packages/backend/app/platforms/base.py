import asyncio
from abc import ABC, abstractmethod
from typing import Optional


class BaseEngine(ABC):
    platform_id: str = ""
    platform_name: str = ""
    platform_icon: str = ""

    def __init__(self):
        self.running = False
        self.current_round = 0
        self.total_rounds = 0
        self.success_count = 0
        self.fail_count = 0
        self.concurrency = 1
        self.active_workers = 0
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    @property
    def total_count(self):
        return self.success_count + self.fail_count

    def get_status(self) -> dict:
        return {
            "platform": self.platform_id,
            "platform_name": self.platform_name,
            "running": self.running,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "total_count": self.total_count,
            "concurrency": self.concurrency,
            "active_workers": self.active_workers,
        }

    async def start(self, count: int = 0, interval: int = 60, concurrency: int = 1, **kwargs):
        if self.running:
            return
        self._stop_event.clear()
        self.total_rounds = count
        self.current_round = 0
        self.concurrency = max(1, int(concurrency or 1))
        self.active_workers = 0
        self._task = asyncio.create_task(self._run(count, interval, self.concurrency, **kwargs))

    async def stop(self):
        if not self.running:
            return
        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=30)
            except asyncio.TimeoutError:
                self._task.cancel()

    async def _wait_for_stop_or_timeout(self, seconds: float) -> bool:
        """Wait until a stop signal arrives or the timeout expires."""
        if seconds <= 0:
            return self._stop_event.is_set()
        if self._stop_event.is_set():
            return True
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return self._stop_event.is_set()

    def reset_stats(self):
        self.success_count = 0
        self.fail_count = 0
        self.current_round = 0

    @abstractmethod
    async def _run(self, count: int, interval: int, concurrency: int = 1, **kwargs):
        ...

    @abstractmethod
    def get_config_fields(self) -> list[dict]:
        ...

    @abstractmethod
    def get_default_config(self) -> dict:
        ...
