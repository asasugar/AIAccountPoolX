import asyncio
import imaplib
import time
from typing import Optional

from imap_tools import AND, MailBox, MailMessage

from ..log_manager import log_manager as log
from .parsing import (
    extract_otp_code,
    looks_like_openai_otp_message,
    recipient_matches,
    recipient_matches_full_email,
)
from .tempmail import TEMPMAIL_OTP_TOLERANCE_SECONDS, get_verification_code_tempmail


IMAP_PRIMARY_FOLDERS = ("INBOX",)
IMAP_SECONDARY_FOLDERS = ("Junk", "&V4NXPpCuTvY-")
OUTLOOK_PRIMARY_FOLDERS = ("INBOX",)
OUTLOOK_SECONDARY_FOLDERS = ("Junk",)


def _imap_login_is_mailbox_for_target(email_lower: str, imap_user: str) -> bool:
    u = (imap_user or "").lower().strip()
    if not u:
        return False
    if u == email_lower:
        return True
    if "@" not in u:
        local, sep, _ = email_lower.partition("@")
        return bool(sep) and u == local
    return False

_imap_lock = asyncio.Lock()
_imap_conn: Optional[MailBox] = None
_imap_conn_key: Optional[tuple] = None
_imap_folders_cache: Optional[tuple[tuple, tuple[str, ...]]] = None
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
    unseen_limit: int = 8,
    all_limit: int = 4,
):
    try:
        conn.select(folder)
    except Exception:
        return []

    messages = []
    try:
        _, unseen_data = conn.search(None, "UNSEEN")
        _, all_data = conn.search(None, "ALL")
    except Exception:
        return []
    unseen_uids = unseen_data[0].split() if unseen_data and unseen_data[0] else []
    all_uids = all_data[0].split() if all_data and all_data[0] else []
    combined_uids = []
    seen_uid = set()
    for uid in (unseen_uids[-unseen_limit:] + all_uids[-all_limit:]):
        if uid in seen_uid:
            continue
        seen_uid.add(uid)
        combined_uids.append(uid)
    max_total = unseen_limit + all_limit
    uids = combined_uids[-max_total:] if len(combined_uids) > max_total else combined_uids
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
    unseen_limit: int = 8,
    all_limit: int = 4,
    target_email: str = "",
):
    target_msgs = []
    unseen_msgs = []
    all_msgs = []
    if target_email:
        try:
            target_msgs = list(
                mailbox.fetch(
                    criteria=AND(to=target_email, all=True),
                    limit=max(unseen_limit, all_limit),
                    reverse=True,
                    mark_seen=False,
                )
            )
        except Exception:
            pass
    try:
        unseen_msgs = list(
            mailbox.fetch(
                criteria=AND(seen=False),
                limit=unseen_limit,
                reverse=True,
                mark_seen=False,
            )
        )
    except Exception:
        pass
    try:
        all_msgs = list(
            mailbox.fetch(
                criteria=AND(all=True),
                limit=all_limit,
                reverse=True,
                mark_seen=False,
            )
        )
    except Exception:
        pass
    return target_msgs + unseen_msgs + all_msgs


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


