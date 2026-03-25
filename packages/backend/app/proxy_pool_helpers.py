import random
from typing import Optional

from .config_defaults import PROXY_SCHEMES


def get_nested_json_value(data: object, field_path: str) -> Optional[str]:
    current = data
    for field in field_path.split("."):
        current = current.get(field, {}) if isinstance(current, dict) else None
    if current is None:
        return None
    value = str(current).strip()
    return value or None


def ensure_proxy_scheme(proxy: str, protocol: str) -> str:
    if not proxy.startswith(PROXY_SCHEMES):
        return protocol + proxy
    return proxy


def select_proxy_by_strategy(available: list, strategy: str, current_index: int) -> tuple[object, int]:
    if strategy == "random":
        return random.choice(available), current_index
    if strategy == "least_used":
        return min(available, key=lambda p: p.used_count), current_index
    idx = current_index % len(available)
    return available[idx], current_index + 1
