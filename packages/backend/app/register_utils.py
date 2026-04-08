import logging
import re
from typing import Optional, Tuple

import httpx


logger = logging.getLogger(__name__)


def check_ip_location() -> Tuple[bool, Optional[str]]:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get("https://cloudflare.com/cdn-cgi/trace")
        trace_text = response.text
        loc_match = re.search(r"loc=([A-Z]+)", trace_text)
        loc = loc_match.group(1) if loc_match else None
        if loc in {"CN", "HK", "MO"}:
            return False, loc
        return True, loc
    except Exception as e:
        logger.error(f"检查 IP 地理位置失败: {e}")
        return False, None