"""
Multi-page crawler. Uses Playwright to discover links, then screenshots +
audits each page with the same auth cookies + same skill config.
"""
import asyncio, io, os, time
from urllib.parse import urljoin, urlparse, urldefrag
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from PIL import Image
from app.config import load_config
from app.logger import step, info, error, get_logger

log = get_logger("crawler")

MAX_PAGES_DEFAULT = 5
MAX_PAGES_HARD = 50
SKIP_EXT = (".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".mp4", ".mp3", ".webp", ".ico")

async def _crawl(urls: list[str], cookies: list, max_pages: int,
                 wait_until: str, cap_ms: int, viewport: dict,
                 same_origin: bool, progress_cb=None):
    """Return [{url, final_url, png_bytes, links_found, error?}]."""
    origin = urlparse(urls[0]).netloc
    queue = list(urls)
    seen = set()
    results = []
    pages_done = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport=viewport,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
        )
        if cookies:
            await ctx.add_cookies(cookies)
        page = await ctx.new_page()

        while queue and pages_done < max_pages:
            url = queue.pop(0)
            clean = urldefrag(url)[0]
            if clean in seen: continue
            if any(clean.lower().endswith(e) for e in SKIP_EXT): continue
            seen.add(clean)

            if same_origin and urlparse(clean).netloc != origin:
                continue

            step(f"Crawl {pages_done+1}/{max_pages}: {clean}")
            entry = {"url": clean, "final_url": None, "png_bytes": None,
                     "links_found": 0, "error": None}
            try:
                await page.goto(clean, wait_until=wait_until, timeout=45000)
                try: await page.wait_for_load_state("networkidle", timeout=cap_ms)
                except PWTimeout: pass
                try: await page.wait_for_timeout(1200)
                except Exception: pass

                shot = await page.screenshot(type="png", full_page=False)
                entry["final_url"] = page.url
                entry["png_bytes"] = shot
                log.info("  screenshot %d bytes at %s", len(shot), page.url)

                # Discover links
                hrefs = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter(h => h && !h.startsWith('javascript:') && !h.startsWith('mailto:'))
                """)
                added = 0
                for h in hrefs:
                    h_clean = urldefrag(h)[0]
                    if h_clean not in seen and (
                        not same_origin or urlparse(h_clean).netloc == origin):
                        queue.append(h_clean)
                        added += 1
                entry["links_found"] = added
                log.info("  discovered %d new links", added)
                time.sleep(6)  # avoid Gemini RPM limits on rapid vision calls
            except Exception as e:
                entry["error"] = str(e)[:200]
                log.error("  crawl error on %s: %s", clean, entry["error"])

            results.append(entry)
            pages_done += 1
            if progress_cb:
                try: progress_cb(pages_done, max_pages, clean)
                except Exception: pass

        await browser.close()

    return results


def crawl_sync(start_url: str, cookies: list = None, max_pages: int = MAX_PAGES_DEFAULT,
               wait_until: str = "load", cap_ms: int = 5000,
               viewport: dict = None, same_origin: bool = True):
    """Thread-safe wrapper — uses asyncio.run() so it works from FastAPI's
    thread pool (AnyIO worker) which has no event loop."""
    viewport = viewport or {"width": 1440, "height": 900}
    max_pages = max(1, min(int(max_pages), MAX_PAGES_HARD))
    return asyncio.run(_crawl(
        [start_url], cookies or [], max_pages, wait_until, cap_ms,
        viewport, same_origin))
