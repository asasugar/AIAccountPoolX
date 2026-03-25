from copy import deepcopy


DEFAULT_IMAP_PORT = 993
DEFAULT_RUN_COUNT = 0
DEFAULT_RUN_INTERVAL = 60
DEFAULT_HEADLESS = False
DEFAULT_LOG_ENABLED = False
DEFAULT_EMAIL_PREFIX = "auto"

DEFAULT_LOG_DIR = "logs"
DEFAULT_DATA_DIR = "data"
PATH_DEFAULTS = {
    "log_dir": DEFAULT_LOG_DIR,
    "data_dir": DEFAULT_DATA_DIR,
}

DEFAULT_PROXY_API_FORMAT = "text"
DEFAULT_PROXY_API_FIELD = "proxy"
DEFAULT_PROXY_PROTOCOL = "http://"
DEFAULT_PROXY_SELECTION_STRATEGY = "round_robin"
DEFAULT_PROXY_REFRESH_INTERVAL = 300
DEFAULT_PROXY_MAX_USES = 1
DEFAULT_PROXY_AUTO_SWITCH = True
PROXY_SCHEMES = ("http://", "https://", "socks5://", "socks4://")
DEFAULT_NEWAPI_TYPE_OPENAI = 57
DEFAULT_NEWAPI_MODELS = "gpt-5.4,gpt-5.3,gpt-5,gpt-5-codex,gpt-5-codex-mini,gpt-5.1,gpt-5.1-codex,gpt-5.1-codex-max,gpt-5.1-codex-mini,gpt-5.2,gpt-5.2-codex,gpt-5.3-codex,gpt-5-openai-compact,gpt-5-codex-openai-compact,gpt-5-codex-mini-openai-compact,gpt-5.1-openai-compact,gpt-5.1-codex-openai-compact,gpt-5.1-codex-max-openai-compact,gpt-5.1-codex-mini-openai-compact,gpt-5.2-openai-compact,gpt-5.2-codex-openai-compact,gpt-5.3-codex-openai-compact"

DEFAULT_EMAIL_PRESETS = [
    {
        "name": "Tempmail.lol",
        "email_type": "tempmail_lol",
        "domain": "",
        "imap_host": "",
        "imap_port": DEFAULT_IMAP_PORT,
        "imap_user": "",
        "imap_pass": "",
        "tempmail_base_url": "https://api.tempmail.lol/v2",
    },
    {"name": "QQ Mail", "email_type": "imap", "domain": "", "imap_host": "imap.qq.com", "imap_port": DEFAULT_IMAP_PORT, "imap_user": "", "imap_pass": ""},
    {"name": "Outlook", "email_type": "imap", "domain": "outlook.com", "imap_host": "outlook.office365.com", "imap_port": DEFAULT_IMAP_PORT, "imap_user": "", "imap_pass": ""},
]
ACTIVE_EMAIL_FIELDS = ("email_type", "domain", "imap_host", "imap_port", "imap_user", "imap_pass", "tempmail_base_url")
CONFIG_SAVE_ORDER = (
    "domain",
    "imap_host",
    "imap_port",
    "imap_user",
    "imap_pass",
    "log_dir",
    "run_count",
    "run_interval",
    "headless",
    "proxy",
    "log_enabled",
    "email_prefix",
    "proxy_pool",
    "proxy_api",
    "proxy_api_format",
    "proxy_api_field",
    "proxy_protocol",
    "proxy_selection_strategy",
    "proxy_refresh_interval",
    "proxy_max_uses",
    "proxy_auto_switch",
    "data_dir",
    "newapi_base_url",
    "newapi_token",
    "newapi_type_openai",
    "newapi_models",
    "newapi_channel_base_url",
    "newapi_sync_last_at",
    "newapi_sync_status",
    "newapi_sync_message",
    "newapi_sync_success_count",
    "newapi_sync_fail_count",
    "newapi_user_id",
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_regions",
    "email_presets",
    "active_email_preset",
    "outlook_client_id",
    "outlook_refresh_token",
)


def get_default_email_presets() -> list[dict]:
    return deepcopy(DEFAULT_EMAIL_PRESETS)


def get_default_config_values() -> dict:
    return {
        "domain": "",
        "imap_host": "",
        "imap_port": DEFAULT_IMAP_PORT,
        "imap_user": "",
        "imap_pass": "",
        "log_dir": DEFAULT_LOG_DIR,
        "data_dir": DEFAULT_DATA_DIR,
        "run_count": DEFAULT_RUN_COUNT,
        "run_interval": DEFAULT_RUN_INTERVAL,
        "headless": DEFAULT_HEADLESS,
        "proxy": None,
        "log_enabled": DEFAULT_LOG_ENABLED,
        "email_prefix": DEFAULT_EMAIL_PREFIX,
        "proxy_pool": [],
        "proxy_api": None,
        "proxy_api_format": DEFAULT_PROXY_API_FORMAT,
        "proxy_api_field": DEFAULT_PROXY_API_FIELD,
        "proxy_protocol": DEFAULT_PROXY_PROTOCOL,
        "proxy_selection_strategy": DEFAULT_PROXY_SELECTION_STRATEGY,
        "proxy_refresh_interval": DEFAULT_PROXY_REFRESH_INTERVAL,
        "proxy_max_uses": DEFAULT_PROXY_MAX_USES,
        "proxy_auto_switch": DEFAULT_PROXY_AUTO_SWITCH,
        "email_presets": get_default_email_presets(),
        "active_email_preset": 0,
        "newapi_base_url": None,
        "newapi_token": None,
        "newapi_user_id": None,
        "newapi_type_openai": DEFAULT_NEWAPI_TYPE_OPENAI,
        "newapi_models": DEFAULT_NEWAPI_MODELS,
        "newapi_channel_base_url": None,
        "aws_access_key_id": None,
        "aws_secret_access_key": None,
        "aws_regions": [],
        "outlook_client_id": None,
        "outlook_refresh_token": None,
    }
