# AIAccountPoolX

OpenAI 账号注册与 Token 管理系统，提供 FastAPI 后端、Vue 3 控制台、实时日志、账号/Token 管理、NewAPI 同步、代理池和可选 AWS API Gateway IP 轮换能力。

> ⚠️ 免责声明：本项目仅供学习、研究和内部测试使用。请自行遵守相关平台条款和当地法律法规，不要用于违法或滥用场景。

## 功能特性

- **OpenAI 注册任务**
  - HTTP/OAuth 注册流程
  - 支持单次注册和批量循环任务
  - 支持并发控制、任务停止、统计重置

- **邮箱与验证码**
  - 支持普通 IMAP 邮箱
  - 支持 Tempmail.lol 临时邮箱
  - 内置 Tempmail.lol / QQ Mail / Outlook 预设
  - Outlook 支持 OAuth2 IMAP 授权
  - IMAP 自动生成邮箱别名并轮询验证码
  - Tempmail.lol 通过 API 创建 inbox + token 拉取验证码

- **账号与 Token 管理**
  - Token 列表、搜索、导出、删除、批量删除
  - Token 刷新、额度估算、占用/释放
  - 账号列表、详情、编辑、删除、统计
  - 可建立账号与 Token 的邮箱关联

- **Web 控制台**
  - Vue 3 三栏面板
  - WebSocket 实时日志
  - 平台状态面板与任务控制
  - 系统配置弹窗热更新

- **渠道同步**
  - 对接 NewAPI 渠道列表
  - 一键同步 Token 到 NewAPI
  - 测试、更新、删除已有渠道

- **代理与 IP 轮换**
  - 支持单代理、静态代理池、动态代理 API
  - 轮询 / 随机 / 最少使用策略
  - 可选 AWS API Gateway 多区域出口轮换

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI · Uvicorn · HTTPX · SQLAlchemy · WebSocket · IMAP |
| 前端 | Vue 3 · TypeScript · Vite · Element Plus · Pinia · Tailwind CSS |
| 工程 | pnpm workspace monorepo |
| 存储 | SQLite |

## 项目结构

```text
AIAccountPoolX/
├── package.json
├── pnpm-workspace.yaml
├── packages/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py                # FastAPI 入口
│   │   │   ├── engine.py              # 平台引擎注册
│   │   │   ├── api/                   # REST / WebSocket 路由
│   │   │   ├── platforms/openai/      # OpenAI 注册实现
│   │   │   ├── database.py            # SQLAlchemy 模型与数据库
│   │   │   ├── token_manager.py       # Token 管理
│   │   │   ├── proxy_pool.py          # 代理池
│   │   │   └── aws_gateway.py         # AWS API Gateway 轮换
│   │   ├── config.example.json        # 安全示例配置
│   │   ├── requirements.txt
│   │   └── setup_outlook_oauth.py     # Outlook OAuth 授权脚本
│   └── frontend/
│       ├── src/components/            # Sidebar / TokenPanel / ConfigDialog / LogViewer
│       ├── src/stores/                # Pinia store
│       ├── src/api/                   # Axios API 封装
│       └── vite.config.ts
└── README.md                               # 文档
```

## 快速开始

### 环境要求

- Node.js 18+
- pnpm 8+
- Python 3.10+

### 安装依赖

```bash
pnpm install:all
```

如果你想分步执行：

```bash
pnpm install:frontend
pnpm install:backend
```

说明：

- `pnpm install:frontend` 会在仓库根目录安装整个 workspace 的 Node.js 依赖，其中已经包含前端包依赖，所以不需要单独进入 `packages/frontend`
- `pnpm install:backend` 会安装 Python 后端依赖
- `pnpm install:all` 会依次完成前后端依赖安装

### 本地配置

仓库不再保留任何可直接使用的真实凭证。

- 示例配置：[`packages/backend/config.example.json`](packages/backend/config.example.json)
- 本地配置文件：`packages/backend/config.json`
- `config.json` 不再随仓库提交，缺失时后端会使用默认配置启动

推荐方式：

1. 复制示例文件并填写你自己的值。
2. 或直接启动项目后在 Web UI 的“系统配置”中保存，系统会自动生成本地 `config.json`。

```bash
cp packages/backend/config.example.json packages/backend/config.json
```

需要开发者自行填写、不要提交到仓库的字段包括：

- `imap_user`
- `imap_pass`
- `proxy`
- `proxy_pool`
- `proxy_api`
- `newapi_base_url`
- `newapi_token`
- `newapi_user_id`
- `aws_access_key_id`
- `aws_secret_access_key`
- `outlook_client_id`
- `outlook_refresh_token`

### 启动开发环境

```bash
pnpm dev
```

或分别启动：

```bash
pnpm dev:backend
pnpm dev:frontend
```

默认地址：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:1455`

## 配置说明

### 邮箱配置

系统通过 `email_presets` 管理多套邮箱配置，`active_email_preset` 决定当前生效预设。

预设类型说明：

- `Tempmail.lol`：使用 `tempmail_base_url`（默认 `https://api.tempmail.lol/v2`）
- `QQ Mail` / `Outlook`：使用 IMAP 参数 `domain`、`imap_host`、`imap_port`、`imap_user`、`imap_pass`

说明：

- `tempmail_base_url` 仅存在于 `Tempmail.lol` 预设内
- 顶层不维护 `email_type` / `tempmail_base_url`
- `email_prefix` 仅在 IMAP 邮箱别名生成时使用

