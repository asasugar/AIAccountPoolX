from typing import Optional
from .base import BaseEngine


class PlatformRegistry:
    def __init__(self):
        self._engines: dict[str, BaseEngine] = {}

    def register(self, engine: BaseEngine):
        self._engines[engine.platform_id] = engine

    def get(self, platform_id: str) -> Optional[BaseEngine]:
        return self._engines.get(platform_id)

    def list_platforms(self) -> list[dict]:
        result = []
        for eng in self._engines.values():
            result.append({
                "id": eng.platform_id,
                "name": eng.platform_name,
                "icon": eng.platform_icon,
                "running": eng.running,
                "success_count": eng.success_count,
                "fail_count": eng.fail_count,
                "total_count": eng.total_count,
                "current_round": eng.current_round,
                "total_rounds": eng.total_rounds,
                "concurrency": eng.concurrency,
                "active_workers": eng.active_workers,
            })
        return result

    def all_engines(self) -> list[BaseEngine]:
        return list(self._engines.values())


registry = PlatformRegistry()
