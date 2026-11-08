import re
import json
import time
import random
import logging
from json import JSONDecodeError

from playwright.sync_api import sync_playwright, BrowserContext

from config.logging_config import setup_logging
from config.settings import CHK_PROXIES_RAW, CHK_SEARCH_URL, CHK_COMPANY_URL
from src.chk.proxy import ProxyRotator, parse_proxy
from utils.logging_decorators import log_calls


logger = setup_logging('parser_chk.log')


class SearchCHK:
    """ Поиск ссылки на компанию """

    def __init__(self):
        self._proxies = CHK_PROXIES_RAW
        self._proxy_rotator = ProxyRotator(self._proxies)
        self._playwright = None
        self._browser = None
        self._retried = 0

    def __enter__(self):
        """ Запуск Playwright и браузера """
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
        """ Закрытие контекстов, браузера и остановка Playwright """
        if self._browser:
            try:
                for ctx in self._browser.contexts:
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

    @log_calls(logger=logger, level=logging.DEBUG, log_args=False, log_result=False)
    def _create_context(self, proxy: str) -> BrowserContext:
        """ Создание контекста с прокси и маскировкой автоматизации """
        context = self._browser.new_context(
            proxy=parse_proxy(proxy),
            viewport={'width': 1920, 'height': 1080},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/126.0.0.0 Safari/537.36'
            ),
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

    @log_calls(logger=logger, level=logging.DEBUG, log_args=False, log_result=False)
    def _context_close(self, context: BrowserContext) -> None:
        """ Безопасное закрытие контекста """
        try:
            context.close()
            time.sleep(3)
        except Exception:
            pass

    @log_calls(logger=logger, level=logging.INFO)
    def search_chk(self, query: str, retry_count: int = 0) -> dict | None:
        """ Поиск ссылки на компанию по запросу `query` """
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
                self._proxy_rotator.report_fails(
                    proxy, is_blok_ip=(response.status == 429 if response else False)
                )
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
                        return self.search_chk(query, retry_count + 1)
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
                return {'link':link, 'inn': query}

            if page.query_selector('text=/не найден|ничего не|no results/i'):
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
                return self.search_chk(query, retry_count + 1)

            self._context_close(context)
            return None


