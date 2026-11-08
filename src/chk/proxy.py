import logging
import threading
import time

from config.logging_config import setup_logging
from utils.logging_decorators import log_calls

logger = setup_logging('proxy.log')


@log_calls(logger=logger, level=logging.DEBUG)
def parse_proxy(proxy: str) -> dict:
    """ Преобразует строку 'host:port:user:pass' в dict для Playwright """
    parts = proxy.split(':', 3)
    if len(parts) == 4:
        host, port, user, password = parts
        return {
            'server': f'http://{host}:{port}',
            'username': user,
            'password': password,
        }
    elif len(parts) == 2:
        host, port = parts
        return {
            'server': f'http://{host}:{port}',
        }
    raise ValueError(f'Неизвестный формат {proxy}')


class ProxyRotator:
    """ Ротатор прокси с временным баном """

    def __init__(self, proxies: list[str], max_ban_minutes: int = 30):
        self._proxies = [p.strip() for p in proxies if p and p.strip()]
        self._current = 0
        self._banned_untils: dict[str, float] = {}
        self._consecutive_fails: dict[str, int] = {}
        self._max_ban_minutes = max_ban_minutes
        self._lock = threading.Lock()

        logger.info(
            "ProxyRotator: инициализирован с %d прокси (max_ban=%d мин)",
            len(self._proxies), max_ban_minutes,
        )

    @log_calls(logger=logger, level=logging.DEBUG)
    def _is_available(self, proxy: str) -> bool:
        """ Прокси доступна, если время бана прошло """
        return time.time() > self._banned_untils.get(proxy, 0)

    @log_calls(logger=logger, level=logging.DEBUG)
    def get_next_proxy(self) -> str | None:
        """ Возвращает следующую доступную прокси """
        if not self._proxies:
            logger.warning("get_next_proxy: пул прокси пуст")
            return None

        with self._lock:
            available = [p for p in self._proxies if self._is_available(p)]

            if not available:
                upcoming = min(
                    self._proxies,
                    key=lambda p: self._banned_untils.get(p, 0),
                )
                wait = self._banned_untils.get(upcoming, 0) - time.time()

                if wait > 0:
                    logger.warning(
                        "get_next_proxy: все прокси в бане, ждём %.1f сек",
                        min(wait, 30),
                    )
                    time.sleep(min(wait, 30))

                available = [p for p in self._proxies if self._is_available(p)]
                if not available:
                    available = self._proxies

            proxy = available[self._current % len(available)]
            self._current += 1
            return proxy

    @log_calls(logger=logger, level=logging.DEBUG)
    def report_fails(self, proxy: str, is_blok_ip: bool) -> None:
        """ Увеличивает счётчик ошибок и временно банит прокси """
        with self._lock:
            fails = self._consecutive_fails.get(proxy, 0) + 1
            self._consecutive_fails[proxy] = fails

            if is_blok_ip:
                ban = min(2 ** fails, self._max_ban_minutes)
            else:
                ban = min(fails ** 2, self._max_ban_minutes)

            self._banned_untils[proxy] = time.time() + ban * 60

            logger.warning(
                "report_fails: прокси %s в бане на %d мин (fails=%d, is_blok_ip=%s)",
                proxy[:40], ban, fails, is_blok_ip,
            )

    @log_calls(logger=logger, level=logging.DEBUG)
    def report_success(self, proxy: str) -> None:
        """ Сбрасывает счётчик ошибок для прокси """
        with self._lock:
            if proxy in self._consecutive_fails:
                logger.info(
                    "report_success: прокси %s восстановлена (было ошибок: %d)",
                    proxy[:40], self._consecutive_fails[proxy],
                )
            self._consecutive_fails.pop(proxy, None)