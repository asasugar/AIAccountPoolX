import asyncio
import base64
import json
import random
import string
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urljoin, urlparse, parse_qs

import anyio
import httpx

try:
    from httpx_socks import AsyncProxyTransport
except ImportError:
    AsyncProxyTransport = None

from ...config import get_config
from ...database import db, Account
from ...email_util import get_verification_code, generate_email, create_tempmail_inbox
from ...log_manager import log_manager as log
from ...oauth import (
    generate_pkce_codes, generate_state,
    CLIENT_ID, AUTH_ENDPOINT, TOKEN_ENDPOINT, REDIRECT_URI,
)
from ...proxy_pool import proxy_pool
from ...token_manager import token_manager
from ...aws_gateway import get_gateway
from ..base import BaseEngine


AUTH_BASE = "https://auth.openai.com"
SENTINEL_API = "https://sentinel.openai.com/backend-api/sentinel/req"
API_AUTHORIZE_CONTINUE = f"{AUTH_BASE}/api/accounts/authorize/continue"
API_USER_REGISTER = f"{AUTH_BASE}/api/accounts/user/register"
SEND_EMAIL_OTP = f"{AUTH_BASE}/api/accounts/email-otp/send"
API_EMAIL_OTP_VALIDATE = f"{AUTH_BASE}/api/accounts/email-otp/validate"
API_CREATE_ACCOUNT = f"{AUTH_BASE}/api/accounts/create_account"
API_WORKSPACE_SELECT = f"{AUTH_BASE}/api/accounts/workspace/select"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Ch-Ua": '"Chromium";v="145", "Not:A-Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
}

IP_CHECK_URLS = (
    "https://api.ipify.org?format=json",
    "http://ifconfig.me/ip",
    "http://checkip.amazonaws.com",
)
REGISTRATION_EXECUTOR = ThreadPoolExecutor(max_workers=50)


