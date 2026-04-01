import logging
import threading
from typing import Dict, List, Optional, Tuple

from .logger import CaptureRecord

_module_logger = logging.getLogger("phantom_snare.observer")

_RISK_HIGH_COUNT: int = 10
_RISK_MEDIUM_COUNT: int = 3

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

_TRAVERSAL_KEYWORDS: tuple = (
    b"../",
    b"..\\",
    b"%2e%2e",
    b"etc/passwd",
    b"etc/shadow",
    b"win/system32",
)


class Observer:
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
        self._session_counts: Dict[str, int] = {}

    def on_capture(self, record: CaptureRecord) -> None:
        if self._store is not None:
            self._store.save_capture(record)

        with self._lock:
            count = self._session_counts.get(record.remote_ip, 0) + 1
            self._session_counts[record.remote_ip] = count

        self._detect_patterns(record, count)

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

    def _detect_patterns(self, record: CaptureRecord, count: int) -> None:
        payload = record.payload or b""
        payload_lower = payload.lower()
        ip = record.remote_ip
        port = record.local_port

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

        if b"HTTP/" in payload:
            self._log_event(
                "HTTP_PROBE",
                ip,
                f"HTTP request on honeypot port {port}",
            )
            self._process_http(payload, ip)

        if any(kw in payload_lower for kw in _CREDENTIAL_KEYWORDS):
            self._log_event(
                "CREDENTIAL_PROBE",
                ip,
                f"Credential keyword detected on port {port}",
            )

        if any(kw in payload_lower for kw in _TRAVERSAL_KEYWORDS):
            self._log_event(
                "TRAVERSAL_ATTEMPT",
                ip,
                f"Directory traversal pattern on port {port}",
            )

        if len(payload) == 0:
            self._log_event(
                "PORT_SCAN_PROBE",
                ip,
                f"Zero-byte probe on port {port}",
            )

    def _extract_http_info(self, payload: bytes) -> Tuple[str, str, str]:
        try:
            lines = payload.split(b"\r\n")
            first_line = lines[0].decode("utf-8", errors="replace")
            parts = first_line.split(" ", 2)
            method = parts[0] if len(parts) >= 1 else ""
            path = parts[1] if len(parts) >= 2 else ""
            host = ""
            for line in lines[1:]:
                if line.lower().startswith(b"host:"):
                    host = line[5:].decode("utf-8", errors="replace").strip()
                    break
            return method, host, path
        except Exception:
            return "", "", ""

    def _classify_url(self, path: str, payload: bytes) -> Tuple[bool, str]:
        path_lower = path.lower()

        if self._deceptor is not None:
            honey_paths = self._deceptor.get_honey_token_paths()
            for hp in honey_paths:
                hp_lower = hp.lower()
                if path_lower == hp_lower or path_lower.startswith(hp_lower):
                    return True, f"Honey token path accessed: {path}"

        path_bytes = path_lower.encode("utf-8", errors="replace")
        for kw in _TRAVERSAL_KEYWORDS:
            if kw in path_bytes:
                return True, f"Directory traversal attempt: {path}"

        for kw in _CREDENTIAL_KEYWORDS:
            if kw in path_bytes:
                return True, f"Credential probe in URL: {path}"

        return False, ""

    def _process_http(self, payload: bytes, remote_ip: str) -> None:
        method, host, path = self._extract_http_info(payload)

        self._check_honey_token(payload, remote_ip)

        is_harmful, harm_reason = self._classify_url(path, payload)

        if self._store is not None:
            self._store.save_site_visit(
                remote_ip=remote_ip,
                host=host,
                path=path,
                method=method,
                is_harmful=is_harmful,
                harm_reason=harm_reason,
            )

        if is_harmful:
            self._log_event(
                "HARMFUL_URL_DETECTED",
                remote_ip,
                f"{method} {host}{path} — {harm_reason}",
            )

    def _check_honey_token(self, payload: bytes, remote_ip: str) -> None:
        if self._deceptor is None:
            return
        try:
            first_line = payload.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
            parts = first_line.split(" ", 2)
            if len(parts) >= 2:
                path = parts[1]
                self._deceptor.check_honey_token(path, remote_ip, f"HTTP payload: {first_line[:80]}")
        except Exception:
            pass

    def _log_event(self, event_type: str, ip: str, details: str) -> None:
        _module_logger.info("[Observer] %s from %s – %s", event_type, ip, details)
        if self._store is not None:
            self._store.save_event(event_type, ip, details)

    def compute_risk_score(self, ip: str) -> int:
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
        if score >= 60:
            return "HIGH"
        if score >= 30:
            return "MEDIUM"
        return "LOW"

    def get_ip_risk_summary(self) -> List[dict]:
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
