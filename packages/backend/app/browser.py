import random

from .log_manager import log_manager as log


async def type_slowly(page, locator, text: str):
    await locator.clear()
    await locator.click()
    for char in text:
        await locator.press_sequentially(char, delay=random.randint(30, 80))
        await page.wait_for_timeout(random.randint(10, 50))


async def handle_cloudflare(page):
    title = await page.title()
    if "Just a moment" not in title and "请稍候" not in title:
        return
    log.warning("检测到 Cloudflare 验证盾牌，尝试突破...")
    await page.wait_for_timeout(3000)
    for frame in page.frames:
        try:
            cf_chk = frame.locator('.cf-turnstile-wrapper, #challenge-stage, input[type="checkbox"]').first
            if await cf_chk.count() > 0:
                log.step("尝试点击 CF 验证框...")
                await cf_chk.click()
                await page.wait_for_timeout(5000)
        except:
            pass


async def move_mouse_organically(page, locator):
    try:
        box = await locator.bounding_box(timeout=2000)
        if box:
            target_x = box['x'] + box['width'] / 2 + random.uniform(-5, 5)
            target_y = box['y'] + box['height'] / 2 + random.uniform(-5, 5)
            start_x, start_y = random.randint(100, 500), random.randint(100, 500)
            steps = random.randint(5, 15)
            for i in range(1, steps + 1):
                partial_x = start_x + (target_x - start_x) * (i / steps) + random.uniform(-10, 10)
                partial_y = start_y + (target_y - start_y) * (i / steps) + random.uniform(-10, 10)
                await page.mouse.move(partial_x, partial_y)
                await page.wait_for_timeout(random.randint(10, 30))
            await page.mouse.move(target_x, target_y)
            await page.wait_for_timeout(random.randint(100, 300))
    except:
        pass


STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel(R) Iris(R) Xe Graphics';
        return getParameter.call(this, parameter);
    };
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'},
        ]
    });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );
    Object.defineProperty(navigator, 'connection', {
        get: () => ({ effectiveType: '4g', rtt: 50, downlink: 10, saveData: false })
    });
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
"""
