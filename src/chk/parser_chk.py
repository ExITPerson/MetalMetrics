import asyncio
import re
from typing import Optional

import requests
import json

from config.settings import CHK_PROXIES_RAW
from src.chk.proxy import ProxyRotator
from playwright.async_api import async_playwright, BrowserContext


class CHKSearch:

    def __init__(self):
        raw_proxies = CHK_PROXIES_RAW
        self._proxies = json.loads(raw_proxies)
        self._proxy_rotator = ProxyRotator(self._proxies)
        self._playwright = None
        self._browser = None

    async def __aenter__(self):
        print('Инициализация Playwright')
        print(f'Прокси в пуле: {len(self._proxies)}')

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
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

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            try:
                contexts = self._browser.contexts
                for ctx in contexts:
                    try:
                        await asyncio.wait_for(ctx.close(), timeout=3.0)

                    except Exception:
                        pass

            except Exception:
                pass

            try:
                await asyncio.wait_for(self._browser.close(), timeout=5.0)
            except Exception:
                pass

        if self._playwright:
            try:
                await asyncio.wait_for(self._playwright.stop(), timeout=5.0)
            except Exception:
                pass

    async def _create_context(self, proxy_url: Optional[str] = None) -> BrowserContext:
        proxy = None
        if proxy_url:
            match = re.match(r'http://([^:]+):([^@]+)@([^:]+):(\d+)', proxy_url)
            if match:
                user, password, host, port = match.groups()
                proxy = {
                    'server': f'http://{host}:{port}',
                    'username': user,
                    'password': password,
                }

        context = await self._browser.new_context(
            proxy=proxy,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            geolocation={'latitude': 55.7558, 'longitude': 37.6173},
            permissions=['geolocation'],
            color_scheme='light',
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = { runtime: {} };
        """)

        return context

    async def _safe_close_context(self, context: BrowserContext):
        if not context:
            return
        try:
            await asyncio.wait_for(context.close(), timeout=3.0)
        except Exception:
            pass