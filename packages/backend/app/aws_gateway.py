"""
AWS API Gateway IP 轮换器
原理：在 AWS 多个 Region 创建 API Gateway，每个 Gateway 出口 IP 不同，
      httpx 请求随机选 Gateway endpoint 发出，实现每次请求 IP 不同。

使用：
    async with AwsGateway(target="https://auth.openai.com", ...) as gw:
        client = gw.build_client()
        resp = await client.get("/api/...")
"""
import asyncio
import random
from typing import Optional

import boto3
import httpx

from .log_manager import log_manager as log

DEFAULT_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "ap-southeast-1", "ap-northeast-1",
]


class AwsGateway:
    """
    在 AWS 多区域创建 API Gateway REST API，让 httpx 通过随机 Gateway 发请求。
    每个 Gateway 出口 IP 不同，达到 IP 轮换效果。
    """

    def __init__(
        self,
        target: str,
        regions: Optional[list[str]] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        api_name: str = "ai-pool-rotator",
    ):
        self.target = target.rstrip("/")
        self.regions = regions or DEFAULT_REGIONS
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.api_name = api_name
        self._endpoints: list[str] = []
        self._created: list[dict] = []

    def _boto_client(self, region: str):
        kwargs = {"region_name": region}
        if self.aws_access_key_id:
            kwargs["aws_access_key_id"] = self.aws_access_key_id
            kwargs["aws_secret_access_key"] = self.aws_secret_access_key
        return boto3.client("apigateway", **kwargs)

    def _create_gateway(self, region: str) -> Optional[str]:
        try:
            client = self._boto_client(region)
            api = client.create_rest_api(
                name=self.api_name,
                endpointConfiguration={"types": ["REGIONAL"]},
            )
            api_id = api["id"]

            resources = client.get_resources(restApiId=api_id)
            root_id = next(r["id"] for r in resources["items"] if r["path"] == "/")

            proxy = client.create_resource(
                restApiId=api_id,
                parentId=root_id,
                pathPart="{proxy+}",
            )
            proxy_id = proxy["id"]

            client.put_method(
                restApiId=api_id,
                resourceId=proxy_id,
                httpMethod="ANY",
                authorizationType="NONE",
                requestParameters={"method.request.path.proxy": True},
            )

            client.put_integration(
                restApiId=api_id,
                resourceId=proxy_id,
                httpMethod="ANY",
                type="HTTP_PROXY",
                integrationHttpMethod="ANY",
                uri=f"{self.target}/{{proxy}}",
                requestParameters={
                    "integration.request.path.proxy": "method.request.path.proxy",
                    "integration.request.header.X-Forwarded-For": "'127.0.0.1'",
                },
            )

            client.create_deployment(restApiId=api_id, stageName="proxy")

            endpoint = f"https://{api_id}.execute-api.{region}.amazonaws.com/proxy"
            self._created.append({"api_id": api_id, "region": region})
            log.success(f"[AwsGateway] 创建成功: {region} → {endpoint}")
            return endpoint
        except Exception as e:
            log.exception(f"[AwsGateway] 创建失败 [{region}]", e)
            return None

    def _delete_gateway(self, api_id: str, region: str):
        try:
            client = self._boto_client(region)
            client.delete_rest_api(restApiId=api_id)
            log.info(f"[AwsGateway] 已删除: {api_id} [{region}]")
        except Exception as e:
            log.exception(f"[AwsGateway] 删除失败 [{region}] {api_id}", e)

    async def start(self):
        log.info(f"[AwsGateway] 正在 {len(self.regions)} 个区域创建 API Gateway...")
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, self._create_gateway, r)
            for r in self.regions
        ]
        results = await asyncio.gather(*tasks)
        self._endpoints = [ep for ep in results if ep]
        if not self._endpoints:
            raise RuntimeError("AwsGateway: 所有区域创建失败，请检查 AWS 凭证和权限")
        log.success(f"[AwsGateway] 共 {len(self._endpoints)} 个 Gateway 就绪")

    async def shutdown(self):
        log.info(f"[AwsGateway] 清理 {len(self._created)} 个 Gateway...")
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, self._delete_gateway, info["api_id"], info["region"])
            for info in self._created
        ]
        await asyncio.gather(*tasks)
        self._endpoints.clear()
        self._created.clear()

    def build_client(self, **kwargs) -> httpx.AsyncClient:
        """
        返回一个 httpx.AsyncClient，所有请求通过随机 Gateway 出去。
        使用方式与普通 client 一致，只是 base_url 变成了随机 Gateway。
        """
        if not self._endpoints:
            raise RuntimeError("AwsGateway 尚未启动，请先调用 start()")
        endpoint = random.choice(self._endpoints)
        return httpx.AsyncClient(base_url=endpoint, follow_redirects=True, **kwargs)

    def get_random_endpoint(self) -> str:
        if not self._endpoints:
            raise RuntimeError("AwsGateway 尚未启动")
        return random.choice(self._endpoints)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.shutdown()


_gateway_instance: Optional[AwsGateway] = None
_gateway_lock = asyncio.Lock()


async def get_gateway(cfg: dict) -> Optional[AwsGateway]:
    """获取或创建全局 Gateway 实例"""
    global _gateway_instance
    if not cfg.get("aws_access_key_id") or not cfg.get("aws_secret_access_key"):
        return None
    if _gateway_instance and _gateway_instance._endpoints:
        return _gateway_instance

    async with _gateway_lock:
        if _gateway_instance and _gateway_instance._endpoints:
            return _gateway_instance
        regions = cfg.get("aws_regions") or DEFAULT_REGIONS[:4]
        _gateway_instance = AwsGateway(
            target="https://auth.openai.com",
            regions=regions,
            aws_access_key_id=cfg["aws_access_key_id"],
            aws_secret_access_key=cfg["aws_secret_access_key"],
        )
        await _gateway_instance.start()
        return _gateway_instance


async def shutdown_gateway():
    global _gateway_instance
    if _gateway_instance:
        await _gateway_instance.shutdown()
        _gateway_instance = None
