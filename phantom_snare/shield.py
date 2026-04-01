import collections
import logging
import threading
import time
from typing import Deque, Dict, Optional

_module_logger = logging.getLogger("phantom_snare.shield")

_DEFAULT_MAX_CPM: int = 20


class Shield:
    def __init__(
        self,
        evidence_store=None,
        max_connections_per_minute: int = _DEFAULT_MAX_CPM,
    ) -> None:
        self._store = evidence_store
        self._max_cpm = max_connections_per_minute
        self._lock = threading.Lock()
        self._rate_table: Dict[str, Deque[float]] = collections.defaultdict(
            lambda: collections.deque(maxlen=200)
        )

    def check_and_record(self, remote_ip: str) -> bool:
        if self._store is not None and self._store.is_blocked(remote_ip):
            _module_logger.info(
                "[Shield] Blocked (blocklist): %s", remote_ip
            )
            return False

        now = time.monotonic()
        with self._lock:
            ts = self._rate_table[remote_ip]
            cutoff = now - 60.0
            while ts and ts[0] < cutoff:
                ts.popleft()
            ts.append(now)
            rate = len(ts)

        if rate > self._max_cpm:
            reason = (
                f"Rate limit exceeded: {rate} connections/minute "
                f"(threshold: {self._max_cpm})"
            )
            _module_logger.warning(
                "[Shield] Auto-blocking %s – %s", remote_ip, reason
            )
            self._persist_block(remote_ip, reason)
            return False

        return True

    def block_ip(self, ip: str, reason: str = "Manual block") -> None:
        self._persist_block(ip, reason)
        _module_logger.info("[Shield] Blocked %s: %s", ip, reason)

    def unblock_ip(self, ip: str) -> None:
        if self._store is not None:
            self._store.unblock_ip(ip)
            self._store.save_event("SHIELD_UNBLOCK", ip, "Manually unblocked")
        _module_logger.info("[Shield] Unblocked %s", ip)

    def is_blocked(self, ip: str) -> bool:
        if self._store is not None:
            return self._store.is_blocked(ip)
        return False

    def _persist_block(self, ip: str, reason: str) -> None:
        if self._store is not None:
            self._store.block_ip(ip, reason)
            self._store.save_event("SHIELD_BLOCK", ip, reason)
