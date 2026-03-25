import base64
import json
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from ...log_manager import log_manager as log


def decode_jwt_segment(seg: str) -> Dict[str, Any]:
    raw = (seg or "").strip()
    if not raw:
        return {}
    pad = "=" * ((4 - (len(raw) % 4)) % 4)
    try:
        decoded = base64.urlsafe_b64decode((raw + pad).encode("ascii"))
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return {}


def truncate_text(text: str, limit: int = 300) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def response_context(resp: httpx.Response, body_limit: int = 300) -> str:
    request = getattr(resp, "request", None)
    method = getattr(request, "method", "UNKNOWN")
    url = str(getattr(request, "url", "")) if request else ""
    body_preview = truncate_text(getattr(resp, "text", ""), limit=body_limit)
    context = f"HTTP {resp.status_code}"
    if method or url:
        context = f"{context} [{method} {url}]"
    if body_preview:
        context = f"{context} - {body_preview}"
    return context


def log_http_failure(prefix: str, resp: httpx.Response, body_limit: int = 300) -> None:
    log.error(f"{prefix}: {response_context(resp, body_limit=body_limit)}")


def extract_workspace_id(auth_cookie: str) -> tuple[bool, Optional[str]]:
    auth_json = decode_jwt_segment(auth_cookie.split(".")[0])
    workspaces = auth_json.get("workspaces") or []
    if not workspaces:
        return False, None
    workspace_id = str((workspaces[0] or {}).get("id") or "").strip()
    return True, workspace_id or None


def extract_callback_params(callback_url: str) -> tuple[Optional[str], Optional[str]]:
    parsed = urlparse(callback_url)
    params = parse_qs(parsed.query)
    return params.get("code", [None])[0], params.get("state", [None])[0]


async def follow_redirect_chain_for_callback(
    client: httpx.AsyncClient,
    url_builder,
    continue_url: str,
) -> Optional[str]:
    current_url = continue_url
    for _ in range(6):
        resp = await client.get(url_builder(current_url), follow_redirects=False)
        location = resp.headers.get("location", "")
        if resp.status_code not in [301, 302, 303, 307, 308]:
            break
        if not location:
            break
        next_url = urljoin(current_url, location)
        if "code=" in next_url and "state=" in next_url:
            return next_url
        current_url = next_url
    return None
