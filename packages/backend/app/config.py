import json
import os
from typing import Optional

from .config_utils import (
    BACKEND_DIR,
    normalize_config as _normalize_config,
    order_config_for_save,
    relativize_paths,
)

CONFIG_PATH = os.getenv("AIACCOUNTPOOLX_CONFIG_PATH", os.path.join(BACKEND_DIR, "config.json"))


def normalize_config(
    cfg: Optional[dict],
    *,
    absolutize_paths: bool = False,
    apply_active_preset: bool = True,
) -> dict:
    return _normalize_config(
        cfg,
        absolutize_config_paths=absolutize_paths,
        apply_active_preset=apply_active_preset,
    )


def _read_raw_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

_config_cache: Optional[dict] = None


def load_config() -> dict:
    global _config_cache
    raw_cfg = _read_raw_config()
    cfg = normalize_config(raw_cfg, absolutize_paths=True)
    _config_cache = cfg
    return cfg


def save_config(cfg: dict):
    save_data = normalize_config(cfg, absolutize_paths=False, apply_active_preset=False)
    relativize_paths(save_data)
    save_data = order_config_for_save(save_data)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    global _config_cache
    _config_cache = normalize_config(save_data, absolutize_paths=True)


def get_config() -> dict:
    if _config_cache is None:
        return load_config()
    return _config_cache