参考指南：

- QQ 邮箱 + Cloudflare 邮件路由配置指南：https://blog.cinb1314.online/other/qq-imap-cloudflare.html

### NewAPI 配置

如需启用 Token 同步到 NewAPI，需要填写：

- `newapi_base_url`
- `newapi_token`
- `newapi_user_id`

同步状态字段如 `newapi_sync_last_at`、`newapi_sync_status` 由系统自动维护，不需要手工填写。

### 代理配置

支持三类入口：

- `proxy`：单个默认代理
- `proxy_pool`：静态代理列表
- `proxy_api`：动态代理 API

配合以下字段控制策略：

- `proxy_selection_strategy`
- `proxy_refresh_interval`
- `proxy_max_uses`
- `proxy_auto_switch`

### AWS API Gateway 轮换

如需使用 AWS 出口轮换，需要填写：

- `aws_access_key_id`
- `aws_secret_access_key`
- `aws_regions`

未配置时该能力自动关闭。

参考指南：

- AWS IP 轮换配置参考：https://blog.cinb1314.online/other/aws-ip-rotation.html

### Outlook OAuth

Outlook IMAP OAuth2 需要先填写 `outlook_client_id`，然后执行：

```bash
cd packages/backend
python setup_outlook_oauth.py
```

脚本会引导获取并写入本地 `outlook_refresh_token`。

参考指南：

- Outlook OAuth2 IMAP 配置指南：https://blog.cinb1314.online/other/outlook-oauth2-imap.html

## 常用命令

```bash
pnpm install:frontend
pnpm install:backend
pnpm install:all
pnpm dev
pnpm dev:backend
pnpm dev:frontend
pnpm build
pnpm kill:all
```

根目录脚本说明：

- `pnpm dev`：并行启动前后端
- `pnpm dev:frontend`：仅启动前端开发服务器
- `pnpm dev:backend`：仅启动后端开发服务器
- `pnpm build`：构建前端产物
- `pnpm kill:backend`：清理 1455 端口
- `pnpm kill:frontend`：清理 3000 端口
- `pnpm kill:all`：同时清理前后端端口

## API 概览

### 平台与任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/platforms` | 平台列表 |
| GET | `/api/platforms/{platform_id}` | 平台状态 |
| GET | `/api/platforms/{platform_id}/config-fields` | 平台配置字段 |
| POST | `/api/task/start?platform=openai` | 启动任务 |
| POST | `/api/task/stop?platform=openai` | 停止任务 |
| GET | `/api/task/status?platform=openai` | 任务状态 |
| POST | `/api/task/reset?platform=openai` | 重置统计 |
| POST | `/api/task/register-once` | 单次注册 |
| GET | `/api/task/proxy-pool/stats` | 代理池统计 |

### Token

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tokens` | Token 列表 |
| POST | `/api/tokens/batch-delete` | 批量删除 Token |
| DELETE | `/api/tokens/{token_id}` | 删除 Token |
| GET | `/api/tokens/export` | 导出 Token |
| POST | `/api/tokens/acquire` | 获取可用 Token |
| POST | `/api/tokens/release` | 释放 Token |
| GET | `/api/tokens/stats` | Token 使用统计 |
| GET | `/api/tokens/{token_id}/quota` | 查询额度 |
| POST | `/api/tokens/{token_id}/quota` | 刷新额度估算 |
| POST | `/api/tokens/{token_id}/refresh` | 刷新 Token |

### 账号与日志

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/accounts` | 账号列表 |
| GET | `/api/accounts/{id}` | 账号详情 |
| GET | `/api/accounts/{id}/token` | 获取关联 Token |
| POST | `/api/accounts` | 创建账号 |
| PUT | `/api/accounts/{id}` | 更新账号 |
| DELETE | `/api/accounts/{id}` | 删除账号 |
| GET | `/api/accounts/stats/summary` | 账号统计 |
| GET | `/api/logs` | 任务日志 |
| GET | `/api/logs/stats` | 日志统计 |
| GET | `/api/logs/today` | 今日统计 |
| WS | `/api/ws/logs` | 实时日志流 |

### 配置与 NewAPI

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取当前配置 |
| PUT | `/api/config` | 更新配置 |
| GET | `/api/newapi/channels` | 获取渠道列表 |
| GET | `/api/newapi/channel/test/{channel_id}` | 测试渠道 |
| DELETE | `/api/newapi/channel/{channel_id}` | 删除渠道 |
| POST | `/api/newapi/channel/batch` | 批量删除渠道 |
| PUT | `/api/newapi/channel` | 更新渠道 |
| GET | `/api/newapi/sync-status` | 获取同步状态 |
| POST | `/api/newapi/sync` | 一键同步到 NewAPI |

## 安全建议

- 不要提交 `packages/backend/config.json`
- 不要提交 `packages/backend/data/`、`packages/backend/logs/`
- 不要在 README、脚本或截图中保留真实邮箱、授权码、Access Key、refresh token、服务地址或内网代理
- 如果仓库历史里已经提交过敏感值，请尽快轮换对应凭证

## 扩展平台

后端采用平台注册表模式。新增平台时：

1. 在 `packages/backend/app/platforms/` 下新增目录。
2. 实现继承 `BaseEngine` 的引擎类。
3. 在 [`packages/backend/app/engine.py`](packages/backend/app/engine.py) 注册到 `registry`。

## License

本项目采用 [MIT License](LICENSE)。
