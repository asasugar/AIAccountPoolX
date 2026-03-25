import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from ..log_manager import log_manager as log
from .parsing import extract_otp_from_text, is_openai_sender


TEMPMAIL_OTP_TOLERANCE_SECONDS = 2


def parse_tempmail_timestamp(value: Any) -> Optional[float]:
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


def get_tempmail_received_timestamp(message: dict) -> Optional[float]:
    for field_name in ("received_at", "date", "created_at", "createdAt", "timestamp"):
        timestamp = parse_tempmail_timestamp(message.get(field_name))
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
                msg_timestamp = get_tempmail_received_timestamp(msg)
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
                if not is_openai_sender(sender) and "openai" not in content.lower():
                    continue
                code = extract_otp_from_text(content)
                if code:
                    log.success(f"[TEMPMAIL] 获取到验证码: {code}")
                    return code
        except Exception as e:
            log.exception("[TEMPMAIL] 查询收件箱异常", e)
        await asyncio.sleep(3)
    return None
