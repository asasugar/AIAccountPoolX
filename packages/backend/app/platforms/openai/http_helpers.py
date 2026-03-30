import base64
import json
import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from ...log_manager import log_manager as log


def decode_jwt_segment(seg: str) -> list[Dict[str, Any]]:
    """尝试从完整 Cookie 或其分段中解码出 JSON。"""
    decoded_objects = []
    candidates = [seg]

    if "." in seg:
        candidates.extend(seg.split("."))

    for candidate in candidates:
        raw = (candidate or "").strip()
        if not raw:
            continue

        pad = "=" * ((4 - (len(raw) % 4)) % 4)
        try:
            decoded = base64.urlsafe_b64decode((raw + pad).encode("ascii"))
        except Exception:
            continue

        try:
            payload = json.loads(decoded.decode("utf-8"))
        except Exception:
            continue

        if isinstance(payload, dict):
            decoded_objects.append(payload)

    return decoded_objects

def extract_workspace_id_from_auth_json(auth_json: Any) -> Optional[str]:
    """从解码后的授权 JSON 中提取 Workspace ID。"""
    if isinstance(auth_json, list):
        for item in auth_json:
            workspace_id = extract_workspace_id_from_auth_json(item)
            if workspace_id:
                return workspace_id
        return None
    if not isinstance(auth_json, dict):
        return None

    workspaces = auth_json.get("workspaces") or []
    if isinstance(workspaces, list):
        for workspace in workspaces:
            if not isinstance(workspace, dict):
                continue

            workspace_id = str(workspace.get("id") or "").strip()
            if workspace_id:
                return workspace_id

    for key in (
        "workspace_id",
        "workspaceId",
        "default_workspace_id",
        "defaultWorkspaceId",
        "active_workspace_id",
        "activeWorkspaceId",
    ):
        workspace_id = str(auth_json.get(key) or "").strip()
        if workspace_id:
            return workspace_id

    for key in (
        "workspace",
        "default_workspace",
        "active_workspace",
        "defaultWorkspace",
        "activeWorkspace",
    ):
        workspace = auth_json.get(key)
        if not isinstance(workspace, dict):
            continue

        workspace_id = str(workspace.get("id") or "").strip()
        if workspace_id:
            return workspace_id

    return None

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
def extract_workspace_id_from_response_payload(payload: Any, depth: int = 0) -> Optional[str]:
    """递归扫描响应载荷中的 Workspace ID。"""
    if payload is None or depth > 5:
        return None

    if isinstance(payload, dict):
        workspace_id = extract_workspace_id_from_auth_json(payload)
        if workspace_id:
            return workspace_id
        for value in payload.values():
            workspace_id = extract_workspace_id_from_response_payload(value, depth + 1)
            if workspace_id:
                return workspace_id
        return None

    if isinstance(payload, list):
        for item in payload:
            workspace_id = extract_workspace_id_from_response_payload(item, depth + 1)
            if workspace_id:
                return workspace_id

    return None

def extract_workspace_id_from_html(html: str) -> Optional[str]:
    if not html:
        return None

    patterns = [
        r'name="workspace_id"[^>]*value="([^"]+)"',
        r"name='workspace_id'[^>]*value='([^']+)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            workspace_id = str(match.group(1) or "").strip()
            if workspace_id:
                return workspace_id
    return None

def extract_workspace_id_from_text(text: str) -> Optional[str]:
    """从 HTML/脚本文本中提取 Workspace ID。"""
    if not text:
        return None

    patterns = [
        r'"workspace_id"\s*:\s*"([^"]+)"',
        r'"workspaceId"\s*:\s*"([^"]+)"',
        r'"default_workspace_id"\s*:\s*"([^"]+)"',
        r'"defaultWorkspaceId"\s*:\s*"([^"]+)"',
        r'"active_workspace_id"\s*:\s*"([^"]+)"',
        r'"activeWorkspaceId"\s*:\s*"([^"]+)"',
        r'"workspace"\s*:\s*\{[^{}]*"id"\s*:\s*"([^"]+)"',
        r'"default_workspace"\s*:\s*\{[^{}]*"id"\s*:\s*"([^"]+)"',
        r'"active_workspace"\s*:\s*\{[^{}]*"id"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            workspace_id = str(match.group(1) or "").strip()
            if workspace_id:
                return workspace_id
    return None

def extract_workspace_id_from_url(url: str) -> Optional[str]:
    """从 URL 查询参数或片段中提取 Workspace ID。"""
    if not url:
        return None

    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    for raw_query in (parsed.query, parsed.fragment):
        query = urllib.parse.parse_qs(raw_query)
        for key in (
            "workspace_id",
            "workspaceId",
            "default_workspace_id",
            "active_workspace_id",
        ):
            values = query.get(key) or []
            if values:
                workspace_id = str(values[0] or "").strip()
                if workspace_id:
                    return workspace_id
    return None

def extract_workspace_id_from_response(
        response: Optional[Any] = None,
        html: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Optional[str]:
    """统一从响应 JSON、HTML、脚本内容和 URL 中提取 Workspace ID。"""
    response_url = str(getattr(response, "url", "") or "").strip()
    response_text = html if html is not None else str(getattr(response, "text", "") or "")
    candidate_url = url or response_url

    if response is not None:
        try:
            payload = response.json()
        except Exception:
            payload = None
        workspace_id = extract_workspace_id_from_response_payload(payload)
        if workspace_id:
            return workspace_id

    for extractor in (
        lambda: extract_workspace_id_from_html(response_text),
        lambda: extract_workspace_id_from_text(response_text),
        lambda: extract_workspace_id_from_url(candidate_url),
    ):
        workspace_id = extractor()
        if workspace_id:
            return workspace_id

    return None

def extract_workspace_id_from_cookie(auth_cookie: str) -> tuple[bool, Optional[str]]:
    auth_json = decode_jwt_segment(auth_cookie)
    workspace_id = extract_workspace_id_from_auth_json(auth_json)
    if not workspace_id:
        return False, None
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