class FinancesParserCHK:
    """ Парсинг финансовой отчётности компании """

    def __init__(self):
        self._proxies = CHK_PROXIES_RAW
        self._proxy_rotator = ProxyRotator(self._proxies)
        self._playwright = None
        self._browser = None
        self._retried = 0

    def __enter__(self):
        """ Запуск Playwright и браузера """
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
        """ Закрытие контекстов, браузера и остановка Playwright """
        if self._browser:
            try:
                for ctx in self._browser.contexts:
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

    @log_calls(logger=logger, level=logging.DEBUG, log_args=False, log_result=False)
    def _create_context(self, proxy: str) -> BrowserContext:
        """ Создание контекста с прокси и маскировкой автоматизации """
        context = self._browser.new_context(
            proxy=parse_proxy(proxy),
            viewport={'width': 1920, 'height': 1080},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/126.0.0.0 Safari/537.36'
            ),
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

    @log_calls(logger=logger, level=logging.DEBUG, log_args=False, log_result=False)
    def _context_close(self, context: BrowserContext) -> None:
        """ Безопасное закрытие контекста """
        try:
            context.close()
            time.sleep(3)
        except Exception:
            pass

    @log_calls(logger=logger, level=logging.DEBUG, log_result=False)
    def _fetch_page(self, url: str, retries: int = 3) -> str | None:
        """ Загрузка HTML страницы с ротацией прокси и обработкой 429/капчи """
        for r in range(retries):
            proxy = self._proxy_rotator.get_next_proxy()
            if not proxy:
                return None

            context = None
            try:
                context = self._create_context(proxy)
                page = context.new_page()

                time.sleep(3)

                response = page.goto(url, wait_until='domcontentloaded', timeout=30000)

                if not response:
                    self._proxy_rotator.report_fails(proxy, is_blok_ip=False)
                    continue

                if response.status == 429:
                    self._proxy_rotator.report_fails(proxy, is_blok_ip=True)
                    continue

                if response.status >= 400:
                    self._proxy_rotator.report_fails(proxy, is_blok_ip=False)
                    continue

                captcha = [
                    'iframe[src*="captcha"]',
                    '.captcha',
                    '[class*="captcha"]',
                    '[id*="captcha"]',
                    'div:has-text("Подтвердите")',
                ]

                for sel in captcha:
                    if page.query_selector(sel):
                        self._proxy_rotator.report_fails(proxy, is_blok_ip=True)
                        self._context_close(context)
                        if r < 2:
                            self._retried += 1
                            time.sleep(120)
                            return self._fetch_page(url, retries)
                        return None

                time.sleep(random.uniform(1, 3))

                html = page.content()

                self._proxy_rotator.report_success(proxy)
                return html

            except Exception:
                self._proxy_rotator.report_fails(proxy, is_blok_ip=False)

            finally:
                if context:
                    try:
                        context.close()
                    except Exception:
                        pass

        return None

    @staticmethod
    def _extract_series(html: str, code: str) -> list[dict]:
        """Извлекает данные для нахождения инфо. для выручки и чистого долга"""
        pattern = rf'if\s*\(\s*code\s*==\s*["\']{code}["\']\s*\)\s*{{?\s*var\s+series\s*=\s*\[\[(.*?)\]\]'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            return []

        parse = re.findall(
            r'\{\s*meta:\s*["\']([^"\']*)["\']\s*,\s*value:\s*["\']([^"\']*)["\']\s*\}',
            match.group(1),
        )
        return [{'meta': m, 'value': v} for m, v in parse]

    @staticmethod
    def _find_object_end(html: str, start_idx: int) -> int:
        """ Находит индекс """
        depth = 0
        in_string = False
        escape = False

        for i in range(start_idx, len(html)):
            ch = html[i]
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return i + 1
        return -1

    @log_calls(logger=logger, level=logging.DEBUG, log_result=False)
    def extract_financial(self, html: str) -> list[dict]:
        """ Извлекает выручку и чистую прибыль по годам """
        labels_match = re.search(r'(?:var|const)\s+labels\s*=\s*\[(.*?)\];', html)
        if not labels_match:
            return []

        years = re.findall(r'["\'](\d{4})["\']', labels_match.group(1))
        revenue_series = self._extract_series(html, '2110')
        profit_series = self._extract_series(html, '2400')

        if not revenue_series and not profit_series:
            return []

        result = []
        for i, year in enumerate(years):
            revenue = revenue_series[i] if i < len(revenue_series) else {'meta': '', 'value': ''}
            profit = profit_series[i] if i < len(profit_series) else {'meta': '', 'value': ''}
            result.append({
                'year': year,
                'revenue_text': revenue['meta'],
                'revenue_value': revenue['value'],
                'profit_text': profit['meta'],
                'profit_value': profit['value'],
            })
        return result

    @log_calls(logger=logger, level=logging.DEBUG, log_result=False)
    def extract_extended_statement_data(self, html_content: str) -> dict:
        """ Детализированные данные по годам """
        marker = "extendedStatementData:"
        start_idx = html_content.find(marker)
        if start_idx == -1:
            return {}

        start_idx += len(marker)
        while start_idx < len(html_content) and html_content[start_idx] in ' \t\n\r':
            start_idx += 1

        if start_idx >= len(html_content) or html_content[start_idx] != '{':
            return {}

        end_idx = self._find_object_end(html_content, start_idx)
        if end_idx == -1:
            return {}

        raw_json = html_content[start_idx:end_idx]
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _extract_company_id(company_url: str) -> str:
        """ Извлекает ID компании"""
        company_url = re.sub(r'/finances.*$', '', company_url.rstrip("/"))
        match = re.search(r'/company/[^/]*?-(\d+)$', company_url)
        if not match:
            match = re.search(r'/company/(\d+)$', company_url)
        if not match:
            raise ValueError(f'Не удалось извлечь ID: {company_url}')
        return match.group(1)

    @log_calls(logger=logger, level=logging.DEBUG, log_result=False)
    def extract_statement_data(self, html_content: str) -> dict:
        """ Плоские данные по годам """
        marker = "statementData:"
        start_idx = html_content.find(marker)
        if start_idx == -1:
            return {}

        start_idx += len(marker)
        while start_idx < len(html_content) and html_content[start_idx] in ' \t\n\r':
            start_idx += 1

        if start_idx >= len(html_content) or html_content[start_idx] != '{':
            return {}

        end_idx = self._find_object_end(html_content, start_idx)
        if end_idx == -1:
            return {}

        raw_json = html_content[start_idx:end_idx]
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return {}

    @log_calls(logger=logger, level=logging.DEBUG, log_result=False)
    def extract_and_calculate_net_debt(self, html_content: str) -> list[dict]:
        """ Считает чистый долг по годам """
        extended = self.extract_extended_statement_data(html_content)
        flat = self.extract_statement_data(html_content)

        result_by_year: dict[str, dict] = {}

        def get_val_from_extended(year_data: dict, code: str) -> float:
            if code in year_data and isinstance(year_data[code], dict):
                val = year_data[code].get('СумОтч', 0)
                if isinstance(val, (int, float)):
                    return val * 1000
            return 0

        def get_val_from_flat(year_data: dict, code: str) -> float:
            val = year_data.get(code, 0)
            if isinstance(val, (int, float)):
                return val * 1000
            return 0

        for year, year_data in extended.items():
            if not isinstance(year_data, dict):
                continue

            short_term = get_val_from_extended(year_data, '1510')
            long_term = get_val_from_extended(year_data, '1410')
            cash = get_val_from_extended(year_data, '1250')
            total_debt = short_term + long_term

            result_by_year[year] = {
                'year': year,
                'short_term_loans': short_term,
                'long_term_loans': long_term,
                'total_debt': total_debt,
                'cash': cash,
                'net_debt': total_debt - cash,
            }

        for year, year_data in flat.items():
            if year in result_by_year:
                continue
            if not isinstance(year_data, dict):
                continue

            short_term = get_val_from_flat(year_data, '1510')
            long_term = get_val_from_flat(year_data, '1410')
            cash = get_val_from_flat(year_data, '1250')

            if short_term == 0 and long_term == 0 and cash == 0:
                continue

            total_debt = short_term + long_term
            result_by_year[year] = {
                'year': year,
                'short_term_loans': short_term,
                'long_term_loans': long_term,
                'total_debt': total_debt,
                'cash': cash,
                'net_debt': total_debt - cash,
            }

        return sorted(result_by_year.values(), key=lambda x: x['year'])

    @log_calls(logger=logger, level=logging.INFO, log_result=False)
    def parse_company(self, company_url: str, inn: str) -> dict:
        """ Главная функция """
        company_id = self._extract_company_id(company_url)

        finance_url = f'{CHK_COMPANY_URL}/company/{company_id}/finances'
        accounting_url = f'{CHK_COMPANY_URL}/company/{company_id}/finances/accounting'

        finance_html = self._fetch_page(finance_url)
        accounting_html = self._fetch_page(accounting_url)

        financials = self.extract_financial(finance_html) if finance_html else []
        net_debt = self.extract_and_calculate_net_debt(accounting_html) if accounting_html else []

        return {
            'inn': inn,
            'financials': financials,
            'net_debt': net_debt,
        }