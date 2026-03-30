"""Module 1: Observer – Forensic Evidence Collection.

The Observer wraps the core :class:`~phantom_snare.snare.Snare` honeypot and
adds a forensic analysis layer.  For every captured connection it:

1. Persists structured evidence to the SQLite store.
2. Detects suspicious patterns (HTTP probing, credential keywords,
   directory-traversal attempts, port scans).
3. Computes per-IP risk scores and levels.
4. Checks whether an incoming HTTP payload targeted a honey-token path and
   hands off to the Deceptor for recording.
5. Notifies the Shield to auto-block IPs that cross the high-risk threshold.
"""

import logging
import threading
from typing import Dict, List, Optional

from .logger import CaptureRecord

_module_logger = logging.getLogger("phantom_snare.observer")

# Connection-count thresholds for risk scoring
_RISK_HIGH_COUNT: int = 10
_RISK_MEDIUM_COUNT: int = 3

# HTTP keywords that indicate credential probing
_CREDENTIAL_KEYWORDS: tuple = (
    b"password",
    b"passwd",
    b"login",
    b"admin",
    b"credential",
    b"secret",
    b"token",
    b"api_key",
    b"apikey",
)

# Path fragments that indicate directory traversal
_TRAVERSAL_KEYWORDS: tuple = (
    b"../",
    b"..\\",
    b"%2e%2e",
    b"etc/passwd",
    b"etc/shadow",
    b"win/system32",
)


class Observer:
    """Forensic evidence collector that sits above the Snare.

    The Snare calls :meth:`on_capture` after every accepted connection.
    This method analyses the capture, updates risk scores, and notifies
    other modules as needed.

    Args:
        evidence_store: Shared SQLite evidence store.
        shield:         Shield module instance (for auto-blocking).
        deceptor:       Deceptor module instance (for honey-token checks).
    """

    def __init__(
        self,
        evidence_store=None,
        shield=None,
        deceptor=None,
    ) -> None:
        self._store = evidence_store
        self._shield = shield
        self._deceptor = deceptor
        self._lock = threading.Lock()
        # Per-IP connection counter for this process session
        self._session_counts: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Capture callback (called from Snare._handle_connection)
    # ------------------------------------------------------------------

    def on_capture(self, record: CaptureRecord) -> None:
        """Analyse a captured connection and update all evidence state.

        This method is designed to be called from a worker thread so all
        operations must be thread-safe.
        """
        # 1. Persist raw capture to the evidence store
        if self._store is not None:
            self._store.save_capture(record)

        # 2. Update in-memory session counter
        with self._lock:
            count = self._session_counts.get(record.remote_ip, 0) + 1
            self._session_counts[record.remote_ip] = count

        # 3. Suspicious-pattern detection
        self._detect_patterns(record, count)

        # 4. Risk escalation – auto-block via Shield
        if count >= _RISK_HIGH_COUNT and self._shield is not None:
            reason = (
                f"Observer: {count} connections this session "
                f"(high-risk threshold: {_RISK_HIGH_COUNT})"
            )
            if not self._shield.is_blocked(record.remote_ip):
                _module_logger.warning(
                    "[Observer] Auto-blocking high-risk IP %s after %d connections",
                    record.remote_ip,
                    count,
                )
                self._shield.block_ip(record.remote_ip, reason)

    # ------------------------------------------------------------------
    # Pattern detection
    # ------------------------------------------------------------------

    def _detect_patterns(self, record: CaptureRecord, count: int) -> None:
        payload = record.payload or b""
        payload_lower = payload.lower()
        ip = record.remote_ip
        port = record.local_port

        # Medium/high risk based on connection frequency
        if count >= _RISK_HIGH_COUNT:
            self._log_event(
                "HIGH_RISK_CONNECTION",
                ip,
                f"Connection #{count} on port {port} (high-risk threshold reached)",
            )
        elif count >= _RISK_MEDIUM_COUNT:
            self._log_event(
                "MEDIUM_RISK_CONNECTION",
                ip,
                f"Connection #{count} on port {port}",
            )

        # HTTP probe
        if b"HTTP/" in payload:
            self._log_event(
                "HTTP_PROBE",
                ip,
                f"HTTP request on honeypot port {port}",
            )
            # Extract request path and check honey tokens
            self._check_honey_token(payload, ip)

        # Credential keyword scan
        if any(kw in payload_lower for kw in _CREDENTIAL_KEYWORDS):
            self._log_event(
                "CREDENTIAL_PROBE",
                ip,
                f"Credential keyword detected on port {port}",
            )

        # Directory traversal
        if any(kw in payload_lower for kw in _TRAVERSAL_KEYWORDS):
            self._log_event(
                "TRAVERSAL_ATTEMPT",
                ip,
                f"Directory traversal pattern on port {port}",
            )

        # Port scan signature: zero-byte payload (SYN probe, no data sent)
        if len(payload) == 0:
            self._log_event(
                "PORT_SCAN_PROBE",
                ip,
                f"Zero-byte probe on port {port}",
            )

    def _check_honey_token(self, payload: bytes, remote_ip: str) -> None:
        """Extract the request path from an HTTP payload and check for honey tokens."""
        if self._deceptor is None:
            return
        try:
            # First line of HTTP request: "GET /path HTTP/1.1"
            first_line = payload.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
            parts = first_line.split(" ", 2)
            if len(parts) >= 2:
                path = parts[1]
                self._deceptor.check_honey_token(path, remote_ip, f"HTTP payload: {first_line[:80]}")
        except Exception:  # pylint: disable=broad-except
            pass

    def _log_event(self, event_type: str, ip: str, details: str) -> None:
        _module_logger.info("[Observer] %s from %s – %s", event_type, ip, details)
        if self._store is not None:
            self._store.save_event(event_type, ip, details)

    # ------------------------------------------------------------------
    # Risk scoring API (used by Vault)
    # ------------------------------------------------------------------

    def compute_risk_score(self, ip: str) -> int:
        """Return a risk score 0-100 for *ip* based on session connection count."""
        count = self._session_counts.get(ip, 0)
        if count == 0:
            return 0
        if count >= _RISK_HIGH_COUNT:
            return min(100, 60 + (count - _RISK_HIGH_COUNT) * 4)
        if count >= _RISK_MEDIUM_COUNT:
            return 30 + (count - _RISK_MEDIUM_COUNT) * 10
        return count * 5

    @staticmethod
    def risk_label(score: int) -> str:
        """Return a human-readable risk label for a numeric score."""
        if score >= 60:
            return "HIGH"
        if score >= 30:
            return "MEDIUM"
        return "LOW"

    def get_ip_risk_summary(self) -> List[dict]:
        """Return a list of per-IP risk summaries for the dashboard."""
        with self._lock:
            items = list(self._session_counts.items())
        result = []
        for ip, count in sorted(items, key=lambda x: -x[1]):
            score = self.compute_risk_score(ip)
            result.append(
                {
                    "ip": ip,
                    "connections": count,
                    "risk_score": score,
                    "risk_level": self.risk_label(score),
                }
            )
        return result
