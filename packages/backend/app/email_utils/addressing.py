import random


def generate_email(cfg: dict) -> str:
    domain = cfg.get("domain", "")
    prefix = cfg.get("email_prefix", "auto")
    rand = random.randint(1000000, 9999999)
    imap_host = cfg.get("imap_host", "")
    if "outlook" in imap_host.lower():
        imap_user = cfg.get("imap_user", "")
        local = imap_user.split("@")[0] if "@" in imap_user else imap_user
        return f"{local}+{prefix}{rand}@{domain}"
    return f"{prefix}{rand}@{domain}"