def get_imap_scan_folders(mailbox: MailBox, conn_key: tuple) -> tuple[str, ...]:
    global _imap_folders_cache
    if _imap_folders_cache is not None and _imap_folders_cache[0] == conn_key:
        return _imap_folders_cache[1]
    listed_folders: list[str] = []
    try:
        for info in mailbox.folder.list():
            name = (getattr(info, "name", "") or "").strip()
            if not name:
                continue
            flags = tuple((f or "").lower() for f in getattr(info, "flags", ()) or ())
            if "\\noselect" in flags:
                continue
            listed_folders.append(name)
    except Exception:
        pass

    def _folder_priority(name: str) -> tuple[int, str]:
        lower_name = name.lower()
        if lower_name == "inbox":
            return (0, lower_name)
        if "spam" in lower_name or "junk" in lower_name:
            return (1, lower_name)
        if "trash" in lower_name or "deleted" in lower_name:
            return (3, lower_name)
        return (2, lower_name)

    ordered = tuple(dict.fromkeys(sorted(listed_folders, key=_folder_priority)))
    if not ordered:
        ordered = IMAP_PRIMARY_FOLDERS + IMAP_SECONDARY_FOLDERS
    _imap_folders_cache = (conn_key, ordered)
    return ordered


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
    global _imap_conn, _imap_conn_key, _imap_folders_cache, _outlook_conn
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
    email_lower = (email or "").lower().strip()
    email_local = email_lower.split("@")[0] if "@" in email_lower else email_lower
    skip_recipient_check = _imap_login_is_mailbox_for_target(email_lower, imap_user)
    use_oauth = is_outlook(imap_host) and outlook_client_id and outlook_refresh_token
    unseen_fetch_limit_base = 10
    all_fetch_limit_base = 6
    max_mail_age = max(300, timeout * 4)
    min_mail_timestamp = (otp_sent_at - TEMPMAIL_OTP_TOLERANCE_SECONDS) if otp_sent_at else None
    min_timestamp_skew_seconds = 180
    total_poll_count = 0
    conn_poll_count = 0
    max_poll_rounds = 5
    imap_miss_rounds = 0
    force_reconnect_next_round = False

    while time.time() - start < timeout and total_poll_count < max_poll_rounds:
        if stop_event and stop_event.is_set():
            log.info("[IMAP] 任务已停止，中断验证码获取")
            return None
        total_poll_count += 1
        conn_poll_count += 1
        try:
            async with _imap_lock:
                found_code = None
                if conn_poll_count >= 6:
                    unseen_fetch_limit = 60
                    all_fetch_limit = 40
                    include_secondary_folders = True
                elif conn_poll_count >= 3:
                    unseen_fetch_limit = 30
                    all_fetch_limit = 20
                    include_secondary_folders = (conn_poll_count % 2 == 0)
                else:
                    unseen_fetch_limit = unseen_fetch_limit_base
                    all_fetch_limit = all_fetch_limit_base
                    include_secondary_folders = (conn_poll_count % 3 == 0)
                if use_oauth:
                    conn = get_outlook_conn(imap_user, outlook_client_id, outlook_refresh_token)
                    msgs = []
                    folders = OUTLOOK_PRIMARY_FOLDERS + (
                        OUTLOOK_SECONDARY_FOLDERS if include_secondary_folders else ()
                    )
                    for folder in folders:
                        msgs += fetch_outlook_messages_by_queries(
                            conn,
                            folder=folder,
                            unseen_limit=unseen_fetch_limit,
                            all_limit=all_fetch_limit,
                        )
                else:
                    if force_reconnect_next_round and _imap_conn is not None:
                        try:
                            _imap_conn.logout()
                        except Exception:
                            pass
                        _imap_conn = None
                        _imap_conn_key = None
                        _imap_folders_cache = None
                        log.info("[IMAP] 连续2轮未命中，重建连接")
                        conn_poll_count = 1
                        imap_miss_rounds = 0
                    force_reconnect_next_round = False
                    imap_conn_key = (imap_host, imap_port, imap_user, imap_pass)
                    if _imap_conn is None or _imap_conn_key != imap_conn_key:
                        if total_poll_count == 1:
                            log.info("[IMAP] 建立连接前等待 5s")
                            await asyncio.sleep(5)
                    mailbox = get_mailbox(imap_host, imap_port, imap_user, imap_pass)
                    msgs = []
                    folder_key = (imap_host, imap_port, imap_user, imap_pass)
                    discovered_folders = get_imap_scan_folders(mailbox, folder_key)
                    if include_secondary_folders:
                        folders = discovered_folders
                    else:
                        folders = tuple(
                            f for f in discovered_folders if f.lower() in {"inbox"}
                        ) or IMAP_PRIMARY_FOLDERS
                    for folder in folders:
                        try:
                            mailbox.client.select(folder)
                            msgs += fetch_mailbox_messages_by_queries(
                                mailbox,
                                unseen_limit=unseen_fetch_limit,
                                all_limit=all_fetch_limit,
                                target_email=email_lower,
                            )
                        except Exception:
                            pass

                msgs = sort_and_dedupe_messages(msgs)
                scanned_count = len(msgs)
                openai_count = 0

                for msg in msgs:
                    if not looks_like_openai_otp_message(msg):
                        continue
                    openai_count += 1

                    msg_timestamp = msg.date.timestamp()
                    age = time.time() - msg_timestamp
                    if age > max_mail_age:
                        continue
                    if min_mail_timestamp is not None and msg_timestamp <= min_mail_timestamp:
                        if (min_mail_timestamp - msg_timestamp) > min_timestamp_skew_seconds:
                            pass

                    otp_code = extract_otp_code(msg)
                    if not otp_code:
                        continue
                    if skip_recipient_check:
                        recipient_ok = True
                    elif conn_poll_count == 1:
                        recipient_ok = recipient_matches_full_email(email_lower, msg)
                    else:
                        recipient_ok = recipient_matches(email_local, msg)
                    if recipient_ok:
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

                if not use_oauth:
                    imap_miss_rounds += 1
                    if imap_miss_rounds % 2 == 0 and total_poll_count < max_poll_rounds:
                        force_reconnect_next_round = True

                elapsed = int(time.time() - start)
                log.info(
                    f"[IMAP] 第 {conn_poll_count} 轮未命中验证码: "
                    f"扫描 {scanned_count} 封, OpenAI 邮件 {openai_count} 封, 已等待 {elapsed}s"
                )

        except Exception as e:
            log.exception("[IMAP] 获取邮件错误", e)
            _imap_conn = None
            _imap_folders_cache = None
            _outlook_conn = None

        if total_poll_count < max_poll_rounds:
            await asyncio.sleep(3)

    if total_poll_count >= max_poll_rounds:
        log.error(f"[IMAP] 已重试 {max_poll_rounds} 轮仍未获取到验证码")

    return None
