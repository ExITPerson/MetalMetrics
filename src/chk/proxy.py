import threading
import time
import asyncio
from typing import List, Dict, Optional

def parse_proxy(proxy: str) -> dict:
    parts = proxy.split(':', 3)
    if len(parts) == 4:
        host, port, user, password = parts

        return {
            'server': f'http://{host}:{port}',
            'username': user,
            'password': password
        }

    elif len(parts) == 2:
        host, port = parts
        return {
            'server': f'http://{host}:{port}'
        }

    raise ValueError(f'Неизвестный формат {proxy}')

class ProxyRotator:
    """ Ротатор с временным баном """

    def __init__(self, proxies: list[str], max_ban_minutes: int = 30):
        self._proxies = [p.strip() for p in proxies if p and p.strip()]
        self._current = 0
        self._banned_untils = {}
        self._consecutive_fails = {}
        self._max_ban_minutes = 30
        self._lock = threading.Lock()

    def _is_available(self, proxy: str) -> bool:
        return time.time() > self._banned_untils.get(proxy, 0)

    def get_next_proxy(self):
        if not self._proxies:
            return None

        with self._lock:
            available = [p for p in self._proxies if self._is_available(p)]

            if not available:
                upcoming = min(self._proxies, key=lambda p: self._banned_untils.get(p, 0))
                wait = self._banned_untils.get(upcoming, 0) - time.time()

                if wait > 0:
                    time.sleep(min(wait, 30))

                available = [p for p in self._proxies if self._is_available(p)]
                if not available:
                    available = self._proxies

            proxy = available[self._current % len(available)]
            self._current += 1

            return proxy

    def report_fails(self, proxy: str, is_blok_ip: bool) -> None:
        with self._lock:
            fails = self._consecutive_fails.get(proxy, 0) + 1
            self._consecutive_fails[proxy] = fails

            if is_blok_ip:
                ban = min(2 ** fails, self._max_ban_minutes)

            else:
                ban = min(fails ** 2, self._max_ban_minutes)

            self._banned_untils[proxy] == time.time() + ban * 60

    def report_success(self, proxy: str) -> None:
        with self._lock:
            self._consecutive_fails.pop(proxy, None)