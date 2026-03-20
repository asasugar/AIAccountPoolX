import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx

from .log_manager import log_manager as log

# OAuth 配置常量 (导出供其他模块使用)
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTH_ENDPOINT = "https://auth.openai.com/oauth/authorize"
TOKEN_ENDPOINT = "https://auth.openai.com/oauth/token"
CALLBACK_PORT = 1455
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/auth/callback"


def generate_pkce_codes():
    verifier_bytes = secrets.token_bytes(32)
    code_verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def generate_state():
    return secrets.token_urlsafe(32)


def build_auth_url(code_challenge, state):
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "openid email profile offline_access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


async def exchange_code_for_tokens(code, code_verifier):
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    log.info("正在用 authorization code 兑换 Token...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TOKEN_ENDPOINT,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
    if resp.status_code != 200:
        log.error(f"Token 兑换失败: HTTP {resp.status_code} - {resp.text[:500]}")
        return None
    token_data = resp.json()
    log.success("Token 兑换成功！")
    return token_data


async def refresh_access_token(refresh_token: str):
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
        "scope": "openid profile email",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TOKEN_ENDPOINT,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
    if resp.status_code != 200:
        return None
    return resp.json()
