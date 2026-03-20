import json
import os
from copy import deepcopy
from typing import Optional

from .config_defaults import (
    ACTIVE_EMAIL_FIELDS,
    CONFIG_SAVE_ORDER,
    PATH_DEFAULTS,
    get_default_config_values,
    get_default_email_presets,
)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BACKEND_DIR, "config.json")


def _apply_active_email_preset(cfg: dict) -> None:
    active_idx = cfg.get("active_email_preset", 0)
    presets = cfg.get("email_presets", [])
    if 0 <= active_idx < len(presets):
        active = presets[active_idx]
        for field in ACTIVE_EMAIL_FIELDS:
            if active.get(field) is not None:
                cfg[field] = active[field]


def _normalize_email_presets(presets: object) -> list[dict]:
    default_presets = get_default_email_presets()
    if not isinstance(presets, list) or not presets:
        return default_presets

    normalized_presets: list[dict] = []
    for idx, preset in enumerate(presets):
        preset_data = preset if isinstance(preset, dict) else {}
        base = deepcopy(default_presets[idx]) if idx < len(default_presets) else {
            "name": f"Preset {idx + 1}",
            "domain": "",
            "imap_host": "",
            "imap_port": default_presets[0]["imap_port"],
            "imap_user": "",
            "imap_pass": "",
        }
        base.update(preset_data)
        if not base.get("name"):
            base["name"] = f"Preset {idx + 1}"
        if not base.get("imap_port"):
            base["imap_port"] = default_presets[0]["imap_port"]
        normalized_presets.append(base)
    return normalized_presets


def _normalize_list(value: object) -> list:
    if isinstance(value, list):
        return list(value)
    return []


def _absolutize_paths(cfg: dict) -> None:
    for key, default in PATH_DEFAULTS.items():
        val = cfg.get(key, default)
        if not os.path.isabs(val):
            cfg[key] = os.path.join(BACKEND_DIR, val)


def _relativize_paths(cfg: dict) -> None:
    backend_prefix = BACKEND_DIR + os.sep
    for key in PATH_DEFAULTS:
        val = cfg.get(key, "")
        if isinstance(val, str) and val.startswith(backend_prefix):
            cfg[key] = val[len(backend_prefix):]


def normalize_config(cfg: Optional[dict], *, absolutize_paths: bool = False) -> dict:
    normalized = get_default_config_values()
    if cfg:
        normalized.update(deepcopy(cfg))

    normalized["proxy_pool"] = _normalize_list(normalized.get("proxy_pool"))
    normalized["aws_regions"] = _normalize_list(normalized.get("aws_regions"))
    normalized["email_presets"] = _normalize_email_presets(normalized.get("email_presets"))

    active_idx = normalized.get("active_email_preset", 0)
    if not isinstance(active_idx, int):
        active_idx = 0
    if normalized["email_presets"]:
        active_idx = max(0, min(active_idx, len(normalized["email_presets"]) - 1))
    else:
        active_idx = 0
    normalized["active_email_preset"] = active_idx

    if absolutize_paths:
        _absolutize_paths(normalized)
    _apply_active_email_preset(normalized)
    return normalized


def _order_config_for_save(cfg: dict) -> dict:
    ordered: dict = {}
    for key in CONFIG_SAVE_ORDER:
        if key in cfg:
            ordered[key] = cfg[key]
    extra_keys = sorted(k for k in cfg.keys() if k not in ordered)
    for key in extra_keys:
        ordered[key] = cfg[key]
    return ordered


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
    save_data = normalize_config(cfg, absolutize_paths=False)
    _relativize_paths(save_data)
    save_data = _order_config_for_save(save_data)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    global _config_cache
    _config_cache = normalize_config(save_data, absolutize_paths=True)


def get_config() -> dict:
    if _config_cache is None:
        return load_config()
    return _config_cache
