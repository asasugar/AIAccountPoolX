from pydantic import BaseModel, Field
from typing import Optional

from .config_defaults import (
    DEFAULT_NEWAPI_MODELS,
    DEFAULT_NEWAPI_TYPE_OPENAI,
    DEFAULT_EMAIL_PREFIX,
    DEFAULT_HEADLESS,
    DEFAULT_IMAP_PORT,
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_ENABLED,
    DEFAULT_PROXY_API_FIELD,
    DEFAULT_PROXY_API_FORMAT,
    DEFAULT_PROXY_AUTO_SWITCH,
    DEFAULT_PROXY_MAX_USES,
    DEFAULT_PROXY_PROTOCOL,
    DEFAULT_PROXY_REFRESH_INTERVAL,
    DEFAULT_PROXY_SELECTION_STRATEGY,
    DEFAULT_RUN_COUNT,
    DEFAULT_RUN_INTERVAL,
    get_default_email_presets,
)


class TaskStartRequest(BaseModel):
    count: int = DEFAULT_RUN_COUNT
    interval: int = DEFAULT_RUN_INTERVAL
    concurrency: int = 1
    mode: str = "parallel"
    interval_min: int = 0
    interval_max: int = 0


class TaskStatusResponse(BaseModel):
    platform: str = "openai"
    platform_name: str = "OpenAI"
    running: bool = False
    current_round: int = 0
    total_rounds: int = 0
    success_count: int = 0
    fail_count: int = 0
    total_count: int = 0
    concurrency: int = 1
    active_workers: int = 0


class RegisterOnceRequest(BaseModel):
    """单次注册请求"""
    platform: str = "openai"
    # 可选：指定使用的代理 (留空则从代理池获取)
    proxy: Optional[str] = None
    # 可选：指定邮箱 (留空则自动生成)
    email: Optional[str] = None
    # 可选：指定密码 (留空则自动生成)
    password: Optional[str] = None


class RegisterOnceResponse(BaseModel):
    """单次注册响应"""
    success: bool
    email: Optional[str] = None
    proxy_used: Optional[str] = None
    message: str = ""
    token: Optional[dict] = None


class TokenItem(BaseModel):
    id: str
    email: str
    platform: str = "openai"
    access_token: str
    refresh_token: str
    saved_at: str
    status: str = "active"


class TokenListResponse(BaseModel):
    items: list[TokenItem]
    total: int


class ConfigModel(BaseModel):
    domain: str = ""
    imap_host: str = ""
    imap_port: int = DEFAULT_IMAP_PORT
    imap_user: str = ""
    imap_pass: str = ""
    log_dir: str = DEFAULT_LOG_DIR
    run_count: int = DEFAULT_RUN_COUNT
    run_interval: int = DEFAULT_RUN_INTERVAL
    headless: bool = DEFAULT_HEADLESS
    proxy: Optional[str] = None
    log_enabled: bool = DEFAULT_LOG_ENABLED
    email_prefix: str = DEFAULT_EMAIL_PREFIX
    # 代理池配置
    proxy_pool: list[str] = Field(default_factory=list)
    proxy_api: Optional[str] = None
    proxy_api_format: str = DEFAULT_PROXY_API_FORMAT
    proxy_api_field: str = DEFAULT_PROXY_API_FIELD
    proxy_protocol: str = DEFAULT_PROXY_PROTOCOL
    proxy_selection_strategy: str = DEFAULT_PROXY_SELECTION_STRATEGY
    proxy_refresh_interval: int = DEFAULT_PROXY_REFRESH_INTERVAL
    proxy_max_uses: int = DEFAULT_PROXY_MAX_USES
    proxy_auto_switch: bool = DEFAULT_PROXY_AUTO_SWITCH
    email_presets: list[dict] = Field(default_factory=get_default_email_presets)
    active_email_preset: int = 0
    newapi_base_url: Optional[str] = None
    newapi_token: Optional[str] = None
    newapi_user_id: Optional[str] = None
    newapi_type_openai: int = DEFAULT_NEWAPI_TYPE_OPENAI
    newapi_models: str = DEFAULT_NEWAPI_MODELS
    newapi_channel_base_url: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_regions: list[str] = Field(default_factory=list)


class ProxyPoolStats(BaseModel):
    """代理池统计"""
    total_proxies: int = 0
    has_api: bool = False
    proxies: list[dict] = Field(default_factory=list)


class LogEntry(BaseModel):
    id: Optional[int | str] = None
    timestamp: str
    level: str
    message: str
