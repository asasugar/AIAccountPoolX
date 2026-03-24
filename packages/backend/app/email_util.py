import asyncio
import imaplib
import random
import re
import time
from datetime import datetime, timezone
from typing import Optional, Any

import httpx
from imap_tools import AND, MailBox, MailMessage


def generate_email(cfg: dict) -> str:
    """
    根据邮箱类型生成注册邮箱地址：
    - Outlook：{imap_user 本地部分}+{prefix}{random}@{domain}
    - 其他（QQ / Cloudflare 路由）：{prefix}{random}@{domain}
    """
    domain = cfg.get("domain", "")
    prefix = cfg.get("email_prefix", "auto")
    rand = random.randint(1000000, 9999999)
    imap_host = cfg.get("imap_host", "")
    if "outlook" in imap_host.lower():
        imap_user = cfg.get("imap_user", "")
        local = imap_user.split("@")[0] if "@" in imap_user else imap_user
        return f"{local}+{prefix}{rand}@{domain}"
    return f"{prefix}{rand}@{domain}"

from .log_manager import log_manager as log

OPENAI_OTP_SUBJECT = "Your ChatGPT code"
OTP_CODE_RE = re.compile(r"\b(\d{6})\b")
IMAP_FOLDERS = ("INBOX", "Junk", "&V4NXPpCuTvY-")
OUTLOOK_FOLDERS = ("INBOX", "Junk")
RECIPIENT_HEADER_NAMES = (
    "delivered-to",
    "x-original-to",
    "x-forwarded-to",
    "x-forwarded-for",
    "envelope-to",
)

# 全局 IMAP 连接锁，避免并发登录触发 QQ 频率限制
_imap_lock = asyncio.Lock()
# 复用的 IMAP 连接（连接参数 -> MailBox）
_imap_conn: Optional[MailBox] = None
_imap_conn_key: Optional[tuple] = None
# Outlook OAuth2 专用连接
_outlook_conn: Optional[imaplib.IMAP4_SSL] = None
_outlook_conn_key: Optional[tuple] = None
TEMPMAIL_OTP_TOLERANCE_SECONDS = 2


def _normalize_header_key(h: str) -> str:
    return h.lower().strip()


def _header_get(msg, name: str):
    key = _normalize_header_key(name)
    headers = getattr(msg, "headers", None) or {}
    for k, v in headers.items():
        k_str = k.decode() if isinstance(k, bytes) else str(k)
        if _normalize_header_key(k_str) == key:
            return v
    return None


def _recipient_matches(target_lower: str, msg) -> bool:
    if msg.to:
        local_target = target_lower.split("@")[0] if "@" in target_lower else ""
        for t in msg.to:
            t_lower = (t or "").lower()
            if target_lower in t_lower:
                return True
            if local_target and ("+" in t_lower and local_target in t_lower):
                return True
    for header_name in RECIPIENT_HEADER_NAMES:
        vals = _header_get(msg, header_name)
        if vals and isinstance(vals, (list, tuple)):
            for v in vals:
                if v and target_lower in str(v).lower():
                    return True
        elif vals and isinstance(vals, str) and target_lower in vals.lower():
            return True
    body_check = msg.text or msg.html or ""
    if target_lower in body_check.lower():
        return True
    return False


def _is_outlook(imap_host: str) -> bool:
    return "outlook" in imap_host.lower()


def _extract_otp_code(msg: MailMessage) -> Optional[str]:
    body = msg.text or msg.html or ""
    match = OTP_CODE_RE.search(body) or OTP_CODE_RE.search(msg.subject or "")
    return match.group(1) if match else None


