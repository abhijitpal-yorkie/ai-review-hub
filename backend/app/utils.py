import io, asyncio, os
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from PIL import Image, ImageDraw, ImageFont
from .config import load_config


async def capture_screenshot(url: str, annotate_boxes: list = None,
                             cookies: list = None):
    """
    Screenshot a URL. Optional cookie injection (Stytch sessions).
    Returns (png_bytes, final_url).
    """
    cfg = load_config()
    wait_until = cfg["playwright"].get("wait_until", "load")
    cap_ms = cfg["playwright"].get("networkidle_cap_ms", 5000)
    vp = cfg["playwright"].get("viewport", {"width": 1440, "height": 900})

    async with async_playwright() as p:
        headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
        browser = await p.chromium.launch(headless=headless, slow_mo=300 if not headless else 0)
        ctx = await browser.new_context(
            viewport=vp,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
        )
        if cookies:
            await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        await page.goto(url, wait_until=wait_until, timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=cap_ms)
        except PWTimeout:
            pass
        try:
            await page.wait_for_timeout(1500)
        except Exception:
            pass
        shot = await page.screenshot(type="png", full_page=False)
        final_url = page.url
        await browser.close()

    img = Image.open(io.BytesIO(shot)).convert("RGB")
    if img.width > 1440:
        ratio = 1440 / img.width
        img = img.resize((1440, int(img.height * ratio)), Image.LANCZOS)

    if annotate_boxes:
        draw = ImageDraw.Draw(img)
        for box in annotate_boxes:
            x, y = box.get("x", 0), box.get("y", 0)
            w, h = box.get("w", 100), box.get("h", 40)
            draw.rectangle([x, y, x + w, y + h], outline="red", width=4)
            label = box.get("label", "issue")
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
            except Exception:
                font = ImageFont.load_default()
            tb = draw.textbbox((x, max(0, y - 22)), label, font=font)
            draw.rectangle(tb, fill="red")
            draw.text((x, max(0, y - 22)), label, fill="white", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), final_url


def capture_screenshot_bytes(url: str, annotate_boxes: list = None,
                             cookies: list = None) -> bytes:
    """Backward-compat helper — returns just the PNG bytes."""
    img, _ = run_async(capture_screenshot(url, annotate_boxes=annotate_boxes,
                                          cookies=cookies))
    return img


def run_async(coro):
    """Thread-safe — works from FastAPI thread pool workers."""
    return asyncio.run(coro)
