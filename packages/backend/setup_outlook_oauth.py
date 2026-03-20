"""
一次性运行脚本：完成 Outlook OAuth2 授权，获取 refresh_token 并写入 config.json

使用方式：
  python setup_outlook_oauth.py

前置条件：
  1. 在 https://portal.azure.com 注册应用（见下方说明）
  2. 在 packages/backend/config.json 中填写 outlook_client_id
"""
import sys

from app.config import get_config, save_config
from app.outlook_oauth import device_code_flow, imap_login_oauth2

cfg = get_config()
client_id = str(cfg.get("outlook_client_id") or "").strip()
if not client_id:
    print("请先在 packages/backend/config.json 中设置 outlook_client_id")
    print("注册应用步骤：")
    print("  1. 访问 https://portal.azure.com → Azure Active Directory → 应用注册 → 新注册")
    print("  2. 名称随意，受支持账户类型选「个人 Microsoft 账户」")
    print("  3. 重定向 URI 选「公共客户端/本机」→ 填 https://login.microsoftonline.com/common/oauth2/nativeclient")
    print("  4. 注册后复制「应用程序(客户端) ID」填入 config.json: outlook_client_id=xxx")
    print("  5. API 权限 → 添加权限 → APIs my organization uses → 搜索 Office 365 Exchange Online")
    print("     → 委托的权限 → IMAP.AccessAsUser.All → 添加")
    sys.exit(1)

user = ""
presets = cfg.get("email_presets", [])
for preset in presets:
    imap_host = str(preset.get("imap_host") or "").lower()
    if "outlook" in imap_host:
        user = str(preset.get("imap_user") or "").strip()
        if user:
            break
if not user:
    user = input("请输入 Outlook 邮箱地址: ").strip()

print(f"\n正在为 {user} 发起 OAuth2 授权...")
result = device_code_flow(client_id)
refresh_token = result["refresh_token"]

cfg["outlook_refresh_token"] = refresh_token
save_config(cfg)
print(f"\nrefresh_token 已写入 packages/backend/config.json")

print("\n验证 IMAP 连接...")
try:
    m = imap_login_oauth2(user, client_id, refresh_token)
    m.select("INBOX")
    print("IMAP 连接成功!")
    m.logout()
except Exception as e:
    print(f"IMAP 连接失败: {e}")
