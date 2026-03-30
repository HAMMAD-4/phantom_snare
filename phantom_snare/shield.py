"""Module 2: Shield – Neutralization & Blocking.

The Shield enforces two protection mechanisms:

1. **Static blocklist** – IPs added manually (via the Vault dashboard or the
   API) or automatically by the Observer are denied on every subsequent
   connection and receive a deceptive response instead.

2. **Rate limiting** – Any IP that exceeds *max_connections_per_minute* is
   automatically added to the blocklist with a reason string.

All state is persisted to the :class:`~phantom_snare.sqlite_db.EvidenceStore`
so that blocks survive a process restart.
"""

import collections
import logging
import threading
import time
from typing import Deque, Dict, Optional

_module_logger = logging.getLogger("phantom_snare.shield")

# Default rate-limit threshold (connections per 60-second rolling window).
_DEFAULT_MAX_CPM: int = 20


class Shield:
    """Rate-limiter and IP blocklist manager.

    Args:
        evidence_store: Shared :class:`~phantom_snare.sqlite_db.EvidenceStore`.
            May be *None* (blocks are then in-memory only).
        max_connections_per_minute: Connections per 60-second rolling window
            before an IP is automatically blocked.
    """

    def __init__(
        self,
        evidence_store=None,
        max_connections_per_minute: int = _DEFAULT_MAX_CPM,
    ) -> None:
        self._store = evidence_store
        self._max_cpm = max_connections_per_minute
        self._lock = threading.Lock()
        # Rolling per-IP timestamps for rate tracking
        self._rate_table: Dict[str, Deque[float]] = collections.defaultdict(
            lambda: collections.deque(maxlen=200)
        )

    # ------------------------------------------------------------------
    # Core decision method (called per incoming connection)
    # ------------------------------------------------------------------

    def check_and_record(self, remote_ip: str) -> bool:
        """Decide whether to allow a connection from *remote_ip*.

        Records the attempt for rate-limit tracking.

        Returns:
            ``True``  – connection should be allowed (normal processing).
            ``False`` – connection should be blocked (deceptive response).
        """
        # 1. Static blocklist check (fast path)
        if self._store is not None and self._store.is_blocked(remote_ip):
            _module_logger.info(
                "[Shield] Blocked (blocklist): %s", remote_ip
            )
            return False

        # 2. Rate-limit check
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

    # ------------------------------------------------------------------
    # Manual blocklist management
    # ------------------------------------------------------------------

    def block_ip(self, ip: str, reason: str = "Manual block") -> None:
        """Add *ip* to the blocklist."""
        self._persist_block(ip, reason)
        _module_logger.info("[Shield] Blocked %s: %s", ip, reason)

    def unblock_ip(self, ip: str) -> None:
        """Remove *ip* from the blocklist."""
        if self._store is not None:
            self._store.unblock_ip(ip)
            self._store.save_event("SHIELD_UNBLOCK", ip, "Manually unblocked")
        _module_logger.info("[Shield] Unblocked %s", ip)

    def is_blocked(self, ip: str) -> bool:
        """Return *True* if *ip* is currently blocked."""
        if self._store is not None:
            return self._store.is_blocked(ip)
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _persist_block(self, ip: str, reason: str) -> None:
        if self._store is not None:
            self._store.block_ip(ip, reason)
            self._store.save_event("SHIELD_BLOCK", ip, reason)
