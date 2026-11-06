import time
import asyncio
from typing import List, Dict, Optional

class ProxyRotator:
    """Ротатор с временным баном."""

    def __init__(self, proxies: List[str]):
        self._proxies = proxies
        self._current = 0
        self._banned_until: Dict[str, float] = {}
        self._consecutive_fails: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    @property
    def has_proxies(self) -> bool:
        return len(self._proxies) > 0

    @property
    def total(self) -> int:
        return len(self._proxies)

    def _is_available(self, proxy: str) -> bool:
        return time.time() > self._banned_until.get(proxy, 0)

    def active_count(self) -> int:
        return sum(1 for p in self._proxies if self._is_available(p))

    async def get_next(self) -> Optional[str]:
        if not self._proxies:
            return None

        async with self._lock:
            available = [p for p in self._proxies if self._is_available(p)]

            if not available:
                soonest = min(self._proxies, key=lambda p: self._banned_until.get(p, 0))
                wait = self._banned_until[soonest] - time.time()
                if wait > 0:
                    print(f"\n⏳ Все прокси в бане, ждём {wait:.0f} сек...")
                    await asyncio.sleep(min(wait, 30))
                available = [p for p in self._proxies if self._is_available(p)]
                if not available:
                    available = self._proxies

            proxy = available[self._current % len(available)]
            self._current += 1
            return proxy

    async def report_fail(self, proxy: str, is_429: bool = False):
        async with self._lock:
            fails = self._consecutive_fails.get(proxy, 0) + 1
            self._consecutive_fails[proxy] = fails
            ban_minutes = min(2 ** fails, 30) if is_429 else min(fails * 2, 10)
            self._banned_until[proxy] = time.time() + (ban_minutes * 60)

    async def report_success(self, proxy: str):
        async with self._lock:
            if proxy in self._consecutive_fails:
                del self._consecutive_fails[proxy]