def _parse_tempmail_timestamp(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            ts = float(text)
        except ValueError:
            try:
                normalized = text.replace("Z", "+00:00")
                ts = datetime.fromisoformat(normalized).astimezone(timezone.utc).timestamp()
            except Exception:
                return None
    while ts > 1e11:
        ts /= 1000.0
    return ts if ts > 0 else None


def _get_tempmail_received_timestamp(message: dict) -> Optional[float]:
    for field_name in ("received_at", "date", "created_at", "createdAt", "timestamp"):
        timestamp = _parse_tempmail_timestamp(message.get(field_name))
        if timestamp is not None:
            return timestamp
    return None


async def create_tempmail_inbox(
    base_url: str = "https://api.tempmail.lol/v2",
    timeout: int = 30,
) -> tuple[Optional[str], Optional[str]]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/inbox/create",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={},
            )
            if response.status_code not in (200, 201):
                log.error(f"[TEMPMAIL] 创建邮箱失败: HTTP {response.status_code}")
                return None, None
            data = response.json()
            email = str(data.get("address", "")).strip()
            token = str(data.get("token", "")).strip()
            if not email or not token:
                log.error("[TEMPMAIL] 创建邮箱失败: 返回 address/token 缺失")
                return None, None
            log.success(f"[TEMPMAIL] 创建邮箱成功: {email}")
            return email, token
    except Exception as e:
        log.exception("[TEMPMAIL] 创建邮箱异常", e)
        return None, None


async def get_verification_code_tempmail(
    email: str,
    token: str,
    timeout: int = 120,
    base_url: str = "https://api.tempmail.lol/v2",
    stop_event=None,
    otp_sent_at: Optional[float] = None,
) -> Optional[str]:
    log.info(f"[TEMPMAIL] 等待验证码... (目标: {email})")
    start_time = time.time()
    seen_ids = set()
    while time.time() - start_time < timeout:
        if stop_event and stop_event.is_set():
            log.info("[TEMPMAIL] 任务已停止，中断验证码获取")
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/inbox",
                    params={"token": token},
                    headers={"Accept": "application/json"},
                )
            if response.status_code != 200:
                await asyncio.sleep(3)
                continue
            data = response.json()
            if data is None or (isinstance(data, dict) and not data):
                log.warning(f"[TEMPMAIL] 邮箱已过期: {email}")
                return None
            email_list = data.get("emails", []) if isinstance(data, dict) else []
            if not isinstance(email_list, list):
                await asyncio.sleep(3)
                continue
            for msg in email_list:
                if not isinstance(msg, dict):
                    continue
                msg_timestamp = _get_tempmail_received_timestamp(msg)
                if otp_sent_at is not None:
                    min_allowed_timestamp = otp_sent_at - TEMPMAIL_OTP_TOLERANCE_SECONDS
                    if msg_timestamp is None or msg_timestamp <= min_allowed_timestamp:
                        continue
                message_id = str(
                    msg.get("id")
                    or msg.get("date")
                    or msg.get("createdAt")
                    or f"{msg.get('from', '')}:{msg.get('subject', '')}:{msg_timestamp}"
                ).strip()
                if not message_id or message_id in seen_ids:
                    continue
                seen_ids.add(message_id)
                sender = str(msg.get("from", "")).lower()
                subject = str(msg.get("subject", ""))
                body = str(msg.get("body", ""))
                html = str(msg.get("html") or "")
                content = "\n".join([sender, subject, body, html])
                if "openai" not in sender and "openai" not in content.lower():
                    continue
                match = OTP_CODE_RE.search(content)
                if match:
                    code = match.group(1)
                    log.success(f"[TEMPMAIL] 获取到验证码: {code}")
                    return code
        except Exception as e:
            log.exception("[TEMPMAIL] 查询收件箱异常", e)
        await asyncio.sleep(3)
    return None


def _get_outlook_conn(imap_user: str, client_id: str, refresh_token: str) -> imaplib.IMAP4_SSL:
    """获取或复用 Outlook OAuth2 IMAP 连接"""
    global _outlook_conn, _outlook_conn_key
    from .outlook_oauth import imap_login_oauth2
    key = (imap_user, client_id)
    if _outlook_conn is not None and _outlook_conn_key == key:
        try:
            _outlook_conn.noop()
            return _outlook_conn
        except Exception:
            try:
                _outlook_conn.logout()
            except Exception:
                pass
            _outlook_conn = None
    conn = imap_login_oauth2(imap_user, client_id, refresh_token)
    _outlook_conn = conn
    _outlook_conn_key = key
    log.info("[IMAP] Outlook OAuth2 连接建立")
    return conn


