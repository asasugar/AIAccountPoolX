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


def apply_active_email_preset(cfg: dict) -> None:
    active_idx = cfg.get("active_email_preset", 0)
    presets = cfg.get("email_presets", [])
    if 0 <= active_idx < len(presets):
        active = presets[active_idx]
        for field in ACTIVE_EMAIL_FIELDS:
            if active.get(field) is not None:
                cfg[field] = active[field]


def is_tempmail_preset(preset: dict) -> bool:
    preset_type = str(preset.get("email_type") or "").lower()
    preset_name = str(preset.get("name") or "").lower()
    return preset_type == "tempmail_lol" or "tempmail.lol" in preset_name


def ensure_tempmail_preset(presets: list[dict]) -> list[dict]:
    if not presets:
        return get_default_email_presets()
    for preset in presets:
        if is_tempmail_preset(preset):
            preset.setdefault("email_type", "tempmail_lol")
            preset.setdefault("tempmail_base_url", "https://api.tempmail.lol/v2")
            for other in presets:
                if other is preset:
                    continue
                if str(other.get("email_type", "")).lower() != "tempmail_lol":
                    other.pop("tempmail_base_url", None)
            return presets
    tempmail_preset = {
        "name": "Tempmail.lol",
        "email_type": "tempmail_lol",
        "domain": "",
        "imap_host": "",
        "imap_port": 993,
        "imap_user": "",
        "imap_pass": "",
        "tempmail_base_url": "https://api.tempmail.lol/v2",
    }
    return [tempmail_preset, *presets]


def normalize_email_presets(presets: object) -> list[dict]:
    default_presets = get_default_email_presets()
    if not isinstance(presets, list) or not presets:
        return default_presets

    normalized_presets: list[dict] = []
    for idx, preset in enumerate(presets):
        preset_data = preset if isinstance(preset, dict) else {}
        base = {
            "name": f"Preset {idx + 1}",
            "email_type": "imap",
            "domain": "",
            "imap_host": "",
            "imap_port": default_presets[0]["imap_port"],
            "imap_user": "",
            "imap_pass": "",
            "tempmail_base_url": "https://api.tempmail.lol/v2",
        }
        base.update(preset_data)
        if not base.get("name"):
            base["name"] = f"Preset {idx + 1}"
        if not base.get("email_type"):
            base["email_type"] = "imap"
        if not base.get("imap_port"):
            base["imap_port"] = default_presets[0]["imap_port"]
        if str(base.get("email_type", "")).lower() == "tempmail_lol":
            if not base.get("tempmail_base_url"):
                base["tempmail_base_url"] = "https://api.tempmail.lol/v2"
        else:
            base.pop("tempmail_base_url", None)
        normalized_presets.append(base)
    return ensure_tempmail_preset(normalized_presets)


def normalize_list(value: object) -> list:
    if isinstance(value, list):
        return list(value)
    return []


def absolutize_paths(cfg: dict) -> None:
    for key, default in PATH_DEFAULTS.items():
        val = cfg.get(key, default)
        if not os.path.isabs(val):
            cfg[key] = os.path.join(BACKEND_DIR, val)


def relativize_paths(cfg: dict) -> None:
    backend_prefix = BACKEND_DIR + os.sep
    for key in PATH_DEFAULTS:
        val = cfg.get(key, "")
        if isinstance(val, str) and val.startswith(backend_prefix):
            cfg[key] = val[len(backend_prefix):]


def normalize_config(
    cfg: Optional[dict],
    *,
    absolutize_config_paths: bool = False,
    apply_active_preset: bool = True,
) -> dict:
    normalized = get_default_config_values()
    has_user_active_preset = isinstance(cfg, dict) and "active_email_preset" in cfg
    if cfg:
        normalized.update(deepcopy(cfg))

    normalized["proxy_pool"] = normalize_list(normalized.get("proxy_pool"))
    normalized["aws_regions"] = normalize_list(normalized.get("aws_regions"))
    normalized["email_presets"] = normalize_email_presets(normalized.get("email_presets"))

    active_idx = normalized.get("active_email_preset", 0)
    if not isinstance(active_idx, int):
        active_idx = 0
    if normalized["email_presets"]:
        tempmail_idx = next((i for i, p in enumerate(normalized["email_presets"]) if is_tempmail_preset(p)), None)
        if has_user_active_preset:
            active_idx = max(0, min(active_idx, len(normalized["email_presets"]) - 1))
        else:
            active_idx = tempmail_idx if tempmail_idx is not None else 0
    else:
        active_idx = 0
    normalized["active_email_preset"] = active_idx

    if absolutize_config_paths:
        absolutize_paths(normalized)
    if apply_active_preset:
        apply_active_email_preset(normalized)
    else:
        normalized.pop("email_type", None)
        normalized.pop("tempmail_base_url", None)
    return normalized


def order_config_for_save(cfg: dict) -> dict:
    ordered: dict = {}
    for key in CONFIG_SAVE_ORDER:
        if key in cfg:
            ordered[key] = cfg[key]
    extra_keys = sorted(k for k in cfg.keys() if k not in ordered)
    for key in extra_keys:
        ordered[key] = cfg[key]
    return ordered
