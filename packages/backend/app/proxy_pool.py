"""
代理池模块 - 支持静态代理列表和动态 API 获取代理
"""
import asyncio
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from .config_defaults import (
    DEFAULT_PROXY_API_FIELD,
    DEFAULT_PROXY_API_FORMAT,
    DEFAULT_PROXY_AUTO_SWITCH,
    DEFAULT_PROXY_MAX_USES,
    DEFAULT_PROXY_PROTOCOL,
    DEFAULT_PROXY_REFRESH_INTERVAL,
    DEFAULT_PROXY_SELECTION_STRATEGY,
)
from .log_manager import log_manager as log
from .proxy_pool_helpers import (
    ensure_proxy_scheme,
    get_nested_json_value,
    select_proxy_by_strategy,
)


@dataclass
class ProxyInfo:
    """代理信息"""
    server: str
    used_count: int = 0
    last_used: Optional[datetime] = None
    success_count: int = 0
    fail_count: int = 0


@dataclass
class ProxyPoolConfig:
    """代理池配置"""
    # 静态代理列表 (格式: ["http://ip:port", "socks5://user:pass@ip:port"])
    proxy_list: list[str] = field(default_factory=list)
    # 动态代理 API URL (GET 请求返回代理地址)
    proxy_api: Optional[str] = None
    # API 返回格式: "text" (直接返回代理地址) 或 "json" (需要指定字段)
    proxy_api_format: str = DEFAULT_PROXY_API_FORMAT
    # JSON 格式时，代理地址所在的字段路径 (如 "data.proxy" 或 "ip")
    proxy_api_field: str = DEFAULT_PROXY_API_FIELD
    # 代理协议前缀 (当 API 返回的代理不包含协议时自动添加)
    proxy_protocol: str = DEFAULT_PROXY_PROTOCOL
    # 代理使用策略: "round_robin" (轮询), "random" (随机), "least_used" (最少使用)
    selection_strategy: str = DEFAULT_PROXY_SELECTION_STRATEGY
    # 代理池刷新间隔 (秒), 仅对 API 模式有效
    refresh_interval: int = DEFAULT_PROXY_REFRESH_INTERVAL
    # 单个代理最大使用次数 (0 表示不限制)
    max_uses_per_proxy: int = DEFAULT_PROXY_MAX_USES
    # 是否在失败后自动切换代理
    auto_switch_on_fail: bool = DEFAULT_PROXY_AUTO_SWITCH


