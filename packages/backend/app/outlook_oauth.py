import base64
import imaplib
import os
import ssl
import time
from typing import Optional

import msal

AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPES = ["https://outlook.office.com/IMAP.AccessAsUser.All"]

_token_cache: dict = {}


def _get_app(client_id: str) -> msal.PublicClientApplication:
    return msal.PublicClientApplication(client_id, authority=AUTHORITY)


def get_access_token(client_id: str, refresh_token: str) -> Optional[str]:
    """用 refresh_token 换取 access_token"""
    cached = _token_cache.get(client_id)
    if cached and cached["expires_at"] - time.time() > 60:
        return cached["access_token"]

    app = _get_app(client_id)
    result = app.acquire_token_by_refresh_token(refresh_token, scopes=SCOPES)
    if "access_token" not in result:
        raise RuntimeError(f"刷新 token 失败: {result.get('error_description', result)}")

    _token_cache[client_id] = {
        "access_token": result["access_token"],
        "expires_at": time.time() + result.get("expires_in", 3600),
    }
    return result["access_token"]


def build_xoauth2_string(user: str, access_token: str) -> bytes:
    # imaplib.authenticate 会自动 base64，这里返回原始字节
    auth_string = f"user={user}\x01auth=Bearer {access_token}\x01\x01"
    return auth_string.encode()


def imap_login_oauth2(user: str, client_id: str, refresh_token: str) -> imaplib.IMAP4_SSL:
    """返回已通过 XOAUTH2 认证的 IMAP4_SSL 连接"""
    access_token = get_access_token(client_id, refresh_token)
    xoauth2 = build_xoauth2_string(user, access_token)

    ctx = ssl.create_default_context()
    m = imaplib.IMAP4_SSL("outlook.office365.com", 993, ssl_context=ctx)
    m.authenticate("XOAUTH2", lambda _: xoauth2)
    return m


def device_code_flow(client_id: str) -> dict:
    """发起 Device Code Flow，返回包含 refresh_token 的结果"""
    app = _get_app(client_id)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"无法发起 Device Code Flow: {flow}")
    print("\n" + "=" * 50)
    print(flow["message"])
    print("=" * 50 + "\n")
    result = app.acquire_token_by_device_flow(flow)
    if "refresh_token" not in result:
        raise RuntimeError(f"授权失败: {result.get('error_description', result)}")
    return result
