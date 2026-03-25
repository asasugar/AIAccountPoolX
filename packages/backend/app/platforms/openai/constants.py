AUTH_BASE = "https://auth.openai.com"
SENTINEL_API = "https://sentinel.openai.com/backend-api/sentinel/req"
API_AUTHORIZE_CONTINUE = f"{AUTH_BASE}/api/accounts/authorize/continue"
API_USER_REGISTER = f"{AUTH_BASE}/api/accounts/user/register"
SEND_EMAIL_OTP = f"{AUTH_BASE}/api/accounts/email-otp/send"
API_EMAIL_OTP_VALIDATE = f"{AUTH_BASE}/api/accounts/email-otp/validate"
API_CREATE_ACCOUNT = f"{AUTH_BASE}/api/accounts/create_account"
API_WORKSPACE_SELECT = f"{AUTH_BASE}/api/accounts/workspace/select"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Ch-Ua": '"Chromium";v="145", "Not:A-Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
}

IP_CHECK_URLS = (
    "https://api.ipify.org?format=json",
    "http://ifconfig.me/ip",
    "http://checkip.amazonaws.com",
)