class ProxyPool:
    """代理池管理器"""

    def __init__(self):
        self._proxies: list[ProxyInfo] = []
        self._current_index: int = 0
        self._config: Optional[ProxyPoolConfig] = None
        self._lock = asyncio.Lock()

    def configure(self, config: dict):
        """从配置字典初始化代理池"""
        self._config = ProxyPoolConfig(
            proxy_list=list(config.get("proxy_pool", [])),
            proxy_api=config.get("proxy_api"),
            proxy_api_format=config.get("proxy_api_format", DEFAULT_PROXY_API_FORMAT),
            proxy_api_field=config.get("proxy_api_field", DEFAULT_PROXY_API_FIELD),
            proxy_protocol=config.get("proxy_protocol", DEFAULT_PROXY_PROTOCOL),
            selection_strategy=config.get("proxy_selection_strategy", DEFAULT_PROXY_SELECTION_STRATEGY),
            refresh_interval=config.get("proxy_refresh_interval", DEFAULT_PROXY_REFRESH_INTERVAL),
            max_uses_per_proxy=config.get("proxy_max_uses", DEFAULT_PROXY_MAX_USES),
            auto_switch_on_fail=config.get("proxy_auto_switch", DEFAULT_PROXY_AUTO_SWITCH),
        )

        # 从静态列表初始化代理
        self._proxies = [ProxyInfo(server=p) for p in self._config.proxy_list]
        self._current_index = 0

        if self._proxies:
            log.info(f"[ProxyPool] 已加载 {len(self._proxies)} 个静态代理")
        if self._config.proxy_api:
            log.info(f"[ProxyPool] 已配置动态代理 API: {self._config.proxy_api}")

    async def _fetch_from_api(self) -> Optional[str]:
        """从 API 获取代理"""
        if not self._config or not self._config.proxy_api:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self._config.proxy_api)
                resp.raise_for_status()

                if self._config.proxy_api_format == "json":
                    proxy = get_nested_json_value(resp.json(), self._config.proxy_api_field)
                else:
                    proxy = resp.text.strip()

                if proxy:
                    proxy = ensure_proxy_scheme(proxy, self._config.proxy_protocol)
                    log.success(f"[ProxyPool] 从 API 获取代理: {proxy}")
                    return proxy

        except Exception as e:
            log.exception("[ProxyPool] 从 API 获取代理失败", e)

        return None

    async def get_proxy(self) -> Optional[str]:
        """获取一个代理地址"""
        async with self._lock:
            # 优先使用 API 获取动态代理
            if self._config and self._config.proxy_api:
                proxy = await self._fetch_from_api()
                if proxy:
                    return proxy

            # 如果没有 API 或 API 获取失败，使用静态代理列表
            if not self._proxies:
                log.warning("[ProxyPool] 代理池为空，将不使用代理")
                return None

            # 根据策略选择代理
            proxy_info = self._select_proxy()
            if not proxy_info:
                return None

            # 更新使用统计
            proxy_info.used_count += 1
            proxy_info.last_used = datetime.now()

            log.info(f"[ProxyPool] 选择代理: {proxy_info.server} (已使用 {proxy_info.used_count} 次)")
            return proxy_info.server

    def _select_proxy(self) -> Optional[ProxyInfo]:
        """根据策略选择代理"""
        if not self._proxies:
            return None

        available = self._proxies
        if self._config and self._config.max_uses_per_proxy > 0:
            available = [p for p in self._proxies if p.used_count < self._config.max_uses_per_proxy]
            if not available:
                # 如果所有代理都达到最大使用次数，重置计数
                log.info("[ProxyPool] 所有代理已达最大使用次数，重置计数器")
                for p in self._proxies:
                    p.used_count = 0
                available = self._proxies

        strategy = self._config.selection_strategy if self._config else "round_robin"
        proxy, next_index = select_proxy_by_strategy(available, strategy, self._current_index)
        self._current_index = next_index
        return proxy

    def report_success(self, proxy: str):
        """报告代理使用成功"""
        for p in self._proxies:
            if p.server == proxy:
                p.success_count += 1
                break

    def report_failure(self, proxy: str):
        """报告代理使用失败"""
        for p in self._proxies:
            if p.server == proxy:
                p.fail_count += 1
                break

    def get_stats(self) -> dict:
        """获取代理池统计信息"""
        return {
            "total_proxies": len(self._proxies),
            "has_api": bool(self._config and self._config.proxy_api),
            "proxies": [
                {
                    "server": p.server[:30] + "..." if len(p.server) > 30 else p.server,
                    "used_count": p.used_count,
                    "success_count": p.success_count,
                    "fail_count": p.fail_count,
                }
                for p in self._proxies
            ]
        }

    def add_proxy(self, proxy: str):
        """动态添加代理"""
        if not any(p.server == proxy for p in self._proxies):
            self._proxies.append(ProxyInfo(server=proxy))
            log.info(f"[ProxyPool] 添加代理: {proxy}")

    def remove_proxy(self, proxy: str):
        """移除代理"""
        self._proxies = [p for p in self._proxies if p.server != proxy]
        log.info(f"[ProxyPool] 移除代理: {proxy}")

    def clear(self):
        """清空代理池"""
        self._proxies.clear()
        self._current_index = 0


# 全局代理池实例
proxy_pool = ProxyPool()
