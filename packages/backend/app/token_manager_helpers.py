from datetime import datetime

from .database import Token


def build_token_id(email: str, platform: str) -> str:
    safe_email = email.replace("@", "_at_").replace(".", "_")
    return f"{platform}_{safe_email}"


def attach_account_fields(token_dict: dict, account) -> dict:
    token_dict["first_name"] = account.first_name if account else None
    token_dict["last_name"] = account.last_name if account else None
    token_dict["username"] = account.username if account else None
    token_dict["account_status"] = account.status if account else None
    return token_dict


def apply_token_update(existing: Token, token_data: dict) -> None:
    existing.access_token = token_data.get("access_token", "")
    existing.refresh_token = token_data.get("refresh_token", "")
    existing.id_token = token_data.get("id_token", "")
    existing.token_type = token_data.get("token_type", "Bearer")
    existing.expires_in = token_data.get("expires_in", 0)
    existing.status = "active"
    existing.synced_to_newapi = False
    existing.updated_at = datetime.utcnow()


def build_token_entity(token_id: str, platform: str, email: str, token_data: dict) -> Token:
    return Token(
        token_id=token_id,
        platform=platform,
        email=email,
        access_token=token_data.get("access_token", ""),
        refresh_token=token_data.get("refresh_token", ""),
        id_token=token_data.get("id_token", ""),
        token_type=token_data.get("token_type", "Bearer"),
        expires_in=token_data.get("expires_in", 0),
        status="active",
    )
