import asyncio
import imaplib
import time
from typing import Optional

from imap_tools import AND, MailBox, MailMessage

from ..log_manager import log_manager as log
from .parsing import (
    extract_otp_code,
    is_openai_sender,
    message_sender_lower,
    recipient_matches,
)
from .tempmail import TEMPMAIL_OTP_TOLERANCE_SECONDS, get_verification_code_tempmail


IMAP_FOLDERS = ("INBOX", "Junk", "&V4NXPpCuTvY-")
OUTLOOK_FOLDERS = ("INBOX", "Junk")

_imap_lock = asyncio.Lock()
_imap_conn: Optional[MailBox] = None
_imap_conn_key: Optional[tuple] = None
_outlook_conn: Optional[imaplib.IMAP4_SSL] = None
_outlook_conn_key: Optional[tuple] = None


def is_outlook(imap_host: str) -> bool:
    return "outlook" in imap_host.lower()


def get_outlook_conn(imap_user: str, client_id: str, refresh_token: str) -> imaplib.IMAP4_SSL:
    global _outlook_conn, _outlook_conn_key
    from ..outlook_oauth import imap_login_oauth2

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


def fetch_outlook_messages_by_queries(
    conn: imaplib.IMAP4_SSL,
    folder: str = "INBOX",
    limit: int = 5,
):
    try:
        conn.select(folder)
    except Exception:
        return []

    messages = []
    try:
        _, data = conn.search(None, "UNSEEN")
    except Exception:
        return []
    uids = data[0].split() if data and data[0] else []
    uids = uids[-limit:] if len(uids) > limit else uids
    for uid in reversed(uids):
        uid_text = uid.decode() if isinstance(uid, bytes) else str(uid)
        try:
            _, msg_data = conn.fetch(uid, "(BODY.PEEK[])")
            if msg_data and msg_data[0]:
                raw = msg_data[0][1]
                msg = MailMessage.from_bytes(raw)
                msg._uid = uid_text
                messages.append(msg)
        except Exception:
            continue
    return messages


def fetch_mailbox_messages_by_queries(
    mailbox: MailBox,
    limit: int = 5,
):
    try:
        return list(
            mailbox.fetch(
                criteria=AND(seen=False),
                limit=limit,
                reverse=True,
                mark_seen=False,
            )
        )
    except Exception:
        return []


def sort_and_dedupe_messages(msgs: list[MailMessage]) -> list[MailMessage]:
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


def summarize_message(msg: MailMessage) -> str:
    return (
        f"From={msg.from_}, To={msg.to}, Subject={msg.subject}, "
        f"Date={msg.date.strftime('%Y-%m-%d %H:%M:%S')}"
    )


def get_mailbox(imap_host: str, imap_port: int, imap_user: str, imap_pass: str) -> MailBox:
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
    mailbox = MailBox(imap_host, port=imap_port).login(imap_user, imap_pass)
    _imap_conn = mailbox
    _imap_conn_key = key
    log.info("[IMAP] 建立新连接")
    return mailbox


async def get_verification_code(
    email: str,
    imap_host: str,
    imap_port: int,
    imap_user: str,
    imap_pass: str,
    timeout=30,
    outlook_client_id: str = "",
    outlook_refresh_token: str = "",
    stop_event=None,
    email_type: str = "imap",
    tempmail_token: str = "",
    tempmail_base_url: str = "https://api.tempmail.lol/v2",
    otp_sent_at: Optional[float] = None,
):
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
    use_oauth = is_outlook(imap_host) and outlook_client_id and outlook_refresh_token
    fetch_limit = 30
    max_mail_age = max(300, timeout * 4)
    min_mail_timestamp = (otp_sent_at - TEMPMAIL_OTP_TOLERANCE_SECONDS) if otp_sent_at else None
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
                    conn = get_outlook_conn(imap_user, outlook_client_id, outlook_refresh_token)
                    msgs = []
                    for folder in OUTLOOK_FOLDERS:
                        msgs += fetch_outlook_messages_by_queries(
                            conn,
                            folder=folder,
                            limit=fetch_limit,
                        )
                else:
                    mailbox = get_mailbox(imap_host, imap_port, imap_user, imap_pass)
                    msgs = []
                    for folder in IMAP_FOLDERS:
                        try:
                            mailbox.client.select(folder)
                            msgs += fetch_mailbox_messages_by_queries(
                                mailbox,
                                limit=fetch_limit,
                            )
                        except Exception:
                            pass

                msgs = sort_and_dedupe_messages(msgs)
                scanned_count = len(msgs)
                openai_count = 0
                recipient_match_count = 0

                for msg in msgs:
                    sender_lower = message_sender_lower(msg)
                    if not is_openai_sender(sender_lower):
                        continue
                    openai_count += 1

                    msg_timestamp = msg.date.timestamp()
                    age = time.time() - msg_timestamp
                    if age > max_mail_age:
                        continue
                    if min_mail_timestamp is not None and msg_timestamp <= min_mail_timestamp:
                        continue
                    if not recipient_matches(email_lower, msg):
                        continue
                    recipient_match_count += 1

                    otp_code = extract_otp_code(msg)
                    if otp_code:
                        found_code = otp_code
                        log.step(f"[IMAP] 命中目标邮件: {summarize_message(msg)}")
                        log.success(f"验证码: {found_code} (邮件时间: {msg.date})")
                        try:
                            if use_oauth:
                                conn.store(str(msg._uid), "+FLAGS", "\\Seen")
                            else:
                                mailbox.client.uid("STORE", str(msg.uid), "+FLAGS", "(\\Seen)")
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
