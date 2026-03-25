import re
from email.header import decode_header
from typing import Any, Optional

from imap_tools import MailMessage


OPENAI_OTP_SUBJECT = "Your ChatGPT code"
OTP_CODE_RE = re.compile(r"\b(\d{6})\b")
OTP_SEMANTIC_CODE_RE = re.compile(
    r"(?:code|verification|one[-\s]?time|otp|验证码)[^\d]{0,32}\b(\d{6})\b",
    re.IGNORECASE,
)
OPENAI_EMAIL_SENDERS = (
    "openai",
    "@openai.com",
    "@account.openai.com",
    "no-reply",
)
RECIPIENT_HEADER_NAMES = (
    "delivered-to",
    "x-original-to",
    "x-forwarded-to",
    "x-forwarded-for",
    "envelope-to",
)


def normalize_header_key(header_name: str) -> str:
    return header_name.lower().strip()


def header_get(msg, name: str):
    key = normalize_header_key(name)
    headers = getattr(msg, "headers", None) or {}
    for header_key, header_value in headers.items():
        key_str = header_key.decode() if isinstance(header_key, bytes) else str(header_key)
        if normalize_header_key(key_str) == key:
            return header_value
    return None


def decode_mime_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    text = str(value)
    try:
        parts = decode_header(text)
    except Exception:
        return text
    decoded_parts = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                decoded_parts.append(part.decode(errors="replace"))
        else:
            decoded_parts.append(str(part))
    return "".join(decoded_parts)


def header_values_to_texts(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        return [decode_mime_value(v) for v in values if v is not None]
    return [decode_mime_value(values)]


def message_sender_lower(msg: MailMessage) -> str:
    sender = decode_mime_value(getattr(msg, "from_", "") or "")
    if sender:
        return sender.lower()
    header_from = header_get(msg, "from")
    header_values = header_values_to_texts(header_from)
    return " ".join(header_values).lower() if header_values else ""


def is_openai_sender(sender_text: str) -> bool:
    sender_lower = (sender_text or "").lower()
    if not sender_lower:
        return False
    for sender in OPENAI_EMAIL_SENDERS:
        if sender.startswith("@") or sender.startswith("."):
            if sender in sender_lower:
                return True
        elif sender in sender_lower:
            return True
    return False


def extract_otp_from_text(text: str) -> Optional[str]:
    match = OTP_SEMANTIC_CODE_RE.search(text) or OTP_CODE_RE.search(text)
    return match.group(1) if match else None


def recipient_matches(target_lower: str, msg) -> bool:
    if msg.to:
        local_target = target_lower.split("@")[0] if "@" in target_lower else ""
        for recipient in msg.to:
            recipient_lower = decode_mime_value(recipient).lower()
            if target_lower in recipient_lower:
                return True
            if local_target and ("+" in recipient_lower and local_target in recipient_lower):
                return True
    for header_name in RECIPIENT_HEADER_NAMES:
        vals = header_get(msg, header_name)
        for value in header_values_to_texts(vals):
            if target_lower in value.lower():
                return True
    body_check = msg.text or msg.html or ""
    if target_lower in body_check.lower():
        return True
    return False


def extract_otp_code(msg: MailMessage) -> Optional[str]:
    subject = decode_mime_value(getattr(msg, "subject", "") or "")
    body = msg.text or msg.html or ""
    content = "\n".join([subject, body])
    return extract_otp_from_text(content)
