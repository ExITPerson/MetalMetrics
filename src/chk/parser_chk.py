import re
import json
import time
import random
from json import JSONDecodeError
from lib2to3.fixes.fix_input import context

from playwright.sync_api import sync_playwright, BrowserContext

from config.settings import CHK_PROXIES_RAW, CHK_SEARCH_URL
from src.chk.proxy import ProxyRotator


class SearchCHK:

    def __init__(self):
        proxies = CHK_PROXIES_RAW
        self._proxies = proxies
        self._proxy_rotator = ProxyRotator(self._proxies)
        self._playwright = None
        self._browser = None
        self._retried = 0

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            try:
                contexts = self._browser.contexts

                for ctx in contexts:
                    try:
                        ctx.close()
                        time.sleep(3)
                    except Exception:
                        pass

            except Exception:
                pass

            try:
                self._browser.close()
                time.sleep(3)
            except Exception:
                pass

        if self._playwright:
            try:
                self._playwright.stop()
                time.sleep(3)
            except Exception:
                pass

    def _create_context(self, proxy: str) -> BrowserContext:
        context = self._browser.new_context(
            proxy=proxy,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            geolocation={'latitude': 55.7558, 'longitude': 37.6173},
            permissions=['geolocation'],
            color_scheme='light',
        )

        context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    window.chrome = { runtime: {} };
                """)

        return context

    def _context_close(self, context: BrowserContext) -> None:
        try:
            context.close()
            time.sleep(3)

        except Exception:
            pass

    def _search_chk(self, query: str, retry_count: int = 0):
        proxy = self._proxy_rotator.get_next_proxy()
        if not proxy:
            return None

        context = None
        try:
            context = self._create_context(proxy)
            page = context.new_page()

            search_url = f'{CHK_SEARCH_URL}{query}'

            response = page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            if not response or response.status >= 400:
                self._proxy_rotator.report_fails(proxy, is_blok_ip=(response.status == 429 if response else False))
                self._context_close(context)
                return None

            time.sleep(random.uniform(4, 7))

            captcha_selectors = [
                'iframe[src*="captcha"]',
                '.captcha',
                '[class*="captcha"]',
                '[id*="captcha"]',
                'div:has-text("Подтвердите")',
            ]

            for sel in captcha_selectors:
                if page.query_selector(sel):
                    self._proxy_rotator.report_fails(proxy, is_blok_ip=True)
                    self._context_close(context)
                    if retry_count < 2:
                        self._retried += 1
                        time.sleep(120)
                        return self._search_chk(query, retry_count)
                    return None

            content = page.content()

            data = None
            link = None
            _RE_HREF = re.compile(r'href="([^"]+)"')

            pre_match = re.search(r'<pre>(.*?)</pre>', content, re.DOTALL)
            if pre_match:
                try:
                    data = json.loads(pre_match.group(1))
                except (JSONDecodeError, ValueError):
                    pass

            if data is None:
                try:
                    data = json.loads(content)
                except (JSONDecodeError, ValueError):
                    pass

            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                if isinstance(first, dict) and 'content' in first:
                    match = _RE_HREF.search(first['content'])
                    if match:
                        link = match.group(1)

            if not link:
                links = page.query_selector_all('a[href^="/company/"], a[href^="/ip/"]')
                if links:
                    href = links[0].get_attribute('href')
                    if href:
                        link = href

            if link and (link.startswith('/company/') or link.startswith('/ip/')):
                self._proxy_rotator.report_success(proxy)
                self._context_close(context)
                return link

            no_results = page.query_selector('text=/не найден|ничего не|no results/i')
            if no_results:
                self._context_close(context)
                return None

            self._context_close(context)
            return None

        except Exception as e:
            err_str = str(e)
            is_429 = '429' in err_str or 'Too Many Requests' in err_str
            self._proxy_rotator.report_fails(proxy, is_blok_ip=is_429)

            if is_429 and retry_count < 2:
                self._retried += 1
                time.sleep(60)
                self._context_close(context)
                return self._search_chk(query, retry_count + 1)

            self._context_close(context)
            return None