class OpenAIEngine(BaseEngine):
    platform_id = "openai"
    platform_name = "OpenAI"
    platform_icon = "🌐"

    @staticmethod
    def _decode_jwt_segment(seg: str) -> Dict[str, Any]:
        raw = (seg or "").strip()
        if not raw:
            return {}
        pad = "=" * ((4 - (len(raw) % 4)) % 4)
        try:
            decoded = base64.urlsafe_b64decode((raw + pad).encode("ascii"))
            return json.loads(decoded.decode("utf-8"))
        except Exception:
            return {}

    def __init__(self):
        super().__init__()
        # 记录最近一次注册产生的账号信息，便于外部查询或排障
        self._last_registered_email: Optional[str] = None
        self._last_registered_password: Optional[str] = None
        # 并发轮次分配锁，确保多 worker 不会拿到重复轮次
        self._round_lock = asyncio.Lock()
        self._counter_lock = asyncio.Lock()
        self._next_round_index = 0

    def get_config_fields(self) -> list[dict]:
        # Web 配置页展示字段
        return [
            {"key": "domain", "label": "邮箱域名", "type": "text", "required": True},
            {"key": "imap_host", "label": "IMAP 主机", "type": "text", "required": True},
            {"key": "imap_port", "label": "IMAP 端口", "type": "number", "default": 993},
            {"key": "imap_user", "label": "IMAP 用户名", "type": "text", "required": True},
            {"key": "imap_pass", "label": "IMAP 密码", "type": "password", "required": True},
            {"key": "email_prefix", "label": "邮箱前缀", "type": "text", "default": "auto"},
            {"key": "proxy", "label": "代理服务器", "type": "text"},
        ]

    def get_default_config(self) -> dict:
        # 引擎默认配置（可被配置文件覆盖）
        return {
            "domain": "",
            "imap_host": "",
            "imap_port": 993,
            "imap_user": "",
            "imap_pass": "",
            "email_prefix": "auto",
            "proxy": None,
        }

    def _save_account_to_db(
        self,
        email: str,
        name: str,
        birthdate: str,
        proxy: Optional[str] = None,
    ) -> None:
        """保存账号信息到数据库"""
        try:
            # 解析 birthdate (格式: YYYY-MM-DD)
            birth_year, birth_month, birth_day = None, None, None
            if birthdate and len(birthdate.split("-")) == 3:
                parts = birthdate.split("-")
                birth_year = int(parts[0])
                birth_month = int(parts[1])
                birth_day = int(parts[2])

            with db.get_session() as session:
                # 检查账号是否已存在
                existing = session.query(Account).filter(
                    Account.platform == "openai",
                    Account.email == email
                ).first()

                if existing:
                    log.info(f"[OpenAI] 账号已存在，跳过保存: {email}")
                    return

                # 创建新账号记录（当前流程为无密码模式）
                account = Account(
                    platform="openai",
                    email=email,
                    password=None,  # 无密码模式
                    username=None,
                    first_name=name,
                    last_name=None,
                    birth_year=birth_year,
                    birth_month=birth_month,
                    birth_day=birth_day,
                    register_ip=proxy,
                    status="active",
                    verified=True,
                )
                session.add(account)
                log.success(f"[OpenAI] 账号信息已保存到数据库: {email}")
        except Exception as e:
            log.exception("[OpenAI] 保存账号信息失败", e)

    def _build_auth_url(self, code_challenge: str, state: str) -> str:
        """构建 OAuth 授权 URL"""
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

    @staticmethod
    def _truncate_text(text: str, limit: int = 300) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit]}..."

    @classmethod
    def _response_context(cls, resp: httpx.Response, body_limit: int = 300) -> str:
        request = getattr(resp, "request", None)
        method = getattr(request, "method", "UNKNOWN")
        url = str(getattr(request, "url", "")) if request else ""
        body_preview = cls._truncate_text(getattr(resp, "text", ""), limit=body_limit)
        context = f"HTTP {resp.status_code}"
        if method or url:
            context = f"{context} [{method} {url}]"
        if body_preview:
            context = f"{context} - {body_preview}"
        return context

    @classmethod
    def _log_http_failure(cls, prefix: str, resp: httpx.Response, body_limit: int = 300) -> None:
        log.error(f"{prefix}: {cls._response_context(resp, body_limit=body_limit)}")

    async def _claim_round(self, count: int) -> Optional[int]:
        # 为 worker 申请一个新的执行轮次；count=0 表示无限轮次
        async with self._round_lock:
            if self._stop_event.is_set():
                return None
            if count != 0 and self._next_round_index >= count:
                return None
            self._next_round_index += 1
            self.current_round = self._next_round_index
            return self._next_round_index

    async def _has_more_rounds(self, count: int) -> bool:
        # 判断有限任务模式下是否还有剩余轮次
        if count == 0:
            return True
        async with self._round_lock:
            return self._next_round_index < count

    async def _sleep_with_stop(self, seconds: int) -> None:
        # 可中断等待：停机时提前结束 sleep
        await self._wait_for_stop_or_timeout(seconds)

    async def _run_round(self, cfg: dict, round_no: int, worker_id: int) -> None:
        # 每一轮独立解析代理，避免固定代理连续失败影响全局
        proxy = await self._resolve_proxy(cfg)

        try:
            ok = await self._register_via_api(cfg, proxy)
            if ok:
                self.success_count += 1
                if proxy:
                    proxy_pool.report_success(proxy)
            else:
                self.fail_count += 1
                if proxy:
                    proxy_pool.report_failure(proxy)
        except Exception as e:
            log.exception(f"[OpenAI][Worker {worker_id}] 第 {round_no} 轮异常", e)
            self.fail_count += 1

    def _run_sync_registration_task(self, cfg: dict, proxy: Optional[str]) -> bool:
        try:
            return asyncio.run(self._register_via_api(cfg, proxy))
        except Exception as e:
            log.exception("[OpenAI] 线程任务执行异常", e)
            return False

    async def run_registration_task(self, cfg: dict, round_no: int) -> None:
        if self._stop_event.is_set():
            return

        proxy = await self._resolve_proxy(cfg)
        loop = asyncio.get_running_loop()
        ok = await loop.run_in_executor(
            REGISTRATION_EXECUTOR,
            self._run_sync_registration_task,
            cfg,
            proxy,
        )
        async with self._counter_lock:
            self.current_round = round_no
            if ok:
                self.success_count += 1
            else:
                self.fail_count += 1
        if proxy:
            if ok:
                proxy_pool.report_success(proxy)
            else:
                proxy_pool.report_failure(proxy)

    async def run_batch_parallel(self, cfg: dict, count: int, concurrency: int) -> None:
        semaphore = asyncio.Semaphore(max(1, concurrency))
        total = count if count > 0 else 0
        if total <= 0:
            return

        async def _one_task(round_no: int):
            async with semaphore:
                if self._stop_event.is_set():
                    return
                self.active_workers += 1
                try:
                    await self.run_registration_task(cfg, round_no)
                finally:
                    self.active_workers = max(0, self.active_workers - 1)

        tasks = [asyncio.create_task(_one_task(i)) for i in range(1, total + 1)]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def run_batch_pipeline(
        self,
        cfg: dict,
        count: int,
        concurrency: int,
        interval_min: int,
        interval_max: int,
    ) -> None:
        semaphore = asyncio.Semaphore(max(1, concurrency))
        tasks: list[asyncio.Task] = []
        round_no = 0
        min_interval = max(0, int(interval_min))
        max_interval = max(min_interval, int(interval_max))

        async def _pipeline_task(task_round: int):
            self.active_workers += 1
            try:
                await self.run_registration_task(cfg, task_round)
            finally:
                self.active_workers = max(0, self.active_workers - 1)
                semaphore.release()

        while not self._stop_event.is_set():
            if count > 0 and round_no >= count:
                break
            await semaphore.acquire()
            if self._stop_event.is_set():
                semaphore.release()
                break
            round_no += 1
            tasks.append(asyncio.create_task(_pipeline_task(round_no)))
            if max_interval > 0:
                wait_seconds = random.randint(min_interval, max_interval)
                if await self._wait_for_stop_or_timeout(wait_seconds):
                    break

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def run_batch_registration(
        self,
        cfg: dict,
        count: int,
        concurrency: int,
        mode: str,
        interval_min: int,
        interval_max: int,
    ) -> None:
        mode_text = str(mode or "parallel").lower()
        if mode_text == "pipeline":
            await self.run_batch_pipeline(
                cfg=cfg,
                count=count,
                concurrency=concurrency,
                interval_min=interval_min,
                interval_max=interval_max,
            )
        else:
            await self.run_batch_parallel(
                cfg=cfg,
                count=count,
                concurrency=concurrency,
            )

    async def _resolve_proxy(self, cfg: dict, preferred_proxy: Optional[str] = None) -> Optional[str]:
        # 代理优先级：显式传入 > 代理池 > 配置文件静态代理
        if preferred_proxy:
            return preferred_proxy
        proxy = await proxy_pool.get_proxy()
        if proxy:
            return proxy
        return cfg.get("proxy", None)

    def _build_transport(self, proxy: Optional[str]) -> tuple[dict, Optional[AsyncProxyTransport]]:
        # 根据代理协议构建 httpx 传输参数
        transport_kwargs = {}
        socks_transport = None
        if not proxy:
            return transport_kwargs, socks_transport

        log.info(f"[OpenAI] 使用代理: {proxy}")
        if proxy.startswith(("socks5://", "socks4://")):
            if AsyncProxyTransport is None:
                raise RuntimeError("使用 SOCKS 代理需安装: pip install httpx-socks[asyncio]")
            # SOCKS 走自定义 transport
            socks_transport = AsyncProxyTransport.from_url(proxy)
        else:
            # HTTP/HTTPS 走 httpx 原生 proxy 参数
            transport_kwargs["proxy"] = proxy
        return transport_kwargs, socks_transport

    @staticmethod
    def _apply_socks_transport(client_kwargs: dict, socks_transport: Optional[AsyncProxyTransport]) -> dict:
        # 仅在 SOCKS 模式下注入 transport，避免与常规代理参数冲突
        if socks_transport is None:
            return client_kwargs
        updated_kwargs = dict(client_kwargs)
        updated_kwargs["transport"] = socks_transport
        updated_kwargs["limits"] = httpx.Limits(max_keepalive_connections=0)
        return updated_kwargs

    async def _fetch_real_ip(self, transport_kwargs: dict, socks_transport: Optional[AsyncProxyTransport]) -> str:
        # 用多种 IP 查询端点确认当前出口 IP，便于排查代理生效情况
        try:
            ip_client_kw = self._apply_socks_transport(
                dict(timeout=5.0, **transport_kwargs),
                socks_transport,
            )
            async with httpx.AsyncClient(**ip_client_kw) as ip_client:
                for ip_url in IP_CHECK_URLS:
                    try:
                        ip_resp = await ip_client.get(ip_url, timeout=4.0)
                        real_ip = ip_resp.json().get("ip", "") if "json" in ip_url else ip_resp.text.strip()
                        if real_ip:
                            return real_ip
                    except Exception:
                        continue
        except Exception as e:
            return f"获取失败: {e}"
        return "获取失败"

    async def _request_with_retries(
        self,
        request_fn,
        *,
        attempts: int,
        retry_exceptions: tuple[type[BaseException], ...],
        on_retry_message,
        sleep_seconds,
    ):
        # 通用异步重试器：仅捕获指定异常类型，达到最大次数后抛出
        for attempt in range(attempts):
            try:
                return await request_fn()
            except retry_exceptions as e:
                if attempt >= attempts - 1:
                    raise
                # 失败后按调用方定义的退避时间等待，再继续重试
                log.info(on_retry_message(attempt, e))
                await asyncio.sleep(sleep_seconds(attempt))

    async def _wait_for_email_otp(
        self,
        cfg: dict,
        email: str,
        tempmail_token: str = "",
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        # 这里不再做外层多轮等待，直接交给 email_util 内部轮询到超时
        if self._stop_event.is_set():
            log.info("[OpenAI] 任务已停止")
            return None
        otp = await get_verification_code(
            email,
            cfg["imap_host"],
            cfg["imap_port"],
            cfg["imap_user"],
            cfg["imap_pass"],
            timeout=int(cfg.get("email_otp_timeout", 120)),
            outlook_client_id=cfg.get("outlook_client_id", ""),
            outlook_refresh_token=cfg.get("outlook_refresh_token", ""),
            stop_event=self._stop_event,
            email_type=cfg.get("email_type", "imap"),
            tempmail_token=tempmail_token,
            tempmail_base_url=cfg.get("tempmail_base_url", "https://api.tempmail.lol/v2"),
            otp_sent_at=otp_sent_at,
        )
        if otp:
            # 只要拿到验证码就立刻返回给后续校验步骤
            log.success(f"[OpenAI] 获取到验证码: {otp}")
            return otp
        return None

    @staticmethod
    def _extract_workspace_id(auth_cookie: str) -> tuple[bool, Optional[str]]:
        auth_json = OpenAIEngine._decode_jwt_segment(auth_cookie.split(".")[0])
        workspaces = auth_json.get("workspaces") or []
        if not workspaces:
            return False, None
        workspace_id = str((workspaces[0] or {}).get("id") or "").strip()
        return True, workspace_id or None

    @staticmethod
    def _extract_callback_params(callback_url: str) -> tuple[Optional[str], Optional[str]]:
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)
        return params.get("code", [None])[0], params.get("state", [None])[0]

    async def _follow_redirect_chain_for_callback(self, client: httpx.AsyncClient, url_builder, continue_url: str) -> Optional[str]:
        # 手动跟踪有限次重定向，直到捕获包含 code/state 的 callback URL
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

    async def _run(
        self,
        count: int,
        interval: int,
        concurrency: int = 1,
        mode: str = "parallel",
        interval_min: int = 0,
        interval_max: int = 0,
        **kwargs,
    ):
        """批量注册任务"""
        self.running = True
        cfg = get_config()
        self._next_round_index = 0
        self.active_workers = 0
        self.current_round = 0

        selected_mode = str(mode or "parallel").lower()
        if selected_mode != "pipeline":
            selected_mode = "parallel"

        if selected_mode == "pipeline":
            pipe_min = int(interval_min or 0)
            pipe_max = int(interval_max or 0)
            if pipe_max <= 0:
                pipe_max = int(interval or 0)
            if pipe_min <= 0:
                pipe_min = min(pipe_max, int(interval or 0)) if pipe_max > 0 else 0
        else:
            pipe_min = 0
            pipe_max = 0
            if count == 0:
                selected_mode = "pipeline"
                pipe_min = max(0, int(interval or 0))
                pipe_max = pipe_min

        log.info(
            f"[OpenAI] 批量注册启动: 共 {'无限' if count == 0 else count} 次, "
            f"模式 {selected_mode}, 并发 {concurrency}"
        )

        try:
            await self.run_batch_registration(
                cfg=cfg,
                count=count,
                concurrency=max(1, int(concurrency or 1)),
                mode=selected_mode,
                interval_min=pipe_min,
                interval_max=pipe_max,
            )

        except Exception as e:
            log.exception("[OpenAI] 引擎异常退出", e, include_traceback=True)
        finally:
            # 无论成功失败都重置运行态
            self.running = False
            self.active_workers = 0
            log.info(f"[OpenAI] 任务结束 - 成功: {self.success_count}, 失败: {self.fail_count}")

    async def register_once(
        self,
        proxy: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict:
        """单次注册 API"""
        cfg = get_config()

        # 单次注册也复用批量流程的代理解析逻辑
        used_proxy = await self._resolve_proxy(cfg, proxy)

        resolved_email = email or generate_email(cfg)

        log.info("[OpenAI] " + "=" * 40)
        log.info("[OpenAI] API 触发单次注册 (HTTP 模式)")
        if used_proxy:
            log.info(f"[OpenAI] 使用代理: {used_proxy}")

        try:
            result = await self._register_via_api(
                cfg,
                used_proxy,
                custom_email=resolved_email,
                custom_password=password,
            )
            if result:
                if used_proxy:
                    proxy_pool.report_success(used_proxy)
                return {
                    "success": True,
                    "email": resolved_email,
                    "proxy_used": used_proxy,
                    "message": "注册成功",
                }
            else:
                if used_proxy:
                    proxy_pool.report_failure(used_proxy)
                return {
                    "success": False,
                    "email": None,
                    "proxy_used": used_proxy,
                    "message": "注册失败",
                }
        except Exception as e:
            log.exception("[OpenAI] 单次注册异常", e)
            return {
                "success": False,
                "email": None,
                "proxy_used": used_proxy,
                "message": f"注册异常: {str(e)}",
            }

    async def _get_sentinel_header(self, client: httpx.AsyncClient, device_id: str) -> Optional[str]:
        try:
            sen_payload = json.dumps({"p": "", "id": device_id, "flow": "authorize_continue"})
            resp = await client.post(
                SENTINEL_API,
                content=sen_payload,
                headers={
                    "Content-Type": "text/plain;charset=UTF-8",
                    "Origin": "https://sentinel.openai.com",
                    "Referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                },
            )
            if resp.status_code != 200:
                log.error(f"[OpenAI] Sentinel 异常: HTTP {resp.status_code}")
                return None
            sen_token = resp.json().get("token", "")
            sentinel = json.dumps({"p": "", "t": "", "c": sen_token, "id": device_id, "flow": "authorize_continue"})
            log.success("[OpenAI] Sentinel token 获取成功")
            return sentinel
        except Exception as e:
            log.exception("[OpenAI] Sentinel 异常", e)
            return None

    async def _register_via_api(
        self,
        cfg: dict,
        proxy: Optional[str] = None,
        custom_email: Optional[str] = None,
        custom_password: Optional[str] = None,
    ) -> bool:
        # 生成 OAuth PKCE 参数，后续 token 兑换时需要回填 verifier
        code_verifier, code_challenge = generate_pkce_codes()
        state = generate_state()
        auth_url = self._build_auth_url(code_challenge, state)

        log.info("[OpenAI] " + "=" * 40)
        log.info("[OpenAI] 开始 HTTP 接口注册流程 (无密码模式)")

        tempmail_token = ""
        email_type = str(cfg.get("email_type", "imap")).lower()
        if custom_email:
            email = custom_email
        elif email_type == "tempmail_lol":
            email, tempmail_token = await create_tempmail_inbox(
                cfg.get("tempmail_base_url", "https://api.tempmail.lol/v2")
            )
            if not email or not tempmail_token:
                log.error("[OpenAI] Tempmail.lol 创建邮箱失败")
                return False
        else:
            email = generate_email(cfg)
        name = "".join(random.choices(string.ascii_letters, k=random.randint(5, 8))).capitalize()

        self._last_registered_email = email
        log.info(f"[OpenAI] 注册邮箱: {email}")

        try:
            transport_kwargs, socks_transport = self._build_transport(proxy)
        except RuntimeError as e:
            log.error(f"[OpenAI] {e}")
            return False

        gateway = await get_gateway(cfg) if not proxy else None
        if gateway:
            base_url = gateway.get_random_endpoint()
            log.info(f"[OpenAI] 使用 AWS Gateway: {base_url}")
        else:
            base_url = None

        extra_headers = dict(BASE_HEADERS)
        if base_url:
            extra_headers["X-Forwarded-For"] = "1.1.1.1"

        client_kwargs = dict(
            timeout=30.0,
            follow_redirects=True,
            headers=extra_headers,
            **transport_kwargs,
        )
        client_kwargs = self._apply_socks_transport(client_kwargs, socks_transport)
        if base_url:
            client_kwargs["base_url"] = base_url.rstrip("/") + "/"

        # 当使用 gateway 时，将绝对 URL 映射为相对路径，统一走 base_url
        def _url(absolute_url: str) -> str:
            if base_url and absolute_url.startswith(AUTH_BASE):
                return absolute_url[len(AUTH_BASE):].lstrip("/")
            return absolute_url

        async with httpx.AsyncClient(
            **client_kwargs,
        ) as client:
            try:
                real_ip = await self._fetch_real_ip(transport_kwargs, socks_transport)
                log.info(f"[OpenAI] 当前出口 IP: {real_ip}")

                # Step 1: 访问授权页面，获取 session 和 oai-did
                log.step("[OpenAI] Step 1: 访问授权页面...")
                _step1_url = _url(auth_url)
                log.info(f"[OpenAI] Step 1 实际请求 URL: {_step1_url[:80]}...")
                resp = await self._request_with_retries(
                    lambda: client.get(_step1_url),
                    attempts=3,
                    retry_exceptions=(httpx.ConnectError, httpx.ConnectTimeout),
                    on_retry_message=lambda attempt, e: f"[OpenAI] Step 1 连接失败，{2 - attempt} 秒后重试: {e}",
                    sleep_seconds=lambda _: 2,
                )
                if resp.status_code not in [200, 302]:
                    self._log_http_failure("[OpenAI] 访问授权页面失败", resp, body_limit=200)
                    return False

                device_id = client.cookies.get("oai-did")
                if not device_id:
                    device_id = str(uuid.uuid4())
                    client.cookies.set("oai-did", device_id, domain=".openai.com")
                log.success(f"[OpenAI] Device ID: {device_id}")

                # Step 2: 获取 Sentinel Token (简单模式，与 auto.py 一致)
                log.step("[OpenAI] Step 2: 获取 Sentinel Token...")
                sentinel = await self._get_sentinel_header(client, device_id)
                if not sentinel:
                    return False

                # Step 3: 提交注册表单 (邮箱 + signup)
                log.step("[OpenAI] Step 3: 提交注册表单...")
                signup_body = json.dumps({"username": {"value": email, "kind": "email"}, "screen_hint": "signup"})
                resp = await client.post(
                    _url(API_AUTHORIZE_CONTINUE),
                    content=signup_body,
                    headers={
                        "Referer": f"{AUTH_BASE}/create-account",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "openai-sentinel-token": sentinel,
                    },
                )
                if resp.status_code != 200:
                    self._log_http_failure("[OpenAI] 提交注册表单失败", resp)
                    return False
                log.success(f"[OpenAI] 注册表单已提交: {resp.status_code}")

                # Step 4: 提交密码注册
                log.step("[OpenAI] Step 4: 提交密码...")
                password = custom_password if custom_password else f"Aa1!{''.join(random.choices(string.ascii_letters + string.digits, k=12))}"
                self._last_registered_password = password
                log.info(f"[OpenAI] 生成密码: {password}")
                resp = await client.post(
                    _url(API_USER_REGISTER),
                    content=json.dumps({"password": password}),
                    headers={
                        "Referer": f"{AUTH_BASE}/create-account/password",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code != 200:
                    self._log_http_failure("[OpenAI] 密码提交失败", resp)
                    return False
                log.success(f"[OpenAI] 密码已提交: {resp.status_code}")

                # Step 4.5: 发送验证码
                log.step("[OpenAI] Step 4.5: 发送验证码...")
                sentinel = await self._get_sentinel_header(client, device_id)
                if not sentinel:
                    return False
                otp_sent_at = time.time()
                resp = await client.post(
                    _url(SEND_EMAIL_OTP),
                    content=json.dumps({}),
                    headers={
                        "Referer": f"{AUTH_BASE}/email-verification",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "openai-sentinel-token": sentinel,
                    },
                )

                # Step 5: 获取邮箱验证码（IMAP/Tempmail 内部负责轮询与超时）
                log.step("[OpenAI] Step 5: 等待邮箱验证码...")
                otp = await self._wait_for_email_otp(
                    cfg,
                    email,
                    tempmail_token=tempmail_token,
                    otp_sent_at=otp_sent_at,
                )
                if not otp:
                    log.error("[OpenAI] 未获取到邮箱验证码")
                    return False

                log.step("[OpenAI] Step 6: 校验验证码...")
                resp = await self._request_with_retries(
                    lambda: client.post(
                        _url(API_EMAIL_OTP_VALIDATE),
                        content=json.dumps({"code": otp}),
                        headers={
                            "Referer": f"{AUTH_BASE}/email-verification",
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                        },
                    ),
                    attempts=4,
                    retry_exceptions=(
                        anyio.EndOfStream,
                        httpx.ConnectError,
                        httpx.ConnectTimeout,
                        httpx.ReadError,
                    ),
                    on_retry_message=lambda attempt, e: f"[OpenAI] Step 6 连接异常重试 ({attempt + 1}/4): {e}",
                    sleep_seconds=lambda attempt: 2 + attempt,
                )
                if resp.status_code != 200:
                    self._log_http_failure("[OpenAI] 验证码校验失败", resp)
                    return False
                log.success(f"[OpenAI] 验证码校验通过: {resp.status_code}")

                # Step 7: 创建账户 (提交个人信息)
                log.step("[OpenAI] Step 7: 创建账户...")
                birth_year = random.randint(1985, 2005)
                birthdate = f"{birth_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
                resp = await client.post(
                    _url(API_CREATE_ACCOUNT),
                    content=json.dumps({"name": name, "birthdate": birthdate}),
                    headers={
                        "Referer": f"{AUTH_BASE}/about-you",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code != 200:
                    self._log_http_failure("[OpenAI] 账户创建失败", resp)
                    return False
                log.success(f"[OpenAI] 账户已创建: {name}, {birthdate}")

                # Step 8: 解析 workspace 并选择
                log.step("[OpenAI] Step 8: 选择 Workspace...")
                auth_cookie = client.cookies.get("oai-client-auth-session")
                if not auth_cookie:
                    log.error("[OpenAI] 未能获取到授权 Cookie")
                    return False

                has_workspaces, workspace_id = self._extract_workspace_id(auth_cookie)
                if not has_workspaces:
                    log.error("[OpenAI] 授权 Cookie 里没有 workspace 信息")
                    return False
                if not workspace_id:
                    log.error("[OpenAI] 无法解析 workspace_id")
                    return False

                resp = await client.post(
                    _url(API_WORKSPACE_SELECT),
                    content=json.dumps({"workspace_id": workspace_id}),
                    headers={
                        "Referer": f"{AUTH_BASE}/sign-in-with-chatgpt/codex/consent",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code != 200:
                    self._log_http_failure("[OpenAI] workspace select 失败", resp)
                    return False

                continue_url = str((resp.json() or {}).get("continue_url") or "").strip()
                if not continue_url:
                    log.error("[OpenAI] workspace/select 响应缺少 continue_url")
                    return False
                log.success(f"[OpenAI] Workspace 已选择, continue_url 已获取")

                # Step 9: 手动跟踪重定向链，捕获 callback URL
                log.step("[OpenAI] Step 9: 跟踪重定向获取 Callback...")
                callback_url = await self._follow_redirect_chain_for_callback(client, _url, continue_url)
                if not callback_url:
                    log.error("[OpenAI] 未能在重定向链中捕获 Callback URL")
                    return False

                # Step 10: 从 callback URL 提取 code 并换取 Token
                log.step("[OpenAI] Step 10: 换取 Token...")
                auth_code, callback_state = self._extract_callback_params(callback_url)

                if not auth_code:
                    log.error("[OpenAI] callback URL 中无 code")
                    return False
                if callback_state != state:
                    log.error(f"[OpenAI] state 不匹配: 期望={state}, 实际={callback_state}")
                    return False

                resp = await client.post(
                    _url(TOKEN_ENDPOINT),
                    data={
                        "grant_type": "authorization_code",
                        "client_id": CLIENT_ID,
                        "code": auth_code,
                        "redirect_uri": REDIRECT_URI,
                        "code_verifier": code_verifier,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )

                if resp.status_code != 200:
                    self._log_http_failure("[OpenAI] Token 兑换失败", resp)
                    return False

                tokens = resp.json()
                token_manager.save_token(email, tokens, platform="openai")

                # 保存账号信息到数据库
                self._save_account_to_db(email, name, birthdate, proxy)

                log.success(f"[OpenAI] 全流程完成！{email} 注册+Token成功")
                return True

            except httpx.HTTPStatusError as e:
                log.exception("[OpenAI] HTTP 错误", e)
                return False
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                target = f"Gateway {base_url}" if base_url else (f"代理 {proxy}" if proxy else "auth.openai.com（直连）")
                log.exception(f"[OpenAI] 连接失败: {target}", e)
                if not proxy and not base_url:
                    log.error("[OpenAI] 当前为直连，若本机无法访问 OpenAI 请配置 HTTP(S) 代理后再试")
                return False
            except httpx.RequestError as e:
                log.exception("[OpenAI] 请求错误", e)
                return False
            except Exception as e:
                log.exception("[OpenAI] 注册异常", e, include_traceback=True)
                return False