def _fetch_outlook_messages_by_queries(
    conn: imaplib.IMAP4_SSL,
    target_email: str,
    folder: str = "INBOX",
    limit: int = 5,
):
    """优先按目标邮箱搜索 Outlook 邮件，失败时再回退到最近邮件。"""
    try:
        conn.select(folder)
    except Exception:
        return []

    searches = [
        ("TO", target_email, "SUBJECT", OPENAI_OTP_SUBJECT),
        ("TO", target_email, "FROM", "openai"),
        ("TO", target_email),
        ("SUBJECT", OPENAI_OTP_SUBJECT, "FROM", "openai"),
        ("ALL",),
    ]

    messages = []
    seen_uids = set()
    for criteria in searches:
        try:
            _, data = conn.search(None, *criteria)
        except Exception:
            continue
        uids = data[0].split() if data and data[0] else []
        uids = uids[-limit:] if len(uids) > limit else uids
        for uid in reversed(uids):
            uid_text = uid.decode() if isinstance(uid, bytes) else str(uid)
            if uid_text in seen_uids:
                continue
            try:
                _, msg_data = conn.fetch(uid, "(RFC822)")
                if msg_data and msg_data[0]:
                    raw = msg_data[0][1]
                    msg = MailMessage.from_bytes(raw)
                    msg._uid = uid_text
                    messages.append(msg)
                    seen_uids.add(uid_text)
            except Exception:
                continue
        if messages:
            break
    return messages


def _fetch_mailbox_messages_by_queries(
    mailbox: MailBox,
    target_email: str,
    limit: int = 5,
):
    """优先按目标邮箱搜索 IMAP 邮件，减少并发场景下无关验证码干扰。"""
    queries = [
        AND(to=target_email, subject=OPENAI_OTP_SUBJECT),
        AND(to=target_email, from_="openai"),
        AND(to=target_email),
        AND(subject=OPENAI_OTP_SUBJECT, from_="openai"),
        AND(all=True),
    ]

    messages = []
    seen_uids = set()
    for criteria in queries:
        try:
            fetched = list(
                mailbox.fetch(
                    criteria=criteria,
                    limit=limit,
                    reverse=True,
                    mark_seen=False,
                )
            )
        except Exception:
            continue

        for msg in fetched:
            uid = getattr(msg, "uid", None)
            if uid and uid in seen_uids:
                continue
            if uid:
                seen_uids.add(uid)
            messages.append(msg)
        if messages:
            break
    return messages


def _sort_and_dedupe_messages(msgs: list[MailMessage]) -> list[MailMessage]:
    deduped_msgs = []
    seen_keys = set()
    for msg in msgs:
        msg_key = getattr(msg, "uid", None) or getattr(msg, "_uid", None)
        if not msg_key:
            msg_key = (str(msg.date), msg.subject or "", str(msg.to or ""))
        if msg_key in seen_keys:
            continue
        seen_keys.add(msg_key)
        deduped_msgs.append(msg)
    return sorted(deduped_msgs, key=lambda m: m.date.timestamp(), reverse=True)


def _summarize_message(msg: MailMessage) -> str:
    return (
        f"From={msg.from_}, To={msg.to}, Subject={msg.subject}, "
        f"Date={msg.date.strftime('%Y-%m-%d %H:%M:%S')}"
    )


def _get_mailbox(imap_host: str, imap_port: int, imap_user: str, imap_pass: str) -> MailBox:
    """获取或复用 IMAP 连接"""
    global _imap_conn, _imap_conn_key
    key = (imap_host, imap_port, imap_user, imap_pass)
    if _imap_conn is not None and _imap_conn_key == key:
        try:
            _imap_conn.client.noop()
            return _imap_conn
        except Exception:
            try:
                _imap_conn.logout()
            except Exception:
                pass
            _imap_conn = None
    mb = MailBox(imap_host, port=imap_port).login(imap_user, imap_pass)
    _imap_conn = mb
    _imap_conn_key = key
    log.info("[IMAP] 建立新连接")
    return mb


async def get_verification_code(email: str, imap_host: str, imap_port: int,
                                 imap_user: str, imap_pass: str, timeout=30,
                                 outlook_client_id: str = "", outlook_refresh_token: str = "",
                                 stop_event=None, email_type: str = "imap",
                                 tempmail_token: str = "", tempmail_base_url: str = "https://api.tempmail.lol/v2",
                                 otp_sent_at: Optional[float] = None):
    """
    通过 IMAP 轮询获取验证码。
    - Outlook：自动走 OAuth2 (XOAUTH2)
    - 其他：基础认证，全局锁串行化避免频率限制
    """
    if str(email_type).lower() == "tempmail_lol":
        if not tempmail_token:
            log.error("[TEMPMAIL] 缺少 token，无法拉取验证码")
            return None
        return await get_verification_code_tempmail(
            email=email,
            token=tempmail_token,
            timeout=timeout,
            base_url=tempmail_base_url or "https://api.tempmail.lol/v2",
            stop_event=stop_event,
            otp_sent_at=otp_sent_at,
        )

    log.info(f"等待验证码... (目标: {email})")
    start = time.time()
    email_lower = email.lower()
    use_oauth = _is_outlook(imap_host) and outlook_client_id and outlook_refresh_token
    fetch_limit = 30
    max_mail_age = max(300, timeout * 4)
    poll_count = 0

    while time.time() - start < timeout:
        if stop_event and stop_event.is_set():
            log.info("[IMAP] 任务已停止，中断验证码获取")
            return None
        poll_count += 1
        try:
            async with _imap_lock:
                found_code = None
                if use_oauth:
                    conn = _get_outlook_conn(imap_user, outlook_client_id, outlook_refresh_token)
                    msgs = []
                    for folder in OUTLOOK_FOLDERS:
                        msgs += _fetch_outlook_messages_by_queries(
                            conn,
                            email_lower,
                            folder=folder,
                            limit=fetch_limit,
                        )
                else:
                    mailbox = _get_mailbox(imap_host, imap_port, imap_user, imap_pass)
                    msgs = []
                    for folder in IMAP_FOLDERS:
                        try:
                            mailbox.client.select(folder)
                            msgs += _fetch_mailbox_messages_by_queries(
                                mailbox,
                                email_lower,
                                limit=fetch_limit,
                            )
                        except Exception:
                            pass

                # 并发注册时邮箱会同时出现多封验证码，这里扩大扫描窗口并按时间倒序处理，
                # 避免目标邮件刚好被挤出“最近几封”而一直匹配不到。
                msgs = _sort_and_dedupe_messages(msgs)
                scanned_count = len(msgs)
                openai_count = 0
                recipient_match_count = 0

                for msg in msgs:
                    if msg.from_ and "openai" not in msg.from_.lower():
                        continue
                    openai_count += 1

                    age = time.time() - msg.date.timestamp()
                    if age > max_mail_age:
                        continue
                    if not _recipient_matches(email_lower, msg):
                        continue
                    recipient_match_count += 1

                    otp_code = _extract_otp_code(msg)
                    if otp_code:
                        found_code = otp_code
                        log.step(f"[IMAP] 命中目标邮件: {_summarize_message(msg)}")
                        log.success(f"验证码: {found_code} (邮件时间: {msg.date})")
                        try:
                            if use_oauth:
                                conn.store(msg._uid.encode(), "+FLAGS", "\\Deleted")
                                conn.expunge()
                            else:
                                mailbox.delete(msg.uid)
                                mailbox.client.expunge()
                        except Exception:
                            pass
                        break

                if found_code:
                    return found_code

                elapsed = int(time.time() - start)
                log.info(
                    f"[IMAP] 第 {poll_count} 轮未命中验证码: "
                    f"扫描 {scanned_count} 封, OpenAI 邮件 {openai_count} 封, "
                    f"目标收件人候选 {recipient_match_count} 封, 已等待 {elapsed}s"
                )

        except Exception as e:
            log.exception("[IMAP] 获取邮件错误", e)
            global _imap_conn, _outlook_conn
            _imap_conn = None
            _outlook_conn = None

        await asyncio.sleep(3)

    return None
